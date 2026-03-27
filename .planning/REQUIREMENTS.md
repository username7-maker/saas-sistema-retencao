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
| Upload real de avatar com storage dedicado neste ciclo | Nesta rodada o piloto fecha avatar por URL para nao abrir infra extra antes da validacao |

---
*Requirements defined: 2026-03-24 for v3.2.0*
