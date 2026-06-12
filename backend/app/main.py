"""CyberSentinel AI — FastAPI application entry point."""

from __future__ import annotations

import time
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from backend.app.core.config import settings
from backend.app.core.database import close_db, init_db
from backend.app.core.logging import logger
from backend.app.core.redis_client import close_redis, get_redis
from backend.app.core.startup import run_startup


# ---------------------------------------------------------------------------
# Lifespan (startup / shutdown)
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:  # noqa: ARG001
    """Manage application-level resources across the full process lifetime."""
    # ---- startup ----
    logger.info("Starting up CyberSentinel AI", version=app.version)
    t0 = time.monotonic()

    # Run the full startup sequence:
    #   - DB table creation
    #   - Qdrant collection bootstrap
    #   - ML model training (if missing)
    #   - Sample data seed (debug / first-boot)
    await run_startup()

    # Warm the Redis connection so the first request does not bear the cost
    try:
        redis = await get_redis()
        await redis.ping()
        logger.info("Redis connection established")
    except Exception as exc:  # pragma: no cover
        logger.warning("Redis unavailable at startup — cache will be skipped", error=str(exc))

    elapsed = time.monotonic() - t0
    logger.info(f"Startup complete in {elapsed:.2f}s")

    yield  # application runs here

    # ---- shutdown ----
    logger.info("Shutting down CyberSentinel AI")
    await close_db()
    await close_redis()
    logger.info("Shutdown complete")


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

def create_app() -> FastAPI:
    """Construct and configure the FastAPI application."""

    app = FastAPI(
        title=settings.APP_NAME,
        version="1.0.0",
        description=(
            "CyberSentinel AI is an agentic cybersecurity incident-response platform. "
            "It combines machine-learning threat classification, retrieval-augmented generation, "
            "a knowledge graph, and LLM-driven playbook generation to help security analysts "
            "triage and respond to incidents faster."
        ),
        docs_url=f"{settings.API_V1_STR}/docs",
        redoc_url=f"{settings.API_V1_STR}/redoc",
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        lifespan=lifespan,
    )

    # ------------------------------------------------------------------
    # Middleware
    # ------------------------------------------------------------------

    # CORS — regex matches any localhost/127.0.0.1 port; production domains listed explicitly.
    # Using allow_origin_regex avoids Starlette exact-match quirks with allow_credentials=True.
    _origin_regex = r"http://(localhost|127\.0\.0\.1)(:\d+)?"
    _explicit_origins = ["https://cybersentinel.ai", "https://app.cybersentinel.ai"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_explicit_origins,
        allow_origin_regex=_origin_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ------------------------------------------------------------------
    # Exception handlers
    # ------------------------------------------------------------------

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        logger.warning(
            "Request validation error",
            path=str(request.url),
            errors=exc.errors(),
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": "Request validation failed.",
                "errors": exc.errors(),
            },
        )

    @app.exception_handler(ValidationError)
    async def pydantic_validation_handler(
        request: Request, exc: ValidationError
    ) -> JSONResponse:
        logger.warning("Pydantic validation error", path=str(request.url))
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": "Data validation failed.", "errors": exc.errors()},
        )

    @app.exception_handler(status.HTTP_401_UNAUTHORIZED)
    async def auth_error_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Authentication required."},
            headers={"WWW-Authenticate": "Bearer"},
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.exception("Unhandled exception", path=str(request.url), exc_info=exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "An unexpected error occurred. Please try again later."},
        )

    # ------------------------------------------------------------------
    # Routers
    # ------------------------------------------------------------------

    _register_routers(app)

    # ------------------------------------------------------------------
    # Utility endpoints
    # ------------------------------------------------------------------

    @app.get(
        "/health",
        tags=["system"],
        summary="Health check",
        response_model=Dict[str, Any],
    )
    async def health_check() -> Dict[str, Any]:
        """Return a simple liveness probe used by load balancers and orchestrators."""
        return {
            "status": "ok",
            "app": settings.APP_NAME,
            "version": app.version,
            "debug": settings.DEBUG,
        }

    return app


