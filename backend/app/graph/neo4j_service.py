"""
Neo4j graph database service for CyberSentinel AI.

Node labels
-----------
- Incident
- AttackType
- Asset       (represents a network asset, keyed by IP address)
- Protocol
- Severity
- Mitigation

Relationship types
------------------
- INCIDENT_OF_TYPE   (Incident)-[]->(AttackType)
- TARGETS_ASSET      (Incident)-[]->(Asset)
- USES_PROTOCOL      (Incident)-[]->(Protocol)
- HAS_SEVERITY       (Incident)-[]->(Severity)
- MITIGATED_BY       (AttackType)-[]->(Mitigation)
- SIMILAR_TO         (Incident)-[score]->(Incident)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from loguru import logger
from neo4j import AsyncGraphDatabase, AsyncDriver


from backend.app.core.config import settings


class GraphService:
    """Async service layer for Neo4j graph operations.

    Parameters
    ----------
    uri:
        Bolt/neo4j URI.  Defaults to ``settings.NEO4J_URI``.
    user:
        Neo4j username.  Defaults to ``settings.NEO4J_USER``.
    password:
        Neo4j password.  Defaults to ``settings.NEO4J_PASSWORD``.
    """

    def __init__(
        self,
        uri: str | None = None,
        user: str | None = None,
        password: str | None = None,
    ) -> None:
        self._uri = uri or settings.NEO4J_URI
        self._user = user or settings.NEO4J_USER
        self._password = password or settings.NEO4J_PASSWORD

        self._driver: AsyncDriver = AsyncGraphDatabase.driver(
            self._uri,
            auth=(self._user, self._password),
        )
        logger.info("GraphService initialised", uri=self._uri)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def close(self) -> None:
        """Close the Neo4j driver and release connections."""
        await self._driver.close()
        logger.info("GraphService closed.")

    # ------------------------------------------------------------------
    # Incident node
    # ------------------------------------------------------------------

    async def create_incident_node(self, incident: Dict[str, Any]) -> None:
        """Create or update an Incident node.

        Parameters
        ----------
        incident:
            Dict with at minimum ``incident_id``.  All other keys are stored
            as node properties.
        """
        incident_id = incident.get("incident_id") or incident.get("id")
        if not incident_id:
            raise ValueError("incident dict must contain 'incident_id' or 'id'.")

        props = {k: v for k, v in incident.items() if v is not None}
        props["incident_id"] = incident_id  # ensure canonical key

        async with self._driver.session() as session:
            await session.execute_write(_create_incident_node_tx, props)

        logger.debug("Incident node created/updated", incident_id=incident_id)

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------

    async def create_relationships(
        self,
        incident_id: str,
        attack_type: str,
        source_ip: str,
        dest_ip: str,
        severity: str,
        protocol: str,
    ) -> None:
        """Create supporting nodes and relationships for an incident.

        Creates (or MERGE-upserts) the following graph structure::

            (Incident)-[:INCIDENT_OF_TYPE]->(AttackType)
            (Incident)-[:TARGETS_ASSET {role:'source'}]->(Asset{ip:source_ip})
            (Incident)-[:TARGETS_ASSET {role:'destination'}]->(Asset{ip:dest_ip})
            (Incident)-[:USES_PROTOCOL]->(Protocol)
            (Incident)-[:HAS_SEVERITY]->(Severity)
        """
        params = {
            "incident_id": incident_id,
            "attack_type": attack_type,
            "source_ip": source_ip,
            "dest_ip": dest_ip,
            "severity": severity,
            "protocol": protocol,
        }
        async with self._driver.session() as session:
            await session.execute_write(_create_relationships_tx, params)

        logger.debug(
            "Incident relationships created",
            incident_id=incident_id,
            attack_type=attack_type,
        )

    # ------------------------------------------------------------------
    # Graph retrieval
    # ------------------------------------------------------------------

    async def get_incident_graph(self, incident_id: str) -> Dict[str, Any]:
        """Return a graph snapshot of an incident for visualisation.

        Returns
        -------
        dict
            Keys: ``nodes``, ``relationships``, ``attack_type``,
            ``affected_assets``, ``similar_incidents``, ``mitigations``.
        """
        async with self._driver.session() as session:
            result = await session.execute_read(_get_incident_graph_tx, incident_id)

        logger.debug("Incident graph fetched", incident_id=incident_id)
        return result

    async def find_related_incidents(
        self,
        attack_type: str,
        severity: str,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Find incidents sharing the same attack type and severity.

        Returns
        -------
        list[dict]
            Each dict contains the Incident node properties.
        """
        params = {
            "attack_type": attack_type,
            "severity": severity,
            "limit": limit,
        }
        async with self._driver.session() as session:
            results = await session.execute_read(_find_related_incidents_tx, params)

        logger.debug(
            "Related incidents found",
            attack_type=attack_type,
            severity=severity,
            count=len(results),
        )
        return results

    # ------------------------------------------------------------------
    # Mitigations
    # ------------------------------------------------------------------

    async def get_mitigations_for_attack(self, attack_type: str) -> List[str]:
        """Return known mitigations for a given attack type.

        Returns
        -------
        list[str]
            Mitigation description strings.
        """
        async with self._driver.session() as session:
            results = await session.execute_read(
                _get_mitigations_tx, attack_type
            )

        logger.debug(
            "Mitigations fetched",
            attack_type=attack_type,
            count=len(results),
        )
        return results

    async def store_mitigation(self, attack_type: str, mitigation: str) -> None:
        """Persist a mitigation linked to an attack type.

        Parameters
        ----------
        attack_type:
            The canonical attack type label (e.g. ``"SQL Injection"``).
        mitigation:
            Human-readable mitigation description.
        """
        params = {"attack_type": attack_type, "mitigation": mitigation}
        async with self._driver.session() as session:
            await session.execute_write(_store_mitigation_tx, params)

        logger.debug(
            "Mitigation stored",
            attack_type=attack_type,
            mitigation=mitigation[:80],
        )

    # ------------------------------------------------------------------
    # Graph RAG context
    # ------------------------------------------------------------------

    async def graph_rag_context(
        self,
        incident_text: str,
        attack_type: str,
    ) -> Dict[str, Any]:
        """Gather all graph-derived context useful for RAG.

        Combines:
        - Related incidents sharing the attack type
        - Known mitigations for the attack type

        Parameters
        ----------
        incident_text:
            The raw incident description (used for logging / future NLP).
        attack_type:
            Detected / classified attack type.

        Returns
        -------
        dict
            Keys: ``attack_type``, ``related_incidents``, ``mitigations``.
        """
        import asyncio

        related_coro = self.find_related_incidents(attack_type, severity="")
        mitigations_coro = self.get_mitigations_for_attack(attack_type)

        related, mitigations = await asyncio.gather(related_coro, mitigations_coro)

        context = {
            "attack_type": attack_type,
            "related_incidents": related,
            "mitigations": mitigations,
        }
        logger.info(
            "Graph RAG context assembled",
            attack_type=attack_type,
            related_count=len(related),
            mitigation_count=len(mitigations),
        )
        return context


