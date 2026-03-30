# Phase 5 Context

## Objective

Criar um fluxo dedicado de atualizacao em massa de membros, fora da importacao, com preview obrigatorio antes do commit.

## Locked Decisions

- O bulk update fica na superficie de `Members`, nao no fluxo de importacao.
- O alvo pode ser `selecionados` ou `todos os filtrados`.
- O V1 so permite quatro campos de baixo risco: `status`, `plan_name`, `monthly_fee` e `preferred_shift`.
- Toda alteracao exige preview fresco antes da confirmacao final.
- Preview e commit precisam gerar trilha auditavel.

## Out of Scope

- Bulk update irrestrito de qualquer campo do membro.
- Edicao linha a linha ou reconciliacao estilo planilha.
- Novo wizard multi-etapas fora da pagina de membros.
