# Context - 04.43.9 Task Autopilot / Auto Resolution Engine

## Problema

Tasks e Work Queue ja organizam a execucao humana, mas ainda criam trabalho demais para a equipe. Eventos simples como check-in apos ausencia, pagamento confirmado, resposta no WhatsApp ou lead ganho/perdido deveriam fechar ou reclassificar tasks sem depender de operador.

## Decisao de corte

Adicionar uma camada segura antes da Work Queue:

- `AutopilotEvent`: log interno/event bus tenant-scoped.
- `AutopilotAction`: acao planejada/executada pelo Autopilot, sem conflitar com `AutomationAction` legado.
- `GymAutopilotSettings`: feature flags e limites por academia.
- `TaskEvent`: continua sendo timeline operacional visivel.
- Work Queue continua sendo entrada humana principal.

## Guardrails

- Auto-send inicia desligado.
- Auto-close pode operar antes do envio automatico.
- Leads nao recebem auto-send na V1.
- Casos sensiveis sempre escalam.
- Nenhuma acao cruza tenant.
- `AutomationJourney` existente deve ser integrada, nao recriada.
