from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from typing import Any

from pydantic import TypeAdapter
from sqlalchemy import DateTime, and_, case, func, not_, or_, select
from sqlalchemy.orm import Session

from app.core.cache import dashboard_cache, make_cache_key
from app.database import get_current_gym_id
from app.models import (
    AITriageRecommendation,
    Assessment,
    AuditLog,
    Checkin,
    Lead,
    LeadStage,
    Member,
    MemberStatus,
    NPSResponse,
    RiskAlert,
    RiskLevel,
    Task,
    TaskStatus,
)
from app.models.enums import ChurnType
from app.schemas import (
    BICohortPoint,
    BIFollowUpImpact,
    BIFoundationDashboard,
    ChurnPoint,
    ConversionBySource,
    CommercialDashboard,
    ExecutiveDashboard,
    FinancialDashboard,
    GrowthPoint,
    HeatmapPoint,
    LTVPoint,
    NPSEvolutionPoint,
    OperationalDashboard,
    PaginatedResponse,
    ProjectionPoint,
    RetentionDashboard,
    RetentionPlaybookStep,
    RetentionQueueItem,
    RetentionQueueResponse,
    RevenuePoint,
    WeeklySummary,
)
from app.services.ai_assistant_service import build_retention_assistant
from app.services.analytics_view_service import get_monthly_member_kpis
from app.services.assessment_intelligence_service import get_assessment_forecast
from app.services.crm_service import calculate_cac
from app.services.finance_service import get_finance_foundation_summary, get_monthly_financial_entry_revenue
from app.services.nps_service import nps_evolution
from app.services.preferred_shift_service import preferred_shift_filter_condition
from app.services.risk import _MIN_RELIABLE_BASELINE_AVG_WEEKLY, _determine_level, _inactivity_points
from app.services.retention_intelligence_service import build_retention_playbook, classify_churn_type
from app.services.retention_stage_service import (
    RETENTION_STAGE_ATTENTION,
    RETENTION_STAGE_COLD_BASE,
    RETENTION_STAGE_MANAGER_ESCALATION,
    RETENTION_STAGE_MONITORING,
    RETENTION_STAGE_REACTIVATION,
    RETENTION_STAGE_RECOVERY,
    RETENTION_STAGE_ORDER,
    calculate_retention_stage,
    retention_stage_payload,
)
from app.utils.birthday import birthday_label_matches_today
from app.schemas.member import MemberOut


def _cache_dashboard_payload(cache_key: str, schema: Any, payload: object) -> None:
    adapter = TypeAdapter(schema)
    normalized_payload = adapter.dump_python(adapter.validate_python(payload, from_attributes=True), mode="json")
    dashboard_cache.set(cache_key, normalized_payload)


def get_executive_dashboard(db: Session) -> ExecutiveDashboard:
    cache_key = make_cache_key("dashboard_executive")
    cached = dashboard_cache.get(cache_key)
    if cached is not None:
        return cached

    total_members = db.scalar(select(func.count()).select_from(Member).where(Member.deleted_at.is_(None))) or 0
    active_members = db.scalar(
        select(func.count()).select_from(Member).where(
            Member.deleted_at.is_(None), Member.status == MemberStatus.ACTIVE
        )
    ) or 0

    mrr = db.scalar(
        select(func.coalesce(func.sum(Member.monthly_fee), Decimal("0"))).where(
            Member.deleted_at.is_(None),
            Member.status == MemberStatus.ACTIVE,
        )
    ) or Decimal("0")

    nps_avg = db.scalar(
        select(func.coalesce(func.avg(NPSResponse.score), 0.0)).where(NPSResponse.response_date >= _utcnow() - timedelta(days=90))
    ) or 0.0

    risk_distribution = {
        "green": db.scalar(select(func.count()).select_from(Member).where(Member.risk_level == RiskLevel.GREEN, Member.deleted_at.is_(None))) or 0,
        "yellow": db.scalar(select(func.count()).select_from(Member).where(Member.risk_level == RiskLevel.YELLOW, Member.deleted_at.is_(None))) or 0,
        "red": db.scalar(select(func.count()).select_from(Member).where(Member.risk_level == RiskLevel.RED, Member.deleted_at.is_(None))) or 0,
    }

    churn_series = _churn_series(db, months=1)
    churn_value = churn_series[0].churn_rate if churn_series else 0.0
    payload = ExecutiveDashboard(
        total_members=total_members,
        active_members=active_members,
        mrr=float(mrr),
        churn_rate=churn_value,
        nps_avg=float(nps_avg),
        risk_distribution=risk_distribution,
    )
    _cache_dashboard_payload(cache_key, ExecutiveDashboard, payload)
    return payload


def get_mrr_dashboard(db: Session, months: int = 12) -> list[RevenuePoint]:
    cache_key = make_cache_key("dashboard_mrr", months)
    cached = dashboard_cache.get(cache_key)
    if cached is not None:
        return cached
    payload = _revenue_series(db, months)
    _cache_dashboard_payload(cache_key, list[RevenuePoint], payload)
    return payload


def get_churn_dashboard(db: Session, months: int = 12) -> list[ChurnPoint]:
    cache_key = make_cache_key("dashboard_churn", months)
    cached = dashboard_cache.get(cache_key)
    if cached is not None:
        return cached
    payload = _churn_series(db, months)
    _cache_dashboard_payload(cache_key, list[ChurnPoint], payload)
    return payload


def get_ltv_dashboard(db: Session, months: int = 12) -> list[LTVPoint]:
    cache_key = make_cache_key("dashboard_ltv", months)
    cached = dashboard_cache.get(cache_key)
    if cached is not None:
        return cached

    materialized = _monthly_member_kpis_rows(db, months)
    if materialized:
        points = []
        for row in materialized:
            churn_rate = (row["cancelled"] / max(1, row["active"])) * 100
            churn_ratio = max(churn_rate / 100, 0.0001)
            ltv = (row["mrr"] / max(1, row["active"])) / churn_ratio
            points.append(LTVPoint(month=row["month"], ltv=round(ltv, 2)))
        _cache_dashboard_payload(cache_key, list[LTVPoint], points)
        return points

    churn_series = _churn_series(db, months)
    revenue_series = _revenue_series(db, months)
    points: list[LTVPoint] = []
    for churn, revenue in zip(churn_series, revenue_series):
        churn_rate = max(churn.churn_rate / 100, 0.0001)
        ltv = (revenue.value / max(1, _active_members_by_month(db, churn.month))) / churn_rate
        points.append(LTVPoint(month=churn.month, ltv=round(ltv, 2)))

    _cache_dashboard_payload(cache_key, list[LTVPoint], points)
    return points


