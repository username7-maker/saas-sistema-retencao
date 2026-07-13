---
phase: 10
slug: integridade-operacional-da-fila-de-tasks-do-piloto
status: approved
nyquist_compliant: true
wave_0_complete: false
created: 2026-07-13
---

# Phase 10 - Validation Strategy

> Contrato de feedback rapido para alcance, verdade do snapshot, reuso, frescor, snooze e runner compartilhado. Claim/CAS e efeitos externos pertencem a Phase 10.1 e nao podem ser declarados validados aqui.

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Backend framework** | pytest 9.0.3 |
| **Frontend framework** | Vitest 4.0.18 + Testing Library 16.3.2 |
| **Backend quick run** | `py -3.12 -m pytest -q tests/test_work_queue_service.py tests/test_ai_triage_service.py` (from `saas-backend`) |
| **Frontend quick run** | `npm.cmd test -- --run src/test/WorkExecutionView.test.tsx` (from `saas-frontend`) |
| **Full focused suite** | backend five-file slice + shared runner + both route suites |
| **Task-level feedback** | Target below 30s for each task command |
| **Full-gate latency** | Measured separately after all tasks; no 30s ceiling |

## Baseline Freeze

| Area | Observed before Phase 10 | Treatment |
|------|--------------------------|-----------|
| Backend focused | 48 passed | Must remain green |
| `AITriageInboxPage` | 9/9 passed before Wave 0 | Every existing and added test, including the synthetic smoke, must pass; final count is not fixed |
| `TasksPage` | 9/12 passed before Wave 0 | Repair the three pre-existing failures and pass every added smoke test; final count is not fixed |

The three existing frontend failures are one stale copy assertion and two ambiguous `Onboarding` role queries. They are test debt, not evidence that Phase 10 regressed the product.

## Sampling Rate

- **After every backend task commit:** run the smallest affected pytest file(s).
- **After every frontend task commit:** run `WorkExecutionView.test.tsx` plus the affected route wrapper.
- **After every plan wave:** run the full focused backend/frontend suite.
- **Before `$gsd-verify-work`:** focused suites, typecheck/build, lint, `specify check` and `git diff --check` must pass.
- **Max feedback latency:** 30 seconds applies only to task-level checks; the aggregated full gate is measured separately and has no artificial ceiling.

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 10-01-01 | 01 | 0 | WQ-01/WQ-02 | backend RED contract | `py -3.12 -m pytest -q tests/test_work_queue_service.py tests/test_work_queue_router.py -k "wq_"` under the expected-RED guard from Plan 01 | service exists; router created in Wave 0 | pending |
| 10-01-02 | 01 | 1 | WQ-01/WQ-02 | backend reachability | `py -3.12 -m pytest -q tests/test_work_queue_service.py tests/test_work_queue_router.py -k "wq_"` | Wave 0 files | pending |
| 10-01-03 | 01 | 1 | WQ-05 | backend clock/order | `py -3.12 -m pytest -q tests/test_work_queue_service.py tests/test_work_queue_router.py` | existing + Wave 0 router | pending |
| 10-02-01 | 02 | 0 | WQ-03/WQ-04 | backend RED reuse/readiness | `py -3.12 -m pytest -q tests/test_ai_triage_service.py tests/test_work_queue_service.py -k "test_wq_reuse_ or test_wq_readiness_"` under the expected-RED guard from Plan 02 | existing, new cases required | pending |
| 10-02-02 | 02 | 2 | WQ-03 | sequential reuse | `py -3.12 -m pytest -q tests/test_ai_triage_service.py -k "test_wq_reuse_"` | Wave 0 cases | pending |
| 10-02-03 | 02 | 2 | WQ-04 | serializer/readiness | `py -3.12 -m pytest -q tests/test_ai_triage_service.py tests/test_work_queue_service.py -k "test_wq_readiness_"` | Wave 0 cases | pending |
| 10-03-01 | 03 | 0 | WQ-01/WQ-02/WQ-08 | wrappers green + runner RED | `npm.cmd test -- --run src/test/TasksPage.test.tsx src/test/AITriageInboxPage.test.tsx`, then expected-RED guard for `WorkExecutionView.test.tsx` titles `WQ runner` | runner test created in Wave 0 | pending |
| 10-03-02 | 03 | 3 | WQ-01/WQ-02/WQ-03/WQ-04/WQ-05 | component/regression | `npm.cmd test -- --run src/test/WorkExecutionView.test.tsx src/test/AITriageInboxPage.test.tsx src/test/TasksPage.test.tsx` | Wave 0 runner + existing wrappers | pending |
| 10-03-03 | 03 | 3 | WQ-08 | in-process synthetic smoke | backend `test_work_queue_router.py -k synthetic_smoke` + frontend wrappers `-t "smoke sintetico"` | Wave 0 cases; output in 10-03-SUMMARY.md | pending |

