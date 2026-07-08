# SOLUTION-OVERVIEW — Cordex Gym OS

> Visão viva da solução. Atualizada a cada milestone fechado (última: M1, 2026-07-08).
> Detalhe por feature: `specs/001-*` … `specs/053-*`. Invariantes: `EMPRESA.md`.

## O que é

**Cordex Gym OS** — SaaS B2B AI-first da Cordex: camada operacional e de receita pra
academias (800–1.500 alunos). **Em produção na ProGym** (cliente fundadora). Transforma
dados soltos em ações com dono, prazo e resultado medido.

## Arquitetura real

- **Backend** `saas-backend/`: Python 3.11+ / FastAPI / SQLAlchemy 2.0 / Alembic /
  APScheduler (worker separado). Postgres no Supabase, Redis (Railway). Padrões:
  routers finos → services com `gym_id` explícito; Pydantic em toda fronteira;
  tenant-guard de sessão (spec 001) como 2ª camada; CPF cifrado AES-256; auditoria.
- **Frontend** `saas-frontend/`: React 18 + TS estrito + Vite + Tailwind + React Query.
  Design system Cordex "Dark Intelligence" (`docs/design/DESIGN-OVERVIEW.md`), biblioteca
  `src/components/ui2` (+ `ui2/command`). Layout `LovableLayout` (sidebar por papel).
- **IA**: Anthropic Claude atrás de adapters em `app/services` — IA sugere, humano aprova,
  output validado por schema. Registry de prompts (`docs/ai-prompt-registry.md`).
- **Canais**: WhatsApp API (rate-limited), SendGrid/Resend (e-mail), Kommo (CRM externo).
- **Deploy**: Railway (API+worker+Redis) + Vercel (front) + Supabase (DB). Push na `main`
  do GitHub dispara deploy → trabalho diário vive em `pilot-safe/*` (ADR 001).

## Módulos principais (pós-M1)

| Módulo | Onde | O que faz |
|---|---|---|
| **Cockpit "Hoje"** (M1) | Dashboard Executivo | Rotina da manhã: follow-ups de leads, alunos em atenção, ações do dia, funil semanal esforço→resultado |
| Dashboards (5) | `/dashboard/*` | Executivo, Operacional, Comercial, Financeiro, Retenção (com copiloto) |
| CRM / Acquisition & Growth OS | `/crm` | Funil Kanban, audiências acionáveis, briefing e script de venda |
| Central Cordex (triagem IA) | `/ai/triage` | Fila de execução guiada com mensagens prontas |
| Tarefas | `/tasks` | Modo execução operacional, subfiltros, autopilot de resolução |
| Retenção preditiva | jobs + `/dashboard/retention` | Score de risco, escada de estágios, playbooks |
| Avaliação física / Perfil 360 | `/assessments` | Bioimpedância + antropometria (7+ protocolos), PDF premium, mapa corporal |
| NPS + sentimento | `/nps` | Coleta, análise Claude, gatilhos |
| LGPD | `/audit`, exports | Export, anonimização, auditoria de ações sensíveis |

## Endpoints do M1 (contratos em specs/slots/M1/*/CONTRACT.md)

- `GET /api/v1/cockpit/daily` — 3 listas da rotina (leads follow-up ≥48h, alunos
  red/yellow, tarefas até hoje) + contagem da Central Cordex. Roles: owner, manager,
  salesperson, recepcionista. Sem cache (operacional).
- `GET /api/v1/cockpit/weekly-funnel?week_offset=` — contatos (MessageLog outbound +
  tarefas concluídas) → respostas (inbound) → conversões (leads ganhos + novos alunos +
  recuperados do risco via MemberRiskHistory), com semana anterior pra comparação.

## Método de trabalho

Time multi-agente a360: `specs/PARALLEL-PROTOCOL.md`, motor `tools/ai-team`
(worktrees + slots + reconcile na `baseBranch` do `.ai-team.json`). Snapshot:
`specs/RESUME.md`. Erros viram `docs/LEARNINGS.md`. Milestones: `docs/ROADMAP.md`.
