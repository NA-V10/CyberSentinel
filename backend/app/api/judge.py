"""FastAPI router: LLM-as-Judge evaluation endpoint."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from backend.app.auth.clerk import get_current_user
from backend.app.services.llm_judge_service import evaluate

router = APIRouter()


class JudgeRequest(BaseModel):
    incident_text: str
    recommendation: Any
    context: Optional[Dict[str, Any]] = None


class JudgeResponse(BaseModel):
    correctness: int
    safety: int
    completeness: int
    hallucination_risk: str
    actionability: int
    evidence_alignment: int
    overall_score: int
    judge_reasoning: str
    passed: bool


@router.post(
    "/evaluate",
    response_model=JudgeResponse,
    status_code=status.HTTP_200_OK,
    summary="Evaluate an incident analysis with the LLM judge",
)
async def evaluate_response(
    request: JudgeRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> JudgeResponse:
    """Run the LLM-as-Judge to score the quality of an incident analysis recommendation."""
    scores = await evaluate(
        incident_text=request.incident_text,
        recommendation=request.recommendation,
        context=request.context,
    )
    return JudgeResponse(**scores)
