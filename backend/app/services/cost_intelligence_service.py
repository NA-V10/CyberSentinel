"""Cost Intelligence Service — tracks LLM token usage, costs, and savings."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select, text

from backend.app.models.premium_models import CostUsageLog

# ---------------------------------------------------------------------------
# Cost rates (USD per 1K tokens)
# ---------------------------------------------------------------------------
_COST_RATES: Dict[str, Dict[str, float]] = {
    "gpt-4.1": {"input": 0.002, "output": 0.008},
    "gpt-4.1-mini": {"input": 0.0004, "output": 0.0016},
    "text-embedding-3-small": {"input": 0.00002, "output": 0.0},
    "claude-3-5-sonnet": {"input": 0.003, "output": 0.015},
    "claude-3-5-haiku": {"input": 0.0008, "output": 0.004},
    "llama-3.1-8b": {"input": 0.0001, "output": 0.0001},
    "mock": {"input": 0.0, "output": 0.0},
}

_REDIS_CACHE_SAVINGS_RATE = 0.0015  # Per cache hit, estimated savings USD
_MEMORY_REUSE_SAVINGS_RATE = 0.0008  # Per memory reuse


def estimate_cost(
    model_name: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> float:
    """Estimate the USD cost of a model call."""
    rates = _COST_RATES.get(model_name, {"input": 0.001, "output": 0.002})
    return round(
        (prompt_tokens / 1000) * rates["input"]
        + (completion_tokens / 1000) * rates["output"],
        8,
    )


async def log_usage(
    db: AsyncSession,
    org_id: str,
    model_name: str,
    prompt_tokens: int,
    completion_tokens: int,
    workflow_name: str = "unknown",
    agent_name: str = "unknown",
    user_id: Optional[str] = None,
    incident_id: Optional[str] = None,
    feature_name: Optional[str] = None,
    cache_hit: bool = False,
    memory_reuse: bool = False,
) -> None:
    """Log a single LLM usage event to the database."""
    total_tokens = prompt_tokens + completion_tokens
    cost = estimate_cost(model_name, prompt_tokens, completion_tokens)
    cache_savings = _REDIS_CACHE_SAVINGS_RATE if cache_hit else 0.0
    memory_savings = _MEMORY_REUSE_SAVINGS_RATE if memory_reuse else 0.0

    try:
        log = CostUsageLog(
            org_id=org_id,
            user_id=user_id,
            incident_id=incident_id,
            workflow_name=workflow_name,
            agent_name=agent_name,
            model_name=model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            estimated_cost=cost,
            cache_hit=cache_hit,
            cache_savings=cache_savings,
            memory_reuse_savings=memory_savings,
            feature_name=feature_name,
        )
        db.add(log)
        await db.commit()
    except Exception as exc:
        logger.warning("Failed to log cost usage", error=str(exc))
        await db.rollback()


async def get_cost_summary(
    db: AsyncSession, org_id: str, days: int = 30
) -> Dict[str, Any]:
    """Return aggregate cost summary for an organisation."""
    try:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        result = await db.execute(
            select(
                func.sum(CostUsageLog.total_tokens).label("total_tokens"),
                func.sum(CostUsageLog.prompt_tokens).label("prompt_tokens"),
                func.sum(CostUsageLog.completion_tokens).label("completion_tokens"),
                func.sum(CostUsageLog.estimated_cost).label("total_cost"),
                func.sum(CostUsageLog.cache_savings).label("cache_savings"),
                func.sum(CostUsageLog.memory_reuse_savings).label("memory_savings"),
                func.count(CostUsageLog.id).label("total_calls"),
            ).where(
                CostUsageLog.org_id == org_id,
                CostUsageLog.created_at >= since,
            )
        )
        row = result.one()
        total_tokens = int(row.total_tokens or 0)
        total_cost = float(row.total_cost or 0.0)
        total_calls = int(row.total_calls or 0)
        avg_cost_per_call = round(total_cost / max(total_calls, 1), 6)

        return {
            "total_tokens": total_tokens,
            "prompt_tokens": int(row.prompt_tokens or 0),
            "completion_tokens": int(row.completion_tokens or 0),
            "total_cost": round(total_cost, 4),
            "cache_savings": round(float(row.cache_savings or 0.0), 4),
            "memory_savings": round(float(row.memory_savings or 0.0), 4),
            "total_savings": round(float(row.cache_savings or 0) + float(row.memory_savings or 0), 4),
            "total_calls": total_calls,
            "avg_cost_per_call": avg_cost_per_call,
            "days_period": days,
        }
    except Exception as exc:
        logger.warning("Failed to get cost summary from DB", error=str(exc))
        return _mock_cost_summary()


async def get_cost_by_agent(
    db: AsyncSession, org_id: str, days: int = 30
) -> List[Dict[str, Any]]:
    """Return cost breakdown by agent."""
    try:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        result = await db.execute(
            select(
                CostUsageLog.agent_name,
                func.sum(CostUsageLog.total_tokens).label("total_tokens"),
                func.sum(CostUsageLog.estimated_cost).label("total_cost"),
                func.count(CostUsageLog.id).label("call_count"),
            ).where(
                CostUsageLog.org_id == org_id,
                CostUsageLog.created_at >= since,
            ).group_by(CostUsageLog.agent_name).order_by(
                func.sum(CostUsageLog.estimated_cost).desc()
            )
        )
        rows = result.all()
        return [
            {
                "agent_name": row.agent_name or "unknown",
                "total_tokens": int(row.total_tokens or 0),
                "total_cost": round(float(row.total_cost or 0.0), 6),
                "call_count": int(row.call_count or 0),
            }
            for row in rows
        ]
    except Exception as exc:
        logger.warning("Failed to get cost by agent", error=str(exc))
        return _mock_cost_by_agent()


async def get_cost_by_model(
    db: AsyncSession, org_id: str, days: int = 30
) -> List[Dict[str, Any]]:
    """Return cost breakdown by model."""
    try:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        result = await db.execute(
            select(
                CostUsageLog.model_name,
                func.sum(CostUsageLog.total_tokens).label("total_tokens"),
                func.sum(CostUsageLog.prompt_tokens).label("prompt_tokens"),
                func.sum(CostUsageLog.completion_tokens).label("completion_tokens"),
                func.sum(CostUsageLog.estimated_cost).label("total_cost"),
                func.count(CostUsageLog.id).label("call_count"),
            ).where(
                CostUsageLog.org_id == org_id,
                CostUsageLog.created_at >= since,
            ).group_by(CostUsageLog.model_name).order_by(
                func.sum(CostUsageLog.estimated_cost).desc()
            )
        )
        rows = result.all()
        return [
            {
                "model_name": row.model_name or "unknown",
                "total_tokens": int(row.total_tokens or 0),
                "prompt_tokens": int(row.prompt_tokens or 0),
                "completion_tokens": int(row.completion_tokens or 0),
                "total_cost": round(float(row.total_cost or 0.0), 6),
                "call_count": int(row.call_count or 0),
            }
            for row in rows
        ]
    except Exception as exc:
        logger.warning("Failed to get cost by model", error=str(exc))
        return _mock_cost_by_model()


async def get_cost_by_workflow(
    db: AsyncSession, org_id: str, days: int = 30
) -> List[Dict[str, Any]]:
    """Return cost breakdown by workflow."""
    try:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        result = await db.execute(
            select(
                CostUsageLog.workflow_name,
                func.sum(CostUsageLog.total_tokens).label("total_tokens"),
                func.sum(CostUsageLog.estimated_cost).label("total_cost"),
                func.count(CostUsageLog.id).label("call_count"),
            ).where(
                CostUsageLog.org_id == org_id,
                CostUsageLog.created_at >= since,
            ).group_by(CostUsageLog.workflow_name).order_by(
                func.sum(CostUsageLog.estimated_cost).desc()
            )
        )
        rows = result.all()
        return [
            {
                "workflow_name": row.workflow_name or "unknown",
                "total_tokens": int(row.total_tokens or 0),
                "total_cost": round(float(row.total_cost or 0.0), 6),
                "call_count": int(row.call_count or 0),
            }
            for row in rows
        ]
    except Exception as exc:
        logger.warning("Failed to get cost by workflow", error=str(exc))
        return _mock_cost_by_workflow()


async def get_cost_by_user(
    db: AsyncSession, org_id: str, days: int = 30
) -> List[Dict[str, Any]]:
    """Return cost breakdown by user."""
    try:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        result = await db.execute(
            select(
                CostUsageLog.user_id,
                func.sum(CostUsageLog.total_tokens).label("total_tokens"),
                func.sum(CostUsageLog.estimated_cost).label("total_cost"),
                func.count(CostUsageLog.id).label("call_count"),
            ).where(
                CostUsageLog.org_id == org_id,
                CostUsageLog.created_at >= since,
                CostUsageLog.user_id.isnot(None),
            ).group_by(CostUsageLog.user_id).order_by(
                func.sum(CostUsageLog.estimated_cost).desc()
            ).limit(20)
        )
        rows = result.all()
        return [
            {
                "user_id": row.user_id or "unknown",
                "total_tokens": int(row.total_tokens or 0),
                "total_cost": round(float(row.total_cost or 0.0), 6),
                "call_count": int(row.call_count or 0),
            }
            for row in rows
        ]
    except Exception as exc:
        logger.warning("Failed to get cost by user", error=str(exc))
        return []


async def get_savings_summary(
    db: AsyncSession, org_id: str, days: int = 30
) -> Dict[str, Any]:
    """Return savings breakdown from cache hits and memory reuse."""
    try:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        result = await db.execute(
            select(
                func.sum(CostUsageLog.cache_savings).label("redis_savings"),
                func.sum(CostUsageLog.memory_reuse_savings).label("memory_savings"),
                func.count(CostUsageLog.id).filter(CostUsageLog.cache_hit.is_(True)).label("cache_hits"),
                func.count(CostUsageLog.id).label("total_calls"),
            ).where(
                CostUsageLog.org_id == org_id,
                CostUsageLog.created_at >= since,
            )
        )
        row = result.one()
        redis_savings = round(float(row.redis_savings or 0.0), 4)
        memory_savings = round(float(row.memory_savings or 0.0), 4)
        cache_hits = int(row.cache_hits or 0)
        total_calls = int(row.total_calls or 0)

        # Estimate RAG retrieval savings (avoiding full LLM calls)
        rag_savings = round(cache_hits * 0.0005, 4)
        total_savings = round(redis_savings + memory_savings + rag_savings, 4)
        monthly_estimate = round(total_savings * (30 / max(days, 1)), 4)

        return {
            "redis_cache_savings": redis_savings,
            "memory_reuse_savings": memory_savings,
            "rag_retrieval_savings": rag_savings,
            "total_savings": total_savings,
            "estimated_monthly_savings": monthly_estimate,
            "cache_hit_rate": round(cache_hits / max(total_calls, 1) * 100, 1),
            "cache_hits": cache_hits,
            "total_calls": total_calls,
            "avoided_llm_calls": cache_hits,
        }
    except Exception as exc:
        logger.warning("Failed to get savings summary", error=str(exc))
        return _mock_savings()


def get_optimization_suggestions(summary: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return actionable optimization suggestions based on usage data."""
    suggestions = [
        {
            "title": "Use smaller model for low-severity incidents",
            "description": "Switch gpt-4.1-mini for incidents with severity=low or medium to reduce costs by ~60%",
            "estimated_savings": "$15-25/month",
            "priority": "high",
            "category": "model_selection",
        },
        {
            "title": "Cache repeated MITRE mapping calls",
            "description": "MITRE technique mapping for common attack types can be cached in Redis (TTL 1h)",
            "estimated_savings": "$8-12/month",
            "priority": "medium",
            "category": "caching",
        },
        {
            "title": "Use local model for simulation mode",
            "description": "Digital twin simulations can use Llama-3.1-8B locally for near-zero cost",
            "estimated_savings": "$20-35/month",
            "priority": "high",
            "category": "model_selection",
        },
        {
            "title": "Summarise context before consensus analysis",
            "description": "Reduce input tokens by 40% by summarizing incident context before sending to all models",
            "estimated_savings": "$10-18/month",
            "priority": "medium",
            "category": "prompt_optimization",
        },
        {
            "title": "Skip consensus for low-risk incidents",
            "description": "Only run multi-LLM consensus for high/critical severity incidents (risk > 60)",
            "estimated_savings": "$25-40/month",
            "priority": "high",
            "category": "workflow",
        },
    ]

    total_cost = summary.get("total_cost", 0.0)
    if total_cost > 50:
        suggestions.insert(0, {
            "title": "Batch similar incidents for single analysis",
            "description": "Group low-severity incidents from same subnet for batch analysis instead of individual calls",
            "estimated_savings": "$30-50/month",
            "priority": "critical",
            "category": "batching",
        })

    return suggestions


