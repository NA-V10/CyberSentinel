"""SLA tracking service per incident severity."""

from __future__ import annotations

import uuid as _uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from loguru import logger
from sqlalchemy import select

from backend.app.core.database import AsyncSessionLocal
from backend.app.models.incident import SLATracker

# SLA rules: severity → minutes until breach
SLA_RULES: Dict[str, int] = {
    "critical": 15,
    "high": 60,
    "medium": 240,
    "low": 1440,
}

SEVERITY_LEVELS: Dict[str, str] = {
    "critical": "L3 Specialist",
    "high": "L2 Analyst",
    "medium": "L1 Analyst",
    "low": "L1 Analyst",
}


async def assign_sla(
    incident_id: str,
    severity: str,
    org_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Assign SLA tracker to an incident based on severity.

    Returns a dict representation of the SLATracker record.
    """
    sev_lower = severity.lower()
    sla_minutes = SLA_RULES.get(sev_lower, 60)
    assigned_level = SEVERITY_LEVELS.get(sev_lower, "L1 Analyst")
    now = datetime.now(timezone.utc)
    deadline = now + timedelta(minutes=sla_minutes)

    try:
        record = SLATracker(
            incident_id=_uuid.UUID(incident_id),
            org_id=org_id,
            severity=sev_lower,
            assigned_level=assigned_level,
            sla_deadline=deadline,
            sla_minutes=sla_minutes,
            is_breached=False,
        )
        async with AsyncSessionLocal() as session:
            # Upsert: remove existing SLA for this incident if any
            existing = await session.execute(
                select(SLATracker).where(SLATracker.incident_id == _uuid.UUID(incident_id))
            )
            existing_row = existing.scalar_one_or_none()
            if existing_row:
                await session.delete(existing_row)
                await session.flush()
            session.add(record)
            await session.commit()
            await session.refresh(record)

        logger.info("SLA assigned", incident_id=incident_id, severity=sev_lower, minutes=sla_minutes)
        return _sla_to_dict(record)

    except Exception as exc:
        logger.warning("Failed to assign SLA", incident_id=incident_id, error=str(exc))
        return {
            "incident_id": incident_id,
            "severity": sev_lower,
            "assigned_level": assigned_level,
            "sla_minutes": sla_minutes,
            "error": str(exc),
        }


async def get_sla_status(incident_id: str) -> Dict[str, Any]:
    """Get current SLA status for an incident."""
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(SLATracker).where(SLATracker.incident_id == _uuid.UUID(incident_id))
            )
            record = result.scalar_one_or_none()

        if not record:
            return {"incident_id": incident_id, "error": "No SLA tracker found"}

        now = datetime.now(timezone.utc)
        deadline = record.sla_deadline
        if deadline and deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=timezone.utc)

        time_remaining = (deadline - now).total_seconds() if deadline else 0
        is_breached = time_remaining <= 0 and not record.resolved_at

        # Auto-update breach flag
        if is_breached and not record.is_breached:
            try:
                async with AsyncSessionLocal() as session:
                    rec = await session.get(SLATracker, record.id)
                    if rec:
                        rec.is_breached = True
                        await session.commit()
            except Exception:
                pass

        return {
            "incident_id": incident_id,
            "severity": record.severity,
            "assigned_level": record.assigned_level,
            "sla_minutes": record.sla_minutes,
            "deadline": deadline.isoformat() if deadline else None,
            "time_remaining_seconds": max(0, int(time_remaining)),
            "is_breached": is_breached or record.is_breached,
            "is_resolved": record.resolved_at is not None,
            "resolved_at": record.resolved_at.isoformat() if record.resolved_at else None,
            "created_at": record.created_at.isoformat(),
        }
    except Exception as exc:
        logger.warning("Failed to get SLA status", incident_id=incident_id, error=str(exc))
        return {"incident_id": incident_id, "error": str(exc)}


async def resolve_sla(incident_id: str) -> Dict[str, Any]:
    """Mark the SLA as resolved."""
    try:
        now = datetime.now(timezone.utc)
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(SLATracker).where(SLATracker.incident_id == _uuid.UUID(incident_id))
            )
            record = result.scalar_one_or_none()
            if not record:
                return {"error": "No SLA tracker found"}
            record.resolved_at = now
            await session.commit()
            await session.refresh(record)
        return _sla_to_dict(record)
    except Exception as exc:
        logger.warning("Failed to resolve SLA", incident_id=incident_id, error=str(exc))
        return {"incident_id": incident_id, "error": str(exc)}


def _sla_to_dict(record: SLATracker) -> Dict[str, Any]:
    return {
        "id": str(record.id),
        "incident_id": str(record.incident_id),
        "severity": record.severity,
        "assigned_level": record.assigned_level,
        "sla_minutes": record.sla_minutes,
        "deadline": record.sla_deadline.isoformat() if record.sla_deadline else None,
        "is_breached": record.is_breached,
        "is_resolved": record.resolved_at is not None,
        "created_at": record.created_at.isoformat(),
    }
