"""FastAPI router: Agent Self-Reflection Engine endpoints."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from backend.app.auth.clerk import get_current_user
from backend.app.core.database import get_db
from backend.app.services.audit_log_service import log_event
from backend.app.services.self_reflection_service import run_self_reflection

router = APIRouter()


class ReflectionRequest(BaseModel):
    incident_text: str = Field(..., min_length=10, max_length=5000)
    initial_analysis: Dict[str, Any]
    judge_score: float = Field(default=8.0, ge=0.0, le=10.0)
    incident_id: Optional[str] = None


class BeforeAfterComparison(BaseModel):
    initial_classification: Optional[str] = None
    improved_classification: Optional[str] = None
    initial_confidence: Optional[float] = None
    improved_confidence: Optional[float] = None
    key_improvements: List[str] = []
    confidence_delta: Optional[float] = None


class ReflectionResponse(BaseModel):
    initial_analysis: Optional[str] = None
    judge_score: float
    weaknesses_detected: List[str] = []
    missing_evidence: List[str] = []
    low_confidence_areas: List[str] = []
    additional_retrieval_required: bool
    improvement_suggestions: List[str] = []
    improved_analysis: Optional[str] = None
    before_after_comparison: Optional[Dict[str, Any]] = None
    final_confidence: float
    reflection_triggered: bool


@router.post(
    "/analyze",
    response_model=ReflectionResponse,
    status_code=status.HTTP_200_OK,
    summary="Run agent self-reflection on an incident analysis",
)
async def analyze_with_reflection(
    request: ReflectionRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db=Depends(get_db),
) -> ReflectionResponse:
    """
    Run the self-reflection loop on an initial AI analysis.

    Detects weak reasoning, missing evidence, and low-confidence areas.
    If judge score is below threshold, triggers re-analysis and returns
    an improved version with before/after comparison.

    **Example Request:**
    ```json
    {
      "incident_text": "SSH brute force attack detected from 45.33.32.156 targeting 192.168.1.10",
      "initial_analysis": {
        "threat_class": "Brute Force",
        "threat_confidence": 0.72,
        "mitigation": "Block source IP"
      },
      "judge_score": 6.5,
      "incident_id": "INC-2024-001"
    }
    ```
    """
    user_id = current_user.get("user_id", "unknown")
    org_id = current_user.get("org_id", "default")

    result = await run_self_reflection(
        incident_text=request.incident_text,
        initial_analysis=request.initial_analysis,
        judge_score=request.judge_score,
        org_id=org_id,
        user_id=user_id,
        incident_id=request.incident_id,
    )

    await log_event(
        db=db,
        org_id=org_id,
        user_id=user_id,
        event_type="self_reflection_analyzed",
        resource_type="incident",
        resource_id=request.incident_id,
        details={
            "judge_score": request.judge_score,
            "reflection_triggered": result.get("reflection_triggered"),
            "final_confidence": result.get("final_confidence"),
        },
    )

    return ReflectionResponse(**result)
