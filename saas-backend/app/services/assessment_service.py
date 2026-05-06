import logging
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.core.cache import invalidate_dashboard_cache
from app.models import Checkin, Member, RoleEnum, Task, TaskPriority, TaskStatus, User
from app.models.assessment import Assessment, MemberConstraints, MemberGoal, TrainingPlan
from app.services.assessment_analytics_service import generate_ai_insights
from app.services.assessment_intelligence_service import sync_assessment_intelligence_tasks
from app.services.autopilot_event_service import record_event
from app.services.autopilot_resolver_service import resolve_event
from app.services.preferred_shift_service import normalize_preferred_shift, normalize_preferred_shift_scope
from app.services.task_event_service import record_task_event


logger = logging.getLogger(__name__)

_DEFAULT_ASSESSMENT_DUE_DAYS = 90
_ASSESSMENT_QUEUE_RESOLUTION_KEYS = (
    "assessment_queue_resolution",
    "assessment_queue_resolution_note",
    "assessment_queue_resolution_at",
    "assessment_queue_resolution_by",
)
_ASSESSMENT_DUE_BY_PLAN_KEYWORD = {
    "mensal": 30,
    "trimestral": 90,
    "semestral": 90,
    "anual": 120,
}
_ASSESSMENT_FEEDBACK_TASK_SOURCE = "assessment_feedback_followup"
_ASSESSMENT_FEEDBACK_TASK_DAY_OFFSET = 14
_ASSESSMENT_TRAINING_DELIVERY_TASK_SOURCE = "assessment_training_delivery_check_d8"
_ASSESSMENT_TRAINING_DELIVERY_TASK_DAY_OFFSET = 8
_ASSESSMENT_REASSESSMENT_TASK_SOURCE = "assessment_reassessment_due"
_ASSESSMENT_REASSESSMENT_VISIBLE_BEFORE_DAYS = 7
_POST_ASSESSMENT_TASK_SOURCES = {
    _ASSESSMENT_TRAINING_DELIVERY_TASK_SOURCE,
    _ASSESSMENT_FEEDBACK_TASK_SOURCE,
    _ASSESSMENT_REASSESSMENT_TASK_SOURCE,
}


def _safe(fn, default=None):
    """Execute fn() returning default on any error, logging the failure."""
    try:
        return fn()
    except Exception:
        logger.exception("Falha parcial em Profile 360")
        return default


def get_member_or_404(db: Session, member_id: UUID, gym_id: UUID | None = None) -> Member:
    stmt = select(Member).where(Member.id == member_id, Member.deleted_at.is_(None))
    if gym_id is not None:
        stmt = stmt.where(Member.gym_id == gym_id)
    member = db.scalar(stmt)
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membro nao encontrado")
    return member


def _calculate_next_assessment_due(db: Session, member_id: UUID, assessment_date: datetime) -> date:
    """Calcula next_assessment_due baseado no tipo de plano do membro."""
    member = db.scalar(select(Member).where(Member.id == member_id))
    if not member:
        return (assessment_date + timedelta(days=_DEFAULT_ASSESSMENT_DUE_DAYS)).date()

    plan = (member.plan_name or "").lower()
    due_days = next(
        (days for keyword, days in _ASSESSMENT_DUE_BY_PLAN_KEYWORD.items() if keyword in plan),
        _DEFAULT_ASSESSMENT_DUE_DAYS,
    )
    return (assessment_date + timedelta(days=due_days)).date()


