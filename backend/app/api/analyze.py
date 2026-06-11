"""FastAPI router: POST /analyze-incident

Runs the full LangGraph multi-agent workflow and returns a structured
incident analysis response.
"""

from __future__ import annotations

import json
import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger

from backend.app.agents.workflow import build_initial_state, create_workflow
from backend.app.auth.clerk import get_current_user
from backend.app.core.logging import logger as app_logger
from backend.app.schemas.incident import (
    AnalyzeIncidentRequest,
    AnalyzeIncidentResponse,
    SimilarIncident,
)

router = APIRouter()

# Compile the LangGraph graph once at module level (thread-safe after compilation)
_workflow = create_workflow()


@router.post(
    "/analyze-incident",
    response_model=AnalyzeIncidentResponse,
    summary="Run full AI incident analysis",
    status_code=status.HTTP_200_OK,
)
async def analyze_incident(
    request: AnalyzeIncidentRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> AnalyzeIncidentResponse:
    """Run the CyberSentinel AI multi-agent workflow on the submitted incident.

    **Authentication**: Bearer JWT (Clerk).

    **Request body**: ``AnalyzeIncidentRequest``

    **Response**: ``AnalyzeIncidentResponse``
    """
    user_id: str = current_user["user_id"]
    app_logger.info(
        "analyze_incident: request received",
        user_id=user_id,
        text_len=len(request.incident_text),
    )

    # Build initial workflow state
    initial_state = build_initial_state(
        incident_text=request.incident_text,
        user_id=user_id,
        session_id=request.session_id,
        source_ip=request.source_ip,
        dest_ip=request.dest_ip,
        protocol=request.protocol,
        severity=request.severity,
        ws_callback=None,  # HTTP path — no WebSocket available here
    )

    try:
        final_state = await _workflow.ainvoke(initial_state)
    except Exception as exc:
        app_logger.exception("analyze_incident: workflow error", exc_info=exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The analysis workflow encountered an unexpected error.",
        ) from exc

    # -----------------------------------------------------------------------
    # Validation failure → 422
    # -----------------------------------------------------------------------
    if not final_state.get("is_valid", True):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=final_state.get("validation_error") or "Input validation failed.",
        )

    # -----------------------------------------------------------------------
    # Build response
    # -----------------------------------------------------------------------
    threat_class: str = final_state.get("threat_class") or "unknown"
    threat_confidence: float = float(final_state.get("threat_confidence") or 0.0)
    similar_raw = final_state.get("similar_incidents") or []
    mitigation: dict = final_state.get("mitigation") or {}
    escalation_level: str = final_state.get("escalation_level") or "L1"
    explanation: str = final_state.get("explanation") or ""
    judge_score: float = float(final_state.get("judge_score") or 0.0)
    graph_context: dict = final_state.get("graph_context") or {}
    session_id: str = final_state.get("session_id") or str(uuid.uuid4())

    similar_incidents = [
        SimilarIncident(
            id=str(inc.get("id", "")),
            score=float(inc.get("score", 0.0)),
            attack_type=inc.get("attack_type"),
            severity=inc.get("severity"),
            summary=inc.get("summary"),
        )
        for inc in similar_raw
    ]

    app_logger.info(
        "analyze_incident: complete",
        user_id=user_id,
        threat_class=threat_class,
        judge_score=judge_score,
        escalation=escalation_level,
    )

    return AnalyzeIncidentResponse(
        threat_class=threat_class,
        severity_score=round(threat_confidence, 4),
        similar_incidents=similar_incidents,
        mitigation=mitigation,
        escalation_level=escalation_level,
        explanation=explanation,
        judge_score=round(judge_score, 4),
        graph_data=graph_context,
        incident_id=None,   # populated by feedback agent asynchronously
        conversation_id=None,
        session_id=session_id,
    )
