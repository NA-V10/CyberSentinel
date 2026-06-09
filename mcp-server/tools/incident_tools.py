"""
CyberSentinel AI — MCP tool implementations.

Each function calls the CyberSentinel backend API (BACKEND_URL env var).
When the backend is unreachable, fallback logic returns best-effort static
data so that the MCP server remains usable during development or outages.
"""

from __future__ import annotations

import os
import json
import math
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
from loguru import logger

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BACKEND_URL: str = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
API_V1: str = os.getenv("API_V1_STR", "/api/v1")
REQUEST_TIMEOUT: float = float(os.getenv("MCP_REQUEST_TIMEOUT", "30"))

# Internal bearer token for service-to-service calls (optional)
SERVICE_TOKEN: str = os.getenv("MCP_SERVICE_TOKEN", "")

# ---------------------------------------------------------------------------
# Known attack-type knowledge base (fallback when backend is unavailable)
# ---------------------------------------------------------------------------

_ATTACK_TYPE_KB: Dict[str, Dict[str, Any]] = {
    "malware": {
        "description": "Malicious software designed to disrupt, damage, or gain unauthorized access to systems.",
        "patterns": ["unusual process execution", "outbound C2 connections", "file system modifications", "registry changes"],
        "affected_systems": ["endpoints", "servers", "mobile devices"],
        "typical_ports": [4444, 1337, 8080, 443],
        "historical_frequency": "very_high",
        "mitre_tactics": ["Execution", "Persistence", "Command and Control"],
    },
    "ddos": {
        "description": "Distributed Denial of Service attack flooding a target with traffic to exhaust resources.",
        "patterns": ["high packet rate", "SYN flood", "UDP flood", "amplification attacks"],
        "affected_systems": ["web servers", "DNS servers", "network infrastructure"],
        "typical_ports": [80, 443, 53],
        "historical_frequency": "high",
        "mitre_tactics": ["Impact"],
    },
    "phishing": {
        "description": "Social engineering attack using deceptive emails or websites to steal credentials.",
        "patterns": ["suspicious email links", "credential harvesting pages", "domain spoofing"],
        "affected_systems": ["email servers", "user workstations", "identity providers"],
        "typical_ports": [25, 587, 443, 80],
        "historical_frequency": "very_high",
        "mitre_tactics": ["Initial Access", "Credential Access"],
    },
    "ransomware": {
        "description": "Malware that encrypts victim files and demands payment for decryption keys.",
        "patterns": ["mass file encryption", "ransom note creation", "shadow copy deletion", "lateral movement"],
        "affected_systems": ["file servers", "endpoints", "NAS devices", "databases"],
        "typical_ports": [445, 3389, 4444],
        "historical_frequency": "high",
        "mitre_tactics": ["Execution", "Lateral Movement", "Impact"],
    },
    "sql_injection": {
        "description": "Injection attack inserting malicious SQL into application queries.",
        "patterns": ["malformed SQL in request parameters", "UNION SELECT patterns", "error-based enumeration"],
        "affected_systems": ["web applications", "databases", "APIs"],
        "typical_ports": [80, 443, 1433, 3306, 5432],
        "historical_frequency": "high",
        "mitre_tactics": ["Initial Access", "Credential Access", "Collection"],
    },
    "xss": {
        "description": "Cross-Site Scripting injects malicious scripts into web pages viewed by other users.",
        "patterns": ["script tag injection", "event handler injection", "DOM manipulation"],
        "affected_systems": ["web applications", "browsers"],
        "typical_ports": [80, 443],
        "historical_frequency": "very_high",
        "mitre_tactics": ["Initial Access", "Credential Access"],
    },
    "brute_force": {
        "description": "Repeated authentication attempts to guess credentials by exhaustive trial.",
        "patterns": ["high login failure rate", "sequential IP attempts", "credential stuffing"],
        "affected_systems": ["SSH servers", "RDP servers", "web authentication", "VPNs"],
        "typical_ports": [22, 3389, 80, 443, 21],
        "historical_frequency": "very_high",
        "mitre_tactics": ["Credential Access", "Initial Access"],
    },
    "port_scan": {
        "description": "Reconnaissance technique probing ports to identify running services.",
        "patterns": ["sequential port access", "SYN packets without handshake completion", "service banner grabbing"],
        "affected_systems": ["network perimeter", "firewalls", "all hosts"],
        "typical_ports": [],
        "historical_frequency": "very_high",
        "mitre_tactics": ["Reconnaissance", "Discovery"],
    },
}

