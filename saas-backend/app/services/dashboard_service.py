from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session

from app.core.cache import dashboard_cache, make_cache_key
from app.database import get_current_gym_id
from app.models import (
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
    TaskPriority,
    TaskStatus,
    User,
)
from app.models.enums import ChurnType
from app.schemas import (
    ActionCenterItem,
    ActionCenterResponse,
    ActionCenterSummary,
    ChurnPoint,
    ConversionBySource,
    ExecutiveDashboard,
    GrowthPoint,
    HeatmapPoint,
    LTVPoint,
    NPSEvolutionPoint,
    PaginatedResponse,
    ProjectionPoint,
    RetentionPlaybookStep,
    RetentionQueueItem,
    RevenuePoint,
    WeeklySummary,
)
from app.services.assessment_analytics_service import _due_label as _assessment_due_label
from app.services.assessment_analytics_service import _latest_assessment_subquery as _assessment_latest_subquery
from app.services.assessment_analytics_service import _queue_conditions as _assessment_queue_conditions
from app.services.ai_assistant_service import build_retention_assistant
from app.services.analytics_view_service import get_monthly_member_kpis
from app.services.crm_service import calculate_cac
from app.services.nps_service import nps_evolution
from app.services.retention_intelligence_service import build_retention_playbook


_ACTION_CENTER_SOURCE_LABELS = {
    "task": "Tarefas",
    "retention": "Retenção",
    "assessment": "Avaliações",
    "crm": "CRM",
}
_ACTION_CENTER_SEVERITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}


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
    dashboard_cache.set(cache_key, payload)
    return payload


def get_mrr_dashboard(db: Session, months: int = 12) -> list[RevenuePoint]:
    cache_key = make_cache_key("dashboard_mrr", months)
    cached = dashboard_cache.get(cache_key)
    if cached is not None:
        return cached
    payload = _revenue_series(db, months)
    dashboard_cache.set(cache_key, payload)
    return payload


def get_churn_dashboard(db: Session, months: int = 12) -> list[ChurnPoint]:
    cache_key = make_cache_key("dashboard_churn", months)
    cached = dashboard_cache.get(cache_key)
    if cached is not None:
        return cached
    payload = _churn_series(db, months)
    dashboard_cache.set(cache_key, payload)
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
        dashboard_cache.set(cache_key, points)
        return points

    churn_series = _churn_series(db, months)
    revenue_series = _revenue_series(db, months)
    points: list[LTVPoint] = []
    for churn, revenue in zip(churn_series, revenue_series):
        churn_rate = max(churn.churn_rate / 100, 0.0001)
        ltv = (revenue.value / max(1, _active_members_by_month(db, churn.month))) / churn_rate
        points.append(LTVPoint(month=churn.month, ltv=round(ltv, 2)))

    dashboard_cache.set(cache_key, points)
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

    dashboard_cache.set(cache_key, values)
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

    payload = {
        "realtime_checkins": realtime_checkins,
        "heatmap": heatmap,
        "inactive_7d_total": total_inactive,
        "inactive_7d_items": items,
    }
    dashboard_cache.set(cache_key, payload)
    return payload


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
    pitch_pipeline_rows = db.execute(
        select(Lead.pitch_step, func.count(Lead.id).label("total"))
        .where(Lead.deleted_at.is_(None))
        .group_by(Lead.pitch_step)
    ).all()
    pitch_pipeline = {
        str(row.pitch_step): int(row.total)
        for row in pitch_pipeline_rows
        if row.pitch_step
    }

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
        "pitch_pipeline": pitch_pipeline,
        "conversion_by_source": conversion,
        "cac": calculate_cac(db),
        "stale_leads_total": stale_leads_total,
        "stale_leads": stale_leads,
    }
    dashboard_cache.set(cache_key, payload)
    return payload


def _severity_rank(value: str) -> int:
    return _ACTION_CENTER_SEVERITY_RANK.get(value, 99)


