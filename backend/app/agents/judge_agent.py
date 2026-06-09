"""LLM-as-Judge Agent for CyberSentinel AI.

Validates the final assembled answer for:
  - Quality        (0–10 score)
  - Safety         (no harmful / dangerous content)
  - Completeness   (all four mitigation phases present, explanation non-empty)
  - Hallucination  risk (low / medium / high)

Updates state keys: ``judge_score``, ``judge_feedback``, ``is_safe``

Scoring rules:
  - Raw LLM quality score / 10 → normalised judge_score (0.0 – 1.0)
  - If quality < 5 OR safety == false → is_safe = False
  - is_safe = False triggers one retry of the mitigation + explainability cycle

Sends WebSocket status: "Running judge validation..."
"""

from __future__ import annotations

import asyncio
import json
import re
from typing import Any, Dict, Optional

from loguru import logger
from openai import AsyncOpenAI

from backend.app.agents.state import AgentState
from backend.app.core.config import settings

# ---------------------------------------------------------------------------
# LLM prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are an expert AI quality judge for a cybersecurity incident response system.

Evaluate the provided incident analysis on four dimensions and return ONLY valid JSON.

JSON schema:
{
  "quality_score"      : <integer 0-10>,
  "is_safe"            : <true|false>,
  "completeness_score" : <integer 0-10>,
  "hallucination_risk" : <"low"|"medium"|"high">,
  "feedback"           : "<one-sentence summary of the main issue, if any>"
}

Scoring guidance:
  quality_score      : 10 = excellent, comprehensive, actionable; 0 = unusable
  is_safe            : false if the response contains dangerous advice, explicit
                       exploit instructions, or promotes harmful activity
  completeness_score : 10 = all four mitigation phases present and non-empty,
                       explanation present; deduct 2 per missing element
  hallucination_risk : low = all claims are plausible given the incident;
                       medium = minor unsupported claims;
                       high = significant fabricated details

Be strict: a score < 5 or is_safe = false means the answer must be regenerated.
"""

_USER_TEMPLATE = """\
=== INCIDENT SUMMARY ===
Description  : {incident_text}
Threat class : {threat_class} ({threat_confidence:.0%} confidence)
Severity     : {severity}

=== MITIGATION PLAN ===
Containment  : {containment}
Eradication  : {eradication}
Recovery     : {recovery}
Prevention   : {prevention}

=== ESCALATION ===
Level  : {escalation_level}
Reason : {escalation_reason}

=== EXPLANATION ===
{explanation}

Evaluate the above analysis now.
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


def _extract_json(text: str) -> dict:
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
    return {}


def _phase_to_str(phase: Any) -> str:
    if isinstance(phase, list):
        return "; ".join(str(p) for p in phase[:3])
    return str(phase or "N/A")


def _rule_based_judge(state: AgentState) -> Dict[str, Any]:
    """Fallback judge when the LLM call fails."""
    mitigation: dict = state.get("mitigation") or {}
    explanation: str = state.get("explanation") or ""

    # Check completeness
    phases = ["containment", "eradication", "recovery", "prevention"]
    missing = [p for p in phases if not mitigation.get(p)]
    completeness = 10 - (2 * len(missing))

    # Check explanation
    if len(explanation) < 50:
        completeness -= 2

    completeness = max(0, completeness)
    quality = min(completeness, 8)  # cap at 8 for fallback
    is_safe = True  # assume safe if LLM judge unavailable

    feedback = (
        f"Rule-based evaluation: {completeness}/10 completeness."
        + (f" Missing phases: {missing}." if missing else "")
    )

    normalised_score = round(quality / 10.0, 3)
    return {
        "judge_score": normalised_score,
        "judge_feedback": feedback,
        "is_safe": is_safe,
    }


async def judge_agent(state: AgentState) -> Dict[str, Any]:
    """LangGraph node: validate the final answer with an LLM judge.

    Parameters
    ----------
    state:
        Current agent state.

    Returns
    -------
    dict
        Partial state update with ``judge_score``, ``judge_feedback``, ``is_safe``.
    """
    await _send_ws(state, "Running judge validation...")
    logger.info("JudgeAgent started")

    mitigation: dict = state.get("mitigation") or {}

    user_message = _USER_TEMPLATE.format(
        incident_text=(state.get("incident_text") or "")[:800],
        threat_class=state.get("threat_class") or "unknown",
        threat_confidence=float(state.get("threat_confidence") or 0.5),
        severity=state.get("severity") or "unknown",
        containment=_phase_to_str(mitigation.get("containment")),
        eradication=_phase_to_str(mitigation.get("eradication")),
        recovery=_phase_to_str(mitigation.get("recovery")),
        prevention=_phase_to_str(mitigation.get("prevention")),
        escalation_level=state.get("escalation_level") or "L1",
        escalation_reason=state.get("escalation_reason") or "",
        explanation=(state.get("explanation") or "")[:600],
    )

    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    result: Optional[dict] = None

    try:
        response = await client.chat.completions.create(
            model=settings.OPENAI_CHAT_MODEL,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0.0,
            max_tokens=256,
            response_format={"type": "json_object"},
        )
        raw_content = response.choices[0].message.content or "{}"
        result = _extract_json(raw_content)
    except Exception as exc:
        logger.error("JudgeAgent LLM call failed", error=str(exc))

    if not result:
        fallback = _rule_based_judge(state)
        logger.info("JudgeAgent: using rule-based fallback")
        await _send_ws(state, f"Judge score: {fallback['judge_score']:.2f} (rule-based).")
        return fallback

    # Parse LLM result
    try:
        raw_quality = int(result.get("quality_score", 7))
        raw_quality = max(0, min(10, raw_quality))
    except (TypeError, ValueError):
        raw_quality = 7

    is_safe: bool = bool(result.get("is_safe", True))
    hallucination_risk: str = str(result.get("hallucination_risk", "low")).lower()
    feedback: str = str(result.get("feedback", ""))

    # Penalise for high hallucination risk
    if hallucination_risk == "high":
        raw_quality = max(0, raw_quality - 2)
        is_safe = False

    normalised_score = round(raw_quality / 10.0, 3)

    # If score < 5 mark unsafe to trigger retry
    if raw_quality < 5:
        is_safe = False

    logger.info(
        "JudgeAgent complete",
        quality=raw_quality,
        normalised=normalised_score,
        is_safe=is_safe,
        hallucination=hallucination_risk,
    )

    status_msg = f"Judge score: {normalised_score:.2f} | Safe: {is_safe}"
    await _send_ws(state, status_msg)

    return {
        "judge_score": normalised_score,
        "judge_feedback": feedback,
        "is_safe": is_safe,
    }
