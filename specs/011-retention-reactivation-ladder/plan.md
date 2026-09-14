# Implementation Plan: Retention Reactivation Ladder

## Backend

- Criar `retention_stage_service`.
- Estender schemas de dashboard e Work Queue.
- Atualizar `get_retention_queue` com filtro e contadores.
- Atualizar `build_retention_playbook`.
- Atualizar `run_daily_retention_intelligence`.
- Persistir a resolucao por combinacao de ausencia e estagio, reabrindo apenas na proxima faixa.
- Reparar alertas reabertos no mesmo estagio sem remover o historico de resolucao.
- Atualizar AI Inbox e Work Queue para tratamento de `reactivation`, `manager_escalation` e `cold_base`.

## Frontend

- Adicionar filtro de estagio no Dashboard de Retencao.
- Adicionar lanes clicaveis.
- Mostrar badge de estagio em linha e drawer.
- Ajustar texto do drawer por estagio.
- Mostrar estagio na Work Queue.

## Tests

- Testes unitarios de calculo de estagio.
- Testes de contrato da fila.
- Testes focados de Work Queue.
- Build frontend.
- Testes de permanencia no estagio, transicao de faixa e normalizacao do ultimo acesso.
