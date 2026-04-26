# ROADMAP

## Milestones

- Completed **[v3.1.0 Prontidao Operacional](./milestones/v3.1.0-ROADMAP.md)** - Phases 1-3 (shipped 2026-03-24)
- In progress **v3.2.0 Operacao de Base** - Phases 4, 4.1, 4.2, 4.3, 4.31, 4.32, 4.33, 4.34, 4.35, 4.36, 4.37, 4.38, 4.39, 4.40, 4.41, 4.42, 4.42.1, 4.42.2, 4.42.3, 4.42.4, 4.42.5, 4.43, 4.43.1, 4.43.2, 5, 6
- In progress **[v3.3.0 AI Lead-to-Member Intelligence Foundation](./milestones/v3.3.0-ROADMAP.md)** - Phase 7.0 aberta com payload canonico `lead -> member`; fases 7.1, 7.2 e 7.3 seguem como proximos cortes, depois [v3.4.0](./milestones/v3.4.0-ROADMAP.md), [v3.5.0](./milestones/v3.5.0-ROADMAP.md) and [v3.6.0](./milestones/v3.6.0-ROADMAP.md)

## Active Milestone - v3.2.0 Operacao de Base

**Goal:** Congelar expansao lateral por um ciclo curto, operar 4.36+4.40 como um unico workstream de sessao e borda, fechar hardening estrutural do core e usar a Fase 4.3 apenas como gate de saida monitorado.

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

**Goal:** Usar o piloto como gate de saida do hardening, com criterios mensuraveis e sem abrir novo escopo enquanto a fase 4.38 nao estiver verde.
**Requirements**: piloto ativo por 2 a 4 semanas sem incidente critico de tenant, realtime ou job perdido
**Depends on:** Phase 4.2
**Plans:** 1 plan

Plans:
- [x] 04.3-PLAN.md - rollout controlado por papel, monitoramento do piloto e checklist de saida

Status:
- [x] context
- [ ] ui-spec
- [x] plan
- [x] execute (piloto monitorado, amostra controlada gerada e gate final lido contra as superficies realmente ativas do tenant `ai-gym-os-piloto`)
- [x] verify/validate (janela de 14 dias auditada com `nps_dispatch` e `whatsapp_webhook_setup` em `PASS`; artefatos finais em `04.3-PILOT-JOB-GATE-2026-04-18.*` e `04.3-VALIDATION.md`)

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
**Plans:** 1 plan

Plans:
- [x] 04.32-PLAN.md - WhatsApp real auditavel no piloto e Actuar automatico tratado como gate binario dependente de credenciais reais da academia piloto

Status:
- [x] context
- [x] ui-spec
- [x] plan
- [x] execute (WhatsApp real validado; `assisted_rpa` do Actuar validado com credenciais reais; correcao final publicada para preencher os campos editaveis de `Composicao corporal e perimetria` no Actuar)
- [x] verify/validate (evidencia operacional registrada em `04.32-STATUS.md`, incluindo job `87fef1c8-3b64-415b-8e0c-4e4dd35c71b8` finalizado como `synced`)

### Phase 4.33: Transparencia de IA e fluxos publicos

**Goal:** Tornar explicitos os modos fallback de IA e decidir o que fica ativo ou escondido nos fluxos publicos do piloto.
**Requirements**: `AI-01`, `PUB-01`
**Depends on:** Phase 4.32
**Plans:** 1 plan

Plans:
- [x] 04.33-PLAN.md - contrato unico de transparencia para superficies AI existentes, com copy honesta para fallback/manual e sem promessas enganosa no piloto

Status:
- [x] context
- [x] ui-spec
- [x] plan
- [x] execute (contrato minimo implementado, publicado no piloto e reforcado no painel compartilhado com `provider`/`mode` visiveis)
- [x] verify/validate (verificacao visual fechada nas superficies autenticadas de `Tasks`, `Onboarding` e `Retencao`, com evidencia registrada em `.planning/phases/04.33-transparencia-de-ia-e-fluxos-publicos/evidence/`)

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
- [ ] execute (blocker-only durante o freeze; so entram correcoes que protejam o loop core)
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
- [ ] execute (blocker-only durante o freeze; sem avancar identidade fora do loop core)
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
- [x] execute (websocket/reset/webhook sairam de query string, readiness foi reduzido, `Origin/Referer` e `no-store` ficaram cobertos na superficie de auth e a regressao final do websocket publicado foi corrigida)
- [x] verify/validate (release candidata validada ao vivo com refresh cookie cross-origin, reject fora da allowlist, websocket por primeira mensagem e headers/CSP da borda publicada)

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
- [x] execute
- [x] verify/validate

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
- [x] execute (query cost e batching principal fecharam; o scheduler automatico de `nps_dispatch` e `monthly_reports_dispatch` ja usa envelope duravel, `queue_wait_seconds` ficou observavel, `whatsapp_webhook_setup` ganhou status consultavel, o `requeue` manual foi documentado e a medicao do budget ganhou script versionado)
- [x] verify/validate (a amostra operacional minima controlada do piloto foi aceita como suficiente; `1` `CoreAsyncJob` registrado com `p95 queue_wait_seconds = 7.21s` e `04.38-VALIDATION.md` marcada como `PASS`)

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
- [x] execute (helpers de bypass exigem `reason` allowlisted, jobs cross-tenant ficaram presos a motivos aprovados, rotas comerciais/publicas do loop core ganharam regressao especifica e os helpers centrais agora emitem telemetria estruturada)
- [x] verify/validate (fase validada com inventario central, regressao focada `40 passed` e `04.39-VALIDATION.md`)

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
- [x] execute
- [x] verify/validate

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

