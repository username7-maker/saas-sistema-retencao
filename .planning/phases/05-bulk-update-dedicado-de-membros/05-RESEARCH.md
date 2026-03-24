# Phase 5: Bulk update dedicado de membros - Research

**Researched:** 2026-03-24
**Domain:** atualizacao em massa segura para membros existentes
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

- Fluxo dedicado fora da tela de importacao inicial
- Arquivo `CSV`/`XLSX` com preview obrigatorio
- Apenas membros existentes
- Match estrito por `member_id`, `external_id` ou `email`
- Sem CPF, sem nome como chave de match, sem criacao/exclusao
- Commit bloqueado se houver linhas invalidas ou ambiguas
- Sem aplicacao parcial nesta fase

</user_constraints>

<research_summary>
## Summary

O sistema ja tem dois blocos reutilizaveis valiosos para esta fase:

1. o padrao operacional de `preview -> confirm` da importacao;
2. a service layer de membros com contratos de listagem e update individual.

A melhor abordagem e criar um contrato dedicado de bulk update sob o modulo de membros, com parser proprio focado apenas em registros existentes e diffs de alteracao. Reusar diretamente a importacao como backend desta fase aumentaria ambiguidade semantica entre "entrada de base" e "correcao de base".

**Primary recommendation:** criar endpoints dedicados de preview e commit para bulk update, com match estrito e diff por campo, e um frontend dedicado a partir de `MembersPage`.
</research_summary>

## Current System Findings

- `MembersPage.tsx` ja e o melhor ponto de entrada para manutencao da base.
- `member_service.py` ja concentra regras de listagem e update individual, mas nao possui nada em lote.
- `ImportsPage.tsx` e `import_service.py` oferecem referencias claras para preview/confirm, warnings, sample rows e summaries.
- O backend atual nao tem contrato para atualizar em lote apenas membros existentes.

## Recommended Backend Shape

- Criar endpoints dedicados sob o dominio de membros:
  - preview de bulk update
  - commit de bulk update
- Criar schemas especificos de preview/summary para diff em lote.
- Reaproveitar `MemberUpdate` apenas como referencia de campos, nao como payload final direto.
- Centralizar matching, diff e validacao em um service proprio para bulk update.

## Matching Recommendation

- Ordem recomendada:
  1. `member_id`
  2. `external_id`
  3. `email`
- Rejeitar:
  - linha sem chave
  - linha com match ambiguo
  - valores invalidos para campos suportados

## Field Scope Recommendation

- Incluir:
  - `full_name`
  - `email`
  - `phone`
  - `plan_name`
  - `monthly_fee`
  - `join_date`
  - `preferred_shift`
  - `status`
  - `external_id`
- Excluir:
  - `cpf`
  - `birthdate`
  - dados tecnicos de avaliacoes
  - `extra_data` livre

## Frontend Recommendation

- Adicionar CTA em `MembersPage` para abrir a sub-rota de bulk update.
- Tela dedicada com:
  - upload
  - regras de identificacao
  - preview agregado
  - diff das alteracoes
  - confirmacao final
- Nao usar drawer; o diff precisa de espaco de leitura.

## Common Pitfalls

### Pitfall 1: tratar bulk update como importacao
- Mistura semantica e regras diferentes
- Evitar reaproveitar a UX de importacao como se fosse o mesmo fluxo

### Pitfall 2: permitir match por nome
- Alto risco de alterar a pessoa errada
- Match deve ser estrito

### Pitfall 3: aplicar parcialmente sem linguagem clara
- Operador acha que atualizou tudo, mas metade falhou
- Nesta fase, commit deve bloquear se houver pendencias

## Test Strategy

- Backend:
  - preview com linhas prontas, invalidas, ambiguas e nao encontradas
  - commit so quando preview e consistente
  - match por `member_id`, `external_id` e `email`
  - diffs corretos por campo
- Frontend:
  - CTA nasce em `MembersPage`
  - preview bloqueia commit com pendencias
  - diff mostra `antes -> depois`
  - confirmacao invalida queries certas apos sucesso

## Validation Architecture

- Quick backend command: `pytest saas-backend/tests/test_member_service_full.py`
- Quick frontend command: `npm.cmd run test -- src/test/MembersPage.test.tsx`
- Phase sign-off command:
  - `pytest saas-backend/tests/test_member_service_full.py`
  - `npm.cmd run test -- src/test/MembersPage.test.tsx`
  - `npm.cmd run lint`
