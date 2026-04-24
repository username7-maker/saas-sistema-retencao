# Implementation Plan: AI Inbox Operational Simplification

**Feature**: [spec.md](./spec.md)  
**Phase Anchor**: `4.43.1 - simplificacao operacional do AI Inbox`  
**Created**: 2026-04-23  
**Status**: Implemented locally, pending pilot confirmation

## Plan Intent

Transformar a AI Inbox validada na `4.43` em uma fila de execucao de verdade para a linha de frente, reduzindo friccao sem perder aprovacao humana, auditoria e tool layer segura.

## Scope

### In scope

- payload operacional curto para lista e detalhe
- CTA principal unico para itens normais
- confirmacao explicita curta para itens criticos ou degradados
- filtros operacionais `Fazer agora`, `Aguardando resultado` e `Todos`
- detalhes analiticos recolhidos por padrao
- observacao unica opcional para prepare/reject/outcome
- manutencao do filtro `Meu turno / Todos os turnos`

### Out of scope

- nova inbox por dominio
- nova inbox por cargo
- execucao autonoma
- novo motor de recomendacao
- remocao de explainability ou metricas do produto

## Delivery Slices

### Slice 1 - Contrato operacional

- estender lista e detalhe com:
  - `operator_summary`
  - `primary_action_type`
  - `primary_action_label`
  - `requires_explicit_approval`
  - `show_outcome_step`
- permitir `auto_approve`, `confirm_approval` e `operator_note` em `actions/prepare`

### Slice 2 - Redesign operador-first

- simplificar a lista
- reorganizar o inspector em:
  - `Fazer agora`
  - `Mensagem pronta` / `Resumo da acao`
  - `CTA principal`
  - `Detalhes analiticos`

### Slice 3 - Validacao

- regressao backend e frontend
- `npm run build`
- `specify check`
- piloto para feedback da equipe executora

## Validation Plan

- `pytest -q saas-backend/tests/test_ai_triage_service.py saas-backend/tests/test_ai_triage_router.py`
- `npm run test -- --run src/test/AITriageInboxPage.test.tsx`
- `npm run build`
- `specify check`

## Exit Condition

O slice pode ser considerado implementado quando:

- item normal prepara acao em um clique com aprovacao implicita
- item critico exige confirmacao explicita
- a lista fica curta e operacional
- os detalhes analiticos ficam recolhidos por padrao
- a trilha auditavel continua integra
