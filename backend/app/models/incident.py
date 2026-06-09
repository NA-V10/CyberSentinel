import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
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


# ---------------------------------------------------------------------------
# Helper for server-side defaults
# ---------------------------------------------------------------------------

def _uuid_default() -> uuid.UUID:
    return uuid.uuid4()


# ---------------------------------------------------------------------------
# Incident
# ---------------------------------------------------------------------------

class Incident(Base):
    """A single detected or reported cybersecurity incident."""

    __tablename__ = "incidents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=_uuid_default,
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    timestamp: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    source_ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    dest_ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    protocol: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    attack_type: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    severity: Mapped[Optional[str]] = mapped_column(
        Enum("low", "medium", "high", "critical", name="severity_enum"),
        nullable=True,
        index=True,
    )
    label: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    raw_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # The UUID of the corresponding vector in Qdrant
    embedding_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    feedbacks: Mapped[list["AnalystFeedback"]] = relationship(
        "AnalystFeedback", back_populates="incident", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Incident id={self.id} attack_type={self.attack_type} severity={self.severity}>"


# ---------------------------------------------------------------------------
# Conversation
# ---------------------------------------------------------------------------

class Conversation(Base):
    """A chat session between an analyst and the AI assistant."""

    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=_uuid_default,
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    title: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    messages: Mapped[list["Message"]] = relationship(
        "Message", back_populates="conversation", cascade="all, delete-orphan"
    )
    feedbacks: Mapped[list["AnalystFeedback"]] = relationship(
        "AnalystFeedback", back_populates="conversation", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Conversation id={self.id} user_id={self.user_id}>"


# ---------------------------------------------------------------------------
# Message
# ---------------------------------------------------------------------------

class Message(Base):
    """A single turn inside a :class:`Conversation`."""

    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=_uuid_default,
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(
        Enum("user", "assistant", "system", name="message_role_enum"),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # Flexible extra data: token counts, tool calls, citations, etc.
    # Column is named "metadata" in the DB but "extra_data" on the ORM to avoid
    # SQLAlchemy's reserved attribute name.
    extra_data: Mapped[Optional[dict]] = mapped_column("metadata", JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="messages")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Message id={self.id} role={self.role}>"


# ---------------------------------------------------------------------------
# AnalystFeedback
# ---------------------------------------------------------------------------

class AnalystFeedback(Base):
    """Feedback provided by an analyst after reviewing an incident response."""

    __tablename__ = "analyst_feedback"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=_uuid_default,
    )
    incident_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("incidents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    conversation_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    # 1 = very poor … 5 = excellent
    rating: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    mitigation_worked: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    incident: Mapped[Optional["Incident"]] = relationship(
        "Incident", back_populates="feedbacks"
    )
    conversation: Mapped[Optional["Conversation"]] = relationship(
        "Conversation", back_populates="feedbacks"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<AnalystFeedback id={self.id} rating={self.rating}>"


# ---------------------------------------------------------------------------
# MemoryEntry
# ---------------------------------------------------------------------------

class MemoryEntry(Base):
    """A long-term memory fragment associated with a user or the system."""

    __tablename__ = "memory_entries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=_uuid_default,
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # The UUID of the corresponding vector in Qdrant (nullable until embedded)
    embedding_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    # e.g. "episodic", "semantic", "procedural"
    memory_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<MemoryEntry id={self.id} memory_type={self.memory_type}>"


# ---------------------------------------------------------------------------
# MITREMapping
# ---------------------------------------------------------------------------

class MITREMapping(Base):
    """MITRE ATT&CK mapping for an incident."""

    __tablename__ = "mitre_mappings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid_default)
    incident_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("incidents.id", ondelete="SET NULL"), nullable=True, index=True
    )
    org_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    tactic: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    technique: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    technique_id: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    attack_category: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    reasoning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    recommended_mitigation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<MITREMapping id={self.id} technique_id={self.technique_id}>"


# ---------------------------------------------------------------------------
# IncidentApproval
# ---------------------------------------------------------------------------

class IncidentApproval(Base):
    """Human-in-the-loop approval record for an incident's AI recommendation."""

    __tablename__ = "incident_approvals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid_default)
    incident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    org_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    approved_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    approval_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    edited_response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    escalated_to: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<IncidentApproval id={self.id} status={self.approval_status}>"


# ---------------------------------------------------------------------------
# AuditLog
# ---------------------------------------------------------------------------

class AuditLog(Base):
    """Immutable audit trail for all significant platform actions."""

    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid_default)
    org_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    resource_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    resource_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<AuditLog id={self.id} event_type={self.event_type}>"


# ---------------------------------------------------------------------------
# SLATracker
# ---------------------------------------------------------------------------

class SLATracker(Base):
    """SLA deadline tracker per incident."""

    __tablename__ = "sla_trackers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid_default)
    incident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True, unique=True
    )
    org_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    assigned_level: Mapped[str] = mapped_column(String(64), nullable=False, default="L1 Analyst")
    sla_deadline: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    sla_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    is_breached: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<SLATracker id={self.id} severity={self.severity} breached={self.is_breached}>"
