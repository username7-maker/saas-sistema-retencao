"""Seed the disposable Cordex audit database with fictitious tenant data only."""

from __future__ import annotations

import json
import hashlib
import sys
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import delete, func, select, text

from app.core.security import hash_password
from app.database import SessionLocal, clear_current_gym_id, set_current_gym_id
from app.models import (
    Assessment,
    BodyCompositionEvaluation,
    Checkin,
    CheckinSource,
    Goal,
    Gym,
    GymAutopilotSettings,
    Lead,
    LeadStage,
    Member,
    MemberRiskHistory,
    MemberStatus,
    NPSResponse,
    NPSSentiment,
    NPSTrigger,
    RiskAlert,
    RiskLevel,
    RoleEnum,
    Task,
    TaskPriority,
    TaskStatus,
    User,
)


PREFIX = "TESTE_AUDITORIA_"
DOMAIN = "teste-auditoria.invalid"
TENANTS = (
    ("TESTE_AUDITORIA_ALPHA", "teste-auditoria-alpha"),
    ("TESTE_AUDITORIA_BETA", "teste-auditoria-beta"),
)
PRIMARY_EMAIL = "TESTE_AUDITORIA_GESTOR@teste-auditoria.invalid"
LEGACY_SLUG = "academia-principal"


def _read_secrets() -> tuple[str, str]:
    password = sys.stdin.readline().rstrip("\r\n")
    reset_token = sys.stdin.readline().rstrip("\r\n")
    if not 16 <= len(password) <= 72 or len(reset_token) < 32:
        raise RuntimeError("Audit password and reset token must be supplied on stdin")
    return password, reset_token


def _tenant_row_counts(db, gym_id) -> dict[str, int]:
    tables = db.execute(
        text(
            """
            SELECT DISTINCT table_name
            FROM information_schema.columns
            WHERE table_schema = 'public' AND column_name = 'gym_id'
            ORDER BY table_name
            """
        )
    ).scalars()
    counts: dict[str, int] = {}
    for table_name in tables:
        if not table_name.replace("_", "").isalnum():
            raise RuntimeError("Unexpected tenant table name")
        count = db.execute(
            text(f'SELECT count(*) FROM "{table_name}" WHERE gym_id = :gym_id'),
            {"gym_id": gym_id},
        ).scalar_one()
        counts[table_name] = int(count)
    return counts


def _remove_empty_migration_tenant(db) -> None:
    existing = list(db.scalars(select(Gym).order_by(Gym.slug)))
    unexpected = [gym.slug for gym in existing if gym.slug != LEGACY_SLUG]
    if unexpected:
        raise RuntimeError(f"Fresh audit database contains unexpected tenants: {unexpected}")
    for gym in existing:
        counts = _tenant_row_counts(db, gym.id)
        non_empty = {name: count for name, count in counts.items() if count}
        if non_empty:
            raise RuntimeError("Migration tenant is not empty; refusing destructive cleanup")
        db.execute(delete(Gym).where(Gym.id == gym.id))
    db.commit()


def _make_user(gym_id, tenant_name: str, role: RoleEnum, password_hash: str) -> User:
    role_label = {
        RoleEnum.OWNER: "OWNER",
        RoleEnum.MANAGER: "GESTOR",
        RoleEnum.SALESPERSON: "COMERCIAL",
        RoleEnum.RECEPTIONIST: "RECEPCAO",
        RoleEnum.TRAINER: "PROFESSOR",
    }[role]
    if tenant_name == "TESTE_AUDITORIA_ALPHA" and role == RoleEnum.MANAGER:
        email = PRIMARY_EMAIL
    else:
        email = f"{tenant_name}_{role_label}@{DOMAIN}"
    return User(
        gym_id=gym_id,
        full_name=f"{tenant_name}_{role_label}",
        email=email,
        hashed_password=password_hash,
        role=role,
        is_active=True,
        job_title=f"{PREFIX}{role_label}",
    )


