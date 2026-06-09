"""
User memory service for CyberSentinel AI.

Manages ChatGPT-like conversation history and long-term user memories.
Conversation/message data is persisted in Postgres.
Memory entries are stored in Postgres and embedded into Qdrant for semantic
search.
All operations are scoped per user_id.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.core.database import AsyncSessionLocal
from backend.app.models.incident import Conversation, MemoryEntry, Message
from backend.app.rag.embeddings import EmbeddingService
from backend.app.rag.vector_store import VectorStoreService

# ---------------------------------------------------------------------------
# Qdrant collection for memory entries (separate from incident collection)
# ---------------------------------------------------------------------------

_MEMORY_QDRANT_COLLECTION = "cybersentinel_memory"

# Similarity search limit defaults
_DEFAULT_SEMANTIC_LIMIT = 5

# ---------------------------------------------------------------------------
# Module-level singletons (lazy)
# ---------------------------------------------------------------------------

_embedding_service: Optional[EmbeddingService] = None
_vector_store: Optional[VectorStoreService] = None


def _get_embedding_service() -> EmbeddingService:
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service


def _get_vector_store() -> VectorStoreService:
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStoreService(collection=_MEMORY_QDRANT_COLLECTION)
    return _vector_store


# ---------------------------------------------------------------------------
# Conversation management
# ---------------------------------------------------------------------------


async def create_conversation(
    user_id: str,
    title: Optional[str] = None,
    db: Optional[AsyncSession] = None,
) -> Dict[str, Any]:
    """Create a new conversation for a user.

    Parameters
    ----------
    user_id:
        The authenticated user's identifier (from Clerk).
    title:
        Optional human-readable title (e.g. "Brute Force Investigation").
    db:
        Optional existing async session.  A new session is opened if omitted.

    Returns
    -------
    dict
        Serialised :class:`~backend.app.models.incident.Conversation`.
    """
    conv = Conversation(
        id=uuid.uuid4(),
        user_id=user_id,
        title=title or f"Conversation {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
    )

    async def _run(session: AsyncSession) -> Dict[str, Any]:
        session.add(conv)
        await session.flush()
        await session.refresh(conv)
        return _serialise_conversation(conv)

    if db is not None:
        result = await _run(db)
        logger.info("Conversation created", conversation_id=str(conv.id), user_id=user_id)
        return result

    async with AsyncSessionLocal() as session:
        result = await _run(session)
        await session.commit()

    logger.info("Conversation created", conversation_id=str(conv.id), user_id=user_id)
    return result


async def add_message(
    conversation_id: str,
    role: str,
    content: str,
    metadata: Optional[Dict[str, Any]] = None,
    db: Optional[AsyncSession] = None,
) -> Dict[str, Any]:
    """Append a message to an existing conversation.

    Parameters
    ----------
    conversation_id:
        UUID of the target conversation.
    role:
        One of ``'user'``, ``'assistant'``, ``'system'``.
    content:
        Message text.
    metadata:
        Optional JSON blob (token counts, tool calls, citations, etc.).
    db:
        Optional existing async session.

    Returns
    -------
    dict
        Serialised :class:`~backend.app.models.incident.Message`.

    Raises
    ------
    ValueError
        If *role* is not one of the accepted values.
    """
    role = role.lower()
    if role not in ("user", "assistant", "system"):
        raise ValueError(f"Invalid role '{role}'.  Must be 'user', 'assistant', or 'system'.")

    msg = Message(
        id=uuid.uuid4(),
        conversation_id=uuid.UUID(conversation_id),
        role=role,
        content=content,
        extra_data=metadata,
    )

    async def _run(session: AsyncSession) -> Dict[str, Any]:
        session.add(msg)
        await session.flush()
        await session.refresh(msg)
        # Bump conversation updated_at
        conv = await session.get(Conversation, uuid.UUID(conversation_id))
        if conv:
            conv.updated_at = datetime.utcnow()
        return _serialise_message(msg)

    if db is not None:
        result = await _run(db)
        logger.debug(
            "Message added",
            conversation_id=conversation_id,
            role=role,
            chars=len(content),
        )
        return result

    async with AsyncSessionLocal() as session:
        result = await _run(session)
        await session.commit()

    logger.debug(
        "Message added",
        conversation_id=conversation_id,
        role=role,
        chars=len(content),
    )
    return result


async def get_conversations(
    user_id: str,
    limit: int = 20,
    db: Optional[AsyncSession] = None,
) -> List[Dict[str, Any]]:
    """Return a user's conversations, most recently updated first.

    Parameters
    ----------
    user_id:
        The authenticated user's identifier.
    limit:
        Maximum number of conversations to return (default 20).
    db:
        Optional existing async session.

    Returns
    -------
    list[dict]
        Serialised conversations ordered by ``updated_at DESC``.
    """
    stmt = (
        select(Conversation)
        .where(Conversation.user_id == user_id)
        .order_by(desc(Conversation.updated_at))
        .limit(limit)
    )

    async def _run(session: AsyncSession) -> List[Dict[str, Any]]:
        result = await session.execute(stmt)
        convs = result.scalars().all()
        return [_serialise_conversation(c) for c in convs]

    if db is not None:
        return await _run(db)

    async with AsyncSessionLocal() as session:
        return await _run(session)


async def get_conversation_messages(
    conversation_id: str,
    db: Optional[AsyncSession] = None,
) -> List[Dict[str, Any]]:
    """Return all messages in a conversation, ordered chronologically.

    Parameters
    ----------
    conversation_id:
        UUID of the target conversation.
    db:
        Optional existing async session.

    Returns
    -------
    list[dict]
        Serialised messages ordered by ``created_at ASC``.
    """
    stmt = (
        select(Message)
        .where(Message.conversation_id == uuid.UUID(conversation_id))
        .order_by(Message.created_at)
    )

    async def _run(session: AsyncSession) -> List[Dict[str, Any]]:
        result = await session.execute(stmt)
        msgs = result.scalars().all()
        return [_serialise_message(m) for m in msgs]

    if db is not None:
        return await _run(db)

    async with AsyncSessionLocal() as session:
        return await _run(session)


# ---------------------------------------------------------------------------
# Semantic memory search
# ---------------------------------------------------------------------------


async def semantic_search_memory(
    user_id: str,
    query: str,
    limit: int = _DEFAULT_SEMANTIC_LIMIT,
) -> List[Dict[str, Any]]:
    """Perform a semantic similarity search over a user's past messages.

    Embeds the *query* and searches the Qdrant memory collection for the
    closest message/memory entry vectors scoped to *user_id*.

    Parameters
    ----------
    user_id:
        The authenticated user's identifier.
    query:
        Natural-language search query.
    limit:
        Maximum number of results.

    Returns
    -------
    list[dict]
        Matching messages/memory entries with ``content``, ``score``, and
        metadata.
    """
    embedding_svc = _get_embedding_service()
    vector_store = _get_vector_store()

    try:
        await vector_store.initialize_collection()
        query_embedding = await embedding_svc.embed_text(query)

        hits = await vector_store.search_similar(
            query_embedding=query_embedding,
            limit=limit,
            filters={"user_id": user_id},
        )
    except Exception as exc:
        logger.warning("Semantic memory search failed", error=str(exc))
        return []

    results = []
    for hit in hits:
        payload = hit.get("payload", {})
        results.append(
            {
                "id": payload.get("memory_id") or hit.get("id"),
                "content": payload.get("content", ""),
                "memory_type": payload.get("memory_type"),
                "score": hit.get("score", 0.0),
                "created_at": payload.get("created_at"),
                "user_id": payload.get("user_id"),
            }
        )

    logger.info(
        "Semantic memory search complete",
        user_id=user_id,
        query_chars=len(query),
        results=len(results),
    )
    return results


# ---------------------------------------------------------------------------
# Memory entry management
# ---------------------------------------------------------------------------


async def store_memory_entry(
    user_id: str,
    content: str,
    memory_type: str = "semantic",
    db: Optional[AsyncSession] = None,
) -> Dict[str, Any]:
    """Store a long-term memory fragment for a user.

    The entry is persisted in Postgres and embedded into Qdrant for later
    semantic search.

    Parameters
    ----------
    user_id:
        The authenticated user's identifier.
    content:
        Memory text to store and embed.
    memory_type:
        Category label: ``'episodic'``, ``'semantic'``, or ``'procedural'``.
    db:
        Optional existing async session.

    Returns
    -------
    dict
        Serialised :class:`~backend.app.models.incident.MemoryEntry`.
    """
    entry = MemoryEntry(
        id=uuid.uuid4(),
        user_id=user_id,
        content=content,
        memory_type=memory_type,
    )

    embedding_id: Optional[str] = None
    try:
        embedding_svc = _get_embedding_service()
        vector_store = _get_vector_store()
        await vector_store.initialize_collection()

        embedding = await embedding_svc.embed_text(content)
        entry_id_str = str(entry.id)

        await vector_store.upsert_incident(
            incident_id=entry_id_str,
            embedding=embedding,
            payload={
                "user_id": user_id,
                "content": content,
                "memory_type": memory_type,
                "memory_id": entry_id_str,
                "created_at": datetime.utcnow().isoformat(),
            },
        )
        embedding_id = entry_id_str
        entry.embedding_id = embedding_id
    except Exception as exc:
        logger.warning(
            "Failed to embed memory entry — saving without vector",
            error=str(exc),
        )

    async def _run(session: AsyncSession) -> Dict[str, Any]:
        session.add(entry)
        await session.flush()
        await session.refresh(entry)
        return _serialise_memory_entry(entry)

    if db is not None:
        result = await _run(db)
        logger.info(
            "Memory entry stored",
            entry_id=str(entry.id),
            user_id=user_id,
            memory_type=memory_type,
            embedded=embedding_id is not None,
        )
        return result

    async with AsyncSessionLocal() as session:
        result = await _run(session)
        await session.commit()

    logger.info(
        "Memory entry stored",
        entry_id=str(entry.id),
        user_id=user_id,
        memory_type=memory_type,
        embedded=embedding_id is not None,
    )
    return result


async def remember_mitigation(
    user_id: str,
    attack_type: str,
    mitigation: str,
    worked: bool,
    db: Optional[AsyncSession] = None,
) -> Dict[str, Any]:
    """Store a mitigation outcome as a procedural memory for a user.

    Formats a human-readable summary and delegates to
    :func:`store_memory_entry`.

    Parameters
    ----------
    user_id:
        The authenticated user's identifier.
    attack_type:
        The threat category (e.g. ``"Brute Force"``).
    mitigation:
        The mitigation action taken.
    worked:
        Whether the mitigation was effective.
    db:
        Optional existing async session.

    Returns
    -------
    dict
        The stored :class:`~backend.app.models.incident.MemoryEntry`.
    """
    outcome = "worked" if worked else "did not work"
    content = (
        f"Mitigation for {attack_type}: '{mitigation}'. "
        f"Outcome: this mitigation {outcome}."
    )
    return await store_memory_entry(
        user_id=user_id,
        content=content,
        memory_type="procedural",
        db=db,
    )


async def get_memory_entries(
    user_id: str,
    memory_type: Optional[str] = None,
    limit: int = 50,
    db: Optional[AsyncSession] = None,
) -> List[Dict[str, Any]]:
    """Return stored memory entries for a user.

    Parameters
    ----------
    user_id:
        The authenticated user's identifier.
    memory_type:
        Optional filter by memory type (``'episodic'``, ``'semantic'``,
        ``'procedural'``).
    limit:
        Maximum number of entries to return.
    db:
        Optional existing async session.

    Returns
    -------
    list[dict]
        Memory entries ordered by ``created_at DESC``.
    """
    stmt = (
        select(MemoryEntry)
        .where(MemoryEntry.user_id == user_id)
    )
    if memory_type:
        stmt = stmt.where(MemoryEntry.memory_type == memory_type)

    stmt = stmt.order_by(desc(MemoryEntry.created_at)).limit(limit)

    async def _run(session: AsyncSession) -> List[Dict[str, Any]]:
        result = await session.execute(stmt)
        entries = result.scalars().all()
        return [_serialise_memory_entry(e) for e in entries]

    if db is not None:
        return await _run(db)

    async with AsyncSessionLocal() as session:
        return await _run(session)


# ---------------------------------------------------------------------------
# Serialisation helpers
# ---------------------------------------------------------------------------


def _serialise_conversation(conv: Conversation) -> Dict[str, Any]:
    return {
        "id": str(conv.id),
        "user_id": conv.user_id,
        "title": conv.title,
        "created_at": conv.created_at.isoformat() if conv.created_at else None,
        "updated_at": conv.updated_at.isoformat() if conv.updated_at else None,
    }


def _serialise_message(msg: Message) -> Dict[str, Any]:
    return {
        "id": str(msg.id),
        "conversation_id": str(msg.conversation_id),
        "role": msg.role,
        "content": msg.content,
        "metadata": msg.extra_data,
        "created_at": msg.created_at.isoformat() if msg.created_at else None,
    }


def _serialise_memory_entry(entry: MemoryEntry) -> Dict[str, Any]:
    return {
        "id": str(entry.id),
        "user_id": entry.user_id,
        "content": entry.content,
        "memory_type": entry.memory_type,
        "embedding_id": entry.embedding_id,
        "created_at": entry.created_at.isoformat() if entry.created_at else None,
    }
