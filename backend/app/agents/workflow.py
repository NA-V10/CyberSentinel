"""LangGraph multi-agent workflow for CyberSentinel AI.

Graph topology
--------------
START
  └─► validation_node
        ├─ (invalid) ──────────────────────────────────────► END
        └─ (valid)  ──► classification_node
                             └─► retrieval_node
                                   └─► mitigation_node
                                         └─► escalation_node
                                               └─► explainability_node
                                                     └─► judge_node
                                                           ├─ (safe)       ──► feedback_node ──► END
                                                           └─ (not safe,
                                                               retry < 1)  ──► mitigation_node (retry)

Usage::

    from backend.app.agents.workflow import create_workflow

    graph = create_workflow()
    final_state = await graph.ainvoke(initial_state)
"""

from __future__ import annotations

import json
import uuid
from typing import Any, Dict, Optional

from langgraph.graph import END, START, StateGraph

from backend.app.agents.state import AgentState
from backend.app.agents.classification_agent import classification_agent
from backend.app.agents.escalation_agent import escalation_agent
from backend.app.agents.explainability_agent import explainability_agent
from backend.app.agents.feedback_agent import feedback_agent
from backend.app.agents.judge_agent import judge_agent
from backend.app.agents.mitigation_agent import mitigation_agent
from backend.app.agents.retrieval_agent import retrieval_agent
from backend.app.agents.validation_agent import validation_agent

# ---------------------------------------------------------------------------
# Node wrapper helpers
# ---------------------------------------------------------------------------

# We wrap each agent function so LangGraph receives a plain async callable
# with signature (state: AgentState) -> dict.


async def _validation_node(state: AgentState) -> Dict[str, Any]:
    return await validation_agent(state)


async def _classification_node(state: AgentState) -> Dict[str, Any]:
    return await classification_agent(state)


async def _retrieval_node(state: AgentState) -> Dict[str, Any]:
    # db_session is not available here — retrieval agent handles the fallback
    return await retrieval_agent(state, db_session=None)


async def _mitigation_node(state: AgentState) -> Dict[str, Any]:
    return await mitigation_agent(state)


async def _escalation_node(state: AgentState) -> Dict[str, Any]:
    return await escalation_agent(state)


async def _explainability_node(state: AgentState) -> Dict[str, Any]:
    return await explainability_agent(state)


async def _judge_node(state: AgentState) -> Dict[str, Any]:
    return await judge_agent(state)


async def _feedback_node(state: AgentState) -> Dict[str, Any]:
    return await feedback_agent(state)


async def _assemble_final_node(state: AgentState) -> Dict[str, Any]:
    """Assemble the ``final_answer`` JSON string from individual state fields."""
    mitigation: dict = state.get("mitigation") or {}
    answer = {
        "threat_class": state.get("threat_class"),
        "threat_confidence": state.get("threat_confidence"),
        "severity": state.get("severity"),
        "similar_incidents": state.get("similar_incidents") or [],
        "mitigation": mitigation,
        "escalation_level": state.get("escalation_level"),
        "escalation_reason": state.get("escalation_reason"),
        "explanation": state.get("explanation"),
        "judge_score": state.get("judge_score"),
        "judge_feedback": state.get("judge_feedback"),
        "is_safe": state.get("is_safe"),
        "citations": state.get("citations") or [],
    }
    return {"final_answer": json.dumps(answer, default=str)}


# ---------------------------------------------------------------------------
# Conditional edge predicates
# ---------------------------------------------------------------------------


def _route_after_validation(state: AgentState) -> str:
    """Route to END immediately if validation failed."""
    if not state.get("is_valid", True):
        return "end"
    return "classification"


def _route_after_judge(state: AgentState) -> str:
    """Retry mitigation once if the judge marks the answer unsafe."""
    is_safe: bool = bool(state.get("is_safe", True))
    retry_count: int = int(state.get("retry_count", 0))

    if not is_safe and retry_count < 1:
        return "retry_mitigation"
    return "assemble"


