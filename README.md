# AI GYM OS - MVP v3.0

Plataforma SaaS B2B para academias (800 a 1.500 alunos) com BI, CRM, retenção preditiva, NPS e compliance LGPD.

## Arquitetura

- Backend: FastAPI + SQLAlchemy 2.0 + PostgreSQL (Supabase) + Alembic + APScheduler.
- Frontend: React 18 + TypeScript + Vite + Tailwind + React Query + Recharts.
- Segurança: JWT access (15 min) + refresh (7 dias), RBAC, bcrypt (12 rounds), AES-256 para CPF, auditoria LGPD.

## Estrutura

- `saas-backend/app/routers`: endpoints REST
- `saas-backend/app/services`: regras de negócio
- `saas-backend/app/models`: entidades e relacionamentos
- `saas-backend/app/schemas`: contratos Pydantic
- `saas-backend/app/core`: config, auth, dependencies, cache
- `saas-backend/app/utils`: integrações e criptografia
- `saas-backend/app/background_jobs`: jobs APScheduler
- `saas-frontend/src/pages`: telas por domínio
- `saas-frontend/src/components`: UI e gráficos
- `saas-frontend/src/hooks`: data hooks React Query
- `saas-frontend/src/services`: camada API
- `saas-frontend/src/contexts`: auth state
- `saas-frontend/src/layouts`: layout principal

## Backend - Setup

1. Criar e ativar ambiente virtual Python 3.11+.
2. Instalar dependências:

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

1. Crie serviço Python.
2. Defina variáveis de ambiente do backend.
3. Build command: `pip install -r requirements.txt`.
4. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.

### Vercel (Frontend)

1. Importar `saas-frontend`.
2. Build command: `npm run build`.
3. Output: `dist`.
4. Env: `VITE_API_BASE_URL=https://seu-backend.railway.app`.

## Variáveis de ambiente principais

Backend:

- `DATABASE_URL`
- `JWT_SECRET_KEY`
- `ACCESS_TOKEN_EXPIRE_MINUTES=15`
- `REFRESH_TOKEN_EXPIRE_DAYS=7`
- `BCRYPT_ROUNDS=12`
- `CPF_ENCRYPTION_KEY` (AES-256)
- `SENDGRID_API_KEY`
- `SENDGRID_SENDER`
- `CLAUDE_API_KEY`
- `CLAUDE_MODEL`
- `CORS_ORIGINS`

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

## Módulos entregues

- Retenção preditiva determinística (score 0-100).
- Automações de inatividade (3/7/10/14/21 dias).
- Dashboards: Executivo, Operacional, Comercial, Financeiro, Retenção.
- CRM com pipeline Kanban e automação de follow-up.
- NPS com gatilhos + análise de sentimento Claude.
- Importador CSV (membros e check-ins) com validação e log de erros.
- Exportação LGPD em PDF + anonimização de membro.
- Auditoria de ações sensíveis.
