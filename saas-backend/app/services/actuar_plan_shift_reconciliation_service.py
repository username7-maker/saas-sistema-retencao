from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import AuditLog, Checkin, CheckinSource, Member
from app.services.audit_service import log_audit_event
from app.services.import_service import (
    CHECKIN_AT_KEYS,
    CHECKIN_DATE_KEYS,
    CHECKIN_TIME_KEYS,
    CPF_KEYS,
    EMAIL_KEYS,
    EXTERNAL_ID_KEYS,
    JOIN_DATE_KEYS,
    PHONE_KEYS,
    PLAN_CONDITION_KEYS,
    PLAN_NAME_SOURCE_KEYS,
    PLAN_RENEWAL_KEYS,
    _digits,
    _external_id_candidates,
    _extract_member_name,
    _extract_plan_metadata,
    _iter_rows,
    _normalize_phone,
    _normalize_text,
    _parse_checkin_datetime,
    _parse_date,
    _pick_first,
)
from app.services.preferred_shift_service import derive_preferred_shift_from_counts
from app.utils.encryption import decrypt_cpf

EXPECTED_CLIENTS_SHA256 = "D6F244CF5CCE1C56C16FE17231C725C2D9E36EA6DDA2B0BFD2F7039F3E8DF3EF"
EXPECTED_ACCESS_SHA256 = "00E3DDC39C7282160C017E32A87ABDA00A0E511D9C26F7A2B41E70A1CCE3D15A"
EXPECTED_CLIENT_ROWS = 1_427
EXPECTED_ACCESS_ROWS = 4_391
LOOKBACK_DAYS = 30

Confidence = Literal["high", "review", "ambiguous", "unmatched"]


@dataclass(frozen=True)
class MatchDecision:
    member_id: UUID | None
    method: str
    confidence: Confidence
    reason: str


@dataclass(frozen=True)
class PreparedCheckin:
    member_id: UUID
    checkin_at: datetime
    hour_bucket: int
    weekday: int

    @property
    def key(self) -> tuple[str, str]:
        return str(self.member_id), _utc_datetime(self.checkin_at).isoformat()


@dataclass(frozen=True)
class MemberChange:
    member_id: UUID
    plan_before: str
    plan_after: str
    shift_before: str | None
    shift_after: str | None
    plan_cycle_before: str | None
    plan_cycle_after: str | None
    plan_cycle_source_before: str | None
    plan_cycle_source_after: str | None
    plan_source: str | None
    shift_source: str

    @property
    def plan_changed(self) -> bool:
        return self.plan_before != self.plan_after

    @property
    def shift_changed(self) -> bool:
        return self.shift_before != self.shift_after


@dataclass(frozen=True)
class ReconciliationReportRow:
    student: str
    member_id: str
    current_plan: str
    expected_plan: str
    plan_source: str
    current_shift: str
    expected_shift: str
    shift_source: str
    confidence: Confidence
    proposed_action: str
    match_method: str
    notes: str


