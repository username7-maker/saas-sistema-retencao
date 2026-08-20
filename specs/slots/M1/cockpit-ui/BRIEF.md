# BRIEF — cockpit-ui

**O quê:** evoluir o Dashboard Executivo (`DashboardLovable.tsx`) com o bloco **"Hoje"**
no topo: 4 painéis — Follow-ups de leads · Alunos em atenção · Ações do dia · Funil da
semana — consumindo `GET /api/cockpit/daily` e `GET /api/cockpit/weekly-funnel`.

**Por quê:** é o cockpit em si (M1): a tela que a recepção abre de manhã. Decisão do
fundador: evoluir a tela existente, não criar página nova.

**Critérios de aceite:**
- O bloco "Hoje" aparece acima do conteúdo atual do dashboard (que permanece), com os
  4 painéis do CONTRACT.md; desktop primeiro (sidebar 272px + grid 4 colunas ≥1280px,
  empilha abaixo disso).
- Cada item tem deep-link: lead → `/crm` no lead certo; aluno → rotina de retenção;
  ação → `/tasks` ou `/ai/triage`. Navegação com `useNavigate` (padrão da tela).
- Estados obrigatórios: carregando (`PremiumSkeleton`), vazio por painel
  (`PremiumEmptyState` com mensagem de operação, ex. "Nenhum lead esperando resposta"),
  erro com retry (padrão React Query da tela).
- Visual 100% com componentes existentes (`ui2` + `ui2/command`: CommandCard, ActionQueue,
  MetricCard, StatusPill, SectionHeader) e tokens do DESIGN-OVERVIEW — nada de estilo novo.
- Funil da semana renderiza os 3 estágios com comparação vs. semana anterior (↑/↓).
- Tipos TS derivados dos contratos dos endpoints (CONTRACT.md), em `src/types/cockpit.ts`.
- Smoke verde: `npm run build` em `saas-frontend/` **e** `py -3.12 -m pytest saas-backend -q`.

**Território (pode editar):**
- `saas-frontend/src/pages/dashboard/DashboardLovable.tsx`
- `saas-frontend/src/pages/dashboard/dashboardAdapters.ts`
- `saas-frontend/src/components/dashboard/cockpit/` (nova pasta, livre dentro dela)
- `saas-frontend/src/hooks/useCockpit.ts` (novo)
- `saas-frontend/src/types/cockpit.ts` (novo)

**Zonas neutras (NÃO tocar — reconciler faz):**
- `saas-frontend/src/App.tsx`, `src/components/ui2/**` (biblioteca), `src/services/api*`
  (cliente HTTP base — importar, não editar), `package.json`, CI
- Qualquer outra página/dashboard (`CommercialDashboardPage`, `RetentionDashboardPage`, …)

**Depende de:** contratos pinados de `cockpit-api` e `funnel-api` (CONTRACT.md — pode
construir em paralelo contra o contrato; integração real valida no reconcile).