def create_assessment(
    db: Session,
    member_id: UUID,
    evaluator_id: UUID,
    data: dict,
    *,
    commit: bool = True,
) -> Assessment:
    member = get_member_or_404(db, member_id)
    previous_count = db.scalar(
        select(func.count(Assessment.id)).where(Assessment.member_id == member_id, Assessment.deleted_at.is_(None))
    ) or 0

    assessment_date = _normalize_datetime(data.get("assessment_date"))
    height_cm = _to_decimal(data.get("height_cm"))
    weight_kg = _to_decimal(data.get("weight_kg"))
    bmi_value = _calculate_bmi(height_cm, weight_kg)
    if bmi_value is None:
        bmi_value = _to_decimal(data.get("bmi"))

    member_gym_id = getattr(member, "gym_id", None)
    assessment = Assessment(
        gym_id=member_gym_id,
        member_id=member_id,
        evaluator_id=evaluator_id,
        assessment_number=int(previous_count) + 1,
        assessment_date=assessment_date,
        next_assessment_due=_calculate_next_assessment_due(db, member_id, assessment_date),
        height_cm=height_cm,
        weight_kg=weight_kg,
        bmi=bmi_value,
        body_fat_pct=_to_decimal(data.get("body_fat_pct")),
        lean_mass_kg=_to_decimal(data.get("lean_mass_kg")),
        waist_cm=_to_decimal(data.get("waist_cm")),
        hip_cm=_to_decimal(data.get("hip_cm")),
        chest_cm=_to_decimal(data.get("chest_cm")),
        arm_cm=_to_decimal(data.get("arm_cm")),
        thigh_cm=_to_decimal(data.get("thigh_cm")),
        resting_hr=data.get("resting_hr"),
        blood_pressure_systolic=data.get("blood_pressure_systolic"),
        blood_pressure_diastolic=data.get("blood_pressure_diastolic"),
        vo2_estimated=_to_decimal(data.get("vo2_estimated")),
        strength_score=data.get("strength_score"),
        flexibility_score=data.get("flexibility_score"),
        cardio_score=data.get("cardio_score"),
        observations=data.get("observations"),
        extra_data=data.get("extra_data") or {},
    )
    if _clear_assessment_queue_resolution(member):
        db.add(member)
    db.add(assessment)
    if commit:
        db.commit()
    else:
        db.flush()
    db.refresh(assessment)

    generate_ai_insights(db, assessment, commit=False)
    _ensure_post_assessment_ladder_tasks(
        db,
        member=member,
        assessment=assessment,
        evaluator_id=evaluator_id,
        commit=False,
    )
    assessment_event = record_event(
        db,
        gym_id=member.gym_id,
        event_type="member_assessment_completed",
        source="assessment",
        member_id=member.id,
        metadata={"assessment_id": str(assessment.id), "assessment_number": assessment.assessment_number},
        deduplication_key=f"assessment:completed:{assessment.id}",
        flush=False,
    )
    resolve_event(db, assessment_event, flush=False)
    sync_assessment_intelligence_tasks(db, member_id, commit=False)

    if commit:
        db.commit()
    else:
        db.flush()

    return assessment


def _assessment_due_datetime(assessment: Assessment) -> datetime:
    next_assessment_due = getattr(assessment, "next_assessment_due", None)
    assessment_date = _normalize_datetime(getattr(assessment, "assessment_date", None))
    if next_assessment_due:
        due = datetime.combine(next_assessment_due, assessment_date.timetz())
        if due.tzinfo is None:
            return due.replace(tzinfo=timezone.utc)
        return due
    return assessment_date + timedelta(days=_DEFAULT_ASSESSMENT_DUE_DAYS)


def _post_assessment_visible_from(source: str, due_date: datetime) -> datetime:
    if source == _ASSESSMENT_REASSESSMENT_TASK_SOURCE:
        return due_date - timedelta(days=_ASSESSMENT_REASSESSMENT_VISIBLE_BEFORE_DAYS)
    return due_date


def _member_first_name(member: Member) -> str:
    member_name = getattr(member, "full_name", "Aluno") or "Aluno"
    return member_name.split()[0] if member_name else "Aluno"


def _user_covers_member_shift(user: User | None, member: Member) -> bool:
    if user is None or not getattr(user, "is_active", False) or getattr(user, "role", None) != RoleEnum.TRAINER:
        return False
    if getattr(user, "gym_id", None) != getattr(member, "gym_id", None):
        return False
    preferred_shift = normalize_preferred_shift(getattr(member, "preferred_shift", None))
    if not preferred_shift:
        return False
    user_scope = normalize_preferred_shift_scope(getattr(user, "work_shift_scope", None), fallback=getattr(user, "work_shift", None))
    return preferred_shift in user_scope


