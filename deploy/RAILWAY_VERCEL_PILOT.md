# Deploy de Piloto — Railway + Vercel

Este guia materializa o caminho recomendado para colocar o piloto no ar com:

- Frontend na Vercel
- API + Worker + Redis no Railway
- PostgreSQL no Supabase

Escopo deste piloto:

- core do sistema
- e-mail
- WhatsApp

Ficam desligados no go-live inicial:

- Claude
- leitura assistida de bioimpedancia
- Actuar

## 1. Provisionar a stack

### Supabase

1. Crie um projeto no Supabase.
2. Copie a string de conexao Postgres.
3. Ajuste para o formato SQLAlchemy:

```text
postgresql+psycopg2://USER:PASSWORD@HOST:PORT/DBNAME
```

### Railway

Crie um projeto com 3 servicos:

- `api`
- `worker`
- `redis`

Para `api` e `worker`, use o mesmo repositorio com root em `saas-backend`.

Start commands:

- API: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Worker: `python -m app.worker`

### Vercel

Crie um projeto apontando para `saas-frontend`.

- Build command: `npm run build`
- Output directory: `dist`

## 2. Configurar variaveis

Use os templates:

- API Railway: [railway-api.env.example](./railway-api.env.example)
- Worker Railway: [railway-worker.env.example](./railway-worker.env.example)
- Frontend Vercel: [vercel.env.example](./vercel.env.example)

Minimos obrigatorios:

- `DATABASE_URL`
- `REDIS_URL`
- `JWT_SECRET_KEY`
- `CPF_ENCRYPTION_KEY`
- `FRONTEND_URL`
- `CORS_ORIGINS`
- `PUBLIC_BACKEND_URL`

Pilot flags obrigatorias:

- API:
  - `ENABLE_SCHEDULER=false`
  - `ENABLE_SCHEDULER_IN_API=false`
- Worker:
  - `ENABLE_SCHEDULER=true`
  - `ENABLE_SCHEDULER_IN_API=false`
- Ambos:
  - `SCHEDULER_CRITICAL_LOCK_FAIL_OPEN=false`
  - `PUBLIC_OBJECTION_RESPONSE_ENABLED=false`
  - `PUBLIC_PROPOSAL_ENABLED=false`
  - `ACTUAR_ENABLED=false`
  - `ACTUAR_SYNC_ENABLED=false`
  - `ACTUAR_SYNC_MODE=disabled`
  - `BODY_COMPOSITION_IMAGE_AI_ENABLED=false`

Integracoes ligadas neste piloto:

- `SENDGRID_API_KEY`
- `SENDGRID_SENDER`
- `WHATSAPP_API_URL`
- `WHATSAPP_API_TOKEN`
- `WHATSAPP_INSTANCE`
- `WHATSAPP_WEBHOOK_TOKEN`

## 3. Rodar migrations

Antes de abrir o frontend, rode:

```bash
cd saas-backend
set DATABASE_URL=postgresql+psycopg2://USER:PASSWORD@HOST:PORT/DBNAME
alembic upgrade head
```

Confirme que o banco ficou em `head`.

## 4. Deploy manual do primeiro piloto

### Backend e worker no Railway

1. Preencha as env vars da API.
2. Faça o primeiro deploy da API.
3. Preencha as env vars do worker.
4. Faça o primeiro deploy do worker.
5. Confirme que:
   - a API sobe com `/health/ready = 200`
   - o worker sobe e inicia jobs
   - a API nao esta rodando scheduler

### Frontend na Vercel

1. Configure `VITE_API_BASE_URL=https://<backend>.up.railway.app`
2. Deixe `VITE_WS_BASE_URL` vazio no primeiro deploy
3. Faça o deploy
4. Atualize na API:
   - `FRONTEND_URL=https://<frontend>.vercel.app`
   - `CORS_ORIGINS=["https://<frontend>.vercel.app"]`

## 5. Criar a academia piloto

Use `POST /api/v1/auth/register` para criar o owner inicial com:

- `full_name`
- `email`
- `password`
- `gym_name`
- `gym_slug`

Depois valide login com:

- `gym_slug`
- `email`
- `password`

## 6. Smoke test obrigatorio

Antes de liberar a equipe:

1. `GET /health/ready` responde `200`
2. login e refresh token funcionam
3. criar 1 membro manualmente funciona
4. importar uma planilha pequena funciona
5. `Retencao`, `Tasks`, `Avaliacoes` e `Profile 360` abrem sem erro
6. worker loga jobs sem `job_skipped_lock_unavailable`
7. email real funciona via SendGrid
8. um fluxo real de WhatsApp funciona
9. websocket em `/ws/updates` conecta com token valido

## 7. Rollback basico

Se houver incidente no piloto:

1. desligue primeiro o worker
2. reverta o backend no Railway
3. reverta o frontend na Vercel
4. revalide:
   - `/health/ready`
   - login
   - importacao
   - fila de retencao

## 8. GitHub Actions

So habilite automacao de deploy depois do primeiro deploy manual bem-sucedido.

Workflows existentes:

- Backend Railway: [deploy-backend-railway.yml](../.github/workflows/deploy-backend-railway.yml)
- Frontend Vercel: [deploy-frontend-vercel.yml](../.github/workflows/deploy-frontend-vercel.yml)

Secrets necessarios:

### Backend

- `RAILWAY_TOKEN`
- `RAILWAY_PROJECT_ID`
- `RAILWAY_ENVIRONMENT_ID`
- `RAILWAY_API_SERVICE_ID`
- `RAILWAY_WORKER_SERVICE_ID`
- `SUPABASE_DATABASE_URL`

### Frontend

- `VERCEL_TOKEN`
- `VERCEL_ORG_ID`
- `VERCEL_PROJECT_ID`

## 9. Defaults deste piloto

- banco no Supabase
- Redis no Railway
- frontend na Vercel
- API e worker em servicos separados no Railway
- deploy inicial manual
- sem Claude no go-live
- sem Actuar no go-live
- sem leitura assistida de bioimpedancia no go-live
