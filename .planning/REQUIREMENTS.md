# Requirements: SaaS Sistema Retencao

**Defined:** 2026-03-24
**Core Value:** A equipe da academia precisa confiar que cada tela mostra o estado real do aluno e so oferece acoes que de fato fecham operacionalmente.

## v3.2.0 Requirements

### Hardening P0

- [x] **HARD-01**: `birthday_label` importado funciona em dashboards e automacoes de aniversario
- [x] **HARD-02**: recalc manual de risco deixa de usar thread daemon e vira solicitacao duravel consumida pelo worker
- [x] **HARD-03**: realtime/WebSocket funciona com mais de um worker da API usando Redis Pub/Sub
- [x] **HARD-04**: suites backend/frontend voltam a ficar totalmente verdes antes do piloto

### Coerencia Operacional P1

- [x] **OPS-01**: routers passam a orquestrar commits dos fluxos criticos do piloto, sem commit implicito espalhado nos services centrais
- [x] **OPS-02**: frontend reflete as capacidades reais do backend para recepcao, comercial e trainer
- [x] **OPS-03**: trainer resolve tarefas tecnicas dentro de `Assessments` sem abrir o modulo geral de tasks
- [x] **OPS-04**: CI do frontend roda lint e testes unitarios alem de typecheck/build/e2e

### Bioimpedancia e Actuar readiness

- [ ] **BODY-01**: fluxo de bioimpedancia deixa explicito quando a leitura e `OCR local`, `IA assistida` ou `fallback/manual`
- [ ] **BODY-02**: piloto nao promete sync Actuar automatico quando a academia ou o ambiente estiverem desabilitados
- [ ] **BODY-03**: campos nao suportados pelo Actuar e necessidade de sync manual ficam visiveis no workflow
- [ ] **BODY-04**: owner, manager e trainer conseguem entender com clareza se o fluxo esta ativo, parcial ou manualmente assistido

### Canais reais do piloto

- [x] **COMMS-01**: WhatsApp do piloto funciona de ponta a ponta com instancia conectada, webhook configurado e uso real no produto
- [ ] **COMMS-02**: email do piloto funciona com remetente verificado e pelo menos um envio real validado

### Transparencia de IA e fluxos publicos

- [x] **AI-01**: dashboards e narrativas deixam explicito quando o conteudo vem de IA real versus fallback automatico
- [x] **PUB-01**: fluxos publicos do piloto ficam claramente ativados ou escondidos, sem endpoints semi-prometidos e desabilitados

### Superficies administrativas e relatorios do piloto

- [ ] **ADMIN-01**: notificacoes do piloto carregam sem redirects quebrando autenticacao
- [ ] **ADMIN-02**: metas podem ser criadas e listadas no piloto sem erro de contrato de rota
- [ ] **ADMIN-03**: relatorios executivo, consolidado e disparo mensal geram PDF sem falhar quando o dashboard vem serializado do cache
- [ ] **ADMIN-04**: NPS deixa explicito o estado vazio e nao parece modulo quebrado quando ainda nao ha respostas
- [ ] **ADMIN-05**: usuarios podem editar foto por URL, cargo e campos basicos de perfil; owner pode ajustar papel e dados da equipe com regras coerentes

### Identidade de usuario e funcoes ricas

- [ ] **IDENTITY-01**: usuarios podem enviar foto real de perfil com upload seguro, preview e persistencia estavel
- [ ] **IDENTITY-02**: sistema separa claramente `role` de permissao de `funcao/cargo` exibida na operacao
- [ ] **IDENTITY-03**: owner e manager conseguem administrar foto, nome exibido, cargo e funcao sem confundir isso com RBAC
- [ ] **IDENTITY-04**: telas administrativas deixam explicito o que muda permissao versus o que muda apenas identidade organizacional

### Higiene de tokens e superficies publicas

