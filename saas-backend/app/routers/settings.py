from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.dependencies import get_request_context, require_roles
from app.database import get_db
from app.models import RoleEnum, User
from app.schemas.settings import ActuarConnectionTestResult, ActuarSettingsRead, ActuarSettingsUpdate
from app.services.actuar_settings_service import get_actuar_settings, test_actuar_connection, update_actuar_settings
from app.services.audit_service import log_audit_event


router = APIRouter(prefix="/settings", tags=["settings"])


def _settings_attr(result: ActuarSettingsRead | dict, key: str):
    if isinstance(result, dict):
        return result.get(key)
    return getattr(result, key)


def _test_attr(result: ActuarConnectionTestResult | dict, key: str):
    if isinstance(result, dict):
        return result.get(key)
    return getattr(result, key)


@router.get("/actuar", response_model=ActuarSettingsRead)
def get_actuar_settings_endpoint(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
) -> ActuarSettingsRead:
    return get_actuar_settings(db, gym_id=current_user.gym_id)


@router.put("/actuar", response_model=ActuarSettingsRead)
def update_actuar_settings_endpoint(
    request: Request,
    payload: ActuarSettingsUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
) -> ActuarSettingsRead:
    result = update_actuar_settings(db, gym_id=current_user.gym_id, payload=payload)
    context = get_request_context(request)
    log_audit_event(
        db,
        action="actuar_settings_updated",
        entity="gym_settings",
        user=current_user,
        entity_id=current_user.gym_id,
        details={
            "actuar_enabled": _settings_attr(result, "actuar_enabled"),
            "actuar_auto_sync_body_composition": _settings_attr(result, "actuar_auto_sync_body_composition"),
            "actuar_base_url": _settings_attr(result, "actuar_base_url"),
            "actuar_username": _settings_attr(result, "actuar_username"),
            "actuar_has_password": _settings_attr(result, "actuar_has_password"),
            "effective_sync_mode": _settings_attr(result, "effective_sync_mode"),
        },
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    return result


@router.post("/actuar/test-connection", response_model=ActuarConnectionTestResult)
def test_actuar_connection_endpoint(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
) -> ActuarConnectionTestResult:
    result = test_actuar_connection(db, gym_id=current_user.gym_id)
    context = get_request_context(request)
    log_audit_event(
        db,
        action="actuar_connection_tested",
        entity="gym_settings",
        user=current_user,
        entity_id=current_user.gym_id,
        details={
            "success": _test_attr(result, "success"),
            "provider": _test_attr(result, "provider"),
            "effective_sync_mode": _test_attr(result, "effective_sync_mode"),
            "automatic_sync_ready": _test_attr(result, "automatic_sync_ready"),
            "message": _test_attr(result, "message"),
        },
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    return result