def _seed_tenant(db, tenant_name: str, slug: str, password_hash: str, reset_token_hash: str) -> dict:
    gym = Gym(
        name=tenant_name,
        slug=slug,
        is_active=True,
        whatsapp_status="disconnected",
        actuar_enabled=False,
        actuar_auto_sync_body_composition=False,
        kommo_enabled=False,
        primary_message_channel="manual",
        kommo_operator_confirmed_send_enabled=False,
        kommo_auto_close_enabled=False,
        kommo_fallback_channel="manual",
    )
    db.add(gym)
    db.flush()
    set_current_gym_id(gym.id)

    users = {
        role: _make_user(gym.id, tenant_name, role, password_hash)
        for role in (
            RoleEnum.OWNER,
            RoleEnum.MANAGER,
            RoleEnum.SALESPERSON,
            RoleEnum.RECEPTIONIST,
            RoleEnum.TRAINER,
        )
    }
    db.add_all(users.values())
    db.flush()
    if tenant_name == "TESTE_AUDITORIA_BETA":
        users[RoleEnum.OWNER].password_reset_token_hash = reset_token_hash
        users[RoleEnum.OWNER].password_reset_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    db.add(
        GymAutopilotSettings(
            gym_id=gym.id,
            autopilot_enabled=False,
            autopilot_auto_close_enabled=False,
            autopilot_auto_send_enabled=False,
            retention_enabled=False,
            finance_enabled=False,
            sales_enabled=False,
            onboarding_enabled=False,
            assessment_enabled=False,
            nps_enabled=False,
            extra_data={
                "ai_service_agent": {"enabled": False, "auto_send_enabled": False},
                "personal_ai": {"enabled": False, "auto_send_enabled": False},
                "movement_video_ai": {"enabled": False, "auto_send_enabled": False},
                "student_personal_ai": {"enabled": False, "auto_send_enabled": False},
                "audit_fixture": f"{PREFIX}CONTROLS_DISABLED",
            },
        )
    )

    now = datetime.now(timezone.utc).replace(microsecond=0)
    today = now.date()
    members: list[Member] = []
    for index in range(1, 33):
        status = MemberStatus.CANCELLED if index % 11 == 0 else MemberStatus.PAUSED if index % 7 == 0 else MemberStatus.ACTIVE
        risk_level = (RiskLevel.RED, RiskLevel.YELLOW, RiskLevel.GREEN)[index % 3]
        risk_score = {RiskLevel.RED: 84, RiskLevel.YELLOW: 52, RiskLevel.GREEN: 18}[risk_level]
        member_name = f"{tenant_name}_MEMBRO_{index:03d}"
        if index == 1:
            member_name = f"{tenant_name}_000_XSS_<script>window.__TESTE_AUDITORIA_XSS__=1</script>"
        member = Member(
            gym_id=gym.id,
            assigned_user_id=(users[RoleEnum.TRAINER].id if index % 2 else users[RoleEnum.RECEPTIONIST].id),
            full_name=member_name,
            email=f"{tenant_name}_MEMBRO_{index:03d}@{DOMAIN}",
            status=status,
            plan_name=f"{PREFIX}PLANO_{(index % 3) + 1}",
            monthly_fee=Decimal("149.90") + Decimal(index),
            join_date=today - timedelta(days=index * 9),
            preferred_shift=("morning", "afternoon", "evening")[index % 3],
            nps_last_score=index % 11,
            loyalty_months=index % 24,
            risk_score=risk_score,
            risk_level=risk_level,
            last_checkin_at=now - timedelta(days=index % 20),
            onboarding_score=(index * 7) % 101,
            onboarding_status="at_risk" if risk_level == RiskLevel.RED else "active",
            retention_stage=f"{PREFIX}ESTAGIO_{risk_level.value.upper()}",
            extra_data={"audit_fixture": True, "source": f"{PREFIX}SEED"},
        )
        db.add(member)
        members.append(member)
    db.flush()

    for index, member in enumerate(members[:20], start=1):
        for offset in range(3):
            checkin_at = now - timedelta(days=index + offset, hours=offset)
            db.add(
                Checkin(
                    gym_id=gym.id,
                    member_id=member.id,
                    checkin_at=checkin_at,
                    source=CheckinSource.MANUAL,
                    hour_bucket=checkin_at.hour,
                    weekday=checkin_at.weekday(),
                    extra_data={"audit_fixture": f"{PREFIX}CHECKIN"},
                )
            )

    leads: list[Lead] = []
    stages = list(LeadStage)
    for index in range(1, 31):
        lead = Lead(
            gym_id=gym.id,
            owner_id=users[RoleEnum.SALESPERSON].id,
            full_name=f"{tenant_name}_LEAD_{index:03d}",
            email=f"{tenant_name}_LEAD_{index:03d}@{DOMAIN}",
            source=f"{PREFIX}ORGANICO",
            stage=stages[index % len(stages)],
            estimated_value=Decimal("199.90") + Decimal(index),
            acquisition_cost=Decimal("12.50"),
            last_contact_at=now - timedelta(days=index % 9),
            notes=[{"text": f"{PREFIX}HISTORICO_INERTE_{index:03d}", "type": "audit_fixture"}],
        )
        db.add(lead)
        leads.append(lead)
    db.flush()

    priorities = list(TaskPriority)
    statuses = list(TaskStatus)
    for index in range(1, 31):
        task_status = statuses[index % len(statuses)]
        db.add(
            Task(
                gym_id=gym.id,
                member_id=members[index % len(members)].id if index % 2 else None,
                lead_id=leads[index % len(leads)].id if index % 2 == 0 else None,
                assigned_to_user_id=(users[RoleEnum.RECEPTIONIST].id if index % 3 else users[RoleEnum.SALESPERSON].id),
                title=f"{tenant_name}_TAREFA_{index:03d}",
                description=f"{PREFIX}DESCRICAO_INERTE_{index:03d}",
                priority=priorities[index % len(priorities)],
                status=task_status,
                kanban_column=task_status.value,
                due_date=now + timedelta(days=(index % 10) - 4),
                completed_at=now - timedelta(days=1) if task_status == TaskStatus.DONE else None,
                extra_data={"audit_fixture": True, "source": f"{PREFIX}SEED"},
            )
        )

    for index, member in enumerate(members[:8], start=1):
        for number in (1, 2):
            assessment_date = now - timedelta(days=(3 - number) * 90 + index)
            db.add(
                Assessment(
                    gym_id=gym.id,
                    member_id=member.id,
                    evaluator_id=users[RoleEnum.TRAINER].id,
                    assessment_number=number,
                    assessment_date=assessment_date,
                    next_assessment_due=(assessment_date + timedelta(days=90)).date(),
                    height_cm=Decimal("170.00") + Decimal(index),
                    weight_kg=Decimal("68.00") + Decimal(index + number),
                    bmi=Decimal("23.40") + Decimal(number) / Decimal("10"),
                    body_fat_pct=Decimal("18.00") + Decimal(index),
                    lean_mass_kg=Decimal("52.00") + Decimal(index),
                    strength_score=55 + index + number,
                    flexibility_score=50 + index,
                    cardio_score=58 + index,
                    observations=f"{PREFIX}AVALIACAO_INERTE_{index}_{number}",
                    extra_data={"audit_fixture": True},
                )
            )

    for index, member in enumerate(members[:4], start=1):
        for offset in (0, 60):
            db.add(
                BodyCompositionEvaluation(
                    gym_id=gym.id,
                    member_id=member.id,
                    evaluation_date=today - timedelta(days=offset),
                    measured_at=now - timedelta(days=offset),
                    age_years=25 + index,
                    sex="other",
                    height_cm=170 + index,
                    weight_kg=70 + index + (offset / 100),
                    body_fat_percent=20 + index,
                    body_fat_used_percent=20 + index,
                    body_fat_used_source="bioimpedance",
                    measurement_source="bioimpedance",
                    source="manual",
                    actuar_sync_mode="disabled",
                    actuar_sync_status="saved",
                    sync_required_for_training=False,
                    notes=f"{PREFIX}BIOIMPEDANCIA_INERTE_{index}_{offset}",
                )
            )

    for index, member in enumerate(members[:12], start=1):
        sentiment = NPSSentiment.POSITIVE if index % 3 == 0 else NPSSentiment.NEUTRAL if index % 3 == 1 else NPSSentiment.NEGATIVE
        db.add(
            NPSResponse(
                gym_id=gym.id,
                member_id=member.id,
                score=index % 11,
                comment=f"{PREFIX}NPS_INERTE_{index:03d}",
                sentiment=sentiment,
                sentiment_summary=f"{PREFIX}SEM_IA_EXTERNA",
                trigger=NPSTrigger.MONTHLY,
                response_date=now - timedelta(days=index),
                extra_data={"audit_fixture": True},
            )
        )
        db.add(
            MemberRiskHistory(
                gym_id=gym.id,
                member_id=member.id,
                score=member.risk_score,
                level=member.risk_level.value,
                reasons={"audit_fixture": f"{PREFIX}RISCO_INERTE"},
                recorded_at=now - timedelta(days=index),
            )
        )
        if member.risk_level != RiskLevel.GREEN:
            db.add(
                RiskAlert(
                    gym_id=gym.id,
                    member_id=member.id,
                    score=member.risk_score,
                    level=member.risk_level,
                    reasons={"audit_fixture": f"{PREFIX}ALERTA_INERTE"},
                    action_history=[],
                    resolved=False,
                )
            )

    db.add_all(
        [
            Goal(
                gym_id=gym.id,
                name=f"{tenant_name}_META_MRR",
                metric_type="mrr",
                comparator="gte",
                target_value=Decimal("25000.00"),
                period_start=today.replace(day=1),
                period_end=today + timedelta(days=30),
                notes=f"{PREFIX}META_INERTE",
            ),
            Goal(
                gym_id=gym.id,
                name=f"{tenant_name}_META_CHURN",
                metric_type="churn",
                comparator="lte",
                target_value=Decimal("3.00"),
                period_start=today.replace(day=1),
                period_end=today + timedelta(days=30),
                notes=f"{PREFIX}META_INERTE",
            ),
        ]
    )
    db.commit()

    return {
        "name": tenant_name,
        "slug": slug,
        "gym_id": str(gym.id),
        "users": {role.value: {"id": str(user.id), "email": user.email} for role, user in users.items()},
        "sample_ids": {
            "member": str(members[0].id),
            "lead": str(leads[0].id),
        },
        "counts": {"users": 5, "members": 32, "leads": 30, "tasks": 30, "assessments": 16},
    }


