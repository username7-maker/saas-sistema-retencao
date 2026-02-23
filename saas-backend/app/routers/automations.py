from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_request_context, require_roles
from app.database import get_db
from app.models import RoleEnum, User
from app.schemas.automation import AutomationExecutionResult, AutomationRuleCreate, AutomationRuleOut, AutomationRuleUpdate, MessageLogOut, WhatsAppSendRequest
from app.services.audit_service import log_audit_event
from app.services.automation_engine import (
    create_automation_rule,
    delete_automation_rule,
    get_automation_rule,
    list_automation_rules,
    run_automation_rules,
    seed_default_rules,
    update_automation_rule,
)
from app.services.whatsapp_service import render_template, send_whatsapp_sync


router = APIRouter(prefix="/automations", tags=["automations"])


@router.get("/rules", response_model=list[AutomationRuleOut])
def list_rules_endpoint(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
    active_only: bool = Query(False),
    trigger_type: str | None = Query(None),
) -> list[AutomationRuleOut]:
    rules = list_automation_rules(db, active_only=active_only, trigger_type=trigger_type)
    return [AutomationRuleOut.model_validate(r) for r in rules]


@router.post("/rules", response_model=AutomationRuleOut, status_code=status.HTTP_201_CREATED)
def create_rule_endpoint(
    request: Request,
    payload: AutomationRuleCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
) -> AutomationRuleOut:
    rule = create_automation_rule(db, data=payload.model_dump())
    context = get_request_context(request)
    log_audit_event(
        db,
        action="automation_rule_created",
        entity="automation_rule",
        user=current_user,
        entity_id=rule.id,
        details={"trigger_type": rule.trigger_type, "action_type": rule.action_type},
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    db.refresh(rule)
    return AutomationRuleOut.model_validate(rule)


@router.get("/rules/{rule_id}", response_model=AutomationRuleOut)
def get_rule_endpoint(
    rule_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
) -> AutomationRuleOut:
    rule = get_automation_rule(db, rule_id)
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Regra de automacao nao encontrada")
    return AutomationRuleOut.model_validate(rule)


@router.patch("/rules/{rule_id}", response_model=AutomationRuleOut)
def update_rule_endpoint(
    request: Request,
    rule_id: UUID,
    payload: AutomationRuleUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
) -> AutomationRuleOut:
    rule = update_automation_rule(db, rule_id, data=payload.model_dump(exclude_unset=True))
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Regra de automacao nao encontrada")
    context = get_request_context(request)
    log_audit_event(
        db,
        action="automation_rule_updated",
        entity="automation_rule",
        user=current_user,
        entity_id=rule.id,
        details={"updated_fields": list(payload.model_dump(exclude_unset=True).keys())},
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    db.refresh(rule)
    return AutomationRuleOut.model_validate(rule)


@router.delete("/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rule_endpoint(
    request: Request,
    rule_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER))],
) -> None:
    deleted = delete_automation_rule(db, rule_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Regra de automacao nao encontrada")
    context = get_request_context(request)
    log_audit_event(
        db,
        action="automation_rule_deleted",
        entity="automation_rule",
        user=current_user,
        entity_id=rule_id,
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()


@router.post("/execute", response_model=list[dict])
def execute_all_rules_endpoint(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
) -> list[dict]:
    results = run_automation_rules(db)
    context = get_request_context(request)
    log_audit_event(
        db,
        action="automations_executed_manually",
        entity="automation_rule",
        user=current_user,
        details={"total_results": len(results)},
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    return results


@router.post("/seed-defaults", response_model=list[AutomationRuleOut], status_code=status.HTTP_201_CREATED)
def seed_defaults_endpoint(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER))],
) -> list[AutomationRuleOut]:
    rules = seed_default_rules(db)
    db.commit()
    return [AutomationRuleOut.model_validate(r) for r in rules]


@router.post("/whatsapp/send")
def send_whatsapp_endpoint(
    request: Request,
    payload: WhatsAppSendRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST))],
) -> MessageLogOut:
    message = payload.message
    if payload.template_name:
        message = render_template(payload.template_name, {"mensagem": message})

    log = send_whatsapp_sync(
        db,
        phone=payload.phone,
        message=message,
        member_id=payload.member_id,
        template_name=payload.template_name,
    )
    context = get_request_context(request)
    log_audit_event(
        db,
        action="whatsapp_sent_manually",
        entity="message_log",
        user=current_user,
        member_id=payload.member_id,
        entity_id=log.id,
        details={"status": log.status, "channel": "whatsapp"},
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    db.refresh(log)
    return MessageLogOut.model_validate(log)
