# ROADMAP

## Milestones

- Completed **[v3.1.0 Prontidao Operacional](./milestones/v3.1.0-ROADMAP.md)** - Phases 1-3 (shipped 2026-03-24)
- In progress **v3.2.0 Operacao de Base** - Phases 4, 4.1, 4.2, 4.3, 4.31, 4.32, 4.33, 4.34, 4.35, 4.36, 4.37, 4.38, 4.39, 4.40, 4.41, 4.42, 5, 6

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
- [~] execute (infraestrutura da ponte local implementada e validada em testes; falta validacao ao vivo na aba real do Actuar)
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

### Phase 4.34: Superficies administrativas e relatorios do piloto

**Goal:** Corrigir bugs reais do piloto em notificacoes, metas e relatorios, melhorar o vazio/clareza do NPS e permitir personalizacao basica de usuarios com foto, cargo e ajuste de papel.
**Requirements**: `ADMIN-01` a `ADMIN-05`
**Depends on:** Phase 4.32
**Plans:** 1 plan

Plans:
- [x] 04.34-PLAN.md - corrigir contratos de rota, serializacao de PDF, acabamento de NPS e editar perfil/equipe sem promessas falsas

Status:
- [x] context
- [x] ui-spec
- [x] plan
- [~] execute
- [ ] verify/validate

### Phase 4.35: Upload real de foto e funcoes mais ricas por usuario

**Goal:** Evoluir a personalizacao basica por URL para um fluxo real de foto com upload e separar melhor `role` operacional de `funcao/cargo` no produto.
**Requirements**: `IDENTITY-01` a `IDENTITY-04`
**Depends on:** Phase 4.34
**Plans:** 1 plan

Plans:
- [x] 04.35-PLAN.md - upload real de avatar com storage seguro, papel versus funcao mais claro e superficies administrativas sem promessas falsas

Status:
- [x] context
- [x] ui-spec
- [x] plan
- [ ] execute
- [ ] verify/validate

### Phase 4.36: Higiene de tokens e lockdown de superficies publicas

**Goal:** Remover segredos em query string, endurecer as superficies publicas e impedir que protecoes de abuso desaparecam silenciosamente em producao.
**Requirements**: `SEC-01` a `SEC-04`
**Depends on:** Phase 4.35
**Plans:** 1 plan

Plans:
- [x] 04.36-PLAN.md - trocar query-string secrets por contratos seguros, tornar rate limiting obrigatorio em producao e rebaixar exposicao dos endpoints publicos e de readiness

Status:
- [x] context
- [x] ui-spec
- [x] plan
- [ ] execute
- [ ] verify/validate

### Phase 4.37: Protecao de PII e seguranca de import/export

**Goal:** Fechar os pontos mais perigosos de LGPD e integridade operacional em PII, CSV/XLSX e trilhas de auditoria.
**Requirements**: `DATA-01` a `DATA-04`
**Depends on:** Phase 4.36
**Plans:** 1 plan

Plans:
- [x] 04.37-PLAN.md - neutralizar formula injection, impor guardrails reais em XLSX/CSV, reduzir PII em claro e redigir melhor logs/auditoria

Status:
- [x] context
- [x] ui-spec
- [x] plan
- [ ] execute
- [ ] verify/validate

### Phase 4.38: Resiliencia de consultas, jobs e DoS logico

**Goal:** Tirar o sistema da zona de risco de escala facil, removendo filtros em memoria, batches sem limite e jobs com timeout desativado.
**Requirements**: `PERF-01` a `PERF-03`
**Depends on:** Phase 4.37
**Plans:** 1 plan

Plans:
- [x] 04.38-PLAN.md - migrar filtros pesados para SQL, batchar jobs e impor limites de custo previsiveis em operacoes de volume

Status:
- [x] context
- [x] ui-spec
- [x] plan
- [ ] execute
- [ ] verify/validate

### Phase 4.39: Guardrails de tenant e consistencia transacional

**Goal:** Reduzir os bypasses manuais do multi-tenant e padronizar ownership transacional dos fluxos criticos.
**Requirements**: `TENANT-01`, `TENANT-02`, `ARCH-01`
**Depends on:** Phase 4.38
**Plans:** 1 plan

Plans:
- [x] 04.39-PLAN.md - reduzir include_all_tenants/unscoped access, criar testes de isolamento e unificar a fronteira de commit nos fluxos criticos

Status:
- [x] context
- [x] ui-spec
- [x] plan
- [ ] execute
- [ ] verify/validate

### Phase 4.40: Hardening de sessao e borda de producao

**Goal:** Redesenhar a exposicao de sessao do frontend e estabelecer um baseline de borda segura para producao.
**Requirements**: `SESSION-01`, `EDGE-01`, `EDGE-02`
**Depends on:** Phase 4.39
**Plans:** 1 plan

Plans:
- [x] 04.40-PLAN.md - mover a sessao para um modelo de menor blast radius e travar headers, CSP e defaults inseguros de build/producao

Status:
- [x] context
- [x] ui-spec
- [x] plan
- [ ] execute
- [ ] verify/validate

### Phase 4.41: Handoff seguro para Kommo

**Goal:** Fazer o AI GYM OS decidir e entregar handoffs operacionais para a Kommo sem disputar o numero oficial da academia, conectando configuracao por gym, automacoes e bioimpedancia.
**Requirements**: `KOMMO-01` a `KOMMO-03`
**Depends on:** Phase 4.40
**Plans:** 1 plan

Plans:
- [x] 04.41-PLAN.md - configurar Kommo por academia, acionar handoff nas automacoes e permitir envio manual da bioimpedancia para a operacao da Kommo

Status:
- [x] context
- [x] ui-spec
- [x] plan
- [~] execute
- [ ] verify/validate

### Phase 4.42: Actuar Bridge local

**Goal:** Tirar o sync Actuar do worker isolado e levar a automacao para uma estacao local da academia, usando a sessao ja aberta do operador sem depender de API/webhook do Actuar.
**Requirements**: `ACTBRIDGE-01` a `ACTBRIDGE-04`
**Depends on:** Phase 4.41
**Plans:** 1 plan

Plans:
- [x] 04.42-PLAN.md - adicionar modo `local_bridge`, pareamento seguro por estacao, fila dedicada para a ponte local e scaffold do app que conversa com o AI GYM OS

Status:
- [x] context
- [x] ui-spec
- [x] plan
- [ ] execute
- [ ] verify/validate

### Phase 5: Bulk update dedicado de membros

**Goal:** Criar fluxo dedicado de atualizacao em massa fora da importacao.
**Requirements**: `BULK-01`, `BULK-02`
**Depends on:** Phase 4.42
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
