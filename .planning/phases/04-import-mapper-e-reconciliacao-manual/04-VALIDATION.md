---
phase: 04
slug: import-mapper-e-reconciliacao-manual
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-24
---

# Phase 04 - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | `pytest` + `vitest` |
| **Config file** | existing repo configs |
| **Quick run command** | `pytest saas-backend/tests/test_import_service_parsing.py` |
| **Full suite command** | `pytest saas-backend/tests/test_import_service_parsing.py && npm.cmd run test -- src/test/ImportsPage.test.tsx && npm.cmd run lint` |
| **Estimated runtime** | ~40 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest saas-backend/tests/test_import_service_parsing.py` or `npm.cmd run test -- src/test/ImportsPage.test.tsx` depending on touched area
- **After every plan wave:** Run `pytest saas-backend/tests/test_import_service_parsing.py` and `npm.cmd run test -- src/test/ImportsPage.test.tsx`
- **Before verification:** Full phase sign-off command must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 04-01 | 04 | 1 | IMP-01 | backend unit | `pytest saas-backend/tests/test_import_service_parsing.py` | ✅ | ⬜ pending |
| 04-02 | 04 | 1 | IMP-02 | backend unit | `pytest saas-backend/tests/test_import_service_parsing.py` | ✅ | ⬜ pending |
| 04-03 | 04 | 2 | IMP-01 | frontend unit | `npm.cmd run test -- src/test/ImportsPage.test.tsx` | ✅ | ⬜ pending |
| 04-04 | 04 | 2 | IMP-02 | frontend unit | `npm.cmd run test -- src/test/ImportsPage.test.tsx` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- Existing infrastructure covers all phase requirements.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Operator understands how to reconcile an unrecognized column | IMP-01 | copy and layout judgment | validar no localhost um arquivo com coluna inesperada, mapear, revalidar e confirmar |
| Warning language prevents accidental ignore of useful data | IMP-02 | operator safety wording | revisar fluxo de ignorar coluna com valores presentes |

---

## Validation Sign-Off

- [x] All tasks have automated verify or existing infrastructure
- [x] Sampling continuity defined
- [x] Wave 0 covers all missing references
- [x] No watch-mode flags
- [x] Feedback latency under 60s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-03-24
