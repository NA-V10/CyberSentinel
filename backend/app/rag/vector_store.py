"""
Qdrant vector store service for CyberSentinel AI.

Provides:
- Collection initialisation (1536 dims, cosine distance)
- Upsert incidents
- Similarity search with optional metadata filters
- Point lookup by ID
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from loguru import logger
from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as qdrant_models
from qdrant_client.http.exceptions import UnexpectedResponse

from backend.app.core.config import settings

# Embedding dimensionality for text-embedding-3-small
_EMBEDDING_DIM = 1536


class VectorStoreService:
    """Async interface to the Qdrant vector database.

    Parameters
    ----------
    url:
        Qdrant server URL.  Defaults to ``settings.QDRANT_URL``.
    api_key:
        Optional Qdrant API key.  Defaults to ``settings.QDRANT_API_KEY``.
    collection:
        Collection name to use.  Defaults to ``settings.QDRANT_COLLECTION``.
    """

    def __init__(
        self,
        url: str | None = None,
        api_key: str | None = None,
        collection: str | None = None,
    ) -> None:
        self._url = url or settings.QDRANT_URL
        self._api_key = api_key or settings.QDRANT_API_KEY
        self._collection = collection or settings.QDRANT_COLLECTION

        self._client = AsyncQdrantClient(
            url=self._url,
            api_key=self._api_key,
            timeout=30,
        )
        logger.info(
            "VectorStoreService initialised",
            url=self._url,
            collection=self._collection,
        )

    # ------------------------------------------------------------------
    # Collection management
    # ------------------------------------------------------------------

    async def initialize_collection(self) -> None:
        """Create the Qdrant collection if it does not already exist.

        The collection is configured with:
        - ``size``: 1536 (text-embedding-3-small output dimension)
        - ``distance``: Cosine similarity
        """
        try:
            existing = await self._client.get_collection(self._collection)
            logger.info(
                "Qdrant collection already exists, skipping creation",
                collection=self._collection,
                vectors_count=existing.vectors_count,
            )
            return
        except (UnexpectedResponse, Exception) as exc:
            # get_collection raises an error when the collection is absent
            if _is_not_found(exc):
                logger.info(
                    "Qdrant collection not found, creating",
                    collection=self._collection,
                )
            else:
                logger.error(
                    "Unexpected error checking Qdrant collection",
                    error=str(exc),
                )
                raise

        await self._client.create_collection(
            collection_name=self._collection,
            vectors_config=qdrant_models.VectorParams(
                size=_EMBEDDING_DIM,
                distance=qdrant_models.Distance.COSINE,
            ),
            optimizers_config=qdrant_models.OptimizersConfigDiff(
                indexing_threshold=10_000,
            ),
        )
        logger.info(
            "Qdrant collection created",
            collection=self._collection,
            dims=_EMBEDDING_DIM,
        )

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    async def upsert_incident(
        self,
        incident_id: str,
        embedding: List[float],
        payload: Dict[str, Any],
    ) -> None:
        """Insert or update an incident vector.

        Parameters
        ----------
        incident_id:
            Unique string identifier for the incident.  Used as the Qdrant
            point ID (stored as a named vector ID via the ``id`` field and
            also persisted in the payload for easy retrieval).
        embedding:
            Float vector of length 1536.
        payload:
            Arbitrary metadata dict (severity, attack_type, protocol, …).
        """
        if len(embedding) != _EMBEDDING_DIM:
            raise ValueError(
                f"Embedding must have {_EMBEDDING_DIM} dimensions, got {len(embedding)}."
            )

        # Persist the id in the payload so callers can recover it from search hits
        full_payload = {**payload, "incident_id": incident_id}

        point = qdrant_models.PointStruct(
            id=_to_qdrant_id(incident_id),
            vector=embedding,
            payload=full_payload,
        )

        await self._client.upsert(
            collection_name=self._collection,
            points=[point],
        )
        logger.debug(
            "Incident upserted into Qdrant",
            incident_id=incident_id,
            payload_keys=list(full_payload.keys()),
        )

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    async def search_similar(
        self,
        query_embedding: List[float],
        limit: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Search for the most similar incident vectors.

        Parameters
        ----------
        query_embedding:
            Query vector (1536-dimensional).
        limit:
            Maximum number of results.
        filters:
            Optional metadata filter dict.  Supported keys: ``severity``,
            ``attack_type``, ``protocol``.

        Returns
        -------
        list[dict]
            Each item contains ``id``, ``score``, and ``payload``.
        """
        qdrant_filter = _build_filter(filters) if filters else None

        hits = await self._client.search(
            collection_name=self._collection,
            query_vector=query_embedding,
            limit=limit,
            query_filter=qdrant_filter,
            with_payload=True,
            with_vectors=False,
        )

        results = [
            {
                "id": hit.payload.get("incident_id", str(hit.id)),
                "score": hit.score,
                "payload": hit.payload,
            }
            for hit in hits
        ]
        logger.debug(
            "Similarity search complete",
            results=len(results),
            limit=limit,
        )
        return results

    async def get_by_id(self, point_id: str) -> Dict[str, Any]:
        """Retrieve a single point by its incident ID string.

        Parameters
        ----------
        point_id:
            The incident ID that was used when upserting.

        Returns
        -------
        dict
            The point payload (empty dict if not found).
        """
        qdrant_id = _to_qdrant_id(point_id)
        points = await self._client.retrieve(
            collection_name=self._collection,
            ids=[qdrant_id],
            with_payload=True,
            with_vectors=False,
        )
        if not points:
            logger.warning("Point not found in Qdrant", point_id=point_id)
            return {}

        return {
            "id": points[0].payload.get("incident_id", str(points[0].id)),
            "payload": points[0].payload,
        }

    # ------------------------------------------------------------------
    # Graceful shutdown
    # ------------------------------------------------------------------

    async def close(self) -> None:
        """Release the underlying HTTP client."""
        await self._client.close()
        logger.info("VectorStoreService closed.")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _to_qdrant_id(incident_id: str) -> int | str:
    """Convert an incident ID string to a Qdrant-compatible point ID.

    Qdrant accepts unsigned 64-bit integers or UUIDs.  If the string is a
    valid UUID it is used as-is; otherwise a stable integer hash is derived.
    """
    try:
        uuid_val = UUID(incident_id)
        return str(uuid_val)
    except ValueError:
        pass

    # Derive a stable unsigned 64-bit integer from the string
    return abs(hash(incident_id)) % (2**63)


def _build_filter(filters: Dict[str, Any]) -> qdrant_models.Filter:
    """Build a Qdrant :class:`~qdrant_client.http.models.Filter` from a plain dict.

    Supported filter keys
    ----------------------
    ``severity``
        Match incidents with this exact severity label.
    ``attack_type``
        Match incidents with this attack type.
    ``protocol``
        Match incidents using this protocol.
    """
    must_conditions: List[qdrant_models.FieldCondition] = []

    _SUPPORTED = ("severity", "attack_type", "protocol")

    for key in _SUPPORTED:
        value = filters.get(key)
        if value is not None:
            must_conditions.append(
                qdrant_models.FieldCondition(
                    key=key,
                    match=qdrant_models.MatchValue(value=value),
                )
            )

    if not must_conditions:
        return qdrant_models.Filter()

    return qdrant_models.Filter(must=must_conditions)


def _is_not_found(exc: Exception) -> bool:
    """Heuristic to detect a 404 / collection-not-found error from Qdrant."""
    msg = str(exc).lower()
    return (
        "not found" in msg
        or "404" in msg
        or "doesn't exist" in msg
        or "does not exist" in msg
    )
