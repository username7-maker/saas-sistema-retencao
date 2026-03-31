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

## Post-Deploy Validation Notes

### 2026-03-30 - Preferred shift derived from check-ins

- Backend deploy validado no Railway (`/health/ready` -> `{"status":"ok"}`).
- Frontend publicado validado na Vercel.
- Distribuicao atual no piloto `ai-gym-os-piloto`:
  - `<null>`: `5976`
  - `morning`: `486`
  - `afternoon`: `412`
  - `evening`: `473`
- Isso confirma que `preferred_shift` deixou de depender apenas de valor legado importado e passou a ser derivado de padrao real de check-in quando existe sinal suficiente.
- Validacao operacional no ambiente publicado:
  - `GET /api/v1/members/` retorna `preferred_shift` derivado (`afternoon` observado em resposta real).
  - `GET /api/v1/assessments/queue` retorna `preferred_shift` derivado (`afternoon` e `evening` observados em resposta real).
  - `GET /api/v1/tasks/` retorna `preferred_shift` no payload; tarefas sem sinal suficiente continuam vindo com `null`.
- Leitura de risco honesta:
  - O dado agora esta util para parte real da base.
  - Ainda existe volume grande de membros sem sinal suficiente de check-in; nesses casos o sistema mantem `null` em vez de inventar turno.

### 2026-03-30 - Preferred shift explanation and responsive hardening

- Badge de `Turno por check-in` agora explica na propria UI que o valor e inferido pelo padrao recente de horarios de treino.
- Shell principal, filtros, tabs, drawers, dialogs e formularios criticos receberam ajustes para celular e tablet.
- Ganhos principais desta rodada:
  - topbar nao disputa largura com perfil e busca em telas menores
  - filtros deixam de quebrar layout horizontalmente
  - drawers e dialogs ocupam largura util no celular sem cortar conteudo
  - modais e formularios com grade dupla agora quebram corretamente para uma coluna em mobile
  - listagens de avaliacoes e tarefas ficam mais legiveis em viewport estreita
- Validacao local:
  - `npm.cmd run test -- src/test/PreferredShiftBadge.test.tsx src/test/MembersPage.test.tsx src/test/AssessmentsPage.test.tsx src/test/TasksPage.test.tsx`
  - `npm.cmd run lint`
  - `npm.cmd run build`
