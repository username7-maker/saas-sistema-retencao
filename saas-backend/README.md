# saas-backend

API FastAPI do AI GYM OS.

## Executar

```bash
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
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
- `/api/v1/imports/*`
- `/api/v1/lgpd/*`
- `/api/v1/audit/*`

## OpenAPI

- Swagger: `/docs`
- ReDoc: `/redoc`
