from __future__ import annotations

import argparse
import json
import pathlib
import sys
from datetime import date, datetime, timezone
from decimal import Decimal

BACKEND_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import select

from app.database import SessionLocal, include_all_tenants, set_current_gym_id, clear_current_gym_id
from app.models import BodyCompositionEvaluation, Gym, Member, User
from app.schemas import MemberCreate
from app.schemas.body_composition import BodyCompositionEvaluationCreate
from app.services.body_composition_service import create_body_composition_evaluation
from app.services.member_service import create_member


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed premium report validation data in the target tenant.")
    parser.add_argument("--gym-slug", required=True)
    parser.add_argument("--owner-email", required=True)
    return parser.parse_args()


def _upsert_member(db, gym_id, payload: MemberCreate) -> Member:
    existing = db.scalar(
        include_all_tenants(
            select(Member).where(
                Member.gym_id == gym_id,
                Member.email == payload.email,
                Member.deleted_at.is_(None),
            ),
            reason="member_service.seed_validation_lookup",
        )
    )
    if existing:
        existing.full_name = payload.full_name
        existing.phone = payload.phone
        existing.plan_name = payload.plan_name
        existing.monthly_fee = payload.monthly_fee
        existing.join_date = payload.join_date
        existing.loyalty_months = payload.loyalty_months
        db.add(existing)
        db.flush()
        db.refresh(existing)
        return existing
    return create_member(db, payload, gym_id=gym_id, commit=False)


def _replace_validation_evaluations(db, *, gym_id, owner_id, member_id) -> dict[str, BodyCompositionEvaluation]:
    existing = db.scalars(
        select(BodyCompositionEvaluation).where(
            BodyCompositionEvaluation.gym_id == gym_id,
            BodyCompositionEvaluation.member_id == member_id,
        )
    ).all()
    for evaluation in existing:
        db.delete(evaluation)
    db.flush()

    previous_payload = BodyCompositionEvaluationCreate(
        evaluation_date=date(2026, 3, 10),
        measured_at=datetime(2026, 3, 10, 9, 30, tzinfo=timezone.utc),
        age_years=31,
        sex="female",
        height_cm=168,
        weight_kg=74.3,
        body_fat_kg=22.4,
        body_fat_percent=30.1,
        waist_hip_ratio=0.86,
        fat_free_mass_kg=51.9,
        inorganic_salt_kg=3.2,
        protein_kg=11.0,
        body_water_kg=38.5,
        lean_mass_kg=51.9,
        muscle_mass_kg=27.4,
        skeletal_muscle_kg=25.6,
        body_water_percent=51.8,
        visceral_fat_level=10,
        bmi=26.3,
        basal_metabolic_rate_kcal=1450,
        target_weight_kg=68.5,
        weight_control_kg=-5.8,
        muscle_control_kg=0.8,
        fat_control_kg=-6.6,
        total_energy_kcal=2140,
        physical_age=34,
        health_score=71,
        source="manual",
        notes="Linha de base da validacao premium.",
        reviewed_manually=True,
        needs_review=False,
    )
    current_payload = BodyCompositionEvaluationCreate(
        evaluation_date=date(2026, 4, 16),
        measured_at=datetime(2026, 4, 16, 9, 30, tzinfo=timezone.utc),
        age_years=31,
        sex="female",
        height_cm=168,
        weight_kg=71.8,
        body_fat_kg=19.6,
        body_fat_percent=27.3,
        waist_hip_ratio=0.83,
        fat_free_mass_kg=52.2,
        inorganic_salt_kg=3.3,
        protein_kg=11.1,
        body_water_kg=39.1,
        lean_mass_kg=52.2,
        muscle_mass_kg=28.0,
        skeletal_muscle_kg=26.1,
        body_water_percent=54.4,
        visceral_fat_level=8,
        bmi=25.4,
        basal_metabolic_rate_kcal=1488,
        target_weight_kg=68.5,
        weight_control_kg=-3.3,
        muscle_control_kg=0.5,
        fat_control_kg=-3.8,
        total_energy_kcal=2205,
        physical_age=30,
        health_score=78,
        source="manual",
        notes="Melhora de gordura corporal com preservacao de massa magra.",
        reviewed_manually=True,
        needs_review=False,
    )

    previous_evaluation, _ = create_body_composition_evaluation(
        db,
        gym_id=gym_id,
        member_id=member_id,
        payload=previous_payload,
        reviewer_user_id=owner_id,
    )
    current_evaluation, _ = create_body_composition_evaluation(
        db,
        gym_id=gym_id,
        member_id=member_id,
        payload=current_payload,
        reviewer_user_id=owner_id,
    )
    db.flush()
    return {"previous": previous_evaluation, "current": current_evaluation}


def main() -> None:
    args = _parse_args()
    with SessionLocal() as db:
        gym = db.scalar(select(Gym).where(Gym.slug == args.gym_slug, Gym.is_active.is_(True)))
        if gym is None:
            raise SystemExit(f"Gym not found for slug: {args.gym_slug}")

        owner = db.scalar(
            include_all_tenants(
                select(User).where(
                    User.gym_id == gym.id,
                    User.email == args.owner_email,
                    User.deleted_at.is_(None),
                ),
                reason="auth.seed_validation_owner_lookup",
            )
        )
        if owner is None:
            raise SystemExit(f"Owner not found for email: {args.owner_email}")

        set_current_gym_id(gym.id)
        try:
            members = [
                MemberCreate(
                    full_name="Alice Premium Validation",
                    email="alice.premium.validation@example.com",
                    phone="5511999000001",
                    plan_name="Plano Premium",
                    monthly_fee=Decimal("199.90"),
                    join_date=date(2026, 1, 15),
                    loyalty_months=3,
                ),
                MemberCreate(
                    full_name="Bruno Premium Validation",
                    email="bruno.premium.validation@example.com",
                    phone="5511999000002",
                    plan_name="Plano Premium",
                    monthly_fee=Decimal("229.90"),
                    join_date=date(2026, 2, 10),
                    loyalty_months=2,
                ),
                MemberCreate(
                    full_name="Carla Premium Validation",
                    email="carla.premium.validation@example.com",
                    phone="5511999000003",
                    plan_name="Plano Base",
                    monthly_fee=Decimal("179.90"),
                    join_date=date(2026, 3, 5),
                    loyalty_months=1,
                ),
            ]

            created_members = [_upsert_member(db, gym.id, payload) for payload in members]
            evaluation_bundle = _replace_validation_evaluations(
                db,
                gym_id=gym.id,
                owner_id=owner.id,
                member_id=created_members[0].id,
            )
            db.commit()
        finally:
            clear_current_gym_id()

        output = {
            "gym_id": str(gym.id),
            "gym_slug": gym.slug,
            "owner_id": str(owner.id),
            "owner_email": owner.email,
            "members": [
                {"id": str(member.id), "full_name": member.full_name, "email": member.email}
                for member in created_members
            ],
            "primary_member": {
                "id": str(created_members[0].id),
                "full_name": created_members[0].full_name,
                "email": created_members[0].email,
            },
            "evaluations": {
                "previous": {
                    "id": str(evaluation_bundle["previous"].id),
                    "evaluation_date": evaluation_bundle["previous"].evaluation_date.isoformat(),
                },
                "current": {
                    "id": str(evaluation_bundle["current"].id),
                    "evaluation_date": evaluation_bundle["current"].evaluation_date.isoformat(),
                },
            },
        }
        print(json.dumps(output))


if __name__ == "__main__":
    main()