def _apply_action_center_filters(items: list[ActionCenterItem], *, source: str, severity: str) -> list[ActionCenterItem]:
    filtered = items
    if source != "all":
        filtered = [item for item in filtered if item.source == source]
    if severity != "all":
        filtered = [item for item in filtered if item.severity == severity]
    return filtered


def _summarize_action_center(items: list[ActionCenterItem]) -> ActionCenterSummary:
    by_source: dict[str, int] = {}
    by_severity: dict[str, int] = {}
    for item in items:
        by_source[item.source] = by_source.get(item.source, 0) + 1
        by_severity[item.severity] = by_severity.get(item.severity, 0) + 1
    return ActionCenterSummary(total=len(items), by_source=by_source, by_severity=by_severity)


def _build_task_action_items(db: Session, *, gym_id, search: str | None) -> list[ActionCenterItem]:
    filters = [
        Task.deleted_at.is_(None),
        Task.status.in_([TaskStatus.TODO, TaskStatus.DOING]),
    ]
    if gym_id is not None:
        filters.append(Task.gym_id == gym_id)
    if search and search.strip():
        search_value = f"%{search.strip()}%"
        filters.append(
            or_(
                Task.title.ilike(search_value),
                Task.description.ilike(search_value),
                Member.full_name.ilike(search_value),
                Lead.full_name.ilike(search_value),
            )
        )

    rows = db.execute(
        select(Task, Member, Lead, User)
        .outerjoin(Member, Member.id == Task.member_id)
        .outerjoin(Lead, Lead.id == Task.lead_id)
        .outerjoin(User, User.id == Task.assigned_to_user_id)
        .where(and_(*filters))
    ).all()

    now = _utcnow()
    items: list[ActionCenterItem] = []
    for task, member, lead, owner in rows:
        due_at = task.due_date
        if due_at is not None and due_at.tzinfo is None:
            due_at = due_at.replace(tzinfo=timezone.utc)

        overdue_days = max(0, (now - due_at).days) if due_at and due_at < now else 0
        if due_at and due_at < now:
            severity = "critical"
        elif task.priority in {TaskPriority.URGENT, TaskPriority.HIGH} or task.status == TaskStatus.DOING:
            severity = "high"
        elif task.priority == TaskPriority.MEDIUM:
            severity = "medium"
        else:
            severity = "low"

        target_name = member.full_name if member else lead.full_name if lead else "Sem vínculo"
        subtitle_parts = [target_name]
        if due_at:
            subtitle_parts.append(f"vence {due_at.strftime('%d/%m %H:%M')}")
        else:
            subtitle_parts.append("sem prazo definido")

        items.append(
            ActionCenterItem(
                id=f"task-{task.id}",
                source="task",
                source_label=_ACTION_CENTER_SOURCE_LABELS["task"],
                severity=severity,
                severity_rank=_severity_rank(severity),
                title=task.title,
                subtitle=" · ".join(subtitle_parts),
                member_id=str(member.id) if member else None,
                lead_id=str(lead.id) if lead else None,
                task_id=str(task.id),
                status=task.status.value,
                owner_label=owner.full_name if owner else None,
                value_amount=float(member.monthly_fee if member else lead.estimated_value if lead else 0),
                stale_days=overdue_days,
                due_at=due_at,
                last_contact_at=lead.last_contact_at if lead else None,
                last_checkin_at=member.last_checkin_at if member else None,
                cta_label="Abrir tarefa",
                cta_target=f"/tasks?taskId={task.id}",
                metadata={
                    "priority": task.priority.value,
                    "member_name": member.full_name if member else None,
                    "lead_name": lead.full_name if lead else None,
                },
            )
        )
    return items


