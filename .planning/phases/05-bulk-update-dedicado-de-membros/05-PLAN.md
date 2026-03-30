# Phase 5 Plan

## Workstreams

1. Adicionar contratos backend para preview e commit do bulk update.
2. Reaproveitar os filtros de members para suportar alvo por selecao ou por lista filtrada.
3. Registrar auditoria no preview e no commit.
4. Incluir selecao em tabela e dialogo dedicado na `MembersPage`.
5. Exigir preview valido antes do commit final e cobrir o fluxo com testes.

## Acceptance

- API aceita preview e commit para bulk update de membros.
- O fluxo suporta `selecionados` e `todos os filtrados`.
- O frontend nao permite confirmar quando o preview esta ausente ou stale.
- Apenas `status`, `plan_name`, `monthly_fee` e `preferred_shift` podem ser alterados em lote.
- O fluxo inteiro fica rastreavel por auditoria e validado em testes backend/frontend.
