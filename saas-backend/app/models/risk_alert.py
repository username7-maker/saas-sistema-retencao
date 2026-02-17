import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import RiskLevel


class RiskAlert(Base):
    __tablename__ = "risk_alerts"
    __table_args__ = (
        Index("ix_risk_alerts_gym_level", "gym_id", "level"),
        Index("ix_risk_alerts_member_created", "member_id", "created_at"),
        Index("ix_risk_alerts_level_resolved", "level", "resolved"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    gym_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("gyms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("members.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    level: Mapped[RiskLevel] = mapped_column(
        Enum(RiskLevel, name="risk_level_enum", native_enum=False),
        nullable=False,
        index=True,
    )
    reasons: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    action_history: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    automation_stage: Mapped[str | None] = mapped_column(String(32), nullable=True)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    resolved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    member = relationship("Member", back_populates="risk_alerts")
    resolved_by = relationship("User")
