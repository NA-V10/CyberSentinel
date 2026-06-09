"""FastAPI router: SLA tracking endpoints."""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from backend.app.auth.clerk import get_current_user
from backend.app.services.sla_service import assign_sla, get_sla_status, resolve_sla

router = APIRouter()


class SLAAssignRequest(BaseModel):
    incident_id: str
    severity: str


@router.post(
    "/assign",
    status_code=status.HTTP_201_CREATED,
    summary="Assign SLA tracker to an incident",
)
async def assign_sla_tracker(
    request: SLAAssignRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Assign SLA deadlines and analyst level based on incident severity."""
    return await assign_sla(
        incident_id=request.incident_id,
        severity=request.severity,
        org_id=current_user.get("org_id"),
    )


@router.get(
    "/{incident_id}",
    status_code=status.HTTP_200_OK,
    summary="Get SLA status for an incident",
)
async def get_sla(
    incident_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get current SLA status including time remaining and breach status."""
    return await get_sla_status(incident_id=incident_id)


@router.post(
    "/{incident_id}/resolve",
    status_code=status.HTTP_200_OK,
    summary="Mark SLA as resolved",
)
async def resolve_sla_tracker(
    incident_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Mark the incident's SLA as resolved."""
    return await resolve_sla(incident_id=incident_id)
