from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from sqlalchemy import select

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.database import SessionLocal, clear_current_gym_id, set_current_gym_id  # noqa: E402
from app.models import Gym  # noqa: E402
from app.services.database_storage_audit_service import build_database_storage_audit  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Auditoria somente leitura do uso do PostgreSQL e de candidatos seguros a limpeza."
    )
    parser.add_argument("--gym-slug", required=True, help="Slug exato da academia.")
    parser.add_argument("--report", required=True, type=Path, help="Destino JSON do relatorio.")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        gym = db.scalar(select(Gym).where(Gym.slug == args.gym_slug, Gym.is_active.is_(True)))
        if gym is None:
            raise RuntimeError(f"Academia ativa nao encontrada: {args.gym_slug}")
        db.commit()
        set_current_gym_id(gym.id)
        audit = build_database_storage_audit(db, gym_id=gym.id)
        db.rollback()
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(audit.as_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        print("MODE=read-only")  # noqa: T201
        print("DATABASE_CHANGED=false")  # noqa: T201
        print(f"AUDIT_DIGEST={audit.digest()}")  # noqa: T201
        print(f"REPORT={args.report.resolve()}")  # noqa: T201
        return 0
    finally:
        clear_current_gym_id()
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())

