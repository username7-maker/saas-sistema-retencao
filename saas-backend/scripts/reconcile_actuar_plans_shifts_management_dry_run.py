from __future__ import annotations

# ruff: noqa: E402, S608, T201 -- CLI bootstrap, fixed management queries and CLI output.
import argparse
import json
import os
import sys
from collections import Counter
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen
from uuid import UUID, uuid4

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.models import Member
from app.services import actuar_plan_shift_reconciliation_service as reconciliation
from app.utils.encryption import decrypt_pii


class _ScalarRows:
    def __init__(self, rows: list[Member]) -> None:
        self._rows = rows

    def all(self) -> list[Member]:
        return self._rows


class _ReadOnlyMemberSession:
    def __init__(self, members: list[Member]) -> None:
        self._members = members

    def scalars(self, _statement: object) -> _ScalarRows:
        return _ScalarRows(self._members)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Dry-run Actuar via Supabase Management API; nunca grava no banco.",
    )
    parser.add_argument("--project-ref", required=True)
    parser.add_argument("--gym-slug", required=True)
    parser.add_argument("--clients-file", type=Path, required=True)
    parser.add_argument("--access-file", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--validate-apply", action="store_true")
    parser.add_argument("--approved-plan-digest")
    return parser


def _query(project_ref: str, sql: str) -> list[dict[str, Any]]:
    token = os.environ.get("SUPABASE_ACCESS_TOKEN", "").strip()
    if not token:
        raise RuntimeError("SUPABASE_ACCESS_TOKEN ausente.")
    request = Request(
        f"https://api.supabase.com/v1/projects/{project_ref}/database/query",
        data=json.dumps({"query": sql}).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "SupabaseCLI/management-dry-run",
        },
        method="POST",
    )
    with urlopen(request, timeout=120) as response:  # noqa: S310 - fixed Supabase endpoint
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, list):
        raise RuntimeError("Resposta inesperada da API de gestao do Supabase.")
    return payload


def _sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _member_from_row(row: dict[str, Any]) -> Member:
    phone = row.get("phone")
    if phone:
        try:
            phone = decrypt_pii(str(phone))
        except Exception:
            phone = str(phone)
    return Member(
        id=UUID(str(row["id"])),
        gym_id=UUID(str(row["gym_id"])),
        full_name=str(row.get("full_name") or ""),
        email=row.get("email"),
        phone=phone,
        cpf_encrypted=row.get("cpf_encrypted"),
        plan_name=str(row.get("plan_name") or "Plano Base"),
        preferred_shift=row.get("preferred_shift"),
        extra_data=row.get("extra_data") or {},
        join_date=date.fromisoformat(str(row["join_date"])),
    )


