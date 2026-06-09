"""Threat Classification Agent for CyberSentinel AI.

Uses OpenAI GPT-4.1-mini to classify the incident into one of:
  phishing | malware | DDoS | brute_force | unauthorized_access |
  network_intrusion | benign

Updates state keys: ``threat_class``, ``threat_confidence``
Sends WebSocket status: "Classifying threat..."
"""

from __future__ import annotations

import asyncio
import json
import re
from typing import Any, Dict

from loguru import logger
from openai import AsyncOpenAI

from backend.app.agents.state import AgentState
from backend.app.core.config import settings

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_ALLOWED_CLASSES = {
    "phishing",
    "malware",
    "ddos",
    "brute_force",
    "unauthorized_access",
    "network_intrusion",
    "benign",
}

_SYSTEM_PROMPT = """\
You are a cybersecurity threat classification engine.
Analyse the provided incident description and classify it into exactly ONE
of the following categories:
  phishing, malware, ddos, brute_force, unauthorized_access, network_intrusion, benign

Rules:
- Return ONLY valid JSON — no markdown, no extra text.
- The JSON must contain exactly two keys:
    "threat_class"  : one of the allowed class strings (lowercase)
    "confidence"    : a float between 0.0 and 1.0

Example output:
{"threat_class": "brute_force", "confidence": 0.93}
"""

_USER_TEMPLATE = """\
Incident description:
{incident_text}

Additional context:
- Source IP  : {source_ip}
- Dest IP    : {dest_ip}
- Protocol   : {protocol}
- Severity   : {severity}

Classify this incident.
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
    """Extract the first JSON object from *text*, even if surrounded by prose."""
    # Try direct parse first
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    # Fallback: find {...} block
    match = re.search(r"\{[^{}]+\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    return {}


async def classification_agent(state: AgentState) -> Dict[str, Any]:
    """LangGraph node: classify the threat using GPT-4.1-mini.

    Parameters
    ----------
    state:
        Current agent state.

    Returns
    -------
    dict
        Partial state update with ``threat_class`` and ``threat_confidence``.
    """
    await _send_ws(state, "Classifying threat...")
    logger.info("ClassificationAgent started")

    user_message = _USER_TEMPLATE.format(
        incident_text=state.get("incident_text", ""),
        source_ip=state.get("source_ip") or "N/A",
        dest_ip=state.get("dest_ip") or "N/A",
        protocol=state.get("protocol") or "N/A",
        severity=state.get("severity") or "N/A",
    )

    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    try:
        response = await client.chat.completions.create(
            model=settings.OPENAI_CHAT_MODEL,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0.0,
            max_tokens=128,
            response_format={"type": "json_object"},
        )
        raw_content = response.choices[0].message.content or "{}"
        result = _extract_json(raw_content)
    except Exception as exc:
        logger.error("ClassificationAgent LLM call failed", error=str(exc))
        result = {}

    # --- validate / normalise LLM output ---
    raw_class: str = str(result.get("threat_class", "network_intrusion")).lower().strip()
    if raw_class not in _ALLOWED_CLASSES:
        logger.warning(
            "ClassificationAgent returned unknown class, defaulting",
            raw=raw_class,
        )
        raw_class = "network_intrusion"

    try:
        confidence = float(result.get("confidence", 0.5))
        confidence = max(0.0, min(1.0, confidence))
    except (TypeError, ValueError):
        confidence = 0.5

    logger.info(
        "ClassificationAgent complete",
        threat_class=raw_class,
        confidence=confidence,
    )
    await _send_ws(state, f"Threat classified as '{raw_class}' (confidence: {confidence:.0%}).")

    return {
        "threat_class": raw_class,
        "threat_confidence": confidence,
    }
