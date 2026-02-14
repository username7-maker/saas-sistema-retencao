import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin
from app.models.enums import RoleEnum


class User(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_role_active", "role", "is_active"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[RoleEnum] = mapped_column(Enum(RoleEnum, name="role_enum", native_enum=False), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    refresh_token_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    refresh_token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    assigned_members = relationship("Member", back_populates="assigned_user")
    tasks_assigned = relationship("Task", back_populates="assigned_user")
    leads_owned = relationship("Lead", back_populates="owner")
    audit_logs = relationship("AuditLog", back_populates="user")
