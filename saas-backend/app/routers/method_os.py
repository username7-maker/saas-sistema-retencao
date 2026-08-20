from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_request_context, require_roles
from app.database import get_db
from app.models import RoleEnum, User
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
    MethodWeeklyReportRequest,
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
from app.services.audit_service import log_audit_event
from app.services.method_os_service import (
    confirm_method_import,
    copy_segment_playbook_to_client_config,
    create_event,
    create_human_action,
    create_outcome,
    create_person,
    generate_task_from_event,
    generate_weekly_report,
    get_client_dashboard,
    get_client_profile,
    get_internal_dashboard,
    get_segment_playbook,
    list_current_clients,
    list_events,
    list_people,
    list_segments,
    list_tasks,
    preview_method_import,
    update_client_config,
    update_task_message,
    upsert_current_client,
)


router = APIRouter(prefix="/method-os", tags=["method-os"])

METHOD_OS_ROLES = (RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.SALESPERSON)
METHOD_OS_CONFIG_ROLES = (RoleEnum.OWNER, RoleEnum.MANAGER)


def _audit(request: Request, db: Session, *, action: str, entity: str, user: User, entity_id=None, details=None) -> None:
    context = get_request_context(request)
    log_audit_event(
        db,
        action=action,
        entity=entity,
        user=user,
        entity_id=entity_id,
        details=details or {},
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )


@router.get("/segments", response_model=list[SegmentOut])
def list_segments_endpoint(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(*METHOD_OS_ROLES))],
) -> list[SegmentOut]:
    return list_segments(db)


@router.get("/segments/{segment_key}/playbook", response_model=SegmentPlaybookOut)
def get_segment_playbook_endpoint(
    segment_key: str,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(*METHOD_OS_ROLES))],
) -> SegmentPlaybookOut:
    return get_segment_playbook(db, segment_key)


@router.get("/client", response_model=MethodClientProfileOut)
def get_current_client_profile_endpoint(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(*METHOD_OS_ROLES))],
) -> MethodClientProfileOut:
    return get_client_profile(db, current_user=current_user)


@router.get("/clients", response_model=list[CordexClientOut])
def list_clients_endpoint(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(*METHOD_OS_ROLES))],
) -> list[CordexClientOut]:
    return list_current_clients(db, current_user=current_user)


@router.post("/clients", response_model=CordexClientOut, status_code=status.HTTP_201_CREATED)
def upsert_client_endpoint(
    request: Request,
    payload: CordexClientUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(*METHOD_OS_CONFIG_ROLES))],
) -> CordexClientOut:
    client = upsert_current_client(db, current_user=current_user, payload=payload, commit=False)
    _audit(request, db, action="method_os_client_upserted", entity="cordex_client", user=current_user, entity_id=client.cordex_client_id)
    db.commit()
    return client


@router.patch("/client", response_model=CordexClientOut)
def update_client_endpoint(
    request: Request,
    payload: CordexClientUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(*METHOD_OS_CONFIG_ROLES))],
) -> CordexClientOut:
    client = upsert_current_client(db, current_user=current_user, payload=payload, commit=False)
    _audit(request, db, action="method_os_client_updated", entity="cordex_client", user=current_user, entity_id=client.cordex_client_id)
    db.commit()
    return client


@router.patch("/client/config", response_model=ClientMethodConfigOut)
def update_client_config_endpoint(
    request: Request,
    payload: ClientMethodConfigUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(*METHOD_OS_CONFIG_ROLES))],
) -> ClientMethodConfigOut:
    config = update_client_config(db, current_user=current_user, payload=payload, commit=False)
    _audit(request, db, action="method_os_client_config_updated", entity="method_client_config", user=current_user, entity_id=config.id)
    db.commit()
    return config


@router.post("/segments/{segment_id}/copy-to-client", response_model=ClientMethodConfigOut)
def copy_playbook_to_client_endpoint(
    request: Request,
    segment_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(*METHOD_OS_CONFIG_ROLES))],
) -> ClientMethodConfigOut:
    config = copy_segment_playbook_to_client_config(db, current_user=current_user, segment_id=segment_id, commit=False)
    _audit(
        request,
        db,
        action="method_os_playbook_copied_to_client",
        entity="method_client_config",
        user=current_user,
        entity_id=config.id,
        details={"segment_id": str(segment_id)},
    )
    db.commit()
    return config


@router.get("/people", response_model=list[PersonOut])
def list_people_endpoint(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(*METHOD_OS_ROLES))],
    person_type: str | None = Query(default=None),
    q: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[PersonOut]:
    return list_people(db, current_user=current_user, person_type=person_type, q=q, limit=limit)


@router.post("/people", response_model=PersonOut, status_code=status.HTTP_201_CREATED)
def create_person_endpoint(
    request: Request,
    payload: PersonCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(*METHOD_OS_ROLES))],
) -> PersonOut:
    person = create_person(db, current_user=current_user, payload=payload, commit=False)
    _audit(request, db, action="method_os_person_created", entity="method_person", user=current_user, entity_id=person.id)
    db.commit()
    return person


@router.get("/events", response_model=list[OperationalEventOut])
def list_events_endpoint(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(*METHOD_OS_ROLES))],
    pillar: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[OperationalEventOut]:
    return list_events(db, current_user=current_user, pillar=pillar, limit=limit)