def _resolve_post_assessment_owner(db: Session, *, member: Member, evaluator_id: UUID | None) -> UUID | None:
    member_gym_id = getattr(member, "gym_id", None)
    if member_gym_id is None:
        return None
    evaluator = None
    if evaluator_id:
        evaluator = db.scalar(
            select(User).where(
                User.id == evaluator_id,
                User.gym_id == member_gym_id,
                User.deleted_at.is_(None),
                User.is_active.is_(True),
            )
        )
    if _user_covers_member_shift(evaluator, member):
        return evaluator.id

    trainers = list(
        db.scalars(
            select(User)
            .where(
                User.gym_id == member_gym_id,
                User.role == RoleEnum.TRAINER,
                User.deleted_at.is_(None),
                User.is_active.is_(True),
            )
            .order_by(User.created_at.asc())
        ).all()
    )
    for trainer in trainers:
        if _user_covers_member_shift(trainer, member):
            return trainer.id
    return None


def _assessment_source_payload(assessment: Assessment, assessment_source_type: str) -> dict:
    source_id = str(getattr(assessment, "id"))
    payload = {"type": assessment_source_type, "id": source_id}
    if assessment_source_type == "body_composition":
        payload["body_composition_evaluation_id"] = source_id
    else:
        payload["assessment_id"] = source_id
    return payload


def _merge_assessment_sources(existing_sources: object, source_payload: dict) -> list[dict]:
    sources = [dict(item) for item in existing_sources if isinstance(item, dict)] if isinstance(existing_sources, list) else []
    source_key = (source_payload.get("type"), source_payload.get("id"))
    if not any((item.get("type"), item.get("id")) == source_key for item in sources):
        sources.append(source_payload)
    return sources


def _post_assessment_task_specs(
    member: Member,
    assessment: Assessment,
    *,
    assessment_source_type: str = "formal_assessment",
) -> list[dict]:
    member_name = getattr(member, "full_name", "Aluno") or "Aluno"
    first_name = _member_first_name(member)
    preferred_shift = normalize_preferred_shift(getattr(member, "preferred_shift", None))
    reassessment_due = _assessment_due_datetime(assessment)
    assessment_date = _normalize_datetime(getattr(assessment, "assessment_date", None))
    reassessment_day_offset = max(0, (reassessment_due.date() - assessment_date.date()).days)
    assessment_number = getattr(assessment, "assessment_number", None)
    source_payload = _assessment_source_payload(assessment, assessment_source_type)
    specs = [
        {
            "source": _ASSESSMENT_TRAINING_DELIVERY_TASK_SOURCE,
            "technical_ladder_step": "training_delivery_check_d8",
            "day_offset": _ASSESSMENT_TRAINING_DELIVERY_TASK_DAY_OFFSET,
            "due_date": assessment_date + timedelta(days=_ASSESSMENT_TRAINING_DELIVERY_TASK_DAY_OFFSET),
            "priority": TaskPriority.HIGH,
            "title": f"Verificar treino D+8 - {member_name}",
            "description": (
                "Confirmar se o aluno recebeu o treino depois da avaliacao, se entendeu a rotina "
                "e se precisa de ajuste tecnico inicial."
            ),
            "primary_action_label": "Verificar treino",
            "suggested_message": (
                f"Oi, {first_name}! Passando para confirmar se seu treino ja ficou claro e se voce conseguiu comecar bem."
            ),
        },
        {
            "source": _ASSESSMENT_FEEDBACK_TASK_SOURCE,
            "technical_ladder_step": "training_feedback_d14",
            "day_offset": _ASSESSMENT_FEEDBACK_TASK_DAY_OFFSET,
            "due_date": assessment_date + timedelta(days=_ASSESSMENT_FEEDBACK_TASK_DAY_OFFSET),
            "priority": TaskPriority.MEDIUM,
            "title": f"Follow-up D+14 da avaliacao - {member_name}",
            "description": (
                "Verificar com o aluno o feedback do treino, aderencia inicial e necessidade de ajuste apos 14 dias da avaliacao."
            ),
            "primary_action_label": "Registrar feedback",
            "suggested_message": (
                f"Oi, {first_name}! Ja se passaram 14 dias da sua avaliacao. "
                "Quero entender como voce esta se sentindo com o treino e se precisamos ajustar alguma coisa."
            ),
        },
        {
            "source": _ASSESSMENT_REASSESSMENT_TASK_SOURCE,
            "technical_ladder_step": "reassessment_due",
            "day_offset": reassessment_day_offset,
            "due_date": reassessment_due,
            "priority": TaskPriority.MEDIUM,
            "title": f"Reavaliacao prevista - {member_name}",
            "description": (
                "Agendar ou confirmar a proxima reavaliacao do aluno conforme a janela definida na avaliacao anterior."
            ),
            "primary_action_label": "Agendar reavaliacao",
            "suggested_message": (
                f"Oi, {first_name}! Sua janela de reavaliacao esta chegando. Vamos marcar um horario para revisar sua evolucao?"
            ),
        },
    ]
    for spec in specs:
        visible_from = _post_assessment_visible_from(spec["source"], spec["due_date"])
        spec["extra_data"] = {
            "source": spec["source"],
            "domain": "trainer",
            "assessment_id": str(assessment.id),
            "assessment_source_id": str(assessment.id),
            "assessment_source_type": assessment_source_type,
            "assessment_sources": [source_payload],
            "assessment_number": assessment_number,
            "day_offset": spec["day_offset"],
            "owner_role": "coach",
            "preferred_shift": preferred_shift,
            "work_queue_visible_from": visible_from.isoformat(),
            "technical_ladder_step": spec["technical_ladder_step"],
            "primary_action_label": spec["primary_action_label"],
        }
        if assessment_source_type == "body_composition":
            spec["extra_data"]["body_composition_evaluation_id"] = str(assessment.id)
        else:
            spec["extra_data"]["formal_assessment_id"] = str(assessment.id)
    return specs