- [x] **SEC-01**: reset de senha, websocket e webhook deixam de transportar segredos ou tokens por query string
- [x] **SEC-02**: ambiente de producao falha o startup se rate limiting real nao estiver disponivel
- [x] **SEC-03**: endpoints publicos mais sensiveis exigem contratos de abuso mais fortes do que apenas payload livre e rate limit superficial
- [x] **SEC-04**: readiness e outros endpoints de operacao nao vazam detalhes internos de banco/cache/infra para clientes anonimos

### Protecao de PII e import/export

- [ ] **DATA-01**: exports CSV neutralizam formula injection em qualquer campo textual exportado
- [ ] **DATA-02**: imports CSV/XLSX impõem limites reais de linhas, colunas e descompressao para evitar parser abuse e DoS logico
- [ ] **DATA-03**: logs e auditoria redigem campos sensiveis de auth, notificacao, CRM e automacoes
- [ ] **DATA-04**: campos de PII mais expostos deixam de permanecer em texto puro sem decisao explicita de protecao ou minimizacao

### Resiliencia de consultas e jobs

- [ ] **PERF-01**: listagens e filtros centrais deixam de carregar datasets inteiros em memoria para filtrar no Python
- [ ] **PERF-02**: jobs pesados passam a usar batches limitados e deixam de depender de `statement_timeout = 0`
- [ ] **PERF-03**: operacoes de importacao, task listing e automacao mantem custo previsivel mesmo com tenants maiores

### Guardrails de tenant e consistencia transacional

- [ ] **TENANT-01**: o uso de `include_all_tenants` e `set_unscoped_access` fica restrito, documentado e coberto por testes
- [ ] **TENANT-02**: rotas, jobs e services criticos ganham testes de regressao contra vazamento cross-tenant
- [ ] **ARCH-01**: fronteira de commit/rollback fica padronizada nos fluxos criticos, sem service e router disputando a transacao

### Sessao e borda de producao

- [x] **SESSION-01**: refresh/access token passam a seguir um modelo com menor blast radius de XSS do que `localStorage` puro
- [x] **EDGE-01**: frontend e backend publicos servem baseline de headers de seguranca e CSP coerente com SPA + API
- [x] **EDGE-02**: builds e runtimes de producao falham rapido diante de envs ausentes ou defaults inseguros como `localhost`

### Handoff seguro para Kommo

- [ ] **KOMMO-01**: owner/manager configuram Kommo por academia com URL, token e teste de conexao sem expor o numero oficial em um segundo motor de WhatsApp
- [ ] **KOMMO-02**: automacoes do AI GYM OS conseguem entregar contexto operacional para a Kommo como handoff, sem depender do envio direto por WhatsApp do proprio sistema
- [ ] **KOMMO-03**: bioimpedancia consegue gerar handoff manual para a Kommo com resumo do aluno, resumo operacional e link do exame no AI GYM OS

### Actuar Bridge local

- [ ] **ACTBRIDGE-01**: owner/manager conseguem parear uma estacao local do Actuar por academia sem expor senha do Actuar no backend
- [ ] **ACTBRIDGE-02**: jobs do Actuar em modo `local_bridge` sao consumidos apenas pela estacao local, nunca pelo worker server-side atual
- [ ] **ACTBRIDGE-03**: a estacao local consegue fazer heartbeat, reivindicar um job, concluir ou falhar a execucao e devolver esse estado ao AI GYM OS
- [ ] **ACTBRIDGE-04**: Settings deixa claro quando existe uma estacao online, quando ela ficou offline e quando o piloto segue no fallback manual
- [ ] **ACTBRIDGE-05**: a operacao consegue anexar explicitamente a aba real do Actuar por extensao do navegador, sem exigir abrir o browser com flags de debugging
- [ ] **ACTBRIDGE-06**: o relay local em loopback consegue entregar jobs para a extensao e receber sucesso/falha de forma segura e observavel

### Plataforma de relatorios premium

