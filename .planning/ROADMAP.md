# ROADMAP

## 🚧 v3.1.0 Prontidao Operacional

**Goal:** Fechar os gaps restantes para piloto com equipe real e operacao limitada.

**Milestone Focus:**
- Integridade do historico comercial e do contexto compartilhado
- Busca operacional de alunos para balcão e gestao
- Superficie administrativa coerente com autorizacao real

### Phase 1: Integridade de CRM e contexto compartilhado

**Goal:** Eliminar perda de contexto comercial no CRM e remover o falso compartilhamento local de notas internas no Profile 360.
**Requirements**: Preservar `Lead.notes` como timeline canonica, trocar edicao destrutiva por append-only e tornar notas internas API-only.
**Depends on:** Bootstrap GSD
**Plans:** 1 plan

Plans:
- [x] Preservar historico comercial e remover fallback local de notas internas

### Phase 2: Balcao real: busca de aluno e filtros operacionais

**Goal:** Permitir busca operacional de alunos por matricula/ID externo e expor filtros de inatividade e provisorios na listagem.
**Requirements**: Reusar endpoints existentes, sem incluir busca por telefone/CPF nesta rodada.
**Depends on:** Phase 1
**Plans:** 1 plan

Plans:
- [x] Ampliar busca de membros e expor filtros operacionais reais

### Phase 3: Superficie verdadeira em administracao

**Goal:** Fechar as ultimas incoerencias administrativas entre UI e autorizacao real.
**Requirements**: Esconder acoes owner-only em automacoes para manager e alinhar a linguagem de usuarios para ativacao/desativacao.
**Depends on:** Phase 2
**Plans:** 1 plan

Plans:
- [x] Alinhar automacoes e users com a superficie administrativa verdadeira

## Backlog

### Phase 999.1: Import mapper e reconciliacao manual (BACKLOG)

**Goal:** [Captured for future planning]
**Requirements:** TBD
**Plans:** 0 plans

Plans:
- [ ] TBD (promote with $gsd-review-backlog when ready)

### Phase 999.2: Bulk update dedicado de membros (BACKLOG)

**Goal:** [Captured for future planning]
**Requirements:** TBD
**Plans:** 0 plans

Plans:
- [ ] TBD (promote with $gsd-review-backlog when ready)

### Phase 999.3: Busca operacional por telefone e CPF (BACKLOG)

**Goal:** [Captured for future planning]
**Requirements:** TBD
**Plans:** 0 plans

Plans:
- [ ] TBD (promote with $gsd-review-backlog when ready)

---
