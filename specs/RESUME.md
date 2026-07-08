# RESUME.md — snapshot do projeto

> Lido por todo worker no início. Mantenha curto e atual. O CTO/Integrador atualizam.

## Estado atual (2026-07-08, pós-M1)

- Produto: **Cordex Gym OS MVP v3.0** — **EM PRODUÇÃO na ProGym** (cliente fundadora usa
  no dia a dia). Toda mudança é mudança em produto vivo: regressão dói em operação real.
- Branch de trabalho vigente: `pilot-safe/p0-blockers-20260424` (= `baseBranch` do
  `.ai-team.json`; ADR 001 — NUNCA trabalhar na main: push nela dispara deploy).
- **M1 "Cockpit Comercial Diário" entregue (HTC aprovado 2026-07-08):** bloco "Hoje" no
  Dashboard Executivo + `GET /api/v1/cockpit/daily` + `GET /api/v1/cockpit/weekly-funnel`
  (spec 053). Ainda NÃO publicado em produção (aguarda decisão de deploy do fundador).
- `saas-backend/` — FastAPI + SQLAlchemy + Alembic + APScheduler (Supabase Postgres).
- `saas-frontend/` — React 18 + Vite + Tailwind + React Query.
- Módulos entregues: cockpit diário, retenção preditiva, automações, dashboards (5),
  CRM Kanban + Growth OS, Central Cordex, NPS + sentimento (Claude), avaliação
  física/Perfil 360, relatórios PDF, importador CSV, LGPD.
- Specs de produto: `specs/001-*` … `specs/053-*` (numeração viva — continue de 054).
- Visão geral: `docs/SOLUTION-OVERVIEW.md`. Milestones: `docs/ROADMAP.md`.
  Aprendizados: `docs/LEARNINGS.md`.

## Regras invioláveis (resumo — detalhe em EMPRESA.md + PARALLEL-PROTOCOL.md)

- Trabalhe SÓ no território do seu slot. Não toque zona neutra (`app/core`, `app/main.py`,
  `App.tsx`, `requirements.txt`, CI).
- Implemente a DESIGN-SPEC literalmente (nomes/schemas exatos). Sem DESIGN-SPEC → blocked.
- Smoke verde é gate pra `done`. Nunca desligue/pule teste.
- Todo `gym_id` em toda query/entidade/log. LGPD: CPF cifrado, nada pessoal em log/prompt.

## Smoke

Backend: `py -3.12 -m pytest saas-backend -q` (configurado em `.ai-team.json` — o
`python` do PATH desta máquina NÃO tem as deps; ver docs/LEARNINGS.md).
Slots de frontend: adicionalmente `npm run build` em `saas-frontend/`.
