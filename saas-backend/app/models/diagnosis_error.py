import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class DiagnosisError(Base):
    __tablename__ = "diagnosis_errors"
    __table_args__ = (
        Index("ix_diagnosis_errors_gym_created", "gym_id", "created_at"),
        Index("ix_diagnosis_errors_email_created", "prospect_email", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    gym_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("gyms.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    prospect_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    prospect_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    endpoint: Mapped[str] = mapped_column(String(80), nullable=False)
    error_message: Mapped[str] = mapped_column(Text, nullable=False)
    traceback_snippet: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
