"""Premium feature database models — Final Feature Set."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base


def _uuid_default() -> uuid.UUID:
    return uuid.uuid4()


# ---------------------------------------------------------------------------
# Self Reflection
# ---------------------------------------------------------------------------

class SelfReflection(Base):
    """Stores agent self-reflection results for a given incident analysis."""

    __tablename__ = "self_reflections"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid_default)
    org_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    incident_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    initial_analysis: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    judge_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    weaknesses_detected: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    missing_evidence: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    additional_retrieval_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    improved_analysis: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    before_after_comparison: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    final_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    reflection_triggered: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<SelfReflection id={self.id} confidence={self.final_confidence}>"


# ---------------------------------------------------------------------------
# Campaign
# ---------------------------------------------------------------------------

class Campaign(Base):
    """An attack campaign grouping related incidents."""

    __tablename__ = "campaigns"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid_default)
    org_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    campaign_name: Mapped[str] = mapped_column(String(512), nullable=False)
    campaign_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    shared_indicators: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    time_window: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    recommended_campaign_response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    attack_patterns: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    mitre_techniques: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    source_subnets: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    targeted_assets: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    incidents: Mapped[list["CampaignIncident"]] = relationship(
        "CampaignIncident", back_populates="campaign", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Campaign id={self.id} name={self.campaign_name}>"


class CampaignIncident(Base):
    """Join table linking campaigns to their constituent incidents."""

    __tablename__ = "campaign_incidents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid_default)
    org_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True
    )
    incident_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    correlation_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    correlation_reasons: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="incidents")

    def __repr__(self) -> str:
        return f"<CampaignIncident campaign={self.campaign_id} incident={self.incident_id}>"


# ---------------------------------------------------------------------------
# Autonomous Investigation
# ---------------------------------------------------------------------------

class AutonomousInvestigation(Base):
    """Record of a fully autonomous AI investigation run."""

    __tablename__ = "autonomous_investigations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid_default)
    org_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    incident_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="running")
    evidence_chain: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    timeline: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    findings: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    final_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    recommended_actions: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    judge_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    total_tool_calls: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    tool_calls: Mapped[list["InvestigationToolCall"]] = relationship(
        "InvestigationToolCall", back_populates="investigation", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<AutonomousInvestigation id={self.id} status={self.status}>"


class InvestigationToolCall(Base):
    """A single MCP tool call made during an autonomous investigation."""

    __tablename__ = "investigation_tool_calls"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid_default)
    org_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    investigation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("autonomous_investigations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    agent_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    tool_name: Mapped[str] = mapped_column(String(128), nullable=False)
    input_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    output_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    full_output: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="completed")
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    investigation: Mapped["AutonomousInvestigation"] = relationship(
        "AutonomousInvestigation", back_populates="tool_calls"
    )

    def __repr__(self) -> str:
        return f"<InvestigationToolCall tool={self.tool_name} status={self.status}>"


# ---------------------------------------------------------------------------
# Consensus Engine
# ---------------------------------------------------------------------------

class ConsensusResult(Base):
    """Multi-LLM consensus analysis result."""

    __tablename__ = "consensus_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid_default)
    org_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    incident_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    consensus_classification: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    consensus_severity: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    agreement_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    disagreement_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    final_recommendation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    models_used: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    total_cost: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    model_outputs: Mapped[list["ConsensusModelOutput"]] = relationship(
        "ConsensusModelOutput", back_populates="consensus", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<ConsensusResult id={self.id} agreement={self.agreement_score}>"


class ConsensusModelOutput(Base):
    """Output from a single LLM model in a consensus analysis."""

    __tablename__ = "consensus_model_outputs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid_default)
    org_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    consensus_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("consensus_results.id", ondelete="CASCADE"), nullable=False, index=True
    )
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    model_provider: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    threat_classification: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    severity: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    mitre_mapping: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    risk_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    recommended_mitigation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    reasoning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    weight: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    prompt_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    estimated_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    consensus: Mapped["ConsensusResult"] = relationship("ConsensusResult", back_populates="model_outputs")

    def __repr__(self) -> str:
        return f"<ConsensusModelOutput model={self.model_name} confidence={self.confidence}>"


# ---------------------------------------------------------------------------
# Digital Twin Simulator
# ---------------------------------------------------------------------------

class DigitalTwinScenario(Base):
    """Predefined simulation scenario for the SOC digital twin."""

    __tablename__ = "digital_twin_scenarios"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid_default)
    org_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    scenario_type: Mapped[str] = mapped_column(String(64), nullable=False)
    attack_type: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    severity: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    expected_mitre_technique: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    expected_response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    scenario_config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    icon: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    difficulty: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, default="medium")
    is_builtin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<DigitalTwinScenario name={self.name} type={self.scenario_type}>"


class DigitalTwinRun(Base):
    """A single execution of a digital twin simulation scenario."""

    __tablename__ = "digital_twin_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid_default)
    org_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    scenario_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    scenario_name: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="running")
    synthetic_incidents: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    agent_responses: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    expected_outcomes: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    actual_outcomes: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    accuracy_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    response_quality_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    comparison_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<DigitalTwinRun id={self.id} status={self.status}>"


# ---------------------------------------------------------------------------
# Cost Intelligence
# ---------------------------------------------------------------------------

class CostUsageLog(Base):
    """Tracks LLM token usage and cost per operation for cost intelligence."""

    __tablename__ = "cost_usage_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid_default)
    org_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    incident_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    workflow_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    agent_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    model_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    prompt_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    estimated_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    cache_hit: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    cache_savings: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    memory_reuse_savings: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    feature_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<CostUsageLog model={self.model_name} cost={self.estimated_cost}>"
