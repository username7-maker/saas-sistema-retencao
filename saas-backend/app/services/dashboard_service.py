from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session

from app.core.cache import dashboard_cache, make_cache_key
from app.models import Checkin, Lead, LeadStage, Member, MemberStatus, NPSResponse, RiskLevel
from app.schemas import (
    ChurnPoint,
    ConversionBySource,
    ExecutiveDashboard,
    GrowthPoint,
    HeatmapPoint,
    LTVPoint,
    NPSEvolutionPoint,
    ProjectionPoint,
    RevenuePoint,
)
from app.services.crm_service import calculate_cac
from app.services.nps_service import nps_evolution


def get_executive_dashboard(db: Session) -> ExecutiveDashboard:
    cache_key = make_cache_key("dashboard_executive")
    if cache_key in dashboard_cache:
        return dashboard_cache[cache_key]

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

    churn_value = _churn_series(db, months=1)[0].churn_rate if _churn_series(db, months=1) else 0.0
    payload = ExecutiveDashboard(
        total_members=total_members,
        active_members=active_members,
        mrr=float(mrr),
        churn_rate=churn_value,
        nps_avg=float(nps_avg),
        risk_distribution=risk_distribution,
    )
    dashboard_cache[cache_key] = payload
    return payload


def get_mrr_dashboard(db: Session, months: int = 12) -> list[RevenuePoint]:
    cache_key = make_cache_key("dashboard_mrr", months)
    if cache_key in dashboard_cache:
        return dashboard_cache[cache_key]
    payload = _revenue_series(db, months)
    dashboard_cache[cache_key] = payload
    return payload


def get_churn_dashboard(db: Session, months: int = 12) -> list[ChurnPoint]:
    cache_key = make_cache_key("dashboard_churn", months)
    if cache_key in dashboard_cache:
        return dashboard_cache[cache_key]
    payload = _churn_series(db, months)
    dashboard_cache[cache_key] = payload
    return payload


def get_ltv_dashboard(db: Session, months: int = 12) -> list[LTVPoint]:
    cache_key = make_cache_key("dashboard_ltv", months)
    if cache_key in dashboard_cache:
        return dashboard_cache[cache_key]

    churn_series = _churn_series(db, months)
    revenue_series = _revenue_series(db, months)
    points: list[LTVPoint] = []
    for churn, revenue in zip(churn_series, revenue_series):
        churn_rate = max(churn.churn_rate / 100, 0.0001)
        ltv = (revenue.value / max(1, _active_members_by_month(db, churn.month))) / churn_rate
        points.append(LTVPoint(month=churn.month, ltv=round(ltv, 2)))

    dashboard_cache[cache_key] = points
    return points


def get_growth_mom_dashboard(db: Session, months: int = 12) -> list[GrowthPoint]:
    cache_key = make_cache_key("dashboard_growth", months)
    if cache_key in dashboard_cache:
        return dashboard_cache[cache_key]

    values: list[GrowthPoint] = []
    month_labels = _month_labels(months)
    previous = None
    for label in month_labels:
        current_total = _members_joined_until_month(db, label)
        if previous in (None, 0):
            growth = 0.0
        else:
            growth = ((current_total - previous) / previous) * 100
        values.append(GrowthPoint(month=label, growth_mom=round(growth, 2)))
        previous = current_total

    dashboard_cache[cache_key] = values
    return values


def get_operational_dashboard(db: Session, page: int = 1, page_size: int = 20) -> dict:
    cache_key = make_cache_key("dashboard_operational", page, page_size)
    if cache_key in dashboard_cache:
        return dashboard_cache[cache_key]

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
    stmt = select(Member).where(
        Member.deleted_at.is_(None),
        Member.status == MemberStatus.ACTIVE,
        or_(Member.last_checkin_at.is_(None), Member.last_checkin_at < cutoff),
    )
    total_inactive = len(db.scalars(stmt).all())
    items = db.scalars(stmt.order_by(Member.last_checkin_at.asc()).offset((page - 1) * page_size).limit(page_size)).all()

    payload = {
        "realtime_checkins": realtime_checkins,
        "heatmap": heatmap,
        "inactive_7d_total": total_inactive,
        "inactive_7d_items": items,
    }
    dashboard_cache[cache_key] = payload
    return payload


def get_commercial_dashboard(db: Session) -> dict:
    cache_key = make_cache_key("dashboard_commercial")
    if cache_key in dashboard_cache:
        return dashboard_cache[cache_key]

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

    payload = {
        "pipeline": pipeline,
        "conversion_by_source": conversion,
        "cac": calculate_cac(db),
    }
    dashboard_cache[cache_key] = payload
    return payload


def get_financial_dashboard(db: Session) -> dict:
    cache_key = make_cache_key("dashboard_financial")
    if cache_key in dashboard_cache:
        return dashboard_cache[cache_key]

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
    dashboard_cache[cache_key] = payload
    return payload


def get_retention_dashboard(db: Session, red_page: int = 1, yellow_page: int = 1, page_size: int = 20) -> dict:
    cache_key = make_cache_key("dashboard_retention", red_page, yellow_page, page_size)
    if cache_key in dashboard_cache:
        return dashboard_cache[cache_key]

    red_query = select(Member).where(Member.deleted_at.is_(None), Member.risk_level == RiskLevel.RED)
    yellow_query = select(Member).where(Member.deleted_at.is_(None), Member.risk_level == RiskLevel.YELLOW)

    red_total = len(db.scalars(red_query).all())
    yellow_total = len(db.scalars(yellow_query).all())

    red_items = db.scalars(
        red_query.order_by(Member.risk_score.desc()).offset((red_page - 1) * page_size).limit(page_size)
    ).all()
    yellow_items = db.scalars(
        yellow_query.order_by(Member.risk_score.desc()).offset((yellow_page - 1) * page_size).limit(page_size)
    ).all()

    nps_trend: list[NPSEvolutionPoint] = nps_evolution(db, months=12)
    payload = {
        "red": {"total": red_total, "items": red_items},
        "yellow": {"total": yellow_total, "items": yellow_items},
        "nps_trend": nps_trend,
    }
    dashboard_cache[cache_key] = payload
    return payload


def _month_labels(months: int) -> list[str]:
    labels = []
    today = date.today().replace(day=1)
    for index in range(months - 1, -1, -1):
        base = _subtract_months(today, index)
        labels.append(base.strftime("%Y-%m"))
    return labels


def _revenue_series(db: Session, months: int) -> list[RevenuePoint]:
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
