from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session


@dataclass(frozen=True)
class CleanupPolicy:
    key: str
    table: str
    description: str
    where_sql: str
    retention_days: int | None = None
    requires_module_retirement: bool = False


@dataclass(frozen=True)
class TableStorageStat:
    table: str
    total_bytes: int
    table_bytes: int
    index_bytes: int
    live_rows_estimate: int
    dead_rows_estimate: int


@dataclass(frozen=True)
class CleanupCandidateStat:
    policy: str
    table: str
    description: str
    candidate_rows: int
    live_rows_estimate: int
    estimated_reclaimable_bytes: int
    retention_days: int | None
    requires_module_retirement: bool


@dataclass(frozen=True)
class DatabaseStorageAudit:
    gym_id: UUID
    generated_at: datetime
    tables: tuple[TableStorageStat, ...]
    candidates: tuple[CleanupCandidateStat, ...]

    def digest(self) -> str:
        payload = {
            "gym_id": str(self.gym_id),
            "tables": [asdict(row) for row in self.tables],
            "candidates": [asdict(row) for row in self.candidates],
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest().upper()

    def as_dict(self) -> dict[str, Any]:
        return {
            "mode": "read_only",
            "database_changed": False,
            "gym_id": str(self.gym_id),
            "generated_at": self.generated_at.isoformat(),
            "digest": self.digest(),
            "tables": [asdict(row) for row in self.tables],
            "candidates": [asdict(row) for row in self.candidates],
            "notes": [
                "Estimated reclaimable bytes are proportional estimates, not a deletion promise.",
                "Method OS rows require explicit approval to retire the module.",
                "No member, assessment, body-composition result, finance row, consent or recent audit is a candidate.",
            ],
        }


METHOD_OS_TABLES = (
    "method_human_actions",
    "method_outcomes",
    "method_operational_tasks",
    "method_operational_events",
    "method_reports",
    "method_import_batches",
    "method_people",
    "method_client_configs",
)


def cleanup_policies(reference_at: datetime) -> tuple[CleanupPolicy, ...]:
    if reference_at.tzinfo is None:
        reference_at = reference_at.replace(tzinfo=UTC)

    method_policies = tuple(
        CleanupPolicy(
            key=f"retire_method_os_{table}",
            table=table,
            description="Dados isolados do Method OS; arquivar antes de remover.",
            where_sql="gym_id = :gym_id",
            requires_module_retirement=True,
        )
        for table in METHOD_OS_TABLES
    )
    return (
        *method_policies,
        CleanupPolicy(
            key="completed_core_jobs_30d",
            table="core_async_jobs",
            description="Jobs concluidos ou falhos ha mais de 30 dias.",
            where_sql=(
                "gym_id = :gym_id AND status IN ('completed', 'failed') "
                "AND created_at < :cutoff_30"
            ),
            retention_days=30,
        ),
        CleanupPolicy(
            key="diagnosis_errors_90d",
            table="diagnosis_errors",
            description="Erros tecnicos com mais de 90 dias.",
            where_sql="gym_id = :gym_id AND created_at < :cutoff_90",
            retention_days=90,
        ),
        CleanupPolicy(
            key="body_composition_sync_attempts_90d",
            table="body_composition_sync_attempts",
            description="Tentativas antigas de sincronizacao; a avaliacao canonica e preservada.",
            where_sql="gym_id = :gym_id AND created_at < :cutoff_90",
            retention_days=90,
        ),
        CleanupPolicy(
            key="actuar_sync_attempts_90d",
            table="actuar_sync_attempts",
            description="Tentativas Actuar encerradas ha mais de 90 dias.",
            where_sql=(
                "gym_id = :gym_id AND status <> 'started' "
                "AND started_at < :cutoff_90"
            ),
            retention_days=90,
        ),
        CleanupPolicy(
            key="automation_execution_logs_90d",
            table="automation_execution_logs",
            description="Logs de execucao de automacoes com mais de 90 dias.",
            where_sql="gym_id = :gym_id AND created_at < :cutoff_90",
            retention_days=90,
        ),
        CleanupPolicy(
            key="read_notifications_90d",
            table="in_app_notifications",
            description="Notificacoes lidas com mais de 90 dias.",
            where_sql=(
                "gym_id = :gym_id AND read_at IS NOT NULL "
                "AND created_at < :cutoff_90"
            ),
            retention_days=90,
        ),
        CleanupPolicy(
            key="inactive_ai_triage_90d",
            table="ai_triage_recommendations",
            description="Recomendacoes inativas da Central Cordex com mais de 90 dias.",
            where_sql=(
                "gym_id = :gym_id AND is_active IS FALSE "
                "AND last_refreshed_at < :cutoff_90"
            ),
            retention_days=90,
        ),
    )


def build_database_storage_audit(
    db: Session,
    *,
    gym_id: UUID,
    reference_at: datetime | None = None,
) -> DatabaseStorageAudit:
    generated_at = reference_at or datetime.now(tz=UTC)
    table_rows = db.execute(
        text(
            """
            SELECT
                relname AS table_name,
                pg_total_relation_size(relid) AS total_bytes,
                pg_relation_size(relid) AS table_bytes,
                pg_indexes_size(relid) AS index_bytes,
                n_live_tup AS live_rows,
                n_dead_tup AS dead_rows
            FROM pg_stat_user_tables
            WHERE schemaname = 'public'
            ORDER BY pg_total_relation_size(relid) DESC, relname ASC
            """
        )
    ).mappings()
    tables = tuple(
        TableStorageStat(
            table=str(row["table_name"]),
            total_bytes=int(row["total_bytes"] or 0),
            table_bytes=int(row["table_bytes"] or 0),
            index_bytes=int(row["index_bytes"] or 0),
            live_rows_estimate=int(row["live_rows"] or 0),
            dead_rows_estimate=int(row["dead_rows"] or 0),
        )
        for row in table_rows
    )
    table_map = {row.table: row for row in tables}
    params = {
        "gym_id": gym_id,
        "cutoff_30": generated_at - timedelta(days=30),
        "cutoff_90": generated_at - timedelta(days=90),
    }
    candidates: list[CleanupCandidateStat] = []
    for policy in cleanup_policies(generated_at):
        if policy.table not in table_map:
            continue
        count = int(
            db.execute(
                # Both the table and predicate come exclusively from the static
                # CleanupPolicy allowlist above; no user input enters this SQL.
                text(f'SELECT count(*) FROM public."{policy.table}" WHERE {policy.where_sql}'),  # nosec B608
                params,
            ).scalar_one()
            or 0
        )
        table = table_map[policy.table]
        denominator = max(table.live_rows_estimate, count, 1)
        estimate = min(table.total_bytes, round(table.total_bytes * count / denominator))
        candidates.append(
            CleanupCandidateStat(
                policy=policy.key,
                table=policy.table,
                description=policy.description,
                candidate_rows=count,
                live_rows_estimate=table.live_rows_estimate,
                estimated_reclaimable_bytes=estimate,
                retention_days=policy.retention_days,
                requires_module_retirement=policy.requires_module_retirement,
            )
        )
    return DatabaseStorageAudit(
        gym_id=gym_id,
        generated_at=generated_at,
        tables=tables,
        candidates=tuple(candidates),
    )