**Goal:** Manter a ponte local do Actuar apenas em modo blocker-only durante o freeze, sem expandir escopo alem do necessario para nao travar o piloto.
**Requirements**: `ACTBRIDGE-01` a `ACTBRIDGE-04`
**Depends on:** Phase 4.41
**Plans:** 1 plan

Plans:
- [x] 04.42-PLAN.md - adicionar modo `local_bridge`, pareamento seguro por estacao, fila dedicada para a ponte local e scaffold do app que conversa com o AI GYM OS

Status:
- [x] context
- [x] ui-spec
- [x] plan
- [ ] execute (blocker-only durante o freeze; apenas correcoes impeditivas ao piloto)
- [ ] verify/validate

### Phase 4.42.1: Actuar Bridge extension relay

**Goal:** Manter o relay/extensao do Actuar em blocker-only durante o freeze, evitando expansao lateral enquanto o core de sessao, tenant, PII e jobs fecha.
**Requirements**: `ACTBRIDGE-05`, `ACTBRIDGE-06`
**Depends on:** Phase 4.42
**Plans:** 1 plan

Plans:
- [x] 04.42.1-PLAN.md - adicionar modo `extension-relay`, relay local HTTP em loopback e extensao enxuta para anexar a aba do Actuar e executar jobs pela sessao ja aberta

Status:
- [x] context
- [x] ui-spec
- [x] plan
- [ ] execute (blocker-only durante o freeze; apenas correcoes impeditivas ao piloto)
- [ ] verify/validate

### Phase 4.42.2: Plataforma de relatorios premium (INSERTED)

**Goal:** Criar a fundacao unica de relatorios premium do produto, trocando os dumps textuais por um pipeline `HTML/CSS -> PDF` com payload semantico proprio, blocos reutilizaveis e branding leve por academia.
**Requirements**: `RPT-01` a `RPT-04`
**Depends on:** Phase 4.42.1
**Plans:** 1 plan

Plans:
- [x] 04.42.2-PLAN.md - fundacao premium de relatorios com pipeline HTML/CSS -> PDF, dominio unico de payload e biblioteca visual reutilizavel

Status:
- [x] context
- [x] ui-spec
- [x] plan
- [x] execute (fundacao premium validada no piloto com renderer compartilhado servindo tela dedicada, `Resumo do aluno`, `Relatorio tecnico` e board pack executivo em uma rodada real de browser + PDFs)
- [x] verify/validate

### Phase 4.42.3: Relatorios premium de avaliacoes (INSERTED)

**Goal:** Transformar os relatorios de bioimpedancia e composicao corporal em laudos premium com leitura para aluno e leitura tecnica para coach, incluindo comparativos, evolucao e fallback elegante para dados opcionais.
**Requirements**: `RPTA-01` a `RPTA-04`
**Depends on:** Phase 4.42.2
**Plans:** 1 plan

Plans:
- [x] 04.42.3-PLAN.md - laudos premium de avaliacoes com `Resumo do aluno`, `Relatorio tecnico`, comparativos, fallback de perimetria e entrega pelos canais existentes

Status:
- [x] context
- [x] ui-spec
- [x] plan
- [x] execute (o fluxo real do workspace do aluno foi fechado no piloto: CTA pos-save, rota dedicada de laudo premium e os dois PDFs reais validados para uma avaliacao com historico)
- [x] verify/validate

### Phase 4.42.4: Relatorios premium de gestao (INSERTED)

**Goal:** Levar `executive`, `operational`, `commercial`, `financial`, `retention` e `consolidated` para um patamar premium de board pack com KPIs, tendencias, leitura executiva e payloads robustos a cache serializado.
**Requirements**: `RPTG-01` a `RPTG-04`
**Depends on:** Phase 4.42.2
**Plans:** 1 plan

Plans:
- [x] 04.42.4-PLAN.md - PDFs premium de gestao com narrativa executiva, board pack mensal e coleta semantica independente dos dumps de dashboard

