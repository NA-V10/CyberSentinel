"""
Hybrid RAG retriever for CyberSentinel AI.

Combines:
- Semantic search via Qdrant vector similarity
- Keyword search via PostgreSQL full-text search (to_tsvector / to_tsquery)
- Score-weighted fusion: 0.7 × semantic + 0.3 × keyword
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.rag.embeddings import EmbeddingService
from backend.app.rag.vector_store import VectorStoreService


# Fusion weights
_SEMANTIC_WEIGHT = 0.7
_KEYWORD_WEIGHT = 0.3


class HybridRetriever:
    """Hybrid retrieval combining semantic and keyword search.

    Parameters
    ----------
    embedding_service:
        :class:`EmbeddingService` instance for generating query embeddings.
    vector_store:
        :class:`VectorStoreService` instance for vector similarity search.
    db_session:
        Async SQLAlchemy session connected to the PostgreSQL incidents table.
    """

    def __init__(
        self,
        embedding_service: EmbeddingService,
        vector_store: VectorStoreService,
        db_session: AsyncSession,
    ) -> None:
        self._embeddings = embedding_service
        self._vector_store = vector_store
        self._db = db_session

    # ------------------------------------------------------------------
    # Semantic search
    # ------------------------------------------------------------------

    async def semantic_search(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Embed *query* and search the Qdrant collection.

        Parameters
        ----------
        query:
            Free-text search query.
        filters:
            Optional metadata filters (severity, attack_type, protocol).
        limit:
            Maximum number of results.

        Returns
        -------
        list[dict]
            Each dict: ``{id, score, payload, source}``.
        """
        query_vector = await self._embeddings.embed_text(query)
        raw = await self._vector_store.search_similar(
            query_embedding=query_vector,
            limit=limit,
            filters=filters,
        )

        results = []
        for item in raw:
            results.append(
                {
                    "id": item["id"],
                    "score": item["score"],
                    "payload": item["payload"],
                    "source": "semantic",
                }
            )

        logger.debug("Semantic search", query_chars=len(query), hits=len(results))
        return results

    # ------------------------------------------------------------------
    # Keyword search
    # ------------------------------------------------------------------

    async def keyword_search(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Full-text search on the PostgreSQL ``incidents`` table.

        Uses ``to_tsvector('english', ...)`` and ``plainto_tsquery`` so that
        stop words and stemming are handled automatically.

        Parameters
        ----------
        query:
            Raw search terms.
        filters:
            Optional filters: ``severity``, ``attack_type``, ``protocol``.
        limit:
            Maximum rows to return.

        Returns
        -------
        list[dict]
            Each dict: ``{id, score, payload, source}``.
        """
        # Build parameterised WHERE clause additions
        where_clauses = [
            "to_tsvector('english', COALESCE(raw_text, '') || ' ' || COALESCE(label, '')) "
            "@@ plainto_tsquery('english', :query)"
        ]
        params: Dict[str, Any] = {"query": query, "limit": limit}

        if filters:
            if filters.get("severity"):
                where_clauses.append("severity = :severity")
                params["severity"] = filters["severity"]
            if filters.get("attack_type"):
                where_clauses.append("attack_type = :attack_type")
                params["attack_type"] = filters["attack_type"]
            if filters.get("protocol"):
                where_clauses.append("protocol = :protocol")
                params["protocol"] = filters["protocol"]

        where_sql = " AND ".join(where_clauses)

        sql = text(
            f"""
            SELECT
                id::text AS incident_id,
                label,
                raw_text,
                severity,
                attack_type,
                protocol,
                source_ip,
                dest_ip,
                created_at,
                ts_rank(
                    to_tsvector('english', COALESCE(raw_text, '') || ' ' || COALESCE(label, '')),
                    plainto_tsquery('english', :query)
                ) AS rank
            FROM incidents
            WHERE {where_sql}
            ORDER BY rank DESC
            LIMIT :limit
            """
        )

        try:
            result = await self._db.execute(sql, params)
            rows = result.mappings().all()
        except Exception as exc:
            logger.error("Keyword search failed", error=str(exc))
            return []

        results = []
        for row in rows:
            payload = {
                "incident_id": row["incident_id"],
                "title": row.get("label"),
                "description": row.get("raw_text"),
                "severity": row.get("severity"),
                "attack_type": row.get("attack_type"),
                "protocol": row.get("protocol"),
                "source_ip": row.get("source_ip"),
                "dest_ip": row.get("dest_ip"),
                "created_at": str(row["created_at"]) if row.get("created_at") else None,
            }
            results.append(
                {
                    "id": row["incident_id"],
                    "score": float(row.get("rank") or 0.0),
                    "payload": payload,
                    "source": "keyword",
                }
            )

        logger.debug("Keyword search", query_chars=len(query), hits=len(results))
        return results

    # ------------------------------------------------------------------
    # Hybrid search
    # ------------------------------------------------------------------

    async def hybrid_search(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Combine semantic and keyword results with weighted score fusion.

        Algorithm
        ---------
        1. Run semantic search (top ``limit``) and keyword search (top ``limit``).
        2. Deduplicate by ``incident_id``.
        3. For hits appearing in both result sets, compute:
           ``fused = 0.7 × semantic_score + 0.3 × keyword_score``
           (scores from a single source receive the full weight for that source).
        4. Sort by ``fused_score`` descending and return top ``limit``.

        Returns
        -------
        list[dict]
            Each dict: ``{id, score, semantic_score, keyword_score, payload, source}``.
        """
        semantic_results, keyword_results = await _run_parallel(
            self.semantic_search(query, filters, limit),
            self.keyword_search(query, filters, limit),
        )

        # --- normalise keyword scores to [0, 1] ---
        keyword_results = _normalise_scores(keyword_results)

        # --- fuse by incident id ---
        seen: Dict[str, Dict[str, Any]] = {}

        for item in semantic_results:
            inc_id = item["id"]
            seen[inc_id] = {
                "id": inc_id,
                "semantic_score": item["score"],
                "keyword_score": 0.0,
                "payload": item["payload"],
                "source": "semantic",
            }

        for item in keyword_results:
            inc_id = item["id"]
            if inc_id in seen:
                seen[inc_id]["keyword_score"] = item["score"]
                seen[inc_id]["source"] = "hybrid"
            else:
                seen[inc_id] = {
                    "id": inc_id,
                    "semantic_score": 0.0,
                    "keyword_score": item["score"],
                    "payload": item["payload"],
                    "source": "keyword",
                }

        # --- compute fused score ---
        fused: List[Dict[str, Any]] = []
        for entry in seen.values():
            fused_score = (
                _SEMANTIC_WEIGHT * entry["semantic_score"]
                + _KEYWORD_WEIGHT * entry["keyword_score"]
            )
            fused.append({**entry, "score": round(fused_score, 6)})

        fused.sort(key=lambda x: x["score"], reverse=True)
        top = fused[:limit]

        logger.info(
            "Hybrid search complete",
            query_chars=len(query),
            semantic_hits=len(semantic_results),
            keyword_hits=len(keyword_results),
            fused_hits=len(top),
        )
        return top

    # ------------------------------------------------------------------
    # High-level retrieval with context
    # ------------------------------------------------------------------

    async def retrieve_with_context(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Run hybrid search and package results with retrieval metadata.

        Returns
        -------
        dict
            Keys: ``results``, ``total``, ``query``, ``filters``.
        """
        results = await self.hybrid_search(query, filters)

        return {
            "results": results,
            "total": len(results),
            "query": query,
            "filters": filters or {},
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _run_parallel(coro1, coro2):
    """Run two coroutines concurrently and return both results."""
    import asyncio
    result1, result2 = await asyncio.gather(coro1, coro2, return_exceptions=False)
    return result1, result2


def _normalise_scores(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Min-max normalise the ``score`` field of a list of result dicts."""
    if not results:
        return results

    scores = [r["score"] for r in results]
    min_s = min(scores)
    max_s = max(scores)
    rng = max_s - min_s

    if rng == 0:
        return [{**r, "score": 1.0 if max_s > 0 else 0.0} for r in results]

    return [{**r, "score": (r["score"] - min_s) / rng} for r in results]