- [x] **RPT-01**: o sistema gera PDFs premium via pipeline `HTML/CSS -> PDF` desacoplado de `reportlab` textual
- [x] **RPT-02**: cada tipo de relatorio passa a ter um payload semantico proprio, sem depender de dump direto de dashboard ou tela
- [x] **RPT-03**: existe uma biblioteca reutilizavel de blocos premium para capa, cabecalho, KPIs, comparativos, graficos, narrativas e CTAs
- [x] **RPT-04**: o PDF premium suporta branding leve da academia sem perder a identidade do AI GYM OS

### Relatorios premium de avaliacoes

- [x] **RPTA-01**: cada avaliacao de composicao corporal consegue gerar um `Resumo do aluno` premium com comparativo e leitura resumida
- [x] **RPTA-02**: cada avaliacao de composicao corporal consegue gerar um `Relatorio tecnico` premium para coach ou operacao
- [x] **RPTA-03**: secoes opcionais como perimetria e exame anterior possuem fallback elegante, sem blocos vazios ou quebrados
- [x] **RPTA-04**: relatorios de avaliacao podem ser entregues pelos canais internos ja existentes sem criar um fluxo paralelo

### Relatorios premium de gestao

- [x] **RPTG-01**: os relatorios `executive`, `operational`, `commercial`, `financial` e `retention` deixam de ser dumps textuais e viram PDFs premium com KPIs, tendencias e leitura curta
- [x] **RPTG-02**: o relatorio `consolidated` vira um board pack mensal de lideranca, nao apenas concatenacao de secoes
- [x] **RPTG-03**: o backend coleta dados de gestao a partir de payloads semanticos robustos a cache serializado, nao de leitura crua do dashboard
- [x] **RPTG-04**: filtros de periodo, tenant e escopo ficam padronizados por tipo de relatorio quando suportados

### Central e distribuicao de relatorios

- [x] **RPTH-01**: a Central de Relatorios deixa claro o que pode ser gerado, para quem e com qual objetivo, com status e historico recente
- [x] **RPTH-02**: a geracao assincrona e o disparo mensal passam a operar com os PDFs premium
- [x] **RPTH-03**: o piloto valida ao menos um relatorio premium de avaliacoes e um relatorio premium de gestao com evidencia visual real

## v3.3.0+ AI-First OS Academia Expansion Requirements

### Lead-to-member intelligence foundation

- [ ] **AIOS-01**: o sistema cria um grafo canonico que une captacao, CRM, consentimentos, onboarding, frequencia, avaliacoes, tarefas, risco, renovacao e upsell
- [ ] **AIOS-02**: origem de lead, etapa comercial e historico de relacionamento continuam disponiveis apos conversao para membro
- [ ] **AIOS-03**: consentimentos e termos operacionais ficam associados ao ciclo lead-to-member sem permitir campanhas fora de base legal
- [ ] **AIOS-04**: Profile 360, AI Inbox, CRM e dashboards passam a consumir o mesmo payload canonico do contato/aluno
- [ ] **AIOS-05**: a jornada operacional cobre aquisicao, onboarding, ativo, risco, renovacao e reativacao com roteamento por turno, papel e owner

### Assessment, coach and BI foundation

- [ ] **AIOS-06**: o coach workspace nasce staff-first, com recomendacoes assistidas e override humano obrigatorio
- [ ] **AIOS-07**: avaliacao fisica IA expande avaliacoes e bioimpedancia sem prometer visao computacional antes de existir pipeline real
- [ ] **AIOS-08**: dashboards e reports passam a expor cohort, LTV, forecast, receita em risco e impacto de follow-up sobre o contexto canonico
- [ ] **AIOS-09**: o motor de recomendacao e scoring fica reutilizavel entre retencao, onboarding, coach, growth e BI

### Acquisition, compliance and revenue

