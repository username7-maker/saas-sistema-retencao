import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.models.base import Base
from app.models.body_composition_constants import ACTUAR_SYNC_ATTEMPT_STATUSES, ACTUAR_SYNC_MODES


class BodyCompositionSyncAttempt(Base):
    __tablename__ = "body_composition_sync_attempts"
    __table_args__ = (
        CheckConstraint(
            f"sync_mode IN {ACTUAR_SYNC_MODES}",
            name="bcsa_sync_mode_valid",
        ),
        CheckConstraint(
            f"status IN {ACTUAR_SYNC_ATTEMPT_STATUSES}",
            name="bcsa_status_valid",
        ),
        Index("ix_bcsa_evaluation_created", "body_composition_evaluation_id", "created_at"),
        Index("ix_bcsa_gym_created", "gym_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    gym_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("gyms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    body_composition_evaluation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("body_composition_evaluations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sync_mode: Mapped[str] = mapped_column(String(20), nullable=False)
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload_snapshot_json: Mapped[dict | list | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    evaluation = relationship("BodyCompositionEvaluation", back_populates="sync_attempts")