def get_growth_mom_dashboard(db: Session, months: int = 12) -> list[GrowthPoint]:
    cache_key = make_cache_key("dashboard_growth", months)
    cached = dashboard_cache.get(cache_key)
    if cached is not None:
        return cached

    values: list[GrowthPoint] = []
    month_labels = _month_labels(months)
    cumulative_members = _members_joined_cumulative_by_month(db, month_labels)
    previous = None
    for label in month_labels:
        current_total = cumulative_members.get(label, 0)
        if previous in (None, 0):
            growth = 0.0
        else:
            growth = ((current_total - previous) / previous) * 100
        values.append(GrowthPoint(month=label, growth_mom=round(growth, 2)))
        previous = current_total

    _cache_dashboard_payload(cache_key, list[GrowthPoint], values)
    return values


def get_operational_dashboard(db: Session, page: int = 1, page_size: int = 20) -> dict:
    cache_key = make_cache_key("dashboard_operational", page, page_size)
    cached = dashboard_cache.get(cache_key)
    if cached is not None:
        return cached

    now = _utcnow()
    realtime_checkins = db.scalar(
        select(func.count()).select_from(Checkin).where(Checkin.checkin_at >= now - timedelta(hours=1))
    ) or 0

    heatmap_rows = db.execute(
        select(Checkin.weekday, Checkin.hour_bucket, func.count(Checkin.id).label("total"))
        .where(Checkin.checkin_at >= now - timedelta(days=60))
        .group_by(Checkin.weekday, Checkin.hour_bucket)
        .order_by(Checkin.weekday, Checkin.hour_bucket)
    ).all()
    heatmap = [
        HeatmapPoint(weekday=int(row.weekday), hour_bucket=int(row.hour_bucket), total_checkins=int(row.total))
        for row in heatmap_rows
    ]

    cutoff = now - timedelta(days=7)
    inactive_filters = (
        Member.deleted_at.is_(None),
        Member.status == MemberStatus.ACTIVE,
        or_(Member.last_checkin_at.is_(None), Member.last_checkin_at < cutoff),
    )
    total_inactive = db.scalar(select(func.count()).select_from(Member).where(*inactive_filters)) or 0
    items = db.scalars(
        select(Member)
        .where(*inactive_filters)
        .order_by(Member.last_checkin_at.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    birthday_today = _get_birthday_today_members(db, now.date())

    payload = {
        "realtime_checkins": realtime_checkins,
        "heatmap": heatmap,
        "inactive_7d_total": total_inactive,
        "inactive_7d_items": [_member_out_snapshot(member) for member in items],
        "birthday_today_total": len(birthday_today),
        "birthday_today_items": [_member_out_snapshot(member) for member in birthday_today],
    }
    _cache_dashboard_payload(cache_key, OperationalDashboard, payload)
    return payload


def _birthday_label_matches_today(member: Member, today: date) -> bool:
    extra_data = member.extra_data or {}
    return birthday_label_matches_today(extra_data.get("birthday_label"), today)


def _get_birthday_today_members(db: Session, today: date) -> list[Member]:
    active_filters = (
        Member.deleted_at.is_(None),
        Member.status == MemberStatus.ACTIVE,
    )

    direct_matches = list(
        db.scalars(
            select(Member)
            .where(
                *active_filters,
                Member.birthdate.is_not(None),
                func.extract("month", Member.birthdate) == today.month,
                func.extract("day", Member.birthdate) == today.day,
            )
            .order_by(Member.full_name.asc())
        ).all()
    )

    label_candidates = list(
        db.scalars(
            select(Member)
            .where(
                *active_filters,
                Member.birthdate.is_(None),
                Member.extra_data["birthday_label"].astext.isnot(None),
            )
            .order_by(Member.full_name.asc())
        ).all()
    )

    combined: dict[str, Member] = {str(member.id): member for member in direct_matches}
    for member in label_candidates:
        if _birthday_label_matches_today(member, today):
            combined[str(member.id)] = member

    return list(combined.values())


def get_commercial_dashboard(db: Session) -> dict:
    cache_key = make_cache_key("dashboard_commercial")
    cached = dashboard_cache.get(cache_key)
    if cached is not None:
        return cached

    pipeline_rows = db.execute(
        select(Lead.stage, func.count(Lead.id).label("total"))
        .where(Lead.deleted_at.is_(None))
        .group_by(Lead.stage)
    ).all()
    pipeline = {row.stage.value: int(row.total) for row in pipeline_rows}

    source_rows = db.execute(
        select(
            Lead.source,
            func.count(Lead.id).label("total"),
            func.sum(case((Lead.stage == LeadStage.WON, 1), else_=0)).label("won"),
        )
        .where(Lead.deleted_at.is_(None))
        .group_by(Lead.source)
    ).all()
    conversion = [
        ConversionBySource(
            source=row.source,
            total=int(row.total),
            won=int(row.won or 0),
            conversion_rate=round((int(row.won or 0) / max(1, int(row.total))) * 100, 2),
        )
        for row in source_rows
    ]

    stale_cutoff = _utcnow() - timedelta(days=3)
    stale_filters = (
        Lead.deleted_at.is_(None),
        Lead.stage.notin_([LeadStage.WON, LeadStage.LOST]),
        or_(Lead.last_contact_at.is_(None), Lead.last_contact_at < stale_cutoff),
    )
    stale_leads_total = db.scalar(select(func.count()).select_from(Lead).where(*stale_filters)) or 0
    stale_leads = db.scalars(
        select(Lead)
        .where(*stale_filters)
        .order_by(Lead.last_contact_at.asc().nullsfirst())
        .limit(20)
    ).all()

    payload = {
        "pipeline": pipeline,
        "conversion_by_source": conversion,
        "cac": calculate_cac(db),
        "stale_leads_total": stale_leads_total,
        "stale_leads": stale_leads,
    }
    _cache_dashboard_payload(cache_key, CommercialDashboard, payload)
    return payload


def get_financial_dashboard(db: Session) -> dict:
    cache_key = make_cache_key("dashboard_financial")
    cached = dashboard_cache.get(cache_key)
    if cached is not None:
        return cached

    resolved_gym_id = _resolve_dashboard_gym_id()
    revenue = _revenue_series(db, 12, gym_id=resolved_gym_id)
    summary = get_finance_foundation_summary(db, gym_id=resolved_gym_id) if resolved_gym_id is not None else None

    growth_last = get_growth_mom_dashboard(db, months=6)
    avg_growth = sum(point.growth_mom for point in growth_last) / max(len(growth_last), 1)
    current_mrr = revenue[-1].value if revenue else 0.0
    projections = [
        ProjectionPoint(horizon_months=3, projected_revenue=round(current_mrr * (1 + avg_growth / 100) ** 3, 2)),
        ProjectionPoint(horizon_months=6, projected_revenue=round(current_mrr * (1 + avg_growth / 100) ** 6, 2)),
        ProjectionPoint(horizon_months=12, projected_revenue=round(current_mrr * (1 + avg_growth / 100) ** 12, 2)),
    ]
    if summary is None:
        delinquent = db.scalar(
            select(func.count())
            .select_from(Member)
            .where(Member.deleted_at.is_(None), Member.status == MemberStatus.ACTIVE, Member.risk_level == RiskLevel.RED)
        ) or 0
        active = db.scalar(
            select(func.count()).select_from(Member).where(Member.deleted_at.is_(None), Member.status == MemberStatus.ACTIVE)
        ) or 0
        payload = {
            "monthly_revenue": revenue,
            "delinquency_rate": round((float(delinquent) / max(float(active), 1.0)) * 100, 2),
            "projections": projections,
            "daily_cash_in": 0.0,
            "daily_cash_out": 0.0,
            "daily_net_cash": 0.0,
            "open_receivables": 0.0,
            "open_payables": 0.0,
            "overdue_receivables": 0.0,
            "overdue_payables": 0.0,
            "revenue_at_risk": 0.0,
            "dre_basic": {"revenue": 0.0, "expenses": 0.0, "net_result": 0.0, "margin_pct": None},
            "data_quality_flags": ["missing_financial_entry_base"],
        }
        _cache_dashboard_payload(cache_key, FinancialDashboard, payload)
        return payload

    payload = {
        "monthly_revenue": revenue,
        "delinquency_rate": summary.delinquency_rate,
        "projections": projections,
        "daily_cash_in": summary.daily_cash_in,
        "daily_cash_out": summary.daily_cash_out,
        "daily_net_cash": summary.daily_net_cash,
        "open_receivables": summary.open_receivables,
        "open_payables": summary.open_payables,
        "overdue_receivables": summary.overdue_receivables,
        "overdue_payables": summary.overdue_payables,
        "revenue_at_risk": summary.revenue_at_risk,
        "dre_basic": summary.dre_basic.model_dump(),
        "data_quality_flags": summary.data_quality_flags,
    }
    _cache_dashboard_payload(cache_key, FinancialDashboard, payload)
    return payload


def get_bi_foundation_dashboard(db: Session, months: int = 6) -> BIFoundationDashboard:
    cache_key = make_cache_key("dashboard_bi_foundation", months)
    cached = dashboard_cache.get(cache_key)
    if cached is not None:
        return BIFoundationDashboard.model_validate(cached)

    months = max(3, min(months, 12))
    resolved_gym_id = _resolve_dashboard_gym_id()
    cohort = _cohort_points(db, months, gym_id=resolved_gym_id)
    ltv = get_ltv_dashboard(db, months=months)
    financial = FinancialDashboard.model_validate(get_financial_dashboard(db))
    retention = RetentionDashboard.model_validate(get_retention_dashboard(db))
    follow_up_impact = _follow_up_impact(db, since=_utcnow() - timedelta(days=30), gym_id=resolved_gym_id)

    red_total = int(retention.red.total or 0)
    yellow_total = int(retention.yellow.total or 0)
    data_quality_flags: list[str] = []

    if not any(point.joined > 0 for point in cohort):
        data_quality_flags.append("missing_cohort_history")
    if not any(point.ltv > 0 for point in ltv):
        data_quality_flags.append("missing_ltv_history")
    if follow_up_impact.data_quality != "ready":
        data_quality_flags.append("missing_follow_up_outcomes")
    if (red_total + yellow_total) > 0 and retention.mrr_at_risk <= 0:
        data_quality_flags.append("revenue_at_risk_without_fee_base")

    payload = BIFoundationDashboard(
        generated_at=_utcnow(),
        cohort=cohort,
        ltv=ltv,
        forecast=financial.projections,
        revenue_at_risk=round(float(retention.mrr_at_risk or 0), 2),
        revenue_at_risk_members=red_total + yellow_total,
        follow_up_impact=follow_up_impact,
        data_quality_flags=data_quality_flags,
    )
    _cache_dashboard_payload(cache_key, BIFoundationDashboard, payload)
    return payload


def _cohort_points(db: Session, months: int, *, gym_id=None) -> list[BICohortPoint]:
    points: list[BICohortPoint] = []
    for label in _month_labels(months):
        month_start, month_end = _month_window(label)
        joined_filters = [
            Member.deleted_at.is_(None),
            Member.join_date >= month_start.date(),
            Member.join_date <= month_end.date(),
        ]
        if gym_id is not None:
            joined_filters.append(Member.gym_id == gym_id)
        joined = int(db.scalar(select(func.count()).select_from(Member).where(*joined_filters)) or 0)
        active = int(
            db.scalar(
                select(func.count())
                .select_from(Member)
                .where(
                    *joined_filters,
                    Member.status == MemberStatus.ACTIVE,
                    or_(Member.cancellation_date.is_(None), Member.cancellation_date > month_end.date()),
                )
            )
            or 0
        )
        mrr = db.scalar(
            select(func.coalesce(func.sum(Member.monthly_fee), Decimal("0")))
            .where(
                *joined_filters,
                Member.status == MemberStatus.ACTIVE,
                or_(Member.cancellation_date.is_(None), Member.cancellation_date > month_end.date()),
            )
        ) or Decimal("0")
        retained_rate = round((active / joined) * 100, 1) if joined else 0.0
        points.append(
            BICohortPoint(
                month=label,
                joined=joined,
                active=active,
                retained_rate=retained_rate,
                mrr=float(mrr),
            )
        )
    return points


def _follow_up_impact(db: Session, *, since: datetime, gym_id=None) -> BIFollowUpImpact:
    triage_filters = [AITriageRecommendation.updated_at >= since]
    task_filters = [
        Task.deleted_at.is_(None),
        Task.status == TaskStatus.DONE,
        Task.completed_at >= since,
        Task.extra_data["source"].astext.in_(
            [
                "ai_triage",
                "onboarding",
                "plan_followup",
                "retention_automation",
                "retention_intelligence",
            ]
        ),
    ]
    audit_filters = [
        AuditLog.created_at >= since,
        AuditLog.action.in_(["whatsapp_sent_manually", "call_log_manual"]),
    ]
    if gym_id is not None:
        triage_filters.append(AITriageRecommendation.gym_id == gym_id)
        task_filters.append(Task.gym_id == gym_id)
        audit_filters.append(AuditLog.gym_id == gym_id)

    prepared_actions = int(
        db.scalar(
            select(func.count())
            .select_from(AITriageRecommendation)
            .where(
                *triage_filters,
                AITriageRecommendation.execution_state.in_(["prepared", "queued", "running", "completed"]),
            )
        )
        or 0
    )
    positive_outcomes = int(
        db.scalar(
            select(func.count())
            .select_from(AITriageRecommendation)
            .where(
                *triage_filters,
                AITriageRecommendation.outcome_state == "positive",
            )
        )
        or 0
    )
    completed_followups = int(
        db.scalar(
            select(func.count())
            .select_from(Task)
            .where(*task_filters)
        )
        or 0
    )
    retention_contacts = int(
        db.scalar(
            select(func.count())
            .select_from(AuditLog)
            .where(*audit_filters)
        )
        or 0
    )
    acceptance_rate = round((positive_outcomes / prepared_actions) * 100, 1) if prepared_actions else None
    data_quality = "ready" if prepared_actions or completed_followups or retention_contacts else "no_base"
    return BIFollowUpImpact(
        prepared_actions_30d=prepared_actions,
        positive_outcomes_30d=positive_outcomes,
        completed_followups_30d=completed_followups,
        retention_contacts_30d=retention_contacts,
        acceptance_rate=acceptance_rate,
        data_quality=data_quality,
    )


def _resolve_dashboard_gym_id(gym_id=None):
    return gym_id or get_current_gym_id()


def _latest_open_retention_alert_subquery():
    ranked_alerts = (
        select(
            RiskAlert.id.label("alert_id"),
            RiskAlert.member_id.label("member_id"),
            func.row_number()
            .over(
                partition_by=RiskAlert.member_id,
                order_by=(RiskAlert.created_at.desc(), RiskAlert.id.desc()),
            )
            .label("row_number"),
        )
        .where(RiskAlert.resolved.is_(False))
        .subquery()
    )

    return (
        select(
            ranked_alerts.c.alert_id.label("alert_id"),
            ranked_alerts.c.member_id.label("member_id"),
        )
        .where(ranked_alerts.c.row_number == 1)
        .subquery()
    )


def _extract_forecast_60d(extra_data: dict | None) -> int | None:
    if not isinstance(extra_data, dict):
        return None
    value = extra_data.get("retention_forecast_60d")
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)) and 0 <= value <= 100:
        return int(round(value))
    return None


