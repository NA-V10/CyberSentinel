"""
Main RAG pipeline orchestrator for CyberSentinel AI.

Combines vector + keyword retrieval (HybridRetriever) with graph expansion
(GraphService) to produce a rich context object ready for LLM prompting.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from loguru import logger

from backend.app.graph.neo4j_service import GraphService
from backend.app.rag.embeddings import EmbeddingService
from backend.app.rag.retriever import HybridRetriever

# ---------------------------------------------------------------------------
# Prompt template constants
# ---------------------------------------------------------------------------

_SYSTEM_HEADER = """\
You are CyberSentinel AI, an expert cybersecurity incident response assistant.
Answer the analyst's question using ONLY the context provided below.
Cite each piece of evidence with its [REF-N] marker.
If the context does not contain enough information, say so clearly.
"""

_CONTEXT_HEADER = "=== RETRIEVED INCIDENT CONTEXT ==="
_GRAPH_HEADER = "=== GRAPH KNOWLEDGE ==="
_QUERY_HEADER = "=== ANALYST QUERY ==="


class RAGPipeline:
    """Orchestrates the full Retrieve-Augment-Generate pipeline.

    Parameters
    ----------
    retriever:
        :class:`HybridRetriever` instance for vector + keyword search.
    graph_service:
        :class:`GraphService` instance for Neo4j graph expansion.
    embedding_service:
        :class:`EmbeddingService` used for any additional embed operations.
    """

    def __init__(
        self,
        retriever: HybridRetriever,
        graph_service: GraphService,
        embedding_service: EmbeddingService,
    ) -> None:
        self._retriever = retriever
        self._graph = graph_service
        self._embeddings = embedding_service

    # ------------------------------------------------------------------
    # Main pipeline entry point
    # ------------------------------------------------------------------

    async def run(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute the full RAG pipeline.

        Steps
        -----
        1. Hybrid retrieval (vector + keyword, deduped, re-ranked).
        2. Graph expansion — gather related incidents and mitigations from
           Neo4j using the top-ranked attack type.
        3. Merge and format all context for the LLM.

        Parameters
        ----------
        query:
            The analyst's free-text question or incident description.
        filters:
            Optional metadata filters forwarded to retrieval (severity,
            attack_type, protocol).

        Returns
        -------
        dict
            Keys:
            - ``vector_results``: raw list from hybrid retrieval
            - ``graph_context``: dict from Neo4j graph RAG
            - ``formatted_context``: single string ready for LLM injection
            - ``citations``: ordered list of citation dicts
        """
        logger.info("RAG pipeline started", query_chars=len(query))

        # --- Step 1: Hybrid retrieval ---
        retrieval_context = await self._retriever.retrieve_with_context(
            query, filters
        )
        vector_results: List[Dict[str, Any]] = retrieval_context["results"]

        # --- Step 2: Graph expansion ---
        attack_type = _infer_attack_type(vector_results, filters)
        graph_context = await self._graph.graph_rag_context(
            incident_text=query,
            attack_type=attack_type,
        )

        # --- Step 3: Build formatted context & citations ---
        citations = _build_citations(vector_results)
        formatted_context = _format_context(vector_results, graph_context, citations)

        logger.info(
            "RAG pipeline complete",
            vector_hits=len(vector_results),
            related_incidents=len(graph_context.get("related_incidents", [])),
            mitigations=len(graph_context.get("mitigations", [])),
            citations=len(citations),
        )

        return {
            "vector_results": vector_results,
            "graph_context": graph_context,
            "formatted_context": formatted_context,
            "citations": citations,
        }

    # ------------------------------------------------------------------
    # Prompt construction
    # ------------------------------------------------------------------

    async def build_prompt(
        self,
        query: str,
        context: Dict[str, Any],
    ) -> str:
        """Build the final LLM-ready prompt string.

        Parameters
        ----------
        query:
            The analyst's question.
        context:
            The dict returned by :meth:`run`.

        Returns
        -------
        str
            Full prompt including system header, context, and the query.
        """
        formatted_context: str = context.get("formatted_context", "")
        citations: List[Dict[str, Any]] = context.get("citations", [])

        citation_index = _format_citation_index(citations)

        prompt_parts = [
            _SYSTEM_HEADER,
            "",
            _CONTEXT_HEADER,
            formatted_context,
            "",
            _GRAPH_HEADER,
            _format_graph_section(context.get("graph_context", {})),
            "",
            "=== CITATION INDEX ===",
            citation_index,
            "",
            _QUERY_HEADER,
            query,
        ]

        prompt = "\n".join(prompt_parts)
        logger.debug("Prompt built", prompt_chars=len(prompt))
        return prompt


