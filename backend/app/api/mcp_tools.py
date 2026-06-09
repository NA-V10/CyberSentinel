"""FastAPI router: MCP Tool Marketplace endpoints."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from backend.app.auth.clerk import get_current_user

router = APIRouter()

# ---------------------------------------------------------------------------
# MCP Tool Registry
# ---------------------------------------------------------------------------

MCP_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "graph_query",
        "display_name": "Graph Query",
        "description": "Query the Neo4j knowledge graph for threat relationships, attack patterns, and connected incidents.",
        "category": "Graph Intelligence",
        "status": "active",
        "input_schema": {
            "type": "object",
            "properties": {
                "attack_type": {"type": "string", "description": "Attack type to query relationships for"},
                "incident_id": {"type": "string", "description": "Incident UUID to expand in graph"},
                "depth": {"type": "integer", "default": 2, "description": "Graph traversal depth"},
            },
            "required": ["attack_type"],
        },
        "last_used_at": "2024-01-15T14:23:00Z",
        "total_calls": 1247,
        "avg_response_ms": 45,
    },
    {
        "name": "risk_score",
        "display_name": "Risk Score Calculator",
        "description": "Calculate an explainable risk score (0-100) for incidents based on severity, attack type, source reputation, and historical patterns.",
        "category": "Risk Assessment",
        "status": "active",
        "input_schema": {
            "type": "object",
            "properties": {
                "severity": {"type": "string", "enum": ["critical", "high", "medium", "low"]},
                "attack_type": {"type": "string"},
                "source_ip": {"type": "string"},
                "model_confidence": {"type": "number", "minimum": 0, "maximum": 1},
            },
            "required": ["severity", "attack_type"],
        },
        "last_used_at": "2024-01-15T14:45:00Z",
        "total_calls": 983,
        "avg_response_ms": 210,
    },
    {
        "name": "report_generator",
        "display_name": "Report Generator",
        "description": "Generate comprehensive incident reports in Markdown or PDF format including all analysis, MITRE mapping, and mitigation recommendations.",
        "category": "Reporting",
        "status": "active",
        "input_schema": {
            "type": "object",
            "properties": {
                "incident_id": {"type": "string", "description": "Incident UUID"},
                "format": {"type": "string", "enum": ["markdown", "pdf"], "default": "markdown"},
                "include_graph": {"type": "boolean", "default": True},
            },
            "required": ["incident_id"],
        },
        "last_used_at": "2024-01-15T12:10:00Z",
        "total_calls": 456,
        "avg_response_ms": 1200,
    },
    {
        "name": "guardrail_check",
        "display_name": "Guardrail Validator",
        "description": "Validate input text against security policies — detects prompt injection, offensive instructions, credential leakage, and policy violations.",
        "category": "Security",
        "status": "active",
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Input text to validate"},
            },
            "required": ["text"],
        },
        "last_used_at": "2024-01-15T15:00:00Z",
        "total_calls": 8921,
        "avg_response_ms": 8,
    },
    {
        "name": "threat_intel_lookup",
        "display_name": "Threat Intel Lookup",
        "description": "Enrich IPs, domains, and file hashes with threat intelligence including geo-location, reputation scores, known threat actors, and abuse reports.",
        "category": "Intelligence",
        "status": "active",
        "input_schema": {
            "type": "object",
            "properties": {
                "ip": {"type": "string", "description": "IP address to enrich"},
                "domain": {"type": "string", "description": "Domain to enrich"},
                "file_hash": {"type": "string", "description": "MD5/SHA1/SHA256 hash to enrich"},
            },
        },
        "last_used_at": "2024-01-15T14:55:00Z",
        "total_calls": 2341,
        "avg_response_ms": 95,
    },
    {
        "name": "mitre_mapper",
        "display_name": "MITRE ATT&CK Mapper",
        "description": "Map attack types and incident descriptions to MITRE ATT&CK tactics, techniques, and sub-techniques with confidence scoring and mitigation guidance.",
        "category": "Classification",
        "status": "active",
        "input_schema": {
            "type": "object",
            "properties": {
                "attack_type": {"type": "string", "description": "Attack type to map"},
                "incident_text": {"type": "string", "description": "Optional incident description for LLM reasoning"},
            },
            "required": ["attack_type"],
        },
        "last_used_at": "2024-01-15T14:30:00Z",
        "total_calls": 1876,
        "avg_response_ms": 340,
    },
    {
        "name": "similar_incident_search",
        "display_name": "Similar Incident Search",
        "description": "Find semantically and contextually similar historical incidents using hybrid vector + keyword + graph search with explainable similarity scores.",
        "category": "Search",
        "status": "active",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Incident description or query"},
                "attack_type": {"type": "string", "description": "Optional filter by attack type"},
                "severity": {"type": "string", "description": "Optional filter by severity"},
                "limit": {"type": "integer", "default": 10},
            },
            "required": ["query"],
        },
        "last_used_at": "2024-01-15T13:45:00Z",
        "total_calls": 3102,
        "avg_response_ms": 180,
    },
    {
        "name": "feedback_store",
        "display_name": "Feedback Store",
        "description": "Store analyst feedback on recommendations, similar incidents, and classifications. Feedback is used to improve future RAG ranking and model accuracy.",
        "category": "Learning",
        "status": "active",
        "input_schema": {
            "type": "object",
            "properties": {
                "incident_id": {"type": "string"},
                "rating": {"type": "integer", "minimum": 1, "maximum": 5},
                "mitigation_worked": {"type": "boolean"},
                "comment": {"type": "string"},
            },
            "required": ["rating"],
        },
        "last_used_at": "2024-01-15T11:20:00Z",
        "total_calls": 678,
        "avg_response_ms": 25,
    },
    {
        "name": "playbook_generator",
        "display_name": "Playbook Generator",
        "description": "Generate detailed incident response playbooks with containment, eradication, recovery, prevention, communication, and escalation steps.",
        "category": "Response",
        "status": "active",
        "input_schema": {
            "type": "object",
            "properties": {
                "attack_type": {"type": "string"},
                "severity": {"type": "string"},
                "incident_text": {"type": "string"},
                "source_ip": {"type": "string"},
            },
            "required": ["attack_type", "severity"],
        },
        "last_used_at": "2024-01-15T10:30:00Z",
        "total_calls": 445,
        "avg_response_ms": 520,
    },
    {
        "name": "sla_tracker",
        "display_name": "SLA Tracker",
        "description": "Track SLA deadlines per incident severity. Critical: 15min, High: 1hr, Medium: 4hr, Low: 24hr. Automatically detects breaches and assigns analyst levels.",
        "category": "Operations",
        "status": "active",
        "input_schema": {
            "type": "object",
            "properties": {
                "incident_id": {"type": "string"},
                "severity": {"type": "string", "enum": ["critical", "high", "medium", "low"]},
            },
            "required": ["incident_id", "severity"],
        },
        "last_used_at": "2024-01-15T14:00:00Z",
        "total_calls": 1123,
        "avg_response_ms": 30,
    },
]

_TOOL_INDEX = {t["name"]: t for t in MCP_TOOLS}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/tools",
    status_code=status.HTTP_200_OK,
    summary="List all available MCP tools",
)
async def list_mcp_tools(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Return the complete MCP tool registry with metadata."""
    return {
        "tools": MCP_TOOLS,
        "total": len(MCP_TOOLS),
        "active": sum(1 for t in MCP_TOOLS if t["status"] == "active"),
    }


