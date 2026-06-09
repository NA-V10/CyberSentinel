"""Explainability Agent for CyberSentinel AI.

Generates a concise, human-readable natural-language explanation covering:
  - Why this threat class was assigned
  - What evidence was found in similar historical incidents
  - Why this escalation level was chosen
  - High-level summary of recommended mitigations

Updates state key: ``explanation``
Sends WebSocket status: "Generating explanation..."
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List, Optional

from loguru import logger
from openai import AsyncOpenAI

from backend.app.agents.state import AgentState
from backend.app.core.config import settings

# ---------------------------------------------------------------------------
# LLM prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are a senior cybersecurity analyst writing an explanation of an AI-generated
incident response for a human analyst.

Write a clear, concise explanation (3-5 paragraphs) that covers:
1. Why the incident was classified as this threat type (cite evidence from the
   incident description and any similar historical incidents).
2. The key risk indicators that drove the confidence score.
3. Why the chosen escalation level is appropriate.
4. A brief summary of the recommended response actions.

Tone: professional, factual, jargon-aware (the reader is a security analyst).
Do NOT hallucinate details not present in the data provided.
Output plain text only — no markdown headers, no bullet points.
"""

_USER_TEMPLATE = """\
=== INCIDENT DETAILS ===
Description  : {incident_text}
Source IP    : {source_ip}
Destination  : {dest_ip}
Protocol     : {protocol}
Severity     : {severity}

=== AI CLASSIFICATION ===
Threat class       : {threat_class}
Confidence         : {threat_confidence:.0%}
Escalation level   : {escalation_level}
Escalation reason  : {escalation_reason}

=== SIMILAR INCIDENTS ({similar_count}) ===
{similar_incidents_text}

=== CITATIONS ===
{citations_text}

=== MITIGATION SUMMARY ===
Containment  : {containment_summary}
Eradication  : {eradication_summary}
Recovery     : {recovery_summary}
Prevention   : {prevention_summary}

Write the explanation now.
"""


def _summarise_phase(phase: Optional[List[str]]) -> str:
    if not phase:
        return "N/A"
    return "; ".join(phase[:2]) + ("..." if len(phase) > 2 else "")


def _format_similar(incidents: List[dict], limit: int = 3) -> str:
    if not incidents:
        return "No similar historical incidents found."
    lines = []
    for inc in incidents[:limit]:
        lines.append(
            f"- ID: {inc.get('id', 'N/A')} | "
            f"Attack: {inc.get('attack_type', 'N/A')} | "
            f"Severity: {inc.get('severity', 'N/A')} | "
            f"Score: {inc.get('score', 0):.2f}"
        )
    return "\n".join(lines)


def _format_citations(citations: List[dict], limit: int = 3) -> str:
    if not citations:
        return "No citations available."
    lines = []
    for c in citations[:limit]:
        lines.append(
            f"[{c.get('ref', '?')}] {c.get('incident_id', 'N/A')} — "
            f"{c.get('attack_type', 'N/A')} | Score: {c.get('score', 0):.3f}"
        )
    return "\n".join(lines)


def _build_fallback_explanation(state: AgentState) -> str:
    """Minimal rule-based explanation used when the LLM call fails."""
    tc = state.get("threat_class") or "unknown"
    conf = float(state.get("threat_confidence") or 0.5)
    level = state.get("escalation_level") or "L1"
    reason = state.get("escalation_reason") or ""
    similar_count = len(state.get("similar_incidents") or [])

    mitigation = state.get("mitigation") or {}
    containment = _summarise_phase(mitigation.get("containment"))

    return (
        f"The incident has been classified as a {tc.upper()} attack with "
        f"{conf:.0%} confidence based on the provided indicators. "
        f"{similar_count} similar historical incidents were identified in the knowledge base. "
        f"The recommended escalation tier is {level}. {reason} "
        f"Immediate containment actions include: {containment}. "
        "Please review the full mitigation plan for complete remediation guidance."
    )


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


async def explainability_agent(state: AgentState) -> Dict[str, Any]:
    """LangGraph node: generate a human-readable explanation.

    Parameters
    ----------
    state:
        Current agent state.

    Returns
    -------
    dict
        Partial state update with ``explanation``.
    """
    await _send_ws(state, "Generating explanation...")
    logger.info("ExplainabilityAgent started")

    mitigation: dict = state.get("mitigation") or {}

    user_message = _USER_TEMPLATE.format(
        incident_text=(state.get("incident_text") or "")[:1000],
        source_ip=state.get("source_ip") or "N/A",
        dest_ip=state.get("dest_ip") or "N/A",
        protocol=state.get("protocol") or "N/A",
        severity=state.get("severity") or "N/A",
        threat_class=state.get("threat_class") or "unknown",
        threat_confidence=float(state.get("threat_confidence") or 0.5),
        escalation_level=state.get("escalation_level") or "L1",
        escalation_reason=state.get("escalation_reason") or "",
        similar_count=len(state.get("similar_incidents") or []),
        similar_incidents_text=_format_similar(state.get("similar_incidents") or []),
        citations_text=_format_citations(state.get("citations") or []),
        containment_summary=_summarise_phase(mitigation.get("containment")),
        eradication_summary=_summarise_phase(mitigation.get("eradication")),
        recovery_summary=_summarise_phase(mitigation.get("recovery")),
        prevention_summary=_summarise_phase(mitigation.get("prevention")),
    )

    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    explanation: Optional[str] = None

    try:
        response = await client.chat.completions.create(
            model=settings.OPENAI_CHAT_MODEL,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0.3,
            max_tokens=600,
        )
        explanation = (response.choices[0].message.content or "").strip()
        if len(explanation) < 50:
            explanation = None
    except Exception as exc:
        logger.error("ExplainabilityAgent LLM call failed", error=str(exc))

    if not explanation:
        explanation = _build_fallback_explanation(state)
        logger.info("ExplainabilityAgent: using rule-based fallback explanation")

    await _send_ws(state, "Explanation generated.")
    logger.info("ExplainabilityAgent complete", chars=len(explanation))

    return {"explanation": explanation}
