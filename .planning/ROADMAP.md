# ROADMAP

## Milestones

- ✅ **[v3.1.0 Prontidao Operacional](./milestones/v3.1.0-ROADMAP.md)** — Phases 1-3 (shipped 2026-03-24)
- 🚧 **v3.2.0 Operacao de Base** — Phases 4-6 (planned)

## Active Milestone — v3.2.0 Operacao de Base

**Goal:** Fechar os maiores atritos de base operacional restantes: importar melhor, atualizar em massa e encontrar membros por identificadores sensiveis com seguranca.

### Phase 4: Import mapper e reconciliacao manual

**Goal:** Permitir reconciliacao manual/visual de colunas antes do commit final de importacao.
**Requirements**: Mapper assistido no preview, com confirmacao explicita antes da escrita.
**Depends on:** Phase 3
**Plans:** 1 plan

Plans:
- [x] 04-PLAN.md

### Phase 5: Bulk update dedicado de membros

**Goal:** Criar fluxo dedicado de atualizacao em massa fora da importacao.
**Requirements**: Atualizacao coletiva segura, com preview e confirmacao.
**Depends on:** Phase 4
**Plans:** 1 plan

Plans:
- [x] 05-PLAN.md

### Phase 6: Busca operacional por telefone e CPF

**Goal:** Permitir busca operacional por telefone/CPF com estrategia segura de indexacao.
**Requirements**: Token/hash/index sem expor dados sensiveis em claro.
**Depends on:** Phase 5
**Plans:** 1 plan

Plans:
- [x] 06-PLAN.md
