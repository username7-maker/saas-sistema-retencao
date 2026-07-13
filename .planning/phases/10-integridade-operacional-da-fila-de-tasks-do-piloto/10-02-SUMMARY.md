---
phase: 10-integridade-operacional-da-fila-de-tasks-do-piloto
plan: "02"
subsystem: api
tags: [fastapi, sqlalchemy, ai-triage, work-queue, task-reuse, readiness]
requires:
  - phase: 10-integridade-operacional-da-fila-de-tasks-do-piloto
    plan: "01"
    provides: Work Queue truth envelope and tenant-scoped loaders
provides:
  - Sequential tenant-scoped reuse of active onboarding tasks for AI triage preparation
  - Canonical prepared task link persisted in payload_snapshot.metadata
  - Additive Work Queue readiness payload with canonical task, freshness, assignment and known/unknown signal state
affects: [10-03, work-queue, ai-triage]
tech-stack:
  added: []
  patterns: [snapshot metadata link, active-task equivalence key, freshness max-age, readiness missing fields]
key-files:
  modified:
    - saas-backend/app/schemas/ai_triage.py
    - saas-backend/app/schemas/work_queue.py
    - saas-backend/app/services/ai_triage_service.py
    - saas-backend/app/services/work_queue_service.py
    - saas-backend/tests/test_ai_triage_service.py
    - saas-backend/tests/test_work_queue_service.py
key-decisions:
  - "Reuse is sequential only: prepared_task_id, active work_queue_equivalence_key/legacy onboarding evidence, then create."
  - "Preparation persists the canonical task link without refreshing last_refreshed_at, so freshness remains tied to the recommendation snapshot."
  - "Readiness is additive and explicit: unknown signal remains unknown, while a persisted zero remains known and noncritical."
  - "Phase 10.1 boundaries remain out of scope: no migration, unique constraint, lock, claim/CAS, consent, provider or idempotency behavior."
requirements-completed: [WQ-03, WQ-04]
completed: 2026-07-13
---

# Phase 10 Plan 02: Canonical Task Reuse and Readiness Summary

AI triage preparation now converges sequentially to one active canonical onboarding task instead of creating duplicates, and Work Queue items expose enough readiness context for the UI to decide between creating, continuing and investigating missing data.

## Accomplishments

- Added RED coverage for repeated preparation, active equivalent task reuse, ineligible task exclusion, canonical task IDs, freshness, assignment, readiness gaps and legacy zero score semantics.
- Added `work_queue_equivalence_key` reuse for onboarding recommendations without adding a database constraint or promising concurrent uniqueness.
- Made `payload_snapshot.metadata.prepared_task_id` the durable sequential link and rejected broken, inactive, deleted, archived, cross-tenant and cross-member candidates.
- Validated the Work Queue `awaiting_outcome` shortcut against the same canonical task resolver before returning a task id, so a broken snapshot link does not become a false "continue task" action.
- Hardened adversarial reuse edges: auto-approval during prepare no longer refreshes the snapshot clock, `assign_owner` uses the canonical resolver, blank `source_domain` falls back to `domain`, and invalid nested `canonical_task_id` is removed from `awaiting_outcome` responses.
- Kept `last_refreshed_at` unchanged during prepare actions so stale recommendations do not become fresh because an operator clicked a CTA.
- Added additive Work Queue fields: `canonical_task_id`, `last_refreshed_at`, `freshness_state`, `freshness_blocking`, `readiness_missing_fields`, `signal_value`, `priority_state`, `assigned_to_name` and `assigned_to_role`.
- Scoped assigned-user serialization through the Task loader query instead of per-item lookups.

## TDD Evidence

### Wave 0 RED

- **RED run:** `py -3.12 -m pytest -q tests/test_ai_triage_service.py tests/test_work_queue_service.py -k "test_wq_reuse_ or test_wq_readiness_"` returned `6 failed, 6 passed, 76 deselected` in `2.68s`.
- **Failure quality:** the six failures were behavior assertions or missing additive fields: sequential prepare called `create_task` twice, active equivalent task was ignored, Work Queue lacked canonical/readiness fields, and Task loader did not scope `assigned_user`.
- **Passing new cases:** the ineligible candidate matrix already behaved correctly by not reusing invalid tasks, and remains as regression coverage.

### GREEN

- **Focused GREEN:** `12 passed, 76 deselected` in `2.16s`.
- **Plan gate:** `py -3.12 -m pytest -q tests/test_ai_triage_service.py tests/test_work_queue_service.py` returned `88 passed` in `2.45s`.
- **Relevant backend gate:** Work Queue, AI triage, Autopilot, AI Service Agent, Student Personal AI and Assessment Queue returned `123 passed` in `4.46s`.
- **Awaiting-outcome RED:** `1 failed, 66 deselected` in `2.41s`, proving the shortcut returned a raw `prepared_task_id` even when canonical validation failed.
- **Final plan gate:** `89 passed` in `2.55s` after validating the shortcut.
- **Final relevant backend gate:** Work Queue, AI triage, Autopilot, AI Service Agent, Student Personal AI and Assessment Queue returned `124 passed` in `4.83s`.
- **Adversarial reuse RED:** `8 failed, 3 passed, 88 deselected` in `2.69s`, covering stale auto-approval refresh, raw `assign_owner`, SQL/Python blank-domain drift and nested raw `canonical_task_id`.
- **Adversarial reuse GREEN:** `11 passed, 88 deselected` in `2.18s`.
- **Final adversarial plan gate:** `99 passed` in `2.52s`.
- **Final adversarial relevant backend gate:** Work Queue, AI triage, Autopilot, AI Service Agent, Student Personal AI and Assessment Queue returned `134 passed` in `4.50s`.
- **Import-order gate:** `py -3.12 -m ruff check --select I app/schemas/ai_triage.py app/schemas/work_queue.py app/services/ai_triage_service.py app/services/work_queue_service.py` passed.
- **Diff gate:** `git diff --check` passed.
- **Boundary check:** changed files were limited to schemas, services, tests and this summary. No migration/model/unique constraint/lock/claim/CAS/consent/idempotency/provider behavior was added.

## Behavioral Notes

- Reuse order is deterministic: valid `prepared_task_id`, then active equivalent onboarding task evidence, then creation.
- Active means `TODO` or `DOING`, same `gym_id`, same `member_id`, not soft-deleted and not operationally archived.
- Legacy reuse requires persisted onboarding evidence in `extra_data`; title text alone is not evidence.
- Exact concurrent duplicate prevention remains deliberately unsolved here and belongs to Phase 10.1.

## Task Commits

1. **Task 10-02-01: Freeze reuse and readiness contracts** - `d88a591` (`test`)
2. **Task 10-02-02/03: Implement canonical reuse and readiness payload** - `7f740d2` (`feat`)
3. **Awaiting outcome canonical validation** - `268e7b6` (`test`)
4. **Awaiting outcome implementation** - `fa9f137` (`fix`)
5. **Adversarial reuse validation contracts** - `70e11d4` (`test`)
6. **Adversarial reuse hardening implementation** - `5c10075` (`fix`)
