"""
CyberSentinel AI — MCP Tools package.

Exports all tool functions that are registered with the MCP server.
Import from this package for both MCP (stdio) and HTTP server usage.
"""

from .incident_tools import (
    search_similar_incidents,
    get_incident_by_id,
    get_attack_type_context,
    recommend_mitigation,
    calculate_risk_score,
    create_incident_report,
    query_graph_relationships,
    store_feedback,
)

__all__ = [
    "search_similar_incidents",
    "get_incident_by_id",
    "get_attack_type_context",
    "recommend_mitigation",
    "calculate_risk_score",
    "create_incident_report",
    "query_graph_relationships",
    "store_feedback",
]
