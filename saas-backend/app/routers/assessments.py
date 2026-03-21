from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_request_context, require_roles
from app.database import get_db
from app.models import RoleEnum, User
from app.schemas import PaginatedResponse
from app.schemas.assessment import (
    AssessmentActionOut,
    AssessmentBenchmarkOut,
    AssessmentCreate,
    AssessmentDashboardOut,
    AssessmentDiagnosisOut,
    AssessmentForecastOut,
    AssessmentMiniOut,
    AssessmentOut,
    AssessmentQueueItemOut,
    AssessmentSummary360Out,
    EvolutionOut,
    MemberConstraintsOut,
    MemberConstraintsUpsert,
    MemberGoalCreate,
    MemberGoalOut,
    MemberMiniOut,
    Profile360Out,
    TrainingPlanCreate,
    TrainingPlanOut,
)
from app.services.assessment_analytics_service import get_assessments_dashboard, get_assessments_queue
from app.services.assessment_goals_service import (
    create_goal,
    create_training_plan,
    list_goals,
    update_goal,
    update_training_plan,
    upsert_constraints,
)
from app.services.assessment_intelligence_service import (
    get_assessment_actions,
    get_assessment_benchmark,
    get_assessment_diagnosis,
    get_assessment_forecast,
    get_assessment_summary_360,
)
from app.services.ai_assistant_service import build_assessment_assistant
from app.services.assessment_service import (
    create_assessment,
    get_evolution_data,
    get_member_profile_360,
    list_assessments,
)
from app.services.audit_service import log_audit_event


router = APIRouter(prefix="/assessments", tags=["assessments"])


@router.get("/dashboard", response_model=AssessmentDashboardOut)
def assessments_dashboard_endpoint(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST))],
) -> AssessmentDashboardOut:
    payload = get_assessments_dashboard(db)
    return AssessmentDashboardOut(
        total_members=payload["total_members"],
        assessed_last_90_days=payload["assessed_last_90_days"],
        overdue_assessments=payload["overdue_assessments"],
        never_assessed=payload["never_assessed"],
        upcoming_7_days=payload["upcoming_7_days"],
        attention_now=[AssessmentQueueItemOut.model_validate(item) for item in payload.get("attention_now", [])],
        total_members_items=[MemberMiniOut.model_validate(item) for item in payload.get("total_members_items", [])],
        assessed_members=[MemberMiniOut.model_validate(item) for item in payload.get("assessed_members", [])],
        overdue_members=[MemberMiniOut.model_validate(item) for item in payload["overdue_members"]],
        never_assessed_members=[MemberMiniOut.model_validate(item) for item in payload.get("never_assessed_members", [])],
        upcoming_members=[MemberMiniOut.model_validate(item) for item in payload.get("upcoming_members", [])],
    )


@router.get("/queue", response_model=PaginatedResponse[AssessmentQueueItemOut])
def assessments_queue_endpoint(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST))],
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    search: str | None = Query(default=None),
    bucket: Literal["all", "overdue", "never", "week", "upcoming", "covered"] = Query(default="all"),
) -> PaginatedResponse[AssessmentQueueItemOut]:
    return get_assessments_queue(
        db,
        page=page,
        page_size=page_size,
        search=search,
        bucket=bucket,
    )


@router.get("/members/{member_id}/profile", response_model=Profile360Out)
def member_profile_360_endpoint(
    member_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.SALESPERSON))],
) -> Profile360Out:
    payload = get_member_profile_360(db, member_id)
    latest_assessment = payload.get("latest_assessment")
    constraints = payload.get("constraints")
    active_training_plan = payload.get("active_training_plan")

    return Profile360Out(
        member=MemberMiniOut.model_validate(payload["member"]),
        latest_assessment=AssessmentMiniOut.model_validate(latest_assessment) if latest_assessment else None,
        constraints=MemberConstraintsOut.model_validate(constraints) if constraints else None,
        goals=[MemberGoalOut.model_validate(item) for item in payload.get("goals", [])],
        active_training_plan=TrainingPlanOut.model_validate(active_training_plan) if active_training_plan else None,
        insight_summary=payload.get("insight_summary"),
    )


