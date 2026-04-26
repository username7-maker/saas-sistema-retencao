import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class MemberConsentRecord(Base, TimestampMixin):
    __tablename__ = "member_consent_records"
    __table_args__ = (
        Index("ix_member_consent_records_gym_member", "gym_id", "member_id"),
        Index("ix_member_consent_records_member_type_created", "member_id", "consent_type", "created_at"),
        Index("ix_member_consent_records_expiration", "gym_id", "expires_at"),
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
    consent_type: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="accepted", server_default="accepted")
    source: Mapped[str] = mapped_column(String(80), nullable=False, default="manual", server_default="manual")
    document_title: Mapped[str | None] = mapped_column(String(160), nullable=True)
    document_version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    evidence_ref: Mapped[str | None] = mapped_column(String(500), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    extra_data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict, server_default="{}")

    member = relationship("Member", back_populates="consent_records")
