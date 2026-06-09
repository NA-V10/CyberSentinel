"""
CyberSentinel AI — Application Startup Orchestrator

Runs all one-time initialisation tasks that must complete before the first
request is served:

1. Database migrations — create all SQLAlchemy tables when absent.
2. Qdrant collection — create the vector collection if it does not exist.
3. ML model bootstrap — train and persist the threat classifier if no model
   file is found on disk.
4. Sample data seed — ingest the bundled CSV into Postgres / Qdrant / Neo4j
   when the incidents table is empty (development / first-boot only).

Call :func:`run_startup` from ``main.py``'s lifespan context manager::

    from backend.app.core.startup import run_startup

    @asynccontextmanager
    async def lifespan(app):
        await run_startup()
        yield
        ...
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict

from loguru import logger

from backend.app.core.config import settings
from backend.app.core.database import AsyncSessionLocal, init_db


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


async def run_startup() -> Dict[str, Any]:
    """Execute all startup tasks in order.

    Each step is wrapped in its own try/except so that a non-fatal failure
    (e.g. Neo4j unreachable) does not prevent the rest of the application
    from starting.

    Returns
    -------
    dict
        A summary of what happened during startup, keyed by task name.
    """
    t_total = time.monotonic()
    results: Dict[str, Any] = {}

    logger.info("=" * 60)
    logger.info("CyberSentinel AI — startup sequence starting")
    logger.info("=" * 60)

    # 1. Database tables
    results["db_init"] = await _step_db_init()

    # 2. Qdrant collection
    results["qdrant_init"] = await _step_qdrant_init()

    # 3. ML model bootstrap
    results["ml_model"] = await _step_ml_model()

    # 4. Sample data seed (dev / first-boot only)
    results["sample_data"] = await _step_seed_data()

    elapsed = time.monotonic() - t_total
    logger.info(
        "Startup sequence complete",
        elapsed_seconds=f"{elapsed:.2f}",
        results=results,
    )
    logger.info("=" * 60)
    return results


# ---------------------------------------------------------------------------
# Step 1 — Database / ORM table creation
# ---------------------------------------------------------------------------


async def _step_db_init() -> Dict[str, Any]:
    """Create all SQLAlchemy ORM tables (idempotent)."""
    step = "db_init"
    t0 = time.monotonic()
    logger.info(f"[{step}] Initialising relational database tables …")

    try:
        await init_db()
        elapsed = time.monotonic() - t0
        logger.info(f"[{step}] Database tables ready", elapsed_seconds=f"{elapsed:.2f}")
        return {"status": "ok", "elapsed": elapsed}
    except Exception as exc:
        elapsed = time.monotonic() - t0
        logger.error(f"[{step}] Database initialisation failed", error=str(exc))
        return {"status": "error", "error": str(exc), "elapsed": elapsed}


# ---------------------------------------------------------------------------
# Step 2 — Qdrant vector collection
# ---------------------------------------------------------------------------


async def _step_qdrant_init() -> Dict[str, Any]:
    """Ensure the Qdrant collection exists with the correct schema."""
    step = "qdrant_init"
    t0 = time.monotonic()
    logger.info(f"[{step}] Initialising Qdrant collection '{settings.QDRANT_COLLECTION}' …")

    try:
        from backend.app.rag.vector_store import VectorStoreService

        svc = VectorStoreService()
        await svc.initialize_collection()
        await svc.close()

        elapsed = time.monotonic() - t0
        logger.info(
            f"[{step}] Qdrant collection ready",
            collection=settings.QDRANT_COLLECTION,
            elapsed_seconds=f"{elapsed:.2f}",
        )
        return {"status": "ok", "collection": settings.QDRANT_COLLECTION, "elapsed": elapsed}
    except Exception as exc:
        elapsed = time.monotonic() - t0
        logger.warning(
            f"[{step}] Qdrant initialisation failed — RAG will be unavailable",
            error=str(exc),
        )
        return {"status": "error", "error": str(exc), "elapsed": elapsed}


# ---------------------------------------------------------------------------
# Step 3 — ML threat classifier model
# ---------------------------------------------------------------------------


async def _step_ml_model() -> Dict[str, Any]:
    """Train and save the ML threat classifier if the model file is absent."""
    import asyncio

    step = "ml_model"
    t0 = time.monotonic()
    model_path = Path(settings.ML_MODEL_PATH)

    if model_path.exists():
        logger.info(
            f"[{step}] ML model already exists — skipping training",
            path=str(model_path),
        )
        elapsed = time.monotonic() - t0
        return {"status": "skipped", "path": str(model_path), "elapsed": elapsed}

    logger.info(
        f"[{step}] ML model not found — training from scratch …",
        target_path=str(model_path),
    )

    try:
        from backend.app.ml.trainer import run_training

        # run_training is CPU-bound; run it in a thread pool to avoid blocking
        # the asyncio event loop during startup.
        loop = asyncio.get_event_loop()
        metrics: Dict[str, Any] = await loop.run_in_executor(
            None,  # default ThreadPoolExecutor
            lambda: run_training(model_path=str(model_path)),
        )

        elapsed = time.monotonic() - t0
        logger.info(
            f"[{step}] ML model trained and saved",
            accuracy=f"{metrics.get('accuracy', 0):.4f}",
            n_samples=metrics.get("n_samples"),
            n_classes=metrics.get("n_classes"),
            path=metrics.get("model_path"),
            elapsed_seconds=f"{elapsed:.2f}",
        )
        return {
            "status": "trained",
            "accuracy": metrics.get("accuracy"),
            "path": metrics.get("model_path"),
            "elapsed": elapsed,
        }
    except Exception as exc:
        elapsed = time.monotonic() - t0
        logger.warning(
            f"[{step}] ML model training failed — predictions will be unavailable",
            error=str(exc),
        )
        return {"status": "error", "error": str(exc), "elapsed": elapsed}


# ---------------------------------------------------------------------------
# Step 4 — Sample data seed
# ---------------------------------------------------------------------------


async def _step_seed_data() -> Dict[str, Any]:
    """Seed the database with sample incidents if the table is empty.

    This step only runs when:
    - ``settings.DEBUG`` is ``True``, OR the env var ``SEED_DATA=true`` is set.
    - The ``incidents`` table is completely empty.

    A non-critical step: failures are logged as warnings, not errors.
    """
    import os

    step = "sample_data"
    t0 = time.monotonic()

    # Only seed in debug mode or when explicitly requested
    should_seed = settings.DEBUG or os.getenv("SEED_DATA", "false").lower() == "true"
    if not should_seed:
        logger.info(f"[{step}] Skipping sample data seed (DEBUG=false, SEED_DATA not set)")
        elapsed = time.monotonic() - t0
        return {"status": "skipped", "reason": "not_debug", "elapsed": elapsed}

    logger.info(f"[{step}] Checking whether incidents table is empty …")

    try:
        from sqlalchemy import func, select

        from backend.app.models.incident import Incident

        async with AsyncSessionLocal() as session:
            count_result = await session.execute(select(func.count()).select_from(Incident))
            incident_count: int = count_result.scalar_one()

        if incident_count > 0:
            elapsed = time.monotonic() - t0
            logger.info(
                f"[{step}] Incidents table already has data — skipping seed",
                incident_count=incident_count,
            )
            return {
                "status": "skipped",
                "reason": "already_populated",
                "incident_count": incident_count,
                "elapsed": elapsed,
            }

        logger.info(f"[{step}] Incidents table is empty — loading sample data …")

        # Locate the sample CSV (ships with the repo under data/sample/)
        sample_csv = (
            Path(__file__).resolve().parents[4] / "data" / "sample" / "sample_incidents.csv"
        )

        if not sample_csv.exists():
            logger.info(
                f"[{step}] Sample CSV not found — generating synthetic dataset …",
                searched_path=str(sample_csv),
            )
            result = await _seed_from_synthetic()
        else:
            logger.info(f"[{step}] Seeding from CSV", path=str(sample_csv))
            result = await _seed_from_csv(str(sample_csv))

        elapsed = time.monotonic() - t0
        logger.info(
            f"[{step}] Sample data seed complete",
            elapsed_seconds=f"{elapsed:.2f}",
            **result,
        )
        return {"status": "seeded", "elapsed": elapsed, **result}

    except Exception as exc:
        elapsed = time.monotonic() - t0
        logger.warning(
            f"[{step}] Sample data seed failed (non-fatal)",
            error=str(exc),
        )
        return {"status": "error", "error": str(exc), "elapsed": elapsed}


async def _seed_from_csv(csv_path: str) -> Dict[str, Any]:
    """Ingest the sample CSV using the existing ingest service."""
    from backend.app.services.ingest_service import clean_dataframe, ingest_dataframe

    import pandas as pd

    df = pd.read_csv(csv_path)
    df = clean_dataframe(df)

    result = await ingest_dataframe(df, user_id="system_seed")
    logger.info(
        "CSV seed complete",
        total=result["total"],
        success=result["success"],
        failed=result["failed"],
    )
    return result


async def _seed_from_synthetic() -> Dict[str, Any]:
    """Generate a synthetic dataset and ingest it."""
    import asyncio

    from backend.app.ml.trainer import _generate_synthetic_dataset
    from backend.app.services.ingest_service import clean_dataframe, ingest_dataframe

    # Generate 200 samples for a quick first-boot experience
    loop = asyncio.get_event_loop()
    df = await loop.run_in_executor(
        None,
        lambda: _generate_synthetic_dataset(n_samples=200),
    )

    # synthetic dataset already has well-formed columns, but run through
    # clean_dataframe to add raw_text and ensure consistency
    #
    # The synthetic generator does not include source_ip/dest_ip so we add
    # plausible stub values so the clean step does not drop all rows.
    import numpy as np

    rng = np.random.default_rng(42)
    n = len(df)
    df["source_ip"] = [f"10.0.{rng.integers(0, 255)}.{rng.integers(1, 254)}" for _ in range(n)]
    df["dest_ip"] = [f"192.168.{rng.integers(0, 10)}.{rng.integers(1, 254)}" for _ in range(n)]
    df["protocol"] = df.get("protocol_encoded", 0).map(
        {0: "TCP", 1: "UDP", 2: "ICMP", 3: "HTTP", 4: "HTTPS", 5: "DNS", 6: "SSH", 7: "FTP"}
    ).fillna("TCP")

    df = clean_dataframe(df)
    result = await ingest_dataframe(df, user_id="system_seed")
    logger.info(
        "Synthetic seed complete",
        total=result["total"],
        success=result["success"],
        failed=result["failed"],
    )
    return result
