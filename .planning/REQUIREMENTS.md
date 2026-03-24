# Requirements: SaaS Sistema Retencao

**Defined:** 2026-03-24
**Core Value:** A equipe da academia precisa confiar que cada tela mostra o estado real do aluno e so oferece acoes que de fato fecham operacionalmente.

## v3.2.0 Requirements

### Import Flow

- [ ] **IMP-01**: Preview de importacao permite mapear/reconciliar colunas antes do commit
- [ ] **IMP-02**: Operador consegue revisar impacto, warnings e colunas nao reconhecidas antes de gravar

### Bulk Update

- [ ] **BULK-01**: Sistema oferece fluxo dedicado de atualizacao em massa fora da importacao
- [ ] **BULK-02**: Atualizacao em massa exige preview/confirmacao e evita escrita cega

### Sensitive Search

- [ ] **SEARCH-01**: Busca operacional suporta telefone com estrategia segura de indexacao
- [ ] **SEARCH-02**: Busca operacional suporta CPF com estrategia segura de indexacao

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| IMP-01 | Phase 4 | Completed |
| IMP-02 | Phase 4 | Completed |
| BULK-01 | Phase 5 | Pending |
| BULK-02 | Phase 5 | Pending |
| SEARCH-01 | Phase 6 | Pending |
| SEARCH-02 | Phase 6 | Pending |

## Out of Scope

| Feature | Reason |
|---------|--------|
| Novo redesign da tela de membros | O foco e fluxo/base operacional, nao repaginacao ampla |
| Expansao de permissoes de backend | A estrategia continua sendo superficie verdadeira |

---
*Requirements defined: 2026-03-24 for v3.2.0*
