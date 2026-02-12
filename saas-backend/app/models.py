import enum
import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Enum, Integer, String, func, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class MemberStatus(str, enum.Enum):
    ACTIVE = "active"
    CANCELLED = "cancelled"

class RiskLevel(str, enum.Enum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"

class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class Member(Base):
    __tablename__ = "members"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    status: Mapped[MemberStatus] = mapped_column(Enum(MemberStatus), default=MemberStatus.ACTIVE)
    join_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_checkin: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    risk_score: Mapped[int] = mapped_column(Integer, default=0)
    risk_level: Mapped[RiskLevel] = mapped_column(Enum(RiskLevel), default=RiskLevel.GREEN)
    
    # Relacionamento com Tarefas
    tasks: Mapped[list["Task"]] = relationship("Task", back_populates="member", cascade="all, delete-orphan")

class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    member_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("members.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relacionamento com Membro
    member: Mapped["Member"] = relationship("Member", back_populates="tasks")