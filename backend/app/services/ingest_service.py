"""
Dataset ingestion service for CyberSentinel AI.

Handles:
- Cleaning and normalising incident DataFrames from CSV uploads or the
  data/ folder.
- Batch-ingesting rows into Postgres, Qdrant (vector embeddings), and
  Neo4j (graph relationships).
- Rebuilding the Qdrant index from Postgres for any rows with a missing
  embedding_id.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import AsyncSessionLocal
from backend.app.models.incident import Incident
from backend.app.rag.embeddings import EmbeddingService
from backend.app.rag.vector_store import VectorStoreService
from backend.app.graph.neo4j_service import GraphService

# ---------------------------------------------------------------------------
# Column normalisation maps
# ---------------------------------------------------------------------------

_SEVERITY_MAP: Dict[str, str] = {
    "critical": "critical",
    "crit": "critical",
    "high": "high",
    "h": "high",
    "medium": "medium",
    "med": "medium",
    "m": "medium",
    "low": "low",
    "l": "low",
    "info": "low",
    "informational": "low",
}

_ATTACK_TYPE_MAP: Dict[str, str] = {
    "bruteforce": "Brute Force",
    "brute force": "Brute Force",
    "brute-force": "Brute Force",
    "brute_force": "Brute Force",
    "ddos": "DDoS",
    "dos": "DDoS",
    "distributed denial of service": "DDoS",
    "phishing": "Phishing",
    "malware": "Malware",
    "malicious software": "Malware",
    "ransomware": "Malware",
    "portscan": "Port Scan",
    "port scan": "Port Scan",
    "port-scan": "Port Scan",
    "port_scan": "Port Scan",
    "sql injection": "SQL Injection",
    "sqli": "SQL Injection",
    "sql_injection": "SQL Injection",
    "xss": "XSS",
    "cross-site scripting": "XSS",
    "cross site scripting": "XSS",
    "benign": "Benign",
    "normal": "Benign",
    "clean": "Benign",
}

_COLUMN_RENAMES: Dict[str, str] = {
    "destination_ip": "dest_ip",
    "dst_ip": "dest_ip",
    "dest": "dest_ip",
    "destination": "dest_ip",
    "source": "source_ip",
    "src_ip": "source_ip",
    "destination_port": "dest_port",
    "dst_port": "dest_port",
    "source_port": "source_port",
    "src_port": "source_port",
    "ts": "timestamp",
    "time": "timestamp",
    "type": "attack_type",
    "attack": "attack_type",
    "proto": "protocol",
}

# ---------------------------------------------------------------------------
# DataFrame cleaning
# ---------------------------------------------------------------------------


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Normalise and clean an incident DataFrame for ingestion.

    Operations performed:
    - Strip whitespace and lower-case all column names; convert spaces to
      underscores.
    - Apply column rename aliases.
    - Normalise ``severity`` values to ``critical|high|medium|low``.
    - Normalise ``attack_type`` values to canonical names.
    - Drop rows with missing ``source_ip`` or ``dest_ip``.
    - Create a ``raw_text`` column with a human-readable incident sentence.

    Parameters
    ----------
    df:
        Raw incident DataFrame (e.g. loaded from a CSV upload).

    Returns
    -------
    pd.DataFrame
        Cleaned DataFrame ready for :func:`ingest_dataframe`.
    """
    df = df.copy()

    # ------------------------------------------------------------------ #
    # 1. Normalise column names                                           #
    # ------------------------------------------------------------------ #
    df.columns = [
        col.strip().lower().replace(" ", "_").replace("-", "_")
        for col in df.columns
    ]
    df = df.rename(columns={k: v for k, v in _COLUMN_RENAMES.items() if k in df.columns})

    # ------------------------------------------------------------------ #
    # 2. Normalise severity                                               #
    # ------------------------------------------------------------------ #
    if "severity" in df.columns:
        df["severity"] = (
            df["severity"]
            .astype(str)
            .str.strip()
            .str.lower()
            .map(lambda v: _SEVERITY_MAP.get(v, "low"))
        )
    else:
        df["severity"] = "low"

    # ------------------------------------------------------------------ #
    # 3. Normalise attack_type                                            #
    # ------------------------------------------------------------------ #
    if "attack_type" in df.columns:
        df["attack_type"] = (
            df["attack_type"]
            .astype(str)
            .str.strip()
            .map(lambda v: _ATTACK_TYPE_MAP.get(v.lower(), v.title()))
        )
    else:
        df["attack_type"] = "Unknown"

    # ------------------------------------------------------------------ #
    # 4. Drop rows with missing source_ip or dest_ip                     #
    # ------------------------------------------------------------------ #
    for col in ("source_ip", "dest_ip"):
        if col in df.columns:
            df = df[df[col].notna() & (df[col].astype(str).str.strip() != "")]
        else:
            logger.warning("Column '%s' not found — skipping IP filter", col)

    if df.empty:
        logger.warning("DataFrame is empty after dropping rows with missing IPs")
        return df

    # ------------------------------------------------------------------ #
    # 5. Ensure optional columns exist                                    #
    # ------------------------------------------------------------------ #
    for col in ("protocol", "label", "timestamp"):
        if col not in df.columns:
            df[col] = None

    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")

    # ------------------------------------------------------------------ #
    # 6. Create raw_text                                                  #
    # ------------------------------------------------------------------ #
    def _build_raw_text(row: pd.Series) -> str:
        ts = row.get("timestamp")
        ts_str = str(ts) if pd.notna(ts) else datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        attack = row.get("attack_type", "Unknown")
        src_ip = row.get("source_ip", "N/A")
        dst_ip = row.get("dest_ip", "N/A")
        proto = row.get("protocol", "Unknown")
        sev = row.get("severity", "low")
        label = row.get("label", "")
        label_part = f", label {label}" if label and str(label).strip() else ""
        return (
            f"Incident on {ts_str}: {attack} from {src_ip} to {dst_ip} "
            f"over {proto}, severity {sev}{label_part}."
        )

    df["raw_text"] = df.apply(_build_raw_text, axis=1)

    logger.info("DataFrame cleaned", rows=len(df), columns=list(df.columns))
    return df