## Wave 0 Requirements

- [ ] Add list envelope/search/count/truncation cases to `saas-backend/tests/test_work_queue_service.py` and create `saas-backend/tests/test_work_queue_router.py` for the real route/422 Query seam.
- [ ] Add canonical snooze fallback and deterministic due-order cases.
- [ ] Add `test_wq_reuse_*` and `test_wq_readiness_*` with expected-RED guard, sequential MagicMock proof and legacy-zero provenance cases.
- [ ] Create `saas-frontend/src/test/WorkExecutionView.test.tsx` with `WQ runner` titles and expected-RED guard after both wrappers are green.
- [ ] Repair the three pre-existing `TasksPage.test.tsx` assertions without weakening selectors.
- [ ] Add backend `test_wq_synthetic_smoke` plus frontend `smoke sintetico /tasks` and `smoke sintetico /ai/triage` using only in-process mocks.

No new test framework or dependency is required.

## Full Focused Commands

The commands below are the final aggregated gate after all tasks. Their runtime is recorded independently and is not subject to the 30-second task-level target.

```powershell
# saas-backend
py -3.12 -m pytest -q tests/test_work_queue_service.py tests/test_work_queue_router.py tests/test_ai_triage_service.py tests/test_ai_triage_router.py tests/test_autopilot_services.py

# saas-frontend
npm.cmd test -- --run src/test/WorkExecutionView.test.tsx src/test/AITriageInboxPage.test.tsx src/test/TasksPage.test.tsx
npm.cmd run build
npm.cmd run lint

# repository root
specify check
git diff --check
```

## Reproducible Synthetic Smoke

```powershell
# saas-backend
py -3.12 -m pytest -q tests/test_work_queue_router.py -k synthetic_smoke

# saas-frontend
npm.cmd test -- --run src/test/AITriageInboxPage.test.tsx src/test/TasksPage.test.tsx -t "smoke sintetico"
```

Both commands run in-process with TestClient/dependency overrides or MemoryRouter/QueryClient/service mocks. `10-03-SUMMARY.md` records each command, exit code and concise output separately for backend and frontend; no public credential or network access is permitted.

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Desktop/mobile hierarchy and keyboard traversal | WQ-08 | Component tests do not prove final responsive composition | Open synthetic local tenant at desktop and mobile widths; traverse filters, search, page controls and cards using keyboard only |
| Published asset/API compatibility | WQ-08 | Requires deployed frontend/backend pair | After explicit deploy authorization, verify public health/401 edge and use only a synthetic authenticated tenant for page 2/search |

## Explicit Non-Claims

- No PostgreSQL two-session proof exists in this phase.
- No provider exactly-once or consent closure is claimed in this phase.
- `total` is exact only when `truncated_sources` is empty; otherwise the UI must say `Pelo menos N`.

## Validation Sign-Off

- [x] All tasks have an automated command or Wave 0 dependency.
- [x] No three consecutive implementation tasks lack automated feedback.
- [x] Wave 0 covers every missing test reference.
- [x] No watch-mode flag is used.
- [ ] Task-level feedback remains below 30 seconds.
- [x] `nyquist_compliant: true` after plan checker approval.

**Approval:** approved by `gsd-plan-checker` on 2026-07-13