@router.post("/events", response_model=OperationalEventOut, status_code=status.HTTP_201_CREATED)
def create_event_endpoint(
    request: Request,
    payload: OperationalEventCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(*METHOD_OS_ROLES))],
) -> OperationalEventOut:
    event = create_event(db, current_user=current_user, payload=payload, commit=False)
    _audit(request, db, action="method_os_event_created", entity="method_operational_event", user=current_user, entity_id=event.id)
    db.commit()
    return event


@router.post("/events/{event_id}/tasks", response_model=OperationalTaskOut, status_code=status.HTTP_201_CREATED)
def generate_task_from_event_endpoint(
    request: Request,
    event_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(*METHOD_OS_ROLES))],
) -> OperationalTaskOut:
    task = generate_task_from_event(db, current_user=current_user, event_id=event_id, commit=False)
    _audit(
        request,
        db,
        action="method_os_task_generated_from_event",
        entity="method_operational_task",
        user=current_user,
        entity_id=task.id,
        details={"event_id": str(event_id), "pillar": task.pillar},
    )
    db.commit()
    return task


@router.get("/tasks", response_model=list[OperationalTaskOut])
def list_tasks_endpoint(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(*METHOD_OS_ROLES))],
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[OperationalTaskOut]:
    return list_tasks(db, current_user=current_user, status_filter=status_filter, limit=limit)


@router.patch("/tasks/{task_id}/message", response_model=OperationalTaskOut)
def update_task_message_endpoint(
    request: Request,
    task_id: UUID,
    payload: OperationalTaskMessageUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(*METHOD_OS_ROLES))],
) -> OperationalTaskOut:
    task = update_task_message(db, current_user=current_user, task_id=task_id, payload=payload, commit=False)
    _audit(request, db, action="method_os_task_message_updated", entity="method_operational_task", user=current_user, entity_id=task.id)
    db.commit()
    return task


@router.post("/tasks/{task_id}/actions", response_model=HumanActionOut, status_code=status.HTTP_201_CREATED)
def create_human_action_endpoint(
    request: Request,
    task_id: UUID,
    payload: HumanActionCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(*METHOD_OS_ROLES))],
) -> HumanActionOut:
    action = create_human_action(db, current_user=current_user, task_id=task_id, payload=payload, commit=False)
    _audit(
        request,
        db,
        action="method_os_human_action_created",
        entity="method_human_action",
        user=current_user,
        entity_id=action.id,
        details={"task_id": str(task_id), "result": action.result},
    )
    db.commit()
    return action


@router.post("/outcomes", response_model=OutcomeOut, status_code=status.HTTP_201_CREATED)
def create_outcome_endpoint(
    request: Request,
    payload: OutcomeCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(*METHOD_OS_ROLES))],
) -> OutcomeOut:
    outcome = create_outcome(db, current_user=current_user, payload=payload, commit=False)
    _audit(
        request,
        db,
        action="method_os_outcome_created",
        entity="method_outcome",
        user=current_user,
        entity_id=outcome.id,
        details={"outcome_type": outcome.outcome_type},
    )
    db.commit()
    return outcome


@router.get("/dashboard/client", response_model=MethodDashboardOut)
def client_dashboard_endpoint(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(*METHOD_OS_ROLES))],
) -> MethodDashboardOut:
    return get_client_dashboard(db, current_user=current_user)


@router.get("/dashboard/internal", response_model=MethodInternalDashboardOut)
def internal_dashboard_endpoint(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
) -> MethodInternalDashboardOut:
    return get_internal_dashboard(db, current_user=current_user)


@router.post("/reports/weekly", response_model=MethodWeeklyReportOut)
def weekly_report_endpoint(
    request: Request,
    payload: MethodWeeklyReportRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(*METHOD_OS_ROLES))],
) -> MethodWeeklyReportOut:
    report = generate_weekly_report(
        db,
        current_user=current_user,
        period_start=payload.period_start,
        period_end=payload.period_end,
        commit=False,
    )
    _audit(request, db, action="method_os_weekly_report_generated", entity="method_report", user=current_user, entity_id=report.report_id)
    db.commit()
    return report


@router.post("/imports/preview", response_model=MethodImportPreviewOut)
def preview_import_endpoint(
    payload: MethodImportPreviewInput,
    _: Annotated[User, Depends(require_roles(*METHOD_OS_CONFIG_ROLES))],
) -> MethodImportPreviewOut:
    return preview_method_import(payload)


@router.post("/imports/confirm", response_model=MethodImportSummaryOut)
def confirm_import_endpoint(
    request: Request,
    payload: MethodImportPreviewInput,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(*METHOD_OS_CONFIG_ROLES))],
) -> MethodImportSummaryOut:
    summary = confirm_method_import(db, current_user=current_user, payload=payload, commit=False)
    _audit(
        request,
        db,
        action="method_os_import_confirmed",
        entity="method_import_batch",
        user=current_user,
        entity_id=summary.batch_id,
        details={"import_type": summary.import_type, "imported": summary.imported, "skipped": summary.skipped},
    )
    db.commit()
    return summary
