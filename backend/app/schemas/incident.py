from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Shared config
# ---------------------------------------------------------------------------

class _OrmBase(BaseModel):
    """Shared config that enables ORM-mode for all response schemas."""

    model_config = ConfigDict(from_attributes=True)


# ===========================================================================
# Incident schemas
# ===========================================================================

class IncidentBase(BaseModel):
    source_ip: Optional[str] = Field(None, description="Source IP address")
    dest_ip: Optional[str] = Field(None, description="Destination IP address")
    protocol: Optional[str] = Field(None, description="Network protocol (e.g. TCP, UDP)")
    attack_type: Optional[str] = Field(None, description="Classified attack type")
    severity: Optional[str] = Field(None, description="Severity level: low|medium|high|critical")
    label: Optional[str] = Field(None, description="Human-readable label")
    raw_text: Optional[str] = Field(None, description="Raw log or alert text")
    timestamp: Optional[datetime] = Field(None, description="When the incident occurred")


class IncidentCreate(IncidentBase):
    user_id: str = Field(..., description="Clerk user ID of the submitting analyst")


class IncidentResponse(_OrmBase, IncidentBase):
    id: uuid.UUID
    user_id: str
    embedding_id: Optional[str] = None
    created_at: datetime


# ===========================================================================
# Conversation schemas
# ===========================================================================

class ConversationCreate(BaseModel):
    title: Optional[str] = Field(None, description="Optional display title for the conversation")


class ConversationResponse(_OrmBase):
    id: uuid.UUID
    user_id: str
    title: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ===========================================================================
# Message schemas
# ===========================================================================

class MessageCreate(BaseModel):
    conversation_id: uuid.UUID
    role: str = Field(..., description="Message role: user|assistant|system")
    content: str = Field(..., description="Text content of the message")
    metadata: Optional[Dict[str, Any]] = Field(
        None, description="Optional metadata (token counts, citations, etc.)"
    )


class MessageResponse(_OrmBase):
    id: uuid.UUID
    conversation_id: uuid.UUID
    role: str
    content: str
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime


# ===========================================================================
# Feedback schemas
# ===========================================================================

class FeedbackCreate(BaseModel):
    incident_id: Optional[uuid.UUID] = Field(None, description="Related incident ID")
    conversation_id: Optional[uuid.UUID] = Field(None, description="Related conversation ID")
    rating: Optional[int] = Field(None, ge=1, le=5, description="Satisfaction rating 1–5")
    comment: Optional[str] = Field(None, description="Free-text analyst comment")
    mitigation_worked: Optional[bool] = Field(
        None, description="Whether the suggested mitigation was effective"
    )


class FeedbackResponse(_OrmBase):
    id: uuid.UUID
    incident_id: Optional[uuid.UUID] = None
    conversation_id: Optional[uuid.UUID] = None
    user_id: str
    rating: Optional[int] = None
    comment: Optional[str] = None
    mitigation_worked: Optional[bool] = None
    created_at: datetime


# ===========================================================================
# Analysis request / response
# ===========================================================================

class AnalyzeIncidentRequest(BaseModel):
    """Payload sent by the frontend to trigger a full AI analysis pipeline."""

    incident_text: str = Field(
        ...,
        min_length=1,
        description="Raw incident description, log snippet, or alert text",
    )
    severity: Optional[str] = Field(
        None, description="Analyst-supplied severity hint (overrides ML prediction)"
    )
    source_ip: Optional[str] = Field(None, description="Source IP observed in the incident")
    dest_ip: Optional[str] = Field(None, description="Destination IP observed in the incident")
    protocol: Optional[str] = Field(None, description="Network protocol involved")
    session_id: Optional[str] = Field(
        None,
        description="Existing conversation session to continue; creates a new one if omitted",
    )


class SimilarIncident(BaseModel):
    """A single result from the vector similarity search."""

    id: str
    score: float
    attack_type: Optional[str] = None
    severity: Optional[str] = None
    summary: Optional[str] = None


class MitigationStep(BaseModel):
    """One recommended mitigation action."""

    step: int
    action: str
    priority: str = Field(description="immediate|short-term|long-term")
    details: Optional[str] = None


class GraphData(BaseModel):
    """Subgraph extracted from Neo4j relevant to this incident."""

    nodes: List[Dict[str, Any]] = Field(default_factory=list)
    edges: List[Dict[str, Any]] = Field(default_factory=list)


class AnalyzeIncidentResponse(BaseModel):
    """Full AI analysis result returned to the frontend."""

    # ML classifier output
    threat_class: str = Field(..., description="Predicted threat category")
    severity_score: float = Field(..., ge=0.0, le=1.0, description="Normalised severity score")

    # RAG / vector search
    similar_incidents: List[SimilarIncident] = Field(
        default_factory=list,
        description="Most semantically similar historical incidents",
    )

    # LLM-generated guidance
    mitigation: Dict[str, Any] = Field(
        ..., description="Structured mitigation plan produced by the LLM"
    )
    escalation_level: str = Field(
        ..., description="Recommended escalation: none|tier1|tier2|soc_manager|ciso"
    )
    explanation: str = Field(
        ..., description="Natural-language explanation of the threat and recommended actions"
    )

    # LLM-as-judge quality score for the generated response
    judge_score: float = Field(
        ..., ge=0.0, le=1.0, description="Self-evaluation confidence score from the judge LLM"
    )

    # Graph data
    graph_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Related nodes and edges from the threat-knowledge graph",
    )

    # Optional identifiers for downstream use
    incident_id: Optional[uuid.UUID] = None
    conversation_id: Optional[uuid.UUID] = None
    session_id: Optional[str] = None