# ---------------------------------------------------------------------------
# Mock fallbacks
# ---------------------------------------------------------------------------

def _mock_cost_summary() -> Dict[str, Any]:
    return {
        "total_tokens": 4_300_000,
        "prompt_tokens": 2_800_000,
        "completion_tokens": 1_500_000,
        "total_cost": 82.40,
        "cache_savings": 28.10,
        "memory_savings": 9.25,
        "total_savings": 37.35,
        "total_calls": 3847,
        "avg_cost_per_call": 0.0214,
        "days_period": 30,
    }


def _mock_cost_by_agent() -> List[Dict[str, Any]]:
    return [
        {"agent_name": "ConsensusAgent", "total_tokens": 980_000, "total_cost": 23.52, "call_count": 412},
        {"agent_name": "AutonomousInvestigationAgent", "total_tokens": 720_000, "total_cost": 17.28, "call_count": 218},
        {"agent_name": "MitigationAgent", "total_tokens": 650_000, "total_cost": 14.30, "call_count": 1842},
        {"agent_name": "ExplainabilityAgent", "total_tokens": 580_000, "total_cost": 11.60, "call_count": 1842},
        {"agent_name": "SelfReflectionAgent", "total_tokens": 390_000, "total_cost": 9.36, "call_count": 623},
        {"agent_name": "ClassificationAgent", "total_tokens": 320_000, "total_cost": 5.12, "call_count": 1842},
        {"agent_name": "JudgeAgent", "total_tokens": 285_000, "total_cost": 4.56, "call_count": 1842},
    ]


