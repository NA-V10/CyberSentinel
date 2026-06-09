"""Similarity Retrieval Agent for CyberSentinel AI.

Runs hybrid RAG (vector + keyword) search and expands the top result
through the Neo4j knowledge graph.

Updates state keys:
    ``similar_incidents``, ``graph_context``, ``rag_context``, ``citations``

Sends WebSocket status:
    "Searching similar incidents...", "Expanding graph context..."
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from loguru import logger

from backend.app.agents.state import AgentState
from backend.app.core.config import settings
from backend.app.graph.neo4j_service import GraphService
from backend.app.rag.embeddings import EmbeddingService
from backend.app.rag.rag_pipeline import RAGPipeline
from backend.app.rag.retriever import HybridRetriever
from backend.app.rag.vector_store import VectorStoreService


async def _send_ws(state: AgentState, message: str) -> None:
    cb = state.get("ws_callback")
    if cb is not None:
        try:
            if asyncio.iscoroutinefunction(cb):
                await cb(message)
            else:
                cb(message)
        except Exception as exc:
            logger.warning("WS callback failed", error=str(exc))


def _format_similar_incidents(vector_results: List[Dict[str, Any]]) -> List[dict]:
    """Convert raw retrieval results into the schema expected by the state."""
    incidents = []
    for item in vector_results:
        payload: dict = item.get("payload") or {}
        incidents.append(
            {
                "id": item.get("id", "unknown"),
                "score": round(item.get("score", 0.0), 4),
                "attack_type": payload.get("attack_type"),
                "severity": payload.get("severity"),
                "summary": (
                    payload.get("description")
                    or payload.get("raw_text")
                    or payload.get("title")
                    or ""
                )[:300],
                "source_ip": payload.get("source_ip"),
                "dest_ip": payload.get("dest_ip"),
                "created_at": payload.get("created_at"),
            }
        )
    return incidents


async def retrieval_agent(
    state: AgentState,
    db_session=None,  # SQLAlchemy AsyncSession injected by workflow
) -> Dict[str, Any]:
    """LangGraph node: hybrid RAG retrieval + graph context expansion.

    Parameters
    ----------
    state:
        Current agent state.
    db_session:
        Optional SQLAlchemy ``AsyncSession``.  When omitted the keyword search
        falls back gracefully (empty results) so the agent degrades nicely in
        unit tests or when the DB is unavailable.

    Returns
    -------
    dict
        Partial state update with retrieval results.
    """
    await _send_ws(state, "Searching similar incidents...")
    logger.info("RetrievalAgent started")

    query_text: str = state.get("incident_text", "")
    threat_class: Optional[str] = state.get("threat_class")
    severity: Optional[str] = state.get("severity")

    # Build optional metadata filters from classified context
    filters: Dict[str, Any] = {}
    if threat_class:
        filters["attack_type"] = threat_class
    if severity:
        filters["severity"] = severity.lower()

    # -----------------------------------------------------------------------
    # Initialise services (they are lightweight wrappers around HTTP clients)
    # -----------------------------------------------------------------------
    embedding_service = EmbeddingService(api_key=settings.OPENAI_API_KEY)
    vector_store = VectorStoreService(
        url=settings.QDRANT_URL,
        api_key=settings.QDRANT_API_KEY,
        collection=settings.QDRANT_COLLECTION,
    )

    similar_incidents: List[dict] = []
    citations: List[dict] = []
    rag_context: str = ""
    graph_ctx: dict = {}

    try:
        # If we have no DB session, fall back to semantic-only retrieval
        if db_session is not None:
            retriever = HybridRetriever(
                embedding_service=embedding_service,
                vector_store=vector_store,
                db_session=db_session,
            )
        else:
            # Build a minimal retriever that only does semantic search
            from backend.app.rag.retriever import HybridRetriever as _HR

            class _SemanticOnlyRetriever(_HR):
                async def keyword_search(self, query, filters=None, limit=5):
                    return []

            retriever = _SemanticOnlyRetriever(
                embedding_service=embedding_service,
                vector_store=vector_store,
                db_session=None,  # type: ignore[arg-type]
            )

        graph_service = GraphService()

        pipeline = RAGPipeline(
            retriever=retriever,
            graph_service=graph_service,
            embedding_service=embedding_service,
        )

        # Run the full RAG pipeline
        result = await pipeline.run(query=query_text, filters=filters or None)

        vector_results: List[Dict[str, Any]] = result.get("vector_results", [])
        graph_ctx = result.get("graph_context") or {}
        rag_context = result.get("formatted_context") or ""
        citations = result.get("citations") or []
        similar_incidents = _format_similar_incidents(vector_results)

        logger.info(
            "RetrievalAgent: hybrid search complete",
            hits=len(similar_incidents),
            citations=len(citations),
        )

        await _send_ws(state, "Expanding graph context...")

        await graph_service.close()

    except Exception as exc:
        logger.error("RetrievalAgent failed", error=str(exc))
        # Non-fatal: workflow continues with empty retrieval context
        similar_incidents = []
        graph_ctx = {}
        rag_context = ""
        citations = []

    await _send_ws(
        state,
        f"Found {len(similar_incidents)} similar incident(s).",
    )

    return {
        "similar_incidents": similar_incidents,
        "graph_context": graph_ctx,
        "rag_context": rag_context,
        "citations": citations,
    }