def _extract_forecast_source(extra_data: dict | None) -> str | None:
    if not isinstance(extra_data, dict):
        return None
    value = extra_data.get("retention_forecast_source")
    return value if isinstance(value, str) and value.strip() else None


def _prefetch_member_ids_with_assessments(db: Session, member_ids: list) -> set:
    if not member_ids:
        return set()
    return {
        member_id
        for member_id in db.scalars(
            select(Assessment.member_id)
            .where(
                Assessment.member_id.in_(member_ids),
                Assessment.deleted_at.is_(None),
            )
            .distinct()
        ).all()
        if member_id is not None
    }


def _normalize_retention_reasons(reasons: dict | None) -> dict:
    normalized = dict(reasons or {})
    baseline_raw = normalized.get("baseline_avg_weekly")
    drop_raw = normalized.get("frequency_drop_pct")
    try:
        baseline_avg = float(baseline_raw) if baseline_raw is not None else None
    except (TypeError, ValueError):
        baseline_avg = None

    if baseline_avg is not None and baseline_avg < _MIN_RELIABLE_BASELINE_AVG_WEEKLY and isinstance(drop_raw, (int, float)):
        normalized["frequency_drop_pct"] = None
    elif baseline_avg is None and isinstance(drop_raw, (int, float)) and float(drop_raw) >= 100:
        normalized["frequency_drop_pct"] = None

    return normalized


