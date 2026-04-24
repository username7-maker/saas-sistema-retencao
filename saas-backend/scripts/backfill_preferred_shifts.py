from __future__ import annotations

import argparse

from sqlalchemy import select

from app.database import SessionLocal, clear_current_gym_id, set_current_gym_id
from app.models import Gym
from app.services.preferred_shift_service import sync_preferred_shifts_from_checkins


def main() -> int:
    parser = argparse.ArgumentParser(description="Recalcula preferred_shift dos membros a partir do historico de check-ins.")
    parser.add_argument("--gym-slug", dest="gym_slug", default=None, help="Sincroniza apenas uma academia especifica.")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        query = select(Gym).where(Gym.is_active.is_(True))
        if args.gym_slug:
            query = query.where(Gym.slug == args.gym_slug)
        gyms = list(db.scalars(query).all())
        total_updated = 0
        for gym in gyms:
            set_current_gym_id(gym.id)
            updated = sync_preferred_shifts_from_checkins(db, gym_id=gym.id, commit=False, flush=False)
            db.commit()
            total_updated += updated
            print(f"{gym.slug}: {updated} membro(s) atualizado(s)")
        print(f"TOTAL_UPDATED={total_updated}")
        return 0
    finally:
        clear_current_gym_id()
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
