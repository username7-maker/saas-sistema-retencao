---
phase: 10-integridade-operacional-da-fila-de-tasks-do-piloto
plan: "01"
subsystem: api
tags: [fastapi, sqlalchemy, work-queue, pagination, tenant-isolation, rbac, pii, search]
requires:
  - phase: 04.43.1-simplificacao-operacional-do-ai-inbox
    provides: Work Queue backend and operator-first execution contract
provides:
  - Typed Work Queue envelope with server-side search, pagination, effective state counts and explicit source truncation
  - Tenant-scoped cap-plus-one loaders for all five Work Queue sources
  - Canonical snooze visibility with legacy fallback and deterministic score/deadline/source ordering
  - SQL search parity for derived operator labels and tenant-scoped agent subjects
  - Pre-cap RBAC/domain bucketization plus tenant-safe batched Member and Lead resolution
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
  - "Mirror visible Task and agent action labels with SQL CASE expressions, then retain Python matching as the final truth."
  - "Resolve agent identities and Task relationships only through gym_id/deleted_at-scoped statements; never serialize an unresolved foreign identifier."
patterns-established:
  - "Truthful snapshot envelope: items, total, page, page_size, state_counts and truncated_sources travel together."
  - "Stable queue ordering: scalar score descending, due_at ascending with null last, then source type and source id."
  - "Authorization before cap: role and requested domain define the source universe before cap-plus-one and global slicing."
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
- Remediated SQL/Python search drift for visible Task and Kommo action labels, including `Registrar resultado`, `Preparar na Kommo` and `Preparar resposta Kommo`.
- Removed per-action `db.get(Member, ...)`, batched agent identity resolution, suppressed unresolved cross-tenant IDs/paths and made Task relationships tenant/deleted scoped at serialization time.
- Moved AI Service Agent role predicates and Assessment role/domain buckets before their technical caps, with exclusions applied before the global sentinel.

## Remediation Follow-up - 2026-07-13

An adversarial post-plan review found three P1 classes in the otherwise-green implementation: the SQL prefilter did not include every value the operator could see, agent Member resolution was unscoped and N+1, and role filtering after source caps could starve authorized work. Two P2 hardening gaps were also confirmed: `%`/`_` acted as SQL wildcards and naive `scheduled_for` values were silently interpreted as UTC.

The remediation remained inside Plan 10-01 ownership:

- Added canonical SQL `CASE` expressions for Task and agent status/action labels while preserving `_matches_search` as the final materialized truth.
- Added tenant/deleted-scoped Member and Lead joins/lookups, batched list resolution, safe fallback names and removal of unresolved foreign UUIDs from the response/context path.
- Reused one scoped Task statement with `contains_eager` so the relationships serialized by `_task_to_item` are the same tenant-safe joins used by the query.
- Added AI Service Agent intent predicates before `LIMIT` for trainer (`assessment`/`injury`) and salesperson (`sales`).
- Bucketized Assessment before the global cap by role and requested domain, preserving the required operational order, applying exclusions before the sentinel and avoiding false truncation from raw totals alone.
- Escaped `%` and `_` as literal search characters and rejected naive snooze datetimes with a clear Pydantic/FastAPI 422 while continuing to accept timezone-aware timestamps.

No migration, model, frontend, deployment, claim/CAS, consent, effect idempotency or provider behavior was introduced.

### Remediation performance

- **Started:** 2026-07-13T18:47:30.0601153Z
- **Completed:** 2026-07-13T19:14:06.2642173Z
- **Duration:** 27 min
- **Product files changed:** 2
- **Regression files changed:** 2

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

### Remediation RED / GREEN

- **Baseline before remediation:** `49 passed` in `3.89s` for the full Plan 10-01 backend pair.
- **Primary RED:** `14 failed, 26 passed, 24 deselected` in `4.76s`. Every failure was a behavior assertion for label reachability, tenant identity, N+1, pre-cap authorization, assessment truncation, wildcard escaping or timezone validation; there were no import, fixture or collection errors.
- **Primary GREEN:** `40 passed, 24 deselected` in `4.03s` for the exact `-k "wq_"` remediation slice.
- **Independent tenant-backstop RED:** `4 failed, 54 deselected` in `2.67s`, proving duplicate/unscoped Task relationship joins and raw cross-tenant agent identifiers still leaked after safe fallback names.
- **Independent tenant-backstop GREEN:** `4 passed, 54 deselected` in `2.10s` after scoped Task eager loading and identifier/path suppression.
- **Assessment-domain RED:** `1 failed, 58 deselected` in `2.35s`, reproducing owner/manager `domain=trainer` starvation behind `never` rows.
- **Assessment-domain GREEN:** `1 passed, 58 deselected` in `1.93s` after intersecting requested domain with the role bucket plan before the cap.
- **Adversarial follow-up RED:** `4 failed, 58 deselected` in `2.37s`, proving two remaining P1 gaps: unresolved Task Member/Lead FKs still serialized as IDs/paths, and `covered` assessment items were missing from the trainer bucket plan.
- **Adversarial follow-up GREEN:** `4 passed, 58 deselected` in `2.14s` after suppressing unresolved Task relationship identifiers/paths and restoring `covered` as a trainer/owner-domain operational bucket.