# ---------------------------------------------------------------------------
# Helpers — all module-private
# ---------------------------------------------------------------------------


def _infer_attack_type(
    vector_results: List[Dict[str, Any]],
    filters: Optional[Dict[str, Any]],
) -> str:
    """Try to determine the most likely attack type from available signals."""
    # Explicit filter wins
    if filters and filters.get("attack_type"):
        return filters["attack_type"]

    # Use the top-ranked vector result's payload
    for item in vector_results:
        payload = item.get("payload") or {}
        attack_type = payload.get("attack_type")
        if attack_type:
            return attack_type

    return "Unknown"


def _build_citations(
    vector_results: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Build an ordered citation list from retrieval results.

    Each citation gets a ``[REF-N]`` label starting at 1.
    """
    citations = []
    for idx, item in enumerate(vector_results, start=1):
        payload = item.get("payload") or {}
        citations.append(
            {
                "ref": f"REF-{idx}",
                "incident_id": item.get("id", "unknown"),
                "title": payload.get("title", "Untitled Incident"),
                "severity": payload.get("severity", "Unknown"),
                "attack_type": payload.get("attack_type", "Unknown"),
                "source": item.get("source", "unknown"),
                "score": round(item.get("score", 0.0), 4),
                "created_at": payload.get("created_at"),
            }
        )
    return citations


def _format_context(
    vector_results: List[Dict[str, Any]],
    graph_context: Dict[str, Any],
    citations: List[Dict[str, Any]],
) -> str:
    """Produce a single formatted string merging all retrieval context."""
    lines: List[str] = []

    # --- Vector results ---
    for citation, item in zip(citations, vector_results):
        ref = citation["ref"]
        payload = item.get("payload") or {}
        # Payload keys use normalised names: description (raw_text) and title (label)
        desc = payload.get("description") or payload.get("raw_text") or payload.get("title") or "No description available."
        lines.append(f"[{ref}] Incident {citation['incident_id']}")
        lines.append(f"  Title     : {citation['title']}")
        lines.append(f"  Severity  : {citation['severity']}")
        lines.append(f"  Attack    : {citation['attack_type']}")
        lines.append(f"  Score     : {citation['score']}")
        if payload.get("source_ip"):
            lines.append(f"  Source IP : {payload['source_ip']}")
        if payload.get("dest_ip"):
            lines.append(f"  Dest IP   : {payload['dest_ip']}")
        lines.append(f"  Summary   : {desc[:500]}")
        lines.append("")

    # --- Graph mitigations inline ---
    mitigations = graph_context.get("mitigations", [])
    if mitigations:
        lines.append("Known Mitigations:")
        for i, m in enumerate(mitigations, start=1):
            lines.append(f"  {i}. {m}")
        lines.append("")

    return "\n".join(lines)


def _format_graph_section(graph_context: Dict[str, Any]) -> str:
    """Format graph context as readable text for the prompt."""
    if not graph_context:
        return "No graph context available."

    parts: List[str] = []

    attack_type = graph_context.get("attack_type", "Unknown")
    parts.append(f"Attack Type  : {attack_type}")

    related = graph_context.get("related_incidents", [])
    if related:
        parts.append(f"Related Incidents ({len(related)}):")
        for inc in related[:5]:
            inc_id = inc.get("incident_id") or inc.get("id", "N/A")
            severity = inc.get("severity", "Unknown")
            parts.append(f"  - {inc_id} [{severity}]")

    mitigations = graph_context.get("mitigations", [])
    if mitigations:
        parts.append(f"Mitigations ({len(mitigations)}):")
        for m in mitigations[:10]:
            parts.append(f"  * {m}")

    return "\n".join(parts)


def _format_citation_index(citations: List[Dict[str, Any]]) -> str:
    """Format a compact citation index for inclusion at the bottom of the prompt."""
    if not citations:
        return "No citations available."

    lines = []
    for c in citations:
        lines.append(
            f"[{c['ref']}] {c['incident_id']} | {c['attack_type']} | "
            f"Severity: {c['severity']} | Score: {c['score']}"
        )
    return "\n".join(lines)