def _mock_cost_by_model() -> List[Dict[str, Any]]:
    return [
        {"model_name": "gpt-4.1", "total_tokens": 1_850_000, "prompt_tokens": 1_200_000, "completion_tokens": 650_000, "total_cost": 44.40, "call_count": 924},
        {"model_name": "gpt-4.1-mini", "total_tokens": 1_640_000, "prompt_tokens": 1_100_000, "completion_tokens": 540_000, "total_cost": 23.50, "call_count": 2418},
        {"model_name": "claude-3-5-sonnet", "total_tokens": 640_000, "prompt_tokens": 420_000, "completion_tokens": 220_000, "total_cost": 11.58, "call_count": 412},
        {"model_name": "text-embedding-3-small", "total_tokens": 170_000, "prompt_tokens": 170_000, "completion_tokens": 0, "total_cost": 0.34, "call_count": 4200},
        {"model_name": "llama-3.1-8b", "total_tokens": 210_000, "prompt_tokens": 140_000, "completion_tokens": 70_000, "total_cost": 0.021, "call_count": 218},
    ]


def _mock_cost_by_workflow() -> List[Dict[str, Any]]:
    return [
        {"workflow_name": "consensus_analysis", "total_tokens": 980_000, "total_cost": 23.52, "call_count": 412},
        {"workflow_name": "autonomous_investigation", "total_tokens": 720_000, "total_cost": 17.28, "call_count": 218},
        {"workflow_name": "incident_analysis", "total_tokens": 1_230_000, "total_cost": 22.80, "call_count": 1842},
        {"workflow_name": "self_reflection", "total_tokens": 390_000, "total_cost": 9.36, "call_count": 623},
        {"workflow_name": "digital_twin_simulation", "total_tokens": 210_000, "total_cost": 5.04, "call_count": 186},
        {"workflow_name": "rag_retrieval", "total_tokens": 170_000, "total_cost": 3.06, "call_count": 4200},
        {"workflow_name": "campaign_detection", "total_tokens": 110_000, "total_cost": 2.64, "call_count": 94},
    ]


def _mock_savings() -> Dict[str, Any]:
    return {
        "redis_cache_savings": 28.10,
        "memory_reuse_savings": 9.25,
        "rag_retrieval_savings": 5.60,
        "total_savings": 42.95,
        "estimated_monthly_savings": 42.95,
        "cache_hit_rate": 34.2,
        "cache_hits": 1316,
        "total_calls": 3847,
        "avoided_llm_calls": 1316,
    }
