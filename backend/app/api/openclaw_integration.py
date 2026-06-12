"""OpenClaw integration router.

Endpoints
---------
POST /api/v1/openclaw/jira      — Create a Jira ticket for an incident
POST /api/v1/openclaw/notify    — Send a webhook notification
POST /api/v1/openclaw/dispatch  — Create ticket + notify in one call
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from pydantic import BaseModel

from backend.app.auth.clerk import get_current_user
from backend.app.services.openclaw_service import OpenClawIncidentAgent

router = APIRouter()


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class CreateJiraTicketRequest(BaseModel):
    summary: str
    description: str
    severity: str = "medium"
    attack_type: Optional[str] = None
    incident_id: Optional[str] = None
    project_key: Optional[str] = None


class NotifyIncidentRequest(BaseModel):
    incident_id: str
    summary: str
    severity: str = "medium"
    threat_class: Optional[str] = None
    escalation_level: Optional[str] = None
    ticket_url: Optional[str] = None


class DispatchRequest(BaseModel):
    """Create a Jira ticket and optionally notify in a single call."""
    summary: str
    description: str
    severity: str = "medium"
    attack_type: Optional[str] = None
    incident_id: Optional[str] = None
    project_key: Optional[str] = None
    escalation_level: Optional[str] = None
    notify: bool = True


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/jira",
    summary="Create Jira ticket for an incident via OpenClaw",
    status_code=status.HTTP_201_CREATED,
)
async def create_jira_ticket(
    request: CreateJiraTicketRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    agent = OpenClawIncidentAgent()
    result = await agent.create_jira_ticket(
        summary=request.summary,
        description=request.description,
        severity=request.severity,
        attack_type=request.attack_type,
        incident_id=request.incident_id,
        project_key=request.project_key,
    )
    if result.get("status") == "error":
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=result.get("detail", "Failed to create Jira ticket"),
        )
    logger.info(
        "openclaw: Jira ticket created",
        user_id=current_user["user_id"],
        ticket_key=result.get("ticket_key"),
    )
    return result


@router.post(
    "/notify",
    summary="Send incident notification via OpenClaw webhook",
    status_code=status.HTTP_200_OK,
)
async def notify_incident(
    request: NotifyIncidentRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    agent = OpenClawIncidentAgent()
    result = await agent.notify_incident(
        incident_id=request.incident_id,
        summary=request.summary,
        severity=request.severity,
        threat_class=request.threat_class,
        escalation_level=request.escalation_level,
        ticket_url=request.ticket_url,
    )
    logger.info(
        "openclaw: notification sent",
        user_id=current_user["user_id"],
        incident_id=request.incident_id,
        status=result.get("status"),
    )
    return result


@router.post(
    "/dispatch",
    summary="Create Jira ticket and send notification (combined)",
    status_code=status.HTTP_201_CREATED,
)
async def dispatch_incident(
    request: DispatchRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    agent = OpenClawIncidentAgent()

    ticket_result = await agent.create_jira_ticket(
        summary=request.summary,
        description=request.description,
        severity=request.severity,
        attack_type=request.attack_type,
        incident_id=request.incident_id,
        project_key=request.project_key,
    )

    notify_result: Dict[str, Any] = {}
    if request.notify:
        notify_result = await agent.notify_incident(
            incident_id=request.incident_id or "N/A",
            summary=request.summary,
            severity=request.severity,
            threat_class=request.attack_type,
            escalation_level=request.escalation_level,
            ticket_url=ticket_result.get("ticket_url"),
        )

    logger.info(
        "openclaw: incident dispatched",
        user_id=current_user["user_id"],
        ticket_key=ticket_result.get("ticket_key"),
        notified=bool(notify_result),
    )
    return {"jira": ticket_result, "notification": notify_result}
