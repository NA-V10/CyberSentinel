"""
CyberSentinel AI — MCP HTTP Server (FastAPI).

Alternative to the stdio MCP server. Exposes MCP tools and resources over HTTP
so the backend agents (and other services) can call MCP tools via standard REST.

Endpoints:
    POST /tools/list          — List all available tools
    POST /tools/call          — Call a tool by name with arguments
    GET  /resources           — List all resources
    GET  /resources/{uri:path} — Read a specific resource by URI
    GET  /health              — Health check

Run with:
    uvicorn http_server:app --host 0.0.0.0 --port 8001 --reload

Or via Docker:
    docker run -p 8001:8001 cybersentinel-mcp-server

Environment variables:
    BACKEND_URL           URL of the CyberSentinel backend  (default: http://localhost:8000)
    API_V1_STR            Backend API prefix                 (default: /api/v1)
    MCP_SERVICE_TOKEN     Bearer token for backend calls     (optional)
    MCP_REQUEST_TIMEOUT   HTTP timeout in seconds            (default: 30)
    MCP_API_KEY           API key for securing this server   (optional)
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Optional

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Path, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from pydantic import BaseModel, Field

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
from tools.incident_tools import (
    API_V1,
    BACKEND_URL,
    REQUEST_TIMEOUT,
    _ATTACK_TYPE_KB,
    _MITIGATION_KB,
    _build_headers,
)

# ---------------------------------------------------------------------------
# Load environment
# ---------------------------------------------------------------------------

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# Optional API key guard for the HTTP server itself
MCP_API_KEY: str = os.getenv("MCP_API_KEY", "")

# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="CyberSentinel AI — MCP HTTP Server",
    version="1.0.0",
    description=(
        "HTTP interface to the CyberSentinel AI MCP tools and resources. "
        "Allows backend agents and services to call MCP tools over plain HTTP "
        "instead of requiring a stdio MCP client."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Tool dispatch registry
# ---------------------------------------------------------------------------

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

_TOOL_SCHEMAS: List[Dict[str, Any]] = [
    {
        "name": "search_similar_incidents",
        "description": (
            "Search for similar cybersecurity incidents using hybrid RAG (semantic + keyword). "
            "Returns a ranked list of historical incidents with similarity scores."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Free-text incident description.", "minLength": 3},
                "severity": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
                "attack_type": {"type": "string", "description": "Optional attack-type filter."},
                "limit": {"type": "integer", "default": 5, "minimum": 1, "maximum": 50},
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_incident_by_id",
        "description": "Retrieve full details of a specific incident by UUID.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "incident_id": {"type": "string", "description": "Incident UUID."},
            },
            "required": ["incident_id"],
        },
    },
    {
        "name": "get_attack_type_context",
        "description": (
            "Get context about an attack type: description, patterns, affected systems, "
            "historical frequency, and MITRE ATT&CK tactics."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "attack_type": {"type": "string", "description": "Attack category name."},
            },
            "required": ["attack_type"],
        },
    },
    {
        "name": "recommend_mitigation",
        "description": "Get containment, eradication, recovery, and prevention recommendations.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "attack_type": {"type": "string"},
                "severity": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
                "context": {"type": "string", "default": ""},
            },
            "required": ["attack_type", "severity"],
        },
    },
    {
        "name": "calculate_risk_score",
        "description": "Calculate a composite risk score (0–100) with impact/likelihood/asset breakdown.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "attack_type": {"type": "string"},
                "severity": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
                "affected_assets": {"type": "array", "items": {"type": "string"}},
                "historical_count": {"type": "integer", "default": 0, "minimum": 0},
            },
            "required": ["attack_type", "severity", "affected_assets"],
        },
    },
    {
        "name": "create_incident_report",
        "description": "Create a structured incident report from analysis data.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "incident_data": {
                    "type": "object",
                    "properties": {
                        "incident_id": {"type": "string"},
                        "title": {"type": "string"},
                        "attack_type": {"type": "string"},
                        "severity": {"type": "string"},
                        "affected_assets": {"type": "array", "items": {"type": "string"}},
                        "source_ip": {"type": "string"},
                        "dest_ip": {"type": "string"},
                        "protocol": {"type": "string"},
                        "description": {"type": "string"},
                        "mitigation": {"type": "object"},
                        "risk_score": {"type": "number"},
                        "analyst_notes": {"type": "string"},
                    },
                    "required": ["attack_type", "severity", "description"],
                },
            },
            "required": ["incident_data"],
        },
    },
    {
        "name": "query_graph_relationships",
        "description": "Query the Neo4j graph for incident/attack-type relationships (nodes + edges).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "incident_id": {"type": "string"},
                "attack_type": {"type": "string"},
            },
        },
    },
    {
        "name": "store_feedback",
        "description": "Store analyst feedback (rating 1–5) for an incident.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "incident_id": {"type": "string"},
                "rating": {"type": "integer", "minimum": 1, "maximum": 5},
                "comment": {"type": "string", "default": ""},
                "mitigation_worked": {"type": "boolean"},
            },
            "required": ["incident_id", "rating", "mitigation_worked"],
        },
    },
]

_RESOURCE_DEFINITIONS: List[Dict[str, Any]] = [
    {
        "uri": "cybersentinel://incidents/recent",
        "name": "Recent Incidents",
        "description": "The 10 most recently ingested cybersecurity incidents.",
        "mimeType": "application/json",
    },
    {
        "uri": "cybersentinel://attack-types",
        "name": "Attack Types Catalog",
        "description": "Catalog of known attack types with descriptions, patterns, and MITRE tactics.",
        "mimeType": "application/json",
    },
    {
        "uri": "cybersentinel://mitigations",
        "name": "Mitigation Templates",
        "description": "Standard mitigation playbooks by attack type and phase.",
        "mimeType": "application/json",
    },
]

# ---------------------------------------------------------------------------
# Pydantic request / response models
# ---------------------------------------------------------------------------


class ToolCallRequest(BaseModel):
    name: str = Field(..., description="Name of the tool to call.")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Tool arguments matching the inputSchema.")


class ToolCallResponse(BaseModel):
    tool: str
    status: str
    result: Any
    duration_ms: float


class ToolListResponse(BaseModel):
    tools: List[Dict[str, Any]]
    count: int


class ResourceListResponse(BaseModel):
    resources: List[Dict[str, Any]]
    count: int


# ---------------------------------------------------------------------------
# Optional API key guard
# ---------------------------------------------------------------------------

def _check_api_key(x_api_key: Optional[str]) -> None:
    if MCP_API_KEY and x_api_key != MCP_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-API-Key header.",
        )


# ===========================================================================
# Routes
# ===========================================================================


@app.get("/health", tags=["system"], summary="Health check")
async def health() -> Dict[str, Any]:
    """Return server health and backend reachability."""
    backend_ok = False
    backend_latency_ms: Optional[float] = None

    try:
        t0 = time.monotonic()
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{BACKEND_URL}/health")
            backend_ok = resp.status_code == 200
        backend_latency_ms = round((time.monotonic() - t0) * 1000, 1)
    except Exception:
        pass

    return {
        "status": "ok",
        "service": "CyberSentinel AI MCP HTTP Server",
        "version": "1.0.0",
        "tools_registered": len(_TOOL_DISPATCH),
        "resources_registered": len(_RESOURCE_DEFINITIONS),
        "backend": {
            "url": BACKEND_URL,
            "reachable": backend_ok,
            "latency_ms": backend_latency_ms,
        },
    }


@app.post(
    "/tools/list",
    response_model=ToolListResponse,
    tags=["tools"],
    summary="List all available MCP tools",
)
async def list_tools(x_api_key: Optional[str] = Header(default=None)) -> ToolListResponse:
    """Return all registered tool definitions with their input schemas."""
    _check_api_key(x_api_key)
    return ToolListResponse(tools=_TOOL_SCHEMAS, count=len(_TOOL_SCHEMAS))


@app.post(
    "/tools/call",
    tags=["tools"],
    summary="Call an MCP tool by name",
)
async def call_tool(
    request: ToolCallRequest,
    x_api_key: Optional[str] = Header(default=None),
) -> JSONResponse:
    """Execute a named tool with the provided arguments.

    Returns the tool result as a JSON object. If the tool raises an error,
    returns a 200 response with `status: "error"` so that calling agents
    can distinguish tool-level errors from server-level errors.
    """
    _check_api_key(x_api_key)

    fn = _TOOL_DISPATCH.get(request.name)
    if fn is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown tool: '{request.name}'. Available: {list(_TOOL_DISPATCH.keys())}",
        )

    logger.info("HTTP call_tool: %s args=%s", request.name, list(request.arguments.keys()))
    t0 = time.monotonic()

    try:
        result = await fn(**request.arguments)
        tool_status = result.get("status", "success") if isinstance(result, dict) else "success"
    except TypeError as exc:
        logger.error("call_tool: bad arguments for %s: %s", request.name, exc)
        result = {"status": "error", "error": f"Invalid arguments: {exc}"}
        tool_status = "error"
    except Exception as exc:
        logger.exception("call_tool: unexpected error in %s", request.name)
        result = {"status": "error", "error": f"Tool error: {exc}"}
        tool_status = "error"

    duration_ms = round((time.monotonic() - t0) * 1000, 1)

    return JSONResponse(
        content={
            "tool": request.name,
            "status": tool_status,
            "result": result,
            "duration_ms": duration_ms,
        }
    )


@app.get(
    "/resources",
    response_model=ResourceListResponse,
    tags=["resources"],
    summary="List all available MCP resources",
)
async def list_resources(x_api_key: Optional[str] = Header(default=None)) -> ResourceListResponse:
    """Return all registered resource definitions."""
    _check_api_key(x_api_key)
    return ResourceListResponse(resources=_RESOURCE_DEFINITIONS, count=len(_RESOURCE_DEFINITIONS))


@app.get(
    "/resources/{uri:path}",
    tags=["resources"],
    summary="Read a specific resource by URI",
)
async def read_resource(
    uri: str = Path(..., description="Resource URI (e.g. cybersentinel://incidents/recent)"),
    x_api_key: Optional[str] = Header(default=None),
) -> JSONResponse:
    """Return the content of a resource. The URI path segment maps to the resource identifier."""
    _check_api_key(x_api_key)

    # Reconstruct the full cybersentinel:// URI from the path parameter
    # FastAPI strips the scheme, so we normalise here
    if not uri.startswith("cybersentinel://"):
        # Try to match by suffix
        for resource in _RESOURCE_DEFINITIONS:
            resource_uri: str = resource["uri"]
            if uri in resource_uri or resource_uri.endswith(uri):
                uri = resource_uri
                break

    logger.info("HTTP read_resource: %s", uri)

    if uri == "cybersentinel://incidents/recent":
        content = await _resource_recent_incidents()
    elif uri == "cybersentinel://attack-types":
        content = await _resource_attack_types()
    elif uri == "cybersentinel://mitigations":
        content = await _resource_mitigations()
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown resource URI: '{uri}'. Available: {[r['uri'] for r in _RESOURCE_DEFINITIONS]}",
        )

    try:
        return JSONResponse(content=json.loads(content))
    except json.JSONDecodeError:
        return JSONResponse(content={"raw": content})


# ---------------------------------------------------------------------------
# Resource data fetchers (duplicated here so http_server is self-contained)
# ---------------------------------------------------------------------------

async def _resource_recent_incidents() -> str:
    url = f"{BACKEND_URL}{API_V1}/ingest/incidents?limit=10&order=desc"
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            response = await client.get(url, headers=_build_headers())
            response.raise_for_status()
            data = response.json()
            return json.dumps(
                {"incidents": data, "count": len(data) if isinstance(data, list) else 0},
                indent=2,
                default=str,
            )
    except Exception as exc:
        logger.warning("_resource_recent_incidents: %s", exc)
        return json.dumps({"incidents": [], "count": 0, "note": "Backend unavailable."}, indent=2)


async def _resource_attack_types() -> str:
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
        entry: Dict[str, Any] = {
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
        "note": "Templates used as fallback when LLM backend is unavailable.",
    }, indent=2)


# ---------------------------------------------------------------------------
# Global exception handler — always return JSON
# ---------------------------------------------------------------------------

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception: %s %s", request.method, request.url)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected error occurred.", "error": str(exc)},
    )


# ---------------------------------------------------------------------------
# Entry point (for direct execution)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "http_server:app",
        host="0.0.0.0",
        port=int(os.getenv("MCP_HTTP_PORT", "8001")),
        reload=os.getenv("DEBUG", "false").lower() == "true",
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
    )
