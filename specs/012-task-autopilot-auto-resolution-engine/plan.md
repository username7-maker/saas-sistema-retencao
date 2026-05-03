# Plan 012 - Task Autopilot

## Backend

- Models: `AutopilotEvent`, `AutopilotAction`, `GymAutopilotSettings`.
- Services:
  - `autopilot_event_service`
  - `autopilot_action_service`
  - `autopilot_safety_service`
  - `autopilot_policy_service`
  - `autopilot_resolver_service`
  - `human_escalation_service`
- Routers:
  - `/api/v1/autopilot/events`
  - `/api/v1/autopilot/actions`
  - `/api/v1/autopilot/metrics`
  - `/api/v1/autopilot/timeline`
  - `/api/v1/settings/autopilot`
- Integrations:
  - WhatsApp inbound
  - check-in
  - finance paid
  - CRM stage finalization

## Frontend

- Work Queue:
  - badges Autopilot
  - CTA `Enviar e aguardar`
- Settings:
  - Aba `Autopilot`
  - flags, horario, limites e metricas simples

## Rollout

1. `autopilot_enabled=true`, `auto_close=true`, `auto_send=false`.
2. Validar auto-close por evento.
3. Liberar `send-and-wait` humano.
4. Só depois avaliar auto-send limitado.
