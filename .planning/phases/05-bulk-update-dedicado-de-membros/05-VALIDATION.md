---
phase: 05
slug: bulk-update-dedicado-de-membros
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-24
---

# Phase 05 - Validation Strategy

## Test Infrastructure

| Property | Value |
|----------|-------|
| Framework | `pytest` + `vitest` |
| Quick backend | `pytest saas-backend/tests/test_member_service_full.py` |
| Quick frontend | `npm.cmd run test -- src/test/MembersPage.test.tsx` |
| Full sign-off | `pytest saas-backend/tests/test_member_service_full.py && npm.cmd run test -- src/test/MembersPage.test.tsx && npm.cmd run lint` |

## Per-Task Verification Map

| Task ID | Requirement | Test Type | Command | Status |
|---------|-------------|-----------|---------|--------|
| 05-01 | BULK-01 | backend | `pytest saas-backend/tests/test_member_service_full.py` | pending |
| 05-02 | BULK-02 | backend | `pytest saas-backend/tests/test_member_service_full.py` | pending |
| 05-03 | BULK-01 | frontend | `npm.cmd run test -- src/test/MembersPage.test.tsx` | pending |
| 05-04 | BULK-02 | frontend | `npm.cmd run test -- src/test/MembersPage.test.tsx` | pending |

## Manual-Only Verifications

| Behavior | Why Manual |
|----------|------------|
| Ler diff em massa com clareza operacional | julgamento visual/UX |
| Entender o bloqueio por linhas pendentes sem confusao | copy e fluxo real |

## Validation Sign-Off

- [x] Infra de teste existente cobre a fase
- [x] Criticos mapeados para backend e frontend
- [x] Manual follow-up listado
