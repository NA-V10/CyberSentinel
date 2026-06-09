"""FastAPI router: Audit log endpoints."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query, status
from loguru import logger
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.clerk import get_current_user
from backend.app.core.database import get_db
from backend.app.models.incident import AuditLog

router = APIRouter()


class AuditLogItem(BaseModel):
    id: str
    user_id: str
    event_type: str
    resource_type: Optional[str]
    resource_id: Optional[str]
    details: Optional[Dict[str, Any]]
    ip_address: Optional[str]
    org_id: Optional[str]
    created_at: str


@router.get(
    "/",
    status_code=status.HTTP_200_OK,
    summary="List audit logs (paginated)",
)
async def list_audit_logs(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    event_type: Optional[str] = Query(default=None),
    user_id_filter: Optional[str] = Query(default=None, alias="user_id"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Retrieve paginated audit logs. Optionally filter by event_type or user_id."""
    try:
        query = select(AuditLog).order_by(AuditLog.created_at.desc())

        if event_type:
            query = query.where(AuditLog.event_type == event_type)
        if user_id_filter:
            query = query.where(AuditLog.user_id == user_id_filter)

        # Filter by org if present
        org_id = current_user.get("org_id")
        if org_id:
            query = query.where(AuditLog.org_id == org_id)

        query = query.offset(offset).limit(limit)
        result = await db.execute(query)
        logs = result.scalars().all()

        items = [
            AuditLogItem(
                id=str(log.id),
                user_id=log.user_id,
                event_type=log.event_type,
                resource_type=log.resource_type,
                resource_id=log.resource_id,
                details=log.details,
                ip_address=log.ip_address,
                org_id=log.org_id,
                created_at=log.created_at.isoformat(),
            )
            for log in logs
        ]

        return {"items": [i.model_dump() for i in items], "total": len(items), "offset": offset, "limit": limit}

    except Exception as exc:
        logger.warning("Failed to fetch audit logs", error=str(exc))
        return {"items": [], "total": 0, "offset": offset, "limit": limit, "error": str(exc)}
