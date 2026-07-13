---
phase: 10-integridade-operacional-da-fila-de-tasks-do-piloto
plan: "01"
subsystem: api
tags: [fastapi, sqlalchemy, work-queue, pagination, tenant-isolation]
requires:
  - phase: 04.43.1-simplificacao-operacional-do-ai-inbox
    provides: Work Queue backend and operator-first execution contract
provides:
  - Typed Work Queue envelope with server-side search, pagination, effective state counts and explicit source truncation
  - Tenant-scoped cap-plus-one loaders for all five Work Queue sources
  - Canonical snooze visibility with legacy fallback and deterministic score/deadline/source ordering
affects: [10-02, 10-03, work-queue]
tech-stack:
  added: []
  patterns: [synthetic TestClient contract, cap-plus-one sentinel, effective-eligibility counts, canonical-legacy temporal compatibility]
key-files:
  created: [saas-backend/tests/test_work_queue_router.py]
  modified:
    - saas-backend/app/schemas/work_queue.py
    - saas-backend/app/routers/work_queue.py
    - saas-backend/app/services/work_queue_service.py
    - saas-backend/tests/test_work_queue_service.py
key-decisions:
  - "Push search into persisted tenant-scoped loaders before source caps; keep assessment search post-cap and declare that source truncated when its cap is reached."
  - "Compute state counts from the same filtered snapshot and clock while ignoring only the selected state tab."
  - "Read canonical work_queue_visible_from first, retain work_queue_snoozed_until as a compatibility fallback, and dual-write both during the transition."
patterns-established:
  - "Truthful snapshot envelope: items, total, page, page_size, state_counts and truncated_sources travel together."
  - "Stable queue ordering: scalar score descending, due_at ascending with null last, then source type and source id."
requirements-completed: [WQ-01, WQ-02, WQ-05]
duration: 17min
completed: 2026-07-13
---

# Phase 10 Plan 01: Work Queue Reachability and Truth Summary

**The backend now exposes a searchable, paginated and tenant-scoped Work Queue snapshot whose counts, source caps, snooze visibility and tie-breaking match the operator-visible truth.**

## Performance

- **Duration:** 17 min
- **Started:** 2026-07-13T18:09:54.3325292Z
- **Completed:** 2026-07-13T18:26:11.7862324Z
- **Tasks:** 3
- **Files modified:** 6

## Accomplishments

- Reached page 2 of a synthetic 188-item tenant snapshot and found records beyond the first 25 through server-side search over subject, reason and action.
- Added a typed six-field list envelope, effective state counts, per-source cap-plus-one detection and explicit `truncated_sources` without exposing the sentinel as data.
- Made canonical snooze visibility authoritative while preserving legacy reads and writes, and stabilized equal-score ordering by deadline and source identity.
- Kept every persisted loader tenant-scoped and verified the real FastAPI route entirely in-process with synthetic dependency overrides.

## TDD Evidence

### Wave 0 RED

- **Collection:** `py -3.12 -m pytest -q tests/test_work_queue_service.py tests/test_work_queue_router.py --collect-only -k "wq_"` collected `25/49` tests with exit `0`.
- **RED run:** `py -3.12 -m pytest -q tests/test_work_queue_service.py tests/test_work_queue_router.py -k "wq_"` returned `21 failed, 4 passed, 24 deselected` in `4.47s`.
- **Failure quality:** every RED case failed on a behavior assertion; there were no import, fixture or collection failures.

| Contract | Expected RED reason |
|---|---|
| 188-item page 2 and search beyond 25 | The legacy response had no complete pre-page search/pagination contract. |
| Effective `state_counts` | Counts were absent and eligibility was not evaluated independently of the selected state. |
| Cap-plus-one across five sources | Sources did not query/trim a sentinel or report truncation; explicit assessment loading was missing. |
| Tenant-scoped persisted queries | Loaders lacked the pushed-down search and cap-plus-one contract exercised by the synthetic statements. |
| Legacy/canonical snooze | The legacy timestamp was not a read fallback and mutations did not write the canonical key. |
| Equal-score ordering | Reverse tuple ordering put later/null deadlines first and had no stable source key. |
| Real route envelope and bounds | The route ignored `q`, serialized only four fields, and needed explicit pagination-bound coverage. |

