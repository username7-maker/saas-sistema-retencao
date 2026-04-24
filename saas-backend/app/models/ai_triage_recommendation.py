import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class AITriageRecommendation(Base, TimestampMixin):
    __tablename__ = "ai_triage_recommendations"
    __table_args__ = (
        UniqueConstraint(
            "gym_id",
            "source_domain",
            "source_entity_kind",
            "source_entity_id",
            name="uq_ai_triage_recommendation_natural_key",
        ),
        Index("ix_ai_triage_recommendations_gym_active_priority", "gym_id", "is_active", "priority_score"),
        Index("ix_ai_triage_recommendations_source", "source_domain", "source_entity_kind", "source_entity_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    gym_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("gyms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_domain: Mapped[str] = mapped_column(String(32), nullable=False)
    source_entity_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    source_entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    member_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("members.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    lead_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("leads.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    priority_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    suggestion_state: Mapped[str] = mapped_column(String(24), default="suggested", nullable=False)
    approval_state: Mapped[str] = mapped_column(String(24), default="pending", nullable=False)
    execution_state: Mapped[str] = mapped_column(String(24), default="pending", nullable=False)
    outcome_state: Mapped[str] = mapped_column(String(24), default="pending", nullable=False)
    last_refreshed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payload_snapshot: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    member = relationship("Member")
    lead = relationship("Lead")
