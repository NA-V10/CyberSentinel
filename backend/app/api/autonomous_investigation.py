"""FastAPI router: Autonomous Investigation Mode endpoints."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from backend.app.auth.clerk import get_current_user
from backend.app.core.database import get_db
from backend.app.services.audit_log_service import log_event
from backend.app.services.autonomous_investigation_service import run_autonomous_investigation

router = APIRouter()


class AutonomousInvestigationRequest(BaseModel):
    incident_text: str = Field(..., min_length=10, max_length=5000)
    source_ip: Optional[str] = None
    severity: str = Field(default="high", pattern="^(critical|high|medium|low)$")
    incident_id: Optional[str] = None


class ToolCallRecord(BaseModel):
    sequence: int
    agent_name: Optional[str] = None
    tool_name: str
    input_summary: Optional[str] = None
    output_summary: Optional[str] = None
    status: str
    duration_ms: Optional[int] = None
    timestamp: str


class AutonomousInvestigationResponse(BaseModel):
    investigation_id: str
    incident_id: Optional[str] = None
    tool_calls: List[Dict[str, Any]] = []
    evidence_chain: List[Dict[str, Any]] = []
    timeline: List[Dict[str, Any]] = []
    findings: Dict[str, Any] = {}
    final_summary: Optional[str] = None
    recommended_actions: List[str] = []
    judge_score: Optional[float] = None
    total_tool_calls: int
    duration_seconds: Optional[float] = None
    status: str


@router.post(
    "/autonomous",
    response_model=AutonomousInvestigationResponse,
    status_code=status.HTTP_200_OK,
    summary="Run fully autonomous incident investigation",
)
async def run_autonomous(
    request: AutonomousInvestigationRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db=Depends(get_db),
) -> AutonomousInvestigationResponse:
    """
    Automatically investigate an incident using all available MCP tools and data sources.

    The agent pipeline:
    1. Threat Classification (map_to_mitre_attack)
    2. Threat Intel Lookup (lookup_ip_reputation)
    3. Graph Expansion (query_threat_graph)
    4. Similar Incident Search (search_similar_incidents)
    5. Risk Assessment (calculate_risk_score)
    6. Mitigation Generation (recommend_mitigation)
    7. Policy Check (check_policy_guardrails)
    8. Report Generation (generate_incident_report)
    9. Judge Validation

    **Example Request:**
    ```json
    {
      "incident_text": "Multiple failed SSH login attempts from 45.33.32.156 targeting admin accounts",
      "source_ip": "45.33.32.156",
      "severity": "high",
      "incident_id": "INC-2024-001"
    }
    ```
    """
    user_id = current_user.get("user_id", "unknown")
    org_id = current_user.get("org_id", "default")

    result = await run_autonomous_investigation(
        incident_text=request.incident_text,
        source_ip=request.source_ip,
        severity=request.severity,
        org_id=org_id,
        user_id=user_id,
        incident_id=request.incident_id,
    )

    await log_event(
        db=db,
        org_id=org_id,
        user_id=user_id,
        event_type="autonomous_investigation_completed",
        resource_type="investigation",
        resource_id=result.get("investigation_id"),
        details={
            "incident_id": request.incident_id,
            "total_tool_calls": result.get("total_tool_calls"),
            "judge_score": result.get("judge_score"),
            "duration_seconds": result.get("duration_seconds"),
        },
    )

    return AutonomousInvestigationResponse(**result)