The four initially passing cases were the exact visibility boundary and the three existing FastAPI bounds (`page=0`, `page_size=0`, `page_size=101`).

## Verification

- Task 2 owned slice: `22 passed, 27 deselected` in `4.04s`.
- Task 2 regression slice excluding only the three Task 3 RED contracts: `46 passed, 3 deselected` in `3.91s`.
- Task 3 focused legacy snooze, canonical write and deterministic ordering slice: `3 passed, 46 deselected` in `2.20s`.
- Full plan gate: `49 passed` in `3.90s`.
- Exact Wave 0 gate after implementation: `25 passed, 24 deselected` in `3.87s`.
- `git diff --check` completed without errors.

## Task Commits

Each task was committed atomically:

1. **Task 10-01-01: Freeze reachability and truth contracts** - `88c800a` (`test`)
2. **Task 10-01-02: Implement envelope, search, counts and truncation** - `d4cbf5b` (`feat`)
3. **Task 10-01-03: Canonicalize snooze and deterministic ordering** - `c0e51c1` (`fix`)

## Files Created/Modified

- `saas-backend/tests/test_work_queue_router.py` - Real TestClient contract for search forwarding, exact envelope, validation bounds and synthetic smoke.
- `saas-backend/tests/test_work_queue_service.py` - Synthetic regression coverage for 188 items, all source caps, tenant predicates, counts, snooze and ordering.
- `saas-backend/app/schemas/work_queue.py` - Typed additive Work Queue list envelope.
- `saas-backend/app/routers/work_queue.py` - Validated `q`, page and page-size inputs with the typed response model.
- `saas-backend/app/services/work_queue_service.py` - Tenant-scoped loaders, search, source truncation, effective counts, canonical visibility and stable ordering.
- `.planning/phases/10-integridade-operacional-da-fila-de-tasks-do-piloto/10-01-SUMMARY.md` - RED/GREEN evidence, decisions and handoff.

## Decisions Made

- Persisted sources search before their technical cap so a match beyond the first page remains reachable; assessment remains post-cap because its analytics service is outside this plan's ownership, and `truncated_sources` makes that lower bound explicit.
- `state_counts` reuses all active filters except state and the same deterministic `now`, so snoozed, cold-base and stale work cannot inflate `do_now`.
- The route imports `WorkQueueListOut` directly from `app.schemas.work_queue`, avoiding an unrelated schema barrel change.
- Existing `due_date` compatibility remains untouched; only `visible_from` decides snooze eligibility, and `due_at` remains the authoritative deadline tie-breaker.

## Deviations from Plan

### Execution-sequence adjustment

- **Found during:** Task 10-01-02 verification.
- **Issue:** The plan's Task 2 selector `-k "wq_"` also selected the three intentionally RED Task 3 contracts.
- **Resolution:** Used an explicit Task 2-owned subset for its atomic GREEN commit, ran a regression slice excluding only those three IDs, and preserved the exact broad selector as the mandatory Task 3 gate.
- **Impact:** Verification sequencing only; no product behavior or scope changed.

**Total deviations:** 1 execution-sequence adjustment. No migration, claim/CAS, consent check, provider idempotency, provider call, deployment or Phase 10.1 behavior was added.

## Issues Encountered

None beyond the selector overlap documented above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 10-02 can build deduplication, freshness and AI recommendation readiness on the truthful snapshot contract.
- Plan 10-03 can integrate the runner and cross-surface smoke against the stable six-field envelope.
- Phase 10 remains in execution until Plans 10-02 and 10-03 complete; no deployment was performed by this plan.

---
*Phase: 10-integridade-operacional-da-fila-de-tasks-do-piloto*
*Completed: 2026-07-13*
