import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, ForeignKey, Index, Numeric, SmallInteger, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Goal(Base, TimestampMixin):
    __tablename__ = "goals"
    __table_args__ = (
        CheckConstraint("target_value >= 0", name="goal_target_non_negative"),
        CheckConstraint("alert_threshold_pct >= 1 AND alert_threshold_pct <= 100", name="goal_alert_threshold_range"),
        CheckConstraint("comparator IN ('gte', 'lte')", name="goal_comparator_allowed"),
        Index("ix_goals_gym_period", "gym_id", "period_start", "period_end"),
        Index("ix_goals_active_metric", "is_active", "metric_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    gym_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("gyms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(140), nullable=False)
    metric_type: Mapped[str] = mapped_column(String(40), nullable=False)
    comparator: Mapped[str] = mapped_column(String(3), default="gte", nullable=False)
    target_value: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    alert_threshold_pct: Mapped[int] = mapped_column(SmallInteger, default=80, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