# ---------------------------------------------------------------------------
# Transaction functions (passed to session.execute_read / execute_write)
# ---------------------------------------------------------------------------


async def _create_incident_node_tx(tx, props: Dict[str, Any]) -> None:
    cypher = """
    MERGE (i:Incident {incident_id: $incident_id})
    SET i += $props
    """
    await tx.run(cypher, incident_id=props["incident_id"], props=props)


async def _create_relationships_tx(tx, params: Dict[str, Any]) -> None:
    cypher = """
    MERGE (i:Incident {incident_id: $incident_id})

    MERGE (at:AttackType {name: $attack_type})
    MERGE (i)-[:INCIDENT_OF_TYPE]->(at)

    MERGE (src:Asset {ip: $source_ip})
    MERGE (i)-[:TARGETS_ASSET {role: 'source'}]->(src)

    MERGE (dst:Asset {ip: $dest_ip})
    MERGE (i)-[:TARGETS_ASSET {role: 'destination'}]->(dst)

    MERGE (pr:Protocol {name: $protocol})
    MERGE (i)-[:USES_PROTOCOL]->(pr)

    MERGE (sv:Severity {level: $severity})
    MERGE (i)-[:HAS_SEVERITY]->(sv)
    """
    await tx.run(
        cypher,
        incident_id=params["incident_id"],
        attack_type=params["attack_type"],
        source_ip=params["source_ip"],
        dest_ip=params["dest_ip"],
        protocol=params["protocol"],
        severity=params["severity"],
    )


