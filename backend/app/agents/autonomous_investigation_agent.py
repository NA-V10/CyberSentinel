"""Autonomous Investigation Agent — orchestrates full agentic investigation pipeline."""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from loguru import logger

from backend.app.services.autonomous_investigation_service import run_autonomous_investigation


class AutonomousInvestigationAgent:
    """Orchestrates the full autonomous investigation workflow using MCP tools.

    The investigation follows this pipeline:
      Threat Classification → Threat Intel → Graph Expansion → MITRE Mapping
      → Risk Assessment → Mitigation → Judge Validation
    """

    async def investigate(
        self,
        incident_text: str,
        source_ip: Optional[str] = None,
        severity: str = "high",
        org_id: str = "default",
        user_id: str = "system",
        incident_id: Optional[str] = None,
        ws_callback: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        """Run a complete autonomous investigation.

        Returns a full investigation report with tool call timeline,
        evidence chain, findings, and recommended actions.
        """
        logger.info(
            "Starting autonomous investigation",
            incident_id=incident_id,
            severity=severity,
            org_id=org_id,
        )

        result = await run_autonomous_investigation(
            incident_text=incident_text,
            source_ip=source_ip,
            severity=severity,
            org_id=org_id,
            user_id=user_id,
            incident_id=incident_id,
            ws_callback=ws_callback,
        )

        logger.info(
            "Autonomous investigation complete",
            investigation_id=result.get("investigation_id"),
            tool_calls=result.get("total_tool_calls", 0),
            duration=result.get("duration_seconds", 0),
        )
        return result


async def autonomous_investigation_node(
    state: Dict[str, Any],
    ws_callback: Optional[Callable] = None,
) -> Dict[str, Any]:
    """LangGraph-compatible node for autonomous investigation.

    Can be inserted into the existing workflow as an optional step
    when autonomous mode is enabled.
    """
    if not state.get("autonomous_mode", False):
        return state

    agent = AutonomousInvestigationAgent()
    result = await agent.investigate(
        incident_text=state.get("incident_text", ""),
        source_ip=state.get("source_ip"),
        severity=state.get("severity", "high"),
        org_id=state.get("org_id", "default"),
        user_id=state.get("user_id", "system"),
        incident_id=state.get("incident_id"),
        ws_callback=ws_callback,
    )

    return {
        **state,
        "autonomous_investigation": result,
        "tool_calls_timeline": result.get("tool_calls", []),
        "evidence_chain": result.get("evidence_chain", []),
    }