def _build_retention_action_items(db: Session, *, gym_id, search: str | None) -> list[ActionCenterItem]:
    latest_alert_subquery = _latest_open_retention_alert_subquery()
    filters = [RiskAlert.resolved.is_(False), Member.deleted_at.is_(None)]
    if gym_id is not None:
        filters.append(RiskAlert.gym_id == gym_id)
    if search and search.strip():
        search_value = f"%{search.strip()}%"
        filters.append(
            or_(
                Member.full_name.ilike(search_value),
                Member.email.ilike(search_value),
                Member.plan_name.ilike(search_value),
            )
        )

    rows = db.execute(
        select(RiskAlert, Member, User)
        .join(latest_alert_subquery, latest_alert_subquery.c.alert_id == RiskAlert.id)
        .join(Member, Member.id == RiskAlert.member_id)
        .outerjoin(User, User.id == Member.assigned_user_id)
        .where(and_(*filters))
    ).all()

    last_contact_map = _retention_last_contact_map(db, [member.id for _, member, _ in rows])
    items: list[ActionCenterItem] = []
    for alert, member, owner in rows:
        forecast_60d = _extract_forecast_60d(member.extra_data)
        days_without_checkin = _days_without_checkin(member)
        severity = "critical" if alert.level == RiskLevel.RED else "high"

        items.append(
            ActionCenterItem(
                id=f"retention-{alert.id}",
                source="retention",
                source_label=_ACTION_CENTER_SOURCE_LABELS["retention"],
                severity=severity,
                severity_rank=_severity_rank(severity),
                title=member.full_name,
                subtitle=_retention_signals_summary(
                    member,
                    alert,
                    days_without_checkin=days_without_checkin,
                    forecast_60d=forecast_60d,
                ),
                member_id=str(member.id),
                risk_alert_id=str(alert.id),
                status=alert.automation_stage or alert.level.value,
                owner_label=owner.full_name if owner else None,
                value_amount=float(member.monthly_fee or 0),
                stale_days=days_without_checkin,
                due_at=alert.created_at,
                last_contact_at=last_contact_map.get(str(member.id)),
                last_checkin_at=member.last_checkin_at,
                cta_label="Abrir retenção",
                cta_target=f"/dashboard/retention?alertId={alert.id}",
                metadata={
                    "risk_level": alert.level.value,
                    "risk_score": int(alert.score or member.risk_score or 0),
                    "churn_type": member.churn_type,
                    "forecast_60d": forecast_60d,
                },
            )
        )
    return items


