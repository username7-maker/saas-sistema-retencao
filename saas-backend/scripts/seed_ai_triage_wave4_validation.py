from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

from sqlalchemy import select

from app.core.security import hash_password
from app.database import SessionLocal, clear_current_gym_id, set_current_gym_id
from app.models import AITriageRecommendation, Gym, Member, MemberStatus, RiskAlert, RiskLevel, RoleEnum, User
from app.services.ai_triage_service import list_ai_triage_recommendations, sync_ai_triage_recommendations


DEFAULT_EMAIL = "ai-triage-validation@automai.com"
DEFAULT_PASSWORD = "Validacao!2026"
DEFAULT_FULL_NAME = "AI Triage Validation Operator"


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


@dataclass
class SeedState:
    gym_slug: str
    user_email: str
    password: str
    retention_member_id: str
    onboarding_member_id: str
    recommendation_ids: list[str]


def _load_gym(db, gym_slug: str) -> Gym:
    gym = db.scalar(select(Gym).where(Gym.slug == gym_slug))
    if gym is None:
        raise SystemExit(f"Gym slug not found: {gym_slug}")
    return gym


def _get_or_create_user(db, *, gym_id: UUID, email: str, password: str) -> User:
    user = db.scalar(select(User).where(User.gym_id == gym_id, User.email == email))
    if user is None:
        user = User(
            gym_id=gym_id,
            full_name=DEFAULT_FULL_NAME,
            email=email,
            hashed_password=hash_password(password),
            role=RoleEnum.MANAGER,
            is_active=True,
        )
        db.add(user)
        db.flush()
        return user

    user.full_name = DEFAULT_FULL_NAME
    user.role = RoleEnum.MANAGER
    user.is_active = True
    user.hashed_password = hash_password(password)
    db.add(user)
    db.flush()
    return user


def _get_or_create_member(db, *, gym_id: UUID, full_name: str) -> Member:
    member = db.scalar(select(Member).where(Member.gym_id == gym_id, Member.full_name == full_name, Member.deleted_at.is_(None)))
    if member is None:
        member = Member(
            gym_id=gym_id,
            full_name=full_name,
            plan_name="Plano Base",
            monthly_fee=199,
            status=MemberStatus.ACTIVE,
            join_date=date.today(),
            onboarding_status="active",
            onboarding_score=0,
            risk_score=0,
            risk_level=RiskLevel.GREEN,
        )
        db.add(member)
        db.flush()
    return member


def _ensure_retention_member(db, *, gym: Gym, user: User) -> Member:
    member = _get_or_create_member(db, gym_id=gym.id, full_name="Wave 4 Retention Member")
    member.assigned_user_id = user.id
    member.email = "wave4-retention@automai.com"
    member.phone = "5511999991111"
    member.plan_name = "Plano Anual"
    member.monthly_fee = 249
    member.join_date = date.today() - timedelta(days=120)
    member.onboarding_status = "completed"
    member.onboarding_score = 88
    member.risk_score = 92
    member.risk_level = RiskLevel.RED
    member.nps_last_score = 4
    member.last_checkin_at = _utcnow() - timedelta(days=17)
    member.loyalty_months = 4
    member.churn_type = "disengagement"
    member.extra_data = {
        "wave4_validation": True,
        "seeded_at": _utcnow().isoformat(),
    }
    db.add(member)
    db.flush()

    alert = db.scalar(
        select(RiskAlert)
        .where(
            RiskAlert.gym_id == gym.id,
            RiskAlert.member_id == member.id,
            RiskAlert.resolved.is_(False),
        )
        .order_by(RiskAlert.created_at.desc())
    )
    if alert is None:
        alert = RiskAlert(
            gym_id=gym.id,
            member_id=member.id,
            score=92,
            level=RiskLevel.RED,
            reasons={
                "days_without_checkin": 17,
                "nps_last_score": 4,
                "forecast_60d": 28,
            },
            action_history=[],
            automation_stage="manual_follow_up",
            resolved=False,
        )
        db.add(alert)
    else:
        alert.score = 92
        alert.level = RiskLevel.RED
        alert.reasons = {
            "days_without_checkin": 17,
            "nps_last_score": 4,
            "forecast_60d": 28,
        }
        alert.automation_stage = "manual_follow_up"
        alert.resolved = False
        db.add(alert)

    db.flush()
    return member


def _ensure_onboarding_member(db, *, gym: Gym, user: User) -> Member:
    member = _get_or_create_member(db, gym_id=gym.id, full_name="Wave 4 Onboarding Member")
    member.assigned_user_id = user.id
    member.email = "wave4-onboarding@automai.com"
    member.phone = "5511999992222"
    member.plan_name = "Plano Start"
    member.monthly_fee = 149
    member.join_date = date.today() - timedelta(days=5)
    member.onboarding_status = "at_risk"
    member.onboarding_score = 23
    member.risk_score = 38
    member.risk_level = RiskLevel.YELLOW
    member.nps_last_score = 0
    member.last_checkin_at = _utcnow() - timedelta(days=3)
    member.loyalty_months = 0
    member.extra_data = {
        "wave4_validation": True,
        "seeded_at": _utcnow().isoformat(),
    }
    db.add(member)
    db.flush()
    return member


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed a controlled pilot sample for 4.43 Wave 4 validation.")
    parser.add_argument("--gym-slug", default="ai-gym-os-piloto")
    parser.add_argument("--email", default=DEFAULT_EMAIL)
    parser.add_argument("--password", default=DEFAULT_PASSWORD)
    parser.add_argument("--output", required=True, help="Path to write the validation state JSON.")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        gym = _load_gym(db, args.gym_slug)
        set_current_gym_id(gym.id)
        user = _get_or_create_user(db, gym_id=gym.id, email=args.email, password=args.password)
        retention_member = _ensure_retention_member(db, gym=gym, user=user)
        onboarding_member = _ensure_onboarding_member(db, gym=gym, user=user)

        sync_ai_triage_recommendations(db, gym_id=gym.id)
        db.commit()

        items = list_ai_triage_recommendations(db, gym_id=gym.id, page=1, page_size=20).items
        recommendation_ids = [str(item.id) for item in items if item.subject_name in {retention_member.full_name, onboarding_member.full_name}]

        payload = {
            "created_at": _utcnow().isoformat(),
            "gym_slug": args.gym_slug,
            "credentials": {
                "gym_slug": args.gym_slug,
                "email": args.email,
                "password": args.password,
            },
            "members": {
                "retention": {
                    "id": str(retention_member.id),
                    "full_name": retention_member.full_name,
                },
                "onboarding": {
                    "id": str(onboarding_member.id),
                    "full_name": onboarding_member.full_name,
                },
            },
            "recommendation_ids": recommendation_ids,
        }

        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(json.dumps(payload, indent=2))
    finally:
        clear_current_gym_id()
        db.close()


if __name__ == "__main__":
    main()