def _parse_db_datetime(value: Any) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _apply_plan(
    project_ref: str,
    plan: reconciliation.ReconciliationPlan,
    *,
    approved_digest: str,
    commit: bool,
) -> dict[str, Any]:
    actual_digest = plan.digest()
    if approved_digest.strip().upper() != actual_digest:
        raise RuntimeError("Digest aprovado nao corresponde ao dry-run atual.")
    batch_id = uuid4()
    changes_json = json.dumps(
        [
            {
                "member_id": str(item.member_id),
                "plan_before": item.plan_before,
                "plan_after": item.plan_after,
                "shift_before": item.shift_before,
                "shift_after": item.shift_after,
                "plan_cycle_before": item.plan_cycle_before,
                "plan_cycle_after": item.plan_cycle_after,
                "plan_cycle_source_before": item.plan_cycle_source_before,
                "plan_cycle_source_after": item.plan_cycle_source_after,
            }
            for item in plan.changes
        ],
        separators=(",", ":"),
    )
    checkins_json = json.dumps(
        [
            {
                "member_id": str(item.member_id),
                "checkin_at": reconciliation._utc_datetime(item.checkin_at).isoformat(),
                "hour_bucket": item.hour_bucket,
                "weekday": item.weekday,
            }
            for item in plan.checkins
        ],
        separators=(",", ":"),
    )
    stats_json = json.dumps(plan.stats, separators=(",", ":"))
    finish = "COMMIT" if commit else "ROLLBACK"
    sql = f"""
BEGIN;
SELECT pg_advisory_xact_lock(hashtext('actuar_plan_shift_reconciliation'));
CREATE TEMP TABLE codex_changes ON COMMIT DROP AS
SELECT * FROM jsonb_to_recordset({_sql_literal(changes_json)}::jsonb) AS x(
  member_id uuid, plan_before text, plan_after text,
  shift_before text, shift_after text,
  plan_cycle_before text, plan_cycle_after text,
  plan_cycle_source_before text, plan_cycle_source_after text
);
CREATE TEMP TABLE codex_checkins ON COMMIT DROP AS
SELECT * FROM jsonb_to_recordset({_sql_literal(checkins_json)}::jsonb) AS x(
  member_id uuid, checkin_at timestamptz, hour_bucket smallint, weekday smallint
);
DO $guard$
BEGIN
  IF EXISTS (
    SELECT 1 FROM codex_changes c
    LEFT JOIN public.members m ON m.id=c.member_id AND m.gym_id={_sql_literal(str(plan.gym_id))}::uuid AND m.deleted_at IS NULL
    WHERE m.id IS NULL OR m.plan_name IS DISTINCT FROM c.plan_before
       OR m.preferred_shift IS DISTINCT FROM c.shift_before
       OR (m.extra_data->>'plan_cycle') IS DISTINCT FROM c.plan_cycle_before
       OR (m.extra_data->>'plan_cycle_source') IS DISTINCT FROM c.plan_cycle_source_before
  ) THEN RAISE EXCEPTION 'member state changed after dry-run'; END IF;
  IF EXISTS (
    SELECT 1 FROM codex_checkins p
    LEFT JOIN public.members m ON m.id=p.member_id AND m.gym_id={_sql_literal(str(plan.gym_id))}::uuid AND m.deleted_at IS NULL
    WHERE m.id IS NULL
  ) THEN RAISE EXCEPTION 'check-in references unavailable member'; END IF;
  IF EXISTS (
    SELECT 1 FROM codex_checkins p JOIN public.checkins c
      ON c.member_id=p.member_id AND c.checkin_at=p.checkin_at
  ) THEN RAISE EXCEPTION 'check-in state changed after dry-run'; END IF;
END $guard$;
CREATE TEMP TABLE codex_snapshots ON COMMIT DROP AS
SELECT m.id AS member_id,
       jsonb_build_object(
         'plan_name',m.plan_name,'preferred_shift',m.preferred_shift,
         'plan_cycle',m.extra_data->>'plan_cycle',
         'plan_cycle_source',m.extra_data->>'plan_cycle_source'
       ) AS before_state,
       (SELECT count(*)::int FROM codex_checkins p WHERE p.member_id=m.id) AS checkins_imported
FROM public.members m
WHERE m.id IN (
  SELECT member_id FROM codex_changes UNION SELECT member_id FROM codex_checkins
);
INSERT INTO public.checkins(id,gym_id,member_id,checkin_at,source,hour_bucket,weekday,extra_data)
SELECT gen_random_uuid(),{_sql_literal(str(plan.gym_id))}::uuid,p.member_id,p.checkin_at,'import',p.hour_bucket,p.weekday,
       jsonb_build_object(
         'imported',true,'import_source','actuar_access_reconciliation',
         'reconciliation_batch_id',{_sql_literal(str(batch_id))},
         'source_file_sha256',{_sql_literal(plan.access_sha256)}
       )
FROM codex_checkins p;
UPDATE public.members m
SET plan_name=c.plan_after,
    preferred_shift=c.shift_after,
    extra_data=(m.extra_data - 'plan_cycle' - 'plan_cycle_source')
      || CASE WHEN c.plan_cycle_after IS NULL THEN '{{}}'::jsonb ELSE jsonb_build_object('plan_cycle',c.plan_cycle_after) END
      || CASE WHEN c.plan_cycle_source_after IS NULL THEN '{{}}'::jsonb ELSE jsonb_build_object('plan_cycle_source',c.plan_cycle_source_after) END
      || jsonb_build_object('plan_reconciliation_batch_id',{_sql_literal(str(batch_id))}),
    updated_at=now()
FROM codex_changes c WHERE m.id=c.member_id;
UPDATE public.members m
SET last_checkin_at=greatest(m.last_checkin_at, x.latest_checkin), updated_at=now()
FROM (SELECT member_id,max(checkin_at) AS latest_checkin FROM codex_checkins GROUP BY member_id) x
WHERE m.id=x.member_id;
INSERT INTO public.audit_logs(id,gym_id,user_id,member_id,action,entity,entity_id,details,ip_address,user_agent)
SELECT gen_random_uuid(),{_sql_literal(str(plan.gym_id))}::uuid,NULL,s.member_id,
       'member_plan_shift_reconciliation_snapshot','member',s.member_id,
       jsonb_build_object(
         'batch_id',{_sql_literal(str(batch_id))},'before',s.before_state,
         'after',jsonb_build_object(
           'plan_name',m.plan_name,'preferred_shift',m.preferred_shift,
           'plan_cycle',m.extra_data->>'plan_cycle',
           'plan_cycle_source',m.extra_data->>'plan_cycle_source'
         ),
         'checkins_imported',s.checkins_imported
       ),NULL,NULL
FROM codex_snapshots s JOIN public.members m ON m.id=s.member_id;
INSERT INTO public.audit_logs(id,gym_id,user_id,member_id,action,entity,entity_id,details,ip_address,user_agent)
VALUES (
 gen_random_uuid(),{_sql_literal(str(plan.gym_id))}::uuid,NULL,NULL,
 'member_plan_shift_reconciliation_applied','reconciliation_batch',{_sql_literal(str(batch_id))}::uuid,
 jsonb_build_object(
   'batch_id',{_sql_literal(str(batch_id))},'mode','high_confidence_only',
   'files',jsonb_build_array(
     jsonb_build_object('kind','members','filename',{_sql_literal(plan.clients_filename)},'sha256',{_sql_literal(plan.clients_sha256)},'mapping','codigo_acesso|cpf|email_unique_or_cpf_between_exports','rows',{plan.client_rows}),
     jsonb_build_object('kind','checkins','filename',{_sql_literal(plan.access_filename)},'sha256',{_sql_literal(plan.access_sha256)},'mapping','codigo_acesso|cpf|email_unique_or_cpf_between_exports','rows',{plan.access_rows})
   ),
   'totals',jsonb_build_object(
     'members_updated',{len(plan.changes)},'plans_updated',{sum(item.plan_changed for item in plan.changes)},
     'shifts_updated',{sum(item.shift_changed for item in plan.changes)},'checkins_imported',{len(plan.checkins)}
   ),
   'plan_digest',{_sql_literal(actual_digest)},'reference_at',{_sql_literal(plan.reference_at.isoformat())},
   'dry_run_stats',{_sql_literal(stats_json)}::jsonb
 ),NULL,NULL
);
{finish};
SELECT {_sql_literal(str(batch_id))} AS batch_id,
       {_sql_literal('applied' if commit else 'validated_rollback')} AS status,
       {len(plan.changes)}::int AS members_updated,
       {sum(item.plan_changed for item in plan.changes)}::int AS plans_updated,
       {sum(item.shift_changed for item in plan.changes)}::int AS shifts_updated,
       {len(plan.checkins)}::int AS checkins_imported;
"""
    rows = _query(project_ref, sql)
    if len(rows) != 1:
        raise RuntimeError("Resultado inesperado da transacao de reconciliacao.")
    return rows[0]


