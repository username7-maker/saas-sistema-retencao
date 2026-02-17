import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class AutomationTrigger:
    RISK_LEVEL_CHANGE = "risk_level_change"
    INACTIVITY_DAYS = "inactivity_days"
    NPS_SCORE = "nps_score"
    LEAD_STALE = "lead_stale"
    BIRTHDAY = "birthday"
    CHECKIN_STREAK = "checkin_streak"


class AutomationAction:
    CREATE_TASK = "create_task"
    SEND_WHATSAPP = "send_whatsapp"
    SEND_EMAIL = "send_email"
    NOTIFY = "notify"


class AutomationRule(Base, TimestampMixin):
    __tablename__ = "automation_rules"
    __table_args__ = (
        Index("ix_automation_rules_gym_active", "gym_id", "is_active"),
        Index("ix_automation_rules_trigger_active", "trigger_type", "is_active"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    gym_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("gyms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    trigger_type: Mapped[str] = mapped_column(String(40), nullable=False)
    trigger_config: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    action_type: Mapped[str] = mapped_column(String(40), nullable=False)
    action_config: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    executions_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
