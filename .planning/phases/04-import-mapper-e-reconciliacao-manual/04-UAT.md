# Phase 4 UAT

Status: passed

## Scenarios

- [x] O operador consegue ver colunas nao reconhecidas e reconciliar inline sem sair da tela.
- [x] Alterar mapeamento exige novo preview antes de habilitar a confirmacao final.
- [x] Preview e commit usam o mesmo contrato de `column_mappings` e `ignored_columns`.
- [x] Mapeamentos conflitantes sao barrados no backend antes do commit.
- [x] Arquivos que ja seguem o template continuam funcionando sem precisar reconciliar nada.

## Evidence

- `pytest saas-backend/tests/test_import_service_parsing.py`
- `npm.cmd run test -- src/test/ImportsPage.test.tsx`
- `npm.cmd run lint`
- `npm.cmd run build`
