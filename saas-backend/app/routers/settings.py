from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.dependencies import get_request_context, require_roles
from app.database import get_db
from app.models import RoleEnum, User
from app.schemas.settings import (
    ActuarConnectionTestResult,
    ActuarSettingsRead,
    ActuarSettingsUpdate,
    KommoConnectionTestResult,
    KommoSettingsRead,
    KommoSettingsUpdate,
)
from app.schemas.actuar_bridge import ActuarBridgeDeviceRead, ActuarBridgePairingCodeRead
from app.services.actuar_bridge_service import issue_actuar_bridge_pairing_code, list_actuar_bridge_devices, revoke_actuar_bridge_device
from app.services.actuar_settings_service import get_actuar_settings, test_actuar_connection, update_actuar_settings
from app.services.kommo_settings_service import get_kommo_settings, test_kommo_connection_for_gym, update_kommo_settings
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
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.TRAINER))],
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


@router.get("/actuar/bridge/devices", response_model=list[ActuarBridgeDeviceRead])
def list_actuar_bridge_devices_endpoint(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
) -> list[ActuarBridgeDeviceRead]:
    return list_actuar_bridge_devices(db, gym_id=current_user.gym_id)


@router.post("/actuar/bridge/pairing-code", response_model=ActuarBridgePairingCodeRead)
def issue_actuar_bridge_pairing_code_endpoint(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
) -> ActuarBridgePairingCodeRead:
    result = issue_actuar_bridge_pairing_code(db, gym_id=current_user.gym_id, created_by_user_id=current_user.id)
    context = get_request_context(request)
    log_audit_event(
        db,
        action="actuar_bridge_pairing_issued",
        entity="gym_settings",
        user=current_user,
        entity_id=current_user.gym_id,
        details={"device_id": str(result.device_id), "expires_at": result.expires_at.isoformat()},
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    return result


@router.post("/actuar/bridge/devices/{device_id}/revoke", response_model=ActuarBridgeDeviceRead)
def revoke_actuar_bridge_device_endpoint(
    request: Request,
    device_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
) -> ActuarBridgeDeviceRead:
    result = revoke_actuar_bridge_device(db, gym_id=current_user.gym_id, device_id=device_id)
    context = get_request_context(request)
    log_audit_event(
        db,
        action="actuar_bridge_device_revoked",
        entity="gym_settings",
        user=current_user,
        entity_id=current_user.gym_id,
        details={"device_id": str(device_id), "device_name": result.device_name},
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    return result


@router.get("/kommo", response_model=KommoSettingsRead)
def get_kommo_settings_endpoint(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
) -> KommoSettingsRead:
    return get_kommo_settings(db, gym_id=current_user.gym_id)


@router.put("/kommo", response_model=KommoSettingsRead)
def update_kommo_settings_endpoint(
    request: Request,
    payload: KommoSettingsUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
) -> KommoSettingsRead:
    result = update_kommo_settings(db, gym_id=current_user.gym_id, payload=payload)
    context = get_request_context(request)
    log_audit_event(
        db,
        action="kommo_settings_updated",
        entity="gym_settings",
        user=current_user,
        entity_id=current_user.gym_id,
        details={
            "kommo_enabled": _settings_attr(result, "kommo_enabled"),
            "kommo_base_url": _settings_attr(result, "kommo_base_url"),
            "kommo_has_access_token": _settings_attr(result, "kommo_has_access_token"),
            "kommo_default_pipeline_id": _settings_attr(result, "kommo_default_pipeline_id"),
            "kommo_default_stage_id": _settings_attr(result, "kommo_default_stage_id"),
            "kommo_default_responsible_user_id": _settings_attr(result, "kommo_default_responsible_user_id"),
            "automatic_handoff_ready": _settings_attr(result, "automatic_handoff_ready"),
        },
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    return result


@router.post("/kommo/test-connection", response_model=KommoConnectionTestResult)
def test_kommo_connection_endpoint(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
) -> KommoConnectionTestResult:
    result = test_kommo_connection_for_gym(db, gym_id=current_user.gym_id)
    context = get_request_context(request)
    log_audit_event(
        db,
        action="kommo_connection_tested",
        entity="gym_settings",
        user=current_user,
        entity_id=current_user.gym_id,
        details={
            "success": _test_attr(result, "success"),
            "automatic_handoff_ready": _test_attr(result, "automatic_handoff_ready"),
            "message": _test_attr(result, "message"),
            "base_url": _test_attr(result, "base_url"),
        },
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    return result
