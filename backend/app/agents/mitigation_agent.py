"""Mitigation Agent for CyberSentinel AI.

Generates a four-phase incident response plan:
  containment | eradication | recovery | prevention

Uses the RAG context + OpenAI GPT-4.1-mini.  Falls back to a hardcoded
lookup table if the LLM call fails.

Updates state key: ``mitigation``
Sends WebSocket status: "Generating mitigation..."
"""

from __future__ import annotations

import asyncio
import json
import re
from typing import Any, Dict, List, Optional

from loguru import logger
from openai import AsyncOpenAI

from backend.app.agents.state import AgentState
from backend.app.core.config import settings

# ---------------------------------------------------------------------------
# Hardcoded fallback mitigations by attack type
# ---------------------------------------------------------------------------

_FALLBACK_MITIGATIONS: Dict[str, Dict[str, List[str]]] = {
    "brute_force": {
        "containment": [
            "Block the offending source IP at the perimeter firewall immediately.",
            "Lock or disable the targeted user account temporarily.",
            "Terminate all active sessions for the affected account.",
        ],
        "eradication": [
            "Audit authentication logs to identify all affected accounts.",
            "Reset passwords for compromised or at-risk accounts.",
            "Remove any persistence mechanisms (scheduled tasks, cron jobs) created by attacker.",
        ],
        "recovery": [
            "Re-enable accounts after forcing a password reset.",
            "Restore any modified configuration files from backup.",
            "Monitor the account closely for 48 hours after restoration.",
        ],
        "prevention": [
            "Enforce multi-factor authentication (MFA) on all accounts.",
            "Implement account lockout policy after 5 failed attempts.",
            "Deploy rate-limiting on login endpoints.",
            "Enable geo-blocking or conditional access policies.",
            "Alert on login attempts from unusual geolocations.",
        ],
    },
    "ddos": {
        "containment": [
            "Enable upstream DDoS scrubbing service or CDN-level traffic filtering.",
            "Rate-limit traffic from the attacking IP ranges at the border router.",
            "Activate null-route (blackhole routing) for the most aggressive source ranges.",
        ],
        "eradication": [
            "Work with ISP to apply upstream ACLs filtering attack traffic.",
            "Identify and sinkhole command-and-control (C2) domains used by botnet.",
            "Purge attacker-injected entries from any manipulated DNS zones.",
        ],
        "recovery": [
            "Gradually restore normal traffic routing as attack subsides.",
            "Validate application availability and performance metrics.",
            "Review and increase auto-scaling thresholds for critical services.",
        ],
        "prevention": [
            "Subscribe to a dedicated DDoS mitigation service (e.g. Cloudflare, AWS Shield).",
            "Implement anycast network diffusion for load distribution.",
            "Configure SYN cookies on all public-facing servers.",
            "Set up real-time traffic anomaly detection and auto-response playbooks.",
            "Publish BCP38/BCP84 ingress filtering to prevent spoofed packets.",
        ],
    },
    "phishing": {
        "containment": [
            "Isolate any endpoints that clicked on the phishing link.",
            "Block the phishing domain and sender address at the email gateway.",
            "Revoke compromised OAuth tokens or SSO sessions.",
        ],
        "eradication": [
            "Delete phishing emails from all mailboxes using admin purge.",
            "Remove malicious attachments or downloaded payloads.",
            "Scan all endpoints involved for malware using EDR tooling.",
        ],
        "recovery": [
            "Reset credentials for all users who interacted with the phishing content.",
            "Re-enable email flow after confirming the attack vector is eliminated.",
            "Restore data from backup if any ransomware was deployed.",
        ],
        "prevention": [
            "Enable DMARC, DKIM, and SPF on all corporate email domains.",
            "Deploy AI-powered email filtering with URL sandboxing.",
            "Conduct regular phishing simulation training for all employees.",
            "Enforce MFA on all email and SaaS accounts.",
            "Implement browser isolation for high-risk users.",
        ],
    },
    "malware": {
        "containment": [
            "Immediately isolate infected hosts from the network (VLAN quarantine or physical disconnect).",
            "Block identified malware C2 IP addresses and domains at the firewall.",
            "Disable affected service accounts and revoke credentials.",
        ],
        "eradication": [
            "Run full forensic scan with updated EDR signatures.",
            "Remove malware binaries, registry keys, and persistence artefacts.",
            "Patch the vulnerability exploited during initial compromise.",
        ],
        "recovery": [
            "Rebuild compromised systems from gold-image if full remediation is uncertain.",
            "Restore data from last-known-good backup after verifying integrity.",
            "Re-join systems to the domain with new credentials.",
        ],
        "prevention": [
            "Enforce application allowlisting to prevent unauthorised binary execution.",
            "Keep all systems and software fully patched using automated patch management.",
            "Deploy behaviour-based EDR with real-time alerting.",
            "Implement least-privilege principles (remove local admin rights).",
            "Segment the network to limit lateral movement.",
        ],
    },
    "network_intrusion": {
        "containment": [
            "Block the attacker's IP at the edge firewall and intrusion prevention system.",
            "Isolate the compromised network segment using VLAN controls.",
            "Terminate all unauthorised active connections identified in session logs.",
        ],
        "eradication": [
            "Review firewall and router configurations for backdoor rules.",
            "Remove any rogue devices or unauthorised access points discovered.",
            "Patch exploited vulnerabilities in network infrastructure.",
        ],
        "recovery": [
            "Restore network device configurations from verified backup.",
            "Re-validate all ACLs and firewall rules after restoration.",
            "Monitor network traffic for residual indicators of compromise (IoCs).",
        ],
        "prevention": [
            "Implement Zero Trust Network Access (ZTNA) architecture.",
            "Deploy a next-generation IDS/IPS with threat-intelligence feeds.",
            "Enable encrypted management protocols (SSH, HTTPS) and disable Telnet/HTTP.",
            "Conduct regular penetration testing and vulnerability assessments.",
            "Enforce network segmentation and micro-segmentation for critical assets.",
        ],
    },
    "unauthorized_access": {
        "containment": [
            "Disable the compromised account or service immediately.",
            "Revoke all active sessions and API tokens for the affected identity.",
            "Block egress connections to unknown external IPs from the affected host.",
        ],
        "eradication": [
            "Audit access logs to determine the full scope of unauthorized access.",
            "Remove any backdoor accounts or SSH keys created by the attacker.",
            "Review and harden IAM policies and role assignments.",
        ],
        "recovery": [
            "Restore normal account access after credential rotation and audit.",
            "Verify data integrity for any resources the attacker accessed.",
            "Notify affected parties if sensitive data was accessed.",
        ],
        "prevention": [
            "Enforce MFA and conditional access policies for all privileged accounts.",
            "Implement Privileged Access Management (PAM) solution.",
            "Enable just-in-time (JIT) access for administrative privileges.",
            "Set up SIEM alerts for anomalous access patterns (off-hours, new locations).",
            "Conduct regular access reviews and remove stale accounts.",
        ],
    },
    "benign": {
        "containment": ["No containment action required — incident classified as benign."],
        "eradication": ["No eradication required."],
        "recovery": ["No recovery action needed."],
        "prevention": [
            "Review detection rules to minimise false-positive alerts.",
            "Document the false positive to improve future classification accuracy.",
        ],
    },
}

