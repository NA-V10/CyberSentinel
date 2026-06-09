"""FastAPI router: Conversation memory endpoints.

Routes
------
GET    /memory/conversations            — List user's conversations (paginated)
GET    /memory/conversations/{id}       — Get full conversation + messages
DELETE /memory/conversations/{id}       — Delete a conversation
POST   /memory/search                   — Semantic search over conversations
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.auth.clerk import get_current_user
from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.models.incident import Conversation, Message
from backend.app.rag.embeddings import EmbeddingService
from backend.app.rag.vector_store import VectorStoreService

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic response schemas
# ---------------------------------------------------------------------------


class MessageOut(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    role: str
    content: str
    metadata: Optional[Dict[str, Any]] = None
    created_at: str

    class Config:
        from_attributes = True


class ConversationSummary(BaseModel):
    id: uuid.UUID
    user_id: str
    title: Optional[str]
    created_at: str
    updated_at: str
    message_count: int = 0

    class Config:
        from_attributes = True


class ConversationDetail(BaseModel):
    id: uuid.UUID
    user_id: str
    title: Optional[str]
    created_at: str
    updated_at: str
    messages: List[MessageOut]


class ConversationListResponse(BaseModel):
    items: List[ConversationSummary]
    total: int
    page: int
    page_size: int
    pages: int


class MemorySearchRequest(BaseModel):
    query: str = Field(..., min_length=3, description="Natural-language search query")
    limit: int = Field(default=5, ge=1, le=20)


class MemorySearchResult(BaseModel):
    conversation_id: str
    message_id: str
    role: str
    snippet: str
    score: float


class MemorySearchResponse(BaseModel):
    results: List[MemorySearchResult]
    total: int


# ---------------------------------------------------------------------------
# GET /memory/conversations
# ---------------------------------------------------------------------------


@router.get(
    "/conversations",
    response_model=ConversationListResponse,
    summary="List user's conversations (paginated)",
)
async def list_conversations(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ConversationListResponse:
    """Return a paginated list of conversations for the authenticated user.

    Ordered by ``updated_at`` descending (most recent first).
    """
    user_id: str = current_user["user_id"]
    offset = (page - 1) * page_size

    # Total count
    count_result = await db.execute(
        select(func.count()).where(Conversation.user_id == user_id)
    )
    total: int = count_result.scalar_one() or 0

    # Conversations with message count
    conv_result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == user_id)
        .order_by(Conversation.updated_at.desc())
        .offset(offset)
        .limit(page_size)
        .options(selectinload(Conversation.messages))
    )
    conversations = list(conv_result.scalars().all())

    items: List[ConversationSummary] = []
    for conv in conversations:
        items.append(
            ConversationSummary(
                id=conv.id,
                user_id=conv.user_id,
                title=conv.title,
                created_at=str(conv.created_at),
                updated_at=str(conv.updated_at),
                message_count=len(conv.messages),
            )
        )

    pages = max(1, (total + page_size - 1) // page_size)
    logger.debug("list_conversations", user_id=user_id, total=total, page=page)

    return ConversationListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


# ---------------------------------------------------------------------------
# GET /memory/conversations/{id}
# ---------------------------------------------------------------------------


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationDetail,
    summary="Get a full conversation with all messages",
)
async def get_conversation(
    conversation_id: uuid.UUID = Path(..., description="Conversation UUID"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ConversationDetail:
    """Retrieve a single conversation with its full message history.

    Users can only access their own conversations.
    """
    user_id: str = current_user["user_id"]

    result = await db.execute(
        select(Conversation)
        .where(Conversation.id == conversation_id, Conversation.user_id == user_id)
        .options(selectinload(Conversation.messages))
    )
    conv = result.scalar_one_or_none()

    if conv is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation '{conversation_id}' not found.",
        )

    messages_out: List[MessageOut] = [
        MessageOut(
            id=msg.id,
            conversation_id=msg.conversation_id,
            role=msg.role,
            content=msg.content,
            metadata=msg.extra_data,
            created_at=str(msg.created_at),
        )
        for msg in sorted(conv.messages, key=lambda m: m.created_at)
    ]

    return ConversationDetail(
        id=conv.id,
        user_id=conv.user_id,
        title=conv.title,
        created_at=str(conv.created_at),
        updated_at=str(conv.updated_at),
        messages=messages_out,
    )


# ---------------------------------------------------------------------------
# DELETE /memory/conversations/{id}
# ---------------------------------------------------------------------------


@router.delete(
    "/conversations/{conversation_id}",
    summary="Delete a conversation and all its messages",
    status_code=status.HTTP_200_OK,
)
async def delete_conversation(
    conversation_id: uuid.UUID = Path(..., description="Conversation UUID to delete"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Permanently delete a conversation (cascade-deletes all messages).

    Users can only delete their own conversations.
    """
    user_id: str = current_user["user_id"]

    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id, Conversation.user_id == user_id
        )
    )
    conv = result.scalar_one_or_none()

    if conv is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation '{conversation_id}' not found.",
        )

    await db.execute(
        delete(Conversation).where(Conversation.id == conversation_id)
    )
    await db.commit()

    logger.info(
        "delete_conversation: deleted",
        conversation_id=str(conversation_id),
        user_id=user_id,
    )

    return {"status": "deleted", "conversation_id": str(conversation_id)}