def _register_routers(app: FastAPI) -> None:
    """Import and mount all API routers.

    Each router module is imported inside this function so that import errors
    surface clearly at startup rather than at first request.
    """
    prefix = settings.API_V1_STR

    try:
        from backend.app.api.ingest import router as ingest_router
        app.include_router(ingest_router, prefix=f"{prefix}/ingest", tags=["ingest"])
    except ImportError:
        logger.warning("Ingest router not found — skipping")

    try:
        from backend.app.api.analyze import router as analyze_router
        app.include_router(analyze_router, prefix=f"{prefix}/analyze", tags=["analyze"])
    except ImportError:
        logger.warning("Analyze router not found — skipping")

    try:
        from backend.app.api.search import router as search_router
        app.include_router(search_router, prefix=f"{prefix}/search", tags=["search"])
    except ImportError:
        logger.warning("Search router not found — skipping")

    try:
        from backend.app.api.predict import router as predict_router
        app.include_router(predict_router, prefix=f"{prefix}/predict-threat", tags=["ML Prediction"])
    except ImportError:
        logger.warning("Predict router not found — skipping")

    try:
        from backend.app.api.feedback import router as feedback_router
        app.include_router(feedback_router, prefix=f"{prefix}/feedback", tags=["feedback"])
    except ImportError:
        logger.warning("Feedback router not found — skipping")

    try:
        from backend.app.api.memory import router as memory_router
        app.include_router(memory_router, prefix=f"{prefix}/memory", tags=["memory"])
    except ImportError:
        logger.warning("Memory router not found — skipping")

    try:
        from backend.app.api.graph import router as graph_router
        app.include_router(graph_router, prefix=f"{prefix}/graph", tags=["graph"])
    except ImportError:
        logger.warning("Graph router not found — skipping")

    try:
        from backend.app.api.ws import router as ws_router
        app.include_router(ws_router, prefix=f"{prefix}/ws", tags=["websocket"])
    except ImportError:
        try:
            from backend.app.api.websocket_router import router as ws_router
            app.include_router(ws_router, prefix=f"{prefix}/ws", tags=["websocket"])
        except ImportError:
            logger.warning("WebSocket router not found — skipping")

    # ------------------------------------------------------------------
    # Feature set v2 — Advanced Differentiators
    # ------------------------------------------------------------------

    try:
        from backend.app.api.mitre import router as mitre_router
        app.include_router(mitre_router, prefix=f"{prefix}/mitre", tags=["MITRE ATT&CK"])
    except ImportError:
        logger.warning("MITRE router not found — skipping")

    try:
        from backend.app.api.approval import router as approval_router
        app.include_router(approval_router, prefix=f"{prefix}/approval", tags=["approval"])
    except ImportError:
        logger.warning("Approval router not found — skipping")

    try:
        from backend.app.api.judge import router as judge_router
        app.include_router(judge_router, prefix=f"{prefix}/judge", tags=["LLM Judge"])
    except ImportError:
        logger.warning("Judge router not found — skipping")

    try:
        from backend.app.api.executive_dashboard import router as exec_dash_router
        app.include_router(exec_dash_router, prefix=f"{prefix}/dashboard", tags=["dashboard"])
    except ImportError:
        logger.warning("Executive dashboard router not found — skipping")

    try:
        from backend.app.api.threat_intel import router as threat_intel_router
        app.include_router(threat_intel_router, prefix=f"{prefix}/threat-intel", tags=["threat-intel"])
    except ImportError:
        logger.warning("Threat intel router not found — skipping")

    try:
        from backend.app.api.risk import router as risk_router
        app.include_router(risk_router, prefix=f"{prefix}/risk", tags=["risk"])
    except ImportError:
        logger.warning("Risk router not found — skipping")

    try:
        from backend.app.api.playbook import router as playbook_router
        app.include_router(playbook_router, prefix=f"{prefix}/playbook", tags=["playbook"])
    except ImportError:
        logger.warning("Playbook router not found — skipping")

    try:
        from backend.app.api.simulation import router as simulation_router
        app.include_router(simulation_router, prefix=f"{prefix}/simulation", tags=["simulation"])
    except ImportError:
        logger.warning("Simulation router not found — skipping")

    try:
        from backend.app.api.sla import router as sla_router
        app.include_router(sla_router, prefix=f"{prefix}/sla", tags=["SLA"])
    except ImportError:
        logger.warning("SLA router not found — skipping")

    try:
        from backend.app.api.audit_logs import router as audit_logs_router
        app.include_router(audit_logs_router, prefix=f"{prefix}/audit-logs", tags=["audit"])
    except ImportError:
        logger.warning("Audit logs router not found — skipping")

    try:
        from backend.app.api.mcp_tools import router as mcp_tools_router
        app.include_router(mcp_tools_router, prefix=f"{prefix}/mcp", tags=["MCP"])
    except ImportError:
        logger.warning("MCP tools router not found — skipping")

    try:
        from backend.app.api.war_room_ws import router as war_room_ws_router
        app.include_router(war_room_ws_router, prefix=f"{prefix}/ws", tags=["war-room-ws"])
    except ImportError:
        logger.warning("War room WebSocket router not found — skipping")

    # ------------------------------------------------------------------
    # Final Premium Feature Set — v3
    # ------------------------------------------------------------------

    try:
        from backend.app.api.reflection import router as reflection_router
        app.include_router(reflection_router, prefix=f"{prefix}/reflection", tags=["Self-Reflection"])
    except ImportError:
        logger.warning("Self-Reflection router not found — skipping")

    try:
        from backend.app.api.campaigns import router as campaigns_router
        app.include_router(campaigns_router, prefix=f"{prefix}/campaigns", tags=["Campaigns"])
    except ImportError:
        logger.warning("Campaigns router not found — skipping")

    try:
        from backend.app.api.autonomous_investigation import router as auto_inv_router
        app.include_router(auto_inv_router, prefix=f"{prefix}/investigation", tags=["Autonomous Investigation"])
    except ImportError:
        logger.warning("Autonomous Investigation router not found — skipping")

    try:
        from backend.app.api.consensus import router as consensus_router
        app.include_router(consensus_router, prefix=f"{prefix}/consensus", tags=["Consensus Engine"])
    except ImportError:
        logger.warning("Consensus router not found — skipping")

    try:
        from backend.app.api.digital_twin import router as digital_twin_router
        app.include_router(digital_twin_router, prefix=f"{prefix}/digital-twin", tags=["Digital Twin"])
    except ImportError:
        logger.warning("Digital Twin router not found — skipping")

    try:
        from backend.app.api.cost_intelligence import router as cost_router
        app.include_router(cost_router, prefix=f"{prefix}/cost", tags=["Cost Intelligence"])
    except ImportError:
        logger.warning("Cost Intelligence router not found — skipping")

    # ------------------------------------------------------------------
    # OpenClaw Integration — Jira + Notifications
    # ------------------------------------------------------------------

    try:
        from backend.app.api.openclaw_integration import router as openclaw_router
        app.include_router(openclaw_router, prefix=f"{prefix}/openclaw", tags=["OpenClaw"])
    except ImportError:
        logger.warning("OpenClaw integration router not found — skipping")


# ---------------------------------------------------------------------------
# Application instance (used by uvicorn and tests)
# ---------------------------------------------------------------------------

app = create_app()