def _materialize_retention_context(
    db: Session,
    members: list[Member],
    *,
    include_forecast: bool,
) -> int:
    changes = 0
    for member in members:
        changed = False

        if not member.churn_type:
            member.churn_type = classify_churn_type(db, member)
            changed = True

        if include_forecast:
            extra_data = dict(member.extra_data or {})
            if _extract_forecast_60d(extra_data) is None:
                try:
                    forecast = get_assessment_forecast(db, member.id)
                except Exception:
                    forecast = None
                probability_60d = forecast.get("probability_60d") if isinstance(forecast, dict) else None
                if isinstance(probability_60d, (int, float)):
                    extra_data["retention_forecast_60d"] = int(round(probability_60d))
                    extra_data.setdefault("retention_forecast_source", "assessment_fallback")
                    member.extra_data = extra_data
                    changed = True

        if changed:
            db.add(member)
            changes += 1

    if changes:
        db.commit()
    return changes


def _resolve_retention_context_snapshot(
    db: Session,
    member: Member,
    *,
    include_forecast: bool,
    assessment_member_ids: set | None = None,
) -> tuple[str | None, int | None]:
    churn_type = member.churn_type
    if not churn_type:
        try:
            churn_type = classify_churn_type(db, member)
        except Exception:
            churn_type = ChurnType.UNKNOWN.value

    forecast_60d = _extract_forecast_60d(member.extra_data)
    forecast_source = _extract_forecast_source(member.extra_data)
    has_assessment_context = assessment_member_ids is not None and member.id in assessment_member_ids

    if not has_assessment_context and forecast_source == "assessment_fallback":
        forecast_60d = None

    if include_forecast and forecast_60d is None:
        if has_assessment_context:
            try:
                forecast = get_assessment_forecast(db, member.id)
            except Exception:
                forecast = None
            probability_60d = forecast.get("probability_60d") if isinstance(forecast, dict) else None
            if isinstance(probability_60d, (int, float)):
                forecast_60d = int(round(probability_60d))

    return churn_type, forecast_60d


