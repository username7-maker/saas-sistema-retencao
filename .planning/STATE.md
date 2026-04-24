---
milestone: v3.2.0
phase: 4.43.1
plan: "Simplificacao operacional do AI Inbox"
status: A `4.43.1` foi validada e o gate de entrada do milestone `v3.3.0` foi liberado; o HTML `ai_first_os_academia_v2.html` foi absorvido no programa futuro e o proximo passo correto agora e abrir `7.0 Lead-to-member intelligence graph e payload canonico`.
last_activity: 2026-04-23 - `4.43.1` promovida para `PASS` com `04.43.1-VALIDATION.md`
---

# STATE

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-24)

**Core value:** A equipe da academia precisa confiar que cada tela mostra o estado real do aluno e so oferece acoes que de fato fecham operacionalmente.
**Current focus:** Abrir o primeiro corte executavel do milestone `v3.3.0 AI Lead-to-Member Intelligence Foundation`.

## Current Position

**Phase:** 7.0 (next)
**Plan:** `Lead-to-member intelligence graph e payload canonico`
**Status:** `v3.2.0` permanece como milestone ativo para documentacao, mas o ultimo gate de entrada foi fechado, a v2 do HTML foi incorporada e a proxima execucao recomendada ja e a abertura de `7.0`
**Last activity:** 2026-04-23 - `4.43.1` fechada em `verify/validate`

## Progress Snapshot

**Active milestone:** v3.2.0
**Phases planned:** 23
**Plans planned:** 23
**Plans completed:** 3

## Accumulated Context

### Latest Milestone Outcome

- `v3.1.0` melhorou CRM, busca operacional inicial e superficies administrativas
- Phase 4 concluiu import mapper com reconciliacao manual e preview seguro
- Phase 4.1 fechou birthday importado, recalc duravel de risco, websocket distribuido e suites verdes
- Phase 4.2 alinhou RBAC com backend, criou task-lite do trainer e completou CI do frontend
- O milestone 4.x entrou em freeze lateral e agora trata o piloto como gate de saida do hardening

### Current Milestone Scope

- Phase 4: import mapper e reconciliacao manual - concluida
- Phase 4.1: hardening P0 - concluida
- Phase 4.2: coerencia operacional P1 - concluida
- Phase 4.3: piloto controlado - validada; o gate passou no escopo ativo do piloto com `nps_dispatch` e `whatsapp_webhook_setup` em `PASS`
- Phase 4.31: bioimpedancia assistida e Actuar readiness - publicada no piloto
- Phase 4.32: canais reais do piloto - concluida com WhatsApp real auditavel e `assisted_rpa` do Actuar validado com credenciais reais; o alvo final foi corrigido para os campos editaveis de `Composicao corporal e perimetria`
- Phase 4.33: transparencia de IA e fluxos publicos - concluida com contrato minimo implementado, publicado no piloto e verificado visualmente nas superficies autenticadas
- Phase 4.34: superficies administrativas e relatorios do piloto - blocker-only durante o freeze
- Phase 4.36 + 4.40: sessao e borda segura - concluida com smoke real publicado e verify/validate fechado
- Phase 4.37: protecao de PII, import/export e baseline LGPD - validada; exportacao/anonymizacao LGPD agora sao tenant-scoped e cobrem entidades correlatas do titular
- Phase 4.38: fila duravel, retry e observabilidade de jobs - validada; amostra operacional minima controlada (`whatsapp_webhook_setup`, `p95 = 7.21s`) aceita como suficiente para o gate desta fase
- Phase 4.39: guardrails de tenant e consistencia transacional - validada; helpers centrais allowlisted, telemetria estruturada e regressao focada do loop core fechadas
- Phase 4.41: handoff seguro para Kommo - blocker-only durante o freeze
- Phase 4.42: Actuar Bridge local - blocker-only durante o freeze
- Phase 4.42.1: Actuar Bridge extension relay - blocker-only durante o freeze
- Phase 4.42.2: plataforma de relatorios premium - validada no piloto com renderer compartilhado servindo tela dedicada e PDFs premium reais
- Phase 4.42.3: relatorios premium de avaliacoes - validada no piloto com CTA no workspace, rota dedicada e PDFs `Resumo do aluno` / `Relatorio tecnico`
- Phase 4.42.4: relatorios premium de gestao - validada no piloto com board pack `executive` gerado sobre o renderer premium
- Phase 4.42.5: central, distribuicao e rollout dos relatorios - validada no piloto com catalogo `/reports`, descoberta do laudo no workspace e geracao real por tipo
- Phase 4.43: AI-first fase 1 - Inbox de triagem - validada no piloto com walkthrough real, aprovacao item por item, tool layer segura e comparacao contra baseline
- Phase 4.43.1: simplificacao operacional do AI Inbox - implementada localmente para transformar a inbox validada em fila de execucao operador-first, sem quebrar os guardrails auditaveis
- Phase 5: bulk update dedicado de membros - pausada ate a saida do hardening
- Phase 6: busca operacional por telefone/CPF - pausada ate a reabertura do roadmap depois do hardening

