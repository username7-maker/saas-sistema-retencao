from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy import select

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.database import SessionLocal, clear_current_gym_id, set_current_gym_id
from app.models import Gym
from app.services.actuar_plan_shift_reconciliation_service import (
    apply_reconciliation,
    build_reconciliation_plan,
    rollback_reconciliation,
    write_dry_run_manifest,
    write_reconciliation_report,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Reconcilia planos e turnos com os dois exports Actuar aprovados. "
            "O modo padrao e dry-run e nunca grava no banco."
        )
    )
    parser.add_argument("--gym-slug", required=True, help="Slug exato da academia.")
    parser.add_argument("--clients-file", type=Path, help="Todos os Clientes.xlsx aprovado.")
    parser.add_argument("--access-file", type=Path, help="Acessos.xlsx aprovado.")
    parser.add_argument("--report", type=Path, help="CSV local do dry-run/apply.")
    parser.add_argument(
        "--reference-at",
        type=datetime.fromisoformat,
        default=None,
        help="Referencia ISO opcional; por padrao usa o acesso mais recente do export.",
    )
    parser.add_argument("--apply", action="store_true", help="Aplica somente as acoes de alta confianca.")
    parser.add_argument(
        "--approved-plan-digest",
        default=None,
        help="Digest exibido pelo dry-run revisado; obrigatorio com --apply.",
    )
    parser.add_argument("--rollback-batch", type=UUID, default=None, help="Reverte explicitamente um batch aplicado.")
    parser.add_argument(
        "--confirm-rollback",
        default=None,
        help="Para rollback, deve ser exatamente o UUID informado em --rollback-batch.",
    )
    return parser


def main() -> int:
    parser = _parser()
    args = parser.parse_args()
    if args.rollback_batch:
        if args.apply or args.clients_file or args.access_file or args.report:
            parser.error("--rollback-batch nao pode ser combinado com apply/arquivos/relatorio.")
        if args.confirm_rollback != str(args.rollback_batch):
            parser.error("Rollback exige --confirm-rollback com o UUID exato do lote.")
    else:
        if not args.clients_file or not args.access_file or not args.report:
            parser.error("--clients-file, --access-file e --report sao obrigatorios.")
        if args.apply and not args.approved_plan_digest:
            parser.error("--apply exige --approved-plan-digest gerado por um dry-run revisado.")
        if not args.apply and args.approved_plan_digest:
            parser.error("--approved-plan-digest so e aceito junto com --apply.")

    db = SessionLocal()
    try:
        gym = db.scalar(select(Gym).where(Gym.slug == args.gym_slug, Gym.is_active.is_(True)))
        if not gym:
            raise RuntimeError(f"Academia ativa nao encontrada: {args.gym_slug}")
        # Close the gym lookup transaction before opening the tenant-scoped unit of work.
        db.commit()
        set_current_gym_id(gym.id)

        if args.rollback_batch:
            result = rollback_reconciliation(db, gym_id=gym.id, batch_id=args.rollback_batch)
            db.commit()
            print(f"ROLLBACK_BATCH_ID={result.batch_id}")
            print(f"MEMBERS_RESTORED={result.members_updated}")
            print(f"PLANS_RESTORED={result.plans_updated}")
            print(f"SHIFTS_RESTORED={result.shifts_updated}")
            print(f"CHECKINS_REMOVED={-result.checkins_imported}")
            return 0

        plan = build_reconciliation_plan(
            db,
            gym_id=gym.id,
            clients_content=args.clients_file.read_bytes(),
            access_content=args.access_file.read_bytes(),
            clients_filename=args.clients_file.name,
            access_filename=args.access_file.name,
            reference_at=args.reference_at,
        )
        write_reconciliation_report(plan, args.report)
        manifest_path = args.report.with_suffix(args.report.suffix + ".manifest.json")
        write_dry_run_manifest(plan, manifest_path)

        print(f"MODE={'apply' if args.apply else 'dry-run'}")
        print(f"PLAN_DIGEST={plan.digest()}")
        print(f"REPORT={args.report.resolve()}")
        print(f"MANIFEST={manifest_path.resolve()}")
        for key, value in plan.stats.items():
            print(f"{key.upper()}={value}")

        if not args.apply:
            db.rollback()
            print("DATABASE_CHANGED=false")
            return 0

        result = apply_reconciliation(db, plan, approved_plan_digest=args.approved_plan_digest)
        db.commit()
        print("DATABASE_CHANGED=true")
        print(f"BATCH_ID={result.batch_id}")
        print(f"MEMBERS_UPDATED={result.members_updated}")
        print(f"PLANS_UPDATED={result.plans_updated}")
        print(f"SHIFTS_UPDATED={result.shifts_updated}")
        print(f"CHECKINS_IMPORTED={result.checkins_imported}")
        return 0
    except Exception:
        db.rollback()
        raise
    finally:
        clear_current_gym_id()
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
