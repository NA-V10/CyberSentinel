"""Escalation Agent for CyberSentinel AI.

Determines the appropriate escalation tier based on:
  - threat_class
  - threat_confidence
  - severity
  - number of similar historical incidents

Escalation levels:
  L1           — Low-severity / benign / low confidence
  L2           — Medium-severity / moderate confidence
  L3           — High-severity / complex threats
  SOC_Manager  — Critical + high-confidence DDoS / malware / APT indicators

Updates state keys: ``escalation_level``, ``escalation_reason``
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from loguru import logger

from backend.app.agents.state import AgentState

# ---------------------------------------------------------------------------
# Escalation rule tables
# ---------------------------------------------------------------------------

# Classes that immediately trigger SOC_Manager when combined with high severity
_SOC_MANAGER_CLASSES = {"malware", "ddos", "network_intrusion"}

# Classes that escalate to L3 at high/critical severity
_L3_CLASSES = {"unauthorized_access", "brute_force", "phishing"}

# Severity numeric weight
_SEVERITY_WEIGHT: Dict[str, int] = {
    "critical": 4,
    "high": 3,
    "medium": 2,
    "low": 1,
    "unknown": 1,
}


def _severity_weight(severity: Optional[str]) -> int:
    return _SEVERITY_WEIGHT.get((severity or "unknown").lower(), 1)


def _compute_escalation(
    threat_class: Optional[str],
    threat_confidence: float,
    severity: Optional[str],
    similar_count: int,
) -> tuple[str, str]:
    """Return *(level, reason)* for the current incident.

    Decision matrix
    ---------------
    1. Benign → L1 regardless.
    2. Critical severity + SOC_MANAGER_CLASSES + confidence ≥ 0.7 → SOC_Manager.
    3. High or Critical severity + SOC_MANAGER_CLASSES → L3.
    4. High or Critical severity + any class + confidence ≥ 0.8 → L3.
    5. Medium severity OR low confidence → L2.
    6. Low severity OR benign OR confidence < 0.5 → L1.
    7. Many similar incidents (≥ 10) bump level by one tier.
    """
    tc = (threat_class or "unknown").lower().strip()
    sev_w = _severity_weight(severity)

    if tc == "benign":
        reason = "Incident classified as benign with no immediate threat."
        level = "L1"
        if similar_count >= 10:
            reason += f" However, {similar_count} similar incidents detected — monitoring recommended."
        return level, reason

    # --- SOC Manager ---
    if tc in _SOC_MANAGER_CLASSES and sev_w >= 4 and threat_confidence >= 0.70:
        reason = (
            f"Critical-severity {tc.upper()} attack detected with "
            f"{threat_confidence:.0%} confidence. Immediate SOC Manager escalation required."
        )
        if similar_count >= 5:
            reason += f" {similar_count} similar historical incidents found — likely coordinated campaign."
        return "SOC_Manager", reason

    # Additional SOC Manager trigger: high severity malware/ddos + many prior incidents
    if tc in _SOC_MANAGER_CLASSES and sev_w >= 3 and similar_count >= 10:
        reason = (
            f"High-severity {tc.upper()} combined with {similar_count} similar incidents "
            "indicates a sustained threat actor campaign. Escalating to SOC Manager."
        )
        return "SOC_Manager", reason

    # --- L3 ---
    if sev_w >= 3 and (tc in _SOC_MANAGER_CLASSES or tc in _L3_CLASSES):
        reason = (
            f"High/critical severity {tc.upper()} ({threat_confidence:.0%} confidence). "
            "Senior analyst (L3) investigation required."
        )
        if similar_count >= 5:
            level = "SOC_Manager"
            reason += f" {similar_count} similar incidents suggest an active campaign — bumping to SOC Manager."
            return level, reason
        return "L3", reason

    if sev_w >= 3 and threat_confidence >= 0.80:
        reason = (
            f"High confidence ({threat_confidence:.0%}) high-severity incident. "
            "L3 analyst review needed."
        )
        return "L3", reason

    # --- L2 ---
    if sev_w == 2 or (0.50 <= threat_confidence < 0.80):
        reason = (
            f"Medium-severity {tc} at {threat_confidence:.0%} confidence. "
            "Standard L2 triage recommended."
        )
        if similar_count >= 5:
            reason += f" {similar_count} similar incidents detected — possible recurrence."
            return "L3", reason
        return "L2", reason

    # --- L1 (default) ---
    reason = (
        f"Low-severity {tc} incident ({threat_confidence:.0%} confidence). "
        "Routine L1 handling is sufficient."
    )
    return "L1", reason


async def escalation_agent(state: AgentState) -> Dict[str, Any]:
    """LangGraph node: determine the escalation tier.

    Parameters
    ----------
    state:
        Current agent state.

    Returns
    -------
    dict
        Partial state update with ``escalation_level`` and ``escalation_reason``.
    """
    logger.info("EscalationAgent started")

    threat_class: Optional[str] = state.get("threat_class")
    threat_confidence: float = float(state.get("threat_confidence") or 0.5)
    severity: Optional[str] = state.get("severity")
    similar_incidents: List[dict] = state.get("similar_incidents") or []
    similar_count = len(similar_incidents)

    level, reason = _compute_escalation(
        threat_class=threat_class,
        threat_confidence=threat_confidence,
        severity=severity,
        similar_count=similar_count,
    )

    logger.info(
        "EscalationAgent complete",
        level=level,
        reason=reason[:120],
        threat_class=threat_class,
        severity=severity,
        similar_count=similar_count,
    )

    # Optionally notify via WS
    cb = state.get("ws_callback")
    if cb is not None:
        try:
            msg = f"Escalation level determined: {level}."
            if asyncio.iscoroutinefunction(cb):
                await cb(msg)
            else:
                cb(msg)
        except Exception:
            pass

    return {
        "escalation_level": level,
        "escalation_reason": reason,
    }
