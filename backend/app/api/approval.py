"""FastAPI router: Human-in-the-loop approval endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.clerk import get_current_user
from backend.app.core.database import get_db
from backend.app.models.incident import IncidentApproval
from backend.app.services.audit_log_service import log_action

router = APIRouter()


class ApprovalActionRequest(BaseModel):
    reason: Optional[str] = None
    edited_response: Optional[str] = None
    escalate_to: Optional[str] = None


class ApprovalResponse(BaseModel):
    id: str
    incident_id: str
    approval_status: str
    approved_by: Optional[str]
    reason: Optional[str]
    edited_response: Optional[str]
    escalated_to: Optional[str]
    created_at: str
    updated_at: str


def _to_response(record: IncidentApproval) -> ApprovalResponse:
    return ApprovalResponse(
        id=str(record.id),
        incident_id=str(record.incident_id),
        approval_status=record.approval_status,
        approved_by=record.approved_by,
        reason=record.reason,
        edited_response=record.edited_response,
        escalated_to=record.escalated_to,
        created_at=record.created_at.isoformat(),
        updated_at=record.updated_at.isoformat(),
    )


async def _get_or_create_approval(
    incident_id: str, db: AsyncSession, user_id: str, org_id: Optional[str]
) -> IncidentApproval:
    """Get existing or create new approval record."""
    try:
        inc_uuid = uuid.UUID(incident_id)
    except ValueError as e:
        raise HTTPException(status_code=422, detail="Invalid incident_id UUID") from e

    result = await db.execute(
        select(IncidentApproval).where(IncidentApproval.incident_id == inc_uuid)
    )
    record = result.scalar_one_or_none()
    if not record:
        record = IncidentApproval(
            incident_id=inc_uuid,
            org_id=org_id,
            approval_status="pending",
        )
        db.add(record)
        await db.flush()
    return record


@router.get("/{incident_id}", response_model=ApprovalResponse)
async def get_approval(
    incident_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApprovalResponse:
    """Get approval status for an incident."""
    org_id = current_user.get("org_id")
    record = await _get_or_create_approval(incident_id, db, current_user["user_id"], org_id)
    await db.commit()
    await db.refresh(record)
    return _to_response(record)


@router.post("/{incident_id}/approve", response_model=ApprovalResponse)
async def approve_incident(
    incident_id: str,
    payload: ApprovalActionRequest = ApprovalActionRequest(),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApprovalResponse:
    """Approve the AI-generated mitigation recommendation."""
    user_id = current_user["user_id"]
    org_id = current_user.get("org_id")
    record = await _get_or_create_approval(incident_id, db, user_id, org_id)
    record.approval_status = "approved"
    record.approved_by = user_id
    record.reason = payload.reason
    await db.commit()
    await db.refresh(record)
    await log_action(user_id=user_id, event_type="mitigation_approved", resource_type="incident",
                     resource_id=incident_id, details={"reason": payload.reason}, org_id=org_id)
    return _to_response(record)


@router.post("/{incident_id}/reject", response_model=ApprovalResponse)
async def reject_incident(
    incident_id: str,
    payload: ApprovalActionRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApprovalResponse:
    """Reject the AI-generated mitigation recommendation."""
    user_id = current_user["user_id"]
    org_id = current_user.get("org_id")
    record = await _get_or_create_approval(incident_id, db, user_id, org_id)
    record.approval_status = "rejected"
    record.approved_by = user_id
    record.reason = payload.reason
    await db.commit()
    await db.refresh(record)
    await log_action(user_id=user_id, event_type="mitigation_rejected", resource_type="incident",
                     resource_id=incident_id, details={"reason": payload.reason}, org_id=org_id)
    return _to_response(record)


@router.post("/{incident_id}/edit", response_model=ApprovalResponse)
async def edit_approval(
    incident_id: str,
    payload: ApprovalActionRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApprovalResponse:
    """Edit the mitigation and approve the edited version."""
    user_id = current_user["user_id"]
    org_id = current_user.get("org_id")
    record = await _get_or_create_approval(incident_id, db, user_id, org_id)
    record.approval_status = "edited_approved"
    record.approved_by = user_id
    record.edited_response = payload.edited_response
    record.reason = payload.reason
    await db.commit()
    await db.refresh(record)
    await log_action(user_id=user_id, event_type="mitigation_edited", resource_type="incident",
                     resource_id=incident_id, org_id=org_id)
    return _to_response(record)


@router.post("/{incident_id}/regenerate", response_model=ApprovalResponse)
async def regenerate_incident(
    incident_id: str,
    payload: ApprovalActionRequest = ApprovalActionRequest(),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApprovalResponse:
    """Request regeneration of the AI analysis."""
    user_id = current_user["user_id"]
    org_id = current_user.get("org_id")
    record = await _get_or_create_approval(incident_id, db, user_id, org_id)
    record.approval_status = "regeneration_requested"
    record.approved_by = user_id
    record.reason = payload.reason or "Analyst requested regeneration"
    await db.commit()
    await db.refresh(record)
    await log_action(user_id=user_id, event_type="recommendation_generated", resource_type="incident",
                     resource_id=incident_id, details={"action": "regenerate"}, org_id=org_id)
    return _to_response(record)


@router.post("/{incident_id}/escalate", response_model=ApprovalResponse)
async def escalate_incident(
    incident_id: str,
    payload: ApprovalActionRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApprovalResponse:
    """Escalate the incident to a higher-level analyst or manager."""
    user_id = current_user["user_id"]
    org_id = current_user.get("org_id")
    record = await _get_or_create_approval(incident_id, db, user_id, org_id)
    record.approval_status = "escalated"
    record.approved_by = user_id
    record.escalated_to = payload.escalate_to or "SOC Manager"
    record.reason = payload.reason
    await db.commit()
    await db.refresh(record)
    await log_action(user_id=user_id, event_type="incident_escalated", resource_type="incident",
                     resource_id=incident_id,
                     details={"escalated_to": record.escalated_to, "reason": payload.reason},
                     org_id=org_id)
    return _to_response(record)
