import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, SmallInteger, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import NPSSentiment, NPSTrigger


class NPSResponse(Base):
    __tablename__ = "nps_responses"
    __table_args__ = (
        CheckConstraint("score >= 0 AND score <= 10", name="nps_score_range"),
        Index("ix_nps_member_date", "member_id", "response_date"),
        Index("ix_nps_score", "score"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    member_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("members.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    score: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    sentiment: Mapped[NPSSentiment] = mapped_column(
        Enum(NPSSentiment, name="nps_sentiment_enum", native_enum=False),
        nullable=False,
    )
    sentiment_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    trigger: Mapped[NPSTrigger] = mapped_column(
        Enum(NPSTrigger, name="nps_trigger_enum", native_enum=False),
        nullable=False,
    )
    response_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    extra_data: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    member = relationship("Member", back_populates="nps_responses")
