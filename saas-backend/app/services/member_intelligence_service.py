from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.database import include_all_tenants
from app.models import (
    Assessment,
    BodyCompositionEvaluation,
    Checkin,
    Lead,
    Member,
    RiskAlert,
    Task,
    TaskStatus,
)
from app.schemas.member_intelligence import (
    ActivityIntelligenceContextOut,
    AssessmentIntelligenceContextOut,
    ConsentIntelligenceContextOut,
    LeadIntelligenceContextOut,
    LeadToMemberIntelligenceContextOut,
    LifecycleIntelligenceContextOut,
    MemberIntelligenceSignalOut,
    MemberIntelligenceSnapshotOut,
    OperationsIntelligenceContextOut,
    RiskIntelligenceContextOut,
)
from app.services.member_service import get_member_or_404


def _tenant_scoped(statement):
    return include_all_tenants(statement, reason="member_intelligence.explicit_gym_scope")


def _enum_value(value: Any) -> str | None:
    if value is None:
        return None
    return str(getattr(value, "value", value))


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_aware_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _date_to_datetime(value: date | None) -> datetime | None:
    if value is None:
        return None
    return datetime.combine(value, time.min, tzinfo=timezone.utc)


def _count(db: Session, model, *conditions) -> int:
    stmt = select(func.count()).select_from(model).where(and_(*conditions))
    return int(db.scalar(_tenant_scoped(stmt)) or 0)


def _latest(db: Session, model, order_by, *conditions):
    stmt = select(model).where(and_(*conditions)).order_by(order_by.desc()).limit(1)
    return db.scalar(_tenant_scoped(stmt))


def _latest_scalar(db: Session, column, order_by, *conditions):
    stmt = select(column).where(and_(*conditions)).order_by(order_by.desc()).limit(1)
    return db.scalar(_tenant_scoped(stmt))


def _first_present(primary: dict[str, Any], secondary: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key in primary:
            return primary[key]
        if key in secondary:
            return secondary[key]
    return None


def _coerce_optional_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "sim", "accepted", "aceito", "ok"}:
            return True
        if normalized in {"false", "0", "no", "nao", "não", "rejected", "recusado"}:
            return False
    return None


def _build_consent_context(member: Member) -> ConsentIntelligenceContextOut:
    extra_data = _as_dict(getattr(member, "extra_data", None))
    consent_data = _as_dict(extra_data.get("consents"))

    lgpd = _coerce_optional_bool(
        _first_present(consent_data, extra_data, ("lgpd", "lgpd_consent", "data_consent", "privacy_consent"))
    )
    communication = _coerce_optional_bool(
        _first_present(
            consent_data,
            extra_data,
            ("communication", "communication_consent", "marketing", "marketing_consent", "whatsapp_consent"),
        )
    )
    image = _coerce_optional_bool(
        _first_present(consent_data, extra_data, ("image", "image_consent", "photo_consent"))
    )
    contract = _coerce_optional_bool(
        _first_present(consent_data, extra_data, ("contract", "contract_consent", "terms", "terms_acceptance"))
    )

    missing = [
        key
        for key, value in {
            "lgpd": lgpd,
            "communication": communication,
            "image": image,
            "contract": contract,
        }.items()
        if value is None
    ]
    return ConsentIntelligenceContextOut(
        lgpd=lgpd,
        communication=communication,
        image=image,
        contract=contract,
        missing=missing,
    )


def _days_without_checkin(last_checkin_at: datetime | None, now: datetime) -> int | None:
    last_checkin_at = _as_aware_datetime(last_checkin_at)
    if last_checkin_at is None:
        return None
    return max(0, (now - last_checkin_at).days)


def _append_flag(flags: list[str], flag: str, condition: bool) -> None:
    if condition and flag not in flags:
        flags.append(flag)


