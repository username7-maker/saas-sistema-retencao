# Phase 3 Context

## Objective

Fechar as ultimas superficies administrativas enganosas sem reabrir o escopo de permissoes.

## Locked Decisions

- `owner` continua vendo `seed` e `delete` em automacoes.
- `manager` mantem `create`, `edit`, `toggle` e `execute`, mas nao ve `seed` nem `delete`.
- Mensagens de erro `403` em automacoes devem ser explicitas se alguma acao residual escapar.
- `UsersPage` passa a falar em `Desativar`/`Reativar`, nao em `Excluir`.

## Out of Scope

- Reabrir dashboards ou navegacao global.
- Mudar API de usuarios ou automacoes.
