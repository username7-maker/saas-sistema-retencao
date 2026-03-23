# Deploy Pilot Checklist

## Env Vars Obrigatorias

- `DATABASE_URL`
- `JWT_SECRET_KEY`
- `CPF_ENCRYPTION_KEY`
- `CORS_ORIGINS`
- `FRONTEND_URL`
- `REDIS_URL`
- `ENABLE_SCHEDULER`
- `ENABLE_SCHEDULER_IN_API`
- `SCHEDULER_CRITICAL_LOCK_FAIL_OPEN=false`
- `PUBLIC_DIAG_GYM_ID`
- `WHATSAPP_WEBHOOK_TOKEN`
- `SENDGRID_API_KEY` e `SENDGRID_SENDER` se o piloto usar e-mail
- `WHATSAPP_API_URL`, `WHATSAPP_API_TOKEN` e `WHATSAPP_INSTANCE` se o piloto usar WhatsApp

## Flags do Piloto

- API: `ENABLE_SCHEDULER=false`
- API: `ENABLE_SCHEDULER_IN_API=false`
- Worker: `ENABLE_SCHEDULER=true`
- Worker: `SCHEDULER_CRITICAL_LOCK_FAIL_OPEN=false`
- Manter desligado:
  - `PUBLIC_OBJECTION_RESPONSE_ENABLED=false`
  - `PUBLIC_PROPOSAL_ENABLED=false`

## Comandos Corretos

- API: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Worker: `python -m app.worker`

## Validacoes Pos-Deploy

- `GET /health/ready` responde `200`
- Login funciona e refresh token continua valido para usuario ativo
- Criacao de member gera membro, tarefas de onboarding e audit log
- `POST /api/v1/public/booking/confirm` confirma booking sem erro
- WebSocket em `/ws/updates` conecta com access token valido
- Logs do worker mostram jobs iniciando normalmente
- Logs do worker nao mostram `job_skipped_lock_unavailable`

## Sanity Checks de Operacao

- API nao sobe scheduler
- Worker dedicado sobe scheduler
- Redis esta acessivel antes de liberar o worker
- Logs estruturados aparecem com `job_started`, `job_completed` e `lock_acquired`
- Nao existem erros repetidos de `websocket_broadcast_unavailable`

## Rollback Basico

- Desligar o worker se houver incidente de jobs
- Reverter para o release anterior no Railway
- Manter `PUBLIC_OBJECTION_RESPONSE_ENABLED=false`
- Manter `PUBLIC_PROPOSAL_ENABLED=false`
- Revalidar `GET /health/ready` e login apos rollback