def main() -> int:
    args = _parser().parse_args()
    if args.apply and args.validate_apply:
        raise RuntimeError("Use somente um entre --apply e --validate-apply.")
    if (args.apply or args.validate_apply) and not args.approved_plan_digest:
        raise RuntimeError("Aplicacao/validacao exige --approved-plan-digest.")
    gym_rows = _query(
        args.project_ref,
        "select id from public.gyms where slug=" + _sql_literal(args.gym_slug) + " and is_active is true limit 1",
    )
    if len(gym_rows) != 1:
        raise RuntimeError(f"Academia ativa nao encontrada: {args.gym_slug}")
    gym_id = UUID(str(gym_rows[0]["id"]))

    members = [
        _member_from_row(row)
        for row in _query(
            args.project_ref,
            "select id,gym_id,full_name,email,phone,cpf_encrypted,plan_name,preferred_shift,extra_data,join_date "
            f"from public.members where gym_id={_sql_literal(str(gym_id))}::uuid and deleted_at is null",
        )
    ]
    member_index = reconciliation._build_member_index(members)
    cpf_decryption_failures: Counter[str] = Counter()
    for member in members:
        if not member.cpf_encrypted:
            continue
        try:
            decrypt_pii(member.cpf_encrypted)
        except Exception as exc:
            cpf_decryption_failures[type(exc).__name__] += 1
    checkin_rows = [
        (UUID(str(row["member_id"])), _parse_db_datetime(row["checkin_at"]), int(row["hour_bucket"]))
        for row in _query(
            args.project_ref,
            "select member_id,checkin_at,hour_bucket from public.checkins "
            f"where gym_id={_sql_literal(str(gym_id))}::uuid and checkin_at >= '2026-07-01T00:00:00Z'::timestamptz",
        )
    ]

    original_loader = reconciliation._load_checkin_rows

    def cached_loader(
        _db: object,
        *,
        gym_id: UUID,
        member_ids: set[UUID],
        start_at: datetime,
        end_at: datetime,
    ) -> list[tuple[UUID, datetime, int]]:
        del gym_id
        start = reconciliation._utc_datetime(start_at)
        end = reconciliation._utc_datetime(end_at)
        return [
            row
            for row in checkin_rows
            if row[0] in member_ids and start <= reconciliation._utc_datetime(row[1]) <= end
        ]

    reconciliation._load_checkin_rows = cached_loader
    try:
        plan = reconciliation.build_reconciliation_plan(
            _ReadOnlyMemberSession(members),  # type: ignore[arg-type]
            gym_id=gym_id,
            clients_content=args.clients_file.read_bytes(),
            access_content=args.access_file.read_bytes(),
            clients_filename=args.clients_file.name,
            access_filename=args.access_file.name,
        )
    finally:
        reconciliation._load_checkin_rows = original_loader

    reconciliation.write_reconciliation_report(plan, args.report)
    manifest = args.report.with_suffix(args.report.suffix + ".manifest.json")
    reconciliation.write_dry_run_manifest(plan, manifest)
    print(f"MODE={'apply' if args.apply else 'validate-apply' if args.validate_apply else 'dry-run'}")
    print(f"DATABASE_CHANGED={'true' if args.apply else 'false'}")
    print(f"PLAN_DIGEST={plan.digest()}")
    print(f"REPORT={args.report.resolve()}")
    print(f"MANIFEST={manifest.resolve()}")
    print(f"MEMBER_INDEX_EXTERNAL_IDS={len(member_index.by_external_id)}")
    print(f"MEMBER_INDEX_CPFS={len(member_index.by_cpf)}")
    print(f"MEMBER_INDEX_EMAILS={len(member_index.by_email)}")
    print(f"CPF_DECRYPTION_FAILURES={dict(cpf_decryption_failures)}")
    for key, value in plan.stats.items():
        print(f"{key.upper()}={value}")
    if args.apply or args.validate_apply:
        result = _apply_plan(
            args.project_ref,
            plan,
            approved_digest=args.approved_plan_digest,
            commit=args.apply,
        )
        print(f"TRANSACTION_STATUS={result['status']}")
        print(f"BATCH_ID={result['batch_id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
