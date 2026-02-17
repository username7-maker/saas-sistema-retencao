import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, DateTime, Enum, ForeignKey, Index, Integer, Numeric, SmallInteger, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin
from app.models.enums import MemberStatus, RiskLevel


class Member(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "members"
    __table_args__ = (
        CheckConstraint("risk_score >= 0 AND risk_score <= 100", name="risk_score_range"),
        CheckConstraint("nps_last_score >= 0 AND nps_last_score <= 10", name="nps_last_score_range"),
        Index("ix_members_gym_status", "gym_id", "status"),
        Index("ix_members_risk_level_score", "risk_level", "risk_score"),
        Index("ix_members_status_last_checkin", "status", "last_checkin_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    gym_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("gyms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    assigned_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    cpf_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[MemberStatus] = mapped_column(
        Enum(MemberStatus, name="member_status_enum", native_enum=False),
        default=MemberStatus.ACTIVE,
        nullable=False,
        index=True,
    )
    plan_name: Mapped[str] = mapped_column(String(100), default="Plano Base", nullable=False)
    monthly_fee: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    join_date: Mapped[date] = mapped_column(Date, default=date.today, nullable=False, index=True)
    cancellation_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    preferred_shift: Mapped[str | None] = mapped_column(String(24), nullable=True)
    nps_last_score: Mapped[int] = mapped_column(SmallInteger, default=7, nullable=False)
    loyalty_months: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    risk_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    risk_level: Mapped[RiskLevel] = mapped_column(
        Enum(RiskLevel, name="risk_level_enum", native_enum=False),
        default=RiskLevel.GREEN,
        nullable=False,
    )
    last_checkin_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    extra_data: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    gym = relationship("Gym", back_populates="members")
    assigned_user = relationship("User", back_populates="assigned_members")
    checkins = relationship("Checkin", back_populates="member", cascade="all, delete-orphan")
    risk_alerts = relationship("RiskAlert", back_populates="member", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="member")
    nps_responses = relationship("NPSResponse", back_populates="member")
    audit_logs = relationship("AuditLog", back_populates="member")
    in_app_notifications = relationship("InAppNotification", back_populates="member")
