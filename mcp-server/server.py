"""
CyberSentinel AI — MCP Server (stdio transport).

Run with:
    python server.py

Claude Desktop / MCP clients connect via stdin/stdout.

Environment variables:
    BACKEND_URL       URL of the CyberSentinel backend  (default: http://localhost:8000)
    API_V1_STR        Backend API prefix                 (default: /api/v1)
    MCP_SERVICE_TOKEN Bearer token for backend calls     (optional)
    MCP_REQUEST_TIMEOUT  HTTP timeout in seconds         (default: 30)
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from typing import Any, Dict, List

from dotenv import load_dotenv
from loguru import logger
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource,
    TextContent,
    Tool,
)

from tools import (
    calculate_risk_score,
    create_incident_report,
    get_attack_type_context,
    get_incident_by_id,
    query_graph_relationships,
    recommend_mitigation,
    search_similar_incidents,
    store_feedback,
)

# ---------------------------------------------------------------------------
# Load .env from the mcp-server directory
# ---------------------------------------------------------------------------

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# Reconfigure loguru to log to stderr (stdout is used for MCP protocol)
logger.remove()
logger.add(sys.stderr, level=os.getenv("LOG_LEVEL", "INFO"))

# ---------------------------------------------------------------------------
# MCP Server instance
# ---------------------------------------------------------------------------

server = Server("cybersentinel-ai")

# ===========================================================================
# Tool definitions — JSON Schema for each tool's inputSchema
# ===========================================================================

TOOL_DEFINITIONS: List[Tool] = [
    Tool(
        name="search_similar_incidents",
        description=(
            "Search for similar cybersecurity incidents using hybrid RAG (semantic + keyword). "
            "Returns a ranked list of historical incidents with similarity scores and metadata. "
            "Use this to find context for a new incident or understand how similar situations were handled."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Free-text description of the incident to search for.",
                    "minLength": 3,
                },
                "severity": {
                    "type": "string",
                    "description": "Optional severity filter.",
                    "enum": ["low", "medium", "high", "critical"],
                },
                "attack_type": {
                    "type": "string",
                    "description": "Optional attack-type filter (e.g. malware, ddos, phishing, ransomware).",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results to return (1–50).",
                    "default": 5,
                    "minimum": 1,
                    "maximum": 50,
                },
            },
            "required": ["query"],
        },
    ),
    Tool(
        name="get_incident_by_id",
        description=(
            "Retrieve full details of a specific incident by its UUID. "
            "Returns all stored fields including IPs, protocol, attack type, severity, "
            "timestamps, analyst notes, and embedding identifiers."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "incident_id": {
                    "type": "string",
                    "description": "UUID of the incident to retrieve.",
                },
            },
            "required": ["incident_id"],
        },
    ),
    Tool(
        name="get_attack_type_context",
        description=(
            "Get comprehensive context about a specific attack type. "
            "Returns typical attack patterns, affected system types, commonly used ports, "
            "historical frequency, and MITRE ATT&CK tactics. "
            "Supported types: malware, ddos, phishing, ransomware, sql_injection, xss, brute_force, port_scan."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "attack_type": {
                    "type": "string",
                    "description": "The attack category to query context for.",
                    "examples": ["malware", "ddos", "phishing", "ransomware", "sql_injection", "xss", "brute_force", "port_scan"],
                },
            },
            "required": ["attack_type"],
        },
    ),
    Tool(
        name="recommend_mitigation",
        description=(
            "Generate containment, eradication, recovery, and prevention recommendations "
            "for a cybersecurity incident. Calls the backend AI pipeline for LLM-powered guidance "
            "and falls back to the built-in knowledge base when offline."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "attack_type": {
                    "type": "string",
                    "description": "The attack category (e.g. malware, ddos, ransomware, phishing).",
                },
                "severity": {
                    "type": "string",
                    "description": "Incident severity level.",
                    "enum": ["low", "medium", "high", "critical"],
                },
                "context": {
                    "type": "string",
                    "description": "Optional additional context about the specific incident to make recommendations more relevant.",
                    "default": "",
                },
            },
            "required": ["attack_type", "severity"],
        },
    ),
    Tool(
        name="calculate_risk_score",
        description=(
            "Calculate a composite risk score (0–100) for an incident. "
            "Combines impact (severity × asset count), likelihood (attack-type base risk + historical frequency), "
            "and asset criticality into a weighted composite score with a risk-level label "
            "(critical/high/medium/low) and prioritised action recommendations."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "attack_type": {
                    "type": "string",
                    "description": "Attack category (e.g. ransomware, ddos, malware).",
                },
                "severity": {
                    "type": "string",
                    "description": "Incident severity level.",
                    "enum": ["low", "medium", "high", "critical"],
                },
                "affected_assets": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of affected asset identifiers (IPs, hostnames, service names).",
                },
                "historical_count": {
                    "type": "integer",
                    "description": "Number of similar incidents in the past 30 days (boosts likelihood score).",
                    "default": 0,
                    "minimum": 0,
                },
            },
            "required": ["attack_type", "severity", "affected_assets"],
        },
    ),
    Tool(
        name="create_incident_report",
        description=(
            "Create a structured, formatted incident report from analysis data. "
            "Builds an executive summary, technical details section, mitigation plan, "
            "and analyst notes. Attempts to persist the report to the backend database. "
            "Returns the full report dict with a unique report_id."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "incident_data": {
                    "type": "object",
                    "description": "Incident data to include in the report.",
                    "properties": {
                        "incident_id": {"type": "string", "description": "Existing incident UUID (optional)."},
                        "title": {"type": "string", "description": "Report title (auto-generated if omitted)."},
                        "attack_type": {"type": "string", "description": "Attack category."},
                        "severity": {"type": "string", "description": "Severity level."},
                        "affected_assets": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of affected assets.",
                        },
                        "source_ip": {"type": "string", "description": "Source IP address."},
                        "dest_ip": {"type": "string", "description": "Destination IP address."},
                        "protocol": {"type": "string", "description": "Network protocol."},
                        "description": {"type": "string", "description": "Incident description or log excerpt."},
                        "mitigation": {
                            "type": "object",
                            "description": "Mitigation plan with containment/eradication/recovery/prevention lists.",
                        },
                        "risk_score": {"type": "number", "description": "Risk score (0–100)."},
                        "analyst_notes": {"type": "string", "description": "Analyst notes or comments."},
                    },
                    "required": ["attack_type", "severity", "description"],
                },
            },
            "required": ["incident_data"],
        },
    ),
    Tool(
        name="query_graph_relationships",
        description=(
            "Query the Neo4j threat-knowledge graph for relationships. "
            "Returns connected attack types, affected assets, mitigation nodes, "
            "and similar incidents as a list of nodes and edges. "
            "Provide either an incident_id (to explore a specific incident's graph) "
            "or an attack_type (to explore the attack-type subgraph)."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "incident_id": {
                    "type": "string",
                    "description": "UUID of a specific incident to explore in the graph.",
                },
                "attack_type": {
                    "type": "string",
                    "description": "Attack type to query graph relationships for.",
                },
            },
        },
    ),
    Tool(
        name="store_feedback",
        description=(
            "Store analyst feedback for an incident to improve future AI recommendations. "
            "Feedback is used to evaluate mitigation quality and fine-tune the system. "
            "Rating scale: 1 (very poor) to 5 (excellent)."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "incident_id": {
                    "type": "string",
                    "description": "UUID of the incident being rated.",
                },
                "rating": {
                    "type": "integer",
                    "description": "Satisfaction rating from 1 (very poor) to 5 (excellent).",
                    "minimum": 1,
                    "maximum": 5,
                },
                "comment": {
                    "type": "string",
                    "description": "Free-text analyst comment or notes.",
                    "default": "",
                },
                "mitigation_worked": {
                    "type": "boolean",
                    "description": "Whether the suggested mitigation steps were effective.",
                },
            },
            "required": ["incident_id", "rating", "mitigation_worked"],
        },
    ),
]

# Map tool names to callables for fast dispatch
_TOOL_DISPATCH: Dict[str, Any] = {
    "search_similar_incidents": search_similar_incidents,
    "get_incident_by_id": get_incident_by_id,
    "get_attack_type_context": get_attack_type_context,
    "recommend_mitigation": recommend_mitigation,
    "calculate_risk_score": calculate_risk_score,
    "create_incident_report": create_incident_report,
    "query_graph_relationships": query_graph_relationships,
    "store_feedback": store_feedback,
}

# ===========================================================================
# MCP request handlers
# ===========================================================================


@server.list_tools()
async def list_tools() -> List[Tool]:
    """Return the full list of available MCP tools."""
    return TOOL_DEFINITIONS


@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Dispatch an MCP tool call and return the result as TextContent."""
    logger.info("MCP call_tool: %s args=%s", name, list(arguments.keys()))

    fn = _TOOL_DISPATCH.get(name)
    if fn is None:
        result = {
            "status": "error",
            "error": f"Unknown tool: '{name}'. Available tools: {list(_TOOL_DISPATCH.keys())}",
        }
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    try:
        result = await fn(**arguments)
    except TypeError as exc:
        logger.error("call_tool: bad arguments for %s: %s", name, exc)
        result = {
            "status": "error",
            "error": f"Invalid arguments for tool '{name}': {exc}",
        }
    except Exception as exc:
        logger.exception("call_tool: unexpected error in %s: %s", name, exc)
        result = {
            "status": "error",
            "error": f"Tool '{name}' encountered an unexpected error: {exc}",
        }

    return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]


