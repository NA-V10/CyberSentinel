"""FastAPI router: MITRE ATT&CK mapping endpoints."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.clerk import get_current_user
from backend.app.core.database import get_db
from backend.app.services.mitre_mapping_service import map_attack, persist_mapping
from backend.app.services.audit_log_service import log_action

router = APIRouter()


class MITREMapRequest(BaseModel):
    incident_text: str = ""
    attack_type: str
    incident_id: Optional[str] = None


class MITREMapResponse(BaseModel):
    attack_type: str
    tactic: str
    technique: str
    technique_id: str
    attack_category: str
    confidence: float
    sub_techniques: list
    recommended_mitigation: str
    reasoning: str
    mapping_id: Optional[str] = None


@router.post(
    "/map",
    response_model=MITREMapResponse,
    status_code=status.HTTP_200_OK,
    summary="Map an attack to MITRE ATT&CK framework",
)
async def map_to_mitre(
    request: MITREMapRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MITREMapResponse:
    """Map an attack type and incident description to MITRE ATT&CK tactic/technique."""
    user_id = current_user["user_id"]
    org_id = current_user.get("org_id")

    try:
        mapping = await map_attack(
            attack_type=request.attack_type,
            incident_text=request.incident_text,
            incident_id=request.incident_id,
            org_id=org_id,
        )
    except Exception as exc:
        logger.exception("MITRE mapping failed", error=str(exc))
        raise HTTPException(status_code=500, detail="MITRE mapping failed.") from exc

    mapping_id = await persist_mapping(mapping)

    await log_action(
        user_id=user_id,
        event_type="recommendation_generated",
        resource_type="mitre_mapping",
        resource_id=mapping_id,
        details={"attack_type": request.attack_type, "technique_id": mapping.get("technique_id")},
        org_id=org_id,
    )

    return MITREMapResponse(
        attack_type=mapping["attack_type"],
        tactic=mapping["tactic"],
        technique=mapping["technique"],
        technique_id=mapping["technique_id"],
        attack_category=mapping["attack_category"],
        confidence=mapping["confidence"],
        sub_techniques=mapping.get("sub_techniques", []),
        recommended_mitigation=mapping["recommended_mitigation"],
        reasoning=mapping["reasoning"],
        mapping_id=mapping_id,
    )
