# ROADMAP

## Milestones

- Completed **[v3.1.0 Prontidao Operacional](./milestones/v3.1.0-ROADMAP.md)** - Phases 1-3 (shipped 2026-03-24)
- In progress **v3.2.0 Operacao de Base** - Phases 4, 4.1, 4.2, 4.3, 5, 6

## Active Milestone - v3.2.0 Operacao de Base

**Goal:** Congelar feature nova por um ciclo curto, fechar hardening de confiabilidade e coerencia operacional para piloto controlado, e so depois retomar bulk update e busca sensivel.

### Phase 4: Import mapper e reconciliacao manual

**Goal:** Permitir reconciliacao manual/visual de colunas antes do commit final de importacao.
**Requirements**: `IMP-01`, `IMP-02`
**Depends on:** Phase 3
**Plans:** 1 plan

Plans:
- [x] 04-PLAN.md - mapper assistido sobre o preview atual, com revalidacao antes do commit

Status:
- [x] context
- [x] ui-spec
- [x] plan
- [x] execute
- [x] verify/validate

### Phase 4.1: Hardening P0

**Goal:** Fechar bloqueadores de confiabilidade operacional antes do piloto.
**Requirements**: `HARD-01` a `HARD-04`
**Depends on:** Phase 4
**Plans:** 1 plan

Plans:
- [x] 04.1-PLAN.md - birthday importado, recalc duravel, websocket distribuido e suites totalmente verdes

Status:
- [x] context
- [x] ui-spec
- [x] plan
- [x] execute
- [x] verify/validate

### Phase 4.2: Coerencia operacional P1

**Goal:** Alinhar papais/permissoes, trainer task-lite, fronteiras transacionais centrais e CI do frontend.
**Requirements**: `OPS-01` a `OPS-04`
**Depends on:** Phase 4.1
**Plans:** 1 plan

Plans:
- [x] 04.2-PLAN.md - RBAC refletindo backend, task-lite do trainer e routers donos do commit nos fluxos centrais do piloto

Status:
- [x] context
- [x] ui-spec
- [x] plan
- [x] execute
- [x] verify/validate

### Phase 4.3: Piloto controlado

**Goal:** Rodar piloto com escopo fechado, monitoramento minimo e criterios de saida objetivos.
**Requirements**: piloto ativo por 2 a 4 semanas sem incidente critico de tenant, realtime ou job perdido
**Depends on:** Phase 4.2
**Plans:** 1 plan

Plans:
- [x] 04.3-PLAN.md - rollout controlado por papel, monitoramento do piloto e checklist de saida

Status:
- [x] context
- [ ] ui-spec
- [x] plan
- [~] execute (kickoff package ready; piloto em campo pendente)
- [ ] verify/validate

### Phase 5: Bulk update dedicado de membros

**Goal:** Criar fluxo dedicado de atualizacao em massa fora da importacao.
**Requirements**: `BULK-01`, `BULK-02`
**Depends on:** Phase 4.3
**Plans:** 1 plan

Plans:
- [x] 05-PLAN.md - bulk update dedicado, com preview de diff e commit bloqueado em caso de pendencias

Status:
- [x] context
- [x] ui-spec
- [x] plan
- [ ] execute (paused until piloto)
- [ ] verify/validate

### Phase 6: Busca operacional por telefone e CPF

**Goal:** Permitir busca operacional por telefone/CPF com estrategia segura de indexacao.
**Requirements**: `SEARCH-01`, `SEARCH-02`
**Depends on:** Phase 5
**Plans:** 0 plans

Plans:
- [ ] TBD (run $gsd-discuss-phase 6 -> $gsd-plan-phase 6) - paused until piloto