def _build_assessment_action_items(db: Session, *, gym_id, search: str | None) -> list[ActionCenterItem]:
    now = _utcnow()
    cutoff_90 = now - timedelta(days=90)
    today = now.date()
    next_7 = today + timedelta(days=7)

    latest_assessment_subquery = _assessment_latest_subquery()
    last_assessment_date_col = latest_assessment_subquery.c.last_assessment_date
    next_assessment_due_col = latest_assessment_subquery.c.next_assessment_due
    queue_conditions = _assessment_queue_conditions(
        last_assessment_date_col,
        next_assessment_due_col,
        cutoff_90=cutoff_90,
        today=today,
        next_7=next_7,
    )
    bucket_expr = case(
        (queue_conditions["never"], "never"),
        (queue_conditions["overdue"], "overdue"),
        (queue_conditions["week"], "week"),
        else_="covered",
    )

    filters = [
        Member.deleted_at.is_(None),
        or_(queue_conditions["never"], queue_conditions["overdue"], queue_conditions["week"]),
    ]
    if gym_id is not None:
        filters.append(Member.gym_id == gym_id)
    if search and search.strip():
        search_value = f"%{search.strip()}%"
        filters.append(
            or_(
                Member.full_name.ilike(search_value),
                Member.email.ilike(search_value),
                Member.plan_name.ilike(search_value),
            )
        )

    rows = db.execute(
        select(
            Member,
            User,
            last_assessment_date_col.label("last_assessment_date"),
            next_assessment_due_col.label("next_assessment_due"),
            bucket_expr.label("bucket"),
        )
        .outerjoin(latest_assessment_subquery, latest_assessment_subquery.c.member_id == Member.id)
        .outerjoin(User, User.id == Member.assigned_user_id)
        .where(and_(*filters))
    ).all()

    items: list[ActionCenterItem] = []
    for member, owner, last_assessment_date, next_assessment_due, bucket in rows:
        if bucket == "never":
            severity = "critical"
            stale_days = max(0, (today - member.join_date).days)
        elif bucket == "overdue":
            severity = "critical"
            if next_assessment_due and next_assessment_due < today:
                stale_days = max(0, (today - next_assessment_due).days)
            elif last_assessment_date is not None:
                stale_days = max(0, (today - last_assessment_date.date()).days - 90)
            else:
                stale_days = 0
        else:
            severity = "high"
            stale_days = max(0, (next_assessment_due - today).days) if next_assessment_due else 0

        due_at = (
            datetime.combine(next_assessment_due, time.min, tzinfo=timezone.utc)
            if next_assessment_due is not None
            else None
        )
        subtitle = _assessment_due_label(bucket, next_assessment_due, today)

        items.append(
            ActionCenterItem(
                id=f"assessment-{member.id}-{bucket}",
                source="assessment",
                source_label=_ACTION_CENTER_SOURCE_LABELS["assessment"],
                severity=severity,
                severity_rank=_severity_rank(severity),
                title=member.full_name,
                subtitle=subtitle,
                member_id=str(member.id),
                status=bucket,
                owner_label=owner.full_name if owner else None,
                value_amount=float(member.monthly_fee or 0),
                stale_days=stale_days,
                due_at=due_at,
                last_checkin_at=member.last_checkin_at,
                cta_label="Abrir avaliações",
                cta_target=f"/assessments?memberId={member.id}&bucket={bucket}",
                metadata={
                    "plan_name": member.plan_name,
                    "risk_level": member.risk_level.value,
                    "risk_score": int(member.risk_score or 0),
                    "last_assessment_date": last_assessment_date.isoformat() if last_assessment_date else None,
                },
            )
        )
    return items


def _build_crm_action_items(db: Session, *, gym_id, search: str | None) -> list[ActionCenterItem]:
    stale_cutoff = _utcnow() - timedelta(days=3)
    filters = [
        Lead.deleted_at.is_(None),
        Lead.stage.notin_([LeadStage.WON, LeadStage.LOST]),
        or_(Lead.last_contact_at.is_(None), Lead.last_contact_at < stale_cutoff),
    ]
    if gym_id is not None:
        filters.append(Lead.gym_id == gym_id)
    if search and search.strip():
        search_value = f"%{search.strip()}%"
        filters.append(
            or_(
                Lead.full_name.ilike(search_value),
                Lead.email.ilike(search_value),
                Lead.source.ilike(search_value),
                Lead.pitch_step.ilike(search_value),
            )
        )

    rows = db.execute(
        select(Lead, User)
        .outerjoin(User, User.id == Lead.owner_id)
        .where(and_(*filters))
    ).all()

    now = _utcnow()
    items: list[ActionCenterItem] = []
    for lead, owner in rows:
        reference = lead.last_contact_at or lead.updated_at or lead.created_at
        if reference.tzinfo is None:
            reference = reference.replace(tzinfo=timezone.utc)
        stale_days = max(0, (now - reference).days)

        if lead.pitch_step in {"booking", "proposal"} and stale_days >= 3:
            severity = "critical"
        elif lead.pitch_step in {"booking", "proposal", "objection"}:
            severity = "high"
        else:
            severity = "medium"

        items.append(
            ActionCenterItem(
                id=f"crm-{lead.id}",
                source="crm",
                source_label=_ACTION_CENTER_SOURCE_LABELS["crm"],
                severity=severity,
                severity_rank=_severity_rank(severity),
                title=lead.full_name,
                subtitle=f"{lead.pitch_step} · {stale_days} dias sem contato",
                lead_id=str(lead.id),
                status=lead.stage.value,
                owner_label=owner.full_name if owner else None,
                value_amount=float(lead.estimated_value or 0),
                stale_days=stale_days,
                due_at=lead.last_contact_at,
                last_contact_at=lead.last_contact_at,
                cta_label="Abrir CRM",
                cta_target=f"/crm?leadId={lead.id}",
                metadata={
                    "source": lead.source,
                    "pitch_step": lead.pitch_step,
                    "estimated_value": float(lead.estimated_value or 0),
                },
            )
        )
    return items