# ---------------------------------------------------------------------------
# Mitigation templates (fallback)
# ---------------------------------------------------------------------------

_MITIGATION_KB: Dict[str, Dict[str, List[str]]] = {
    "malware": {
        "containment": [
            "Isolate infected host from the network immediately",
            "Block outbound connections to identified C2 IPs/domains",
            "Suspend compromised user accounts",
            "Enable enhanced endpoint logging",
        ],
        "eradication": [
            "Run full AV/EDR scan on isolated host",
            "Remove malicious processes and persistence mechanisms",
            "Patch exploited vulnerabilities",
            "Restore system from clean backup if integrity compromised",
        ],
        "recovery": [
            "Reimage or restore host from verified clean backup",
            "Reset all credentials that may have been exposed",
            "Re-enable network access after verification",
            "Monitor host for recurrence for 30 days",
        ],
        "prevention": [
            "Deploy EDR solution across all endpoints",
            "Implement application whitelisting",
            "Enable email attachment sandboxing",
            "Enforce least-privilege access controls",
        ],
    },
    "ddos": {
        "containment": [
            "Activate upstream DDoS mitigation provider (Cloudflare, Akamai, AWS Shield)",
            "Implement rate limiting at the edge",
            "Block attacking IP ranges at perimeter firewall",
            "Shift DNS to scrubbing center",
        ],
        "eradication": [
            "Identify and null-route attack sources",
            "Configure ACLs to drop attack traffic patterns",
            "Work with ISP for BGP blackhole routing if necessary",
        ],
        "recovery": [
            "Gradually restore services starting with critical systems",
            "Monitor traffic baselines for 24 hours post-attack",
            "Verify service health and integrity",
        ],
        "prevention": [
            "Subscribe to DDoS protection service",
            "Implement anycast network diffusion",
            "Configure auto-scaling for web infrastructure",
            "Establish traffic baseline and anomaly alerting",
        ],
    },
    "phishing": {
        "containment": [
            "Block sender domains/IPs at email gateway",
            "Quarantine all emails from identified campaign",
            "Reset credentials for targeted accounts",
            "Enable MFA for affected user accounts",
        ],
        "eradication": [
            "Remove phishing emails from all user mailboxes",
            "Block phishing URLs at web proxy/DNS",
            "Revoke and reissue compromised tokens/sessions",
            "Conduct user awareness notification",
        ],
        "recovery": [
            "Restore access to legitimate services",
            "Verify no persistent access was established",
            "Review and harden email filtering rules",
        ],
        "prevention": [
            "Enable DMARC/DKIM/SPF for all owned domains",
            "Implement security awareness training",
            "Deploy browser isolation for risky sites",
            "Enforce phishing-resistant MFA (FIDO2/hardware keys)",
        ],
    },
    "default": {
        "containment": [
            "Isolate affected systems from the network",
            "Block all traffic from identified attack sources",
            "Preserve forensic evidence (memory dumps, logs)",
            "Alert the security operations team",
        ],
        "eradication": [
            "Identify and remove root cause",
            "Patch exploited vulnerabilities",
            "Remove attacker persistence mechanisms",
            "Reset compromised credentials",
        ],
        "recovery": [
            "Restore services from clean backups",
            "Validate system integrity before reconnecting",
            "Monitor for recurrence",
        ],
        "prevention": [
            "Apply security patches promptly",
            "Implement network segmentation",
            "Enable comprehensive logging and SIEM alerting",
            "Conduct regular security assessments",
        ],
    },
}

# ---------------------------------------------------------------------------
# Severity weights for risk scoring
# ---------------------------------------------------------------------------

_SEVERITY_WEIGHTS: Dict[str, float] = {
    "critical": 1.0,
    "high": 0.75,
    "medium": 0.50,
    "low": 0.25,
    "unknown": 0.40,
}

_ATTACK_TYPE_BASE_RISK: Dict[str, float] = {
    "ransomware": 0.95,
    "malware": 0.85,
    "ddos": 0.75,
    "sql_injection": 0.80,
    "phishing": 0.70,
    "brute_force": 0.65,
    "xss": 0.60,
    "port_scan": 0.35,
    "default": 0.55,
}


