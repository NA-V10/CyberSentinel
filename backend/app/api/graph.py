"""FastAPI router: Graph visualisation endpoints.

Routes
------
GET  /graph/incident/{id}   — Graph data for a specific incident (Neo4j subgraph)
GET  /graph/attack/{type}   — All incidents + assets for a given attack type
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, status
from loguru import logger
from pydantic import BaseModel, Field

from backend.app.auth.clerk import get_current_user
from backend.app.graph.neo4j_service import GraphService

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class GraphNode(BaseModel):
    id: str
    label: str
    type: str  # incident | attack_type | asset | severity | protocol | mitigation
    properties: Dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    source: str
    target: str
    type: str
    label: Optional[str] = None


class IncidentGraphResponse(BaseModel):
    incident_id: str
    nodes: List[Dict[str, Any]] = Field(default_factory=list)
    edges: List[Dict[str, Any]] = Field(default_factory=list)
    attack_type: Optional[str] = None
    affected_assets: List[str] = Field(default_factory=list)
    similar_incidents: List[str] = Field(default_factory=list)
    mitigations: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AttackTypeGraphResponse(BaseModel):
    attack_type: str
    incident_count: int
    nodes: List[Dict[str, Any]] = Field(default_factory=list)
    edges: List[Dict[str, Any]] = Field(default_factory=list)
    mitigations: List[str] = Field(default_factory=list)
    related_incidents: List[Dict[str, Any]] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# GET /graph/incident/{incident_id}
# ---------------------------------------------------------------------------


@router.get(
    "/incident/{incident_id}",
    response_model=IncidentGraphResponse,
    summary="Retrieve Neo4j subgraph for a specific incident",
)
async def get_incident_graph(
    incident_id: str = Path(..., description="Incident UUID"),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> IncidentGraphResponse:
    """Return nodes and edges of the Neo4j knowledge graph for one incident.

    The subgraph includes:
    - The Incident node
    - Connected AttackType, Asset (source/dest IPs), Protocol, Severity nodes
    - AttackType → Mitigation relationships
    - SimilarIncident links (up to 5)

    **Authentication**: Bearer JWT required (analyst / manager / admin).
    """
    logger.info(
        "get_incident_graph: request",
        incident_id=incident_id,
        user_id=current_user["user_id"],
    )

    graph_svc = GraphService()
    try:
        raw = await graph_svc.get_incident_graph(incident_id)
    except Exception as exc:
        logger.error("get_incident_graph: neo4j error", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Graph service error: {str(exc)}",
        ) from exc
    finally:
        await graph_svc.close()

    if not raw:
        # Return an empty graph rather than 404 — the incident may exist in
        # Postgres but not yet have a graph node (e.g. not yet indexed).
        return IncidentGraphResponse(incident_id=incident_id)

    # ---- Build frontend-ready nodes & edges ----
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []
    seen_node_ids: set = set()

    def _add_node(node_id: str, label: str, node_type: str, props: dict = None) -> None:
        if node_id not in seen_node_ids:
            seen_node_ids.add(node_id)
            nodes.append(
                {
                    "id": node_id,
                    "label": label,
                    "type": node_type,
                    "properties": props or {},
                }
            )

    def _add_edge(source: str, target: str, rel_type: str) -> None:
        edges.append({"source": source, "target": target, "type": rel_type, "label": rel_type})

    # Core incident node
    _add_node(incident_id, f"Incident {incident_id[:8]}", "incident", {"id": incident_id})

    # Attack type
    attack_type: Optional[str] = raw.get("attack_type")
    if attack_type:
        at_id = f"at:{attack_type}"
        _add_node(at_id, attack_type, "attack_type")
        _add_edge(incident_id, at_id, "INCIDENT_OF_TYPE")

    # Affected assets (IPs)
    affected_assets: List[str] = []
    for asset in raw.get("affected_assets", []):
        ip = asset.get("ip") or str(asset)
        role = asset.get("role", "asset")
        asset_id = f"asset:{ip}"
        _add_node(asset_id, ip, "asset", {"ip": ip, "role": role})
        rel = "SOURCE_IP" if role == "source" else "DESTINATION_IP"
        _add_edge(incident_id, asset_id, rel)
        affected_assets.append(ip)

    # Severity
    severity = raw.get("severity")
    if severity:
        sev_id = f"sev:{severity}"
        _add_node(sev_id, severity, "severity")
        _add_edge(incident_id, sev_id, "HAS_SEVERITY")

    # Protocol
    protocol = raw.get("protocol")
    if protocol:
        proto_id = f"proto:{protocol}"
        _add_node(proto_id, protocol, "protocol")
        _add_edge(incident_id, proto_id, "USES_PROTOCOL")

    # Mitigations
    mitigations: List[str] = raw.get("mitigations", [])
    for i, mitigation in enumerate(mitigations):
        mit_id = f"mit:{attack_type or 'unknown'}:{i}"
        _add_node(mit_id, mitigation[:50], "mitigation", {"text": mitigation})
        if attack_type:
            _add_edge(f"at:{attack_type}", mit_id, "HAS_MITIGATION")
        else:
            _add_edge(incident_id, mit_id, "HAS_MITIGATION")

    # Similar incidents
    similar_ids: List[str] = raw.get("similar_incidents", [])
    for sim_id in similar_ids[:5]:
        sim_node_id = str(sim_id)
        _add_node(sim_node_id, f"Similar {sim_node_id[:8]}", "incident", {"id": sim_node_id})
        _add_edge(incident_id, sim_node_id, "SIMILAR_TO")

    return IncidentGraphResponse(
        incident_id=incident_id,
        nodes=nodes,
        edges=edges,
        attack_type=attack_type,
        affected_assets=affected_assets,
        similar_incidents=[str(s) for s in similar_ids],
        mitigations=mitigations,
        metadata={
            "severity": severity,
            "protocol": protocol,
            "node_count": len(nodes),
            "edge_count": len(edges),
        },
    )


# ---------------------------------------------------------------------------
# GET /graph/attack/{attack_type}
# ---------------------------------------------------------------------------


@router.get(
    "/attack/{attack_type}",
    response_model=AttackTypeGraphResponse,
    summary="Get graph data for all incidents of a given attack type",
)
async def get_attack_type_graph(
    attack_type: str = Path(..., description="Attack type, e.g. brute_force, ddos, phishing"),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> AttackTypeGraphResponse:
    """Return a graph centered on an AttackType node — useful for exploring
    all incidents of a particular category and their shared mitigations.

    **Authentication**: Bearer JWT required.
    """
    logger.info(
        "get_attack_type_graph: request",
        attack_type=attack_type,
        user_id=current_user["user_id"],
    )

    graph_svc = GraphService()
    try:
        related = await graph_svc.find_related_incidents(attack_type=attack_type, severity=None)
        mitigations = await graph_svc.get_mitigations_for_attack(attack_type)
    except Exception as exc:
        logger.error("get_attack_type_graph: neo4j error", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Graph service error: {str(exc)}",
        ) from exc
    finally:
        await graph_svc.close()

    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []
    seen: set = set()

    def _n(nid: str, label: str, ntype: str, props: dict = None) -> None:
        if nid not in seen:
            seen.add(nid)
            nodes.append({"id": nid, "label": label, "type": ntype, "properties": props or {}})

    def _e(src: str, tgt: str, rel: str) -> None:
        edges.append({"source": src, "target": tgt, "type": rel, "label": rel})

    at_id = f"at:{attack_type}"
    _n(at_id, attack_type, "attack_type")

    for i, mit in enumerate(mitigations):
        mit_id = f"mit:{attack_type}:{i}"
        _n(mit_id, mit[:50], "mitigation", {"text": mit})
        _e(at_id, mit_id, "HAS_MITIGATION")

    for inc in related[:20]:
        inc_id = str(inc.get("id") or inc.get("incident_id", f"inc:{i}"))
        _n(inc_id, f"Incident {inc_id[:8]}", "incident", inc)
        _e(inc_id, at_id, "INCIDENT_OF_TYPE")

    return AttackTypeGraphResponse(
        attack_type=attack_type,
        incident_count=len(related),
        nodes=nodes,
        edges=edges,
        mitigations=mitigations,
        related_incidents=related[:20],
    )
