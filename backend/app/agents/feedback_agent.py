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

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.agents.state import AgentState
from backend.app.core.config import settings
from backend.app.core.database import AsyncSessionLocal
from backend.app.models.incident import Conversation, Incident, Message
from backend.app.rag.embeddings import EmbeddingService
from backend.app.rag.vector_store import VectorStoreService


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
    severity_norm: Optional[str] = None

    if severity_raw:
        sv = severity_raw.strip().lower()
        valid = {"low", "medium", "high", "critical"}
        severity_norm = sv if sv in valid else None

    # Pre-generate the UUID so embedding_id can reference it in the same transaction.
    # The Qdrant point ID is derived from this UUID (see _to_qdrant_id), so both
    # stores share a stable identifier without a second DB round-trip.
    incident_uuid = uuid.uuid4()

    incident = Incident(
        id=incident_uuid,
        user_id=user_id,
        source_ip=state_snapshot.get("source_ip"),
        dest_ip=state_snapshot.get("dest_ip"),
        protocol=state_snapshot.get("protocol"),
        attack_type=threat_class,
        severity=severity_norm,
        raw_text=state_snapshot.get("incident_text"),
        embedding_id=str(incident_uuid),
    )
    db.add(incident)
    await db.flush()
    logger.debug("Incident record created", incident_id=str(incident.id))
    return incident.id


async def _store_embedding(incident_id: uuid.UUID, state_snapshot: Dict[str, Any]) -> None:
    """Generate an embedding for the incident text and upsert it into Qdrant.

    Runs after the Postgres commit so the incident_id is stable.
    Failures are logged and swallowed — the main workflow must not break
    if Qdrant or the OpenAI embeddings API is temporarily unavailable.
    """
    raw_text: str = state_snapshot.get("incident_text") or ""
    if not raw_text.strip():
        return

    try:
        embedding_svc = EmbeddingService(api_key=settings.OPENAI_API_KEY)
        vector_store = VectorStoreService(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY,
            collection=settings.QDRANT_COLLECTION,
        )

        await vector_store.initialize_collection()

        vector = await embedding_svc.embed_text(raw_text)

        payload = {
            "attack_type": state_snapshot.get("threat_class"),
            "severity": state_snapshot.get("severity", "").lower() or None,
            "protocol": state_snapshot.get("protocol"),
            "source_ip": state_snapshot.get("source_ip"),
            "dest_ip": state_snapshot.get("dest_ip"),
            "description": raw_text[:500],
            "user_id": state_snapshot.get("user_id"),
        }

        await vector_store.upsert_incident(
            incident_id=str(incident_id),
            embedding=vector,
            payload={k: v for k, v in payload.items() if v is not None},
        )

        await vector_store.close()
        logger.info("Embedding stored in Qdrant", incident_id=str(incident_id))

    except Exception as exc:
        logger.warning("Failed to store embedding in Qdrant", incident_id=str(incident_id), error=str(exc))


async def _persist(state: AgentState) -> Optional[uuid.UUID]:
    """Run all DB writes inside a single async session, then store the embedding."""
    user_id: str = state.get("user_id") or "anonymous"
    session_id: str = state.get("session_id") or str(uuid.uuid4())
    incident_text: str = state.get("incident_text") or ""
    final_answer: str = state.get("final_answer") or state.get("explanation") or ""
    threat_class: Optional[str] = state.get("threat_class")

    incident_id: Optional[uuid.UUID] = None

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
        except Exception as exc:
            await db.rollback()
            logger.error("FeedbackAgent: DB write failed", error=str(exc))
            return None

    # Embed and upsert into Qdrant after the DB transaction is committed
    if incident_id is not None:
        await _store_embedding(incident_id, dict(state))

    return incident_id


async def feedback_agent(state: AgentState) -> Dict[str, Any]:
    """LangGraph node: persist conversation + incident data to Neon and Qdrant.

    Runs synchronously so that the incident_id is available in the final state
    and can be returned to the caller via the HTTP response.

    Parameters
    ----------
    state:
        Current agent state.

    Returns
    -------
    dict
        Partial state update containing ``incident_id``.
    """
    logger.info("FeedbackAgent started")

    incident_id = await _persist(state)

    return {"incident_id": str(incident_id) if incident_id else None}