Status:
- [x] context
- [x] ui-spec
- [x] plan
- [x] execute (payloads premium de gestao e board packs foram validados no piloto com geracao real do `executive` board pack sobre o novo renderer)
- [x] verify/validate

### Phase 4.42.5: Central, distribuicao e rollout dos relatorios (INSERTED)

**Goal:** Evoluir a Central de Relatorios para catalogo premium com geracao, historico, status, distribuicao assincrona e rollout controlado dos novos PDFs de avaliacoes e gestao.
**Requirements**: `RPTH-01` a `RPTH-03`
**Depends on:** Phase 4.42.4
**Plans:** 1 plan

Plans:
- [x] 04.42.5-PLAN.md - central de relatorios com catalogo, historico, jobs premium, rollout no piloto e evidencias visuais por trilho

Status:
- [x] context
- [x] ui-spec
- [x] plan
- [x] execute (catalogo premium, CTA no workspace e geracao real de board pack e laudos foram validados no piloto em uma rodada controlada)
- [x] verify/validate

### Phase 4.43: AI-first fase 1 - Inbox de triagem

**Goal:** Abrir a primeira superficie realmente AI-first do produto sem quebrar o core endurecido, transformando a triagem diaria em uma inbox orientada por IA com prioridade explicavel, proxima melhor acao e aprovacao humana antes da execucao.
**Requirements**: `AIFIRST-01` a `AIFIRST-05`
**Depends on:** Phase 4.42.5
**Plans:** 1 plan

Plans:
- [x] 04.43-PLAN.md - AI Triage Inbox como primeira superficie AI-first, com decisao explicavel, tool layer segura e aprovacao humana obrigatoria

Status:
- [x] context
- [x] ui-spec
- [x] plan
- [x] execute (Wave 1 backend, Wave 2 inbox UI, Wave 3 tool layer/outcome measurement e Wave 4 walkthrough real no piloto concluidas)
- [x] verify/validate

### Phase 4.43.1: Simplificacao operacional do AI Inbox (INSERTED)

**Goal:** Reduzir o atrito operacional da inbox AI-first validada na `4.43`, trocando explainability densa por uma fila de execucao com CTA principal unico, aprovacao leve e detalhes analiticos recolhidos.
**Requirements**: `AIFIRST-OPS-01` a `AIFIRST-OPS-04`
**Depends on:** Phase 4.43
**Plans:** 1 plan

Plans:
- [x] 04.43.1-PLAN.md - simplificar lista e inspector, unificar approval + prepare para itens normais e preservar guardrails auditaveis

Status:
- [x] context
- [x] ui-spec
- [x] plan
- [x] execute (payload operador-first, CTA unico para itens normais, confirmacao curta para itens criticos e filtros operacionais implementados, publicados no piloto e estabilizados por hotfixes de CTA/approval)
- [x] verify/validate (fase validada com testes focados, build verde, feedback operacional real do piloto e hotfixes consolidados em `04.43.1-VALIDATION.md`)

### Phase 4.43.2: Piloto seguro - sinais operacionais reais (INSERTED)

**Goal:** Remover sinais demo/hardcoded das superficies executivas do piloto e evitar que KPI, badge ou card induza decisao operacional sem base real.
**Requirements**: `PILOT-TRUTH-01`, `PILOT-TRUTH-02`
**Depends on:** Phase 4.43.1
**Plans:** 1 plan

Plans:
- [x] 04.43.2-PLAN.md - higienizar dashboard/layout contra dados cenograficos e adicionar regressao para empty states honestos

Status:
- [x] context
- [x] ui-spec
- [x] plan
- [x] execute (fallback demo removido, KPI executivo rebaixado para `Sem base` quando nao ha serie/dado real e card de ROI deixou de afirmar automacao ativa sem resultado confirmado)
- [x] verify/validate (testes focados de dashboard/ROI e build do frontend verdes)

### Phase 5: Bulk update dedicado de membros

**Goal:** Criar fluxo dedicado de atualizacao em massa fora da importacao.
**Requirements**: `BULK-01`, `BULK-02`
**Depends on:** Phase 4.42.1
**Plans:** 1 plan

Plans:
- [x] 05-PLAN.md - bulk update dedicado, com preview de diff e commit bloqueado em caso de pendencias

Status:
- [x] context
- [x] ui-spec
- [x] plan
- [ ] execute (blocked until a Fase 4.3 passar no gate de saida)
- [ ] verify/validate

### Phase 6: Busca operacional por telefone e CPF

**Goal:** Permitir busca operacional por telefone/CPF com estrategia segura de indexacao.
**Requirements**: `SEARCH-01`, `SEARCH-02`
**Depends on:** Phase 5
**Plans:** 0 plans

Plans:
- [ ] TBD (run $gsd-discuss-phase 6 -> $gsd-plan-phase 6) - blocked until o freeze do core terminar e a Fase 5 reabrir
