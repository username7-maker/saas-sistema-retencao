"""Fail closed unless the running audit sandbox has every external effect disabled."""

from __future__ import annotations

import json
import os

from sqlalchemy import func, select, text

from app.core.config import settings
from app.database import SessionLocal, include_all_tenants
from app.models import AutomationRule, Gym, GymAutopilotSettings, Lead, Member, RoleEnum, Task, User


EXPECTED_TENANTS = {"TESTE_AUDITORIA_ALPHA", "TESTE_AUDITORIA_BETA"}
EXPECTED_SLUGS = {"teste-auditoria-alpha", "teste-auditoria-beta"}
EXPECTED_ROLES = {role.value for role in RoleEnum}


def main() -> None:
    controls = {
        "environment_is_audit": settings.environment == "audit",
        "reserved_email_gate_enabled": os.getenv("AUDIT_ALLOW_RESERVED_EMAILS", "").lower() == "true",
        "scheduler_disabled": not settings.enable_scheduler and not settings.enable_scheduler_in_api,
        "scheduler_fail_closed": not settings.scheduler_critical_lock_fail_open,
        "email_delivery_disabled": not settings.email_delivery_configured,
        "paid_ai_disabled": not settings.claude_api_key and not settings.openai_api_key and not settings.body_composition_image_ai_enabled,
        "sentry_disabled": not settings.sentry_dsn,
        "whatsapp_disabled": not settings.whatsapp_api_url and not settings.whatsapp_api_token and not settings.whatsapp_webhook_token,
        "whatsapp_agent_disabled": settings.whatsapp_agent_mode.lower() == "off" and not settings.whatsapp_external_auto_reply_enabled,
        "actuar_disabled": not settings.actuar_enabled and not settings.actuar_sync_enabled and settings.actuar_sync_mode == "disabled",
        "public_mutations_disabled": not any(
            (
                settings.public_diagnosis_enabled,
                settings.public_booking_confirm_enabled,
                settings.public_objection_response_enabled,
                settings.public_proposal_enabled,
                settings.public_proposal_email_enabled,
            )
        ),
        "scheduled_dispatch_disabled": not settings.monthly_reports_dispatch_enabled,
        "local_database_only": "@db:5432/cordex_audit" in settings.database_url,
        "internal_redis_only": settings.redis_url == "redis://redis:6379/0",
    }

    db = SessionLocal()
    try:
        gyms = list(db.scalars(select(Gym).order_by(Gym.name)))
        controls["exactly_two_fictitious_tenants"] = (
            len(gyms) == 2
            and {gym.name for gym in gyms} == EXPECTED_TENANTS
            and {gym.slug for gym in gyms} == EXPECTED_SLUGS
        )
        controls["tenant_integrations_disabled"] = all(
            not gym.actuar_enabled
            and not gym.actuar_auto_sync_body_composition
            and not gym.kommo_enabled
            and gym.whatsapp_status == "disconnected"
            and not gym.kommo_operator_confirmed_send_enabled
            and not gym.kommo_auto_close_enabled
            and gym.primary_message_channel == "manual"
            and gym.kommo_fallback_channel == "manual"
            for gym in gyms
        )
        autopilot_settings = list(
            db.scalars(
                include_all_tenants(
                    select(GymAutopilotSettings),
                    reason="auth.audit_controls_autopilot",
                )
            )
        )
        controls["autopilot_disabled"] = len(autopilot_settings) == 2 and all(
            not any(
                (
                    item.autopilot_enabled,
                    item.autopilot_auto_close_enabled,
                    item.autopilot_auto_send_enabled,
                    item.retention_enabled,
                    item.finance_enabled,
                    item.sales_enabled,
                    item.onboarding_enabled,
                    item.assessment_enabled,
                    item.nps_enabled,
                )
            )
            and all(
                not item.extra_data.get(key, {}).get("enabled", True)
                and not item.extra_data.get(key, {}).get("auto_send_enabled", True)
                for key in ("ai_service_agent", "personal_ai", "movement_video_ai", "student_personal_ai")
            )
            for item in autopilot_settings
        )
        controls["external_automation_rules_absent"] = (
            db.scalar(
                include_all_tenants(
                    select(func.count(AutomationRule.id)).where(
                        AutomationRule.is_active.is_(True),
                        AutomationRule.action_type.in_(("send_primary_channel", "send_whatsapp", "send_email", "send_to_kommo")),
                    ),
                    reason="auth.audit_controls_automation_rules",
                )
            )
            == 0
        )
        role_sets = {}
        prefix_checks = []
        for gym in gyms:
            users = list(
                db.scalars(
                    include_all_tenants(
                        select(User).where(User.gym_id == gym.id),
                        reason="auth.audit_controls_users",
                    )
                )
            )
            role_sets[gym.name] = sorted(user.role.value for user in users)
            prefix_checks.extend(
                user.email.upper().startswith("TESTE_AUDITORIA_")
                and user.email.lower().endswith("@teste-auditoria.invalid")
                for user in users
            )
            for table in ("members", "leads", "tasks"):
                bad = db.execute(
                    text(
                        f'SELECT count(*) FROM "{table}" WHERE gym_id = :gym_id '
                        "AND NOT (upper(full_name) LIKE 'TESTE_AUDITORIA_%')"
                        if table != "tasks"
                        else f'SELECT count(*) FROM "{table}" WHERE gym_id = :gym_id '
                        "AND NOT (upper(title) LIKE 'TESTE_AUDITORIA_%')"
                    ),
                    {"gym_id": gym.id},
                ).scalar_one()
                prefix_checks.append(int(bad) == 0)
        controls["tenant_scoped_roles_only"] = all(set(roles) == EXPECTED_ROLES and len(roles) == 5 for roles in role_sets.values())
        controls["fixture_prefixes_only"] = all(prefix_checks)
        controls["no_global_admin_role"] = all("admin" not in roles and "superadmin" not in roles for roles in role_sets.values())
        controls["fixture_volume_present"] = all(
            db.scalar(
                include_all_tenants(
                    select(func.count(model.id)),
                    reason=f"auth.audit_controls_{model.__tablename__}",
                )
            )
            >= 40
            for model in (Member, Lead, Task)
        )
    finally:
        db.close()

    failures = sorted(name for name, passed in controls.items() if not passed)
    print(
        json.dumps(
            {
                "classification": "test",
                "target": "sandbox",
                "status": "pass" if not failures else "fail",
                "controls": controls,
                "failed_controls": failures,
            },
            sort_keys=True,
        )
    )
    if failures:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