# ===========================================================================
# Resources
# ===========================================================================

RESOURCE_DEFINITIONS: List[Resource] = [
    Resource(
        uri="cybersentinel://incidents/recent",
        name="Recent Incidents",
        description="The 10 most recently ingested cybersecurity incidents.",
        mimeType="application/json",
    ),
    Resource(
        uri="cybersentinel://attack-types",
        name="Attack Types Catalog",
        description="Catalog of known attack types with descriptions, patterns, and MITRE tactics.",
        mimeType="application/json",
    ),
    Resource(
        uri="cybersentinel://mitigations",
        name="Mitigation Templates",
        description="Standard mitigation playbooks organized by attack type and phase (containment/eradication/recovery/prevention).",
        mimeType="application/json",
    ),
]


@server.list_resources()
async def list_resources() -> List[Resource]:
    """Return the list of resources exposed by this MCP server."""
    return RESOURCE_DEFINITIONS


@server.read_resource()
async def read_resource(uri: str) -> str:
    """Return the content of a resource identified by URI."""
    logger.info("MCP read_resource: %s", uri)

    if uri == "cybersentinel://incidents/recent":
        return await _resource_recent_incidents()
    elif uri == "cybersentinel://attack-types":
        return await _resource_attack_types()
    elif uri == "cybersentinel://mitigations":
        return await _resource_mitigations()
    else:
        return json.dumps({"error": f"Unknown resource URI: '{uri}'"}, indent=2)