async def _get_incident_graph_tx(tx, incident_id: str) -> Dict[str, Any]:
    # Fetch the incident and all directly connected nodes/rels
    cypher = """
    MATCH (i:Incident {incident_id: $incident_id})
    OPTIONAL MATCH (i)-[r1:INCIDENT_OF_TYPE]->(at:AttackType)
    OPTIONAL MATCH (i)-[r2:TARGETS_ASSET]->(a:Asset)
    OPTIONAL MATCH (i)-[r3:USES_PROTOCOL]->(pr:Protocol)
    OPTIONAL MATCH (i)-[r4:HAS_SEVERITY]->(sv:Severity)
    OPTIONAL MATCH (at)-[:MITIGATED_BY]->(m:Mitigation)
    OPTIONAL MATCH (i2:Incident)-[:INCIDENT_OF_TYPE]->(at)
        WHERE i2.incident_id <> $incident_id
    RETURN
        i                                       AS incident,
        collect(DISTINCT at.name)               AS attack_types,
        collect(DISTINCT {ip: a.ip, role: r2.role}) AS affected_assets,
        collect(DISTINCT pr.name)               AS protocols,
        collect(DISTINCT sv.level)              AS severities,
        collect(DISTINCT m.description)         AS mitigations,
        collect(DISTINCT i2.incident_id)[..5]   AS similar_incident_ids
    """
    record = await tx.run(cypher, incident_id=incident_id)
    row = await record.single()

    if row is None:
        return {"nodes": [], "relationships": [], "incident_id": incident_id}

    return {
        "incident_id": incident_id,
        "incident": dict(row["incident"]) if row["incident"] else {},
        "attack_type": row["attack_types"][0] if row["attack_types"] else None,
        "affected_assets": [a for a in row["affected_assets"] if a.get("ip")],
        "protocols": row["protocols"],
        "severities": row["severities"],
        "mitigations": [m for m in row["mitigations"] if m],
        "similar_incidents": row["similar_incident_ids"],
    }


async def _find_related_incidents_tx(tx, params: Dict[str, Any]) -> List[Dict[str, Any]]:
    # Build dynamic WHERE based on whether severity is provided
    severity_filter = ""
    if params.get("severity"):
        severity_filter = "AND (i2)-[:HAS_SEVERITY]->(:Severity {level: $severity})"

    cypher = f"""
    MATCH (at:AttackType {{name: $attack_type}})<-[:INCIDENT_OF_TYPE]-(i2:Incident)
    WHERE true {severity_filter}
    RETURN i2
    LIMIT $limit
    """
    result = await tx.run(
        cypher,
        attack_type=params["attack_type"],
        severity=params.get("severity", ""),
        limit=params["limit"],
    )
    records = await result.data()
    return [dict(r["i2"]) for r in records]


async def _get_mitigations_tx(tx, attack_type: str) -> List[str]:
    cypher = """
    MATCH (at:AttackType {name: $attack_type})-[:MITIGATED_BY]->(m:Mitigation)
    RETURN m.description AS description
    """
    result = await tx.run(cypher, attack_type=attack_type)
    records = await result.data()
    return [r["description"] for r in records if r.get("description")]


async def _store_mitigation_tx(tx, params: Dict[str, Any]) -> None:
    cypher = """
    MERGE (at:AttackType {name: $attack_type})
    MERGE (m:Mitigation {description: $mitigation})
    MERGE (at)-[:MITIGATED_BY]->(m)
    """
    await tx.run(
        cypher,
        attack_type=params["attack_type"],
        mitigation=params["mitigation"],
    )