def get_action_center(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 25,
    search: str | None = None,
    source: str = "all",
    severity: str = "all",
    gym_id=None,
) -> ActionCenterResponse:
    resolved_gym_id = _resolve_dashboard_gym_id(gym_id)
    normalized_search = (search or "").strip()
    cache_key = make_cache_key(
        "dashboard_action_center",
        page,
        page_size,
        normalized_search,
        source,
        severity,
    )
    cached = dashboard_cache.get(cache_key)
    if cached is not None:
        return cached

    items: list[ActionCenterItem] = []
    if source in {"all", "task"}:
        items.extend(_build_task_action_items(db, gym_id=resolved_gym_id, search=normalized_search))
    if source in {"all", "retention"}:
        items.extend(_build_retention_action_items(db, gym_id=resolved_gym_id, search=normalized_search))
    if source in {"all", "assessment"}:
        items.extend(_build_assessment_action_items(db, gym_id=resolved_gym_id, search=normalized_search))
    if source in {"all", "crm"}:
        items.extend(_build_crm_action_items(db, gym_id=resolved_gym_id, search=normalized_search))

    filtered = _apply_action_center_filters(items, source=source, severity=severity)
    filtered.sort(
        key=lambda item: (
            item.severity_rank,
            -item.stale_days,
            -item.value_amount,
            item.title.lower(),
        )
    )
    summary = _summarize_action_center(filtered)
    offset = (page - 1) * page_size
    payload = ActionCenterResponse(
        items=filtered[offset : offset + page_size],
        total=summary.total,
        page=page,
        page_size=page_size,
        summary=summary,
    )
    dashboard_cache.set(cache_key, payload)
    return payload


def get_financial_dashboard(db: Session) -> dict:
    cache_key = make_cache_key("dashboard_financial")
    cached = dashboard_cache.get(cache_key)
    if cached is not None:
        return cached

    revenue = _revenue_series(db, 12)
    delinquent = db.scalar(
        select(func.count()).select_from(Member).where(
            Member.deleted_at.is_(None),
            Member.status == MemberStatus.ACTIVE,
            Member.extra_data["delinquent"].astext == "true",
        )
    ) or 0
    active = db.scalar(
        select(func.count()).select_from(Member).where(Member.deleted_at.is_(None), Member.status == MemberStatus.ACTIVE)
    ) or 0
    delinquency_rate = (delinquent / max(active, 1)) * 100

    growth_last = get_growth_mom_dashboard(db, months=6)
    avg_growth = sum(point.growth_mom for point in growth_last) / max(len(growth_last), 1)
    current_mrr = revenue[-1].value if revenue else 0.0
    projections = [
        ProjectionPoint(horizon_months=3, projected_revenue=round(current_mrr * (1 + avg_growth / 100) ** 3, 2)),
        ProjectionPoint(horizon_months=6, projected_revenue=round(current_mrr * (1 + avg_growth / 100) ** 6, 2)),
        ProjectionPoint(horizon_months=12, projected_revenue=round(current_mrr * (1 + avg_growth / 100) ** 12, 2)),
    ]

    payload = {
        "monthly_revenue": revenue,
        "delinquency_rate": round(delinquency_rate, 2),
        "projections": projections,
    }
    dashboard_cache.set(cache_key, payload)
    return payload


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


