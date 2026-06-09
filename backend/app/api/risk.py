"""FastAPI router: Risk scoring endpoint."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from backend.app.auth.clerk import get_current_user
from backend.app.services.risk_scoring_service import calculate_risk_score

router = APIRouter()


class RiskScoreRequest(BaseModel):
    severity: str
    attack_type: str
    source_ip: Optional[str] = None
    model_confidence: float = 0.0
    frequency: int = 1
    asset_criticality: str = "medium"
    technique_id: Optional[str] = None
    incident_id: Optional[str] = None


@router.post(
    "/score",
    status_code=status.HTTP_200_OK,
    summary="Calculate explainable risk score for an incident",
)
async def score_risk(
    request: RiskScoreRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Calculate an explainable 0-100 risk score with contributing factors."""
    return await calculate_risk_score(
        severity=request.severity,
        attack_type=request.attack_type,
        source_ip=request.source_ip,
        model_confidence=request.model_confidence,
        frequency=request.frequency,
        asset_criticality=request.asset_criticality,
        technique_id=request.technique_id,
    )