_DEFAULT_MITIGATION = _FALLBACK_MITIGATIONS["network_intrusion"]

# ---------------------------------------------------------------------------
# LLM prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are an expert cybersecurity incident responder.
Generate a structured four-phase incident response plan for the provided incident.

Return ONLY valid JSON with exactly these four top-level keys:
  "containment"  : list of strings (immediate actions to stop the threat)
  "eradication"  : list of strings (steps to remove the threat completely)
  "recovery"     : list of strings (steps to restore normal operations)
  "prevention"   : list of strings (long-term controls to prevent recurrence)

Each list must contain 3–6 specific, actionable steps.
Base your recommendations on the incident details and the RAG context provided.
No markdown, no extra commentary — pure JSON only.
"""

_USER_TEMPLATE = """\
Incident description:
{incident_text}

Threat class   : {threat_class}
Threat confidence: {threat_confidence:.0%}
Severity       : {severity}
Source IP      : {source_ip}
Destination IP : {dest_ip}
Protocol       : {protocol}

Relevant historical context (RAG):
{rag_context}

Generate the four-phase mitigation plan.
"""


async def _send_ws(state: AgentState, message: str) -> None:
    cb = state.get("ws_callback")
    if cb is not None:
        try:
            if asyncio.iscoroutinefunction(cb):
                await cb(message)
            else:
                cb(message)
        except Exception as exc:
            logger.warning("WS callback failed", error=str(exc))


def _extract_json(text: str) -> Optional[dict]:
    """Return first JSON object found in *text*, or None."""
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{[\s\S]+\}", text)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return None


def _get_fallback(threat_class: Optional[str]) -> dict:
    """Return hardcoded mitigation for *threat_class*, or a generic default."""
    key = (threat_class or "").lower().strip()
    return dict(_FALLBACK_MITIGATIONS.get(key, _DEFAULT_MITIGATION))


def _validate_mitigation(mitigation: Any) -> bool:
    """Check that the LLM-generated mitigation has all required phases."""
    if not isinstance(mitigation, dict):
        return False
    required = {"containment", "eradication", "recovery", "prevention"}
    for phase in required:
        val = mitigation.get(phase)
        if not isinstance(val, list) or len(val) == 0:
            return False
    return True


async def mitigation_agent(state: AgentState) -> Dict[str, Any]:
    """LangGraph node: generate a four-phase mitigation plan.

    Parameters
    ----------
    state:
        Current agent state.

    Returns
    -------
    dict
        Partial state update with ``mitigation`` dict.
    """
    await _send_ws(state, "Generating mitigation...")
    logger.info("MitigationAgent started")

    threat_class: Optional[str] = state.get("threat_class")
    rag_context: str = state.get("rag_context") or "No historical context available."

    user_message = _USER_TEMPLATE.format(
        incident_text=state.get("incident_text", ""),
        threat_class=threat_class or "unknown",
        threat_confidence=state.get("threat_confidence") or 0.5,
        severity=state.get("severity") or "unknown",
        source_ip=state.get("source_ip") or "N/A",
        dest_ip=state.get("dest_ip") or "N/A",
        protocol=state.get("protocol") or "N/A",
        rag_context=rag_context[:3000],  # stay within context window
    )

    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    mitigation: Optional[dict] = None

    try:
        response = await client.chat.completions.create(
            model=settings.OPENAI_CHAT_MODEL,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0.2,
            max_tokens=1024,
            response_format={"type": "json_object"},
        )
        raw_content = response.choices[0].message.content or "{}"
        parsed = _extract_json(raw_content)
        if parsed and _validate_mitigation(parsed):
            mitigation = parsed
            logger.info("MitigationAgent: LLM mitigation generated successfully")
        else:
            logger.warning(
                "MitigationAgent: LLM output failed validation, using fallback",
                raw=str(raw_content)[:200],
            )
    except Exception as exc:
        logger.error("MitigationAgent LLM call failed", error=str(exc))

    if mitigation is None:
        mitigation = _get_fallback(threat_class)
        logger.info("MitigationAgent: using fallback mitigation", threat_class=threat_class)

    await _send_ws(state, "Mitigation plan generated.")
    return {"mitigation": mitigation}