# ---------------------------------------------------------------------------
# HTTP client factory
# ---------------------------------------------------------------------------

def _build_headers() -> Dict[str, str]:
    headers: Dict[str, str] = {"Content-Type": "application/json", "Accept": "application/json"}
    if SERVICE_TOKEN:
        headers["Authorization"] = f"Bearer {SERVICE_TOKEN}"
    return headers


# ===========================================================================
# Tool 1 — search_similar_incidents
# ===========================================================================

async def search_similar_incidents(
    query: str,
    severity: str | None = None,
    attack_type: str | None = None,
    limit: int = 5,
) -> dict:
    """Search for similar cybersecurity incidents using hybrid RAG.

    Performs a semantic + keyword hybrid search over historical incidents
    stored in the vector database. Returns a ranked list of similar incidents
    with similarity scores and key metadata.

    Args:
        query: Free-text description of the incident to search for.
        severity: Optional severity filter — one of: low, medium, high, critical.
        attack_type: Optional attack-type filter (e.g. malware, ddos, phishing).
        limit: Maximum number of results to return (1–50, default 5).

    Returns:
        dict with keys:
          - status: "success" or "error"
          - results: list of incident dicts (id, score, attack_type, severity, summary, ...)
          - total: number of results returned
          - query: the original query string
          - filters: active filters dict
    """
    payload: Dict[str, Any] = {"query": query, "limit": min(max(limit, 1), 50)}
    if severity:
        payload["severity"] = severity.lower()
    if attack_type:
        payload["attack_type"] = attack_type.lower()

    url = f"{BACKEND_URL}{API_V1}/search/similar"
    logger.debug("search_similar_incidents → %s", url)

    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            response = await client.post(url, json=payload, headers=_build_headers())
            response.raise_for_status()
            data = response.json()
            return {
                "status": "success",
                "results": data.get("results", []),
                "total": data.get("total", 0),
                "query": data.get("query", query),
                "filters": data.get("filters", {}),
            }
    except httpx.HTTPStatusError as exc:
        logger.warning("search_similar_incidents: HTTP %d — %s", exc.response.status_code, exc.response.text)
        return {
            "status": "error",
            "error": f"Backend returned HTTP {exc.response.status_code}",
            "results": [],
            "total": 0,
            "query": query,
            "filters": payload,
        }
    except Exception as exc:
        logger.warning("search_similar_incidents: backend unreachable — using fallback: %s", exc)
        # Fallback: return synthetic results based on known attack-type KB
        fallback_results = _fallback_search(query, attack_type, severity, limit)
        return {
            "status": "fallback",
            "warning": "Backend unavailable — returning knowledge-base fallback results.",
            "results": fallback_results,
            "total": len(fallback_results),
            "query": query,
            "filters": payload,
        }


def _fallback_search(
    query: str,
    attack_type: str | None,
    severity: str | None,
    limit: int,
) -> List[Dict[str, Any]]:
    """Return synthetic similarity results from the static KB when backend is down."""
    results = []
    query_lower = query.lower()

    # Score each known attack type by keyword overlap with query
    for at_key, kb in _ATTACK_TYPE_KB.items():
        if attack_type and at_key != attack_type.lower().replace(" ", "_"):
            continue
        score = 0.1
        for pattern in kb.get("patterns", []):
            if any(word in query_lower for word in pattern.lower().split()):
                score += 0.15
        if at_key in query_lower:
            score += 0.30
        score = round(min(score, 0.99), 4)

        results.append({
            "id": f"fallback-{at_key}-{uuid.uuid4().hex[:8]}",
            "score": score,
            "attack_type": at_key,
            "severity": severity or "medium",
            "summary": kb["description"][:200],
            "source": "knowledge_base_fallback",
        })

    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:limit]


# ===========================================================================
# Tool 2 — get_incident_by_id
# ===========================================================================

