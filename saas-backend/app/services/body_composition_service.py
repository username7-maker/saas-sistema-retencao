from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.body_composition import BodyCompositionEvaluation
from app.schemas.body_composition import BodyCompositionEvaluationCreate
from app.services.member_service import get_member_or_404


def create_body_composition_evaluation(
    db: Session,
    gym_id: UUID,
    member_id: UUID,
    payload: BodyCompositionEvaluationCreate,
) -> BodyCompositionEvaluation:
    get_member_or_404(db, member_id)
    evaluation = BodyCompositionEvaluation(
        gym_id=gym_id,
        member_id=member_id,
        **payload.model_dump(),
    )
    db.add(evaluation)
    db.flush()
    return evaluation


def list_body_composition_evaluations(
    db: Session,
    gym_id: UUID,
    member_id: UUID,
    limit: int = 20,
) -> list[BodyCompositionEvaluation]:
    return list(
        db.scalars(
            select(BodyCompositionEvaluation)
            .where(
                BodyCompositionEvaluation.gym_id == gym_id,
                BodyCompositionEvaluation.member_id == member_id,
            )
            .order_by(BodyCompositionEvaluation.evaluation_date.desc())
            .limit(limit)
        ).all()
    )
