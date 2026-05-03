# Plan - 04.43.9 Task Autopilot / Auto Resolution Engine

## Objetivo

Reduzir tasks humanas com auto-fechamento, safety checks, envio manual monitorado e escalonamento auditavel.

## Entregas

1. Criar modelos e migration para `autopilot_events`, `autopilot_actions` e `gym_autopilot_settings`.
2. Criar servicos de evento, action, safety, policy, resolver e escalonamento humano.
3. Integrar eventos reais de WhatsApp inbound, check-in, financeiro pago e CRM.
4. Criar jobs para eventos pendentes, actions agendadas e timeouts.
5. Criar APIs `/api/v1/autopilot/*` e `/api/v1/settings/autopilot`.
6. Adicionar `send-and-wait` na Work Queue para envio humano monitorado pelo Autopilot.
7. Atualizar UI com badges, botao de envio monitorado e aba de configuracao Autopilot.
8. Documentar rollout seguro em `docs/autopilot.md`.

## Validacao

- Compile backend.
- Build frontend.
- Spec Kit health check.
- Testar manualmente: check-in fecha retencao, pagamento fecha financeiro, WhatsApp inbound resolve ou escala, send-and-wait cria action aguardando outcome.
