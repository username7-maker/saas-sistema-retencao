---
phase: 10
slug: integridade-operacional-da-fila-de-tasks-do-piloto
status: draft
nyquist_compliant: false
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
| **Full focused suite** | backend four-file slice + shared runner + both route suites |
| **Estimated feedback** | backend ~5s; frontend ~12s; build ~30s |

## Baseline Freeze

| Area | Observed before Phase 10 | Treatment |
|------|--------------------------|-----------|
| Backend focused | 48 passed | Must remain green |
| `AITriageInboxPage` | 9/9 passed | Must remain green |
| `TasksPage` | 9/12 passed | Three pre-existing assertions/selectors must be repaired in Wave 0 and never hidden |

The three existing frontend failures are one stale copy assertion and two ambiguous `Onboarding` role queries. They are test debt, not evidence that Phase 10 regressed the product.

## Sampling Rate

- **After every backend task commit:** run the smallest affected pytest file(s).
- **After every frontend task commit:** run `WorkExecutionView.test.tsx` plus the affected route wrapper.
- **After every plan wave:** run the full focused backend/frontend suite.
- **Before `$gsd-verify-work`:** focused suites, typecheck/build, lint, `specify check` and `git diff --check` must pass.
- **Max feedback latency:** 30 seconds for task-level checks.

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 10-01-01 | 01 | 0 | WQ-01/WQ-02 | backend contract | `py -3.12 -m pytest -q tests/test_work_queue_service.py tests/test_ai_triage_router.py` | existing, new cases required | pending |
| 10-01-02 | 01 | 1 | WQ-01/WQ-02 | backend unit | `py -3.12 -m pytest -q tests/test_work_queue_service.py` | existing | pending |
| 10-01-03 | 01 | 1 | WQ-05 | backend clock/order | `py -3.12 -m pytest -q tests/test_work_queue_service.py` | existing, new cases required | pending |
| 10-02-01 | 02 | 0 | WQ-03 | AI reuse matrix | `py -3.12 -m pytest -q tests/test_ai_triage_service.py` | existing, new cases required | pending |
| 10-02-02 | 02 | 2 | WQ-04 | serializer/readiness | `py -3.12 -m pytest -q tests/test_ai_triage_service.py tests/test_work_queue_service.py` | existing | pending |
| 10-03-01 | 03 | 0 | WQ-01/WQ-02/WQ-08 | component | `npm.cmd test -- --run src/test/WorkExecutionView.test.tsx` | missing - Wave 0 | pending |
| 10-03-02 | 03 | 3 | WQ-01/WQ-02/WQ-04/WQ-05 | component/regression | `npm.cmd test -- --run src/test/WorkExecutionView.test.tsx src/test/AITriageInboxPage.test.tsx src/test/TasksPage.test.tsx` | partial | pending |
| 10-03-03 | 03 | 4 | WQ-08 | build/spec/smoke | `npm.cmd run build` + `specify check` + `git diff --check` | existing | pending |

## Wave 0 Requirements

- [ ] Add list envelope/search/count/truncation cases to `saas-backend/tests/test_work_queue_service.py` and router contract coverage.
- [ ] Add canonical snooze fallback and deterministic due-order cases.
- [ ] Add active-task reuse matrix to `saas-backend/tests/test_ai_triage_service.py`.
- [ ] Create `saas-frontend/src/test/WorkExecutionView.test.tsx` with remote search, page 2, loading counts and truncation.
- [ ] Repair the three pre-existing `TasksPage.test.tsx` assertions without weakening selectors.

No new test framework or dependency is required.

## Full Focused Commands

```powershell
# saas-backend
py -3.12 -m pytest -q tests/test_work_queue_service.py tests/test_ai_triage_service.py tests/test_ai_triage_router.py tests/test_autopilot_services.py

# saas-frontend
npm.cmd test -- --run src/test/WorkExecutionView.test.tsx src/test/AITriageInboxPage.test.tsx src/test/TasksPage.test.tsx
npm.cmd run build
npm.cmd run lint

# repository root
specify check
git diff --check
```

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

- [ ] All tasks have an automated command or Wave 0 dependency.
- [ ] No three consecutive implementation tasks lack automated feedback.
- [ ] Wave 0 covers every missing test reference.
- [ ] No watch-mode flag is used.
- [ ] Task-level feedback remains below 30 seconds.
- [ ] `nyquist_compliant: true` after plan checker approval.

**Approval:** pending