Post-RED edits to regression files did not weaken the frozen contracts. The only mechanical changes were import sorting, blank-line normalization and wrapping one long assertion; behavior assertions were only added, never removed or broadened.

## Verification

- Task 2 owned slice: `22 passed, 27 deselected` in `4.04s`.
- Task 2 regression slice excluding only the three Task 3 RED contracts: `46 passed, 3 deselected` in `3.91s`.
- Task 3 focused legacy snooze, canonical write and deterministic ordering slice: `3 passed, 46 deselected` in `2.20s`.
- Full plan gate: `49 passed` in `3.90s`.
- Exact Wave 0 gate after implementation: `25 passed, 24 deselected` in `3.87s`.
- `git diff --check` completed without errors.
- Remediation final Plan 10-01 gate: `66 passed` in `4.02s`.
- Remediation relevant backend gate (Work Queue, AI triage, Autopilot, AI Service Agent, Student Personal AI and Assessment Queue): `108 passed` in `4.38s`.
- Final Plan 10-01 gate after adversarial follow-up: `69 passed` in `4.79s`.
- Final relevant backend gate after adversarial follow-up (Work Queue, AI triage, Autopilot, AI Service Agent, Student Personal AI and Assessment Queue): `111 passed` in `4.80s`.
- PostgreSQL-dialect compilation succeeded for Task, AI Service Agent and Student Personal AI statements; all three emitted explicit `ESCAPE` handling for literal wildcard input.
- Product import-order gate: `py -3.12 -m ruff check --select I app/schemas/work_queue.py app/services/work_queue_service.py` passed.
- Product import-order gate after adversarial follow-up: `py -3.12 -m ruff check --select I app/services/work_queue_service.py` passed.
- Forbidden-boundary audit returned `boundary-clean`; no migration/model/frontend/claim/CAS/consent/idempotency/provider addition was present.
- `requirements-completed: [WQ-01, WQ-02, WQ-05]` was retained only after the final `69 passed` plan gate and `111 passed` relevant backend gate were green.

### Self-check: PASS

- All five remediation commits resolve as commit objects.
- Every artifact named by the remediation exists in the worktree.
- `git diff --check` passed and `.planning/STATE.md` still reads `Plan: 2 of 3`.

## Task Commits

Each task was committed atomically:

1. **Task 10-01-01: Freeze reachability and truth contracts** - `88c800a` (`test`)
2. **Task 10-01-02: Implement envelope, search, counts and truncation** - `d4cbf5b` (`feat`)
3. **Task 10-01-03: Canonicalize snooze and deterministic ordering** - `c0e51c1` (`fix`)
4. **Remediation contracts: SQL parity, tenant identity, RBAC/cap, wildcards and timezone** - `7e77644` (`test`)
5. **Tenant backstop contracts: serialized relationships and unresolved identifiers** - `aff8706` (`test`)
6. **Remediation implementation: search, RBAC, scoped identities and timezone** - `c588232` (`fix`)
7. **Assessment requested-domain pre-cap regression** - `f4976a1` (`test`)
8. **Assessment requested-domain pre-cap implementation** - `a6509c3` (`fix`)
9. **Adversarial follow-up contracts: unresolved Task links and covered bucket** - `f9072ca` (`test`)
10. **Adversarial follow-up implementation: safe Task serialization and covered bucket** - `4c3c144` (`fix`)

## Files Created/Modified

- `saas-backend/tests/test_work_queue_router.py` - Real TestClient contract for search forwarding, exact envelope, validation bounds and synthetic smoke.
- `saas-backend/tests/test_work_queue_service.py` - Synthetic regression coverage for 188 items, all source caps, tenant predicates, counts, snooze and ordering.
- `saas-backend/app/schemas/work_queue.py` - Typed additive Work Queue list envelope.
- `saas-backend/app/routers/work_queue.py` - Validated `q`, page and page-size inputs with the typed response model.
- `saas-backend/app/services/work_queue_service.py` - Tenant-scoped loaders, search, source truncation, effective counts, canonical visibility and stable ordering.
- `saas-backend/app/services/work_queue_service.py` remediation - Canonical label expressions, literal LIKE escaping, scoped/batched identities, scoped Task relationships and pre-cap role/domain buckets.
- `saas-backend/app/schemas/work_queue.py` remediation - Timezone-aware `scheduled_for` contract with clear validation failure.
- `saas-backend/tests/test_work_queue_service.py` remediation - Adversarial statement, role distribution, cross-tenant identity, cap and wildcard regressions.
- `saas-backend/tests/test_work_queue_router.py` remediation - Naive 422 and aware datetime route contracts.
- `.planning/phases/10-integridade-operacional-da-fila-de-tasks-do-piloto/10-01-SUMMARY.md` - RED/GREEN evidence, decisions and handoff.

