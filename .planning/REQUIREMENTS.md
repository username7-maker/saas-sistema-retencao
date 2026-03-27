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

- [ ] **COMMS-01**: WhatsApp do piloto funciona de ponta a ponta com instancia conectada, webhook configurado e uso real no produto
- [ ] **COMMS-02**: email do piloto funciona com remetente verificado e pelo menos um envio real validado

### Transparencia de IA e fluxos publicos

- [ ] **AI-01**: dashboards e narrativas deixam explicito quando o conteudo vem de IA real versus fallback automatico
- [ ] **PUB-01**: fluxos publicos do piloto ficam claramente ativados ou escondidos, sem endpoints semi-prometidos e desabilitados

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

- [ ] **SEC-01**: reset de senha, websocket e webhook deixam de transportar segredos ou tokens por query string
- [ ] **SEC-02**: ambiente de producao falha o startup se rate limiting real nao estiver disponivel
- [ ] **SEC-03**: endpoints publicos mais sensiveis exigem contratos de abuso mais fortes do que apenas payload livre e rate limit superficial
- [ ] **SEC-04**: readiness e outros endpoints de operacao nao vazam detalhes internos de banco/cache/infra para clientes anonimos

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

- [ ] **SESSION-01**: refresh/access token passam a seguir um modelo com menor blast radius de XSS do que `localStorage` puro
- [ ] **EDGE-01**: frontend e backend publicos servem baseline de headers de seguranca e CSP coerente com SPA + API
- [ ] **EDGE-02**: builds e runtimes de producao falham rapido diante de envs ausentes ou defaults inseguros como `localhost`

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
| COMMS-01 | Phase 4.32 | Planned |
| COMMS-02 | Phase 4.32 | Planned |
| AI-01 | Phase 4.33 | Planned |
| PUB-01 | Phase 4.33 | Planned |
| ADMIN-01 | Phase 4.34 | Planned |
| ADMIN-02 | Phase 4.34 | Planned |
| ADMIN-03 | Phase 4.34 | Planned |
| ADMIN-04 | Phase 4.34 | Planned |
| ADMIN-05 | Phase 4.34 | Planned |
| IDENTITY-01 | Phase 4.35 | Planned |
| IDENTITY-02 | Phase 4.35 | Planned |
| IDENTITY-03 | Phase 4.35 | Planned |
| IDENTITY-04 | Phase 4.35 | Planned |
| SEC-01 | Phase 4.36 | Planned |
| SEC-02 | Phase 4.36 | Planned |
| SEC-03 | Phase 4.36 | Planned |
| SEC-04 | Phase 4.36 | Planned |
| DATA-01 | Phase 4.37 | Planned |
| DATA-02 | Phase 4.37 | Planned |
| DATA-03 | Phase 4.37 | Planned |
| DATA-04 | Phase 4.37 | Planned |
| PERF-01 | Phase 4.38 | Planned |
| PERF-02 | Phase 4.38 | Planned |
| PERF-03 | Phase 4.38 | Planned |
| TENANT-01 | Phase 4.39 | Planned |
| TENANT-02 | Phase 4.39 | Planned |
| ARCH-01 | Phase 4.39 | Planned |
| SESSION-01 | Phase 4.40 | Planned |
| EDGE-01 | Phase 4.40 | Planned |
| EDGE-02 | Phase 4.40 | Planned |
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