async def get_incident_by_id(incident_id: str) -> dict:
    """Get full details of a specific incident by ID.

    Retrieves a complete incident record from the database, including
    source/destination IPs, attack classification, severity, timestamps,
    and any analyst notes.

    Args:
        incident_id: UUID string identifying the incident.

    Returns:
        dict with keys:
          - status: "success" or "error"
          - incident: full incident record dict (or None on error)
    """
    url = f"{BACKEND_URL}{API_V1}/ingest/incidents/{incident_id}"
    logger.debug("get_incident_by_id → %s", url)

    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            response = await client.get(url, headers=_build_headers())
            if response.status_code == 404:
                return {"status": "error", "error": f"Incident '{incident_id}' not found.", "incident": None}
            response.raise_for_status()
            return {"status": "success", "incident": response.json()}
    except httpx.HTTPStatusError as exc:
        logger.warning("get_incident_by_id: HTTP %d", exc.response.status_code)
        return {
            "status": "error",
            "error": f"Backend returned HTTP {exc.response.status_code}",
            "incident": None,
        }
    except Exception as exc:
        logger.warning("get_incident_by_id: backend unreachable — %s", exc)
        return {
            "status": "error",
            "error": "Backend unavailable. Please retry when the service is up.",
            "incident": {
                "id": incident_id,
                "note": "Backend unreachable — data not available.",
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
            },
        }


# ===========================================================================
# Tool 3 — get_attack_type_context
# ===========================================================================

async def get_attack_type_context(attack_type: str) -> dict:
    """Get full context about an attack type.

    Returns typical patterns, affected systems, historical frequency,
    MITRE ATT&CK tactics, and any recent incidents of this type.

    Args:
        attack_type: The attack category (e.g. malware, ddos, phishing, ransomware,
                     sql_injection, xss, brute_force, port_scan).

    Returns:
        dict with keys:
          - status: "success", "fallback", or "error"
          - attack_type: normalised attack type string
          - description: plain-language description
          - patterns: list of typical indicators
          - affected_systems: list of commonly targeted system types
          - typical_ports: list of commonly used ports
          - historical_frequency: low | medium | high | very_high
          - mitre_tactics: list of MITRE ATT&CK tactics
          - recent_incidents: list of recent incidents of this type (if available)
    """
    normalised = attack_type.lower().replace(" ", "_").replace("-", "_")

    # Try fetching aggregated stats from feedback endpoint as a proxy
    url = f"{BACKEND_URL}{API_V1}/feedback/stats"
    recent_incidents: List[Dict[str, Any]] = []

    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            response = await client.get(url, headers=_build_headers())
            if response.status_code == 200:
                stats = response.json()
                for item in stats.get("items", []):
                    if item.get("attack_type", "").lower().replace(" ", "_") == normalised:
                        recent_incidents = [{
                            "total_feedback": item.get("total_feedback"),
                            "avg_rating": item.get("avg_rating"),
                            "mitigation_worked_pct": item.get("mitigation_worked_pct"),
                        }]
                        break
    except Exception as exc:
        logger.debug("get_attack_type_context: could not fetch stats: %s", exc)

    kb = _ATTACK_TYPE_KB.get(normalised) or _ATTACK_TYPE_KB.get(
        next((k for k in _ATTACK_TYPE_KB if normalised in k or k in normalised), ""), {}
    )

    if not kb:
        return {
            "status": "error",
            "error": f"Unknown attack type: '{attack_type}'. Known types: {list(_ATTACK_TYPE_KB.keys())}",
            "attack_type": normalised,
        }

    return {
        "status": "success" if recent_incidents else "fallback",
        "attack_type": normalised,
        "description": kb.get("description", ""),
        "patterns": kb.get("patterns", []),
        "affected_systems": kb.get("affected_systems", []),
        "typical_ports": kb.get("typical_ports", []),
        "historical_frequency": kb.get("historical_frequency", "unknown"),
        "mitre_tactics": kb.get("mitre_tactics", []),
        "recent_incidents": recent_incidents,
    }


# ===========================================================================
# Tool 4 — recommend_mitigation
# ===========================================================================