def _supersede_open_post_assessment_tasks(
    db: Session,
    *,
    member: Member,
    assessment: Assessment,
    evaluator_id: UUID | None,
    keep_task_ids: set[UUID] | None = None,
) -> None:
    now = datetime.now(tz=timezone.utc)
    keep_task_ids = keep_task_ids or set()
    member_gym_id = getattr(member, "gym_id", None)
    if member_gym_id is None:
        return
    tasks = list(
        db.scalars(
            select(Task).where(
                Task.member_id == member.id,
                Task.gym_id == member_gym_id,
                Task.deleted_at.is_(None),
                Task.status.in_((TaskStatus.TODO, TaskStatus.DOING)),
                Task.due_date >= now,
                Task.extra_data["source"].astext.in_(tuple(_POST_ASSESSMENT_TASK_SOURCES)),
                Task.extra_data["assessment_id"].astext != str(assessment.id),
            )
        ).all()
    )
    for task in tasks:
        if task.id in keep_task_ids:
            continue
        extra = dict(task.extra_data or {})
        extra["superseded_by_assessment_id"] = str(assessment.id)
        extra["superseded_at"] = now.isoformat()
        task.extra_data = extra
        task.status = TaskStatus.CANCELLED
        task.kanban_column = TaskStatus.CANCELLED.value
        db.add(task)
        record_task_event(
            db,
            task=task,
            current_user=None,
            event_type="status_changed",
            outcome="superseded_by_new_assessment",
            note="Task futura da regua tecnica substituida por nova avaliacao.",
            metadata_json={
                "source": "post_assessment_ladder",
                "new_assessment_id": str(assessment.id),
                "evaluator_id": str(evaluator_id) if evaluator_id else None,
            },
            flush=False,
        )


def _find_existing_post_assessment_task_for_cycle(
    db: Session,
    *,
    member: Member,
    spec: dict,
    assessment: Assessment,
) -> Task | None:
    source = spec["source"]
    source_id = str(assessment.id)
    exact = db.scalar(
        select(Task).where(
            Task.member_id == member.id,
            Task.deleted_at.is_(None),
            Task.extra_data["source"].astext == source,
            Task.extra_data["assessment_id"].astext == source_id,
        )
    )
    if exact:
        return exact

    due_date = spec["due_date"]
    return db.scalar(
        select(Task)
        .where(
            Task.member_id == member.id,
            Task.deleted_at.is_(None),
            Task.status.in_((TaskStatus.TODO, TaskStatus.DOING)),
            Task.extra_data["source"].astext == source,
            Task.due_date >= due_date - timedelta(hours=12),
            Task.due_date <= due_date + timedelta(hours=12),
        )
        .order_by(Task.created_at.desc())
        .limit(1)
    )


