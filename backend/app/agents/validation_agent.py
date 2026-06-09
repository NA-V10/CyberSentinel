"""Input Validation Agent for CyberSentinel AI.

Validates:
- Incident text (length, content)
- IP addresses (source / destination)
- Severity label
- Prompt-injection attempts

Updates state keys: ``is_valid``, ``validation_error``
Sends WebSocket status update: "Validating input..."
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict

from loguru import logger

from backend.app.agents.state import AgentState
from backend.app.guardrails.validator import validate_incident_input


async def _send_ws(state: AgentState, message: str) -> None:
    """Fire-and-forget WebSocket status update."""
    cb = state.get("ws_callback")
    if cb is not None:
        try:
            if asyncio.iscoroutinefunction(cb):
                await cb(message)
            else:
                cb(message)
        except Exception as exc:  # pragma: no cover
            logger.warning("WS callback failed", error=str(exc))


async def validation_agent(state: AgentState) -> Dict[str, Any]:
    """LangGraph node: validate all incident input fields.

    Parameters
    ----------
    state:
        Current agent state.

    Returns
    -------
    dict
        Partial state update containing ``is_valid`` and optionally
        ``validation_error``.
    """
    await _send_ws(state, "Validating input...")
    logger.info("ValidationAgent started", user_id=state.get("user_id"))

    incident_text: str = state.get("incident_text", "")
    source_ip = state.get("source_ip")
    dest_ip = state.get("dest_ip")
    severity = state.get("severity")

    is_valid, error_msg = validate_incident_input(
        text=incident_text,
        source_ip=source_ip,
        dest_ip=dest_ip,
        severity=severity,
    )

    if is_valid:
        logger.info("ValidationAgent: input is valid")
        await _send_ws(state, "Input validation passed.")
        return {"is_valid": True, "validation_error": None}
    else:
        logger.warning(
            "ValidationAgent: input is invalid",
            reason=error_msg,
            user_id=state.get("user_id"),
        )
        await _send_ws(state, f"Validation failed: {error_msg}")
        return {
            "is_valid": False,
            "validation_error": error_msg,
            "final_answer": f"Input validation failed: {error_msg}",
        }