async def recommend_mitigation(
    attack_type: str,
    severity: str,
    context: str = "",
) -> dict:
    """Get containment, eradication, recovery, and prevention recommendations.

    Calls the backend analysis API to generate LLM-powered mitigation guidance,
    falling back to the built-in mitigation knowledge base when the backend is
    unavailable.

    Args:
        attack_type: The attack category (e.g. malware, ddos, ransomware).
        severity: Incident severity — low, medium, high, or critical.
        context: Optional free-text context about the specific incident to
                 make recommendations more relevant.

    Returns:
        dict with keys:
          - status: "success" or "fallback"
          - attack_type, severity
          - containment: list of immediate containment actions
          - eradication: list of eradication steps
          - recovery: list of recovery actions
          - prevention: list of long-term prevention measures
          - priority: urgency label (immediate | high | medium | low)
          - source: "llm" or "knowledge_base"
    """
    normalised_at = attack_type.lower().replace(" ", "_").replace("-", "_")
    normalised_sev = severity.lower() if severity else "medium"

    # Attempt to call the backend analysis endpoint
    try:
        incident_text = f"Attack type: {attack_type}. Severity: {severity}."
        if context:
            incident_text += f" Additional context: {context}"

        payload = {"incident_text": incident_text, "severity": normalised_sev}
        url = f"{BACKEND_URL}{API_V1}/analyze/analyze-incident"

        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            response = await client.post(url, json=payload, headers=_build_headers())
            response.raise_for_status()
            data = response.json()
            mitigation = data.get("mitigation", {})

            if mitigation:
                return {
                    "status": "success",
                    "attack_type": attack_type,
                    "severity": severity,
                    "containment": mitigation.get("containment", []),
                    "eradication": mitigation.get("eradication", []),
                    "recovery": mitigation.get("recovery", []),
                    "prevention": mitigation.get("prevention", []),
                    "priority": _severity_to_priority(normalised_sev),
                    "source": "llm",
                    "explanation": data.get("explanation", ""),
                    "escalation_level": data.get("escalation_level", "L1"),
                }
    except Exception as exc:
        logger.warning("recommend_mitigation: backend call failed — using KB fallback: %s", exc)

    # Fallback: use built-in mitigation templates
    templates = _MITIGATION_KB.get(normalised_at) or _MITIGATION_KB.get(
        next((k for k in _MITIGATION_KB if normalised_at in k or k in normalised_at), "default"),
        _MITIGATION_KB["default"],
    )

    return {
        "status": "fallback",
        "attack_type": attack_type,
        "severity": severity,
        "containment": templates.get("containment", []),
        "eradication": templates.get("eradication", []),
        "recovery": templates.get("recovery", []),
        "prevention": templates.get("prevention", []),
        "priority": _severity_to_priority(normalised_sev),
        "source": "knowledge_base",
        "warning": "Backend unavailable — mitigation from static knowledge base.",
    }


def _severity_to_priority(severity: str) -> str:
    mapping = {"critical": "immediate", "high": "high", "medium": "medium", "low": "low"}
    return mapping.get(severity, "medium")


# ===========================================================================
# Tool 5 — calculate_risk_score
# ===========================================================================

