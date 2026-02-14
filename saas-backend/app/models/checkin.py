import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, SmallInteger, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import CheckinSource


class Checkin(Base):
    __tablename__ = "checkins"
    __table_args__ = (
        CheckConstraint("hour_bucket >= 0 AND hour_bucket <= 23", name="hour_bucket_range"),
        CheckConstraint("weekday >= 0 AND weekday <= 6", name="weekday_range"),
        UniqueConstraint("member_id", "checkin_at", name="uq_checkin_member_datetime"),
        Index("ix_checkins_member_date_desc", "member_id", "checkin_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("members.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    checkin_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    source: Mapped[CheckinSource] = mapped_column(
        Enum(CheckinSource, name="checkin_source_enum", native_enum=False),
        default=CheckinSource.MANUAL,
        nullable=False,
    )
    hour_bucket: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    weekday: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    extra_data: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    member = relationship("Member", back_populates="checkins")