def _member_out_snapshot(
    member: Member,
    *,
    churn_type: str | None = None,
    forecast_60d: int | None = None,
) -> MemberOut:
    payload = MemberOut.model_validate(member)
    if churn_type is None:
        churn_type = payload.churn_type

    extra_data = dict(payload.extra_data or {})
    if isinstance(forecast_60d, int):
        extra_data.setdefault("retention_forecast_60d", forecast_60d)

    return payload.model_copy(
        update={
            "churn_type": churn_type,
            "extra_data": extra_data,
        }
    )


def _days_without_checkin(member: Member) -> int:
    reference = member.last_checkin_at
    if reference is None:
        reference = datetime.combine(member.join_date, time.min, tzinfo=timezone.utc)
    elif reference.tzinfo is None:
        reference = reference.replace(tzinfo=timezone.utc)
    return max(0, (_utcnow() - reference).days)


def _effective_retention_severity(alert: RiskAlert, member: Member, *, days_without_checkin: int) -> tuple[int, RiskLevel]:
    """Escala a fila com o estado vivo do aluno, nao so com o snapshot salvo no alerta."""
    live_inactivity_floor = _inactivity_points(days_without_checkin)
    effective_score = max(
        int(alert.score or 0),
        int(member.risk_score or 0),
        int(live_inactivity_floor),
    )
    return effective_score, _determine_level(effective_score)


def _retention_signals_summary(member: Member, alert: RiskAlert, *, days_without_checkin: int, forecast_60d: int | None) -> str:
    reasons = _normalize_retention_reasons(alert.reasons)
    parts: list[str] = [f"{days_without_checkin} dias sem check-in"]

    frequency_drop_pct = reasons.get("frequency_drop_pct")
    if isinstance(frequency_drop_pct, (int, float)) and frequency_drop_pct >= 25:
        parts.append(f"queda de {round(float(frequency_drop_pct))}% na frequência")

    shift_change_hours = reasons.get("shift_change_hours")
    if isinstance(shift_change_hours, (int, float)) and shift_change_hours >= 2:
        parts.append(f"mudança de {int(shift_change_hours)}h no horário")

    if isinstance(member.nps_last_score, int) and 0 < member.nps_last_score <= 7:
        parts.append(f"NPS {member.nps_last_score}")

    if forecast_60d is not None and forecast_60d < 60:
        parts.append(f"forecast em {forecast_60d}%")

    return " · ".join(parts[:4]) if parts else "Alerta ativo aguardando ação do time."


def _retention_last_contact_map(db: Session, member_ids) -> dict[str, datetime]:
    if not member_ids:
        return {}

    rows = db.execute(
        select(AuditLog.member_id, func.max(AuditLog.created_at).label("last_at"))
        .where(
            AuditLog.member_id.in_(member_ids),
            AuditLog.action.in_(["whatsapp_sent_manually", "call_log_manual"]),
        )
        .group_by(AuditLog.member_id)
    ).all()
    return {str(row.member_id): row.last_at for row in rows if row.last_at is not None}


def _retention_plan_cycle_filter(plan_cycle: str):
    plan_label = {
        "monthly": "mensal",
        "semiannual": "semestral",
        "annual": "anual",
    }[plan_cycle]
    stored_plan_cycle = func.coalesce(Member.extra_data["plan_cycle"].astext, "")
    explicit_plan_cycle_in_name = or_(
        Member.plan_name.ilike("%mensal%"),
        Member.plan_name.ilike("%semestral%"),
        Member.plan_name.ilike("%anual%"),
    )
    return or_(
        Member.plan_name.ilike(f"%{plan_label}%"),
        and_(
            not_(explicit_plan_cycle_in_name),
            stored_plan_cycle == plan_cycle,
        ),
    )


def _retention_preferred_shift_filter(preferred_shift: str):
    return preferred_shift_filter_condition(Member.preferred_shift, preferred_shift)


def _retention_stage_filter_condition(retention_stage: str | None):
    if not retention_stage:
        return None

    now = _utcnow()
    reference = func.coalesce(Member.last_checkin_at, func.cast(Member.join_date, DateTime(timezone=True)))
    stage_windows = {
        RETENTION_STAGE_MONITORING: (None, 6),
        RETENTION_STAGE_ATTENTION: (7, 13),
        RETENTION_STAGE_RECOVERY: (14, 29),
        RETENTION_STAGE_REACTIVATION: (30, 44),
        RETENTION_STAGE_MANAGER_ESCALATION: (45, 59),
        RETENTION_STAGE_COLD_BASE: (60, None),
    }
    window = stage_windows.get(retention_stage)
    if window is None:
        return None
    min_days, max_days = window
    conditions = []
    if min_days is not None:
        conditions.append(reference <= now - timedelta(days=min_days))
    if max_days is not None:
        conditions.append(reference > now - timedelta(days=max_days + 1))
    return and_(*conditions) if conditions else None


