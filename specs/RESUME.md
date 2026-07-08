# RESUME.md — snapshot do projeto

> Lido por todo worker no início. Mantenha curto e atual. O CTO/Integrador atualizam.

## Estado atual (2026-07-08)

- Produto: **Cordex Gym OS MVP v3.0** — rumo ao piloto com a ProGym.
- Branch de trabalho vigente: `pilot-safe/p0-blockers-20260424`.
- `saas-backend/` — FastAPI + SQLAlchemy + Alembic + APScheduler (Supabase Postgres).
- `saas-frontend/` — React 18 + Vite + Tailwind + React Query.
- Módulos entregues: retenção preditiva, automações de inatividade, dashboards (5),
  CRM Kanban, NPS + sentimento (Claude), avaliação física/Perfil 360, relatórios PDF,
  importador CSV, LGPD (export/anonimização/auditoria).
- Specs de produto: `specs/001-*` … `specs/0NN-*` (numeração viva — continue dela).

## Regras invioláveis (resumo — detalhe em EMPRESA.md + PARALLEL-PROTOCOL.md)

- Trabalhe SÓ no território do seu slot. Não toque zona neutra (`app/core`, `app/main.py`,
  `App.tsx`, `requirements.txt`, CI).
- Implemente a DESIGN-SPEC literalmente (nomes/schemas exatos). Sem DESIGN-SPEC → blocked.
- Smoke verde é gate pra `done`. Nunca desligue/pule teste.
- Todo `gym_id` em toda query/entidade/log. LGPD: CPF cifrado, nada pessoal em log/prompt.

## Smoke

Backend: `python -m pytest saas-backend -q` (configurado em `.ai-team.json`).
Slots de frontend: adicionalmente `npm run build` em `saas-frontend/`.