- [ ] **AIOS-10**: captacao de leads suporta origem/canal/campanha, landing ou formulario, aula experimental e handoff para CRM
- [ ] **AIOS-11**: chatbot qualificador e score de propensao aparecem somente quando houver consentimento, origem e degraded state claros
- [ ] **AIOS-12**: contratos, termos, consentimento LGPD, imagem e comunicacao possuem historico auditavel por aluno/lead
- [ ] **AIOS-13**: vencimento ou ausencia de termo critico gera alerta operacional sem bloquear indevidamente a rotina da academia
- [ ] **AIOS-14**: marketing IA opera por audiencias, copy e canais com aprovacao humana e trilha auditavel
- [ ] **AIOS-15**: CRM, WhatsApp, Kommo, NPS e automations formam a base canonica de campanhas, reativacao, renovacao e upsell
- [ ] **AIOS-16**: financeiro usa fonte real para caixa, contas, inadimplencia, DRE basico e receita em risco
- [ ] **AIOS-17**: forecast financeiro e fluxo de caixa mostram confianca/degraded state quando a base for insuficiente

### Adherence, schedule and staff operations

- [ ] **AIOS-18**: nutricao entra como plano/metas/aderencia assistiva, sem foto de refeicao automatica sem revisao ou provider real
- [ ] **AIOS-19**: recomendacoes de suplementacao ou dieta exigem linguagem assistiva e revisao humana
- [ ] **AIOS-20**: agenda inteligente suporta reservas, ocupacao, fila de espera, cancelamento e reagendamento
- [ ] **AIOS-21**: sugestao de horario considera capacidade real, preferencia do aluno e historico de comparecimento
- [ ] **AIOS-22**: aulas online/hibridas usam provider ou biblioteca real e deixam claro quando o modulo esta manual/degradado
- [ ] **AIOS-23**: gestao de equipe separa role, cargo, escala, owner, turno e performance operacional
- [ ] **AIOS-24**: NPS, tarefas, avaliacoes e follow-ups podem ser analisados por professor/equipe quando houver dado suficiente
- [ ] **AIOS-25**: estoque/loja/PDV opera apenas com produto, estoque, venda e fonte real definidos

### Student companion and connected network

- [ ] **AIOS-26**: app/student companion so abre experiencia direta ao aluno depois do workspace staff-first estar validado
- [ ] **AIOS-27**: app white label suporta progresso, agenda, metas, mensagens e push notifications sem quebrar a verdade tecnica do professor
- [ ] **AIOS-28**: gamificacao e comunidade usam consentimento e configuracao clara de privacidade
- [ ] **AIOS-29**: desafios, rankings, badges e grupos alimentam o contexto do aluno e o BI quando ativos
- [ ] **AIOS-30**: multiunidade/franquia opera sobre o multi-tenant atual sem vazamento entre academias
- [ ] **AIOS-31**: benchmarking e consolidado de rede deixam claro unidade, escopo e permissoes
- [ ] **AIOS-32**: wearables, equipamentos, catraca, pagamentos e API aberta entram por integracoes com origem e confianca rastreaveis
- [ ] **AIOS-33**: superficies conectadas exibem manual/degraded state quando a integracao nao estiver ativa
- [ ] **AIOS-34**: data warehouse, vector store e recomendacao compartilhada respeitam tenant safety, LGPD e auditoria
- [ ] **AIOS-35**: voz, visao computacional e learning loops so entram apos governanca e dados suficientes

### Import Flow

- [x] **IMP-01**: Preview de importacao permite mapear/reconciliar colunas antes do commit
- [x] **IMP-02**: Operador consegue revisar impacto, warnings e colunas nao reconhecidas antes de gravar

### Bulk Update

- [ ] **BULK-01**: Sistema oferece fluxo dedicado de atualizacao em massa fora da importacao
- [ ] **BULK-02**: Atualizacao em massa exige preview/confirmacao e evita escrita cega

### Sensitive Search