# ---------------------------------------------------------------------------
# Batch ingestion
# ---------------------------------------------------------------------------


async def ingest_dataframe(
    df: pd.DataFrame,
    user_id: str,
    batch_size: int = 50,
    db: Optional[AsyncSession] = None,
) -> Dict[str, int]:
    """Ingest a cleaned incident DataFrame into Postgres, Qdrant, and Neo4j.

    For each row:
    1. Creates an :class:`~backend.app.models.incident.Incident` in Postgres.
    2. Generates a text embedding for ``raw_text``.
    3. Upserts the vector into Qdrant with incident metadata.
    4. Creates Neo4j nodes and relationships.

    Parameters
    ----------
    df:
        Cleaned incident DataFrame (output of :func:`clean_dataframe`).
    user_id:
        Clerk user ID of the uploader.
    batch_size:
        Number of rows to embed in a single OpenAI API call.
    db:
        Optional existing async session.  A fresh session is created per
        batch if omitted.

    Returns
    -------
    dict
        ``{total: int, success: int, failed: int}``
    """
    if df.empty:
        logger.warning("ingest_dataframe called with empty DataFrame")
        return {"total": 0, "success": 0, "failed": 0}

    embedding_svc = EmbeddingService()
    vector_store = VectorStoreService()
    graph_svc = GraphService()

    await vector_store.initialize_collection()

    total = len(df)
    success = 0
    failed = 0

    # Split into batches
    rows_list = df.to_dict(orient="records")
    batches = [rows_list[i : i + batch_size] for i in range(0, total, batch_size)]

    for batch_idx, batch in enumerate(batches):
        logger.info(
            "Processing ingestion batch",
            batch=batch_idx + 1,
            total_batches=len(batches),
            rows=len(batch),
        )

        # ---- Generate embeddings for the whole batch ---- #
        raw_texts = [row.get("raw_text", "") for row in batch]
        try:
            embeddings = await embedding_svc.embed_batch(raw_texts)
        except Exception as exc:
            logger.error("Embedding batch failed", batch=batch_idx, error=str(exc))
            failed += len(batch)
            continue

        # ---- Persist each row ---- #
        async def _process_batch(session: AsyncSession) -> Tuple[int, int]:
            batch_success = 0
            batch_failed = 0

            for row_idx, (row, embedding) in enumerate(zip(batch, embeddings)):
                try:
                    incident_id = uuid.uuid4()

                    # Parse timestamp
                    ts = row.get("timestamp")
                    if ts is not None and not isinstance(ts, datetime):
                        try:
                            ts = pd.to_datetime(ts).to_pydatetime()
                        except Exception:
                            ts = None

                    # Build Incident ORM object
                    incident = Incident(
                        id=incident_id,
                        user_id=user_id,
                        timestamp=ts,
                        source_ip=str(row.get("source_ip", "") or ""),
                        dest_ip=str(row.get("dest_ip", "") or ""),
                        protocol=str(row.get("protocol", "") or ""),
                        attack_type=str(row.get("attack_type", "") or ""),
                        severity=str(row.get("severity", "low") or "low").lower(),
                        label=str(row.get("label", "") or "") or None,
                        raw_text=str(row.get("raw_text", "") or ""),
                        embedding_id=str(incident_id),
                    )
                    session.add(incident)

                    # Upsert into Qdrant
                    payload: Dict[str, Any] = {
                        "incident_id": str(incident_id),
                        "user_id": user_id,
                        "attack_type": incident.attack_type,
                        "severity": incident.severity,
                        "protocol": incident.protocol,
                        "source_ip": incident.source_ip,
                        "dest_ip": incident.dest_ip,
                        "raw_text": incident.raw_text,
                        "timestamp": incident.timestamp.isoformat() if incident.timestamp else None,
                    }
                    await vector_store.upsert_incident(
                        incident_id=str(incident_id),
                        embedding=embedding,
                        payload=payload,
                    )

                    # Create Neo4j relationships (best-effort)
                    try:
                        await graph_svc.create_incident_node(
                            {
                                "incident_id": str(incident_id),
                                "attack_type": incident.attack_type,
                                "severity": incident.severity,
                                "source_ip": incident.source_ip,
                                "dest_ip": incident.dest_ip,
                                "protocol": incident.protocol,
                            }
                        )
                        if (
                            incident.attack_type
                            and incident.source_ip
                            and incident.dest_ip
                        ):
                            await graph_svc.create_relationships(
                                incident_id=str(incident_id),
                                attack_type=incident.attack_type,
                                source_ip=incident.source_ip,
                                dest_ip=incident.dest_ip,
                                severity=incident.severity or "low",
                                protocol=incident.protocol or "Unknown",
                            )
                    except Exception as graph_exc:
                        logger.warning(
                            "Neo4j ingestion failed for row",
                            row_idx=row_idx,
                            error=str(graph_exc),
                        )

                    batch_success += 1

                except Exception as row_exc:
                    logger.error(
                        "Row ingestion failed",
                        batch=batch_idx,
                        row=row_idx,
                        error=str(row_exc),
                    )
                    batch_failed += 1

            await session.flush()
            return batch_success, batch_failed

        if db is not None:
            bs, bf = await _process_batch(db)
        else:
            async with AsyncSessionLocal() as session:
                bs, bf = await _process_batch(session)
                try:
                    await session.commit()
                except Exception as commit_exc:
                    await session.rollback()
                    logger.error(
                        "Batch commit failed",
                        batch=batch_idx,
                        error=str(commit_exc),
                    )
                    bs, bf = 0, len(batch)

        success += bs
        failed += bf

    await graph_svc.close()

    result = {"total": total, "success": success, "failed": failed}
    logger.info("Ingestion complete", **result)
    return result