def build_lead_to_member_intelligence_context(
    *,
    member: Member,
    lead: Lead | None,
    checkins_30d: int,
    checkins_90d: int,
    latest_checkin_at: datetime | None,
    assessments_total: int,
    latest_assessment: Assessment | None,
    body_composition_total: int,
    latest_body_composition: BodyCompositionEvaluation | None,
    open_tasks_total: int,
    overdue_tasks_total: int,
    next_task_due_at: datetime | None,
    latest_completed_task_at: datetime | None,
    open_alerts_total: int,
    generated_at: datetime | None = None,
) -> LeadToMemberIntelligenceContextOut:
    now = generated_at or datetime.now(tz=timezone.utc)
    extra_data = _as_dict(getattr(member, "extra_data", None))
    consent = _build_consent_context(member)
    preferred_shift = getattr(member, "preferred_shift", None) or extra_data.get("preferred_shift")
    days_without_checkin = _days_without_checkin(
        latest_checkin_at or getattr(member, "last_checkin_at", None),
        now,
    )

    lead_context = None
    if lead is not None:
        notes = getattr(lead, "notes", None)
        lead_context = LeadIntelligenceContextOut(
            lead_id=getattr(lead, "id", None),
            source=getattr(lead, "source", None),
            stage=_enum_value(getattr(lead, "stage", None)),
            owner_id=getattr(lead, "owner_id", None),
            last_contact_at=getattr(lead, "last_contact_at", None),
            estimated_value=_to_float(getattr(lead, "estimated_value", None)),
            acquisition_cost=_to_float(getattr(lead, "acquisition_cost", None)),
            converted=bool(getattr(lead, "converted_member_id", None)),
            notes_count=len(notes) if isinstance(notes, list) else 0,
        )

    latest_body_at = _as_aware_datetime(getattr(latest_body_composition, "measured_at", None))
    if latest_body_at is None and latest_body_composition is not None:
        latest_body_at = _date_to_datetime(getattr(latest_body_composition, "evaluation_date", None))

    data_quality_flags: list[str] = []
    _append_flag(data_quality_flags, "missing_lead_origin", lead is None or not getattr(lead, "source", None))
    _append_flag(data_quality_flags, "missing_lgpd_consent", consent.lgpd is None)
    _append_flag(data_quality_flags, "missing_communication_consent", consent.communication is None)
    _append_flag(data_quality_flags, "missing_preferred_shift", not preferred_shift)
    _append_flag(data_quality_flags, "missing_recent_checkin", days_without_checkin is None)
    _append_flag(data_quality_flags, "missing_assessment", assessments_total == 0)
    _append_flag(data_quality_flags, "missing_body_composition", body_composition_total == 0)

    signals: list[MemberIntelligenceSignalOut] = []
    if lead_context and lead_context.source:
        signals.append(
            MemberIntelligenceSignalOut(
                key="lead_origin",
                label="Origem comercial preservada",
                value=lead_context.source,
                severity="info",
                source="lead.source",
                observed_at=lead_context.last_contact_at,
            )
        )
    if days_without_checkin is not None:
        signals.append(
            MemberIntelligenceSignalOut(
                key="days_without_checkin",
                label="Dias sem check-in",
                value=days_without_checkin,
                severity="danger" if days_without_checkin >= 30 else "warning" if days_without_checkin >= 14 else "success",
                source="checkins",
                observed_at=latest_checkin_at,
            )
        )
    if open_tasks_total:
        signals.append(
            MemberIntelligenceSignalOut(
                key="open_tasks",
                label="Tasks abertas",
                value=open_tasks_total,
                severity="warning" if overdue_tasks_total else "info",
                source="tasks",
                observed_at=next_task_due_at,
            )
        )
    risk_level = _enum_value(getattr(member, "risk_level", None))
    risk_score = getattr(member, "risk_score", None)
    if risk_level == "red" or (isinstance(risk_score, int) and risk_score >= 70):
        signals.append(
            MemberIntelligenceSignalOut(
                key="risk_attention",
                label="Atenção de retenção",
                value=risk_score,
                severity="danger",
                source="member.risk",
                observed_at=getattr(member, "updated_at", None),
            )
        )
    if body_composition_total:
        signals.append(
            MemberIntelligenceSignalOut(
                key="body_composition_available",
                label="Bioimpedância disponível",
                value=body_composition_total,
                severity="success",
                source="body_composition",
                observed_at=latest_body_at,
            )
        )

    return LeadToMemberIntelligenceContextOut(
        generated_at=now,
        member=MemberIntelligenceSnapshotOut(
            member_id=member.id,
            full_name=member.full_name,
            email=getattr(member, "email", None),
            phone=getattr(member, "phone", None),
            status=_enum_value(getattr(member, "status", None)) or "unknown",
            plan_name=getattr(member, "plan_name", None),
            monthly_fee=_to_float(getattr(member, "monthly_fee", None)),
            join_date=getattr(member, "join_date", None),
            preferred_shift=preferred_shift,
            assigned_user_id=getattr(member, "assigned_user_id", None),
            is_vip=bool(getattr(member, "is_vip", False)),
        ),
        lead=lead_context,
        consent=consent,
        lifecycle=LifecycleIntelligenceContextOut(
            onboarding_status=_enum_value(getattr(member, "onboarding_status", None)),
            onboarding_score=getattr(member, "onboarding_score", None),
            retention_stage=getattr(member, "retention_stage", None),
            churn_type=_enum_value(getattr(member, "churn_type", None)),
            loyalty_months=getattr(member, "loyalty_months", None),
        ),
        activity=ActivityIntelligenceContextOut(
            last_checkin_at=_as_aware_datetime(latest_checkin_at or getattr(member, "last_checkin_at", None)),
            days_without_checkin=days_without_checkin,
            checkins_30d=checkins_30d,
            checkins_90d=checkins_90d,
            preferred_shift=preferred_shift,
        ),
        assessment=AssessmentIntelligenceContextOut(
            assessments_total=assessments_total,
            latest_assessment_at=_as_aware_datetime(getattr(latest_assessment, "assessment_date", None)),
            body_composition_total=body_composition_total,
            latest_body_composition_at=latest_body_at,
            latest_body_fat_percent=_to_float(getattr(latest_body_composition, "body_fat_percent", None)),
            latest_muscle_mass_kg=_to_float(
                getattr(latest_body_composition, "skeletal_muscle_kg", None)
                or getattr(latest_body_composition, "muscle_mass_kg", None)
            ),
            latest_weight_kg=_to_float(getattr(latest_body_composition, "weight_kg", None)),
        ),
        operations=OperationsIntelligenceContextOut(
            open_tasks_total=open_tasks_total,
            overdue_tasks_total=overdue_tasks_total,
            next_task_due_at=_as_aware_datetime(next_task_due_at),
            latest_completed_task_at=_as_aware_datetime(latest_completed_task_at),
        ),
        risk=RiskIntelligenceContextOut(
            risk_level=risk_level,
            risk_score=risk_score,
            open_alerts_total=open_alerts_total,
            nps_last_score=getattr(member, "nps_last_score", None),
        ),
        signals=signals,
        data_quality_flags=data_quality_flags,
    )