def _merge_post_assessment_task_source(task: Task, spec: dict) -> None:
    extra = dict(task.extra_data or {})
    new_extra = dict(spec["extra_data"])
    source_payload = new_extra["assessment_sources"][0]
    extra["assessment_sources"] = _merge_assessment_sources(extra.get("assessment_sources"), source_payload)
    extra["assessment_source_type"] = "mixed" if len(extra["assessment_sources"]) > 1 else source_payload.get("type")
    extra["assessment_source_id"] = source_payload.get("id")
    for key in ("body_composition_evaluation_id", "formal_assessment_id"):
        if key in new_extra:
            extra[key] = new_extra[key]
    if not extra.get("preferred_shift") and new_extra.get("preferred_shift"):
        extra["preferred_shift"] = new_extra["preferred_shift"]
    extra["work_queue_visible_from"] = new_extra.get("work_queue_visible_from", extra.get("work_queue_visible_from"))
    task.extra_data = extra


def _ensure_post_assessment_ladder_tasks(
    db: Session,
    *,
    member: Member,
    assessment: Assessment,
    evaluator_id: UUID | None,
    commit: bool = True,
    assessment_source_type: str = "formal_assessment",
) -> list[Task]:
    gym_id = getattr(member, "gym_id", None) or getattr(assessment, "gym_id", None)
    if gym_id is None:
        return []

    owner_id = _resolve_post_assessment_owner(db, member=member, evaluator_id=evaluator_id)
    created_or_existing: list[Task] = []
    kept_task_ids: set[UUID] = set()

    for spec in _post_assessment_task_specs(member, assessment, assessment_source_type=assessment_source_type):
        existing = _find_existing_post_assessment_task_for_cycle(db, member=member, spec=spec, assessment=assessment)
        if existing:
            _merge_post_assessment_task_source(existing, spec)
            db.add(existing)
            kept_task_ids.add(existing.id)
            created_or_existing.append(existing)
            continue

        task = Task(
            gym_id=gym_id,
            member_id=member.id,
            assigned_to_user_id=owner_id,
            title=spec["title"],
            description=spec["description"],
            priority=spec["priority"],
            status=TaskStatus.TODO,
            kanban_column=TaskStatus.TODO.value,
            due_date=spec["due_date"],
            suggested_message=spec["suggested_message"],
            extra_data=spec["extra_data"],
        )
        db.add(task)
        created_or_existing.append(task)

    _supersede_open_post_assessment_tasks(
        db,
        member=member,
        assessment=assessment,
        evaluator_id=evaluator_id,
        keep_task_ids=kept_task_ids,
    )
    invalidate_dashboard_cache("tasks")
    if commit:
        db.commit()
    else:
        db.flush()
    return created_or_existing


def _body_composition_as_assessment_source(evaluation) -> SimpleNamespace:
    base_date = getattr(evaluation, "measured_at", None)
    if isinstance(base_date, datetime):
        assessment_date = base_date if base_date.tzinfo else base_date.replace(tzinfo=timezone.utc)
    else:
        evaluation_date = getattr(evaluation, "evaluation_date", None)
        if isinstance(evaluation_date, date):
            assessment_date = datetime.combine(evaluation_date, time(hour=12), tzinfo=timezone.utc)
        else:
            assessment_date = datetime.now(tz=timezone.utc)
    next_due = getattr(evaluation, "next_assessment_due", None)
    if next_due is None:
        next_due = (assessment_date + timedelta(days=_DEFAULT_ASSESSMENT_DUE_DAYS)).date()
    return SimpleNamespace(
        id=getattr(evaluation, "id"),
        gym_id=getattr(evaluation, "gym_id", None),
        assessment_number=None,
        assessment_date=assessment_date,
        next_assessment_due=next_due,
    )


def ensure_body_composition_technical_ladder_tasks(
    db: Session,
    *,
    member: Member,
    evaluation,
    reviewer_user_id: UUID | None,
    commit: bool = True,
) -> list[Task]:
    if getattr(member, "gym_id", None) is None:
        return []
    return _ensure_post_assessment_ladder_tasks(
        db,
        member=member,
        assessment=_body_composition_as_assessment_source(evaluation),
        evaluator_id=reviewer_user_id,
        commit=commit,
        assessment_source_type="body_composition",
    )


