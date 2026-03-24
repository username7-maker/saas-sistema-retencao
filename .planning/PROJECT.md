# SaaS Sistema Retencao

## What This Is

Plataforma operacional para academias acompanharem alunos, risco de churn, onboarding, CRM, tarefas e avaliacoes tecnicas em um unico fluxo. O foco atual e tornar o produto confiavel para piloto real e operacao limitada, com interfaces honestas por papel e leitura operacional consistente.

## Core Value

A equipe da academia precisa confiar que cada tela mostra o estado real do aluno e so oferece acoes que de fato fecham operacionalmente.

## Current Milestone: v3.1.0 Prontidao Operacional

**Goal:** Fechar os gaps restantes para piloto com equipe real e operacao limitada.

**Target features:**
- Integridade do historico comercial e do contexto compartilhado
- Busca e filtros de membros mais uteis para recepcao e gerente
- Superficie administrativa coerente com as permissoes reais

## Requirements

### Validated

- [x] Contencao de navegacao e rotas por papel ja reduz 403 previsiveis
- [x] Importacao com preview e confirmacao explicita antes do commit
- [x] Workspace tecnico de assessments separado por papel
- [x] Conversao de lead com handoff minimo obrigatorio

### Active

- [ ] CRM preserva timeline estruturada de contato sem achatar metadata
- [ ] Busca de membros atende melhor o fluxo de balcao usando nome, email ou matricula
- [ ] Gestao administrativa mostra apenas acoes que o backend realmente sustenta

### Out of Scope

- Mapper manual/visual de colunas na importacao - adiado para backlog porque nao bloqueia piloto controlado
- Bulk update dedicado fora da importacao - adiado para backlog por nao ser necessario nesta rodada
- Busca por telefone/CPF - adiada porque exige estrategia propria para dados criptografados em repouso

## Context

- Produto brownfield ja em operacao de desenvolvimento, com tag Git existente `v3.0.0`
- Backend FastAPI + SQLAlchemy e frontend React/Vite
- O repositorio ja tinha auditoria operacional e correcao relevante de permissoes, importacao e assessments antes deste milestone
- O GSD estava configurado via `.planning/config.json`, mas sem artefatos de milestone e fases

## Constraints

- **Tech stack**: Manter FastAPI, SQLAlchemy e React existentes - evitar refactors estruturais fora do escopo
- **Authorization**: Nao expandir permissao de backend para acomodar UI - a UI deve se alinhar ao backend
- **Operational target**: Alvo e piloto + operacao limitada - nao transformar este milestone em redesign total
- **Data integrity**: Nao fazer migracoes destrutivas de `Lead.notes` neste ciclo

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Usar `v3.1.0` como milestone atual | Existe tag `v3.0.0` no repo e este ciclo e incremental | - Pending |
| Fechar CRM sem migracao destrutiva | Preserva historico legado enquanto estabiliza a timeline | - Pending |
| Tratar matricula via `extra_data.external_id` | Ja e o identificador operacional mais confiavel na base atual | - Pending |
| Nao incluir busca por telefone/CPF agora | Dados estao criptografados em repouso e exigem desenho proprio | - Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition**:
1. Requirements invalidated? -> Move to Out of Scope with reason
2. Requirements validated? -> Move to Validated with phase reference
3. New requirements emerged? -> Add to Active
4. Decisions to log? -> Add to Key Decisions
5. "What This Is" still accurate? -> Update if drifted

**After each milestone**:
1. Full review of all sections
2. Core Value check - still the right priority?
3. Audit Out of Scope - reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-03-24 after GSD bootstrap for v3.1.0*