async def calculate_risk_score(
    attack_type: str,
    severity: str,
    affected_assets: list,
    historical_count: int = 0,
) -> dict:
    """Calculate a composite risk score (0-100) with breakdown.

    Uses a weighted formula combining:
    - Impact score (based on severity and number of affected assets)
    - Likelihood score (based on attack-type base risk and historical frequency)
    - Asset criticality score (based on asset types and count)

    Args:
        attack_type: Attack category (e.g. ransomware, ddos, malware).
        severity: Incident severity — low, medium, high, or critical.
        affected_assets: List of affected asset identifiers (IPs, hostnames, services).
        historical_count: Number of similar incidents in the past 30 days.

    Returns:
        dict with keys:
          - status: "success"
          - risk_score: composite score 0–100
          - impact_score: 0–100
          - likelihood_score: 0–100
          - asset_criticality_score: 0–100
          - risk_level: critical | high | medium | low
          - breakdown: detailed calculation explanation
          - recommendations: list of priority actions based on score
    """
    normalised_at = attack_type.lower().replace(" ", "_").replace("-", "_")
    normalised_sev = severity.lower() if severity else "medium"

    # --- Impact ---
    sev_weight = _SEVERITY_WEIGHTS.get(normalised_sev, 0.40)
    asset_count = len(affected_assets) if isinstance(affected_assets, list) else 0
    asset_factor = min(1.0, 0.5 + asset_count * 0.1)  # 0.5 baseline, +0.1 per asset, cap at 1.0
    impact_score = round(sev_weight * asset_factor * 100, 1)

    # --- Likelihood ---
    base_risk = _ATTACK_TYPE_BASE_RISK.get(normalised_at, _ATTACK_TYPE_BASE_RISK["default"])
    # Historical frequency boosts likelihood
    hist_boost = min(0.20, historical_count * 0.02)  # +2% per prior incident, max +20%
    likelihood_score = round(min(1.0, base_risk + hist_boost) * 100, 1)

    # --- Asset criticality ---
    # Heuristic: certain strings suggest high-value assets
    high_value_keywords = {"database", "db", "prod", "production", "dc", "domain", "admin", "controller", "critical"}
    high_value_count = sum(
        1 for asset in (affected_assets or [])
        if any(kw in str(asset).lower() for kw in high_value_keywords)
    )
    asset_criticality_score = round(
        min(100.0, 30.0 + (high_value_count / max(asset_count, 1)) * 70.0), 1
    )

    # --- Composite ---
    composite = round(
        impact_score * 0.40 + likelihood_score * 0.35 + asset_criticality_score * 0.25, 1
    )
    composite = max(0.0, min(100.0, composite))

    # --- Risk level ---
    if composite >= 80:
        risk_level = "critical"
    elif composite >= 60:
        risk_level = "high"
    elif composite >= 35:
        risk_level = "medium"
    else:
        risk_level = "low"

    # --- Recommendations ---
    recommendations = _risk_recommendations(risk_level, normalised_at)

    return {
        "status": "success",
        "risk_score": composite,
        "impact_score": impact_score,
        "likelihood_score": likelihood_score,
        "asset_criticality_score": asset_criticality_score,
        "risk_level": risk_level,
        "breakdown": {
            "severity_weight": sev_weight,
            "asset_count": asset_count,
            "asset_factor": asset_factor,
            "base_attack_risk": base_risk,
            "historical_boost": hist_boost,
            "high_value_assets": high_value_count,
            "formula": "risk = impact(0.40) + likelihood(0.35) + asset_criticality(0.25)",
        },
        "recommendations": recommendations,
    }


def _risk_recommendations(risk_level: str, attack_type: str) -> List[str]:
    if risk_level == "critical":
        return [
            "IMMEDIATE: Escalate to CISO and SOC Manager",
            "Activate incident response team and war-room protocol",
            "Isolate all affected systems from the network NOW",
            "Engage external DFIR firm if internal capacity is insufficient",
            "Notify regulatory bodies within required timeframes",
        ]
    elif risk_level == "high":
        return [
            "Escalate to Tier 2 SOC analyst and security manager",
            "Initiate containment procedures within 1 hour",
            "Enable enhanced monitoring across adjacent systems",
            "Prepare executive incident summary",
        ]
    elif risk_level == "medium":
        return [
            "Assign to Tier 1 analyst for investigation",
            "Apply containment measures within 4 hours",
            "Review similar recent incidents for patterns",
        ]
    else:
        return [
            "Log incident for tracking and trend analysis",
            "Apply standard security hardening checklist",
            "Schedule review at next security meeting",
        ]


# ===========================================================================
# Tool 6 — create_incident_report
# ===========================================================================

