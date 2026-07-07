import csv
from collections.abc import Iterable
from datetime import datetime, timedelta, timezone
from io import StringIO
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Gym, User
from app.models.method_os import (
    METHOD_TASK_STATUSES,
    PILLARS,
    TASK_PRIORITIES,
    ClientMethodConfig,
    HumanAction,
    ImportBatch,
    MethodReport,
    OperationalEvent,
    OperationalTask,
    Outcome,
    Person,
    Segment,
    SegmentPlaybook,
)
from app.schemas.method_os import (
    ClientMethodConfigOut,
    ClientMethodConfigUpdate,
    CordexClientOut,
    CordexClientUpdate,
    HumanActionCreate,
    HumanActionOut,
    MethodClientProfileOut,
    MethodDashboardOut,
    MethodImportPreviewInput,
    MethodImportPreviewOut,
    MethodImportSummaryOut,
    MethodInternalDashboardOut,
    MethodWeeklyReportOut,
    OperationalEventCreate,
    OperationalEventOut,
    OperationalTaskMessageUpdate,
    OperationalTaskOut,
    OutcomeCreate,
    OutcomeOut,
    PersonCreate,
    PersonOut,
    SegmentOut,
    SegmentPlaybookOut,
)
from app.services import method_ai_service


DEFAULT_ACTIVE_PILLARS = {"acquisition": True, "sales": True, "post_sale": True}
OPEN_TASK_STATUSES = ("open", "in_progress")
SALE_OUTCOME_TYPES = ("closed_sale", "sale", "bought", "renewal", "won")
RECOVERY_OUTCOME_TYPES = ("recovered_customer", "returned", "renewed", "reactivated")
RISK_STATUSES = ("risk", "at_risk", "inactive", "churn_risk")
PEOPLE_COLUMN_ALIASES = {
    "name": {"name", "nome", "full_name", "cliente", "lead"},
    "phone": {"phone", "telefone", "celular", "whatsapp"},
    "email": {"email", "e-mail"},
    "person_type": {"tipo", "type", "person_type"},
    "external_id": {"external_id", "id_externo", "codigo", "id"},
    "source_channel": {"origem", "source", "canal"},
    "status": {"status", "situacao"},
}
EVENT_COLUMN_ALIASES = {
    "person_external_id": {"person_external_id", "external_id", "id_externo", "codigo", "id"},
    "person_name": {"person_name", "nome", "cliente", "lead"},
    "pillar": {"pillar", "pilar"},
    "event_type": {"event_type", "tipo_evento", "evento"},
    "event_source": {"event_source", "origem"},
    "occurred_at": {"occurred_at", "data", "quando"},
    "notes": {"notes", "observacao", "obs"},
}


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _not_found(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def _bad_request(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)


def _count(db: Session, statement) -> int:
    value = db.scalar(statement)
    if value is None:
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _current_gym(db: Session, gym_id: UUID) -> Gym:
    gym = db.get(Gym, gym_id)
    if gym is None:
        raise _not_found("Cordex client nao encontrado")
    return gym


def _segment_or_404(db: Session, segment_id: UUID) -> Segment:
    segment = db.get(Segment, segment_id)
    if segment is None:
        raise _not_found("Segmento nao encontrado")
    return segment


def _segment_by_slug(db: Session, slug: str) -> Segment | None:
    return db.scalar(select(Segment).where(Segment.slug == slug))


def _person_or_404(db: Session, *, gym_id: UUID, person_id: UUID) -> Person:
    person = db.scalar(select(Person).where(Person.id == person_id, Person.gym_id == gym_id))
    if person is None:
        raise _not_found("Pessoa nao encontrada")
    return person


def _event_or_404(db: Session, *, gym_id: UUID, event_id: UUID) -> OperationalEvent:
    event = db.scalar(select(OperationalEvent).where(OperationalEvent.id == event_id, OperationalEvent.gym_id == gym_id))
    if event is None:
        raise _not_found("Evento operacional nao encontrado")
    return event


def _task_or_404(db: Session, *, gym_id: UUID, task_id: UUID) -> OperationalTask:
    task = db.scalar(select(OperationalTask).where(OperationalTask.id == task_id, OperationalTask.gym_id == gym_id))
    if task is None:
        raise _not_found("Tarefa operacional nao encontrada")
    return task


def _action_or_404(db: Session, *, gym_id: UUID, action_id: UUID) -> HumanAction:
    action = db.scalar(select(HumanAction).where(HumanAction.id == action_id, HumanAction.gym_id == gym_id))
    if action is None:
        raise _not_found("Acao humana nao encontrada")
    return action


def _client_out(gym: Gym, config: ClientMethodConfig | None = None) -> CordexClientOut:
    segment_id = getattr(gym, "segment_id", None) or getattr(config, "segment_id", None)
    status_value = getattr(gym, "cordex_status", None) or ("active" if getattr(gym, "is_active", True) else "paused")
    return CordexClientOut(
        cordex_client_id=gym.id,
        name=gym.name,
        slug=gym.slug,
        is_active=bool(gym.is_active),
        segment_id=segment_id,
        status=status_value,
        city=getattr(gym, "city", None),
        state=getattr(gym, "state", None),
        main_contact_name=getattr(gym, "main_contact_name", None),
        main_contact_phone=getattr(gym, "main_contact_phone", None),
        main_contact_email=getattr(gym, "main_contact_email", None),
        created_at=getattr(gym, "created_at", None),
        updated_at=getattr(gym, "updated_at", None),
    )


def _config_out(config: ClientMethodConfig) -> ClientMethodConfigOut:
    return ClientMethodConfigOut(
        id=config.id,
        cordex_client_id=config.gym_id,
        segment_id=config.segment_id,
        active_pillars=dict(config.active_pillars_json or DEFAULT_ACTIVE_PILLARS),
        entry_pillar=config.entry_pillar,
        toolkit=dict(config.toolkit_json or {}),
        baseline=dict(config.baseline_json or {}),
        success_criteria=dict(config.success_criteria_json or {}),
        cadence=dict(config.cadence_json or {}),
        created_at=getattr(config, "created_at", None),
        updated_at=getattr(config, "updated_at", None),
    )


def _segment_out(segment: Segment | None) -> SegmentOut | None:
    if segment is None:
        return None
    return SegmentOut.model_validate(segment)


def _playbook_out(playbook: SegmentPlaybook | None, segment: Segment | None = None) -> SegmentPlaybookOut | None:
    if playbook is None:
        return None
    return SegmentPlaybookOut(
        id=playbook.id,
        segment_id=playbook.segment_id,
        channels=list(playbook.channels_json or []),
        qualification_questions=list(playbook.qualification_questions_json or []),
        risk_opportunity_signals=list(playbook.risk_opportunity_signals_json or []),
        message_templates=dict(playbook.message_templates_json or {}),
        success_metrics=list(playbook.success_metrics_json or []),
        segment=_segment_out(segment or getattr(playbook, "segment", None)),
    )


def _person_out(person: Person) -> PersonOut:
    return PersonOut(
        id=person.id,
        cordex_client_id=person.gym_id,
        external_id=person.external_id,
        name=person.name,
        phone=person.phone,
        email=person.email,
        person_type=person.person_type,
        status=person.status,
        source_channel=person.source_channel,
        metadata=dict(person.metadata_json or {}),
        created_at=getattr(person, "created_at", None),
        updated_at=getattr(person, "updated_at", None),
    )


def _event_out(event: OperationalEvent, person: Person | None = None) -> OperationalEventOut:
    resolved_person = person or getattr(event, "person", None)
    return OperationalEventOut(
        id=event.id,
        cordex_client_id=event.gym_id,
        person_id=event.person_id,
        person_name=getattr(resolved_person, "name", None),
        pillar=event.pillar,
        event_type=event.event_type,
        event_source=event.event_source,
        event_payload=dict(event.event_payload_json or {}),
        occurred_at=event.occurred_at,
        created_at=event.created_at,
    )


def _task_out(task: OperationalTask, person: Person | None = None) -> OperationalTaskOut:
    resolved_person = person or getattr(task, "person", None)
    return OperationalTaskOut(
        id=task.id,
        cordex_client_id=task.gym_id,
        person_id=task.person_id,
        person_name=getattr(resolved_person, "name", None),
        person_phone=getattr(resolved_person, "phone", None),
        event_id=task.event_id,
        pillar=task.pillar,
        task_type=task.task_type,
        title=task.title,
        description=task.description,
        assigned_role=task.assigned_role,
        assigned_to=task.assigned_to,
        priority=task.priority,
        status=task.status,
        due_date=task.due_date,
        suggested_message=task.suggested_message,
        wa_me_link=task.wa_me_link,
        dismissal_reason=task.dismissal_reason,
        completed_at=task.completed_at,
        dismissed_at=task.dismissed_at,
        requires_human_approval=task.requires_human_approval,
        ai_metadata=dict(task.ai_metadata_json or {}),
        metadata=dict(task.metadata_json or {}),
        created_at=getattr(task, "created_at", None),
        updated_at=getattr(task, "updated_at", None),
    )


def _action_out(action: HumanAction) -> HumanActionOut:
    return HumanActionOut(
        id=action.id,
        cordex_client_id=action.gym_id,
        person_id=action.person_id,
        task_id=action.task_id,
        action_type=action.action_type,
        action_summary=action.action_summary,
        result=action.result,
        notes=action.notes,
        created_by=action.created_by,
        created_at=action.created_at,
    )


def _outcome_out(outcome: Outcome) -> OutcomeOut:
    return OutcomeOut(
        id=outcome.id,
        cordex_client_id=outcome.gym_id,
        person_id=outcome.person_id,
        task_id=outcome.task_id,
        action_id=outcome.action_id,
        outcome_type=outcome.outcome_type,
        value_numeric=outcome.value_numeric,
        value_text=outcome.value_text,
        measured_at=outcome.measured_at,
        created_at=outcome.created_at,
    )


def list_segments(db: Session) -> list[SegmentOut]:
    return [SegmentOut.model_validate(segment) for segment in db.scalars(select(Segment).order_by(Segment.name)).all()]


def get_segment_playbook(db: Session, segment_key: UUID | str) -> SegmentPlaybookOut:
    segment: Segment | None
    if isinstance(segment_key, UUID):
        segment = db.get(Segment, segment_key)
    else:
        try:
            segment = db.get(Segment, UUID(str(segment_key)))
        except ValueError:
            segment = db.scalar(select(Segment).where(Segment.slug == str(segment_key)))
    if segment is None:
        raise _not_found("Segmento nao encontrado")
    playbook = db.scalar(select(SegmentPlaybook).where(SegmentPlaybook.segment_id == segment.id))
    if playbook is None:
        raise _not_found("Playbook do segmento nao encontrado")
    return _playbook_out(playbook, segment)  # type: ignore[return-value]


def _ensure_client_config(db: Session, gym: Gym) -> ClientMethodConfig:
    config = db.scalar(select(ClientMethodConfig).where(ClientMethodConfig.gym_id == gym.id))
    if config is not None:
        return config

    segment_id = getattr(gym, "segment_id", None)
    segment = db.get(Segment, segment_id) if segment_id else None
    if segment is None:
        segment = _segment_by_slug(db, "academia")
    config = ClientMethodConfig(
        gym_id=gym.id,
        segment_id=getattr(segment, "id", None),
        active_pillars_json=dict(DEFAULT_ACTIVE_PILLARS),
        entry_pillar=getattr(segment, "default_entry_pillar", "post_sale"),
        toolkit_json={},
        baseline_json={},
        success_criteria_json={},
        cadence_json={"weekly_report": True},
    )
    if getattr(gym, "segment_id", None) is None and segment is not None:
        gym.segment_id = segment.id
    db.add(config)
    db.flush()
    return config


def get_client_profile(db: Session, *, current_user: User) -> MethodClientProfileOut:
    gym = _current_gym(db, current_user.gym_id)
    config = _ensure_client_config(db, gym)
    segment = db.get(Segment, config.segment_id) if config.segment_id else None
    playbook = db.scalar(select(SegmentPlaybook).where(SegmentPlaybook.segment_id == segment.id)) if segment else None
    return MethodClientProfileOut(
        client=_client_out(gym, config),
        config=_config_out(config),
        segment=_segment_out(segment),
        playbook=_playbook_out(playbook, segment),
    )


def list_current_clients(db: Session, *, current_user: User) -> list[CordexClientOut]:
    gym = _current_gym(db, current_user.gym_id)
    config = _ensure_client_config(db, gym)
    return [_client_out(gym, config)]


def upsert_current_client(db: Session, *, current_user: User, payload: CordexClientUpdate, commit: bool = True) -> CordexClientOut:
    gym = _current_gym(db, current_user.gym_id)
    config = _ensure_client_config(db, gym)
    data = payload.model_dump(exclude_unset=True)
    if "segment_id" in data and data["segment_id"] is not None:
        _segment_or_404(db, data["segment_id"])
        gym.segment_id = data["segment_id"]
        config.segment_id = data["segment_id"]
    if "name" in data and data["name"] is not None:
        gym.name = data["name"]
    if "status" in data and data["status"] is not None:
        gym.cordex_status = data["status"]
        gym.is_active = data["status"] not in {"paused", "churned"}
    for field in ("city", "state", "main_contact_name", "main_contact_phone", "main_contact_email"):
        if field in data:
            setattr(gym, field, data[field])
    db.flush()
    if commit:
        db.commit()
    return _client_out(gym, config)


def update_client_config(db: Session, *, current_user: User, payload: ClientMethodConfigUpdate, commit: bool = True) -> ClientMethodConfigOut:
    gym = _current_gym(db, current_user.gym_id)
    config = _ensure_client_config(db, gym)
    data = payload.model_dump(exclude_unset=True)

    if data.get("segment_id") is not None:
        segment = _segment_or_404(db, data["segment_id"])
        config.segment_id = segment.id
        gym.segment_id = segment.id
        if payload.entry_pillar is None:
            config.entry_pillar = segment.default_entry_pillar
    if data.get("active_pillars") is not None:
        active_pillars = {pillar: bool(data["active_pillars"].get(pillar, False)) for pillar in PILLARS}
        if not any(active_pillars.values()):
            raise _bad_request("Ao menos um pilar deve ficar ativo")
        config.active_pillars_json = active_pillars
    if data.get("entry_pillar") is not None:
        config.entry_pillar = data["entry_pillar"]
    if data.get("toolkit") is not None:
        config.toolkit_json = data["toolkit"]
    if data.get("baseline") is not None:
        config.baseline_json = data["baseline"]
    if data.get("success_criteria") is not None:
        config.success_criteria_json = data["success_criteria"]
    if data.get("cadence") is not None:
        config.cadence_json = data["cadence"]
    db.flush()
    if commit:
        db.commit()
    return _config_out(config)


def copy_segment_playbook_to_client_config(db: Session, *, current_user: User, segment_id: UUID, commit: bool = True) -> ClientMethodConfigOut:
    segment = _segment_or_404(db, segment_id)
    playbook = db.scalar(select(SegmentPlaybook).where(SegmentPlaybook.segment_id == segment.id))
    if playbook is None:
        raise _not_found("Playbook do segmento nao encontrado")
    gym = _current_gym(db, current_user.gym_id)
    config = _ensure_client_config(db, gym)
    config.segment_id = segment.id
    config.entry_pillar = segment.default_entry_pillar
    config.toolkit_json = {
        "channels": list(playbook.channels_json or []),
        "qualification_questions": list(playbook.qualification_questions_json or []),
        "risk_opportunity_signals": list(playbook.risk_opportunity_signals_json or []),
        "message_templates": dict(playbook.message_templates_json or {}),
    }
    config.success_criteria_json = {"metrics": list(playbook.success_metrics_json or [])}
    gym.segment_id = segment.id
    db.flush()
    if commit:
        db.commit()
    return _config_out(config)


def create_person(db: Session, *, current_user: User, payload: PersonCreate, commit: bool = True) -> PersonOut:
    person = Person(
        gym_id=current_user.gym_id,
        external_id=payload.external_id,
        name=payload.name,
        phone=payload.phone,
        email=payload.email,
        person_type=payload.person_type,
        status=payload.status,
        source_channel=payload.source_channel,
        metadata_json=dict(payload.metadata),
    )
    db.add(person)
    db.flush()
    if commit:
        db.commit()
    return _person_out(person)


def list_people(db: Session, *, current_user: User, person_type: str | None = None, q: str | None = None, limit: int = 50) -> list[PersonOut]:
    statement = select(Person).where(Person.gym_id == current_user.gym_id).order_by(Person.created_at.desc()).limit(limit)
    if person_type:
        statement = statement.where(Person.person_type == person_type)
    if q:
        like = f"%{q.strip()}%"
        statement = statement.where(Person.name.ilike(like))
    return [_person_out(person) for person in db.scalars(statement).all()]


def create_event(db: Session, *, current_user: User, payload: OperationalEventCreate, commit: bool = True) -> OperationalEventOut:
    person = _person_or_404(db, gym_id=current_user.gym_id, person_id=payload.person_id) if payload.person_id else None
    now = _now()
    event = OperationalEvent(
        gym_id=current_user.gym_id,
        person_id=getattr(person, "id", None),
        pillar=payload.pillar,
        event_type=payload.event_type,
        event_source=payload.event_source,
        event_payload_json=dict(payload.event_payload),
        occurred_at=payload.occurred_at or now,
        created_at=now,
    )
    db.add(event)
    db.flush()
    if commit:
        db.commit()
    return _event_out(event, person)


def list_events(db: Session, *, current_user: User, limit: int = 50, pillar: str | None = None) -> list[OperationalEventOut]:
    statement = select(OperationalEvent).where(OperationalEvent.gym_id == current_user.gym_id).order_by(OperationalEvent.occurred_at.desc()).limit(limit)
    if pillar:
        statement = statement.where(OperationalEvent.pillar == pillar)
    return [_event_out(event) for event in db.scalars(statement).all()]


def _task_blueprint(event: OperationalEvent, priority: str) -> dict[str, str]:
    event_type = event.event_type
    if event.pillar == "acquisition":
        return {
            "task_type": "first_response" if event_type == "new_contact" else "qualification",
            "title": "Responder contato e qualificar necessidade",
            "description": "Validar origem, necessidade, disponibilidade e proximo passo.",
            "assigned_role": "recepcao",
        }
    if event.pillar == "sales":
        return {
            "task_type": "follow_up" if event_type != "proposal_sent" else "proposal_follow_up",
            "title": "Fazer follow-up comercial",
            "description": "Retomar conversa, remover duvidas e definir uma decisao clara.",
            "assigned_role": "comercial",
        }
    task_type = "risk_intervention" if priority in {"high", "critical"} else "post_sale_check"
    return {
        "task_type": task_type,
        "title": "Executar acao de pos-venda",
        "description": "Checar contexto, orientar proximo passo e registrar resultado humano.",
        "assigned_role": "operacao",
    }


def generate_task_from_event(db: Session, *, current_user: User, event_id: UUID, commit: bool = True) -> OperationalTaskOut:
    event = _event_or_404(db, gym_id=current_user.gym_id, event_id=event_id)
    person = _person_or_404(db, gym_id=current_user.gym_id, person_id=event.person_id) if event.person_id else None
    priority = method_ai_service.suggest_priority(event.event_type, event.pillar, event.event_payload_json)
    if priority not in TASK_PRIORITIES:
        priority = "medium"
    blueprint = _task_blueprint(event, priority)
    context = {
        "person_name": getattr(person, "name", None),
        "pillar": event.pillar,
        "event_type": event.event_type,
        "payload": dict(event.event_payload_json or {}),
    }
    ai_result = (
        method_ai_service.generate_post_sale_message(context)
        if event.pillar == "post_sale"
        else method_ai_service.generate_follow_up_message(context)
    )
    message = str(ai_result.get("message") or "").strip() or None
    due_delta = timedelta(hours=4) if priority in {"high", "critical"} else timedelta(days=1)
    now = _now()
    task = OperationalTask(
        gym_id=current_user.gym_id,
        person_id=getattr(person, "id", None),
        event_id=event.id,
        pillar=event.pillar,
        task_type=blueprint["task_type"],
        title=blueprint["title"],
        description=blueprint["description"],
        assigned_role=blueprint["assigned_role"],
        priority=priority,
        status="open",
        due_date=now + due_delta,
        suggested_message=message,
        wa_me_link=method_ai_service.build_wa_me_link(getattr(person, "phone", None), message),
        requires_human_approval=True,
        ai_metadata_json=dict(ai_result.get("metadata") or {}),
        metadata_json={"source_event_type": event.event_type, "source_event_payload": dict(event.event_payload_json or {})},
    )
    db.add(task)
    db.flush()
    if commit:
        db.commit()
    return _task_out(task, person)


def list_tasks(db: Session, *, current_user: User, status_filter: str | None = None, limit: int = 50) -> list[OperationalTaskOut]:
    statement = select(OperationalTask).where(OperationalTask.gym_id == current_user.gym_id).order_by(OperationalTask.due_date.asc().nullslast(), OperationalTask.created_at.desc()).limit(limit)
    if status_filter:
        statement = statement.where(OperationalTask.status == status_filter)
    return [_task_out(task) for task in db.scalars(statement).all()]


def update_task_message(
    db: Session,
    *,
    current_user: User,
    task_id: UUID,
    payload: OperationalTaskMessageUpdate,
    commit: bool = True,
) -> OperationalTaskOut:
    task = _task_or_404(db, gym_id=current_user.gym_id, task_id=task_id)
    person = _person_or_404(db, gym_id=current_user.gym_id, person_id=task.person_id) if task.person_id else None
    task.suggested_message = payload.suggested_message
    task.wa_me_link = method_ai_service.build_wa_me_link(getattr(person, "phone", None), payload.suggested_message)
    task.requires_human_approval = True
    db.flush()
    if commit:
        db.commit()
    return _task_out(task, person)


def create_human_action(
    db: Session,
    *,
    current_user: User,
    task_id: UUID,
    payload: HumanActionCreate,
    commit: bool = True,
) -> HumanActionOut:
    task = _task_or_404(db, gym_id=current_user.gym_id, task_id=task_id)
    now = _now()
    action = HumanAction(
        gym_id=current_user.gym_id,
        person_id=task.person_id,
        task_id=task.id,
        action_type=payload.action_type,
        action_summary=payload.action_summary,
        result=payload.result,
        notes=payload.notes,
        created_by=getattr(current_user, "full_name", None) or getattr(current_user, "email", None) or str(current_user.id),
        created_at=now,
    )
    db.add(action)

    next_status = payload.mark_task_status
    if next_status is None and payload.result in {"bought", "returned", "renewed", "lost", "dismissed"}:
        next_status = "dismissed" if payload.result in {"lost", "dismissed"} else "done"
    if next_status:
        task.status = next_status
        if next_status == "done":
            task.completed_at = now
        if next_status == "dismissed":
            task.dismissed_at = now
            task.dismissal_reason = payload.dismissal_reason or payload.result
    db.flush()
    if commit:
        db.commit()
    return _action_out(action)


def create_outcome(db: Session, *, current_user: User, payload: OutcomeCreate, commit: bool = True) -> OutcomeOut:
    task = _task_or_404(db, gym_id=current_user.gym_id, task_id=payload.task_id) if payload.task_id else None
    action = _action_or_404(db, gym_id=current_user.gym_id, action_id=payload.action_id) if payload.action_id else None
    person_id = payload.person_id or getattr(task, "person_id", None) or getattr(action, "person_id", None)
    if person_id is not None:
        _person_or_404(db, gym_id=current_user.gym_id, person_id=person_id)
    now = _now()
    outcome = Outcome(
        gym_id=current_user.gym_id,
        person_id=person_id,
        task_id=getattr(task, "id", None),
        action_id=getattr(action, "id", None),
        outcome_type=payload.outcome_type,
        value_numeric=payload.value_numeric,
        value_text=payload.value_text,
        measured_at=payload.measured_at or now,
        created_at=now,
    )
    db.add(outcome)
    db.flush()
    if commit:
        db.commit()
    return _outcome_out(outcome)


def _period_filter(column, start: datetime, end: datetime):
    return column >= start, column <= end


def build_dashboard_metrics(db: Session, *, gym_id: UUID, generated_at: datetime | None = None) -> MethodDashboardOut:
    now = generated_at or _now()
    week_start = now - timedelta(days=7)
    open_tasks = _count(
        db,
        select(func.count()).select_from(OperationalTask).where(OperationalTask.gym_id == gym_id, OperationalTask.status.in_(OPEN_TASK_STATUSES)),
    )
    overdue_tasks = _count(
        db,
        select(func.count())
        .select_from(OperationalTask)
        .where(OperationalTask.gym_id == gym_id, OperationalTask.status.in_(OPEN_TASK_STATUSES), OperationalTask.due_date < now),
    )
    completed_7d = _count(
        db,
        select(func.count())
        .select_from(OperationalTask)
        .where(OperationalTask.gym_id == gym_id, OperationalTask.status == "done", OperationalTask.completed_at >= week_start),
    )
    people_total = _count(db, select(func.count()).select_from(Person).where(Person.gym_id == gym_id))
    leads_total = _count(db, select(func.count()).select_from(Person).where(Person.gym_id == gym_id, Person.person_type.in_(("lead", "prospect"))))
    customers_total = _count(db, select(func.count()).select_from(Person).where(Person.gym_id == gym_id, Person.person_type.in_(("customer", "inactive_customer"))))
    opportunities = _count(
        db,
        select(func.count()).select_from(OperationalTask).where(OperationalTask.gym_id == gym_id, OperationalTask.pillar == "sales", OperationalTask.status.in_(OPEN_TASK_STATUSES)),
    )
    closed_sales = _count(
        db,
        select(func.count()).select_from(Outcome).where(Outcome.gym_id == gym_id, Outcome.outcome_type.in_(SALE_OUTCOME_TYPES)),
    )
    risk_customers = _count(
        db,
        select(func.count())
        .select_from(Person)
        .where(Person.gym_id == gym_id, ((Person.status.in_(RISK_STATUSES)) | (Person.person_type == "inactive_customer"))),
    )
    recovered_customers = _count(
        db,
        select(func.count()).select_from(Outcome).where(Outcome.gym_id == gym_id, Outcome.outcome_type.in_(RECOVERY_OUTCOME_TYPES)),
    )
    by_pillar = {
        pillar: _count(
            db,
            select(func.count()).select_from(OperationalTask).where(OperationalTask.gym_id == gym_id, OperationalTask.pillar == pillar, OperationalTask.status.in_(OPEN_TASK_STATUSES)),
        )
        for pillar in PILLARS
    }
    by_priority = {
        priority: _count(
            db,
            select(func.count()).select_from(OperationalTask).where(OperationalTask.gym_id == gym_id, OperationalTask.priority == priority, OperationalTask.status.in_(OPEN_TASK_STATUSES)),
        )
        for priority in TASK_PRIORITIES
    }

    bottlenecks: list[str] = []
    if overdue_tasks:
        bottlenecks.append(f"{overdue_tasks} tarefas operacionais vencidas")
    if by_priority.get("critical", 0):
        bottlenecks.append(f"{by_priority['critical']} tarefas criticas abertas")
    if risk_customers:
        bottlenecks.append(f"{risk_customers} pessoas em risco ou inativas")
    recommendations: list[str] = []
    if overdue_tasks:
        recommendations.append("Resolver tarefas vencidas antes de criar novos ciclos de contato.")
    if by_pillar.get("sales", 0) > by_pillar.get("acquisition", 0) + by_pillar.get("post_sale", 0):
        recommendations.append("Separar follow-ups comerciais por prioridade e idade da proposta.")
    if not recommendations:
        recommendations.append("Manter rotina diaria de evento, tarefa, acao humana e resultado medido.")

    return MethodDashboardOut(
        cordex_client_id=gym_id,
        generated_at=now,
        open_tasks=open_tasks,
        overdue_tasks=overdue_tasks,
        completed_7d=completed_7d,
        people_total=people_total,
        leads_total=leads_total,
        customers_total=customers_total,
        opportunities=opportunities,
        closed_sales=closed_sales,
        risk_customers=risk_customers,
        recovered_customers=recovered_customers,
        by_pillar=by_pillar,
        by_priority=by_priority,
        bottlenecks=bottlenecks,
        recommendations=recommendations,
    )


def get_client_dashboard(db: Session, *, current_user: User) -> MethodDashboardOut:
    return build_dashboard_metrics(db, gym_id=current_user.gym_id)


def get_internal_dashboard(db: Session, *, current_user: User) -> MethodInternalDashboardOut:
    gym = _current_gym(db, current_user.gym_id)
    config = _ensure_client_config(db, gym)
    summary = build_dashboard_metrics(db, gym_id=current_user.gym_id)
    return MethodInternalDashboardOut(
        generated_at=summary.generated_at,
        clients_total=1,
        current_client=_client_out(gym, config),
        client_summary=summary,
    )


def _weekly_metrics(db: Session, *, gym_id: UUID, period_start: datetime, period_end: datetime) -> dict[str, Any]:
    period_conditions = _period_filter(OperationalTask.created_at, period_start, period_end)
    tasks_created = _count(
        db,
        select(func.count()).select_from(OperationalTask).where(OperationalTask.gym_id == gym_id, *period_conditions),
    )
    tasks_completed = _count(
        db,
        select(func.count())
        .select_from(OperationalTask)
        .where(OperationalTask.gym_id == gym_id, OperationalTask.status == "done", OperationalTask.completed_at >= period_start, OperationalTask.completed_at <= period_end),
    )
    leads = _count(
        db,
        select(func.count()).select_from(Person).where(Person.gym_id == gym_id, Person.person_type.in_(("lead", "prospect")), Person.created_at <= period_end),
    )
    dashboard = build_dashboard_metrics(db, gym_id=gym_id, generated_at=period_end)
    return {
        "tasks_created": tasks_created,
        "tasks_completed": tasks_completed,
        "leads": leads,
        "opportunities": dashboard.opportunities,
        "closed_sales": dashboard.closed_sales,
        "risk_customers": dashboard.risk_customers,
        "recovered_customers": dashboard.recovered_customers,
        "bottlenecks": dashboard.bottlenecks,
        "recommendations": dashboard.recommendations,
        "by_pillar": dashboard.by_pillar,
        "by_priority": dashboard.by_priority,
    }


def generate_weekly_report(
    db: Session,
    *,
    current_user: User,
    period_start: datetime | None = None,
    period_end: datetime | None = None,
    commit: bool = True,
) -> MethodWeeklyReportOut:
    end = period_end or _now()
    start = period_start or (end - timedelta(days=7))
    if start >= end:
        raise _bad_request("period_start deve ser anterior a period_end")
    metrics = _weekly_metrics(db, gym_id=current_user.gym_id, period_start=start, period_end=end)
    generated = method_ai_service.generate_weekly_report(metrics)
    report = MethodReport(
        gym_id=current_user.gym_id,
        report_type="weekly",
        period_start=start,
        period_end=end,
        summary=generated["summary"],
        metrics_json=metrics,
        recommendations_json=list(generated["recommendations"]),
        created_at=_now(),
    )
    db.add(report)
    db.flush()
    if commit:
        db.commit()
    return MethodWeeklyReportOut(
        report_id=report.id,
        cordex_client_id=current_user.gym_id,
        report_type="weekly",
        period_start=start,
        period_end=end,
        summary=generated["summary"],
        markdown=generated["markdown"],
        metrics=metrics,
        bottlenecks=list(generated["bottlenecks"]),
        recommendations=list(generated["recommendations"]),
        requires_human_review=True,
    )


def _parse_csv_rows(csv_content: str) -> list[dict[str, str]]:
    reader = csv.DictReader(StringIO(csv_content))
    if not reader.fieldnames:
        raise _bad_request("CSV sem cabecalho")
    rows: list[dict[str, str]] = []
    for row in reader:
        cleaned = {str(key or "").strip(): str(value or "").strip() for key, value in row.items()}
        if any(cleaned.values()):
            rows.append(cleaned)
    return rows


def _resolve_mapping(columns: Iterable[str], aliases: dict[str, set[str]], explicit: dict[str, str] | None = None) -> dict[str, str]:
    explicit = explicit or {}
    normalized_columns = {column.lower().strip(): column for column in columns}
    mapping: dict[str, str] = {}
    for target, source in explicit.items():
        if source in columns:
            mapping[target] = source
    for target, target_aliases in aliases.items():
        if target in mapping:
            continue
        for alias in target_aliases:
            if alias in normalized_columns:
                mapping[target] = normalized_columns[alias]
                break
    return mapping


def preview_method_import(payload: MethodImportPreviewInput) -> MethodImportPreviewOut:
    rows = _parse_csv_rows(payload.csv_content)
    columns = list(rows[0].keys()) if rows else []
    aliases = PEOPLE_COLUMN_ALIASES if payload.import_type == "people" else EVENT_COLUMN_ALIASES
    mapping = _resolve_mapping(columns, aliases, payload.column_mapping)
    recognized = sorted(set(mapping.values()))
    ignored = set(payload.ignored_columns)
    unrecognized = [column for column in columns if column not in recognized and column not in ignored]
    blocking_issues: list[str] = []
    if payload.import_type == "people" and "name" not in mapping:
        blocking_issues.append("Coluna de nome e obrigatoria para importar pessoas")
    if payload.import_type == "events" and "event_type" not in mapping:
        blocking_issues.append("Coluna event_type/tipo_evento e obrigatoria para importar eventos")
    return MethodImportPreviewOut(
        import_type=payload.import_type,
        total_rows=len(rows),
        valid_rows=0 if blocking_issues else len(rows),
        recognized_columns=recognized,
        unrecognized_columns=unrecognized,
        sample_rows=rows[:5],
        blocking_issues=blocking_issues,
        can_confirm=not blocking_issues,
    )


def _row_value(row: dict[str, str], mapping: dict[str, str], target: str) -> str | None:
    source = mapping.get(target)
    if not source:
        return None
    value = row.get(source)
    return value.strip() if isinstance(value, str) and value.strip() else None


def _coerce_person_type(value: str | None) -> str:
    if value in {"lead", "customer", "inactive_customer", "prospect"}:
        return value
    return "lead"


def confirm_method_import(
    db: Session,
    *,
    current_user: User,
    payload: MethodImportPreviewInput,
    commit: bool = True,
) -> MethodImportSummaryOut:
    preview = preview_method_import(payload)
    if not preview.can_confirm:
        raise _bad_request("; ".join(preview.blocking_issues))
    rows = _parse_csv_rows(payload.csv_content)
    columns = list(rows[0].keys()) if rows else []
    aliases = PEOPLE_COLUMN_ALIASES if payload.import_type == "people" else EVENT_COLUMN_ALIASES
    mapping = _resolve_mapping(columns, aliases, payload.column_mapping)
    imported = 0
    skipped = 0
    errors: list[dict[str, Any]] = []
    now = _now()

    for index, row in enumerate(rows, start=2):
        try:
            if payload.import_type == "people":
                name = _row_value(row, mapping, "name")
                if not name:
                    skipped += 1
                    continue
                db.add(
                    Person(
                        gym_id=current_user.gym_id,
                        external_id=_row_value(row, mapping, "external_id"),
                        name=name,
                        phone=_row_value(row, mapping, "phone"),
                        email=_row_value(row, mapping, "email"),
                        person_type=_coerce_person_type(_row_value(row, mapping, "person_type")),
                        status=_row_value(row, mapping, "status") or "active",
                        source_channel=_row_value(row, mapping, "source_channel"),
                        metadata_json={"import_filename": payload.filename},
                    )
                )
            else:
                event_type = _row_value(row, mapping, "event_type")
                if not event_type:
                    skipped += 1
                    continue
                db.add(
                    OperationalEvent(
                        gym_id=current_user.gym_id,
                        person_id=None,
                        pillar=_row_value(row, mapping, "pillar") if _row_value(row, mapping, "pillar") in PILLARS else "post_sale",
                        event_type=event_type,
                        event_source=_row_value(row, mapping, "event_source") or "import",
                        event_payload_json={"row": row, "notes": _row_value(row, mapping, "notes")},
                        occurred_at=now,
                        created_at=now,
                    )
                )
            imported += 1
        except Exception as exc:  # pragma: no cover - defensive per-row isolation
            errors.append({"row_number": index, "reason": str(exc), "payload": row})

    batch = ImportBatch(
        gym_id=current_user.gym_id,
        import_type=payload.import_type,
        filename=payload.filename,
        status="imported" if not errors else "failed",
        column_mapping_json=mapping,
        summary_json={"imported": imported, "skipped": skipped},
        error_report_json=errors,
        created_at=now,
    )
    db.add(batch)
    db.flush()
    if commit:
        db.commit()
    return MethodImportSummaryOut(import_type=payload.import_type, imported=imported, skipped=skipped, errors=errors, batch_id=batch.id)
