from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dependencies import require_roles
from app.database import get_db
from app.models import RoleEnum, User
from app.schemas import (
    ChurnPoint,
    CommercialDashboard,
    ExecutiveDashboard,
    FinancialDashboard,
    GrowthPoint,
    LTVPoint,
    OperationalDashboard,
    RetentionDashboard,
    RevenuePoint,
)
from app.schemas.insights import InsightResponse
from app.services.ai_insight_service import generate_executive_insight, generate_retention_insight
from app.services.dashboard_service import (
    get_churn_dashboard,
    get_commercial_dashboard,
    get_executive_dashboard,
    get_financial_dashboard,
    get_growth_mom_dashboard,
    get_ltv_dashboard,
    get_mrr_dashboard,
    get_operational_dashboard,
    get_retention_dashboard,
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


@router.get("/retention", response_model=RetentionDashboard)
def retention_dashboard(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST))],
    red_page: int = Query(1, ge=1),
    yellow_page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> RetentionDashboard:
    return get_retention_dashboard(db, red_page=red_page, yellow_page=yellow_page, page_size=page_size)


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
