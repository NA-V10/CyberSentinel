"""FastAPI router: Playbook generator endpoint."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from backend.app.auth.clerk import get_current_user
from backend.app.services.playbook_service import generate_playbook
from backend.app.services.audit_log_service import log_action

router = APIRouter()


class PlaybookRequest(BaseModel):
    attack_type: str
    severity: str
    incident_text: str = ""
    source_ip: Optional[str] = None


@router.post(
    "/generate",
    status_code=status.HTTP_200_OK,
    summary="Generate an incident response playbook",
)
async def generate_incident_playbook(
    request: PlaybookRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Generate a structured incident response playbook for the given attack type and severity."""
    playbook = await generate_playbook(
        attack_type=request.attack_type,
        severity=request.severity,
        incident_text=request.incident_text,
        source_ip=request.source_ip,
    )
    await log_action(
        user_id=current_user["user_id"],
        event_type="recommendation_generated",
        resource_type="playbook",
        details={"attack_type": request.attack_type, "severity": request.severity},
        org_id=current_user.get("org_id"),
    )
    return playbook
