"""LangGraph state definition for the CyberSentinel AI multi-agent workflow."""

from __future__ import annotations

from typing import Any, List, Optional, TypedDict


class AgentState(TypedDict):
    """Shared state passed between all agents in the LangGraph workflow."""

    # -----------------------------------------------------------------------
    # Input fields
    # -----------------------------------------------------------------------
    incident_text: str
    source_ip: Optional[str]
    dest_ip: Optional[str]
    protocol: Optional[str]
    severity: Optional[str]
    session_id: str
    user_id: str

    # -----------------------------------------------------------------------
    # Validation
    # -----------------------------------------------------------------------
    is_valid: bool
    validation_error: Optional[str]

    # -----------------------------------------------------------------------
    # Classification
    # -----------------------------------------------------------------------
    threat_class: Optional[str]
    threat_confidence: float

    # -----------------------------------------------------------------------
    # Retrieval
    # -----------------------------------------------------------------------
    similar_incidents: List[dict]
    graph_context: Optional[dict]
    rag_context: Optional[str]
    citations: List[dict]

    # -----------------------------------------------------------------------
    # Mitigation  {containment, eradication, recovery, prevention}
    # -----------------------------------------------------------------------
    mitigation: Optional[dict]

    # -----------------------------------------------------------------------
    # Escalation
    # -----------------------------------------------------------------------
    escalation_level: Optional[str]   # L1 | L2 | L3 | SOC_Manager
    escalation_reason: Optional[str]

    # -----------------------------------------------------------------------
    # Explanation
    # -----------------------------------------------------------------------
    explanation: Optional[str]

    # -----------------------------------------------------------------------
    # Judge
    # -----------------------------------------------------------------------
    judge_score: float
    judge_feedback: Optional[str]
    is_safe: bool

    # -----------------------------------------------------------------------
    # WebSocket streaming callback
    # -----------------------------------------------------------------------
    ws_callback: Optional[Any]   # async callable(message: str) -> None

    # -----------------------------------------------------------------------
    # Final answer
    # -----------------------------------------------------------------------
    final_answer: Optional[str]
    messages: List[dict]

    # -----------------------------------------------------------------------
    # Internal retry counter (used by workflow to guard against infinite loops)
    # -----------------------------------------------------------------------
    retry_count: int

    # -----------------------------------------------------------------------
    # Persisted record identifier (set by feedback_agent after DB write)
    # -----------------------------------------------------------------------
    incident_id: Optional[str]