@dataclass
class ReconciliationPlan:
    gym_id: UUID
    clients_filename: str
    access_filename: str
    clients_sha256: str
    access_sha256: str
    client_rows: int
    access_rows: int
    reference_at: datetime
    changes: list[MemberChange] = field(default_factory=list)
    checkins: list[PreparedCheckin] = field(default_factory=list)
    report_rows: list[ReconciliationReportRow] = field(default_factory=list)
    stats: dict[str, int] = field(default_factory=dict)

    def digest(self) -> str:
        payload = {
            "gym_id": str(self.gym_id),
            "clients_sha256": self.clients_sha256,
            "access_sha256": self.access_sha256,
            "reference_at": _utc_datetime(self.reference_at).isoformat(),
            "changes": [
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
                for item in sorted(self.changes, key=lambda change: str(change.member_id))
            ],
            "checkins": [
                {"member_id": item.key[0], "checkin_at": item.key[1]}
                for item in sorted(self.checkins, key=lambda checkin: checkin.key)
            ],
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest().upper()


@dataclass(frozen=True)
class ApplyResult:
    batch_id: UUID
    members_updated: int
    plans_updated: int
    shifts_updated: int
    checkins_imported: int


@dataclass
class _MemberIndex:
    members: dict[UUID, Member]
    by_external_id: dict[str, set[UUID]]
    by_cpf: dict[str, set[UUID]]
    by_email: dict[str, set[UUID]]
    by_name: dict[str, set[UUID]]


@dataclass(frozen=True)
class _PlanCandidate:
    member_id: UUID
    plan_name: str
    cycle: str | None
    cycle_source: str
    match: MatchDecision
    row_number: int


def build_reconciliation_plan(
    db: Session,
    *,
    gym_id: UUID,
    clients_content: bytes,
    access_content: bytes,
    clients_filename: str,
    access_filename: str,
    reference_at: datetime | None = None,
) -> ReconciliationPlan:
    """Build a deterministic, read-only reconciliation plan.

    The two source hashes and row counts are deliberately pinned to the exports
    approved for this one-off repair. A different export must result in a new,
    reviewed batch instead of silently reusing this command.
    """

    clients_sha256 = _verify_file(
        clients_content,
        expected_sha256=EXPECTED_CLIENTS_SHA256,
        label="Todos os Clientes.xlsx",
    )
    access_sha256 = _verify_file(
        access_content,
        expected_sha256=EXPECTED_ACCESS_SHA256,
        label="Acessos.xlsx",
    )
    client_rows = list(_iter_rows(clients_content, filename=clients_filename))
    access_rows = list(_iter_rows(access_content, filename=access_filename))
    if len(client_rows) != EXPECTED_CLIENT_ROWS:
        raise ValueError(f"Todos os Clientes.xlsx deveria conter {EXPECTED_CLIENT_ROWS} linhas; recebeu {len(client_rows)}.")
    if len(access_rows) != EXPECTED_ACCESS_ROWS:
        raise ValueError(f"Acessos.xlsx deveria conter {EXPECTED_ACCESS_ROWS} linhas; recebeu {len(access_rows)}.")

    members = list(
        db.scalars(
            select(Member).where(
                Member.gym_id == gym_id,
                Member.deleted_at.is_(None),
            )
        ).all()
    )
    index = _build_member_index(members)

    stats: Counter[str] = Counter()
    report_rows: list[ReconciliationReportRow] = []
    candidates_by_member: dict[UUID, list[_PlanCandidate]] = defaultdict(list)
    client_members_by_cpf: dict[str, set[UUID]] = defaultdict(set)
    high_scope: set[UUID] = set()
    match_method_by_member: dict[UUID, set[str]] = defaultdict(set)

    for row_number, row in client_rows:
        plan_parts = _safe_plan_candidate(row)
        decision = _match_row(row, index, expected_plan=plan_parts[0] if plan_parts else None)
        stats[f"clients_match_{decision.confidence}"] += 1
        if decision.member_id is not None:
            match_method_by_member[decision.member_id].add(decision.method)
        if decision.confidence == "high" and decision.member_id is not None:
            high_scope.add(decision.member_id)
            client_cpf = _digits(_pick_first(row, CPF_KEYS))
            if client_cpf:
                client_members_by_cpf[client_cpf].add(decision.member_id)

        if plan_parts is None:
            stats["plans_ignored_empty_or_generic"] += 1
            if decision.confidence != "high":
                report_rows.append(_review_report_row(row, decision, notes="Plano vazio, generico ou Plano Base; nenhuma alteracao proposta."))
            continue

        plan_name, cycle, cycle_source = plan_parts
        if decision.member_id is not None:
            candidates_by_member[decision.member_id].append(
                _PlanCandidate(
                    member_id=decision.member_id,
                    plan_name=plan_name,
                    cycle=cycle,
                    cycle_source=cycle_source,
                    match=decision,
                    row_number=row_number,
                )
            )
        else:
            report_rows.append(
                _review_report_row(
                    row,
                    decision,
                    expected_plan=plan_name,
                    plan_source=f"{clients_filename}:{cycle_source}",
                    notes=decision.reason,
                )
            )

    parsed_access: list[tuple[int, dict[str, str], datetime, MatchDecision]] = []
    latest_access_at: datetime | None = None
    for row_number, row in access_rows:
        parsed = _parse_access_datetime(row)
        if parsed is None:
            stats["access_invalid_datetime"] += 1
            report_rows.append(_review_report_row(row, MatchDecision(None, "none", "unmatched", "Data/hora invalida.")))
            continue
        latest_access_at = max(latest_access_at, parsed) if latest_access_at else parsed
        access_plan = _safe_plan_candidate(row)
        decision = _match_row(row, index, expected_plan=access_plan[0] if access_plan else None)
        decision = _bridge_access_decision_through_clients(
            row,
            decision,
            client_members_by_cpf=client_members_by_cpf,
        )
        stats[f"access_match_{decision.confidence}"] += 1
        parsed_access.append((row_number, row, parsed, decision))
        if decision.member_id is not None:
            match_method_by_member[decision.member_id].add(decision.method)
        if decision.confidence == "high" and decision.member_id is not None:
            high_scope.add(decision.member_id)

    resolved_reference_at = _utc_datetime(reference_at or latest_access_at or datetime.now(tz=UTC))
    cutoff = resolved_reference_at - timedelta(days=LOOKBACK_DAYS)
    candidate_checkins: dict[tuple[str, str], PreparedCheckin] = {}
    review_access_by_identity: dict[str, tuple[dict[str, str], MatchDecision, int]] = {}
    for _row_number, row, parsed, decision in parsed_access:
        if decision.confidence != "high" or decision.member_id is None:
            identity = _normalize_text(_extract_member_name(row) or "") or f"row-{_row_number}"
            existing = review_access_by_identity.get(identity)
            if existing:
                review_access_by_identity[identity] = (existing[0], existing[1], existing[2] + 1)
            else:
                review_access_by_identity[identity] = (row, decision, 1)
            continue
        prepared = PreparedCheckin(
            member_id=decision.member_id,
            checkin_at=_utc_datetime(parsed),
            hour_bucket=parsed.hour,
            weekday=parsed.weekday(),
        )
        if prepared.key in candidate_checkins:
            stats["access_duplicate_in_file"] += 1
            continue
        candidate_checkins[prepared.key] = prepared

    for row, decision, occurrence_count in review_access_by_identity.values():
        report_rows.append(
            _review_report_row(
                row,
                decision,
                notes=f"{decision.reason} {occurrence_count} acesso(s) ficaram fora da importacao automatica.",
            )
        )

    existing_checkin_rows = _load_checkin_rows(
        db,
        gym_id=gym_id,
        member_ids=high_scope,
        start_at=min((item.checkin_at for item in candidate_checkins.values()), default=cutoff),
        end_at=max((item.checkin_at for item in candidate_checkins.values()), default=resolved_reference_at),
    )
    existing_keys = {
        (str(member_id), _utc_datetime(checkin_at).isoformat())
        for member_id, checkin_at, _hour_bucket in existing_checkin_rows
    }
    prepared_checkins = [item for key, item in candidate_checkins.items() if key not in existing_keys]
    stats["access_existing_duplicates"] += len(candidate_checkins) - len(prepared_checkins)
    stats["access_to_import"] = len(prepared_checkins)

    recent_rows = _load_checkin_rows(
        db,
        gym_id=gym_id,
        member_ids=high_scope,
        start_at=cutoff,
        end_at=resolved_reference_at,
    )
    counts_by_member: dict[UUID, Counter[str]] = defaultdict(Counter)
    for member_id, _checkin_at, hour_bucket in recent_rows:
        counts_by_member[member_id][_shift_for_hour(int(hour_bucket))] += 1
    for item in prepared_checkins:
        if cutoff <= item.checkin_at <= resolved_reference_at:
            counts_by_member[item.member_id][_shift_for_hour(item.hour_bucket)] += 1

    selected_plans: dict[UUID, _PlanCandidate] = {}
    plan_review_rows: list[ReconciliationReportRow] = []
    for member_id, candidates in candidates_by_member.items():
        distinct_plans = {_normalize_text(item.plan_name): item.plan_name for item in candidates}
        high_candidates = [item for item in candidates if item.match.confidence == "high"]
        if len(distinct_plans) > 1:
            member = index.members[member_id]
            stats["plans_conflicting_rows"] += 1
            plan_review_rows.append(
                ReconciliationReportRow(
                    student=member.full_name,
                    member_id=str(member.id),
                    current_plan=member.plan_name,
                    expected_plan=" | ".join(sorted(distinct_plans.values())),
                    plan_source=clients_filename,
                    current_shift=member.preferred_shift or "",
                    expected_shift="",
                    shift_source="",
                    confidence="ambiguous",
                    proposed_action="manual_review",
                    match_method=", ".join(sorted({item.match.method for item in candidates})),
                    notes="Mais de um plano esperado para o mesmo membro no arquivo.",
                )
            )
            continue
        if not high_candidates:
            candidate = candidates[0]
            member = index.members[member_id]
            plan_review_rows.append(
                ReconciliationReportRow(
                    student=member.full_name,
                    member_id=str(member.id),
                    current_plan=member.plan_name,
                    expected_plan=candidate.plan_name,
                    plan_source=f"{clients_filename}:{candidate.cycle_source}",
                    current_shift=member.preferred_shift or "",
                    expected_shift="",
                    shift_source="",
                    confidence=candidate.match.confidence,
                    proposed_action="manual_review",
                    match_method=candidate.match.method,
                    notes="Correspondencia sem identificador forte unico; plano nao sera aplicado automaticamente.",
                )
            )
            continue
        selected_plans[member_id] = high_candidates[0]

    report_rows.extend(plan_review_rows)
    changes: list[MemberChange] = []
    prepared_counts: Counter[UUID] = Counter(item.member_id for item in prepared_checkins)
    for member_id in sorted(high_scope, key=str):
        member = index.members[member_id]
        plan_candidate = selected_plans.get(member_id)
        expected_plan = plan_candidate.plan_name if plan_candidate else member.plan_name
        expected_cycle = plan_candidate.cycle if plan_candidate else (member.extra_data or {}).get("plan_cycle")
        expected_cycle_source = (
            plan_candidate.cycle_source if plan_candidate else (member.extra_data or {}).get("plan_cycle_source")
        )
        shift_counts = dict(counts_by_member.get(member_id, Counter()))
        expected_shift = derive_preferred_shift_from_counts(shift_counts)
        shift_status = "dominant" if expected_shift else ("tie" if sum(shift_counts.values()) else "no_access")
        shift_source = (
            f"checkins_{LOOKBACK_DAYS}d:{shift_status}:"
            + ",".join(f"{key}={shift_counts.get(key, 0)}" for key in ("overnight", "morning", "afternoon", "evening"))
        )
        plan_source = f"{clients_filename}:{plan_candidate.cycle_source}" if plan_candidate else None
        change = MemberChange(
            member_id=member_id,
            plan_before=member.plan_name,
            plan_after=expected_plan,
            shift_before=member.preferred_shift,
            shift_after=expected_shift,
            plan_cycle_before=(member.extra_data or {}).get("plan_cycle"),
            plan_cycle_after=expected_cycle,
            plan_cycle_source_before=(member.extra_data or {}).get("plan_cycle_source"),
            plan_cycle_source_after=expected_cycle_source,
            plan_source=plan_source,
            shift_source=shift_source,
        )
        if change.plan_changed or change.shift_changed or (
            plan_candidate
            and (
                change.plan_cycle_before != change.plan_cycle_after
                or change.plan_cycle_source_before != change.plan_cycle_source_after
            )
        ):
            changes.append(change)

        actions: list[str] = []
        if change.plan_changed:
            actions.append("update_plan")
        if change.shift_changed:
            actions.append("update_shift")
        if prepared_counts[member_id]:
            actions.append(f"import_{prepared_counts[member_id]}_checkins")
        report_rows.append(
            ReconciliationReportRow(
                student=member.full_name,
                member_id=str(member.id),
                current_plan=member.plan_name,
                expected_plan=expected_plan,
                plan_source=plan_source or "unchanged",
                current_shift=member.preferred_shift or "",
                expected_shift=expected_shift or "",
                shift_source=shift_source,
                confidence="high",
                proposed_action=";".join(actions) if actions else "no_change",
                match_method=", ".join(sorted(match_method_by_member[member_id])),
                notes="Somente identificadores fortes unicos entram no apply.",
            )
        )

    stats["members_in_high_confidence_scope"] = len(high_scope)
    stats["members_to_update"] = len(changes)
    stats["plans_to_update"] = sum(item.plan_changed for item in changes)
    stats["shifts_to_update"] = sum(item.shift_changed for item in changes)
    stats["report_rows"] = len(report_rows)

    return ReconciliationPlan(
        gym_id=gym_id,
        clients_filename=Path(clients_filename).name,
        access_filename=Path(access_filename).name,
        clients_sha256=clients_sha256,
        access_sha256=access_sha256,
        client_rows=len(client_rows),
        access_rows=len(access_rows),
        reference_at=resolved_reference_at,
        changes=changes,
        checkins=sorted(prepared_checkins, key=lambda item: item.key),
        report_rows=sorted(report_rows, key=lambda item: (item.student.casefold(), item.member_id, item.proposed_action)),
        stats=dict(sorted(stats.items())),
    )


def apply_reconciliation(
    db: Session,
    plan: ReconciliationPlan,
    *,
    approved_plan_digest: str,
) -> ApplyResult:
    """Stage a reviewed plan in the caller-owned transaction; never commits."""

    actual_digest = plan.digest()
    if approved_plan_digest.strip().upper() != actual_digest:
        raise ValueError("Digest aprovado nao corresponde ao dry-run atual; gere e revise um novo relatorio.")

    batch_id = uuid4()
    member_ids = {change.member_id for change in plan.changes} | {item.member_id for item in plan.checkins}
    members = {
        member.id: member
        for member in db.scalars(
            select(Member).where(
                Member.gym_id == plan.gym_id,
                Member.id.in_(member_ids),
                Member.deleted_at.is_(None),
            )
        ).all()
    }
    if set(members) != member_ids:
        raise RuntimeError("A base mudou desde o dry-run: um ou mais membros nao estao mais disponiveis.")

    changes_by_member = {change.member_id: change for change in plan.changes}
    for change in plan.changes:
        member = members[change.member_id]
        extra_data = dict(member.extra_data or {})
        if (
            member.plan_name != change.plan_before
            or member.preferred_shift != change.shift_before
            or extra_data.get("plan_cycle") != change.plan_cycle_before
            or extra_data.get("plan_cycle_source") != change.plan_cycle_source_before
        ):
            raise RuntimeError(f"A base mudou desde o dry-run para o membro {member.id}; apply abortado.")

    existing_keys = _load_existing_keys_for_prepared(db, plan.gym_id, plan.checkins)
    if existing_keys:
        raise RuntimeError("A base recebeu check-ins depois do dry-run; gere e aprove um novo digest.")

    imported_member_ids: set[UUID] = set()
    for item in plan.checkins:
        member = members[item.member_id]
        db.add(
            Checkin(
                gym_id=plan.gym_id,
                member_id=item.member_id,
                checkin_at=item.checkin_at,
                source=CheckinSource.IMPORT,
                hour_bucket=item.hour_bucket,
                weekday=item.weekday,
                extra_data={
                    "imported": True,
                    "import_source": "actuar_access_reconciliation",
                    "reconciliation_batch_id": str(batch_id),
                    "source_file_sha256": plan.access_sha256,
                },
            )
        )
        imported_member_ids.add(item.member_id)
        if member.last_checkin_at is None or _utc_datetime(item.checkin_at) > _utc_datetime(member.last_checkin_at):
            member.last_checkin_at = item.checkin_at
            db.add(member)

    for member_id in sorted(member_ids, key=str):
        member = members[member_id]
        change = changes_by_member.get(member_id)
        before = {
            "plan_name": member.plan_name,
            "preferred_shift": member.preferred_shift,
            "plan_cycle": (member.extra_data or {}).get("plan_cycle"),
            "plan_cycle_source": (member.extra_data or {}).get("plan_cycle_source"),
        }
        if change:
            member.plan_name = change.plan_after
            member.preferred_shift = change.shift_after
            extra_data = dict(member.extra_data or {})
            if change.plan_cycle_after is None:
                extra_data.pop("plan_cycle", None)
            else:
                extra_data["plan_cycle"] = change.plan_cycle_after
            if change.plan_cycle_source_after is None:
                extra_data.pop("plan_cycle_source", None)
            else:
                extra_data["plan_cycle_source"] = change.plan_cycle_source_after
            extra_data["plan_reconciliation_batch_id"] = str(batch_id)
            member.extra_data = extra_data
            db.add(member)
        after = {
            "plan_name": member.plan_name,
            "preferred_shift": member.preferred_shift,
            "plan_cycle": (member.extra_data or {}).get("plan_cycle"),
            "plan_cycle_source": (member.extra_data or {}).get("plan_cycle_source"),
        }
        log_audit_event(
            db,
            "member_plan_shift_reconciliation_snapshot",
            "member",
            gym_id=plan.gym_id,
            member_id=member_id,
            entity_id=member_id,
            details={
                "batch_id": str(batch_id),
                "before": before,
                "after": after,
                "checkins_imported": sum(1 for item in plan.checkins if item.member_id == member_id),
            },
            flush=False,
        )

    plans_updated = sum(change.plan_changed for change in plan.changes)
    shifts_updated = sum(change.shift_changed for change in plan.changes)
    log_audit_event(
        db,
        "member_plan_shift_reconciliation_applied",
        "reconciliation_batch",
        gym_id=plan.gym_id,
        entity_id=batch_id,
        details={
            "batch_id": str(batch_id),
            "mode": "high_confidence_only",
            "files": [
                {
                    "kind": "members",
                    "filename": plan.clients_filename,
                    "sha256": plan.clients_sha256,
                    "mapping": "codigo_acesso|cpf|email_unique",
                    "rows": plan.client_rows,
                },
                {
                    "kind": "checkins",
                    "filename": plan.access_filename,
                    "sha256": plan.access_sha256,
                    "mapping": "codigo_acesso|cpf|email_unique",
                    "rows": plan.access_rows,
                },
            ],
            "totals": {
                "members_updated": len(plan.changes),
                "plans_updated": plans_updated,
                "shifts_updated": shifts_updated,
                "checkins_imported": len(plan.checkins),
                "members_with_checkins": len(imported_member_ids),
            },
            "plan_digest": actual_digest,
            "reference_at": plan.reference_at.isoformat(),
        },
        flush=False,
    )
    db.flush()
    return ApplyResult(
        batch_id=batch_id,
        members_updated=len(plan.changes),
        plans_updated=plans_updated,
        shifts_updated=shifts_updated,
        checkins_imported=len(plan.checkins),
    )


def rollback_reconciliation(db: Session, *, gym_id: UUID, batch_id: UUID) -> ApplyResult:
    """Stage rollback of a reconciliation batch in the caller-owned transaction."""

    prior_rollback = list(
        db.scalars(
            select(AuditLog).where(
                AuditLog.gym_id == gym_id,
                AuditLog.action == "member_plan_shift_reconciliation_rolled_back",
            )
        ).all()
    )
    if any(str((event.details or {}).get("batch_id")) == str(batch_id) for event in prior_rollback):
        raise ValueError(f"Lote {batch_id} ja foi revertido.")

    snapshot_events = list(
        db.scalars(
            select(AuditLog).where(
                AuditLog.gym_id == gym_id,
                AuditLog.action == "member_plan_shift_reconciliation_snapshot",
            )
        ).all()
    )
    snapshot_events = [
        event for event in snapshot_events if str((event.details or {}).get("batch_id")) == str(batch_id)
    ]
    if not snapshot_events:
        raise ValueError(f"Lote de reconciliacao nao encontrado: {batch_id}.")

    members = {
        member.id: member
        for member in db.scalars(
            select(Member).where(
                Member.gym_id == gym_id,
                Member.id.in_({event.member_id for event in snapshot_events if event.member_id}),
                Member.deleted_at.is_(None),
            )
        ).all()
    }
    for event in snapshot_events:
        member = members.get(event.member_id)
        if member is None:
            raise RuntimeError(f"Membro do lote nao esta mais disponivel: {event.member_id}.")
        details = event.details or {}
        before = details.get("before") or {}
        after = details.get("after") or {}
        current = {
            "plan_name": member.plan_name,
            "preferred_shift": member.preferred_shift,
            "plan_cycle": (member.extra_data or {}).get("plan_cycle"),
            "plan_cycle_source": (member.extra_data or {}).get("plan_cycle_source"),
        }
        if current != after:
            raise RuntimeError(f"Membro {member.id} mudou depois do lote; rollback abortado para evitar sobrescrita.")
        member.plan_name = before.get("plan_name") or "Plano Base"
        member.preferred_shift = before.get("preferred_shift")
        extra_data = dict(member.extra_data or {})
        for key in ("plan_cycle", "plan_cycle_source"):
            if before.get(key) is None:
                extra_data.pop(key, None)
            else:
                extra_data[key] = before[key]
        if extra_data.get("plan_reconciliation_batch_id") == str(batch_id):
            extra_data.pop("plan_reconciliation_batch_id", None)
        member.extra_data = extra_data
        db.add(member)

    batch_checkins = list(
        db.scalars(
            select(Checkin).where(
                Checkin.gym_id == gym_id,
                Checkin.extra_data["reconciliation_batch_id"].as_string() == str(batch_id),
            )
        ).all()
    )
    affected_member_ids = {item.member_id for item in batch_checkins}
    for checkin in batch_checkins:
        db.delete(checkin)
    db.flush()

    if affected_member_ids:
        latest_rows = db.execute(
            select(Checkin.member_id, func.max(Checkin.checkin_at))
            .where(Checkin.member_id.in_(affected_member_ids))
            .group_by(Checkin.member_id)
        ).all()
        latest_by_member: dict[UUID, datetime] = dict(latest_rows)
        for member_id in affected_member_ids:
            member = members.get(member_id)
            if member:
                member.last_checkin_at = latest_by_member.get(member_id)
                db.add(member)

    plans_updated = sum(
        ((event.details or {}).get("before") or {}).get("plan_name")
        != ((event.details or {}).get("after") or {}).get("plan_name")
        for event in snapshot_events
    )
    shifts_updated = sum(
        ((event.details or {}).get("before") or {}).get("preferred_shift")
        != ((event.details or {}).get("after") or {}).get("preferred_shift")
        for event in snapshot_events
    )
    rollback_id = uuid4()
    log_audit_event(
        db,
        "member_plan_shift_reconciliation_rolled_back",
        "reconciliation_batch",
        gym_id=gym_id,
        entity_id=rollback_id,
        details={
            "batch_id": str(batch_id),
            "rollback_id": str(rollback_id),
            "totals": {
                "members_restored": len(snapshot_events),
                "plans_restored": plans_updated,
                "shifts_restored": shifts_updated,
                "checkins_removed": len(batch_checkins),
            },
        },
        flush=False,
    )
    db.flush()
    return ApplyResult(
        batch_id=batch_id,
        members_updated=len(snapshot_events),
        plans_updated=plans_updated,
        shifts_updated=shifts_updated,
        checkins_imported=-len(batch_checkins),
    )


def write_reconciliation_report(plan: ReconciliationPlan, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(ReconciliationReportRow.__dataclass_fields__)
    with output_path.open("w", encoding="utf-8-sig", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for row in plan.report_rows:
            writer.writerow(asdict(row))


def write_dry_run_manifest(plan: ReconciliationPlan, output_path: Path) -> None:
    """Write aggregate review metadata only; no member identifiers or source rows."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "mode": "dry_run",
        "plan_digest": plan.digest(),
        "gym_id": str(plan.gym_id),
        "reference_at": plan.reference_at.isoformat(),
        "files": [
            {
                "kind": "members",
                "filename": plan.clients_filename,
                "sha256": plan.clients_sha256,
                "rows": plan.client_rows,
            },
            {
                "kind": "checkins",
                "filename": plan.access_filename,
                "sha256": plan.access_sha256,
                "rows": plan.access_rows,
            },
        ],
        "stats": plan.stats,
    }
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _verify_file(content: bytes, *, expected_sha256: str, label: str) -> str:
    actual = hashlib.sha256(content).hexdigest().upper()
    if actual != expected_sha256:
        raise ValueError(f"SHA-256 inesperado para {label}: {actual}. Apply bloqueado.")
    return actual


def _build_member_index(members: Iterable[Member]) -> _MemberIndex:
    member_map: dict[UUID, Member] = {}
    by_external_id: dict[str, set[UUID]] = defaultdict(set)
    by_cpf: dict[str, set[UUID]] = defaultdict(set)
    by_email: dict[str, set[UUID]] = defaultdict(set)
    by_name: dict[str, set[UUID]] = defaultdict(set)
    for member in members:
        member_map[member.id] = member
        for external_id in _external_id_candidates(str((member.extra_data or {}).get("external_id") or "")):
            by_external_id[external_id].add(member.id)
        if member.cpf_encrypted:
            try:
                cpf = _digits(decrypt_cpf(member.cpf_encrypted))
            except Exception:
                cpf = ""
            if cpf:
                by_cpf[cpf].add(member.id)
        if member.email:
            by_email[_normalize_text(member.email)].add(member.id)
        name = _normalize_text(member.full_name or "")
        if name:
            by_name[name].add(member.id)
    return _MemberIndex(
        members=member_map,
        by_external_id=dict(by_external_id),
        by_cpf=dict(by_cpf),
        by_email=dict(by_email),
        by_name=dict(by_name),
    )


def _match_row(row: dict[str, str], index: _MemberIndex, *, expected_plan: str | None) -> MatchDecision:
    resolved: dict[str, UUID] = {}
    ambiguous_methods: list[str] = []

    external_raw = _pick_first(row, EXTERNAL_ID_KEYS)
    if external_raw:
        candidates: set[UUID] = set()
        for key in _external_id_candidates(external_raw):
            candidates.update(index.by_external_id.get(key, set()))
        _record_identifier_resolution("codigo_acesso", candidates, resolved, ambiguous_methods)

    cpf = _digits(_pick_first(row, CPF_KEYS))
    if cpf:
        _record_identifier_resolution("cpf", index.by_cpf.get(cpf, set()), resolved, ambiguous_methods)

    email = _normalize_text(_pick_first(row, EMAIL_KEYS) or "")
    if email:
        _record_identifier_resolution("email", index.by_email.get(email, set()), resolved, ambiguous_methods)

    if ambiguous_methods:
        return MatchDecision(None, "+".join(ambiguous_methods), "ambiguous", "Identificador forte duplicado na base.")
    unique_members = set(resolved.values())
    if len(unique_members) > 1:
        return MatchDecision(None, "+".join(sorted(resolved)), "ambiguous", "Identificadores fortes apontam para membros diferentes.")
    if len(unique_members) == 1:
        member_id = next(iter(unique_members))
        methods = sorted(method for method, resolved_id in resolved.items() if resolved_id == member_id)
        return MatchDecision(member_id, "+".join(methods), "high", "Identificador forte unico.")

    name = _normalize_text(_extract_member_name(row) or "")
    name_candidates = index.by_name.get(name, set()) if name else set()
    if len(name_candidates) > 1:
        return MatchDecision(None, "name", "ambiguous", "Nome nao e unico na base.")
    if len(name_candidates) == 1:
        member_id = next(iter(name_candidates))
        member = index.members[member_id]
        corroborators: list[str] = []
        incoming_phone = _normalize_phone(_pick_first(row, PHONE_KEYS))
        if incoming_phone and incoming_phone == _normalize_phone(member.phone):
            corroborators.append("phone")
        incoming_join_date = _parse_date(_pick_first(row, JOIN_DATE_KEYS))
        if incoming_join_date and member.join_date == incoming_join_date:
            corroborators.append("join_date")
        if expected_plan and _normalize_text(member.plan_name or "") == _normalize_text(expected_plan):
            corroborators.append("plan")
        if corroborators:
            return MatchDecision(
                member_id,
                "name+" + "+".join(sorted(corroborators)),
                "review",
                "Nome unico e corroborado, mas sem identificador forte; revisao manual obrigatoria.",
            )
        return MatchDecision(None, "name", "unmatched", "Nome sem campo corroborador; correspondencia automatica bloqueada.")
    return MatchDecision(None, "none", "unmatched", "Nenhum identificador forte unico encontrado.")


def _bridge_access_decision_through_clients(
    row: dict[str, str],
    direct: MatchDecision,
    *,
    client_members_by_cpf: dict[str, set[UUID]],
) -> MatchDecision:
    """Resolve an access through a unique CPF shared by the approved exports."""

    if direct.confidence == "high":
        return direct
    if direct.confidence == "ambiguous" and direct.method != "name":
        return direct
    cpf = _digits(_pick_first(row, CPF_KEYS))
    if not cpf:
        return direct
    candidates = client_members_by_cpf.get(cpf, set())
    if len(candidates) == 1:
        return MatchDecision(
            next(iter(candidates)),
            "cpf_between_exports+client_strong",
            "high",
            "CPF unico entre os exports e cliente ligado por identificador forte unico.",
        )
    if len(candidates) > 1:
        return MatchDecision(
            None,
            "cpf_between_exports",
            "ambiguous",
            "CPF do acesso aponta para mais de um cliente fortemente identificado.",
        )
    return direct


def _record_identifier_resolution(
    method: str,
    candidates: set[UUID],
    resolved: dict[str, UUID],
    ambiguous_methods: list[str],
) -> None:
    if len(candidates) == 1:
        resolved[method] = next(iter(candidates))
    elif len(candidates) > 1:
        ambiguous_methods.append(method)


def _safe_plan_candidate(row: dict[str, str]) -> tuple[str, str | None, str] | None:
    primary = _pick_first(row, PLAN_NAME_SOURCE_KEYS)
    conditions = _pick_first(row, PLAN_CONDITION_KEYS)
    renewal = _pick_first(row, PLAN_RENEWAL_KEYS)
    if not primary and not conditions and not renewal:
        return None
    plan_name, cycle, cycle_source = _extract_plan_metadata(row, join_date=_parse_date(_pick_first(row, JOIN_DATE_KEYS)))
    normalized = _normalize_text(plan_name)
    if not normalized or normalized in {"plano base", "livre", "sem plano", "nao informado"}:
        return None
    return plan_name, cycle, cycle_source


def _parse_access_datetime(row: dict[str, str]) -> datetime | None:
    return _parse_checkin_datetime(
        checkin_raw=_pick_first(row, CHECKIN_AT_KEYS),
        date_raw=_pick_first(row, CHECKIN_DATE_KEYS),
        time_raw=_pick_first(row, CHECKIN_TIME_KEYS),
    )


def _load_checkin_rows(
    db: Session,
    *,
    gym_id: UUID,
    member_ids: set[UUID],
    start_at: datetime,
    end_at: datetime,
) -> list[tuple[UUID, datetime, int]]:
    if not member_ids:
        return []
    return list(
        db.execute(
            select(Checkin.member_id, Checkin.checkin_at, Checkin.hour_bucket).where(
                Checkin.gym_id == gym_id,
                Checkin.member_id.in_(member_ids),
                Checkin.checkin_at >= start_at,
                Checkin.checkin_at <= end_at,
            )
        ).all()
    )


def _load_existing_keys_for_prepared(
    db: Session,
    gym_id: UUID,
    prepared: list[PreparedCheckin],
) -> set[tuple[str, str]]:
    if not prepared:
        return set()
    rows = _load_checkin_rows(
        db,
        gym_id=gym_id,
        member_ids={item.member_id for item in prepared},
        start_at=min(item.checkin_at for item in prepared),
        end_at=max(item.checkin_at for item in prepared),
    )
    target_keys = {item.key for item in prepared}
    return {
        (str(member_id), _utc_datetime(checkin_at).isoformat())
        for member_id, checkin_at, _hour_bucket in rows
        if (str(member_id), _utc_datetime(checkin_at).isoformat()) in target_keys
    }


def _shift_for_hour(hour: int) -> str:
    if hour < 6:
        return "overnight"
    if hour < 12:
        return "morning"
    if hour < 18:
        return "afternoon"
    return "evening"


def _review_report_row(
    row: dict[str, str],
    decision: MatchDecision,
    *,
    expected_plan: str = "",
    plan_source: str = "",
    notes: str = "",
) -> ReconciliationReportRow:
    return ReconciliationReportRow(
        student=_extract_member_name(row) or "(sem nome)",
        member_id=str(decision.member_id or ""),
        current_plan="",
        expected_plan=expected_plan,
        plan_source=plan_source,
        current_shift="",
        expected_shift="",
        shift_source="",
        confidence=decision.confidence,
        proposed_action="manual_review" if decision.confidence != "high" else "no_change",
        match_method=decision.method,
        notes=notes or decision.reason,
    )


def _utc_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
