"""Self-Reflection Agent — evaluates and improves initial analysis quality."""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from loguru import logger

from backend.app.services.self_reflection_service import run_self_reflection

_REFLECTION_SCORE_THRESHOLD = 7.5


async def self_reflection_node(
    state: Dict[str, Any],
    ws_callback: Optional[Callable] = None,
) -> Dict[str, Any]:
    """LangGraph-compatible node that runs the self-reflection loop.

    Integrates into the existing workflow after judge_node.
    Triggers re-analysis if judge_score is below threshold.
    """
    judge_score = state.get("judge_score", 10.0)
    incident_text = state.get("incident_text", "")
    session_id = state.get("session_id", "")

    async def emit(event: str, data: Dict[str, Any]) -> None:
        if ws_callback:
            try:
                await ws_callback({"event": event, "data": data})
            except Exception:
                pass

    await emit("self_reflection_started", {
        "session_id": session_id,
        "judge_score": judge_score,
        "threshold": _REFLECTION_SCORE_THRESHOLD,
    })

    # Build the initial analysis dict from state
    initial_analysis: Dict[str, Any] = {
        "threat_class": state.get("threat_class"),
        "threat_confidence": state.get("threat_confidence"),
        "severity": state.get("severity"),
        "mitigation": state.get("mitigation"),
        "explanation": state.get("explanation"),
        "judge_score": judge_score,
        "judge_feedback": state.get("judge_feedback"),
    }

    org_id = state.get("org_id", "default")
    user_id = state.get("user_id", "system")
    incident_id = state.get("incident_id")

    reflection = await run_self_reflection(
        incident_text=incident_text,
        initial_analysis=initial_analysis,
        judge_score=judge_score,
        org_id=org_id,
        user_id=user_id,
        incident_id=incident_id,
    )

    if reflection.get("weaknesses_detected"):
        await emit("weaknesses_detected", {
            "weaknesses": reflection["weaknesses_detected"],
            "count": len(reflection["weaknesses_detected"]),
        })

    if reflection.get("additional_retrieval_required"):
        await emit("additional_retrieval_requested", {
            "missing_evidence": reflection.get("missing_evidence", []),
        })

    if reflection.get("reflection_triggered") and reflection.get("improved_analysis"):
        await emit("analysis_improved", {
            "final_confidence": reflection.get("final_confidence"),
            "before_after": reflection.get("before_after_comparison"),
        })

    await emit("self_reflection_completed", {
        "final_confidence": reflection.get("final_confidence"),
        "reflection_triggered": reflection.get("reflection_triggered", False),
    })

    # Update state with reflection results
    updated_state = {**state, "self_reflection": reflection}

    # If improved analysis exists, update explanation and mitigation
    if reflection.get("reflection_triggered") and reflection.get("improved_analysis"):
        import json
        try:
            improved = json.loads(reflection["improved_analysis"])
            if improved.get("improved_mitigation"):
                updated_state["mitigation"] = {
                    **state.get("mitigation", {}),
                    "improved": improved["improved_mitigation"],
                    "reflection_applied": True,
                }
            if improved.get("improved_reasoning"):
                current_explanation = state.get("explanation", "")
                updated_state["explanation"] = (
                    current_explanation
                    + "\n\n---\n**Self-Reflection Improvement:**\n"
                    + improved["improved_reasoning"]
                )
        except (json.JSONDecodeError, TypeError):
            pass

    logger.info(
        "Self-reflection agent complete",
        triggered=reflection.get("reflection_triggered"),
        confidence=reflection.get("final_confidence"),
        session_id=session_id,
    )
    return updated_state


def should_reflect(state: Dict[str, Any]) -> str:
    """Conditional edge: determine if self-reflection should be triggered."""
    judge_score = state.get("judge_score", 10.0)
    retry_count = state.get("retry_count", 0)

    if judge_score < _REFLECTION_SCORE_THRESHOLD and retry_count < 1:
        return "reflect"
    return "skip_reflection"


class SelfReflectionAgent:
    """Wrapper class for integration into the multi-agent orchestration system."""

    THRESHOLD = _REFLECTION_SCORE_THRESHOLD

    async def run(
        self,
        incident_text: str,
        initial_analysis: Dict[str, Any],
        judge_score: float,
        org_id: str = "default",
        user_id: str = "system",
        incident_id: Optional[str] = None,
        ws_callback: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        """Run standalone self-reflection analysis."""
        return await run_self_reflection(
            incident_text=incident_text,
            initial_analysis=initial_analysis,
            judge_score=judge_score,
            org_id=org_id,
            user_id=user_id,
            incident_id=incident_id,
        )
