import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class ObjectionResponse(Base, TimestampMixin):
    __tablename__ = "objection_responses"
    __table_args__ = (
        Index("ix_objection_responses_gym_active", "gym_id", "is_active"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    gym_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("gyms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    trigger_keywords: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list, server_default="[]")
    objection_summary: Mapped[str] = mapped_column(Text, nullable=False)
    response_template: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