async def create_incident_report(incident_data: dict) -> dict:
    """Create a structured incident report from analysis data.

    Formats a comprehensive incident report from the provided analysis data,
    then attempts to persist it via the backend report service.

    Args:
        incident_data: Dict containing incident details. Expected keys include:
            - incident_id (optional)
            - title (optional)
            - attack_type
            - severity
            - affected_assets (list)
            - source_ip (optional)
            - dest_ip (optional)
            - protocol (optional)
            - description
            - mitigation (dict with containment/eradication/recovery/prevention)
            - risk_score (optional)
            - analyst_notes (optional)

    Returns:
        dict with keys:
          - status: "success" or "error"
          - report: the formatted report dict
          - report_id: unique report identifier
          - created_at: ISO timestamp
    """
    now = datetime.now(timezone.utc)
    report_id = str(uuid.uuid4())

    attack_type = incident_data.get("attack_type", "unknown")
    severity = incident_data.get("severity", "unknown")
    title = incident_data.get("title") or f"{attack_type.title()} Incident — {now.strftime('%Y-%m-%d %H:%M UTC')}"
    description = incident_data.get("description", "No description provided.")
    affected_assets = incident_data.get("affected_assets", [])
    mitigation = incident_data.get("mitigation", {})
    risk_score = incident_data.get("risk_score")
    analyst_notes = incident_data.get("analyst_notes", "")

    # Build executive summary
    asset_summary = ", ".join(str(a) for a in affected_assets[:5]) if affected_assets else "unknown"
    if len(affected_assets) > 5:
        asset_summary += f" (+{len(affected_assets) - 5} more)"

    executive_summary = (
        f"A {severity.upper()} severity {attack_type} incident was detected affecting {asset_summary}. "
        f"{description[:500]}"
    )
    if risk_score is not None:
        executive_summary += f" Composite risk score: {risk_score}/100."

    report = {
        "report_id": report_id,
        "title": title,
        "created_at": now.isoformat(),
        "classification": "CONFIDENTIAL — INTERNAL USE ONLY",
        "severity": severity,
        "attack_type": attack_type,
        "incident_id": incident_data.get("incident_id"),
        "executive_summary": executive_summary,
        "technical_details": {
            "source_ip": incident_data.get("source_ip"),
            "dest_ip": incident_data.get("dest_ip"),
            "protocol": incident_data.get("protocol"),
            "affected_assets": affected_assets,
            "risk_score": risk_score,
            "description": description,
        },
        "timeline": [
            {"time": now.isoformat(), "event": "Incident report generated by CyberSentinel AI"},
        ],
        "mitigation_plan": {
            "containment": mitigation.get("containment", []),
            "eradication": mitigation.get("eradication", []),
            "recovery": mitigation.get("recovery", []),
            "prevention": mitigation.get("prevention", []),
        },
        "analyst_notes": analyst_notes,
        "generated_by": "CyberSentinel AI MCP Server",
        "version": "1.0",
    }

    # Attempt to persist via backend
    try:
        url = f"{BACKEND_URL}{API_V1}/ingest/incidents"
        backend_payload = {
            "attack_type": attack_type,
            "severity": severity,
            "raw_text": description,
            "source_ip": incident_data.get("source_ip"),
            "dest_ip": incident_data.get("dest_ip"),
            "protocol": incident_data.get("protocol"),
            "label": title,
        }
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            response = await client.post(url, json=backend_payload, headers=_build_headers())
            if response.status_code in (200, 201):
                saved = response.json()
                report["incident_id"] = str(saved.get("id", report.get("incident_id", "")))
                report["persisted"] = True
            else:
                report["persisted"] = False
    except Exception as exc:
        logger.warning("create_incident_report: could not persist to backend: %s", exc)
        report["persisted"] = False

    return {
        "status": "success",
        "report": report,
        "report_id": report_id,
        "created_at": now.isoformat(),
    }


# ===========================================================================
# Tool 7 — query_graph_relationships
# ===========================================================================

