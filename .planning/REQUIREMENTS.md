# Requirements: SaaS Sistema Retencao

**Defined:** 2026-03-24
**Core Value:** A equipe da academia precisa confiar que cada tela mostra o estado real do aluno e so oferece acoes que de fato fecham operacionalmente.

## v3.1.0 Requirements

### CRM Integrity

- [ ] **CRM-01**: Editar lead nao destrói o historico estruturado de contato existente
- [ ] **CRM-02**: Equipe pode adicionar nova observacao comercial via append sem sobrescrever eventos anteriores
- [ ] **CRM-03**: Timeline de contato do lead exibe entradas legadas e estruturadas em uma leitura unica
- [ ] **CRM-04**: Handoff de conversao continua separado do historico de contato

### Member Lookup

- [ ] **LOOK-01**: Busca de membros aceita nome, email ou matricula (`external_id`)
- [ ] **LOOK-02**: Recepcao e gerente conseguem filtrar alunos com 7, 14 ou 30 dias sem check-in
- [ ] **LOOK-03**: Recepcao e gerente conseguem isolar ou ocultar membros provisórios
- [ ] **LOOK-04**: Listagem sinaliza visualmente quando um membro e provisório

### Shared Context

- [ ] **CTX-01**: Notas internas do Profile 360 passam a refletir apenas o estado persistido na API
- [ ] **CTX-02**: Falha ao salvar nota interna e mostrada explicitamente, sem persistencia silenciosa local

### Admin Surface

- [ ] **ADMIN-01**: Manager nao ve mais seed/delete owner-only em automacoes
- [ ] **ADMIN-02**: Owner continua com controle completo de automacoes
- [ ] **ADMIN-03**: Gestao de usuarios usa terminologia correta de desativacao/reativacao

## vNext Requirements

### Operations

- **OPS-01**: Importacao permite mapeamento manual/visual de colunas antes do commit
- **OPS-02**: Sistema oferece bulk update dedicado fora do fluxo de importacao
- **OPS-03**: Busca operacional suporta telefone/CPF com estrategia segura de indexacao

## Out of Scope

| Feature | Reason |
|---------|--------|
| Mapper visual de importacao | Import preview atual sustenta piloto; mapper completo fica para milestone futuro |
| Bulk update dedicado | Nao bloqueia o milestone atual |
| Busca por telefone/CPF | Dados criptografados exigem desenho especifico antes de expor a busca |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| CRM-01 | Phase 1 | Pending |
| CRM-02 | Phase 1 | Pending |
| CRM-03 | Phase 1 | Pending |
| CRM-04 | Phase 1 | Pending |
| CTX-01 | Phase 1 | Pending |
| CTX-02 | Phase 1 | Pending |
| LOOK-01 | Phase 2 | Pending |
| LOOK-02 | Phase 2 | Pending |
| LOOK-03 | Phase 2 | Pending |
| LOOK-04 | Phase 2 | Pending |
| ADMIN-01 | Phase 3 | Pending |
| ADMIN-02 | Phase 3 | Pending |
| ADMIN-03 | Phase 3 | Pending |

**Coverage:**
- v3.1.0 requirements: 13 total
- Mapped to phases: 13
- Unmapped: 0

---
*Requirements defined: 2026-03-24*
*Last updated: 2026-03-24 after GSD bootstrap*