@router.get("/members/{member_id}/summary-360", response_model=AssessmentSummary360Out)
def assessment_summary_360_endpoint(
    member_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.SALESPERSON))],
) -> AssessmentSummary360Out:
    payload = get_assessment_summary_360(db, member_id)
    return AssessmentSummary360Out(
        member=MemberMiniOut.model_validate(payload["member"]),
        latest_assessment=AssessmentMiniOut.model_validate(payload["latest_assessment"]) if payload.get("latest_assessment") else None,
        goal_type=payload["goal_type"],
        status=payload["status"],
        days_since_last_checkin=payload["days_since_last_checkin"],
        recent_weekly_checkins=payload["recent_weekly_checkins"],
        target_frequency_per_week=payload["target_frequency_per_week"],
        forecast=AssessmentForecastOut.model_validate(payload["forecast"]),
        diagnosis=AssessmentDiagnosisOut.model_validate(payload["diagnosis"]),
        benchmark=AssessmentBenchmarkOut.model_validate(payload["benchmark"]),
        narratives=payload["narratives"],
        next_best_action=AssessmentActionOut.model_validate(payload["next_best_action"]),
        actions=[AssessmentActionOut.model_validate(item) for item in payload["actions"]],
        assistant=build_assessment_assistant(payload),
    )


@router.get("/members/{member_id}/diagnosis", response_model=AssessmentDiagnosisOut)
def member_assessment_diagnosis_endpoint(
    member_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.SALESPERSON))],
) -> AssessmentDiagnosisOut:
    return AssessmentDiagnosisOut.model_validate(get_assessment_diagnosis(db, member_id))


@router.get("/members/{member_id}/forecast", response_model=AssessmentForecastOut)
def member_assessment_forecast_endpoint(
    member_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.SALESPERSON))],
) -> AssessmentForecastOut:
    return AssessmentForecastOut.model_validate(get_assessment_forecast(db, member_id))


@router.get("/members/{member_id}/benchmark", response_model=AssessmentBenchmarkOut)
def member_assessment_benchmark_endpoint(
    member_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.SALESPERSON))],
) -> AssessmentBenchmarkOut:
    return AssessmentBenchmarkOut.model_validate(get_assessment_benchmark(db, member_id))


@router.get("/members/{member_id}/actions", response_model=list[AssessmentActionOut])
def member_assessment_actions_endpoint(
    member_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.SALESPERSON))],
) -> list[AssessmentActionOut]:
    return [AssessmentActionOut.model_validate(item) for item in get_assessment_actions(db, member_id)]


@router.post("/members/{member_id}", response_model=AssessmentOut, status_code=status.HTTP_201_CREATED)
def create_assessment_endpoint(
    request: Request,
    member_id: UUID,
    payload: AssessmentCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
) -> AssessmentOut:
    assessment = create_assessment(db, member_id, current_user.id, payload.model_dump(exclude_unset=True))
    context = get_request_context(request)
    log_audit_event(
        db,
        action="assessment_created",
        entity="assessment",
        user=current_user,
        member_id=member_id,
        entity_id=assessment.id,
        details={"assessment_number": assessment.assessment_number},
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    return AssessmentOut.model_validate(assessment)


@router.get("/members/{member_id}", response_model=list[AssessmentOut])
def list_assessments_endpoint(
    member_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.SALESPERSON))],
) -> list[AssessmentOut]:
    return [AssessmentOut.model_validate(item) for item in list_assessments(db, member_id)]


@router.get("/members/{member_id}/evolution", response_model=EvolutionOut)
def member_evolution_endpoint(
    member_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.SALESPERSON))],
) -> EvolutionOut:
    return EvolutionOut.model_validate(get_evolution_data(db, member_id))