def main() -> None:
    password, reset_token = _read_secrets()
    password_hash = hash_password(password)
    reset_token_hash = hashlib.sha256(reset_token.encode("utf-8")).hexdigest()
    del password, reset_token
    db = SessionLocal()
    try:
        _remove_empty_migration_tenant(db)
        manifests = [_seed_tenant(db, name, slug, password_hash, reset_token_hash) for name, slug in TENANTS]
        clear_current_gym_id()
        try:
            db.execute(text("REFRESH MATERIALIZED VIEW mv_monthly_member_kpis"))
            db.commit()
        except Exception:
            db.rollback()
        gym_names = list(db.scalars(select(Gym.name).order_by(Gym.name)))
        if gym_names != sorted(name for name, _ in TENANTS):
            raise RuntimeError(f"Unexpected final tenant set: {gym_names}")
        print(
            json.dumps(
                {
                    "classification": "test",
                    "target": "sandbox",
                    "primary_account": {
                        "email": PRIMARY_EMAIL,
                        "tenant": "TESTE_AUDITORIA_ALPHA",
                        "gym_slug": "teste-auditoria-alpha",
                        "role": "manager",
                        "password": "generated-at-runtime-not-recorded",
                    },
                    "tenants": manifests,
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
    except Exception:
        db.rollback()
        raise
    finally:
        clear_current_gym_id()
        db.close()


if __name__ == "__main__":
    main()
