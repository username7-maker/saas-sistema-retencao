from collections import Counter
import os

from sqlalchemy import select

from app.database import SessionLocal, clear_current_gym_id, set_current_gym_id
from app.models import Gym, Member
from app.services.import_service import refresh_member_plan_metadata


GYM_SLUG = os.getenv("GYM_SLUG", "academia-principal")


def main() -> None:
    db = SessionLocal()
    try:
        gym = db.scalar(select(Gym).where(Gym.slug == GYM_SLUG, Gym.is_active.is_(True)))
        if not gym:
            raise RuntimeError(f"Gym nao encontrada: {GYM_SLUG}")

        set_current_gym_id(gym.id)
        updated = refresh_member_plan_metadata(db, gym_id=gym.id)

        members = list(db.scalars(select(Member).where(Member.gym_id == gym.id, Member.deleted_at.is_(None))).all())
        counts = Counter(str((member.extra_data or {}).get("plan_cycle") or "unknown") for member in members)

        print(f"gym_slug={GYM_SLUG}")
        print(f"updated={updated}")
        for cycle in ("monthly", "semiannual", "annual", "unknown"):
            print(f"{cycle}={counts.get(cycle, 0)}")
    finally:
        clear_current_gym_id()
        db.close()


if __name__ == "__main__":
    main()
