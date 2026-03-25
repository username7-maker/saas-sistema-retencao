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

---
*Requirements defined: 2026-03-24 for v3.2.0*