## Decisions Made

- Persisted sources search before their technical cap so a match beyond the first page remains reachable; assessment remains post-cap because its analytics service is outside this plan's ownership, and `truncated_sources` makes that lower bound explicit.
- `state_counts` reuses all active filters except state and the same deterministic `now`, so snoozed, cold-base and stale work cannot inflate `do_now`.
- The route imports `WorkQueueListOut` directly from `app.schemas.work_queue`, avoiding an unrelated schema barrel change.
- Existing `due_date` compatibility remains untouched; only `visible_from` decides snooze eligibility, and `due_at` remains the authoritative deadline tie-breaker.
- SQL prefilters mirror operator-visible derived labels instead of hidden raw metadata; Python `_matches_search` remains the final response truth.
- Agent identity is considered resolved only after `id + gym_id + deleted_at` validation. Missing or foreign Member/Lead records produce a generic subject and no foreign identifier or context path.
- Assessment role and requested domain choose the operational bucket plan before the source cap; the cap and sentinel remain global across the selected buckets.
- Naive write timestamps are rejected instead of being guessed as UTC; legacy naive values remain readable through the compatibility parser.

## Deviations from Plan

### Execution-sequence adjustment

- **Found during:** Task 10-01-02 verification.
- **Issue:** The plan's Task 2 selector `-k "wq_"` also selected the three intentionally RED Task 3 contracts.
- **Resolution:** Used an explicit Task 2-owned subset for its atomic GREEN commit, ran a regression slice excluding only those three IDs, and preserved the exact broad selector as the mandatory Task 3 gate.
- **Impact:** Verification sequencing only; no product behavior or scope changed.

### Post-completion adversarial remediation

- **Found during:** Independent review after the original Plan 10-01 summary.
- **Issue:** Green happy-path tests did not prove SQL/serializer parity, tenant-safe identity hydration or role/domain authorization before source caps.
- **Resolution:** Added three explicit RED cycles, implemented only the no-migration read/validation fixes owned by 10-01, and reran the full relevant backend gate.
- **Impact:** Strengthened WQ-01/WQ-02 tenant/search truth without changing the response shape, ledger, provider behavior or Phase 10.1 boundary.

**Total deviations:** 1 execution-sequence adjustment and 1 adversarial remediation follow-up. No migration, claim/CAS, consent check, provider idempotency, provider call, deployment or Phase 10.1 behavior was added.

## Issues Encountered

- The original implementation passed its planned gates but still had contract overlap gaps that only adversarial distribution, cross-tenant corruption and literal wildcard cases exposed.
- All in-scope P1 findings were closed before this summary update; remaining limitations are listed under `CONCERNS` rather than being silently treated as complete behavior.

## User Setup Required

None - no external service configuration required.

## CONCERNS

- **P2 - `state_counts` schema completeness:** `WorkQueueListOut.state_counts` is typed as a dictionary and therefore does not make all three keys structurally mandatory. The service currently emits `do_now`, `awaiting_outcome` and `done` on every response and tests assert the complete shape, but a future serializer refactor could omit one key without Pydantic rejecting it.
- **Known lower-bound - Assessment search:** Assessment Queue search intentionally remains post-cap because `assessment_analytics_service` is outside Plan 10-01 ownership. A match after the selected source cap can remain unreachable; whenever that cap is hit, `assessment_queue` stays in `truncated_sources` and totals/search results must be interpreted as lower bounds.
- **P2 - malformed JSON metadata:** Canonical SQL expressions assume producer-owned label, message and intent metadata are strings. Python remains the final filter, so hidden raw metadata is not returned as a false positive, but malformed legacy non-string JSON could still create a SQL false negative until write-path type guarantees are centralized.
- **Contract change:** `scheduled_for` without timezone now returns 422. Current frontend timestamps include `Z`/offset and the aware path is covered, but any external consumer relying on implicit UTC must add an explicit timezone.
- **Explicit non-claims:** This remediation does not prove exact totals for a truncated Assessment source, concurrent claim/deduplication, consent, provider idempotency, deployment parity or any Phase 10.1 behavior.

## Next Phase Readiness

- Plan 10-02 can build deduplication, freshness and AI recommendation readiness on the truthful snapshot contract.
- Plan 10-03 can integrate the runner and cross-surface smoke against the stable six-field envelope.
- Phase 10 remains in execution until Plans 10-02 and 10-03 complete; no deployment was performed by this plan.
- `.planning/STATE.md` deliberately remains at **Plan 2 of 3**; this remediation did not advance the phase.

---
*Phase: 10-integridade-operacional-da-fila-de-tasks-do-piloto*
*Completed: 2026-07-13*
