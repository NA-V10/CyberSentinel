"""Audit log service — records all significant platform actions."""

from __future__ import annotations

from typing import Any, Dict, Optional

from loguru import logger

from backend.app.core.database import AsyncSessionLocal
from backend.app.models.incident import AuditLog

# Known event types
AUDIT_EVENTS = {
    "incident_analyzed",
    "recommendation_generated",
    "mitigation_approved",
    "mitigation_rejected",
    "mitigation_edited",
    "report_exported",
    "incident_escalated",
    "feedback_submitted",
    "admin_changed_settings",
    "user_login",
    "user_logout",
    "data_ingested",
    "model_trained",
    "simulation_run",
    "memory_saved",
    "sla_assigned",
    "sla_breached",
}


async def log_action(
    user_id: str,
    event_type: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    org_id: Optional[str] = None,
) -> Optional[str]:
    """Write an audit log entry to the database.

    Parameters
    ----------
    user_id:
        The Clerk user ID performing the action.
    event_type:
        One of the known AUDIT_EVENTS values (or any custom string).
    resource_type:
        e.g. "incident", "report", "memory_entry"
    resource_id:
        UUID or identifier of the resource being acted upon.
    details:
        Arbitrary JSON details for the event.
    ip_address:
        The request IP address (from FastAPI Request object).
    org_id:
        Clerk organization ID for multi-tenant filtering.

    Returns
    -------
    str | None
        The created AuditLog ID as string, or None on failure.
    """
    try:
        record = AuditLog(
            user_id=user_id,
            org_id=org_id,
            event_type=event_type,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else None,
            details=details,
            ip_address=ip_address,
        )
        async with AsyncSessionLocal() as session:
            session.add(record)
            await session.commit()
            await session.refresh(record)
            log_id = str(record.id)
        logger.debug("Audit log written", event_type=event_type, user_id=user_id, id=log_id)
        return log_id
    except Exception as exc:
        logger.warning("Failed to write audit log", event_type=event_type, error=str(exc))
        return None
