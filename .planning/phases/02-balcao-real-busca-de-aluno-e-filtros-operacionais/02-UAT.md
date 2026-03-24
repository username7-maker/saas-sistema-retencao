# Phase 2 UAT

Status: passed

## Scenarios

- [x] Busca por matricula/`external_id` retorna o membro correto.
- [x] Filtros `7/14/30` dias sem check-in chegam na query de membros.
- [x] Filtro tri-state de provisorios chega corretamente na query.
- [x] A listagem mostra badge de matricula e indicador de provisiorio.

## Evidence

- `npm.cmd run test -- src/test/MembersPage.test.tsx`
- `pytest saas-backend/tests/test_members_service.py`