# ---------------------------------------------------------------------------
# Qdrant index rebuild
# ---------------------------------------------------------------------------


async def build_qdrant_index(
    user_id: Optional[str] = None,
    batch_size: int = 50,
) -> Dict[str, int]:
    """Rebuild the Qdrant index from Postgres incidents.

    Loads all incidents (optionally filtered by *user_id*), generates
    embeddings for any row whose ``embedding_id`` is ``None``, and
    upserts all vectors into Qdrant.

    Parameters
    ----------
    user_id:
        Optional user ID filter.  If ``None``, all incidents are processed.
    batch_size:
        Number of incidents per embedding API call.

    Returns
    -------
    dict
        ``{total: int, upserted: int, failed: int}``
    """
    embedding_svc = EmbeddingService()
    vector_store = VectorStoreService()
    await vector_store.initialize_collection()

    # ------------------------------------------------------------------ #
    # Load incidents from Postgres                                        #
    # ------------------------------------------------------------------ #

    async with AsyncSessionLocal() as session:
        stmt = select(Incident)
        if user_id:
            stmt = stmt.where(Incident.user_id == user_id)
        result = await session.execute(stmt)
        incidents: List[Incident] = list(result.scalars().all())

    total = len(incidents)
    upserted = 0
    failed = 0

    logger.info("Building Qdrant index", total_incidents=total)

    if total == 0:
        return {"total": 0, "upserted": 0, "failed": 0}

    # ------------------------------------------------------------------ #
    # Process in batches                                                  #
    # ------------------------------------------------------------------ #

    batches = [incidents[i : i + batch_size] for i in range(0, total, batch_size)]

    for batch_idx, batch in enumerate(batches):
        raw_texts = [inc.raw_text or "" for inc in batch]
        try:
            embeddings = await embedding_svc.embed_batch(raw_texts)
        except Exception as exc:
            logger.error(
                "Embedding batch failed during index rebuild",
                batch=batch_idx,
                error=str(exc),
            )
            failed += len(batch)
            continue

        for inc, embedding in zip(batch, embeddings):
            try:
                payload: Dict[str, Any] = {
                    "incident_id": str(inc.id),
                    "user_id": inc.user_id,
                    "attack_type": inc.attack_type,
                    "severity": inc.severity,
                    "protocol": inc.protocol,
                    "source_ip": inc.source_ip,
                    "dest_ip": inc.dest_ip,
                    "raw_text": inc.raw_text,
                    "timestamp": inc.timestamp.isoformat() if inc.timestamp else None,
                }
                await vector_store.upsert_incident(
                    incident_id=str(inc.id),
                    embedding=embedding,
                    payload=payload,
                )

                # Update embedding_id in Postgres if missing
                if not inc.embedding_id:
                    async with AsyncSessionLocal() as session:
                        db_inc = await session.get(Incident, inc.id)
                        if db_inc:
                            db_inc.embedding_id = str(inc.id)
                            await session.commit()

                upserted += 1
            except Exception as upsert_exc:
                logger.error(
                    "Upsert failed during index rebuild",
                    incident_id=str(inc.id),
                    error=str(upsert_exc),
                )
                failed += 1

    result_dict = {"total": total, "upserted": upserted, "failed": failed}
    logger.info("Qdrant index rebuild complete", **result_dict)
    return result_dict


# ---------------------------------------------------------------------------
# CSV file ingestion helper
# ---------------------------------------------------------------------------


async def ingest_csv_file(
    file_path: str,
    user_id: str,
    batch_size: int = 50,
) -> Dict[str, int]:
    """Load a CSV from *file_path*, clean it, and ingest it.

    Parameters
    ----------
    file_path:
        Absolute path to a CSV file.
    user_id:
        Clerk user ID of the uploader.
    batch_size:
        Embedding batch size.

    Returns
    -------
    dict
        ``{total: int, success: int, failed: int}``
    """
    df = pd.read_csv(file_path)
    df = clean_dataframe(df)
    return await ingest_dataframe(df, user_id=user_id, batch_size=batch_size)