- [ ] **SEARCH-01**: Busca operacional suporta telefone com estrategia segura de indexacao
- [ ] **SEARCH-02**: Busca operacional suporta CPF com estrategia segura de indexacao

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| HARD-01 | Phase 4.1 | Completed |
| HARD-02 | Phase 4.1 | Completed |
| HARD-03 | Phase 4.1 | Completed |
| HARD-04 | Phase 4.1 | Completed |
| OPS-01 | Phase 4.2 | Completed |
| OPS-02 | Phase 4.2 | Completed |
| OPS-03 | Phase 4.2 | Completed |
| OPS-04 | Phase 4.2 | Completed |
| BODY-01 | Phase 4.31 | Planned |
| BODY-02 | Phase 4.31 | Planned |
| BODY-03 | Phase 4.31 | Planned |
| BODY-04 | Phase 4.31 | Planned |
| COMMS-01 | Phase 4.32 | Completed |
| COMMS-02 | Phase 4.32 | Blocked by provider credits / not part of gate atual |
| AI-01 | Phase 4.33 | Completed |
| PUB-01 | Phase 4.33 | Completed |
| ADMIN-01 | Phase 4.34 | Planned |
| ADMIN-02 | Phase 4.34 | Planned |
| ADMIN-03 | Phase 4.34 | Planned |
| ADMIN-04 | Phase 4.34 | Planned |
| ADMIN-05 | Phase 4.34 | Planned |
| IDENTITY-01 | Phase 4.35 | Planned |
| IDENTITY-02 | Phase 4.35 | Planned |
| IDENTITY-03 | Phase 4.35 | Planned |
| IDENTITY-04 | Phase 4.35 | Planned |
| SEC-01 | Phase 4.36 | Completed |
| SEC-02 | Phase 4.36 | Completed |
| SEC-03 | Phase 4.36 | Completed |
| SEC-04 | Phase 4.36 | Completed |
| DATA-01 | Phase 4.37 | Completed |
| DATA-02 | Phase 4.37 | Completed |
| DATA-03 | Phase 4.37 | Completed |
| DATA-04 | Phase 4.37 | Completed |
| PERF-01 | Phase 4.38 | Completed |
| PERF-02 | Phase 4.38 | Completed |
| PERF-03 | Phase 4.38 | Completed |
| TENANT-01 | Phase 4.39 | Completed |
| TENANT-02 | Phase 4.39 | Completed |
| ARCH-01 | Phase 4.39 | Completed |
| SESSION-01 | Phase 4.40 | Completed |
| EDGE-01 | Phase 4.40 | Completed |
| EDGE-02 | Phase 4.40 | Completed |
| KOMMO-01 | Phase 4.41 | Planned |
| KOMMO-02 | Phase 4.41 | Planned |
| KOMMO-03 | Phase 4.41 | Planned |
| ACTBRIDGE-01 | Phase 4.42 | Implemented, awaiting live validation |
| ACTBRIDGE-02 | Phase 4.42 | Implemented, awaiting live validation |
| ACTBRIDGE-03 | Phase 4.42 | Implemented, awaiting live validation |
| ACTBRIDGE-04 | Phase 4.42 | Implemented, awaiting live validation |
| ACTBRIDGE-05 | Phase 4.42.1 | Implemented, awaiting live validation |
| ACTBRIDGE-06 | Phase 4.42.1 | Implemented, awaiting live validation |
| RPT-01 | Phase 4.42.2 | Completed |
| RPT-02 | Phase 4.42.2 | Completed |
| RPT-03 | Phase 4.42.2 | Completed |
| RPT-04 | Phase 4.42.2 | Completed |
| RPTA-01 | Phase 4.42.3 | Completed |
| RPTA-02 | Phase 4.42.3 | Completed |
| RPTA-03 | Phase 4.42.3 | Completed |
| RPTA-04 | Phase 4.42.3 | Completed |
| RPTG-01 | Phase 4.42.4 | Completed |
| RPTG-02 | Phase 4.42.4 | Completed |
| RPTG-03 | Phase 4.42.4 | Completed |
| RPTG-04 | Phase 4.42.4 | Completed |
| RPTH-01 | Phase 4.42.5 | Completed |
| RPTH-02 | Phase 4.42.5 | Completed |
| RPTH-03 | Phase 4.42.5 | Completed |
| AIOS-01 | Phase 7.0 | Planned |
| AIOS-02 | Phase 7.0 | Planned |
| AIOS-03 | Phase 7.0 | Planned |
| AIOS-04 | Phase 7.1 | Planned |
| AIOS-05 | Phase 7.1 | Planned |
| AIOS-06 | Phase 7.2 | Planned |
| AIOS-07 | Phase 7.2 | Planned |
| AIOS-08 | Phase 7.3 | Planned |
| AIOS-09 | Phase 7.3 | Planned |
| AIOS-10 | Phase 8.0 | Planned |
| AIOS-11 | Phase 8.0 | Planned |
| AIOS-12 | Phase 8.1 | Planned |
| AIOS-13 | Phase 8.1 | Planned |
| AIOS-14 | Phase 8.2 | Planned |
| AIOS-15 | Phase 8.2 | Planned |
| AIOS-16 | Phase 8.3 | Planned |
| AIOS-17 | Phase 8.3 | Planned |
| AIOS-18 | Phase 9.0 | Planned |
| AIOS-19 | Phase 9.0 | Planned |
| AIOS-20 | Phase 9.1 | Planned |
| AIOS-21 | Phase 9.1 | Planned |
| AIOS-22 | Phase 9.2 | Planned |
| AIOS-23 | Phase 9.3 | Planned |
| AIOS-24 | Phase 9.3 | Planned |
| AIOS-25 | Phase 9.4 | Planned |
| AIOS-26 | Phase 10.0 | Planned |
| AIOS-27 | Phase 10.0 | Planned |
| AIOS-28 | Phase 10.1 | Planned |
| AIOS-29 | Phase 10.1 | Planned |
| AIOS-30 | Phase 10.2 | Planned |
| AIOS-31 | Phase 10.2 | Planned |
| AIOS-32 | Phase 10.3 | Planned |
| AIOS-33 | Phase 10.3 | Planned |
| AIOS-34 | Phase 10.4 | Planned |
| AIOS-35 | Phase 10.4 | Planned |
| IMP-01 | Phase 4 | Completed |
| IMP-02 | Phase 4 | Completed |
| BULK-01 | Phase 5 | Deferred until post-pilot |
| BULK-02 | Phase 5 | Deferred until post-pilot |
| SEARCH-01 | Phase 6 | Deferred until post-pilot |
| SEARCH-02 | Phase 6 | Deferred until post-pilot |

## Out of Scope

| Feature | Reason |
|---------|--------|
| Novo redesign amplo de Members ou Profile 360 | O ciclo atual e de hardening e piloto, nao de repaginacao |
| Expansao de permissoes de backend so para caber na UI | A estrategia continua sendo superficie verdadeira |
| Bulk update e busca sensivel antes do piloto | Foram explicitamente pausados ate validacao do piloto |
| Bioimpedancia com IA real, Actuar, canais e fluxos publicos tratados como detalhe de configuracao | Agora fazem parte do readiness real do piloto e ganharam fases urgentes proprias |
| Upload real de avatar com storage dedicado nesta rodada | Foi movido para a Phase 4.35 para acontecer de forma explicita, sem improvisar storage dentro da fase administrativa anterior |
| Auditoria agressiva de seguranca tratada como backlog indefinido | Os achados agora foram convertidos em fases urgentes 4.36 a 4.40 antes da retomada de feature work |

---
*Requirements defined: 2026-03-24 for v3.2.0*
