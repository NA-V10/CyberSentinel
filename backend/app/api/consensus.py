"""FastAPI router: Multi-LLM Consensus Engine endpoints."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from backend.app.auth.clerk import get_current_user
from backend.app.core.database import get_db
from backend.app.services.audit_log_service import log_event
from backend.app.services.consensus_service import run_consensus_analysis

router = APIRouter()


class ConsensusRequest(BaseModel):
    incident_text: str = Field(..., min_length=10, max_length=5000)
    incident_id: Optional[str] = None


class ModelOutputItem(BaseModel):
    model: str
    provider: str
    available: bool
    weight: float
    effective_weight: float
    threat_classification: Optional[str] = None
    severity: Optional[str] = None
    mitre_mapping: Optional[str] = None
    risk_score: Optional[int] = None
    recommended_mitigation: Optional[str] = None
    confidence: Optional[int] = None
    reasoning: Optional[str] = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    estimated_cost: float = 0.0


class ConsensusResponse(BaseModel):
    model_outputs: List[Dict[str, Any]] = []
    consensus_classification: Optional[str] = None
    consensus_severity: Optional[str] = None
    consensus_mitre: Optional[str] = None
    consensus_risk_score: Optional[int] = None
    consensus_mitigation: Optional[str] = None
    agreement_score: Optional[float] = None
    disagreement_summary: Optional[str] = None
    final_recommendation: Optional[str] = None
    models_used: List[str] = []
    total_cost: float = 0.0
    weights_used: Dict[str, float] = {}


@router.post(
    "/analyze",
    response_model=ConsensusResponse,
    status_code=status.HTTP_200_OK,
    summary="Run multi-LLM consensus analysis on an incident",
)
async def analyze_consensus(
    request: ConsensusRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db=Depends(get_db),
) -> ConsensusResponse:
    """
    Analyze an incident with multiple LLM models and compute weighted consensus.

    Models (with fallback to mock if key unavailable):
    - OpenAI GPT-4.1 (weight: 0.45)
    - Anthropic Claude-3.5-Sonnet (weight: 0.35)
    - Local Llama-3.1-8B (weight: 0.20)

    Weights are automatically redistributed for unavailable models.

    **Example Response:**
    ```json
    {
      "model_outputs": [
        {"model": "GPT-4.1", "classification": "Brute Force", "confidence": 94},
        {"model": "Claude-3.5-Sonnet", "classification": "Brute Force", "confidence": 91},
        {"model": "Llama-3.1-8B", "classification": "Credential Stuffing", "confidence": 78}
      ],
      "consensus_classification": "Brute Force",
      "agreement_score": 89,
      "disagreement_summary": "Local model classified as credential stuffing...",
      "final_recommendation": "Treat as brute force with credential-stuffing monitoring."
    }
    ```
    """
    user_id = current_user.get("user_id", "unknown")
    org_id = current_user.get("org_id", "default")

    result = await run_consensus_analysis(
        incident_text=request.incident_text,
        org_id=org_id,
        user_id=user_id,
        incident_id=request.incident_id,
    )

    await log_event(
        db=db,
        org_id=org_id,
        user_id=user_id,
        event_type="consensus_analysis_completed",
        resource_type="incident",
        resource_id=request.incident_id,
        details={
            "models_used": result.get("models_used", []),
            "agreement_score": result.get("agreement_score"),
            "consensus_classification": result.get("consensus_classification"),
            "total_cost": result.get("total_cost"),
        },
    )

    return ConsensusResponse(**result)