async def query_graph_relationships(
    incident_id: str | None = None,
    attack_type: str | None = None,
) -> dict:
    """Query Neo4j graph for relationships.

    Returns connected attack types, affected assets, mitigation nodes,
    and similar incidents from the knowledge graph.

    Args:
        incident_id: Optional UUID of a specific incident to explore.
        attack_type: Optional attack type to query relationships for.

    Returns:
        dict with keys:
          - status: "success", "fallback", or "error"
          - nodes: list of graph nodes
          - edges: list of graph edges
          - attack_type: the attack type (if resolved)
          - affected_assets: list of asset nodes
          - similar_incidents: list of similar incident IDs
          - mitigations: list of mitigation labels
    """
    if not incident_id and not attack_type:
        return {
            "status": "error",
            "error": "At least one of incident_id or attack_type must be provided.",
        }

    # Try to fetch from backend graph endpoint
    if incident_id:
        url = f"{BACKEND_URL}{API_V1}/search/incident/{incident_id}"
        try:
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                response = await client.get(url, headers=_build_headers())
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "status": "success",
                        "incident_id": incident_id,
                        "nodes": data.get("nodes", []),
                        "edges": data.get("edges", []),
                        "attack_type": data.get("attack_type"),
                        "affected_assets": data.get("affected_assets", []),
                        "similar_incidents": data.get("similar_incidents", []),
                        "mitigations": data.get("mitigations", []),
                    }
                elif response.status_code == 404:
                    return {"status": "error", "error": f"Incident '{incident_id}' not found in graph."}
        except Exception as exc:
            logger.warning("query_graph_relationships: backend call failed: %s", exc)

    # Fallback: build synthetic graph from KB
    normalised_at = (attack_type or "unknown").lower().replace(" ", "_").replace("-", "_")
    kb = _ATTACK_TYPE_KB.get(normalised_at, {})

    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []
    center_id = incident_id or f"at_{normalised_at}"

    if incident_id:
        nodes.append({"id": incident_id, "label": incident_id[:8], "type": "Incident", "properties": {}})

    if normalised_at != "unknown":
        at_node_id = f"at_{normalised_at}"
        nodes.append({"id": at_node_id, "label": normalised_at, "type": "AttackType", "properties": kb})
        if incident_id:
            edges.append({"source": incident_id, "target": at_node_id, "type": "INCIDENT_OF_TYPE", "properties": {}})

    mitigations = list(_MITIGATION_KB.get(normalised_at, _MITIGATION_KB["default"]).keys())
    for mit_key in mitigations:
        mit_id = f"mit_{normalised_at}_{mit_key}"
        nodes.append({"id": mit_id, "label": mit_key.title(), "type": "Mitigation", "properties": {}})
        edges.append({"source": at_node_id if normalised_at != "unknown" else center_id, "target": mit_id, "type": "MITIGATED_BY", "properties": {}})

    return {
        "status": "fallback",
        "warning": "Backend unavailable — synthetic graph from knowledge base.",
        "incident_id": incident_id,
        "nodes": nodes,
        "edges": edges,
        "attack_type": normalised_at,
        "affected_assets": [],
        "similar_incidents": [],
        "mitigations": mitigations,
    }


# ===========================================================================
# Tool 8 — store_feedback
# ===========================================================================

async def store_feedback(
    incident_id: str,
    rating: int,
    comment: str,
    mitigation_worked: bool,
) -> dict:
    """Store analyst feedback for an incident to improve future recommendations.

    Submits analyst feedback to the backend feedback service. This data is used
    to fine-tune recommendations and evaluate the quality of AI-generated mitigations.

    Args:
        incident_id: UUID of the incident being rated.
        rating: Satisfaction rating from 1 (very poor) to 5 (excellent).
        comment: Free-text analyst comment or notes about the incident handling.
        mitigation_worked: True if the suggested mitigation steps were effective.

    Returns:
        dict with keys:
          - status: "success" or "error"
          - feedback_id: UUID of the stored feedback record (or None on error)
          - message: human-readable result message
    """
    if not 1 <= rating <= 5:
        return {
            "status": "error",
            "error": "Rating must be between 1 and 5.",
            "feedback_id": None,
        }

    payload = {
        "incident_id": incident_id,
        "rating": rating,
        "comment": comment,
        "mitigation_worked": mitigation_worked,
    }
    url = f"{BACKEND_URL}{API_V1}/feedback/"
    logger.debug("store_feedback → %s", url)

    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            response = await client.post(url, json=payload, headers=_build_headers())
            response.raise_for_status()
            data = response.json()
            return {
                "status": "success",
                "feedback_id": str(data.get("id", "")),
                "message": f"Feedback stored successfully. Rating: {rating}/5, Mitigation worked: {mitigation_worked}.",
            }
    except httpx.HTTPStatusError as exc:
        error_detail = exc.response.text[:200]
        logger.warning("store_feedback: HTTP %d — %s", exc.response.status_code, error_detail)
        return {
            "status": "error",
            "error": f"Backend returned HTTP {exc.response.status_code}: {error_detail}",
            "feedback_id": None,
        }
    except Exception as exc:
        logger.warning("store_feedback: backend unreachable — %s", exc)
        # Generate a local feedback record ID so the caller has something to reference
        local_id = str(uuid.uuid4())
        logger.info("store_feedback: stored locally with id %s (will sync when backend is available)", local_id)
        return {
            "status": "queued",
            "feedback_id": local_id,
            "message": (
                "Backend unavailable — feedback queued locally. "
                f"Local reference ID: {local_id}. Rating: {rating}/5."
            ),
            "warning": "Feedback was not persisted to the database; retry when backend is reachable.",
        }
