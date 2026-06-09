"""
Report generation service for CyberSentinel AI.

Transforms an incident analysis result dict (as produced by the multi-agent
pipeline) into a structured, human-readable report suitable for export or
display in the frontend.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger


# ---------------------------------------------------------------------------
# Severity utilities
# ---------------------------------------------------------------------------

_SEVERITY_SCORES: Dict[str, float] = {
    "critical": 1.0,
    "high": 0.75,
    "medium": 0.5,
    "low": 0.25,
}

_ESCALATION_LABELS: Dict[str, str] = {
    "l1": "Tier 1 — Analyst on duty",
    "l2": "Tier 2 — Senior Analyst",
    "l3": "Tier 3 — Incident Response Team",
    "soc_manager": "SOC Manager",
    "ciso": "CISO / Executive Team",
    "none": "No escalation required",
}


def _normalise_escalation(level: str) -> str:
    """Return a human-readable escalation description."""
    return _ESCALATION_LABELS.get((level or "").lower(), level)


# ---------------------------------------------------------------------------
# Executive summary builder
# ---------------------------------------------------------------------------


def _build_executive_summary(analysis: Dict[str, Any]) -> str:
    """Compose a concise executive summary from the analysis dict.

    Parameters
    ----------
    analysis:
        Full incident analysis result.

    Returns
    -------
    str
        Two-to-three sentence executive summary.
    """
    threat_class = analysis.get("threat_class") or "Unknown"
    severity_score = analysis.get("severity_score", 0.0)
    escalation_level = analysis.get("escalation_level") or "L1"
    similar_count = len(analysis.get("similar_incidents") or [])
    judge_score = analysis.get("judge_score", 0.0)

    # Map numeric score back to a label
    severity_label = "Unknown"
    for label, score in sorted(_SEVERITY_SCORES.items(), key=lambda x: x[1], reverse=True):
        if severity_score >= score - 0.01:
            severity_label = label.capitalize()
            break

    summary_parts = [
        f"A {severity_label}-severity {threat_class} threat was detected and analysed "
        f"with a confidence score of {judge_score:.0%}.",
    ]

    if similar_count > 0:
        summary_parts.append(
            f"{similar_count} historically similar incident(s) were identified in the "
            f"knowledge base to support contextual analysis."
        )

    esc_human = _normalise_escalation(escalation_level)
    summary_parts.append(
        f"Recommended escalation path: {esc_human}.  "
        "Immediate mitigation steps are provided below."
    )

    return " ".join(summary_parts)


# ---------------------------------------------------------------------------
# Similar incidents formatter
# ---------------------------------------------------------------------------


def _format_similar_incidents(similar: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return a clean list of similar incident summaries for the report."""
    formatted = []
    for inc in (similar or []):
        formatted.append(
            {
                "id": inc.get("id", "N/A"),
                "attack_type": inc.get("attack_type") or inc.get("payload", {}).get("attack_type"),
                "severity": inc.get("severity") or inc.get("payload", {}).get("severity"),
                "similarity_score": round(float(inc.get("score", 0.0)), 4),
                "summary": (
                    inc.get("summary")
                    or inc.get("payload", {}).get("raw_text", "No summary available")
                ),
            }
        )
    return formatted


# ---------------------------------------------------------------------------
# Mitigation formatter
# ---------------------------------------------------------------------------


