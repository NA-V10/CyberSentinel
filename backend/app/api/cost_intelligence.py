"""FastAPI router: Cost Intelligence Platform endpoints."""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, Query, status

from backend.app.auth.clerk import get_current_user
from backend.app.core.database import get_db
from backend.app.services.cost_intelligence_service import (
    get_cost_by_agent,
    get_cost_by_model,
    get_cost_by_user,
    get_cost_by_workflow,
    get_cost_summary,
    get_optimization_suggestions,
    get_savings_summary,
)

router = APIRouter()


@router.get(
    "/summary",
    status_code=status.HTTP_200_OK,
    summary="Get cost summary for the organisation",
)
async def cost_summary(
    days: int = Query(default=30, ge=1, le=365),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db=Depends(get_db),
) -> Dict[str, Any]:
    """
    Return aggregate cost summary for the organisation.

    **Example Response:**
    ```json
    {
      "total_tokens": 4300000,
      "total_cost": 82.40,
      "cache_savings": 28.10,
      "total_calls": 3847,
      "avg_cost_per_call": 0.0214
    }
    ```
    """
    org_id = current_user.get("org_id", "default")
    summary = await get_cost_summary(db=db, org_id=org_id, days=days)
    suggestions = get_optimization_suggestions(summary)
    return {**summary, "optimization_suggestions": suggestions}


@router.get(
    "/by-agent",
    status_code=status.HTTP_200_OK,
    summary="Get cost breakdown by agent",
)
async def cost_by_agent(
    days: int = Query(default=30, ge=1, le=365),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db=Depends(get_db),
) -> Dict[str, Any]:
    """Return LLM cost breakdown grouped by agent name."""
    org_id = current_user.get("org_id", "default")
    data = await get_cost_by_agent(db=db, org_id=org_id, days=days)
    return {"data": data, "total": len(data)}


@router.get(
    "/by-model",
    status_code=status.HTTP_200_OK,
    summary="Get cost breakdown by model",
)
async def cost_by_model(
    days: int = Query(default=30, ge=1, le=365),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db=Depends(get_db),
) -> Dict[str, Any]:
    """Return LLM cost breakdown grouped by model name."""
    org_id = current_user.get("org_id", "default")
    data = await get_cost_by_model(db=db, org_id=org_id, days=days)
    return {"data": data, "total": len(data)}


@router.get(
    "/by-user",
    status_code=status.HTTP_200_OK,
    summary="Get cost breakdown by user",
)
async def cost_by_user(
    days: int = Query(default=30, ge=1, le=365),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db=Depends(get_db),
) -> Dict[str, Any]:
    """Return LLM cost breakdown grouped by user ID."""
    org_id = current_user.get("org_id", "default")
    data = await get_cost_by_user(db=db, org_id=org_id, days=days)
    return {"data": data, "total": len(data)}


@router.get(
    "/by-workflow",
    status_code=status.HTTP_200_OK,
    summary="Get cost breakdown by workflow",
)
async def cost_by_workflow(
    days: int = Query(default=30, ge=1, le=365),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db=Depends(get_db),
) -> Dict[str, Any]:
    """Return LLM cost breakdown grouped by workflow name."""
    org_id = current_user.get("org_id", "default")
    data = await get_cost_by_workflow(db=db, org_id=org_id, days=days)
    return {"data": data, "total": len(data)}


@router.get(
    "/savings",
    status_code=status.HTTP_200_OK,
    summary="Get cost savings summary",
)
async def cost_savings(
    days: int = Query(default=30, ge=1, le=365),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db=Depends(get_db),
) -> Dict[str, Any]:
    """
    Return savings breakdown from Redis cache hits, memory reuse, and RAG retrieval.

    **Example Response:**
    ```json
    {
      "redis_cache_savings": 28.10,
      "memory_reuse_savings": 9.25,
      "rag_retrieval_savings": 5.60,
      "total_savings": 42.95,
      "cache_hit_rate": 34.2
    }
    ```
    """
    org_id = current_user.get("org_id", "default")
    return await get_savings_summary(db=db, org_id=org_id, days=days)