# ---------------------------------------------------------------------------
# Resource data fetchers
# ---------------------------------------------------------------------------

async def _resource_recent_incidents() -> str:
    """Fetch the 10 most recent incidents from the backend (or return empty list)."""
    import httpx
    from tools.incident_tools import BACKEND_URL, API_V1, REQUEST_TIMEOUT, _build_headers

    url = f"{BACKEND_URL}{API_V1}/ingest/incidents?limit=10&order=desc"
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            response = await client.get(url, headers=_build_headers())
            response.raise_for_status()
            data = response.json()
            return json.dumps({"incidents": data, "count": len(data) if isinstance(data, list) else 0}, indent=2, default=str)
    except Exception as exc:
        logger.warning("_resource_recent_incidents: %s", exc)
        return json.dumps({
            "incidents": [],
            "count": 0,
            "note": "Backend unavailable — no recent incidents to display.",
        }, indent=2)


async def _resource_attack_types() -> str:
    """Return the static attack-type catalog enriched with backend stats where available."""
    from tools.incident_tools import (
        BACKEND_URL, API_V1, REQUEST_TIMEOUT, _build_headers, _ATTACK_TYPE_KB
    )
    import httpx

    # Try to enrich with feedback stats
    stats_by_type: Dict[str, Any] = {}
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            response = await client.get(f"{BACKEND_URL}{API_V1}/feedback/stats", headers=_build_headers())
            if response.status_code == 200:
                for item in response.json().get("items", []):
                    at = (item.get("attack_type") or "").lower().replace(" ", "_")
                    if at:
                        stats_by_type[at] = {
                            "total_incidents": item.get("total_feedback"),
                            "avg_analyst_rating": item.get("avg_rating"),
                            "mitigation_success_pct": item.get("mitigation_worked_pct"),
                        }
    except Exception:
        pass

    catalog = []
    for at_key, kb in _ATTACK_TYPE_KB.items():
        entry = {
            "id": at_key,
            "description": kb.get("description", ""),
            "patterns": kb.get("patterns", []),
            "affected_systems": kb.get("affected_systems", []),
            "typical_ports": kb.get("typical_ports", []),
            "historical_frequency": kb.get("historical_frequency", "unknown"),
            "mitre_tactics": kb.get("mitre_tactics", []),
        }
        if at_key in stats_by_type:
            entry["live_stats"] = stats_by_type[at_key]
        catalog.append(entry)

    return json.dumps({"attack_types": catalog, "count": len(catalog)}, indent=2)


async def _resource_mitigations() -> str:
    """Return the built-in mitigation templates for all known attack types."""
    from tools.incident_tools import _MITIGATION_KB

    result = []
    for at_key, templates in _MITIGATION_KB.items():
        result.append({
            "attack_type": at_key,
            "phases": {
                "containment": templates.get("containment", []),
                "eradication": templates.get("eradication", []),
                "recovery": templates.get("recovery", []),
                "prevention": templates.get("prevention", []),
            },
        })

    return json.dumps({
        "mitigation_templates": result,
        "count": len(result),
        "note": "Templates are used as fallback when the backend LLM service is unavailable.",
    }, indent=2)


# ===========================================================================
# Entry point
# ===========================================================================

async def main() -> None:
    logger.info("Starting CyberSentinel AI MCP Server (stdio transport)")
    logger.info("Backend URL: %s", os.getenv("BACKEND_URL", "http://localhost:8000"))

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