def _format_mitigation(mitigation: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Ensure mitigation is cleanly structured for the report."""
    if not mitigation:
        return {
            "containment": [],
            "eradication": [],
            "recovery": [],
            "prevention": [],
            "summary": "No mitigation steps available.",
        }

    # Mitigation dict may come from the agent in different shapes
    if isinstance(mitigation, str):
        return {
            "containment": [],
            "eradication": [],
            "recovery": [],
            "prevention": [],
            "summary": mitigation,
        }

    return {
        "containment": mitigation.get("containment") or [],
        "eradication": mitigation.get("eradication") or [],
        "recovery": mitigation.get("recovery") or [],
        "prevention": mitigation.get("prevention") or [],
        "summary": mitigation.get("summary") or mitigation.get("overview") or "",
        "additional": mitigation.get("additional") or {},
    }


# ---------------------------------------------------------------------------
# Graph summary formatter
# ---------------------------------------------------------------------------


def _format_graph_summary(graph: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Extract a lightweight graph summary for the report."""
    if not graph:
        return {
            "attack_type": None,
            "related_incidents_count": 0,
            "mitigations": [],
            "affected_assets": [],
        }
    return {
        "attack_type": graph.get("attack_type"),
        "related_incidents_count": graph.get("related_incidents_count", 0),
        "mitigations": graph.get("mitigations") or [],
        "affected_assets": graph.get("affected_assets") or [],
        "protocols": graph.get("protocols") or [],
    }


# ---------------------------------------------------------------------------
# Main report generator
# ---------------------------------------------------------------------------


def generate_report(
    incident_analysis: Dict[str, Any],
    user_id: str,
    incident_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate a structured incident report from a completed analysis dict.

    Parameters
    ----------
    incident_analysis:
        The full analysis result dict produced by the WebSocket pipeline /
        ``AnalyzeIncidentResponse``.  Expected keys:

        - ``threat_class``
        - ``severity_score``
        - ``similar_incidents``
        - ``mitigation``
        - ``escalation_level``
        - ``escalation_reason``
        - ``explanation``
        - ``judge_score``
        - ``judge_feedback``
        - ``graph_summary`` or ``graph_data``
        - ``citations``  (optional)
        - ``session_id`` (optional)

    user_id:
        The authenticated user who triggered the analysis.
    incident_id:
        Optional pre-existing incident UUID to embed in the report.

    Returns
    -------
    dict
        Structured report with the following top-level keys:

        - ``report_id``
        - ``generated_at``
        - ``analyst_user_id``
        - ``executive_summary``
        - ``incident_details``
        - ``threat_classification``
        - ``similar_incidents``
        - ``mitigation_steps``
        - ``escalation_recommendation``
        - ``explanation``
        - ``judge_validation``
        - ``graph_summary``
        - ``metadata``
    """
    report_id = str(uuid.uuid4())
    generated_at = datetime.utcnow().isoformat() + "Z"

    threat_class = incident_analysis.get("threat_class") or "Unknown"
    severity_score = float(incident_analysis.get("severity_score") or 0.0)
    escalation_level = incident_analysis.get("escalation_level") or "L1"
    escalation_reason = incident_analysis.get("escalation_reason") or ""
    explanation = incident_analysis.get("explanation") or ""
    judge_score = float(incident_analysis.get("judge_score") or 0.0)
    judge_feedback = incident_analysis.get("judge_feedback") or ""
    citations = incident_analysis.get("citations") or []
    session_id = incident_analysis.get("session_id")

    # Resolve severity label
    severity_label = "Unknown"
    for label, score in sorted(_SEVERITY_SCORES.items(), key=lambda x: x[1], reverse=True):
        if severity_score >= score - 0.01:
            severity_label = label.capitalize()
            break

    similar_incidents = _format_similar_incidents(
        incident_analysis.get("similar_incidents") or []
    )
    mitigation = _format_mitigation(incident_analysis.get("mitigation"))
    graph_summary = _format_graph_summary(
        incident_analysis.get("graph_summary") or incident_analysis.get("graph_data")
    )

    # ------------------------------------------------------------------ #
    # Determine overall risk rating                                       #
    # ------------------------------------------------------------------ #
    risk_rating: str
    if severity_score >= 0.9:
        risk_rating = "Critical"
    elif severity_score >= 0.65:
        risk_rating = "High"
    elif severity_score >= 0.40:
        risk_rating = "Medium"
    else:
        risk_rating = "Low"

    # ------------------------------------------------------------------ #
    # Assemble the report                                                 #
    # ------------------------------------------------------------------ #

    report: Dict[str, Any] = {
        "report_id": report_id,
        "generated_at": generated_at,
        "analyst_user_id": user_id,

        # -------------------------------------------------------------- #
        # Executive summary (non-technical, suitable for management)     #
        # -------------------------------------------------------------- #
        "executive_summary": _build_executive_summary(incident_analysis),

        # -------------------------------------------------------------- #
        # Incident details                                                #
        # -------------------------------------------------------------- #
        "incident_details": {
            "incident_id": incident_id or incident_analysis.get("incident_id"),
            "session_id": session_id,
            "threat_class": threat_class,
            "severity": severity_label,
            "severity_score": round(severity_score, 4),
            "risk_rating": risk_rating,
            "protocol": incident_analysis.get("protocol"),
            "source_ip": incident_analysis.get("source_ip"),
            "dest_ip": incident_analysis.get("dest_ip"),
            "raw_text": incident_analysis.get("incident_text") or incident_analysis.get("raw_text"),
        },

        # -------------------------------------------------------------- #
        # ML threat classification                                       #
        # -------------------------------------------------------------- #
        "threat_classification": {
            "attack_type": threat_class,
            "confidence": round(severity_score, 4),
            "risk_rating": risk_rating,
            "all_probabilities": incident_analysis.get("all_probabilities") or [],
        },

        # -------------------------------------------------------------- #
        # Similar historical incidents                                   #
        # -------------------------------------------------------------- #
        "similar_incidents": similar_incidents,

        # -------------------------------------------------------------- #
        # Mitigation playbook                                            #
        # -------------------------------------------------------------- #
        "mitigation_steps": mitigation,

        # -------------------------------------------------------------- #
        # Escalation recommendation                                      #
        # -------------------------------------------------------------- #
        "escalation_recommendation": {
            "level": escalation_level,
            "description": _normalise_escalation(escalation_level),
            "reason": escalation_reason,
            "immediate_action_required": escalation_level.lower() in (
                "l3", "soc_manager", "ciso", "critical"
            ),
        },

        # -------------------------------------------------------------- #
        # Natural-language explanation                                   #
        # -------------------------------------------------------------- #
        "explanation": explanation,

        # -------------------------------------------------------------- #
        # Judge / quality validation                                     #
        # -------------------------------------------------------------- #
        "judge_validation": {
            "score": round(judge_score, 4),
            "feedback": judge_feedback,
            "quality_label": (
                "Excellent" if judge_score >= 0.85
                else "Good" if judge_score >= 0.65
                else "Acceptable" if judge_score >= 0.45
                else "Needs Review"
            ),
            "is_safe": incident_analysis.get("is_safe", True),
        },

        # -------------------------------------------------------------- #
        # Knowledge graph summary                                        #
        # -------------------------------------------------------------- #
        "graph_summary": graph_summary,

        # -------------------------------------------------------------- #
        # Metadata / provenance                                          #
        # -------------------------------------------------------------- #
        "metadata": {
            "citations": citations,
            "rag_context_used": bool(incident_analysis.get("rag_context")),
            "graph_context_used": bool(incident_analysis.get("graph_context")),
            "similar_incidents_found": len(similar_incidents),
            "model_used": incident_analysis.get("model_used"),
            "pipeline_version": "1.0.0",
        },
    }

    logger.info(
        "Report generated",
        report_id=report_id,
        threat_class=threat_class,
        severity=severity_label,
        user_id=user_id,
    )
    return report


# ---------------------------------------------------------------------------
# Report comparison helper
# ---------------------------------------------------------------------------


def diff_reports(
    report_a: Dict[str, Any],
    report_b: Dict[str, Any],
) -> Dict[str, Any]:
    """Produce a high-level diff between two reports for the same incident.

    Useful when a re-analysis is run after mitigation or additional context
    is added.

    Parameters
    ----------
    report_a:
        Earlier report (baseline).
    report_b:
        Later report (comparison).

    Returns
    -------
    dict
        Keys: ``threat_class_changed``, ``severity_changed``,
        ``escalation_changed``, ``judge_score_delta``.
    """
    a_class = report_a.get("incident_details", {}).get("threat_class")
    b_class = report_b.get("incident_details", {}).get("threat_class")

    a_sev = report_a.get("incident_details", {}).get("severity")
    b_sev = report_b.get("incident_details", {}).get("severity")

    a_esc = report_a.get("escalation_recommendation", {}).get("level")
    b_esc = report_b.get("escalation_recommendation", {}).get("level")

    a_judge = report_a.get("judge_validation", {}).get("score", 0.0)
    b_judge = report_b.get("judge_validation", {}).get("score", 0.0)

    return {
        "threat_class_changed": a_class != b_class,
        "old_threat_class": a_class,
        "new_threat_class": b_class,
        "severity_changed": a_sev != b_sev,
        "old_severity": a_sev,
        "new_severity": b_sev,
        "escalation_changed": a_esc != b_esc,
        "old_escalation": a_esc,
        "new_escalation": b_esc,
        "judge_score_delta": round(float(b_judge) - float(a_judge), 4),
    }