# ---------------------------------------------------------------------------
# Workflow factory
# ---------------------------------------------------------------------------


def create_workflow() -> Any:
    """Build and compile the CyberSentinel AI LangGraph workflow.

    Returns
    -------
    CompiledGraph
        A compiled LangGraph graph ready for ``ainvoke`` / ``astream``.
    """
    graph = StateGraph(AgentState)

    # --- Register nodes ---
    graph.add_node("validation", _validation_node)
    graph.add_node("classification", _classification_node)
    graph.add_node("retrieval", _retrieval_node)
    graph.add_node("mitigation", _mitigation_node)
    graph.add_node("escalation", _escalation_node)
    graph.add_node("explainability", _explainability_node)
    graph.add_node("judge", _judge_node)
    graph.add_node("feedback", _feedback_node)
    graph.add_node("assemble_final", _assemble_final_node)

    # Retry mitigation node is the same function; LangGraph tracks state between visits
    # We re-use the "mitigation" node name — the _route_after_judge predicate
    # increments retry_count to prevent infinite loops.

    # --- Entry point ---
    graph.set_entry_point("validation")

    # --- Edges ---

    # validation → classification  OR  END
    graph.add_conditional_edges(
        "validation",
        _route_after_validation,
        {
            "end": END,
            "classification": "classification",
        },
    )

    # classification → retrieval (always)
    graph.add_edge("classification", "retrieval")

    # retrieval → mitigation (always)
    graph.add_edge("retrieval", "mitigation")

    # mitigation → escalation (always)
    graph.add_edge("mitigation", "escalation")

    # escalation → explainability (always)
    graph.add_edge("escalation", "explainability")

    # explainability → judge (always)
    graph.add_edge("explainability", "judge")

    # judge → assemble_final  OR  retry mitigation once
    graph.add_conditional_edges(
        "judge",
        _route_after_judge,
        {
            "retry_mitigation": "mitigation",
            "assemble": "assemble_final",
        },
    )

    # assemble_final → feedback → END
    graph.add_edge("assemble_final", "feedback")
    graph.add_edge("feedback", END)

    compiled = graph.compile()
    return compiled


def build_initial_state(
    incident_text: str,
    user_id: str,
    session_id: Optional[str] = None,
    source_ip: Optional[str] = None,
    dest_ip: Optional[str] = None,
    protocol: Optional[str] = None,
    severity: Optional[str] = None,
    ws_callback=None,
) -> AgentState:
    """Construct an initial AgentState dict for a new workflow invocation.

    Parameters
    ----------
    incident_text:
        Raw incident description.
    user_id:
        Clerk user ID of the requesting analyst.
    session_id:
        Existing conversation UUID or None (a new UUID is generated).
    source_ip:
        Optional source IP.
    dest_ip:
        Optional destination IP.
    protocol:
        Optional network protocol.
    severity:
        Optional analyst-supplied severity hint.
    ws_callback:
        Optional async callable for streaming status updates.

    Returns
    -------
    AgentState
        Fully initialised state dict ready to pass to ``graph.ainvoke``.
    """
    return AgentState(
        incident_text=incident_text,
        source_ip=source_ip,
        dest_ip=dest_ip,
        protocol=protocol,
        severity=severity,
        session_id=session_id or str(uuid.uuid4()),
        user_id=user_id,
        # Validation
        is_valid=False,
        validation_error=None,
        # Classification
        threat_class=None,
        threat_confidence=0.0,
        # Retrieval
        similar_incidents=[],
        graph_context=None,
        rag_context=None,
        citations=[],
        # Mitigation
        mitigation=None,
        # Escalation
        escalation_level=None,
        escalation_reason=None,
        # Explanation
        explanation=None,
        # Judge
        judge_score=0.0,
        judge_feedback=None,
        is_safe=True,
        # Misc
        ws_callback=ws_callback,
        final_answer=None,
        messages=[],
        retry_count=0,
    )