def _ensure_assessment_feedback_followup_task(
    db: Session,
    *,
    member: Member,
    assessment: Assessment,
    evaluator_id: UUID | None,
    commit: bool = True,
) -> Task | None:
    existing = db.scalar(
        select(Task).where(
            Task.member_id == member.id,
            Task.deleted_at.is_(None),
            Task.extra_data["source"].astext == _ASSESSMENT_FEEDBACK_TASK_SOURCE,
            Task.extra_data["assessment_id"].astext == str(assessment.id),
        )
    )
    if existing:
        return existing

    gym_id = getattr(member, "gym_id", None) or getattr(assessment, "gym_id", None)
    if gym_id is None:
        return None

    member_name = getattr(member, "full_name", "Aluno")
    member_first_name = member_name.split()[0] if member_name else "Aluno"
    task = Task(
        gym_id=gym_id,
        member_id=member.id,
        assigned_to_user_id=evaluator_id,
        title=f"Follow-up D+14 da avaliacao - {member_name}",
        description="Verificar com o aluno o feedback do treino, aderencia inicial e necessidade de ajuste apos 14 dias da avaliacao.",
        priority=TaskPriority.MEDIUM,
        status=TaskStatus.TODO,
        kanban_column=TaskStatus.TODO.value,
        due_date=assessment.assessment_date + timedelta(days=_ASSESSMENT_FEEDBACK_TASK_DAY_OFFSET),
        suggested_message=(
            f"Oi, {member_first_name}! Ja se passaram 14 dias da sua avaliacao. "
            "Quero entender como voce esta se sentindo com o treino e se precisamos ajustar alguma coisa."
        ),
        extra_data={
            "source": _ASSESSMENT_FEEDBACK_TASK_SOURCE,
            "domain": "trainer",
            "assessment_id": str(assessment.id),
            "assessment_number": assessment.assessment_number,
            "day_offset": _ASSESSMENT_FEEDBACK_TASK_DAY_OFFSET,
            "owner_role": "coach",
        },
    )
    db.add(task)
    invalidate_dashboard_cache("tasks")
    if commit:
        db.commit()
    else:
        db.flush()
    return task


def update_assessment_queue_resolution(
    db: Session,
    member_id: UUID,
    *,
    resolution_status: str,
    note: str | None = None,
    resolved_by_user_id: UUID | None = None,
    gym_id: UUID | None = None,
    commit: bool = True,
) -> Member:
    member = get_member_or_404(db, member_id, gym_id=gym_id)
    extra_data = dict(member.extra_data or {})

    if resolution_status == "active":
        changed = _clear_assessment_queue_resolution(member, extra_data=extra_data)
    else:
        changed = _apply_assessment_queue_resolution(
            member,
            resolution_status=resolution_status,
            note=note,
            resolved_by_user_id=resolved_by_user_id,
            extra_data=extra_data,
        )

    if changed:
        db.add(member)
    invalidate_dashboard_cache("members", gym_id=member.gym_id)
    if commit:
        db.commit()
        db.refresh(member)
    return member


def list_assessments(db: Session, member_id: UUID) -> list[Assessment]:
    get_member_or_404(db, member_id)
    return list(
        db.scalars(
            select(Assessment)
            .where(Assessment.member_id == member_id, Assessment.deleted_at.is_(None))
            .order_by(desc(Assessment.assessment_date))
        ).all()
    )


def get_assessment(db: Session, assessment_id: UUID) -> Assessment:
    assessment = db.scalar(select(Assessment).where(Assessment.id == assessment_id, Assessment.deleted_at.is_(None)))
    if not assessment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Avaliacao nao encontrada")
    return assessment


