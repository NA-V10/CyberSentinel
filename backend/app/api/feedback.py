"""FastAPI router: Analyst feedback endpoints.

Routes
------
POST /feedback             — Store analyst feedback for an incident/conversation
GET  /feedback/stats       — Aggregate feedback statistics by attack_type
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.clerk import get_current_user
from backend.app.core.database import get_db
from backend.app.models.incident import AnalystFeedback, Incident
from backend.app.schemas.incident import FeedbackCreate, FeedbackResponse

router = APIRouter()


# ---------------------------------------------------------------------------
# Extra response schemas
# ---------------------------------------------------------------------------


class FeedbackStatsItem(BaseModel):
    attack_type: Optional[str]
    total_feedback: int
    avg_rating: Optional[float]
    mitigation_worked_pct: Optional[float]
    positive_count: int    # rating >= 4
    negative_count: int    # rating <= 2


class FeedbackStatsResponse(BaseModel):
    items: List[FeedbackStatsItem]
    total_feedback_records: int


# ---------------------------------------------------------------------------
# POST /feedback
# ---------------------------------------------------------------------------


@router.post(
    "/",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit analyst feedback for an incident or conversation",
)
async def submit_feedback(
    payload: FeedbackCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FeedbackResponse:
    """Store analyst feedback.

    Either ``incident_id`` or ``conversation_id`` (or both) must be supplied.

    **Rating**: 1 (very poor) to 5 (excellent).

    **Authentication**: Bearer JWT required (any role).
    """
    user_id: str = current_user["user_id"]

    if payload.incident_id is None and payload.conversation_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="At least one of 'incident_id' or 'conversation_id' must be provided.",
        )

    feedback = AnalystFeedback(
        user_id=user_id,
        incident_id=payload.incident_id,
        conversation_id=payload.conversation_id,
        rating=payload.rating,
        comment=payload.comment,
        mitigation_worked=payload.mitigation_worked,
    )
    db.add(feedback)
    await db.flush()
    await db.commit()

    logger.info(
        "submit_feedback: stored",
        feedback_id=str(feedback.id),
        user_id=user_id,
        rating=payload.rating,
    )

    return FeedbackResponse(
        id=feedback.id,
        incident_id=feedback.incident_id,
        conversation_id=feedback.conversation_id,
        user_id=feedback.user_id,
        rating=feedback.rating,
        comment=feedback.comment,
        mitigation_worked=feedback.mitigation_worked,
        created_at=feedback.created_at,
    )


# ---------------------------------------------------------------------------
# GET /feedback/stats
# ---------------------------------------------------------------------------


@router.get(
    "/stats",
    response_model=FeedbackStatsResponse,
    summary="Aggregate feedback statistics grouped by attack type",
)
async def feedback_stats(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FeedbackStatsResponse:
    """Return aggregated analyst feedback statistics, grouped by attack type.

    Joins ``analyst_feedback`` with ``incidents`` to get the attack type.

    **Authentication**: Bearer JWT required (any role).
    """
    user_id: str = current_user["user_id"]

    # ----- Raw aggregation query -----
    # We join feedback → incident to get attack_type per feedback record.
    # Feedback without an incident_id is bucketed under NULL attack_type.
    stmt = (
        select(
            Incident.attack_type.label("attack_type"),
            func.count(AnalystFeedback.id).label("total_feedback"),
            func.avg(AnalystFeedback.rating).label("avg_rating"),
            func.avg(
                func.cast(AnalystFeedback.mitigation_worked, type_=func.Float if False else None)
            ).label("mitigation_worked_avg"),
            func.sum(
                func.case(
                    (AnalystFeedback.rating >= 4, 1),
                    else_=0,
                )
            ).label("positive_count"),
            func.sum(
                func.case(
                    (AnalystFeedback.rating <= 2, 1),
                    else_=0,
                )
            ).label("negative_count"),
        )
        .outerjoin(Incident, AnalystFeedback.incident_id == Incident.id)
        .group_by(Incident.attack_type)
        .order_by(func.count(AnalystFeedback.id).desc())
    )

    result = await db.execute(stmt)
    rows = result.mappings().all()

    # ---- Also get total count ----
    total_result = await db.execute(select(func.count()).select_from(AnalystFeedback))
    total: int = total_result.scalar_one() or 0

    items: List[FeedbackStatsItem] = []
    for row in rows:
        avg_rating = round(float(row["avg_rating"]), 2) if row["avg_rating"] is not None else None

        # mitigation_worked is stored as boolean; compute percentage manually
        mw_avg = None
        if row["mitigation_worked_avg"] is not None:
            try:
                mw_avg = round(float(row["mitigation_worked_avg"]) * 100, 1)
            except (TypeError, ValueError):
                mw_avg = None

        items.append(
            FeedbackStatsItem(
                attack_type=row["attack_type"],
                total_feedback=int(row["total_feedback"] or 0),
                avg_rating=avg_rating,
                mitigation_worked_pct=mw_avg,
                positive_count=int(row["positive_count"] or 0),
                negative_count=int(row["negative_count"] or 0),
            )
        )

    logger.debug("feedback_stats: returned", items=len(items), total=total, user_id=user_id)

    return FeedbackStatsResponse(items=items, total_feedback_records=total)
