# saas-backend

API FastAPI do AI GYM OS.

## Executar

```bash
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

## Worker (scheduler em processo separado)

Para producao, mantenha `ENABLE_SCHEDULER=false` na API e rode o worker dedicado:

```bash
python -m app.worker
```

## Rotas principais

- `/api/v1/auth/*`
- `/api/v1/users/*`
- `/api/v1/members/*`
- `/api/v1/checkins/*`
- `/api/v1/tasks/*`
- `/api/v1/crm/*`
- `/api/v1/nps/*`
- `/api/v1/dashboards/*`
- `/api/v1/goals/*`
- `/api/v1/reports/*`
- `/ws/updates` (WebSocket realtime, autenticado com access token)
- `/api/v1/imports/*`
- `/api/v1/lgpd/*`
- `/api/v1/audit/*`
- `/api/v1/notifications/*`
- `/api/v1/risk-alerts/*`

## Multi-tenant

- Cada academia possui `gym_id` e `gym_slug`.
- Login exige `gym_slug`, `email` e `password`.
- Bootstrap de academia: `POST /api/v1/auth/register` com `gym_name` e `gym_slug`.

## Cache

- Dashboards usam cache por tenant (`gym_id`) com TTL padrao de 5 minutos.
- Com `REDIS_URL` configurado, o cache e distribuido (multi-instancia) com fallback automatico para memoria.
- Insights de IA dos dashboards usam cache de 1 hora com invalidacao inteligente quando os dados mudam.

## Performance de dashboard

- Migration `20260217_0006` cria indices compostos para consultas de membros/check-ins/leads/tasks/NPS.
- Foi adicionada materialized view `mv_monthly_member_kpis` para acelerar MRR/Churn/LTV.
- O scheduler executa refresh da view a cada 30 minutos (`refresh_dashboard_views`).

## OpenAPI

- Swagger: `/docs`
- ReDoc: `/redoc`
- Health liveness: `/health`
- Health readiness: `/health/ready`

## CI/CD Deploy

- Workflow backend Railway: `.github/workflows/deploy-backend-railway.yml`
- Secrets obrigatorios:
  - `RAILWAY_TOKEN`
  - `RAILWAY_PROJECT_ID`
  - `RAILWAY_ENVIRONMENT_ID`
  - `RAILWAY_API_SERVICE_ID`
- Secrets opcionais:
  - `RAILWAY_WORKER_SERVICE_ID` (deploy do worker)
  - `SUPABASE_DATABASE_URL` (executa `alembic upgrade head` antes do deploy)