def get_member_intelligence_context(
    db: Session,
    member_id: UUID,
    *,
    gym_id: UUID,
) -> LeadToMemberIntelligenceContextOut:
    member = get_member_or_404(db, member_id, gym_id=gym_id)
    now = datetime.now(tz=timezone.utc)
    cutoff_30d = now - timedelta(days=30)
    cutoff_90d = now - timedelta(days=90)
    open_statuses = (TaskStatus.TODO, TaskStatus.DOING)

    lead = db.scalar(
        _tenant_scoped(
            select(Lead)
            .where(
                Lead.gym_id == gym_id,
                Lead.converted_member_id == member.id,
                Lead.deleted_at.is_(None),
            )
            .order_by(Lead.updated_at.desc())
            .limit(1)
        )
    )
    latest_checkin = _latest(
        db,
        Checkin,
        Checkin.checkin_at,
        Checkin.gym_id == gym_id,
        Checkin.member_id == member.id,
    )
    checkins_30d = _count(
        db,
        Checkin,
        Checkin.gym_id == gym_id,
        Checkin.member_id == member.id,
        Checkin.checkin_at >= cutoff_30d,
    )
    checkins_90d = _count(
        db,
        Checkin,
        Checkin.gym_id == gym_id,
        Checkin.member_id == member.id,
        Checkin.checkin_at >= cutoff_90d,
    )
    latest_assessment = _latest(
        db,
        Assessment,
        Assessment.assessment_date,
        Assessment.gym_id == gym_id,
        Assessment.member_id == member.id,
        Assessment.deleted_at.is_(None),
    )
    assessments_total = _count(
        db,
        Assessment,
        Assessment.gym_id == gym_id,
        Assessment.member_id == member.id,
        Assessment.deleted_at.is_(None),
    )
    latest_body_composition = db.scalar(
        _tenant_scoped(
            select(BodyCompositionEvaluation)
            .where(
                BodyCompositionEvaluation.gym_id == gym_id,
                BodyCompositionEvaluation.member_id == member.id,
            )
            .order_by(
                BodyCompositionEvaluation.measured_at.desc().nullslast(),
                BodyCompositionEvaluation.evaluation_date.desc(),
            )
            .limit(1)
        )
    )
    body_composition_total = _count(
        db,
        BodyCompositionEvaluation,
        BodyCompositionEvaluation.gym_id == gym_id,
        BodyCompositionEvaluation.member_id == member.id,
    )
    open_tasks_total = _count(
        db,
        Task,
        Task.gym_id == gym_id,
        Task.member_id == member.id,
        Task.deleted_at.is_(None),
        Task.status.in_(open_statuses),
    )
    overdue_tasks_total = _count(
        db,
        Task,
        Task.gym_id == gym_id,
        Task.member_id == member.id,
        Task.deleted_at.is_(None),
        Task.status.in_(open_statuses),
        Task.due_date.is_not(None),
        Task.due_date < now,
    )
    next_task_due_at = db.scalar(
        _tenant_scoped(
            select(Task.due_date)
            .where(
                Task.gym_id == gym_id,
                Task.member_id == member.id,
                Task.deleted_at.is_(None),
                Task.status.in_(open_statuses),
                Task.due_date.is_not(None),
            )
            .order_by(Task.due_date.asc())
            .limit(1)
        )
    )
    latest_completed_task_at = _latest_scalar(
        db,
        Task.completed_at,
        Task.completed_at,
        Task.gym_id == gym_id,
        Task.member_id == member.id,
        Task.deleted_at.is_(None),
        Task.completed_at.is_not(None),
    )
    open_alerts_total = _count(
        db,
        RiskAlert,
        RiskAlert.gym_id == gym_id,
        RiskAlert.member_id == member.id,
        RiskAlert.resolved.is_(False),
    )

    return build_lead_to_member_intelligence_context(
        member=member,
        lead=lead,
        checkins_30d=checkins_30d,
        checkins_90d=checkins_90d,
        latest_checkin_at=getattr(latest_checkin, "checkin_at", None),
        assessments_total=assessments_total,
        latest_assessment=latest_assessment,
        body_composition_total=body_composition_total,
        latest_body_composition=latest_body_composition,
        open_tasks_total=open_tasks_total,
        overdue_tasks_total=overdue_tasks_total,
        next_task_due_at=next_task_due_at,
        latest_completed_task_at=latest_completed_task_at,
        open_alerts_total=open_alerts_total,
        generated_at=now,
    )
