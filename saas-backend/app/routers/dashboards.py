from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dependencies import require_roles
from app.database import get_db
from app.models import RoleEnum, User
from app.schemas import (
    BIFoundationDashboard,
    ChurnPoint,
    CommercialDashboard,
    ExecutiveDashboard,
    FinancialDashboard,
    GrowthPoint,
    LTVPoint,
    OperationalDashboard,
    RetentionDashboard,
    RetentionQueueResponse,
    RevenuePoint,
    WeeklySummary,
)
from app.schemas.insights import InsightResponse
from app.services.ai_insight_service import (
    generate_commercial_insight,
    generate_executive_insight,
    generate_financial_insight,
    generate_operational_insight,
    generate_retention_insight,
)
from app.services.dashboard_service import (
    get_churn_dashboard,
    get_bi_foundation_dashboard,
    get_commercial_dashboard,
    get_executive_dashboard,
    get_financial_dashboard,
    get_growth_mom_dashboard,
    get_ltv_dashboard,
    get_mrr_dashboard,
    get_operational_dashboard,
    get_retention_dashboard,
    get_retention_queue,
    get_weekly_summary,
)


router = APIRouter(prefix="/dashboards", tags=["dashboards"])


@router.get("/executive", response_model=ExecutiveDashboard)
def executive_dashboard(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
) -> ExecutiveDashboard:
    return get_executive_dashboard(db)


@router.get("/mrr", response_model=list[RevenuePoint])
def mrr_dashboard(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
    months: int = Query(12, ge=1, le=24),
) -> list[RevenuePoint]:
    return get_mrr_dashboard(db, months=months)


@router.get("/churn", response_model=list[ChurnPoint])
def churn_dashboard(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
    months: int = Query(12, ge=1, le=24),
) -> list[ChurnPoint]:
    return get_churn_dashboard(db, months=months)


@router.get("/ltv", response_model=list[LTVPoint])
def ltv_dashboard(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
    months: int = Query(12, ge=1, le=24),
) -> list[LTVPoint]:
    return get_ltv_dashboard(db, months=months)


@router.get("/growth-mom", response_model=list[GrowthPoint])
def growth_dashboard(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
    months: int = Query(12, ge=1, le=24),
) -> list[GrowthPoint]:
    return get_growth_mom_dashboard(db, months=months)


@router.get("/operational", response_model=OperationalDashboard)
def operational_dashboard(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST))],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> OperationalDashboard:
    return get_operational_dashboard(db, page=page, page_size=page_size)


@router.get("/commercial", response_model=CommercialDashboard)
def commercial_dashboard(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.SALESPERSON))],
) -> CommercialDashboard:
    return get_commercial_dashboard(db)


@router.get("/financial", response_model=FinancialDashboard)
def financial_dashboard(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
) -> FinancialDashboard:
    return get_financial_dashboard(db)


@router.get("/bi-foundation", response_model=BIFoundationDashboard)
def bi_foundation_dashboard(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
    months: int = Query(6, ge=3, le=12),
) -> BIFoundationDashboard:
    return get_bi_foundation_dashboard(db, months=months)


@router.get("/retention", response_model=RetentionDashboard)
def retention_dashboard(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST))],
    red_page: int = Query(1, ge=1),
    yellow_page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> RetentionDashboard:
    return get_retention_dashboard(db, red_page=red_page, yellow_page=yellow_page, page_size=page_size)


@router.get("/retention/queue", response_model=RetentionQueueResponse)
def retention_queue(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST))],
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    search: str | None = Query(None),
    level: Literal["all", "red", "yellow"] = Query("all"),
    churn_type: str | None = Query(None),
    plan_cycle: Literal["monthly", "semiannual", "annual"] | None = Query(None),
    preferred_shift: Literal["overnight", "morning", "afternoon", "evening"] | None = Query(None),
    retention_stage: Literal["monitoring", "attention", "recovery", "reactivation", "manager_escalation", "cold_base"] | None = Query(None),
) -> RetentionQueueResponse:
    return get_retention_queue(
        db,
        page=page,
        page_size=page_size,
        search=search,
        level=level,
        churn_type=churn_type,
        plan_cycle=plan_cycle,
        preferred_shift=preferred_shift,
        retention_stage=retention_stage,
    )


@router.get("/weekly-summary", response_model=WeeklySummary)
def weekly_summary(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
) -> WeeklySummary:
    return get_weekly_summary(db)


@router.get("/insights/executive", response_model=InsightResponse)
def executive_insight(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
) -> InsightResponse:
    dashboard_data = get_executive_dashboard(db)
    data_dict = dashboard_data.model_dump() if hasattr(dashboard_data, "model_dump") else dict(dashboard_data)
    insight_text = generate_executive_insight(data_dict)
    source = "ai" if settings.claude_api_key else "fallback"
    return InsightResponse(dashboard="executive", insight=insight_text, source=source)


@router.get("/insights/retention", response_model=InsightResponse)
def retention_insight(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
) -> InsightResponse:
    retention_data = get_retention_dashboard(db)
    # get_retention_dashboard() may return ORM objects nested inside dicts; normalize via schema validation.
    data_dict = RetentionDashboard.model_validate(retention_data).model_dump()
    insight_text = generate_retention_insight(data_dict)
    source = "ai" if settings.claude_api_key else "fallback"
    return InsightResponse(dashboard="retention", insight=insight_text, source=source)


@router.get("/insights/operational", response_model=InsightResponse)
def operational_insight(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
) -> InsightResponse:
    dashboard_data = get_operational_dashboard(db)
    data_dict = OperationalDashboard.model_validate(dashboard_data).model_dump()
    insight_text = generate_operational_insight(data_dict)
    source = "ai" if settings.claude_api_key else "fallback"
    return InsightResponse(dashboard="operational", insight=insight_text, source=source)


@router.get("/insights/commercial", response_model=InsightResponse)
def commercial_insight(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
) -> InsightResponse:
    dashboard_data = get_commercial_dashboard(db)
    data_dict = CommercialDashboard.model_validate(dashboard_data).model_dump()
    insight_text = generate_commercial_insight(data_dict)
    source = "ai" if settings.claude_api_key else "fallback"
    return InsightResponse(dashboard="commercial", insight=insight_text, source=source)


@router.get("/insights/financial", response_model=InsightResponse)
def financial_insight(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
) -> InsightResponse:
    dashboard_data = get_financial_dashboard(db)
    data_dict = FinancialDashboard.model_validate(dashboard_data).model_dump()
    insight_text = generate_financial_insight(data_dict)
    source = "ai" if settings.claude_api_key else "fallback"
    return InsightResponse(dashboard="financial", insight=insight_text, source=source)
