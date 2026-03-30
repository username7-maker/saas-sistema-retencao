# Deploy Pilot Checklist

Stack alvo deste checklist:

- frontend na Vercel
- API + worker + Redis no Railway
- Postgres no Supabase

Escopo do piloto:

- core do sistema
- e-mail
- WhatsApp

Ficam desligados no go-live inicial:

- Claude
- leitura assistida de bioimpedancia
- Actuar

## Artefatos De Execucao

- runbook do piloto: [deploy/CONTROLLED_PILOT_RUNBOOK.md](./deploy/CONTROLLED_PILOT_RUNBOOK.md)
- checklist diario: [deploy/CONTROLLED_PILOT_DAILY_CHECKLIST.md](./deploy/CONTROLLED_PILOT_DAILY_CHECKLIST.md)
- template de incidente: [deploy/CONTROLLED_PILOT_INCIDENT_TEMPLATE.md](./deploy/CONTROLLED_PILOT_INCIDENT_TEMPLATE.md)

## Env Vars Obrigatorias

- `DATABASE_URL`
- `REDIS_URL`
- `JWT_SECRET_KEY`
- `CPF_ENCRYPTION_KEY`
- `CORS_ORIGINS`
- `FRONTEND_URL`
- `PUBLIC_BACKEND_URL`
- `ENABLE_SCHEDULER`
- `ENABLE_SCHEDULER_IN_API`
- `SCHEDULER_CRITICAL_LOCK_FAIL_OPEN=false`
- `WHATSAPP_WEBHOOK_TOKEN`
- `SENDGRID_API_KEY` e `SENDGRID_SENDER` se o piloto usar e-mail
  - `SENDGRID_SENDER` precisa ser um `Sender Identity` verificado no SendGrid, senao o worker vai responder `403 Forbidden`
- `WHATSAPP_API_URL`, `WHATSAPP_API_TOKEN` e `WHATSAPP_INSTANCE` se o piloto usar WhatsApp
- `PUBLIC_BOOKING_CONFIRM_TOKEN` apenas se `PUBLIC_BOOKING_CONFIRM_ENABLED=true`

## Flags do Piloto

- API: `ENABLE_SCHEDULER=false`
- API: `ENABLE_SCHEDULER_IN_API=false`
- Worker: `ENABLE_SCHEDULER=true`
- Worker: `ENABLE_SCHEDULER_IN_API=false`
- Worker: `SCHEDULER_CRITICAL_LOCK_FAIL_OPEN=false`
- Manter desligado:
  - `PUBLIC_DIAGNOSIS_ENABLED=false`
  - `PUBLIC_BOOKING_CONFIRM_ENABLED=false`
  - `PUBLIC_OBJECTION_RESPONSE_ENABLED=false`
  - `PUBLIC_PROPOSAL_ENABLED=false`
  - `PUBLIC_PROPOSAL_EMAIL_ENABLED=false`
  - `MONTHLY_REPORTS_DISPATCH_ENABLED=false`
  - `ACTUAR_ENABLED=false`
  - `ACTUAR_SYNC_ENABLED=false`
  - `ACTUAR_SYNC_MODE=disabled`
  - `ACTUAR_IGNORE_HTTPS_ERRORS=false`
  - `BODY_COMPOSITION_IMAGE_AI_ENABLED=false`

## Comandos Corretos

- API: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Worker: `python -m app.worker`

## Provisionamento

1. Criar banco no Supabase
2. Criar projeto Railway com:
   - `api`
   - `worker`
   - `redis`
3. Criar frontend na Vercel
4. Rodar migration no banco antes de liberar o frontend

## Validacoes Pos-Deploy

- `GET /health/ready` responde `200`
- `GET /health/ready` em producao responde apenas `{ "status": "ok" }`
- Login funciona e refresh token continua valido para usuario ativo
- Criacao de member gera membro, tarefas de onboarding e audit log
- Importacao pequena de membros funciona com preview e commit
- Retencao, Tasks, Avaliacoes e Profile 360 carregam sem erro
- WebSocket em `/ws/updates` conecta com access token valido
- Logs do worker mostram jobs iniciando normalmente
- Logs do worker nao mostram `job_skipped_lock_unavailable`
- Rotas publicas bloqueadas retornam `503`:
  - `/api/v1/public/diagnostico`
  - `/api/v1/public/booking/confirm`
  - `/api/v1/public/proposal`
  - `/api/v1/public/objection-response`
- E-mail real via SendGrid funciona
- Um fluxo real de WhatsApp funciona

## Sanity Checks de Operacao

- API nao sobe scheduler
- Worker dedicado sobe scheduler
- Redis esta acessivel antes de liberar o worker
- Logs estruturados aparecem com `job_started`, `job_completed` e `lock_acquired`
- Nao existem erros repetidos de `websocket_broadcast_unavailable`

## Rollback Basico

- Desligar o worker se houver incidente de jobs
- Reverter para o release anterior no Railway
- Reverter o frontend na Vercel
- Manter `PUBLIC_OBJECTION_RESPONSE_ENABLED=false`
- Manter `PUBLIC_PROPOSAL_ENABLED=false`
- Revalidar `GET /health/ready` e login apos rollback