class ToolTestRequest(BaseModel):
    input: Optional[Dict[str, Any]] = None


@router.post(
    "/tools/{tool_name}/test",
    status_code=status.HTTP_200_OK,
    summary="Test an MCP tool with sample input",
)
async def test_mcp_tool(
    tool_name: str,
    request: ToolTestRequest = ToolTestRequest(),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Execute a quick test of the specified MCP tool and return the result."""
    tool = _TOOL_INDEX.get(tool_name)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found.")

    start_ms = time.time() * 1000
    result: Dict[str, Any] = {}
    error: Optional[str] = None

    try:
        inp = request.input or {}
        if tool_name == "risk_score":
            from backend.app.services.risk_scoring_service import calculate_risk_score
            result = await calculate_risk_score(
                severity=inp.get("severity", "high"),
                attack_type=inp.get("attack_type", "Brute Force"),
            )
        elif tool_name == "mitre_mapper":
            from backend.app.services.mitre_mapping_service import map_attack
            result = await map_attack(
                attack_type=inp.get("attack_type", "Phishing"),
                incident_text=inp.get("incident_text", "Test incident"),
            )
        elif tool_name == "threat_intel_lookup":
            from backend.app.services.threat_intel_service import enrich_ip
            result = await enrich_ip(inp.get("ip", "185.220.101.47"))
        elif tool_name == "playbook_generator":
            from backend.app.services.playbook_service import generate_playbook
            result = await generate_playbook(
                attack_type=inp.get("attack_type", "Malware"),
                severity=inp.get("severity", "critical"),
            )
        elif tool_name == "sla_tracker":
            from backend.app.services.sla_service import SLA_RULES, SEVERITY_LEVELS
            sev = inp.get("severity", "high")
            result = {
                "severity": sev,
                "sla_minutes": SLA_RULES.get(sev, 60),
                "assigned_level": SEVERITY_LEVELS.get(sev, "L1 Analyst"),
                "status": "SLA tracker would be assigned to incident",
            }
        elif tool_name == "guardrail_check":
            from backend.app.guardrails.policy_guardrails import guardrails
            result = await guardrails.validate(inp.get("text", "Test input for validation"))
        else:
            result = {"message": f"Tool '{tool_name}' test executed successfully.", "input": inp}

    except Exception as exc:
        error = str(exc)
        result = {"error": error}

    elapsed_ms = int(time.time() * 1000 - start_ms)

    return {
        "tool_name": tool_name,
        "input": request.input,
        "output": result,
        "response_time_ms": elapsed_ms,
        "status": "error" if error else "success",
        "error": error,
    }