@router.put("/members/{member_id}/constraints", response_model=MemberConstraintsOut)
def upsert_constraints_endpoint(
    request: Request,
    member_id: UUID,
    payload: MemberConstraintsUpsert,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
) -> MemberConstraintsOut:
    constraints = upsert_constraints(db, member_id, payload.model_dump(exclude_unset=True))
    context = get_request_context(request)
    log_audit_event(
        db,
        action="member_constraints_upserted",
        entity="member_constraints",
        user=current_user,
        member_id=member_id,
        entity_id=constraints.id,
        details={"updated_fields": list(payload.model_dump(exclude_unset=True).keys())},
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    return MemberConstraintsOut.model_validate(constraints)


@router.post("/members/{member_id}/goals", response_model=MemberGoalOut, status_code=status.HTTP_201_CREATED)
def create_member_goal_endpoint(
    request: Request,
    member_id: UUID,
    payload: MemberGoalCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
) -> MemberGoalOut:
    goal = create_goal(db, member_id, payload.model_dump(exclude_unset=True))
    context = get_request_context(request)
    log_audit_event(
        db,
        action="member_goal_created",
        entity="member_goal",
        user=current_user,
        member_id=member_id,
        entity_id=goal.id,
        details={"title": goal.title, "target_date": str(goal.target_date) if goal.target_date else None},
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    return MemberGoalOut.model_validate(goal)


@router.get("/members/{member_id}/goals", response_model=list[MemberGoalOut])
def list_member_goals_endpoint(
    member_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.SALESPERSON))],
) -> list[MemberGoalOut]:
    return [MemberGoalOut.model_validate(item) for item in list_goals(db, member_id)]


@router.put("/members/{member_id}/goals/{goal_id}", response_model=MemberGoalOut)
def update_member_goal_endpoint(
    request: Request,
    member_id: UUID,
    goal_id: UUID,
    payload: MemberGoalCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
) -> MemberGoalOut:
    goal = update_goal(db, member_id, goal_id, payload.model_dump(exclude_unset=True))
    context = get_request_context(request)
    log_audit_event(
        db,
        action="member_goal_updated",
        entity="member_goal",
        user=current_user,
        member_id=member_id,
        entity_id=goal.id,
        details={"title": goal.title, "target_date": str(goal.target_date) if goal.target_date else None},
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    return MemberGoalOut.model_validate(goal)


@router.post("/members/{member_id}/training-plans", response_model=TrainingPlanOut, status_code=status.HTTP_201_CREATED)
def create_training_plan_endpoint(
    request: Request,
    member_id: UUID,
    payload: TrainingPlanCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
) -> TrainingPlanOut:
    plan = create_training_plan(db, member_id, current_user.id, payload.model_dump(exclude_unset=True))
    context = get_request_context(request)
    log_audit_event(
        db,
        action="training_plan_created",
        entity="training_plan",
        user=current_user,
        member_id=member_id,
        entity_id=plan.id,
        details={"name": plan.name, "sessions_per_week": plan.sessions_per_week},
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    return TrainingPlanOut.model_validate(plan)


@router.put("/members/{member_id}/training-plans/{plan_id}", response_model=TrainingPlanOut)
def update_training_plan_endpoint(
    request: Request,
    member_id: UUID,
    plan_id: UUID,
    payload: TrainingPlanCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
) -> TrainingPlanOut:
    plan = update_training_plan(db, member_id, plan_id, current_user.id, payload.model_dump(exclude_unset=True))
    context = get_request_context(request)
    log_audit_event(
        db,
        action="training_plan_updated",
        entity="training_plan",
        user=current_user,
        member_id=member_id,
        entity_id=plan.id,
        details={"name": plan.name, "sessions_per_week": plan.sessions_per_week},
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    return TrainingPlanOut.model_validate(plan)
