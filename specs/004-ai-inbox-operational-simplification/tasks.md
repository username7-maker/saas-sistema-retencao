# Tasks: AI Inbox Operational Simplification

**Feature**: [spec.md](./spec.md)  
**Plan**: [plan.md](./plan.md)  
**Phase Anchor**: `4.43.1 - simplificacao operacional do AI Inbox`  
**Status**: Implemented locally

## Execution

### Wave 1 - Backend contract

- [x] T001 Estender o payload da inbox com `operator_summary`, `primary_action_type`, `primary_action_label`, `requires_explicit_approval` e `show_outcome_step`.
- [x] T002 Ajustar `actions/prepare` para suportar `auto_approve`, `confirm_approval` e `operator_note`.
- [x] T003 Manter a trilha auditavel de aprovacao, preparacao e outcome sem abrir execucao autonoma.

### Wave 2 - Frontend operator-first

- [x] T004 Simplificar a lista para exibir apenas informacao operacional curta.
- [x] T005 Reorganizar o inspector em `Fazer agora`, `Mensagem pronta` / `Resumo da acao`, `CTA principal` e `Detalhes analiticos`.
- [x] T006 Esconder metricas e explainability profunda atras de superficies recolhidas.
- [x] T007 Introduzir filtros `Fazer agora`, `Aguardando resultado` e `Todos`, preservando `Meu turno / Todos os turnos`.

### Wave 3 - Validation

- [x] T008 Cobrir item normal com aprovacao implicita em testes.
- [x] T009 Cobrir item critico com confirmacao explicita em testes.
- [x] T010 Validar build e contratos focados sem regressao.

## Notes

- Este slice nao reabre a `4.43`; ele a endurece para execucao pela linha de frente.
- A inbox continua assistiva, auditavel e supervisionada.
