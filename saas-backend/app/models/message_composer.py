import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class GymMessageTemplateOverride(Base, TimestampMixin):
    __tablename__ = "gym_message_template_overrides"
    __table_args__ = (
        UniqueConstraint("gym_id", "template_key", name="uq_gym_message_template_override_key"),
        Index("ix_gym_message_template_override_gym_active", "gym_id", "is_active"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    gym_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("gyms.id", ondelete="CASCADE"), nullable=False, index=True
    )
    template_key: Mapped[str] = mapped_column(String(100), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class MessageCompositionRequest(Base, TimestampMixin):
    __tablename__ = "message_composition_requests"
    __table_args__ = (
        UniqueConstraint("gym_id", "idempotency_key", name="uq_message_composition_gym_idempotency"),
        Index("ix_message_composition_gym_created", "gym_id", "created_at"),
        Index("ix_message_composition_gym_status", "gym_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    gym_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("gyms.id", ondelete="CASCADE"), nullable=False, index=True
    )
    requested_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    source_type: Mapped[str] = mapped_column(String(40), nullable=False)
    source_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(180), nullable=False)
    template_key: Mapped[str] = mapped_column(String(100), nullable=False)
    objective: Mapped[str] = mapped_column(String(280), nullable=False)
    base_message: Mapped[str] = mapped_column(Text, nullable=False)
    improved_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    base_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    improved_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    context_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="previewed", server_default="previewed")
    provider: Mapped[str] = mapped_column(String(32), nullable=False, default="system", server_default="system")
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    prompt_key: Mapped[str | None] = mapped_column(String(100), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    fallback_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    warnings_json: Mapped[list] = mapped_column(JSONB, nullable=False, default=list, server_default="[]")
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
