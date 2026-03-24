# Phase 1 UAT

Status: passed

## Scenarios

- [x] Editar um lead preserva `notes` existentes.
- [x] Adicionar observacao manual cria novo evento append-only.
- [x] Quick action e nota manual coexistem no mesmo historico.
- [x] `Profile 360` nao le mais notas internas de `localStorage`.

## Evidence

- `npm.cmd run test -- src/test/CrmPage.test.tsx src/test/MemberProfile360Page.test.tsx`
- `pytest saas-backend/tests/test_crm_service.py`
