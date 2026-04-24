from __future__ import annotations

import argparse
from datetime import datetime, timezone

from sqlalchemy import select

from app.database import SessionLocal, clear_current_gym_id, set_current_gym_id
from app.models import AITriageRecommendation, Gym, Member, Task


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


def _clean_metadata(metadata: dict | None) -> dict:
    if not metadata:
        return {}
    keys_to_drop = {
        "prepared_action",
        "prepared_task_id",
        "prepared_at",
        "prepared_by_user_id",
        "follow_up_url",
        "last_action_note",
        "last_outcome_note",
        "last_outcome_recorded_at",
        "last_outcome_recorded_by_user_id",
    }
    return {key: value for key, value in metadata.items() if key not in keys_to_drop}


def main() -> None:
    parser = argparse.ArgumentParser(description="Reset the controlled Wave 4 AI triage sample to pending state.")
    parser.add_argument("--gym-slug", default="ai-gym-os-piloto")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        gym = db.scalar(select(Gym).where(Gym.slug == args.gym_slug))
        if gym is None:
            raise SystemExit(f"Gym slug not found: {args.gym_slug}")
        set_current_gym_id(gym.id)

        members = db.scalars(
            select(Member).where(
                Member.gym_id == gym.id,
                Member.full_name.in_(("Wave 4 Retention Member", "Wave 4 Onboarding Member")),
                Member.deleted_at.is_(None),
            )
        ).all()
        member_ids = [member.id for member in members]
        if not member_ids:
            raise SystemExit("Wave 4 validation members not found.")

        recommendations = db.scalars(
            select(AITriageRecommendation).where(
                AITriageRecommendation.gym_id == gym.id,
                AITriageRecommendation.member_id.in_(member_ids),
                AITriageRecommendation.is_active.is_(True),
            )
        ).all()
        for recommendation in recommendations:
            snapshot = dict(recommendation.payload_snapshot or {})
            snapshot["metadata"] = _clean_metadata(dict(snapshot.get("metadata") or {}))
            recommendation.payload_snapshot = snapshot
            recommendation.suggestion_state = "suggested"
            recommendation.approval_state = "pending"
            recommendation.execution_state = "pending"
            recommendation.outcome_state = "pending"
            recommendation.last_refreshed_at = _utcnow()
            db.add(recommendation)

        tasks = db.scalars(
            select(Task).where(
                Task.member_id.in_(member_ids),
                Task.deleted_at.is_(None),
                Task.extra_data["source"].astext == "ai_triage",
            )
        ).all()
        for task in tasks:
            task.deleted_at = _utcnow()
            db.add(task)

        db.commit()
        print(
            {
                "gym_slug": args.gym_slug,
                "members_reset": len(member_ids),
                "recommendations_reset": len(recommendations),
                "tasks_soft_deleted": len(tasks),
            }
        )
    finally:
        clear_current_gym_id()
        db.close()


if __name__ == "__main__":
    main()
