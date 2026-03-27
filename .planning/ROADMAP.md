# ROADMAP

## Milestones

- Completed **[v3.1.0 Prontidao Operacional](./milestones/v3.1.0-ROADMAP.md)** - Phases 1-3 (shipped 2026-03-24)
- In progress **v3.2.0 Operacao de Base** - Phases 4, 4.1, 4.2, 4.3, 4.31, 4.32, 4.33, 5, 6

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
- [~] execute (piloto publicado em 2026-03-26; dia 0 em andamento)
- [ ] verify/validate (aguardando janela de 2 a 4 semanas e auditoria UAT)

### Phase 4.31: Bioimpedancia assistida e Actuar readiness

**Goal:** Fechar a distancia entre promessa e entrega real na bioimpedancia, deixando leitura assistida, sync Actuar e fallback manual explicitamente operacionais no piloto.
**Requirements**: `BODY-01` a `BODY-04`
**Depends on:** Phase 4.3
**Plans:** 1 plan

Plans:
- [x] 04.31-PLAN.md - capability state explicito para OCR local, IA assistida, sync Actuar, campos nao suportados e fallback manual

Status:
- [x] context
- [x] ui-spec
- [x] plan
- [ ] execute
- [ ] verify/validate

### Phase 4.32: Canais reais do piloto

**Goal:** Colocar WhatsApp e email em estado realmente operacional ou rebaixar a promessa do piloto de forma explicita.
**Requirements**: `COMMS-01`, `COMMS-02`
**Depends on:** Phase 4.31
**Plans:** 0 plans

Plans:
- [ ] TBD (run $gsd-discuss-phase 4.32 -> $gsd-plan-phase 4.32)

Status:
- [ ] context
- [ ] ui-spec
- [ ] plan
- [ ] execute
- [ ] verify/validate

### Phase 4.33: Transparencia de IA e fluxos publicos

**Goal:** Tornar explicitos os modos fallback de IA e decidir o que fica ativo ou escondido nos fluxos publicos do piloto.
**Requirements**: `AI-01`, `PUB-01`
**Depends on:** Phase 4.32
**Plans:** 0 plans

Plans:
- [ ] TBD (run $gsd-discuss-phase 4.33 -> $gsd-plan-phase 4.33)

Status:
- [ ] context
- [ ] ui-spec
- [ ] plan
- [ ] execute
- [ ] verify/validate

### Phase 5: Bulk update dedicado de membros

**Goal:** Criar fluxo dedicado de atualizacao em massa fora da importacao.
**Requirements**: `BULK-01`, `BULK-02`
**Depends on:** Phase 4.33
**Plans:** 1 plan

Plans:
- [x] 05-PLAN.md - bulk update dedicado, com preview de diff e commit bloqueado em caso de pendencias

Status:
- [x] context
- [x] ui-spec
- [x] plan
- [ ] execute (blocked until Fase 4.3 atingir criterio de saida e as fases urgentes 4.31-4.33 serem fechadas)
- [ ] verify/validate

### Phase 6: Busca operacional por telefone e CPF

**Goal:** Permitir busca operacional por telefone/CPF com estrategia segura de indexacao.
**Requirements**: `SEARCH-01`, `SEARCH-02`
**Depends on:** Phase 5
**Plans:** 0 plans

Plans:
- [ ] TBD (run $gsd-discuss-phase 6 -> $gsd-plan-phase 6) - blocked until Fase 5