### Roadmap Evolution

- Phase 4.43 added: AI-first fase 1 - Inbox de triagem, posicionada como primeira aposta pos-freeze e bloqueada pelos gates de hardening, canais reais e transparencia de IA
- 2026-04-02: gate operacional da 4.43 formalizado com `04.43-BASELINE.md` e `04.43-APPROVAL-POLICY.md`
- 2026-04-02: 4.32 e 4.33 passaram a existir como fases GSD completas em documentacao, em vez de placeholders no roadmap
- 2026-04-02: `saas-frontend-pearl.vercel.app` recebeu a rodada da 4.33; Railway API `eb0f9583-e09c-4ee7-bb43-eb361b6309cf` e worker `05f388c1-fde6-4a24-bb40-1fa69655fb83` fecharam `SUCCESS`
- 2026-04-02: evidencia operacional da 4.32 consolidada: `ai-gym-os-piloto` nao possui credenciais reais do Actuar automatico e os syncs observados seguem em `local_bridge`/manual
- 2026-04-02: `assisted_rpa` foi implementado sobre o provider Playwright ja existente e conectado ao teste de conexao e ao sync server-side
- 2026-04-02: credenciais reais do Actuar foram gravadas na academia piloto; o `test-connection` validou login real, o worker abriu o dashboard administrativo autenticado, e a hipoteses antiga de `bioimpedancia/perimetria` foi descartada
- 2026-04-02: o fluxo `assisted_rpa` do backend foi trocado para o caminho informado pela operacao real do Actuar, abrindo `Nova avaliacao` e corrigindo o alvo final para `Composicao corporal e perimetria`
- 2026-04-02: publish da rodada `assisted_rpa` concluido no Railway: API `fd053d63-9de1-43a3-a08a-d815a5c44703` e worker `b56cdafe-86bf-4cc9-a9bb-b4bf55600343` -> `SUCCESS`
- 2026-04-02: o `assisted_rpa` passou no smoke real com um aluno controlado do piloto na superficie `Composicao corporal e perimetria`, preenchendo `weight`, `height_cm`, `body_fat_percent`, `muscle_mass_kg` e `total_energy_kcal`, com save confirmado
- 2026-04-02: a correcao final do Actuar foi publicada no Railway: API `24a4e1c8-7914-45a8-be6a-e5b78c6a8ab9` e worker `50cfd1c5-919f-4952-9e1c-605bffe138cc` -> `SUCCESS`
- 2026-04-03: logs reais do worker mostraram falha em `Nova Avaliacao` apesar do membro ter sido encontrado; o cliente Playwright passou a iterar sobre matches visiveis e a usar fallback para o CTA global em `todas-avaliacoes`, publicado em Railway: API `bebb6f52-3214-4984-a66c-2fc3bc69e6c7` e worker `fbb8c5f5-3666-4f48-80db-c696093ebba4`
- 2026-04-03: a regressao restante do aluno controlado do piloto foi fechada com seletores por `href` para `Nova avaliacao`, espera da tabela `Avaliacoes realizadas` como superficie interativa real e correcoes de texto com acento no Actuar; publicado em Railway: API `a4a94f65-c182-42e1-98b1-b861f6ddd37a` e worker `11fd1497-9b18-4bdb-992b-3362aebc1b26`, com reprocessamento final `a3ba5e69-5f91-42b5-82fc-71775acbd018` terminando `synced_to_actuar`
- 2026-04-02: a 4.33 foi reforcada no `AIAssistantPanel` com `provider` e `mode` visiveis, publicada no alias `saas-frontend-pearl.vercel.app` via Vercel `dpl_12GeBAXzVs2k9xFyMa3mjLbuSMfp` e validada visualmente com evidencias em `.planning/phases/04.33-transparencia-de-ia-e-fluxos-publicos/evidence/04.33-{tasks-drawer,onboarding-panel,retention-drawer}.png`
- 2026-04-09: `4.36+4.40` ganhou hardening local adicional com normalizacao de origens, guardrail de producao para `FRONTEND_URL`/`CORS_ORIGINS`, `no-store` uniforme em `/api/v1/auth/*` e baseline de headers reforcado; suites focadas fecharam `32 passed` no backend e `2 passed` no frontend
- 2026-04-09: Phase 4.42.2 inserted after Phase 4.42.1: Plataforma de relatorios premium (URGENT)
- 2026-04-09: Phase 4.42.3 inserted after Phase 4.42.2: Relatorios premium de avaliacoes (URGENT)
- 2026-04-09: Phase 4.42.4 inserted after Phase 4.42.3: Relatorios premium de gestao (URGENT)
- 2026-04-09: Phase 4.42.5 inserted after Phase 4.42.4: Central, distribuicao e rollout dos relatorios (URGENT)
- 2026-04-09: programa de relatorios premium passou a existir antes da `4.43`, com fundacao compartilhada, trilhos separados para avaliacoes e gestao, e rollout/catalogo planejados para validacao no piloto antes da primeira fase AI-first
- 2026-04-09: 4.42.2 iniciou execucao tecnica com novo `premium_report_service`, renderer `HTML/CSS -> PDF` baseado em Playwright, blocos premium reutilizaveis, payload semantico para dashboards e troca do endpoint `/reports/dashboard/{dashboard}/pdf` para o novo pipeline
- 2026-04-09: 4.42.3 iniciou execucao tecnica com substituicao do PDF textual de bioimpedancia por laudos premium, dois formatos (`Resumo do aluno` e `Relatorio tecnico`) e endpoints internos `/{member_id}/body-composition/{evaluation_id}/pdf` e `/technical-pdf`
- 2026-04-09: 4.42.4 iniciou execucao tecnica com enriquecimento dos payloads premium de gestao; `executive`, `operational`, `commercial`, `financial`, `retention` e `consolidated` ganharam comparativos, graficos adicionais, narrativas e tabelas de apoio para board packs mais densos
- 2026-04-09: 4.42.5 iniciou execucao tecnica com a evolucao de `ReportsPage` para catalogo premium, card de distribuicao mensal com status humano e guia explicito para `Resumo do aluno` e `Relatorio tecnico`; `ReportsPage.test.tsx` fechou `2 passed` e o build do frontend ficou verde
- 2026-04-09: a rodada premium foi publicada; preview frontend em `https://saas-frontend-1w3isepad-automai.vercel.app` (`dpl_3a4nYkxhimBd2iK5AGqqdUTK7k5U`, `READY`), backend Railway `58ea040d-f443-49c5-bd9b-49dca1d7097f` e worker `8a33f2e5-c467-4a42-acee-b48debfd5743` terminaram `SUCCESS`, com `/health/ready` em `{"status":"ok"}`
- 2026-04-09: regressao publicada do Actuar mostrou `massa` e rollups ainda zerados apesar de `estatura`, `% gordura` e `massa muscular` ja persistirem; a correcao endureceu o selector de `massa`, adicionou `target_weight_kg`, passou a clicar `Atualizar` antes do `Salvar` e foi publicada no Railway: API `228d33c0-5a86-43f9-8b3e-d95678b7112f`, worker `9e03153f-0a2d-403a-b7bd-8b3c53968bf6`
- 2026-04-09: o worker publicado ainda encontrou um overlay global de privacidade na tela `#/avaliacoes/todas-avaliacoes`; o browser client passou a tratar esse consent modal como overlay global, com suites focadas em `41 passed`
- 2026-04-09: retry real de um aluno controlado do piloto (`evaluation_id` e `job_id` redigidos no historico publico) terminou `synced`, e o `action_log` confirmou `weight`, `height_cm`, `target_weight_kg`, `body_fat_percent`, `muscle_mass_kg`, `total_energy_kcal` e `recalculated`
- 2026-04-10: a fila `Pendencias Actuar` deixou de mostrar historico obsoleto por aluno; o incidente de uma aluna piloto foi reduzido a supersedencia de tentativas antigas, com API Railway `24332afd-60a1-4abe-95b4-a7a028f3bfcd`, worker `3c455c5d-7d89-4f08-9a76-d72fcfc4caa8` e cheque no banco real retornando fila vazia para a busca controlada
- 2026-04-10: o smoke de `4.36+4.40` encontrou e corrigiu uma regressao real no websocket publicado (`websocket.accept()` duplicado entre `app.main` e `websocket_manager.connect`); a release Railway API `89e81518-0505-49ed-a5ff-5d2b344ff6da` validou login/refresh/logout cross-origin, reject fora da allowlist, websocket por frame inicial e baseline de headers/CSP na borda publicada
- 2026-04-10: `4.39` ganhou allowlist explicita no helper central de tenant bypass; `include_all_tenants(...)` agora aceita apenas prefixes aprovados, `unscoped_tenant_access(...)` ficou limitado aos motivos de jobs cross-tenant nomeados, e a regressao focada (`test_database_tenant_guardrails`, `test_dependencies`, `test_scheduler_jobs`, `test_actuar_bridge_service`, `test_body_composition_sync`) fechou `44 passed`
- 2026-04-14: a trilha premium de bioimpedancia fechou o primeiro corte full-stack: modelo/schema expandido com `measured_at`, `age_years`, `sex`, `height_cm`, `parsing_confidence`, `data_quality_flags_json`, `reviewer_user_id` e `import_batch_id`; o OCR passou a devolver flags de qualidade sem persistir automaticamente; o backend ganhou `review`, `report` e aliases REST coerentes; o workspace do aluno ganhou gate de revisao humana, CTA `Relatorio premium pronto` e rota `/assessments/members/{member_id}/body-composition/{evaluation_id}/report`; regressao focada fechou `28 passed` no backend e `2 passed` no frontend, com `npm run build` verde
- 2026-04-14: a rodada premium de bioimpedancia foi publicada no piloto; Vercel production `dpl_BeV2FSEpF27bdq99XMVW7LADcvTj` ficou `READY` e foi aliased para `https://saas-frontend-pearl.vercel.app`, Railway API `ccac2270-5e14-47df-aad7-d75751a40763` e worker `1b7cc6b9-5213-4c15-8e0b-3529d0ddbd3e` terminaram `SUCCESS`, com `https://ai-gym-os-api-production.up.railway.app/health/ready` respondendo `200 {"status":"ok"}`
- 2026-04-14: o laudo premium de bioimpedancia saiu do layout de app/card para um layout clinico/documental inspirado na referencia operacional do InBody, sem copiar a marca nem a pagina pixel a pixel; a tela premium, o `Resumo do aluno` e o `Relatorio tecnico` agora compartilham header de ficha, tabela densa de composicao, bandas clinicas de `musculo-gordura` e `obesidade`, rail lateral de score/controle, historico em grade e leitura final deterministica
- 2026-04-14: o redesign clinico/documental dos laudos premium foi publicado no piloto; Vercel production `dpl_5vK3dguGPEjkpTPy3tBpqtLs1o8V` ficou `READY` e foi aliased para `https://saas-frontend-pearl.vercel.app`, Railway API `cce8bde2-9526-47f7-8600-c9943079f7b2` e worker `833ed9fc-5c3a-428d-86fa-3c84677ea1bd` terminaram `SUCCESS`
- 2026-04-15: o feedback do piloto ainda mostrou corte no final de `Atual x anterior` e `Leitura final e observacoes` em PDFs tecnicos densos; o rail lateral foi compactado com menos linhas em `Comparativo rapido`, menos `Dados adicionais`, truncamento controlado de insight/notas e tipografia menor apenas na lateral; validacao local fechou `25 passed` e screenshots worst-case integrais, e a API correta foi publicada no Railway via `--path-as-root` em `a66e5896-83c8-4890-b325-ed0bf6cd9749` -> `SUCCESS`
- 2026-04-16: os HTMLs conceituais `ai_first_os_academia` e `diagnostico_ai_gym_os` foram convertidos em recorte executavel via Spec Kit, abrindo `specs/002-ai-first-operating-inbox`; decisao mantida: a primeira aposta AI-first continua sendo a inbox operacional de triagem da `4.43`, sem abrir coach pessoal, nutricao, wearables ou marketing IA amplo neste ciclo
- 2026-04-16: a `specs/002-ai-first-operating-inbox` avancou para `plan.md`; o plano confirma implementacao futura em slices sobre a `4.43`, mas continua explicitamente bloqueado ate os gates de hardening, piloto e relatorios premium fecharem
- 2026-04-16: `4.39` ganhou regressao focada para workers e jobs cross-tenant; `test_core_async_job_service.py` entrou cobrindo claim allowlisted de `CoreAsyncJob` e `RiskRecalculationRequest`, troca de contexto por `gym_id` e contrato de `get_public_diagnosis_job`, enquanto `test_scheduler_jobs.py` passou a verificar os motivos allowlisted de `nurturing_followup_job` e `booking_reminder_job`; corte validado com `23 passed`
- 2026-04-16: `4.39` ganhou regressao adicional no nivel de endpoint; `test_sales_routes.py` passou a cobrir binding de `lead_id` e lookup por `gym_id` em `proposal_dispatch_status_endpoint`, contrato basico de `booking_status_endpoint`, e `test_public_endpoints.py` agora cobre `404` do status publico de diagnostico quando o `lead_id` nao fecha; corte validado com `38 passed`
- 2026-04-16: `4.39` ganhou telemetria estruturada nos helpers centrais de bypass; `include_all_tenants(...)` e `unscoped_tenant_access(...)` agora emitem eventos allowlisted com `tenant_bypass_reason` e `gym_id` quando houver contexto, e a regressao focada fechou `40 passed`
- 2026-04-16: `4.39` passou para `verify/validate`; a fase ganhou `04.39-VALIDATION.md`, o roadmap foi marcado como `execute + verify/validate` concluido e o corte do loop core foi considerado fechado
- 2026-04-16: `4.37` passou para `verify/validate`; a fase ganhou `04.37-VALIDATION.md`, o DSAR deixou de cobrir apenas `Member` e passou a redigir `Lead`, `MessageLog`, `MemberConstraints`, `BodyCompositionEvaluation` e textos livres de `NPSResponse`, com regressao focada `81 passed`
- 2026-04-17: `4.38` passou para `verify/validate`; a fase ganhou `04.38-VALIDATION.md` com `PASS`, com base em amostra operacional minima controlada no piloto (`1` `CoreAsyncJob`, `p95 queue_wait_seconds = 7.21s`)
- 2026-04-18: a `4.3` passou no escopo ativo do piloto; `pilot_gate_report.py` passou a medir apenas as superficies realmente habilitadas no tenant, `whatsapp_webhook_setup` foi estabilizado com reuso de instancia + payload correto de webhook na Evolution API, e a `4.43` ficou oficialmente desbloqueada para execucao
- 2026-04-18: a `4.43` iniciou a `Wave 1 backend` com `AITriageRecommendation`, migration `20260418_0031`, agregacao `retention + onboarding`, rotas `GET /api/v1/ai/triage/items*` e auditoria tenant-safe, validada com `6 passed`
- 2026-04-18: a `4.43` fechou a `Wave 2` com a pagina dedicada `AI Triage Inbox`, rota `/ai/triage`, shell na navegacao principal, estados `loading/empty/error/degraded`, e aprovacao humana item por item via `PATCH /api/v1/ai/triage/items/{recommendation_id}/approval`, validada com `9 passed` no backend, `3 passed` no frontend e `npm run build` verde
- 2026-04-19: a `4.43` fechou localmente a `Wave 3`; a API ganhou `POST /api/v1/ai/triage/items/{recommendation_id}/actions/prepare`, `PATCH /api/v1/ai/triage/items/{recommendation_id}/outcome` e `GET /api/v1/ai/triage/metrics/summary`, a inbox passou a preparar task/owner/follow-up/mensagem sob aprovacao humana, `enqueue_approved_job` ficou honesto como indisponivel sem contrato seguro, e a validacao fechou `16 passed` no backend, `4 passed` no frontend e `npm run build` verde
- 2026-04-19: a `4.43` fechou a `Wave 4` no piloto; o frontend publicado no alias `saas-frontend-pearl.vercel.app` completou walkthrough controlado com `Wave 4 Retention Member` e `Wave 4 Onboarding Member`, a captura browser gerou evidencias reais da inbox/lista/detalhe/aprovacao/metricas, e a comparacao contra o baseline congelado foi registrada em `04.43-WAVE4-WALKTHROUGH-2026-04-19.{md,json}` e `04.43-VALIDATION.md`
- 2026-04-23: a `4.43.1` abriu um slice incremental pos-validacao para reduzir o atrito da AI Inbox; o backend passou a expor `operator_summary`, `primary_action_type`, `primary_action_label`, `requires_explicit_approval` e `show_outcome_step`, `actions/prepare` ganhou `auto_approve`, `confirm_approval` e `operator_note`, e a UI foi reorganizada para `Fazer agora`, mensagem/resumo curto, CTA principal e detalhes analiticos recolhidos; validacao local fechou `20 passed` no backend, `7 passed` no frontend e `npm run build` verde, e a rodada foi publicada no piloto com frontend `dpl_AriTb8CyJLUkfTQeWetXZ5EHoXGE` e Railway `6f507927-9cd5-4711-95e6-741c5990a60f`

### Security Hardening Backlog Now Converted To Phases

- Workstream 4.36+4.40: sessao e borda segura - P0
- Phase 4.37: protecao de PII, import/export e baseline LGPD - P0
- Phase 4.39: guardrails de tenant e consistencia transacional - P0/P1 do loop core
- Phase 4.38: fila duravel, retry e observabilidade de jobs - P1 estrutural

These phases now gate any feature expansion beyond the pilot.
