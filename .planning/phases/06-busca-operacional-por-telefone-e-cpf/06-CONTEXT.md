# Phase 6 Context

## Objective

Permitir busca operacional por telefone e CPF nas superficies de membros e avaliacoes sem expor PII em texto claro no banco ou nos filtros.

## Locked Decisions

- A busca de telefone e CPF sera exata, baseada em hash/index deterministico.
- O dado sensivel continua criptografado em repouso; o hash existe apenas para lookup.
- O fluxo deve cobrir criacao, edicao e importacao de membros para manter o indice consistente.
- O header search contextual passa a funcionar em `Members` e `Assessments`.

## Out of Scope

- Busca parcial/fuzzy por telefone ou CPF.
- Exposicao de CPF na UI.
- Busca cross-tenant ou qualquer relaxamento do isolamento por `gym_id`.
