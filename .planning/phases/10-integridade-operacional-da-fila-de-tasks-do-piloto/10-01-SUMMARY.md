---
phase: 10-integridade-operacional-da-fila-de-tasks-do-piloto
plan: "01"
subsystem: api
tags: [fastapi, sqlalchemy, work-queue, pagination, tenant-isolation]
requires:
  - phase: 04.43.1-simplificacao-operacional-do-ai-inbox
    provides: Work Queue backend and operator-first execution contract
provides:
  - Work Queue list contract tests for reachability, truthful counts, truncation, snooze and ordering
affects: [10-02, 10-03, work-queue]
tech-stack:
  added: []
  patterns: [synthetic TestClient contract, cap-plus-one sentinel]
key-files:
  created: [saas-backend/tests/test_work_queue_router.py]
  modified: [saas-backend/tests/test_work_queue_service.py]
key-decisions:
  - "Use the real FastAPI route with dependency overrides to freeze Query validation and the six-field envelope."
patterns-established:
  - "Wave 0 RED failures are behavior assertions over synthetic data; no credential, provider or network is used."
requirements-completed: []
duration: in-progress
completed: pending
---

# Phase 10 Plan 01: Work Queue Reachability and Truth Summary

**Execution in progress; Wave 0 freezes the backend contract before implementation.**

## Wave 0 RED Evidence

- **Command:** `py -3.12 -m pytest -q tests/test_work_queue_service.py tests/test_work_queue_router.py -k "wq_"`
- **Result before implementation:** exit `1`; `21 failed, 4 passed, 24 deselected` in `4.47s`.
- **Collection gate:** `25/49 tests collected (24 deselected)` with exit `0`.
- **Failure quality:** all RED cases failed on behavior assertions; there were no import, fixture or collection failures.

| Test ID | Expected RED reason |
|---|---|
| `test_wq_dataset_188_reaches_page_two_without_repeating_page_one` | List response has no truncation metadata. |
| `test_wq_search_finds_item_after_first_25_before_pagination[subject_name/reason/primary_action_label]` | Service has no `q` contract or pre-page search. |
| `test_wq_state_counts_ignore_only_state_and_use_effective_eligibility` | Service has no `q` or authoritative `state_counts`. |
| `test_wq_cap_plus_one_marks_source_and_excludes_sentinel[task/ai_triage/assessment_queue/ai_service_agent/student_personal_ai]` | Source caps do not query/trim a sentinel or declare truncation; explicit assessment source is skipped. |
| `test_wq_explicit_assessment_source_runs_dedicated_loader` | `source=assessment_queue` does not execute its loader. |
| `test_wq_persisted_loader_query_is_tenant_scoped_searchable_and_cap_plus_one[_list_task_items/_list_ai_items/_list_ai_service_agent_items/_list_student_personal_ai_items]` | Persisted loaders do not accept pushed-down search and still use cap rather than cap plus one. |
| `test_wq_assessment_loader_is_tenant_scoped_cap_plus_one_and_searches_post_cap` | Assessment loader has no post-cap search contract and requests only 200 rows. |
| `test_wq_legacy_snooze_is_visible_from_fallback_and_canonical_value_wins` | Legacy snooze timestamp is not read as fallback. |
| `test_wq_equal_scores_sort_due_ascending_null_last_then_stable_source_key` | Existing reverse tuple sort puts null/later deadlines first and has no stable source key. |
| `test_wq_snooze_outcome_writes_canonical_and_legacy_visibility` | Snooze mutation does not write canonical `work_queue_visible_from`. |
| `test_wq_list_route_forwards_search_and_returns_exact_envelope` | Route ignores `q` and its response model drops the two new envelope fields. |
| `test_wq_synthetic_smoke_uses_in_process_overrides_only` | Real route serializes only the legacy four-field page shape. |

The four passing Wave 0 cases were the exact `visible_from` boundary and the three existing FastAPI pagination bounds (`page=0`, `page_size=0`, `page_size=101`).

## Task 10-01-02 GREEN Evidence

- **Owned subset:** `py -3.12 -m pytest -q tests/test_work_queue_service.py tests/test_work_queue_router.py -k "wq_ and not legacy_snooze and not equal_scores and not snooze_outcome"`
- **Result:** exit `0`; `22 passed, 27 deselected` in `4.04s`.
- **Regression subset:** both files excluding only the three Task 10-01-03 RED cases returned `46 passed, 3 deselected` in `3.91s`.
- **Broad Wave 0 command:** `22 passed` with exactly three expected RED IDs reserved for Task 10-01-03: `test_wq_legacy_snooze_is_visible_from_fallback_and_canonical_value_wins`, `test_wq_equal_scores_sort_due_ascending_null_last_then_stable_source_key`, and `test_wq_snooze_outcome_writes_canonical_and_legacy_visibility`.
- **Sequence adjustment:** the plan's Task 10-01-02 `-k "wq_"` selector also includes Task 10-01-03 contracts. The narrower owned subset preserves atomic commits; the exact broad command remains the mandatory Task 10-01-03 gate.

## Performance

- **Started:** 2026-07-13T18:09:54.3325292Z
- **Completed:** pending
- **Tasks:** 2 of 3 in progress

## Task Commits

1. **Task 10-01-01: Wave 0 contract freeze** - `88c800a` (`test`)
2. **Task 10-01-02: Envelope, search, counts and truncation** - pending commit

## Deviations from Plan

None at Wave 0.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Task 10-01-02 can start after the Wave 0 test commit.

---
*Phase: 10-integridade-operacional-da-fila-de-tasks-do-piloto*
*Completed: pending*
