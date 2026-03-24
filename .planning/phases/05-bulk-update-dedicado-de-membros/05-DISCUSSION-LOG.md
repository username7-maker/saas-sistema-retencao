# Phase 5: Bulk update dedicado de membros - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md.

**Date:** 2026-03-24
**Phase:** 05-bulk-update-dedicado-de-membros
**Areas discussed:** superficie do fluxo, chave de match, escopo de campos, seguranca do commit

---

## Surface

| Option | Description | Selected |
|--------|-------------|----------|
| Reusar ImportsPage | Mantem a mesma tela, mas mistura onboarding e manutencao de base | |
| Sub-rota do modulo de membros | Mantem contexto do diretorio e da manutencao coletiva | ✓ |
| Drawer compacto | Menor mudanca visual, mas pouco espaco para diff operacional | |

**User's choice:** auto-selected recommended default
**Notes:** bulk update deve ser separado da importacao inicial e nascer no modulo de membros.

---

## Matching

| Option | Description | Selected |
|--------|-------------|----------|
| Nome/email/matricula | Mais flexivel, mas nome torna o fluxo fragil | |
| `member_id`, `external_id`, `email` | Match estrito com chaves operacionais existentes | ✓ |
| Nome apenas | Risco operacional alto | |

**User's choice:** auto-selected recommended default
**Notes:** nome fica fora como chave de bulk update.

---

## Field Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Todos os campos de membro | Mais completo, mas abre risco em dados sensiveis | |
| Campos operacionais seguros | Nome, email, telefone, plano, mensalidade, status, matricula, turno e data de inicio | ✓ |
| Apenas status/plano | Seguro, mas estreito demais para o objetivo da fase | |

**User's choice:** auto-selected recommended default
**Notes:** CPF e campos tecnicos ficam fora desta fase.

---

## Commit Safety

| Option | Description | Selected |
|--------|-------------|----------|
| Commit parcial | Atualiza linhas validas e ignora o resto | |
| Commit bloqueado com qualquer linha invalida | Mais seguro para manutencao coletiva | ✓ |
| Aplicacao manual linha a linha | Seguro, mas vira operacao lenta | |

**User's choice:** auto-selected recommended default
**Notes:** esta fase prioriza seguranca operacional acima de throughput.

---

## the agent's Discretion

- Escolha exata da composicao visual do diff
- Nome final da sub-rota/endpoints de bulk update

## Deferred Ideas

- Aplicacao parcial
- Edicao inline do preview
- Templates persistentes
