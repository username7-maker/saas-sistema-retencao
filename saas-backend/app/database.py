import logging
from collections.abc import Generator
from contextvars import ContextVar
from uuid import UUID

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker, with_loader_criteria

from app.core.config import settings

logger = logging.getLogger(__name__)
from app.models import (
    ActuarMemberLink,
    ActuarSyncAttempt,
    ActuarSyncJob,
    Assessment,
    AuditLog,
    AutomationExecutionLog,
    AutomationRule,
    BodyCompositionEvaluation,
    BodyCompositionSyncAttempt,
    Checkin,
    DiagnosisError,
    Goal,
    InAppNotification,
    LeadBooking,
    Lead,
    Member,
    MemberConstraints,
    MemberGoal,
    MemberRiskHistory,
    MessageLog,
    NPSResponse,
    NurturingSequence,
    RiskAlert,
    Task,
    TrainingPlan,
    User,
)
from app.models.base import Base


engine = create_engine(
    str(settings.database_url),
    pool_pre_ping=True,
    future=True,
    pool_size=20,
    max_overflow=10,
    pool_recycle=3600,
    pool_timeout=30,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

_current_gym_id: ContextVar[UUID | None] = ContextVar("current_gym_id", default=None)
_unscoped_access: ContextVar[bool] = ContextVar("unscoped_access", default=False)

_DENY_GYM_ID = UUID(int=0)  # Impossible UUID — matches no real row
TENANT_SCOPED_MODELS = (
    User,
    Member,
    ActuarMemberLink,
    ActuarSyncJob,
    ActuarSyncAttempt,
    Checkin,
    RiskAlert,
    Lead,
    LeadBooking,
    Task,
    NPSResponse,
    AuditLog,
    InAppNotification,
    AutomationExecutionLog,
    AutomationRule,
    MessageLog,
    Goal,
    Assessment,
    MemberConstraints,
    MemberGoal,
    MemberRiskHistory,
    NurturingSequence,
    DiagnosisError,
    TrainingPlan,
    BodyCompositionEvaluation,
    BodyCompositionSyncAttempt,
)
_TENANT_SCOPED_TABLE_NAMES = frozenset(m.__tablename__ for m in TENANT_SCOPED_MODELS)


def set_current_gym_id(gym_id: UUID | None) -> None:
    _current_gym_id.set(gym_id)


def clear_current_gym_id() -> None:
    _current_gym_id.set(None)


def get_current_gym_id() -> UUID | None:
    return _current_gym_id.get()


def set_unscoped_access(enabled: bool) -> None:
    """Allow background jobs to query across all tenants without a gym_id context.

    Must be called explicitly by cross-gym background jobs (e.g. nurturing, booking).
    All request-scoped code should never call this.
    """
    _unscoped_access.set(enabled)


@event.listens_for(Session, "do_orm_execute")
def _apply_tenant_filter(execute_state) -> None:  # type: ignore[no-untyped-def]
    if not execute_state.is_select:
        return
    if execute_state.execution_options.get("include_all_tenants"):
        return

    gym_id = get_current_gym_id()
    if gym_id is None:
        if _unscoped_access.get():
            # Explicit cross-gym access granted (e.g. nurturing/booking background jobs).
            return
        # Default-deny: apply impossible gym_id so no tenant rows leak.
        # Legitimate non-scoped queries (auth login, Gym table) don't touch
        # TENANT_SCOPED_MODELS so with_loader_criteria is a no-op for them.
        gym_id = _DENY_GYM_ID
        logger.debug("No gym_id context — applying deny filter to prevent data leak.")

    statement = execute_state.statement
    for model in TENANT_SCOPED_MODELS:
        statement = statement.options(
            with_loader_criteria(
                model,
                lambda cls: cls.gym_id == gym_id,
                include_aliases=True,
            )
        )
    execute_state.statement = statement


def _infer_gym_id_from_relations(session: Session, obj: object) -> UUID | None:
    relation_candidates = ("member", "lead", "user", "assigned_user", "owner", "resolved_by", "assessment")
    for relation_name in relation_candidates:
        related = getattr(obj, relation_name, None)
        gym_id = getattr(related, "gym_id", None)
        if gym_id:
            return gym_id

    fk_candidates: tuple[tuple[str, type], ...] = (
        ("member_id", Member),
        ("lead_id", Lead),
        ("user_id", User),
        ("assigned_to_user_id", User),
        ("owner_id", User),
        ("resolved_by_user_id", User),
        ("assigned_user_id", User),
        ("converted_member_id", Member),
        ("automation_rule_id", AutomationRule),
        ("assessment_id", Assessment),
    )
    with session.no_autoflush:
        for fk_name, model in fk_candidates:
            fk_value = getattr(obj, fk_name, None)
            if not fk_value:
                continue
            related = session.get(model, fk_value)
            gym_id = getattr(related, "gym_id", None)
            if gym_id:
                return gym_id
    return None


@event.listens_for(Session, "before_flush")
def _assign_gym_on_new_objects(session: Session, flush_context, instances) -> None:  # type: ignore[no-untyped-def,unused-argument]
    tenant_gym_id = get_current_gym_id()
    for obj in session.new:
        if not hasattr(obj, "gym_id"):
            continue
        if getattr(obj, "gym_id", None):
            continue

        inferred_gym_id = tenant_gym_id or _infer_gym_id_from_relations(session, obj)
        if inferred_gym_id:
            setattr(obj, "gym_id", inferred_gym_id)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