def get_member_profile_360(db: Session, member_id: UUID) -> dict:
    member = get_member_or_404(db, member_id)

    latest_assessment = _safe(lambda: db.scalar(
        select(Assessment)
        .where(Assessment.member_id == member_id, Assessment.deleted_at.is_(None))
        .order_by(desc(Assessment.assessment_date))
        .limit(1)
    ))
    constraints = _safe(lambda: db.scalar(
        select(MemberConstraints)
        .where(MemberConstraints.member_id == member_id, MemberConstraints.deleted_at.is_(None))
        .order_by(desc(MemberConstraints.created_at))
        .limit(1)
    ))
    goals = _safe(lambda: list(
        db.scalars(
            select(MemberGoal)
            .where(MemberGoal.member_id == member_id, MemberGoal.deleted_at.is_(None))
            .order_by(MemberGoal.achieved.asc(), MemberGoal.target_date.asc().nullslast(), MemberGoal.created_at.desc())
        ).all()
    ), default=[])
    active_training_plan = _safe(lambda: db.scalar(
        select(TrainingPlan)
        .where(
            TrainingPlan.member_id == member_id,
            TrainingPlan.deleted_at.is_(None),
            TrainingPlan.is_active.is_(True),
        )
        .order_by(desc(TrainingPlan.start_date))
        .limit(1)
    ))

    return {
        "member": member,
        "latest_assessment": latest_assessment,
        "constraints": constraints,
        "goals": goals if goals is not None else [],
        "active_training_plan": active_training_plan,
        "insight_summary": latest_assessment.ai_analysis if latest_assessment else None,
    }


def get_evolution_data(db: Session, member_id: UUID) -> dict:
    get_member_or_404(db, member_id)
    assessments = list(
        db.scalars(
            select(Assessment)
            .where(Assessment.member_id == member_id, Assessment.deleted_at.is_(None))
            .order_by(Assessment.assessment_date.asc())
        ).all()
    )

    labels = [item.assessment_date.date().isoformat() for item in assessments]
    weight = [_decimal_to_float(item.weight_kg) for item in assessments]
    body_fat = [_decimal_to_float(item.body_fat_pct) for item in assessments]
    lean_mass = [_decimal_to_float(item.lean_mass_kg) for item in assessments]
    bmi = [_decimal_to_float(item.bmi) for item in assessments]
    strength = [item.strength_score for item in assessments]
    flexibility = [item.flexibility_score for item in assessments]
    cardio = [item.cardio_score for item in assessments]
    main_lift_load = [_extract_main_lift_load(item) for item in assessments]

    checkin_labels = _last_month_labels(6)
    checkins_per_month = [0 for _ in checkin_labels]
    if checkin_labels:
        first_label = checkin_labels[0]
        first_month_start = datetime.strptime(f"{first_label}-01", "%Y-%m-%d").replace(tzinfo=timezone.utc)
        checkin_dates = db.scalars(
            select(Checkin.checkin_at).where(
                Checkin.member_id == member_id,
                Checkin.checkin_at >= first_month_start,
            )
        ).all()
        bucket_index = {label: index for index, label in enumerate(checkin_labels)}
        for checkin_at in checkin_dates:
            label = checkin_at.strftime("%Y-%m")
            idx = bucket_index.get(label)
            if idx is not None:
                checkins_per_month[idx] += 1

    return {
        "labels": labels,
        "weight": weight,
        "body_fat": body_fat,
        "lean_mass": lean_mass,
        "bmi": bmi,
        "strength": strength,
        "flexibility": flexibility,
        "cardio": cardio,
        "checkins_labels": checkin_labels,
        "checkins_per_month": checkins_per_month,
        "main_lift_load": main_lift_load,
        "main_lift_label": "Carga principal",
        "deltas": {
            "weight": _calculate_delta(weight),
            "body_fat": _calculate_delta(body_fat),
            "lean_mass": _calculate_delta(lean_mass),
            "bmi": _calculate_delta(bmi),
            "strength": _calculate_delta(strength),
            "flexibility": _calculate_delta(flexibility),
            "cardio": _calculate_delta(cardio),
            "main_lift_load": _calculate_delta(main_lift_load),
        },
    }


def _validate_assessment_belongs_to_member(db: Session, member_id: UUID, assessment_id: UUID) -> None:
    assessment = db.scalar(
        select(Assessment).where(
            Assessment.id == assessment_id,
            Assessment.member_id == member_id,
            Assessment.deleted_at.is_(None),
        )
    )
    if not assessment:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Avaliacao informada nao pertence ao membro")