def _days_without_checkin(member: Member) -> int:
    reference = member.last_checkin_at
    if reference is None:
        reference = datetime.combine(member.join_date, time.min, tzinfo=timezone.utc)
    elif reference.tzinfo is None:
        reference = reference.replace(tzinfo=timezone.utc)
    return max(0, (_utcnow() - reference).days)


def _retention_signals_summary(member: Member, alert: RiskAlert, *, days_without_checkin: int, forecast_60d: int | None) -> str:
    reasons = alert.reasons or {}
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


def get_retention_queue(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 50,
    search: str | None = None,
    level: str = "all",
    churn_type: str | None = None,
    gym_id=None,
) -> PaginatedResponse[RetentionQueueItem]:
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

    rows = db.execute(
        base_stmt
        .order_by(level_priority, RiskAlert.score.desc(), RiskAlert.created_at.asc(), Member.full_name.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    member_ids = [member.id for _, member in rows]
    last_contact_map = _retention_last_contact_map(db, member_ids)

    items: list[RetentionQueueItem] = []
    for alert, member in rows:
        forecast_60d = _extract_forecast_60d(member.extra_data)
        days_without_checkin = _days_without_checkin(member)
        playbook = [
            RetentionPlaybookStep.model_validate(step)
            for step in build_retention_playbook(db, member, member.churn_type or ChurnType.UNKNOWN.value)
        ]
        queue_item = RetentionQueueItem(
            alert_id=str(alert.id),
            member_id=str(member.id),
            full_name=member.full_name,
            email=member.email,
            phone=member.phone,
            plan_name=member.plan_name,
            risk_level=alert.level,
            risk_score=int(alert.score or member.risk_score or 0),
            nps_last_score=int(member.nps_last_score or 0),
            days_without_checkin=days_without_checkin,
            last_checkin_at=member.last_checkin_at,
            last_contact_at=last_contact_map.get(str(member.id)),
            churn_type=member.churn_type,
            automation_stage=alert.automation_stage,
            created_at=alert.created_at,
            forecast_60d=forecast_60d,
            signals_summary=_retention_signals_summary(
                member,
                alert,
                days_without_checkin=days_without_checkin,
                forecast_60d=forecast_60d,
            ),
            next_action=playbook[0].title if playbook else None,
            reasons=alert.reasons or {},
            action_history=alert.action_history or [],
            playbook_steps=playbook,
        )
        queue_item.assistant = build_retention_assistant(queue_item)
        items.append(queue_item)

    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)


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

    nps_trend: list[NPSEvolutionPoint] = nps_evolution(db, months=12)
    payload = {
        "red": {"total": red_total, "items": red_items},
        "yellow": {"total": yellow_total, "items": yellow_items},
        "nps_trend": nps_trend,
        "mrr_at_risk": mrr_at_risk,
        "avg_red_score": round(avg_red_score, 1),
        "avg_yellow_score": round(avg_yellow_score, 1),
        "churn_distribution": churn_distribution,
        "last_contact_map": last_contact_map,
    }
    dashboard_cache.set(cache_key, payload)
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
    dashboard_cache.set(cache_key, payload)
    return payload


def _month_labels(months: int) -> list[str]:
    labels = []
    today = date.today().replace(day=1)
    for index in range(months - 1, -1, -1):
        base = _subtract_months(today, index)
        labels.append(base.strftime("%Y-%m"))
    return labels


def _revenue_series(db: Session, months: int) -> list[RevenuePoint]:
    materialized = _monthly_member_kpis_rows(db, months)
    if materialized:
        return [RevenuePoint(month=row["month"], value=float(row["mrr"])) for row in materialized]

    labels = _month_labels(months)
    points: list[RevenuePoint] = []
    for label in labels:
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
