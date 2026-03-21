import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Gym(Base, TimestampMixin):
    __tablename__ = "gyms"
    __table_args__ = (
        Index("ix_gyms_slug_unique", "slug", unique=True),
        Index("ix_gyms_whatsapp_instance", "whatsapp_instance", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    whatsapp_instance: Mapped[str | None] = mapped_column(String(120), nullable=True)
    whatsapp_status: Mapped[str] = mapped_column(String(30), nullable=False, default="disconnected")
    whatsapp_phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    whatsapp_connected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    users = relationship("User", back_populates="gym")
    members = relationship("Member", back_populates="gym")
    goals = relationship("Goal")
