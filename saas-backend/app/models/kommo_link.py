import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class KommoMemberLink(Base, TimestampMixin):
    __tablename__ = "kommo_member_links"
    __table_args__ = (
        UniqueConstraint("gym_id", "member_id", name="uq_kommo_member_links_gym_member"),
        Index("ix_kommo_member_links_gym_lead", "gym_id", "kommo_lead_id"),
        Index("ix_kommo_member_links_gym_contact", "gym_id", "kommo_contact_id"),
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
    kommo_contact_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    kommo_lead_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    last_handoff_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_action_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
