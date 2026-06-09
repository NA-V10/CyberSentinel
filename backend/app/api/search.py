"""FastAPI router: Search and graph visualisation endpoints.

Routes
------
POST /search/similar          — Hybrid similarity search over incidents
GET  /graph/incident/{id}     — Graph data for a specific incident
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.clerk import get_current_user
from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.graph.neo4j_service import GraphService
from backend.app.rag.embeddings import EmbeddingService
from backend.app.rag.retriever import HybridRetriever
from backend.app.rag.vector_store import VectorStoreService

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class SimilarSearchRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=3,
        description="Free-text query for similarity search",
    )
    attack_type: Optional[str] = Field(
        None, description="Filter by attack type (e.g. malware, ddos)"
    )
    severity: Optional[str] = Field(
        None, description="Filter by severity: low|medium|high|critical"
    )
    protocol: Optional[str] = Field(None, description="Filter by network protocol")
    limit: int = Field(default=10, ge=1, le=50, description="Max results to return")


class SimilarIncidentResult(BaseModel):
    id: str
    score: float
    attack_type: Optional[str] = None
    severity: Optional[str] = None
    summary: Optional[str] = None
    source_ip: Optional[str] = None
    dest_ip: Optional[str] = None
    protocol: Optional[str] = None
    created_at: Optional[str] = None
    source: Optional[str] = None  # "semantic" | "keyword" | "hybrid"


class SimilarSearchResponse(BaseModel):
    results: List[SimilarIncidentResult]
    total: int
    query: str
    filters: Dict[str, Any] = Field(default_factory=dict)


class GraphNode(BaseModel):
    id: str
    label: str
    type: str
    properties: Dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    source: str
    target: str
    type: str
    properties: Dict[str, Any] = Field(default_factory=dict)


class GraphResponse(BaseModel):
    incident_id: str
    nodes: List[Dict[str, Any]] = Field(default_factory=list)
    edges: List[Dict[str, Any]] = Field(default_factory=list)
    attack_type: Optional[str] = None
    affected_assets: List[Dict[str, Any]] = Field(default_factory=list)
    similar_incidents: List[str] = Field(default_factory=list)
    mitigations: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# POST /search/similar
# ---------------------------------------------------------------------------


@router.post(
    "/similar",
    response_model=SimilarSearchResponse,
    summary="Hybrid similarity search over historical incidents",
)
async def search_similar(
    request: SimilarSearchRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SimilarSearchResponse:
    """Run a hybrid (semantic + keyword) search and return ranked incidents.

    **Authentication**: Bearer JWT required (any role).
    """
    logger.info(
        "search_similar: request",
        query=request.query[:80],
        user_id=current_user["user_id"],
    )

    # Build metadata filters
    filters: Dict[str, Any] = {}
    if request.attack_type:
        filters["attack_type"] = request.attack_type.lower()
    if request.severity:
        filters["severity"] = request.severity.lower()
    if request.protocol:
        filters["protocol"] = request.protocol.upper()

    embedding_svc = EmbeddingService(api_key=settings.OPENAI_API_KEY)
    vector_store = VectorStoreService()
    retriever = HybridRetriever(
        embedding_service=embedding_svc,
        vector_store=vector_store,
        db_session=db,
    )

    try:
        context = await retriever.retrieve_with_context(
            query=request.query,
            filters=filters or None,
        )
        raw_results: List[Dict[str, Any]] = context.get("results", [])
    except Exception as exc:
        logger.error("search_similar: retriever error", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Search service error: {str(exc)}",
        ) from exc

    # Shape results
    results: List[SimilarIncidentResult] = []
    for item in raw_results[: request.limit]:
        payload: dict = item.get("payload") or {}
        results.append(
            SimilarIncidentResult(
                id=str(item.get("id", "")),
                score=round(float(item.get("score", 0.0)), 4),
                attack_type=payload.get("attack_type"),
                severity=payload.get("severity"),
                summary=(
                    payload.get("description")
                    or payload.get("raw_text")
                    or payload.get("title")
                    or ""
                )[:300],
                source_ip=payload.get("source_ip"),
                dest_ip=payload.get("dest_ip"),
                protocol=payload.get("protocol"),
                created_at=str(payload.get("created_at") or ""),
                source=item.get("source"),
            )
        )

    return SimilarSearchResponse(
        results=results,
        total=len(results),
        query=request.query,
        filters=filters,
    )


# ---------------------------------------------------------------------------
# GET /graph/incident/{incident_id}
# ---------------------------------------------------------------------------


@router.get(
    "/incident/{incident_id}",
    response_model=GraphResponse,
    summary="Retrieve graph data for an incident",
)
async def get_incident_graph(
    incident_id: str = Path(..., description="Incident UUID"),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> GraphResponse:
    """Return the Neo4j subgraph for a given incident (nodes + relationships).

    The graph includes:
    - The Incident node
    - AttackType, Asset, Protocol, Severity connected nodes
    - Known Mitigation nodes
    - Up to 5 similar Incident nodes sharing the same attack type

    **Authentication**: Bearer JWT required (any role).
    """
    logger.info(
        "get_incident_graph: request",
        incident_id=incident_id,
        user_id=current_user["user_id"],
    )

    graph_svc = GraphService()
    try:
        raw_graph = await graph_svc.get_incident_graph(incident_id=incident_id)
    except Exception as exc:
        logger.error("get_incident_graph: Neo4j error", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Graph service error: {str(exc)}",
        ) from exc
    finally:
        await graph_svc.close()

    if not raw_graph or (not raw_graph.get("incident") and not raw_graph.get("nodes")):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No graph data found for incident '{incident_id}'.",
        )

    # Build a simple nodes/edges representation for frontend visualisation
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []

    # Central incident node
    incident_props = raw_graph.get("incident") or {}
    nodes.append(
        {"id": incident_id, "label": incident_id[:8], "type": "Incident", "properties": incident_props}
    )

    # Attack type node
    attack_type = raw_graph.get("attack_type")
    if attack_type:
        at_id = f"at_{attack_type}"
        nodes.append({"id": at_id, "label": attack_type, "type": "AttackType", "properties": {}})
        edges.append({"source": incident_id, "target": at_id, "type": "INCIDENT_OF_TYPE", "properties": {}})

    # Asset nodes
    for asset in raw_graph.get("affected_assets") or []:
        ip = asset.get("ip")
        if ip:
            asset_id = f"asset_{ip}"
            nodes.append({"id": asset_id, "label": ip, "type": "Asset", "properties": {"ip": ip}})
            edges.append(
                {
                    "source": incident_id,
                    "target": asset_id,
                    "type": "TARGETS_ASSET",
                    "properties": {"role": asset.get("role", "")},
                }
            )

    # Similar incident nodes
    for sim_id in (raw_graph.get("similar_incidents") or [])[:5]:
        if sim_id:
            nodes.append({"id": str(sim_id), "label": str(sim_id)[:8], "type": "Incident", "properties": {}})
            edges.append({"source": incident_id, "target": str(sim_id), "type": "SIMILAR_TO", "properties": {}})

    return GraphResponse(
        incident_id=incident_id,
        nodes=nodes,
        edges=edges,
        attack_type=attack_type,
        affected_assets=raw_graph.get("affected_assets") or [],
        similar_incidents=[str(s) for s in (raw_graph.get("similar_incidents") or []) if s],
        mitigations=raw_graph.get("mitigations") or [],
    )
