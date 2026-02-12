from pydantic import BaseModel, EmailStr, Field, StringConstraints
from typing import Annotated, Optional, List
from datetime import datetime
from uuid import UUID
from enum import Enum

# --- ENUMS ---
class MemberStatus(str, Enum):
    ACTIVE = "active"
    CANCELLED = "cancelled"

class RiskLevel(str, Enum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"

# --- SCHEMAS DE AUTENTICAÇÃO ---
class UserCreate(BaseModel):
    email: EmailStr
    password: Annotated[str, StringConstraints(min_length=8, max_length=72)]

class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

# --- SCHEMAS DE MEMBROS ---
class MemberBase(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    last_checkin: Optional[datetime] = None

class MemberCreate(MemberBase):
    pass

class MemberUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    status: Optional[MemberStatus] = None

class MemberResponse(MemberBase):
    id: UUID
    status: MemberStatus
    risk_score: int
    risk_level: RiskLevel
    join_date: datetime

    class Config:
        from_attributes = True

# --- SCHEMAS DE TAREFAS (TASKS) ---
class TaskBase(BaseModel):
    member_id: UUID
    description: Optional[str] = None
    is_completed: bool = False

class TaskCreate(TaskBase):
    """O que o Frontend envia ao salvar um novo atendimento."""
    pass

class TaskUpdate(BaseModel):
    is_completed: Optional[bool] = None
    description: Optional[str] = None 

class Task(TaskBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True

# Alias para compatibilidade com as rotas
TaskResponse = Task

# --- SCHEMA DE DASHBOARD ---
class DashboardSummary(BaseModel):
    total_members: int
    active_members: int
    risk_green: int
    risk_yellow: int
    risk_red: int
    pending_tasks: int

# --- SCHEMA PARA IMPORTAÇÃO ---
class MemberImportRow(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    last_checkin: Optional[str] = None