# ---------------------------------------------------------------------------
# POST /memory/search
# ---------------------------------------------------------------------------


@router.post(
    "/search",
    response_model=MemorySearchResponse,
    summary="Semantic search over the user's conversation history",
)
async def search_memory(
    request: MemorySearchRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MemorySearchResponse:
    """Perform semantic similarity search across the user's past conversations.

    Uses the same embedding + Qdrant pipeline as the main search endpoint but
    filters by the authenticated user's conversation messages.

    Falls back to a simple PostgreSQL full-text search if the vector service
    is unavailable.
    """
    user_id: str = current_user["user_id"]
    logger.info("search_memory: request", user_id=user_id, query=request.query[:80])

    results: List[MemorySearchResult] = []

    # ---- Attempt semantic search via Qdrant ----
    try:
        embedding_svc = EmbeddingService(api_key=settings.OPENAI_API_KEY)
        query_vector = await embedding_svc.embed_text(request.query)
        vector_store = VectorStoreService()
        hits = await vector_store.search_similar(
            query_embedding=query_vector,
            limit=request.limit * 3,  # over-fetch, filter below
            filters=None,
        )

        # Filter to user's incidents (conversation messages aren't directly in Qdrant
        # at this stage — use the payload user_id if available)
        user_hits = [h for h in hits if h.get("payload", {}).get("user_id") == user_id]

        for h in user_hits[: request.limit]:
            payload = h.get("payload") or {}
            results.append(
                MemorySearchResult(
                    conversation_id=str(payload.get("conversation_id", h.get("id", ""))),
                    message_id=str(h.get("id", "")),
                    role="assistant",
                    snippet=(payload.get("raw_text") or payload.get("description") or "")[:250],
                    score=round(float(h.get("score", 0.0)), 4),
                )
            )

    except Exception as exc:
        logger.warning("search_memory: vector search failed, falling back to FTS", error=str(exc))

    # ---- Fallback: PostgreSQL full-text search on messages ----
    if not results:
        try:
            # Get user's conversation IDs first
            conv_result = await db.execute(
                select(Conversation.id).where(Conversation.user_id == user_id)
            )
            conv_ids = [row[0] for row in conv_result.all()]

            if conv_ids:
                from sqlalchemy import text as sa_text

                fts_result = await db.execute(
                    sa_text(
                        """
                        SELECT
                            m.id           AS message_id,
                            m.conversation_id,
                            m.role,
                            m.content,
                            ts_rank(
                                to_tsvector('english', m.content),
                                plainto_tsquery('english', :query)
                            ) AS rank
                        FROM messages m
                        WHERE m.conversation_id = ANY(:conv_ids)
                          AND to_tsvector('english', m.content)
                              @@ plainto_tsquery('english', :query)
                        ORDER BY rank DESC
                        LIMIT :limit
                        """
                    ),
                    {
                        "query": request.query,
                        "conv_ids": conv_ids,
                        "limit": request.limit,
                    },
                )
                for row in fts_result.mappings().all():
                    results.append(
                        MemorySearchResult(
                            conversation_id=str(row["conversation_id"]),
                            message_id=str(row["message_id"]),
                            role=row["role"],
                            snippet=(row["content"] or "")[:250],
                            score=round(float(row.get("rank") or 0.0), 4),
                        )
                    )
        except Exception as exc:
            logger.error("search_memory: FTS fallback failed", error=str(exc))

    return MemorySearchResponse(results=results, total=len(results))
