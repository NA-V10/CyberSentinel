"""FastAPI router: Incident ingestion endpoints.

Routes
------
POST /ingest/upload-csv   — Upload a CSV file and batch-ingest incidents
POST /ingest/build-index  — Re-index all DB incidents into Qdrant

Both routes require the authenticated user to have the "admin" role.
"""

from __future__ import annotations

import csv
import io
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from loguru import logger
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.clerk import get_current_user
from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.graph.neo4j_service import GraphService
from backend.app.models.incident import Incident
from backend.app.rag.embeddings import EmbeddingService
from backend.app.rag.vector_store import VectorStoreService

router = APIRouter()

# ---------------------------------------------------------------------------
# Required CSV columns (case-insensitive)
# ---------------------------------------------------------------------------
_REQUIRED_COLUMNS = {"raw_text"}
_OPTIONAL_COLUMNS = {
    "source_ip",
    "dest_ip",
    "protocol",
    "attack_type",
    "severity",
    "label",
    "timestamp",
}
_VALID_SEVERITIES = {"low", "medium", "high", "critical"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _require_admin(current_user: Dict[str, Any]) -> None:
    role: str = current_user.get("role", "analyst")
    if role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required for this operation.",
        )


def _normalise_severity(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    s = raw.strip().lower()
    return s if s in _VALID_SEVERITIES else None


def _parse_csv(content: bytes) -> List[Dict[str, str]]:
    """Parse CSV bytes into a list of row dicts."""
    text_content = content.decode("utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(text_content))
    rows = list(reader)
    return rows


def _validate_columns(rows: List[Dict[str, str]]) -> str:
    """Return an error message if required columns are missing, else empty str."""
    if not rows:
        return "CSV file is empty."
    columns = {k.strip().lower() for k in (rows[0].keys() or [])}
    missing = _REQUIRED_COLUMNS - columns
    if missing:
        return f"Missing required CSV columns: {missing}"
    return ""


def _clean_row(row: Dict[str, str]) -> Dict[str, Any]:
    """Normalise a raw CSV row dict into a cleaned incident field dict."""
    normalised = {k.strip().lower(): (v.strip() if isinstance(v, str) else v) for k, v in row.items()}
    return {
        "raw_text": normalised.get("raw_text") or "",
        "source_ip": normalised.get("source_ip") or None,
        "dest_ip": normalised.get("dest_ip") or None,
        "protocol": normalised.get("protocol") or None,
        "attack_type": normalised.get("attack_type") or None,
        "severity": _normalise_severity(normalised.get("severity")),
        "label": normalised.get("label") or None,
    }


# ---------------------------------------------------------------------------
# CSV upload endpoint
# ---------------------------------------------------------------------------


@router.post(
    "/upload-csv",
    summary="Upload a CSV file of incidents for batch ingestion",
    status_code=status.HTTP_200_OK,
)
async def upload_csv(
    file: UploadFile = File(..., description="CSV file with incident records"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Parse a CSV file and bulk-ingest incidents into Postgres, Qdrant, and Neo4j.

    **Required columns**: ``raw_text``

    **Optional columns**: ``source_ip``, ``dest_ip``, ``protocol``,
    ``attack_type``, ``severity``, ``label``, ``timestamp``

    **Authentication**: Admin role required.
    """
    _require_admin(current_user)
    user_id: str = current_user["user_id"]

    # ---- Read file ----
    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    rows = _parse_csv(content)
    col_error = _validate_columns(rows)
    if col_error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=col_error,
        )

    logger.info("upload_csv: processing", rows=len(rows), user_id=user_id)

    # ---- Services ----
    embedding_svc = EmbeddingService(api_key=settings.OPENAI_API_KEY)
    vector_store = VectorStoreService()
    graph_svc = GraphService()

    await vector_store.initialize_collection()

    processed = 0
    errors: List[str] = []
    incidents_created: List[Incident] = []

    for idx, raw_row in enumerate(rows):
        try:
            cleaned = _clean_row(raw_row)
            if not cleaned["raw_text"]:
                errors.append(f"Row {idx + 1}: empty raw_text, skipped.")
                continue

            incident = Incident(
                user_id=user_id,
                source_ip=cleaned["source_ip"],
                dest_ip=cleaned["dest_ip"],
                protocol=cleaned["protocol"],
                attack_type=cleaned["attack_type"],
                severity=cleaned["severity"],
                label=cleaned["label"],
                raw_text=cleaned["raw_text"],
            )
            db.add(incident)
            incidents_created.append(incident)
            processed += 1

        except Exception as exc:
            errors.append(f"Row {idx + 1}: {str(exc)}")

    # Flush to get IDs assigned
    await db.flush()

    # ---- Embed + upsert into Qdrant + Neo4j ----
    texts = [inc.raw_text or "" for inc in incidents_created]
    embeddings = []
    try:
        embeddings = await embedding_svc.embed_batch(texts)
    except Exception as exc:
        logger.error("upload_csv: embedding failed", error=str(exc))
        errors.append(f"Embedding batch failed: {str(exc)}")

    for inc, emb in zip(incidents_created, embeddings):
        try:
            inc_id = str(inc.id)
            payload = {
                "incident_id": inc_id,
                "user_id": user_id,
                "raw_text": (inc.raw_text or "")[:500],
                "attack_type": inc.attack_type,
                "severity": inc.severity,
                "protocol": inc.protocol,
                "source_ip": inc.source_ip,
                "dest_ip": inc.dest_ip,
                "label": inc.label,
            }
            await vector_store.upsert_incident(
                incident_id=inc_id,
                embedding=emb,
                payload=payload,
            )
            inc.embedding_id = inc_id

            # Neo4j node + relationships
            await graph_svc.create_incident_node(
                {
                    "incident_id": inc_id,
                    "user_id": user_id,
                    "attack_type": inc.attack_type or "Unknown",
                    "severity": inc.severity or "unknown",
                }
            )
            if inc.attack_type:
                await graph_svc.create_relationships(
                    incident_id=inc_id,
                    attack_type=inc.attack_type or "Unknown",
                    source_ip=inc.source_ip or "0.0.0.0",
                    dest_ip=inc.dest_ip or "0.0.0.0",
                    severity=inc.severity or "unknown",
                    protocol=inc.protocol or "TCP",
                )
        except Exception as exc:
            errors.append(f"Incident {inc.id}: vector/graph upsert failed: {str(exc)}")

    await db.commit()
    await graph_svc.close()

    logger.info(
        "upload_csv: complete",
        processed=processed,
        errors=len(errors),
        user_id=user_id,
    )

    return {
        "status": "success" if not errors else "partial",
        "processed": processed,
        "total_rows": len(rows),
        "errors": errors[:20],  # cap error list in response
    }


# ---------------------------------------------------------------------------
# Build index endpoint
# ---------------------------------------------------------------------------


@router.post(
    "/build-index",
    summary="Re-index all incidents from the database into Qdrant",
    status_code=status.HTTP_200_OK,
)
async def build_index(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Re-embed all incidents in the Postgres database and upsert into Qdrant.

    Useful after changing the embedding model or clearing the vector index.

    **Authentication**: Admin role required.
    """
    _require_admin(current_user)
    user_id: str = current_user["user_id"]
    logger.info("build_index: starting full re-index", user_id=user_id)

    result = await db.execute(select(Incident).order_by(Incident.created_at))
    incidents: List[Incident] = list(result.scalars().all())

    if not incidents:
        return {"status": "ok", "indexed": 0, "errors": []}

    embedding_svc = EmbeddingService(api_key=settings.OPENAI_API_KEY)
    vector_store = VectorStoreService()
    await vector_store.initialize_collection()

    _CHUNK = 50  # embed in batches to respect rate limits
    indexed = 0
    errors: List[str] = []

    for start in range(0, len(incidents), _CHUNK):
        chunk = incidents[start : start + _CHUNK]
        texts = [inc.raw_text or inc.label or "" for inc in chunk]

        try:
            embeddings = await embedding_svc.embed_batch(texts)
        except Exception as exc:
            error_msg = f"Batch {start}-{start+len(chunk)}: embedding failed: {str(exc)}"
            errors.append(error_msg)
            logger.error(error_msg)
            continue

        for inc, emb in zip(chunk, embeddings):
            try:
                payload = {
                    "incident_id": str(inc.id),
                    "user_id": inc.user_id,
                    "raw_text": (inc.raw_text or "")[:500],
                    "attack_type": inc.attack_type,
                    "severity": inc.severity,
                    "protocol": inc.protocol,
                    "source_ip": inc.source_ip,
                    "dest_ip": inc.dest_ip,
                    "label": inc.label,
                }
                await vector_store.upsert_incident(
                    incident_id=str(inc.id),
                    embedding=emb,
                    payload=payload,
                )
                inc.embedding_id = str(inc.id)
                indexed += 1
            except Exception as exc:
                errors.append(f"Incident {inc.id}: {str(exc)}")

    await db.commit()

    logger.info("build_index: complete", indexed=indexed, errors=len(errors))

    return {
        "status": "success" if not errors else "partial",
        "indexed": indexed,
        "total": len(incidents),
        "errors": errors[:20],
    }
