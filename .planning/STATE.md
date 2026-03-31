---
milestone: v3.2.0
phase: 4.42.1
plan: "04.42.1-STATUS.md"
status: A ponte local do Actuar evoluiu para relay local + extensao de navegador, reduzindo o atrito operacional para usar a aba real do operador sem depender de flags manuais de debugging
last_activity: 2026-03-31 - 4.42.1 abriu a trilha de extensao/relay para simplificar a operacao da ponte local do Actuar
---

# STATE

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-24)

**Core value:** A equipe da academia precisa confiar que cada tela mostra o estado real do aluno e so oferece acoes que de fato fecham operacionalmente.
**Current focus:** Fechar hardening e coerencia operacional antes de liberar o piloto controlado.

## Current Position

**Phase:** 4.42.1
**Plan:** `04.42.1-STATUS.md`
**Status:** Piloto controlado segue ativo, agora com a evolucao da ponte local para relay + extensao de navegador, buscando uma instalacao mais simples no computador da academia
**Last activity:** 2026-03-31 - a fase 4.42.1 abriu o caminho de relay local HTTP e extensao Chrome/Edge para anexar explicitamente a aba do Actuar

## Progress Snapshot

**Active milestone:** v3.2.0
**Phases planned:** 16
**Plans planned:** 12
**Plans completed:** 3

## Accumulated Context

### Latest Milestone Outcome

- `v3.1.0` melhorou CRM, busca operacional inicial e superficies administrativas
- Phase 4 concluiu import mapper com reconciliacao manual e preview seguro
- Phase 4.1 fechou birthday importado, recalc duravel de risco, websocket distribuido e suites verdes
- Phase 4.2 alinhou RBAC com backend, criou task-lite do trainer e completou CI do frontend
- Phase 4.32 colocou WhatsApp real no piloto e validou a trilha premium/OpenAI da bioimpedancia

### Current Milestone Scope

- Phase 4: import mapper e reconciliacao manual - concluida
- Phase 4.1: hardening P0 - concluida
- Phase 4.2: coerencia operacional P1 - concluida
- Phase 4.3: piloto controlado - em execucao
- Phase 4.31: bioimpedancia assistida e Actuar readiness - publicada no piloto
- Phase 4.32: canais reais do piloto - publicada no piloto, com pendencia apenas de credenciais reais do Actuar automatico
- Phase 4.33: transparencia de IA e fluxos publicos - aguardando 4.32
- Phase 4.34: superficies administrativas e relatorios do piloto - em execucao
- Phase 4.36: higiene de tokens e lockdown de superficies publicas - concluindo validacao inicial
- Phase 4.37: protecao de PII e seguranca de import/export - primeira fatia concluida, com endurecimento estrutural ainda pendente
- Phase 4.38: resiliencia de consultas, jobs e DoS logico - em execucao
- Phase 4.39: guardrails de tenant e consistencia transacional - em execucao
- Phase 4.40: hardening de sessao e borda de producao - em execucao
- Phase 4.41: handoff seguro para Kommo - em execucao
- Phase 4.42: Actuar Bridge local - infraestrutura implementada e validada em testes; falta validacao ao vivo
- Phase 4.42.1: Actuar Bridge extension relay - em execucao
- Phase 5: bulk update dedicado de membros - pausada ate saida do piloto e fechamento das fases urgentes 4.36-4.40
- Phase 6: busca operacional por telefone/CPF - pausada ate saida do piloto e fase 5

### Security Hardening Backlog Now Converted To Phases

- Phase 4.36: higiene de tokens e lockdown de superficies publicas - P0
- Phase 4.37: protecao de PII e seguranca de import/export - P0
- Phase 4.38: resiliencia de consultas, jobs e DoS logico - P1
- Phase 4.39: guardrails de tenant e consistencia transacional - P1
- Phase 4.40: hardening de sessao e borda de producao - P2

These phases now gate any feature expansion beyond the pilot.
