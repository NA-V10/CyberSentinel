"""Feedback Learning Agent for CyberSentinel AI.

Stores the completed conversation + final answer to the database.
Runs asynchronously and does NOT block the main agent workflow.

Responsibilities:
  - Create or update the Conversation record in Postgres.
  - Append the user message and assistant final answer as Message records.
  - Update incident records with the generated threat classification.
  - (Future) Re-rank vector embeddings based on analyst feedback signal.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.agents.state import AgentState
from backend.app.core.database import AsyncSessionLocal
from backend.app.models.incident import Conversation, Incident, Message


async def _upsert_conversation(
    db: AsyncSession,
    session_id: str,
    user_id: str,
    threat_class: Optional[str],
) -> Conversation:
    """Return an existing Conversation or create a new one."""
    try:
        conv_uuid = uuid.UUID(session_id)
    except (ValueError, AttributeError):
        conv_uuid = uuid.uuid4()

    result = await db.execute(
        select(Conversation).where(Conversation.id == conv_uuid)
    )
    conv = result.scalar_one_or_none()

    if conv is None:
        title = f"Incident Analysis — {(threat_class or 'Unknown').title()}"
        conv = Conversation(
            id=conv_uuid,
            user_id=user_id,
            title=title,
        )
        db.add(conv)
        await db.flush()
        logger.debug("Conversation created", conv_id=str(conv_uuid))
    else:
        # Touch updated_at
        conv.updated_at = datetime.now(timezone.utc)  # type: ignore[assignment]
        logger.debug("Conversation updated", conv_id=str(conv_uuid))

    return conv


async def _store_messages(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    incident_text: str,
    final_answer: str,
    state_snapshot: Dict[str, Any],
) -> None:
    """Append user + assistant messages for this analysis turn."""
    # User message
    user_msg = Message(
        conversation_id=conversation_id,
        role="user",
        content=incident_text,
        extra_data={
            "source_ip": state_snapshot.get("source_ip"),
            "dest_ip": state_snapshot.get("dest_ip"),
            "protocol": state_snapshot.get("protocol"),
            "severity": state_snapshot.get("severity"),
        },
    )
    db.add(user_msg)

    # Assistant message (the full analysis)
    assistant_metadata = {
        "threat_class": state_snapshot.get("threat_class"),
        "threat_confidence": state_snapshot.get("threat_confidence"),
        "escalation_level": state_snapshot.get("escalation_level"),
        "judge_score": state_snapshot.get("judge_score"),
        "is_safe": state_snapshot.get("is_safe"),
        "citations": state_snapshot.get("citations") or [],
    }
    assistant_msg = Message(
        conversation_id=conversation_id,
        role="assistant",
        content=final_answer,
        extra_data=assistant_metadata,
    )
    db.add(assistant_msg)
    await db.flush()
    logger.debug(
        "Messages stored",
        conversation_id=str(conversation_id),
        roles=["user", "assistant"],
    )


async def _update_incident(
    db: AsyncSession,
    user_id: str,
    state_snapshot: Dict[str, Any],
) -> Optional[uuid.UUID]:
    """Create a new Incident record from the analysis state."""
    threat_class: Optional[str] = state_snapshot.get("threat_class")
    severity_raw: Optional[str] = state_snapshot.get("severity")
    severity_normalised: Optional[str] = None

    if severity_raw:
        sv = severity_raw.strip().lower()
        valid = {"low", "medium", "high", "critical"}
        severity_normalised = sv if sv in valid else None

    incident = Incident(
        user_id=user_id,
        source_ip=state_snapshot.get("source_ip"),
        dest_ip=state_snapshot.get("dest_ip"),
        protocol=state_snapshot.get("protocol"),
        attack_type=threat_class,
        severity=severity_normalised,
        raw_text=state_snapshot.get("incident_text"),
    )
    db.add(incident)
    await db.flush()
    logger.debug("Incident record created", incident_id=str(incident.id))
    return incident.id


async def _persist(state: AgentState) -> Optional[uuid.UUID]:
    """Run all DB writes inside a single async session."""
    user_id: str = state.get("user_id") or "anonymous"
    session_id: str = state.get("session_id") or str(uuid.uuid4())
    incident_text: str = state.get("incident_text") or ""
    final_answer: str = state.get("final_answer") or state.get("explanation") or ""
    threat_class: Optional[str] = state.get("threat_class")

    async with AsyncSessionLocal() as db:
        try:
            conv = await _upsert_conversation(db, session_id, user_id, threat_class)
            await _store_messages(db, conv.id, incident_text, final_answer, dict(state))
            incident_id = await _update_incident(db, user_id, dict(state))
            await db.commit()
            logger.info(
                "FeedbackAgent: data persisted",
                conversation_id=str(conv.id),
                incident_id=str(incident_id) if incident_id else None,
            )
            return incident_id
        except Exception as exc:
            await db.rollback()
            logger.error("FeedbackAgent: DB write failed", error=str(exc))
            return None


async def feedback_agent(state: AgentState) -> Dict[str, Any]:
    """LangGraph node: persist conversation data asynchronously.

    This node fires off a background task so it does not add latency to the
    response returned to the analyst.

    Parameters
    ----------
    state:
        Current agent state.

    Returns
    -------
    dict
        Empty state update (this agent only has side-effects).
    """
    logger.info("FeedbackAgent started (non-blocking)")

    # Schedule persistence as a background task so it doesn't block the graph
    asyncio.ensure_future(_persist(state))

    return {}
