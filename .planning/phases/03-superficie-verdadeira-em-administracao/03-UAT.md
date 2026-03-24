# Phase 3 UAT

Status: passed

## Scenarios

- [x] `manager` nao ve `Regras Padrao` quando a tela esta vazia.
- [x] `manager` nao ve CTA de excluir regra.
- [x] `owner` continua vendo `Regras Padrao`.
- [x] `UsersPage` mostra `Desativar`/`Reativar` e usa o endpoint correto.

## Evidence

- `npm.cmd run test -- src/test/AutomationsPage.test.tsx src/test/UsersPage.test.tsx src/test/roleAccess.test.ts`
