# Validacao

## Backend
- Autopilot `send_primary_channel` resolve Kommo quando configurada.
- Retencao D3/D7 e financeiro D+1 nao usam `send_whatsapp` direto na policy.
- Regra legada `send_whatsapp` respeita canal principal.
- Falta de rota Kommo gera erro claro e fallback auditavel.
- Cooldown de mensagens automaticas considera WhatsApp e Kommo.

## Frontend
- Settings mostra cobertura por dominio.
- UI nao promete Kommo pronto quando faltam pipeline, etapa, Salesbot ou campo de mensagem.

## Comandos executados

- `python -m compileall saas-backend/app/services/autopilot_action_service.py saas-backend/app/services/automation_engine.py saas-backend/app/services/kommo_settings_service.py saas-backend/app/schemas/settings.py`
- `python -m pytest tests/test_automation_engine.py tests/test_kommo_settings_service.py tests/test_autopilot_services.py`
- `npm.cmd run build`

## Resultado

- Backend compile: aprovado.
- Backend testes focados: 28 passed.
- Frontend build: aprovado.
