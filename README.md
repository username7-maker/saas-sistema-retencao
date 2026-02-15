# AI GYM OS - MVP v3.0

Plataforma SaaS B2B para academias (800 a 1.500 alunos) com BI, CRM, retencao preditiva, NPS e compliance LGPD.

## Arquitetura

- Backend: FastAPI + SQLAlchemy 2.0 + PostgreSQL (Supabase) + Alembic + APScheduler.
- Frontend: React 18 + TypeScript + Vite + Tailwind + React Query + Recharts.
- Seguranca: JWT access (15 min) + refresh (7 dias), RBAC, bcrypt (12 rounds), AES-256 para CPF, auditoria LGPD.

## Estrutura

- `saas-backend/app/routers`: endpoints REST
- `saas-backend/app/services`: regras de negocio
- `saas-backend/app/models`: entidades e relacionamentos
- `saas-backend/app/schemas`: contratos Pydantic
- `saas-backend/app/core`: config, auth, dependencies, cache
- `saas-backend/app/utils`: integracoes e criptografia
- `saas-backend/app/background_jobs`: jobs APScheduler
- `saas-frontend/src/pages`: telas por dominio
- `saas-frontend/src/components`: UI e graficos
- `saas-frontend/src/hooks`: data hooks React Query
- `saas-frontend/src/services`: camada API
- `saas-frontend/src/contexts`: auth state
- `saas-frontend/src/layouts`: layout principal

## Backend - Setup

1. Criar e ativar ambiente virtual Python 3.11+.
2. Instalar dependencias:

```bash
cd saas-backend
pip install -r requirements.txt
```

3. Configurar `.env` usando `.env.example`.
4. Aplicar migration:

```bash
alembic upgrade head
```

5. Rodar API:

```bash
uvicorn app.main:app --reload
```

6. Opcional (scheduler em processo dedicado):

```bash
python -m app.worker
```

Swagger/OpenAPI: `http://127.0.0.1:8000/docs`

## Frontend - Setup

```bash
cd saas-frontend
npm install
npm run dev
```

Defina `VITE_API_BASE_URL` apontando para o backend.

## Deploy

### Supabase (PostgreSQL)

1. Crie projeto no Supabase.
2. Copie connection string PostgreSQL para `DATABASE_URL`.
3. Rode `alembic upgrade head` com essa URL.

### Railway (Backend)

1. Crie servico Python.
2. Defina variaveis de ambiente do backend.
3. Build command: `pip install -r requirements.txt`.
4. Start command (API): `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
5. Crie um segundo servico worker com start command: `python -m app.worker`.
6. No servico da API use `ENABLE_SCHEDULER=false` para evitar job duplicado em multiplas replicas.

### Vercel (Frontend)

1. Importar `saas-frontend`.
2. Build command: `npm run build`.
3. Output: `dist`.
4. Env: `VITE_API_BASE_URL=https://seu-backend.railway.app`.

## Variaveis de ambiente principais

Backend:

- `DATABASE_URL`
- `ENABLE_SCHEDULER`
- `JWT_SECRET_KEY`
- `ACCESS_TOKEN_EXPIRE_MINUTES=15`
- `REFRESH_TOKEN_EXPIRE_DAYS=7`
- `BCRYPT_ROUNDS=12`
- `CPF_ENCRYPTION_KEY` (AES-256)
- `SENDGRID_API_KEY`
- `SENDGRID_SENDER`
- `CLAUDE_API_KEY`
- `CLAUDE_MODEL`
- `CORS_ORIGINS` (formato JSON, ex: `["https://app.exemplo.com"]`)

Frontend:

- `VITE_API_BASE_URL`

## Testes

Backend:

```bash
cd saas-backend
pytest
```

Frontend E2E:

```bash
cd saas-frontend
npm run test:e2e
```

## Modulos entregues

- Retencao preditiva deterministica (score 0-100).
- Automacoes de inatividade (3/7/10/14/21 dias).
- Notificacoes in-app de retencao + resolucao de risk alerts com historico de acoes.
- Dashboards: Executivo, Operacional, Comercial, Financeiro, Retencao.
- CRM com pipeline Kanban e automacao de follow-up.
- NPS com gatilhos + analise de sentimento Claude.
- Importador CSV (membros e check-ins) com validacao e log de erros.
- Exportacao LGPD em PDF + anonimizacao de membro.
- Auditoria de acoes sensiveis.