def _extract_retention_cooldown_until(extra_data: dict | None) -> datetime | None:
    if not isinstance(extra_data, dict):
        return None
    value = extra_data.get("retention_cooldown_until")
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def get_retention_queue(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 50,
    search: str | None = None,
    level: str = "all",
    churn_type: str | None = None,
    plan_cycle: str | None = None,
    preferred_shift: str | None = None,
    retention_stage: str | None = None,
    gym_id=None,
) -> RetentionQueueResponse:
    resolved_gym_id = _resolve_dashboard_gym_id(gym_id)
    latest_alert_subquery = _latest_open_retention_alert_subquery()
    level_priority = case(
        (RiskAlert.level == RiskLevel.RED, 0),
        (RiskAlert.level == RiskLevel.YELLOW, 1),
        else_=2,
    )

    filters = [Member.deleted_at.is_(None)]
    if resolved_gym_id is not None:
        filters.append(RiskAlert.gym_id == resolved_gym_id)
    if level in {"red", "yellow"}:
        filters.append(RiskAlert.level == RiskLevel(level))
    if churn_type:
        filters.append(Member.churn_type == churn_type)
    if plan_cycle:
        filters.append(_retention_plan_cycle_filter(plan_cycle))
    preferred_shift_filter = _retention_preferred_shift_filter(preferred_shift or "")
    if preferred_shift_filter is not None:
        filters.append(preferred_shift_filter)
    stage_count_filters = list(filters)
    retention_stage_filter = _retention_stage_filter_condition(retention_stage)
    if retention_stage_filter is not None:
        filters.append(retention_stage_filter)
    if search and search.strip():
        search_value = f"%{search.strip()}%"
        filters.append(
            or_(
                Member.full_name.ilike(search_value),
                Member.email.ilike(search_value),
                Member.plan_name.ilike(search_value),
            )
        )

    base_stmt = (
        select(RiskAlert, Member)
        .join(latest_alert_subquery, latest_alert_subquery.c.alert_id == RiskAlert.id)
        .join(Member, Member.id == RiskAlert.member_id)
        .where(and_(*filters))
    )

    total = int(
        db.scalar(
            select(func.count())
            .select_from(RiskAlert)
            .join(latest_alert_subquery, latest_alert_subquery.c.alert_id == RiskAlert.id)
            .join(Member, Member.id == RiskAlert.member_id)
            .where(and_(*filters))
        )
        or 0
    )

    stage_counts = {stage: 0 for stage in RETENTION_STAGE_ORDER}
    for stage in RETENTION_STAGE_ORDER:
        stage_filter = _retention_stage_filter_condition(stage)
        stage_filters = list(stage_count_filters)
        if stage_filter is not None:
            stage_filters.append(stage_filter)
        stage_counts[stage] = int(
            db.scalar(
                select(func.count())
                .select_from(RiskAlert)
                .join(latest_alert_subquery, latest_alert_subquery.c.alert_id == RiskAlert.id)
                .join(Member, Member.id == RiskAlert.member_id)
                .where(and_(*stage_filters))
            )
            or 0
        )

    rows = db.execute(
        base_stmt
        .order_by(level_priority, RiskAlert.score.desc(), RiskAlert.created_at.asc(), Member.full_name.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    member_ids = [member.id for _, member in rows]
    assessment_member_ids = _prefetch_member_ids_with_assessments(db, member_ids)
    last_contact_map = _retention_last_contact_map(db, member_ids)

    items: list[RetentionQueueItem] = []
    for alert, member in rows:
        churn_type, forecast_60d = _resolve_retention_context_snapshot(
            db,
            member,
            include_forecast=True,
            assessment_member_ids=assessment_member_ids,
        )
        days_without_checkin = _days_without_checkin(member)
        calculated_retention_stage = calculate_retention_stage(days_without_checkin)
        stage_payload = retention_stage_payload(calculated_retention_stage)
        cooldown_until = _extract_retention_cooldown_until(getattr(member, "extra_data", None))
        effective_risk_score, effective_risk_level = _effective_retention_severity(
            alert,
            member,
            days_without_checkin=days_without_checkin,
        )
        normalized_reasons = _normalize_retention_reasons(alert.reasons)
        playbook = [
            RetentionPlaybookStep.model_validate(step)
            for step in build_retention_playbook(
                db,
                member,
                churn_type or ChurnType.UNKNOWN.value,
                retention_stage=calculated_retention_stage,
                days_without_checkin=days_without_checkin,
            )
        ]
        queue_item = RetentionQueueItem(
            alert_id=str(alert.id),
            member_id=str(member.id),
            full_name=member.full_name,
            email=member.email,
            phone=member.phone,
            plan_name=member.plan_name,
            preferred_shift=getattr(member, "preferred_shift", None),
            risk_level=effective_risk_level,
            risk_score=effective_risk_score,
            nps_last_score=int(member.nps_last_score or 0),
            days_without_checkin=days_without_checkin,
            last_checkin_at=member.last_checkin_at,
            last_contact_at=last_contact_map.get(str(member.id)),
            churn_type=churn_type,
            automation_stage=alert.automation_stage,
            created_at=alert.created_at,
            forecast_60d=forecast_60d,
            cooldown_until=cooldown_until,
            signals_summary=_retention_signals_summary(
                member,
                alert,
                days_without_checkin=days_without_checkin,
                forecast_60d=forecast_60d,
            ),
            **stage_payload,
            next_action=playbook[0].title if playbook else None,
            reasons=normalized_reasons,
            action_history=alert.action_history or [],
            playbook_steps=playbook,
        )
        queue_item.assistant = build_retention_assistant(queue_item)
        items.append(queue_item)

    items.sort(
        key=lambda item: (
            -int(item.retention_stage_priority or 0),
            0 if item.risk_level == RiskLevel.RED else 1 if item.risk_level == RiskLevel.YELLOW else 2,
            -item.risk_score,
            item.full_name.lower(),
        )
    )

    return RetentionQueueResponse(items=items, total=total, page=page, page_size=page_size, stage_counts=stage_counts)


def get_retention_dashboard(db: Session, red_page: int = 1, yellow_page: int = 1, page_size: int = 20) -> dict:
    cache_key = make_cache_key("dashboard_retention", red_page, yellow_page, page_size)
    cached = dashboard_cache.get(cache_key)
    if cached is not None:
        return cached

    base_red = (Member.deleted_at.is_(None), Member.risk_level == RiskLevel.RED)
    base_yellow = (Member.deleted_at.is_(None), Member.risk_level == RiskLevel.YELLOW)

    red_total = db.scalar(select(func.count()).select_from(Member).where(*base_red)) or 0
    yellow_total = db.scalar(select(func.count()).select_from(Member).where(*base_yellow)) or 0

    red_items = db.scalars(
        select(Member).where(*base_red).order_by(Member.risk_score.desc()).offset((red_page - 1) * page_size).limit(page_size)
    ).all()
    yellow_items = db.scalars(
        select(Member).where(*base_yellow).order_by(Member.risk_score.desc()).offset((yellow_page - 1) * page_size).limit(page_size)
    ).all()

    # Computed KPIs based on the full population, not just the paged samples.
    mrr_at_risk = float(
        db.scalar(
            select(func.coalesce(func.sum(Member.monthly_fee), Decimal("0"))).where(
                Member.deleted_at.is_(None),
                Member.risk_level.in_([RiskLevel.RED, RiskLevel.YELLOW]),
            )
        )
        or Decimal("0")
    )
    avg_red_score = float(
        db.scalar(select(func.coalesce(func.avg(Member.risk_score), 0.0)).where(*base_red))
        or 0.0
    )
    avg_yellow_score = float(
        db.scalar(select(func.coalesce(func.avg(Member.risk_score), 0.0)).where(*base_yellow))
        or 0.0
    )
    churn_distribution_rows = db.execute(
        select(
            func.coalesce(Member.churn_type, ChurnType.UNKNOWN.value).label("churn_type"),
            func.count(Member.id).label("total"),
        )
        .where(
            Member.deleted_at.is_(None),
            Member.risk_level.in_([RiskLevel.RED, RiskLevel.YELLOW]),
        )
        .group_by(func.coalesce(Member.churn_type, ChurnType.UNKNOWN.value))
    ).all()
    churn_distribution = {
        str(row.churn_type): int(row.total)
        for row in churn_distribution_rows
    }

    # Last contact per at-risk member (whatsapp or call)
    all_at_risk = list(red_items) + list(yellow_items)
    member_ids = [m.id for m in all_at_risk]
    last_contact_map: dict[str, str] = {}
    if member_ids:
        rows = db.execute(
            select(AuditLog.member_id, func.max(AuditLog.created_at).label("last_at"))
            .where(
                AuditLog.member_id.in_(member_ids),
                AuditLog.action.in_(["whatsapp_sent_manually", "call_log_manual"]),
            )
            .group_by(AuditLog.member_id)
        ).all()
        last_contact_map = {str(row.member_id): row.last_at.isoformat() for row in rows}

    red_payload = []
    for member in red_items:
        churn_type, _ = _resolve_retention_context_snapshot(db, member, include_forecast=False)
        red_payload.append(_member_out_snapshot(member, churn_type=churn_type))

    yellow_payload = []
    for member in yellow_items:
        churn_type, _ = _resolve_retention_context_snapshot(db, member, include_forecast=False)
        yellow_payload.append(_member_out_snapshot(member, churn_type=churn_type))

    nps_trend: list[NPSEvolutionPoint] = nps_evolution(db, months=12)
    payload = {
        "red": {"total": red_total, "items": red_payload},
        "yellow": {"total": yellow_total, "items": yellow_payload},
        "nps_trend": nps_trend,
        "mrr_at_risk": mrr_at_risk,
        "avg_red_score": round(avg_red_score, 1),
        "avg_yellow_score": round(avg_yellow_score, 1),
        "churn_distribution": churn_distribution,
        "last_contact_map": last_contact_map,
    }
    _cache_dashboard_payload(cache_key, RetentionDashboard, payload)
    return payload


def get_weekly_summary(db: Session) -> WeeklySummary:
    cache_key = make_cache_key("dashboard_weekly_summary")
    cached = dashboard_cache.get(cache_key)
    if cached is not None:
        return cached

    now = _utcnow()
    week_ago = now - timedelta(days=7)
    two_weeks_ago = now - timedelta(days=14)

    checkins_this_week = db.scalar(
        select(func.count()).select_from(Checkin).where(
            Checkin.checkin_at >= week_ago, Checkin.checkin_at < now,
        )
    ) or 0

    checkins_last_week = db.scalar(
        select(func.count()).select_from(Checkin).where(
            Checkin.checkin_at >= two_weeks_ago, Checkin.checkin_at < week_ago,
        )
    ) or 0

    new_registrations = db.scalar(
        select(func.count()).select_from(Member).where(
            Member.deleted_at.is_(None),
            Member.join_date >= week_ago.date(),
        )
    ) or 0

    new_at_risk = db.scalar(
        select(func.count()).select_from(Member).where(
            Member.deleted_at.is_(None),
            Member.status == MemberStatus.ACTIVE,
            Member.risk_level.in_([RiskLevel.YELLOW, RiskLevel.RED]),
            Member.updated_at >= week_ago,
        )
    ) or 0

    mrr_at_risk = db.scalar(
        select(func.sum(Member.monthly_fee)).where(
            Member.deleted_at.is_(None),
            Member.status == MemberStatus.ACTIVE,
            Member.risk_level == RiskLevel.RED,
        )
    ) or Decimal("0.00")

    total_active = db.scalar(
        select(func.count()).select_from(Member).where(
            Member.deleted_at.is_(None),
            Member.status == MemberStatus.ACTIVE,
        )
    ) or 0

    if checkins_last_week == 0:
        delta_pct = 100.0 if checkins_this_week > 0 else 0.0
    else:
        delta_pct = round(((checkins_this_week - checkins_last_week) / checkins_last_week) * 100, 1)

    payload = WeeklySummary(
        checkins_this_week=checkins_this_week,
        checkins_last_week=checkins_last_week,
        checkins_delta_pct=delta_pct,
        new_registrations=new_registrations,
        new_at_risk=new_at_risk,
        mrr_at_risk=float(mrr_at_risk),
        total_active=total_active,
    )
    _cache_dashboard_payload(cache_key, WeeklySummary, payload)
    return payload


def _month_labels(months: int) -> list[str]:
    labels = []
    today = date.today().replace(day=1)
    for index in range(months - 1, -1, -1):
        base = _subtract_months(today, index)
        labels.append(base.strftime("%Y-%m"))
    return labels


def _revenue_series(db: Session, months: int, *, gym_id=None) -> list[RevenuePoint]:
    materialized = _monthly_member_kpis_rows(db, months)
    if materialized:
        points: list[RevenuePoint] = []
        for row in materialized:
            entry_revenue = (
                get_monthly_financial_entry_revenue(db, gym_id=gym_id, month_label=str(row["month"]))
                if gym_id is not None
                else None
            )
            points.append(RevenuePoint(month=str(row["month"]), value=float(entry_revenue) if entry_revenue is not None else float(row["mrr"])))
        return points

    labels = _month_labels(months)
    points: list[RevenuePoint] = []
    for label in labels:
        entry_revenue = get_monthly_financial_entry_revenue(db, gym_id=gym_id, month_label=label) if gym_id is not None else None
        if entry_revenue is not None:
            points.append(RevenuePoint(month=label, value=float(entry_revenue)))
            continue
        month_start, month_end = _month_window(label)
        total = db.scalar(
            select(func.coalesce(func.sum(Member.monthly_fee), Decimal("0"))).where(
                Member.deleted_at.is_(None),
                Member.join_date <= month_end.date(),
                or_(Member.cancellation_date.is_(None), Member.cancellation_date >= month_start.date()),
            )
        ) or Decimal("0")
        points.append(RevenuePoint(month=label, value=float(total)))
    return points


def _churn_series(db: Session, months: int) -> list[ChurnPoint]:
    materialized = _monthly_member_kpis_rows(db, months)
    if materialized:
        points = []
        for row in materialized:
            churn_rate = (row["cancelled"] / max(1, row["active"])) * 100
            points.append(ChurnPoint(month=row["month"], churn_rate=round(churn_rate, 2)))
        return points

    labels = _month_labels(months)
    points: list[ChurnPoint] = []
    for label in labels:
        month_start, month_end = _month_window(label)
        cancelled = db.scalar(
            select(func.count()).select_from(Member).where(
                Member.deleted_at.is_(None),
                Member.cancellation_date >= month_start.date(),
                Member.cancellation_date <= month_end.date(),
            )
        ) or 0
        active_base = db.scalar(
            select(func.count()).select_from(Member).where(
                Member.deleted_at.is_(None),
                Member.join_date < month_start.date(),
                or_(Member.cancellation_date.is_(None), Member.cancellation_date >= month_start.date()),
            )
        ) or 0
        churn_rate = (cancelled / max(active_base, 1)) * 100
        points.append(ChurnPoint(month=label, churn_rate=round(churn_rate, 2)))
    return points


def _active_members_by_month(db: Session, month_label: str) -> int:
    month_start, month_end = _month_window(month_label)
    return db.scalar(
        select(func.count()).select_from(Member).where(
            Member.deleted_at.is_(None),
            Member.join_date <= month_end.date(),
            or_(Member.cancellation_date.is_(None), Member.cancellation_date >= month_start.date()),
        )
    ) or 0


def _members_joined_until_month(db: Session, month_label: str) -> int:
    _, month_end = _month_window(month_label)
    return db.scalar(
        select(func.count()).select_from(Member).where(Member.deleted_at.is_(None), Member.join_date <= month_end.date())
    ) or 0


def _members_joined_cumulative_by_month(db: Session, labels: list[str]) -> dict[str, int]:
    if not labels:
        return {}

    first_start, _ = _month_window(labels[0])
    _, last_end = _month_window(labels[-1])

    base_before_period = db.scalar(
        select(func.count()).select_from(Member).where(
            Member.deleted_at.is_(None),
            Member.join_date < first_start.date(),
        )
    ) or 0

    joined_rows = db.execute(
        select(
            func.to_char(Member.join_date, "YYYY-MM").label("month"),
            func.count(Member.id).label("total"),
        )
        .where(
            Member.deleted_at.is_(None),
            Member.join_date >= first_start.date(),
            Member.join_date <= last_end.date(),
        )
        .group_by(func.to_char(Member.join_date, "YYYY-MM"))
    ).all()
    joined_by_month = {str(row.month): int(row.total) for row in joined_rows}

    running = int(base_before_period)
    cumulative: dict[str, int] = {}
    for label in labels:
        running += joined_by_month.get(label, 0)
        cumulative[label] = running
    return cumulative


def _monthly_member_kpis_rows(db: Session, months: int) -> list[dict[str, int | float | str]] | None:
    labels = _month_labels(months)
    kpis_by_month = get_monthly_member_kpis(db, months)
    if not kpis_by_month:
        return None

    rows: list[dict[str, int | float | str]] = []
    for label in labels:
        values = kpis_by_month.get(label)
        if values:
            rows.append(
                {
                    "month": label,
                    "mrr": float(values["mrr"]),
                    "cancelled": int(values["cancelled"]),
                    "active": int(values["active"]),
                }
            )
        else:
            rows.append({"month": label, "mrr": 0.0, "cancelled": 0, "active": 0})
    return rows


def _subtract_months(base_date: date, months: int) -> date:
    year = base_date.year
    month = base_date.month - months
    while month <= 0:
        month += 12
        year -= 1
    return date(year, month, 1)


def _month_window(month_label: str) -> tuple[datetime, datetime]:
    year, month = (int(value) for value in month_label.split("-"))
    start = datetime(year, month, 1, tzinfo=timezone.utc)
    if month == 12:
        end = datetime(year + 1, 1, 1, tzinfo=timezone.utc) - timedelta(microseconds=1)
    else:
        end = datetime(year, month + 1, 1, tzinfo=timezone.utc) - timedelta(microseconds=1)
    return start, end


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)
