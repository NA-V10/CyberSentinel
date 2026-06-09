"""
FastAPI WebSocket router for real-time incident analysis streaming.

Endpoint:
  WS /ws/analyze/{session_id}

The client connects, sends a JSON incident payload, and the server streams
progress updates for each agent step.  The final message carries the
complete analysis result.

Wire protocol (server → client)
--------------------------------
Status update::

    {
        "type": "status",
        "step": "<AnalysisStep value>",
        "message": "<human-readable progress message>",
        "data": { ... }            # optional per-step data
    }

Completion::

    {
        "type": "complete",
        "step": "complete",
        "result": { <AnalyzeIncidentResponse> }
    }

Error::

    {
        "type": "error",
        "step": "error",
        "message": "<summary>",
        "detail": "<optional detail>"
    }
"""

from __future__ import annotations

import traceback
import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from loguru import logger

from backend.app.agents.state import AgentState
from backend.app.websocket.handler import AnalysisStep, ConnectionManager, manager

router = APIRouter()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_incident_payload(data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract and normalise incident fields from a raw client JSON dict.

    Returns a dict compatible with :class:`~backend.app.agents.state.AgentState`.
    """
    return {
        "incident_text": str(data.get("incident_text") or data.get("text") or ""),
        "source_ip": data.get("source_ip"),
        "dest_ip": data.get("dest_ip"),
        "protocol": data.get("protocol"),
        "severity": data.get("severity"),
    }


async def _run_analysis_pipeline(
    session_id: str,
    user_id: str,
    incident_data: Dict[str, Any],
    conn_manager: ConnectionManager,
) -> None:
    """Execute the multi-agent analysis pipeline and stream progress to the client.

    Imports the LangGraph workflow lazily to avoid circular imports.

    Parameters
    ----------
    session_id:
        WebSocket session identifier.
    user_id:
        Authenticated user ID (from JWT or query param).
    incident_data:
        Parsed incident fields extracted from the client payload.
    conn_manager:
        The active :class:`~backend.app.websocket.handler.ConnectionManager`.
    """
    # ------------------------------------------------------------------ #
    # Build the WebSocket callback forwarded into each agent               #
    # ------------------------------------------------------------------ #

    step_sequence = [
        AnalysisStep.VALIDATION,
        AnalysisStep.CLASSIFICATION,
        AnalysisStep.RETRIEVAL,
        AnalysisStep.GRAPH_EXPANSION,
        AnalysisStep.MITIGATION,
        AnalysisStep.ESCALATION,
        AnalysisStep.EXPLANATION,
        AnalysisStep.JUDGE,
    ]
    step_messages: Dict[str, str] = {
        AnalysisStep.VALIDATION: "Validating incident input...",
        AnalysisStep.CLASSIFICATION: "Classifying threat type...",
        AnalysisStep.RETRIEVAL: "Retrieving similar incidents from vector store...",
        AnalysisStep.GRAPH_EXPANSION: "Expanding threat knowledge graph...",
        AnalysisStep.MITIGATION: "Generating mitigation playbook...",
        AnalysisStep.ESCALATION: "Determining escalation path...",
        AnalysisStep.EXPLANATION: "Composing threat explanation...",
        AnalysisStep.JUDGE: "Validating response quality...",
    }

    # Track current step for the WS callback
    _current_step: list = [AnalysisStep.VALIDATION]

    async def ws_callback(message: str) -> None:
        """Forward agent status strings to the connected WebSocket client."""
        step = _current_step[0]
        await conn_manager.send_status(
            session_id=session_id,
            step=step,
            message=message,
        )

    # ------------------------------------------------------------------ #
    # Emit initial per-step status messages                                #
    # ------------------------------------------------------------------ #

    async def advance_step(step: AnalysisStep) -> None:
        _current_step[0] = step
        await conn_manager.send_status(
            session_id=session_id,
            step=step,
            message=step_messages.get(step, f"Running {step.value}..."),
        )

    await advance_step(AnalysisStep.VALIDATION)

    # ------------------------------------------------------------------ #
    # Build initial agent state                                            #
    # ------------------------------------------------------------------ #

    initial_state: AgentState = {
        "incident_text": incident_data["incident_text"],
        "source_ip": incident_data.get("source_ip"),
        "dest_ip": incident_data.get("dest_ip"),
        "protocol": incident_data.get("protocol"),
        "severity": incident_data.get("severity"),
        "session_id": session_id,
        "user_id": user_id,
        # Defaults for all other fields
        "is_valid": False,
        "validation_error": None,
        "threat_class": None,
        "threat_confidence": 0.0,
        "similar_incidents": [],
        "graph_context": None,
        "rag_context": None,
        "citations": [],
        "mitigation": None,
        "escalation_level": None,
        "escalation_reason": None,
        "explanation": None,
        "judge_score": 0.0,
        "judge_feedback": None,
        "is_safe": True,
        "final_answer": None,
        "messages": [],
        "retry_count": 0,
        "ws_callback": ws_callback,
    }

    # ------------------------------------------------------------------ #
    # Import and run the LangGraph workflow                                #
    # ------------------------------------------------------------------ #

    try:
        # Import lazily to avoid top-level circular import chains
        from backend.app.agents.validation_agent import validation_agent
        from backend.app.agents.classification_agent import classification_agent
        from backend.app.agents.retrieval_agent import retrieval_agent
        from backend.app.agents.mitigation_agent import mitigation_agent
        from backend.app.agents.escalation_agent import escalation_agent
        from backend.app.agents.explainability_agent import explainability_agent
        from backend.app.agents.judge_agent import judge_agent

        state = dict(initial_state)

        # --- Validation ---
        update = await validation_agent(state)
        state.update(update)
        if not state.get("is_valid", False):
            await conn_manager.send_error(
                session_id=session_id,
                error="Input validation failed",
                detail=state.get("validation_error"),
            )
            return

        # --- Classification ---
        await advance_step(AnalysisStep.CLASSIFICATION)
        update = await classification_agent(state)
        state.update(update)

        # --- Retrieval ---
        await advance_step(AnalysisStep.RETRIEVAL)
        update = await retrieval_agent(state)
        state.update(update)

        # --- Graph expansion (best-effort) ---
        await advance_step(AnalysisStep.GRAPH_EXPANSION)
        try:
            from backend.app.graph.neo4j_service import GraphService

            graph_svc = GraphService()
            graph_ctx = await graph_svc.graph_rag_context(
                incident_text=state["incident_text"],
                attack_type=state.get("threat_class") or "Unknown",
            )
            await graph_svc.close()
            state["graph_context"] = graph_ctx
        except Exception as graph_exc:
            logger.warning("Graph expansion skipped", error=str(graph_exc))
            state["graph_context"] = {}

        await conn_manager.send_status(
            session_id=session_id,
            step=AnalysisStep.GRAPH_EXPANSION,
            message="Graph context retrieved.",
            data={"mitigations_count": len(state.get("graph_context", {}).get("mitigations", []))},
        )

        # --- Mitigation ---
        await advance_step(AnalysisStep.MITIGATION)
        update = await mitigation_agent(state)
        state.update(update)

        # --- Escalation ---
        await advance_step(AnalysisStep.ESCALATION)
        update = await escalation_agent(state)
        state.update(update)

        # --- Explanation ---
        await advance_step(AnalysisStep.EXPLANATION)
        update = await explainability_agent(state)
        state.update(update)

        # --- Judge ---
        await advance_step(AnalysisStep.JUDGE)
        update = await judge_agent(state)
        state.update(update)

    except Exception as exc:
        tb = traceback.format_exc()
        logger.error("Analysis pipeline error", session_id=session_id, error=str(exc))
        await conn_manager.send_error(
            session_id=session_id,
            error=f"Analysis pipeline failed: {exc}",
            detail=tb,
        )
        return

    # ------------------------------------------------------------------ #
    # Assemble the final result                                            #
    # ------------------------------------------------------------------ #

    similar = []
    for inc in state.get("similar_incidents", []):
        payload = inc.get("payload", inc)
        similar.append(
            {
                "id": inc.get("id", ""),
                "score": inc.get("score", 0.0),
                "attack_type": payload.get("attack_type"),
                "severity": payload.get("severity"),
                "summary": payload.get("raw_text", ""),
            }
        )

    graph_ctx = state.get("graph_context") or {}
    result: Dict[str, Any] = {
        "threat_class": state.get("threat_class") or "Unknown",
        "severity_score": state.get("threat_confidence", 0.0),
        "similar_incidents": similar,
        "mitigation": state.get("mitigation") or {},
        "escalation_level": state.get("escalation_level") or "L1",
        "escalation_reason": state.get("escalation_reason"),
        "explanation": state.get("explanation") or state.get("final_answer") or "",
        "judge_score": state.get("judge_score", 0.0),
        "judge_feedback": state.get("judge_feedback"),
        "graph_summary": {
            "attack_type": graph_ctx.get("attack_type"),
            "related_incidents_count": len(graph_ctx.get("related_incidents", [])),
            "mitigations": graph_ctx.get("mitigations", []),
        },
        "session_id": session_id,
        "citations": state.get("citations", []),
    }

    await conn_manager.send_complete(session_id=session_id, result=result)
    logger.info(
        "Analysis pipeline complete",
        session_id=session_id,
        threat_class=result["threat_class"],
        judge_score=result["judge_score"],
    )


# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------


@router.websocket("/analyze/{session_id}")
async def websocket_analyze(
    websocket: WebSocket,
    session_id: str,
) -> None:
    """WebSocket endpoint for streaming real-time incident analysis.

    URL
    ---
    ``WS /ws/analyze/{session_id}``

    The client:
    1. Connects to this endpoint.
    2. Sends a JSON object containing the incident payload::

           {
               "incident_text": "...",
               "source_ip":     "192.168.1.10",
               "dest_ip":       "10.0.0.5",
               "protocol":      "TCP",
               "severity":      "high",
               "user_id":       "user_abc123"
           }

    3. Receives streamed ``status`` messages for each analysis step.
    4. Receives the final ``complete`` message with the full result.

    Parameters
    ----------
    websocket:
        The incoming WebSocket connection.
    session_id:
        A unique session identifier embedded in the URL path.  The client
        should generate a UUID per analysis session.
    """
    await manager.connect(session_id, websocket)

    try:
        # Wait for the incident payload from the client
        data: Dict[str, Any] = await websocket.receive_json()
        logger.info(
            "WebSocket analysis request received",
            session_id=session_id,
            keys=list(data.keys()),
        )

        # Extract user_id (sent in payload or fall back to anonymous)
        user_id: str = str(data.get("user_id") or "anonymous")

        # Parse and normalise incident fields
        incident_data = _parse_incident_payload(data)

        if not incident_data["incident_text"]:
            await manager.send_error(
                session_id=session_id,
                error="incident_text is required.",
            )
            return

        # Run the full analysis pipeline
        await _run_analysis_pipeline(
            session_id=session_id,
            user_id=user_id,
            incident_data=incident_data,
            conn_manager=manager,
        )

    except WebSocketDisconnect:
        logger.info("Client disconnected during analysis", session_id=session_id)

    except Exception as exc:
        tb = traceback.format_exc()
        logger.error(
            "Unhandled WebSocket error",
            session_id=session_id,
            error=str(exc),
        )
        try:
            await manager.send_error(
                session_id=session_id,
                error=f"Internal server error: {exc}",
                detail=tb,
            )
        except Exception:
            pass

    finally:
        await manager.disconnect(session_id)