def _normalize_datetime(value: datetime | str | None) -> datetime:
    if value is None:
        return datetime.now(tz=timezone.utc)
    if isinstance(value, str):
        parsed = datetime.fromisoformat(value)
    else:
        parsed = value
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _apply_assessment_queue_resolution(
    member: Member,
    *,
    resolution_status: str,
    note: str | None,
    resolved_by_user_id: UUID | None,
    extra_data: dict | None = None,
) -> bool:
    working_extra = extra_data if extra_data is not None else dict(member.extra_data or {})
    normalized_status = str(resolution_status or "").strip().lower()
    if normalized_status not in {"scheduled", "dismissed"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Status de fila de avaliacao invalido")

    cleaned_note = (note or "").strip() or None
    before_snapshot = dict(working_extra)
    working_extra["assessment_queue_resolution"] = normalized_status
    if cleaned_note:
        working_extra["assessment_queue_resolution_note"] = cleaned_note[:280]
    else:
        working_extra.pop("assessment_queue_resolution_note", None)
    working_extra["assessment_queue_resolution_at"] = datetime.now(tz=timezone.utc).isoformat()
    if resolved_by_user_id:
        working_extra["assessment_queue_resolution_by"] = str(resolved_by_user_id)
    else:
        working_extra.pop("assessment_queue_resolution_by", None)

    if working_extra == before_snapshot:
        return False
    member.extra_data = working_extra
    return True


def _clear_assessment_queue_resolution(member: Member, *, extra_data: dict | None = None) -> bool:
    working_extra = extra_data if extra_data is not None else dict(member.extra_data or {})
    before_snapshot = dict(working_extra)
    for key in _ASSESSMENT_QUEUE_RESOLUTION_KEYS:
        working_extra.pop(key, None)
    if working_extra == before_snapshot:
        return False
    member.extra_data = working_extra
    return True


def _to_decimal(value: float | int | str | Decimal | None) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))


def _decimal_to_float(value: Decimal | None) -> float | None:
    if value is None:
        return None
    return float(value)


def _calculate_bmi(height_cm: Decimal | None, weight_kg: Decimal | None) -> Decimal | None:
    if not height_cm or not weight_kg:
        return None
    height_m = float(height_cm) / 100
    if height_m <= 0:
        return None
    return Decimal(str(round(float(weight_kg) / (height_m**2), 2)))


def _calculate_progress_pct(current_value: Decimal | None, target_value: Decimal | None) -> int:
    if not target_value or target_value <= 0:
        return 0
    if current_value is None:
        return 0
    pct = (float(current_value) / float(target_value)) * 100
    return int(max(0, min(100, round(pct))))


def _calculate_delta(series: list[float | int | None]) -> float | int | None:
    valid_values = [value for value in series if value is not None]
    if len(valid_values) < 2:
        return None
    first = valid_values[0]
    last = valid_values[-1]
    if isinstance(first, int) and isinstance(last, int):
        return last - first
    return round(float(last) - float(first), 2)


def _safe_delta_value(previous: Decimal | None, current: Decimal | None) -> str:
    if previous is None or current is None:
        return "n/a"
    delta = current - previous
    return f"{delta:+.2f}"


def _last_month_labels(months: int) -> list[str]:
    if months <= 0:
        return []
    base = date.today().replace(day=1)
    labels: list[str] = []
    for index in range(months - 1, -1, -1):
        current = _subtract_months(base, index)
        labels.append(current.strftime("%Y-%m"))
    return labels


def _subtract_months(base: date, months_back: int) -> date:
    year = base.year
    month = base.month - months_back
    while month <= 0:
        month += 12
        year -= 1
    return date(year, month, 1)


def _extract_main_lift_load(assessment: Assessment) -> float | None:
    extra = assessment.extra_data if isinstance(assessment.extra_data, dict) else {}
    candidate_keys = (
        "main_lift_load",
        "principal_exercise_load",
        "carga_principal",
        "leg_press_load",
        "supino_load",
    )
    for key in candidate_keys:
        raw = extra.get(key)
        if raw is None:
            continue
        try:
            return float(raw)
        except (TypeError, ValueError):
            continue

    if assessment.strength_score is not None:
        return float(assessment.strength_score)
    return None

