import argparse
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import create_engine, text


ALL_INTERNAL_JOB_TYPES = (
    "public_diagnosis",
    "nps_dispatch",
    "monthly_reports_dispatch",
)
ALL_EXTERNAL_PROVIDER_JOB_TYPES = (
    "lead_proposal_dispatch",
    "whatsapp_webhook_setup",
)


def _env_enabled(name: str, default: bool = False) -> bool:
    raw = os.getenv(name, "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "t", "yes", "y", "on"}


def _active_internal_job_types() -> tuple[str, ...]:
    active = ["nps_dispatch"]
    if _env_enabled("PUBLIC_DIAGNOSIS_ENABLED", False):
        active.insert(0, "public_diagnosis")
    if _env_enabled("MONTHLY_REPORTS_DISPATCH_ENABLED", False):
        active.append("monthly_reports_dispatch")
    return tuple(active)


def _active_external_provider_job_types() -> tuple[str, ...]:
    active = ["whatsapp_webhook_setup"]
    if _env_enabled("PUBLIC_PROPOSAL_ENABLED", False) or _env_enabled("PUBLIC_PROPOSAL_EMAIL_ENABLED", False):
        active.insert(0, "lead_proposal_dispatch")
    return tuple(active)


@dataclass
class JobTypeStats:
    job_type: str
    total_jobs: int
    completed_jobs: int
    successful_jobs: int
    failed_jobs: int
    retry_scheduled_jobs: int
    pending_jobs: int
    processing_jobs: int
    classified_terminal_failed_jobs: int
    success_rate_percent: float | None


def _require_database_url() -> str:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        raise SystemExit("DATABASE_URL nao encontrada no ambiente.")
    return database_url


def _round_metric(value: Any) -> float | None:
    if value is None:
        return None
    return round(float(value), 2)


def _success_rate(*, total_jobs: int, completed_jobs: int, classified_terminal_failed_jobs: int, discount_terminal: bool) -> float | None:
    denominator = total_jobs - classified_terminal_failed_jobs if discount_terminal else total_jobs
    if denominator <= 0:
        return None
    return round((completed_jobs / denominator) * 100, 2)


def _fetch_job_type_rows(*, connection, cutoff: datetime, gym_slug: str | None) -> list[JobTypeStats]:
    critical_job_types = _active_internal_job_types() + _active_external_provider_job_types()
    external_provider_job_types = set(_active_external_provider_job_types())
    if not critical_job_types:
        return []

    params = {"cutoff": cutoff, "gym_slug": gym_slug}
    critical_job_types_sql = ", ".join(f"'{job_type}'" for job_type in critical_job_types)
    query = text(
        f"""
        select
            j.job_type,
            count(*) as total_jobs,
            sum(case when j.status = 'completed' then 1 else 0 end) as completed_jobs,
            sum(
                case
                    when j.job_type = 'lead_proposal_dispatch'
                        and j.status = 'completed'
                        and coalesce((j.result_json ->> 'emailed')::boolean, false) = true
                        then 1
                    when j.job_type = 'monthly_reports_dispatch'
                        and j.status = 'completed'
                        and coalesce((j.result_json ->> 'sent')::int, 0) > 0
                        then 1
                    when j.job_type not in ('lead_proposal_dispatch', 'monthly_reports_dispatch')
                        and j.status = 'completed'
                        then 1
                    else 0
                end
            ) as successful_jobs,
            sum(case when j.status = 'failed' then 1 else 0 end) as failed_jobs,
            sum(case when j.status = 'retry_scheduled' then 1 else 0 end) as retry_scheduled_jobs,
            sum(case when j.status = 'pending' then 1 else 0 end) as pending_jobs,
            sum(case when j.status = 'processing' then 1 else 0 end) as processing_jobs,
            sum(case when j.status = 'failed' and j.error_code is not null then 1 else 0 end) as classified_terminal_failed_jobs
        from core_async_jobs j
        join gyms g on g.id = j.gym_id
        where j.created_at >= :cutoff
          and j.job_type in ({critical_job_types_sql})
          and (:gym_slug is null or g.slug = :gym_slug)
        group by j.job_type
        order by j.job_type
        """
    )
    rows = []
    for row in connection.execute(query, params).mappings().all():
        job_type = str(row["job_type"])
        rows.append(
            JobTypeStats(
                job_type=job_type,
                total_jobs=int(row["total_jobs"] or 0),
                completed_jobs=int(row["completed_jobs"] or 0),
                successful_jobs=int(row["successful_jobs"] or 0),
                failed_jobs=int(row["failed_jobs"] or 0),
                retry_scheduled_jobs=int(row["retry_scheduled_jobs"] or 0),
                pending_jobs=int(row["pending_jobs"] or 0),
                processing_jobs=int(row["processing_jobs"] or 0),
                classified_terminal_failed_jobs=int(row["classified_terminal_failed_jobs"] or 0),
                success_rate_percent=_success_rate(
                    total_jobs=int(row["total_jobs"] or 0),
                    completed_jobs=int(row["successful_jobs"] or 0),
                    classified_terminal_failed_jobs=int(row["classified_terminal_failed_jobs"] or 0),
                    discount_terminal=job_type in external_provider_job_types,
                ),
            )
        )
    return rows


def _aggregate(rows: list[JobTypeStats], *, included_job_types: tuple[str, ...], success_target_percent: float, discount_terminal: bool) -> dict[str, Any]:
    filtered = [row for row in rows if row.job_type in included_job_types]
    total_jobs = sum(row.total_jobs for row in filtered)
    completed_jobs = sum(row.completed_jobs for row in filtered)
    successful_jobs = sum(row.successful_jobs for row in filtered)
    failed_jobs = sum(row.failed_jobs for row in filtered)
    classified_terminal_failed_jobs = sum(row.classified_terminal_failed_jobs for row in filtered)
    denominator = total_jobs - classified_terminal_failed_jobs if discount_terminal else total_jobs
    success_rate_percent = None if denominator <= 0 else round((successful_jobs / denominator) * 100, 2)
    return {
        "job_types": list(included_job_types),
        "total_jobs": total_jobs,
        "completed_jobs": completed_jobs,
        "successful_jobs": successful_jobs,
        "failed_jobs": failed_jobs,
        "classified_terminal_failed_jobs": classified_terminal_failed_jobs,
        "effective_denominator": denominator,
        "success_rate_percent": success_rate_percent,
        "success_target_percent": success_target_percent,
        "enough_data": total_jobs > 0,
        "target_passed": success_rate_percent is not None and success_rate_percent >= success_target_percent,
    }


def _payload(*, cutoff: datetime, gym_slug: str | None, rows: list[JobTypeStats]) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    internal_job_types = _active_internal_job_types()
    external_provider_job_types = _active_external_provider_job_types()
    critical_job_types = internal_job_types + external_provider_job_types
    return {
        "window_days": int((now - cutoff).days),
        "window_started_at": cutoff.isoformat(),
        "window_ended_at": now.isoformat(),
        "gym_slug": gym_slug,
        "critical_job_types": list(critical_job_types),
        "job_type_stats": [asdict(row) for row in rows],
        "internal_critical_jobs": _aggregate(
            rows,
            included_job_types=internal_job_types,
            success_target_percent=99.0,
            discount_terminal=False,
        ),
        "external_provider_jobs": _aggregate(
            rows,
            included_job_types=external_provider_job_types,
            success_target_percent=95.0,
            discount_terminal=True,
        ),
    }


def _render_markdown(payload: dict[str, Any]) -> str:
    internal = payload["internal_critical_jobs"]
    external = payload["external_provider_jobs"]
    lines = [
        "# Pilot Gate Report",
        "",
        f"- Scope: `{payload['gym_slug'] or 'all-tenants'}`",
        f"- Window started at: `{payload['window_started_at']}`",
        f"- Window ended at: `{payload['window_ended_at']}`",
        "",
        "## Internal Critical Jobs",
        "",
        f"- total_jobs: `{internal['total_jobs']}`",
        f"- completed_jobs: `{internal['completed_jobs']}`",
        f"- successful_jobs: `{internal['successful_jobs']}`",
        f"- failed_jobs: `{internal['failed_jobs']}`",
        f"- success_rate_percent: `{internal['success_rate_percent']}`",
        f"- enough_data: `{internal['enough_data']}`",
        f"- target_passed (`>= {internal['success_target_percent']}%`): `{internal['target_passed']}`",
        "",
        "## External Provider Jobs",
        "",
        f"- total_jobs: `{external['total_jobs']}`",
        f"- completed_jobs: `{external['completed_jobs']}`",
        f"- successful_jobs: `{external['successful_jobs']}`",
        f"- failed_jobs: `{external['failed_jobs']}`",
        f"- classified_terminal_failed_jobs: `{external['classified_terminal_failed_jobs']}`",
        f"- success_rate_percent: `{external['success_rate_percent']}`",
        f"- enough_data: `{external['enough_data']}`",
        f"- target_passed (`>= {external['success_target_percent']}%`): `{external['target_passed']}`",
        "",
        "## By Job Type",
        "",
        "| job_type | total | completed_status | successful | failed | retry_scheduled | pending | processing | classified_terminal_failed | success_rate_percent |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in payload["job_type_stats"]:
        lines.append(
            f"| {row['job_type']} | {row['total_jobs']} | {row['completed_jobs']} | {row['successful_jobs']} | {row['failed_jobs']} | {row['retry_scheduled_jobs']} | {row['pending_jobs']} | {row['processing_jobs']} | {row['classified_terminal_failed_jobs']} | {row['success_rate_percent']} |"
        )
    if not payload["job_type_stats"]:
        lines.append("| no-data | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - |")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Measure pilot gate readiness for critical core async jobs.")
    parser.add_argument("--days", type=int, default=14, help="Rolling window size in days.")
    parser.add_argument("--gym-slug", default="", help="Optional gym slug to scope the report.")
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    args = parser.parse_args()

    cutoff = datetime.now(timezone.utc) - timedelta(days=max(args.days, 1))
    gym_slug = args.gym_slug.strip() or None
    engine = create_engine(_require_database_url(), future=True)
    with engine.connect() as connection:
        rows = _fetch_job_type_rows(connection=connection, cutoff=cutoff, gym_slug=gym_slug)
    payload = _payload(cutoff=cutoff, gym_slug=gym_slug, rows=rows)
    if args.format == "markdown":
        print(_render_markdown(payload))
        return
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
