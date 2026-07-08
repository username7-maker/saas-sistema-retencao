# ARTIFACTS — cockpit-ui (worker-C)

## Arquivos (todos dentro do território)
Criados:
- `saas-frontend/src/types/cockpit.ts` — espelho literal dos 2 contratos.
- `saas-frontend/src/hooks/useCockpit.ts` — `useDailyCockpit` (refetch 60s) + `useWeeklyFunnel`.
- `saas-frontend/src/components/dashboard/cockpit/{index.ts,TodayBlock.tsx,FollowupsPanel.tsx,AttentionPanel.tsx,ActionsTodayPanel.tsx,WeeklyFunnelPanel.tsx}`.

Editado:
- `saas-frontend/src/pages/dashboard/DashboardLovable.tsx` — import + `<TodayBlock />` como
  primeira seção (2 linhas; conteúdo existente intacto).
- `dashboardAdapters.ts` NÃO foi tocado (a spec preferia não tocar — não precisou).

## Smoke
- `npm run build` (saas-frontend) → ✓ built in 8.97s, TypeScript estrito verde.
- `py -3.12 -m pytest saas-backend -q` → 1075 passed (backend intacto).

## Decisões (desvios documentados da DESIGN-SPEC)
1. **Base path real:** endpoints consumidos em `/api/v1/cockpit/*` (padrão de
   `dashboardService.ts`), não `/cockpit/*` — a spec assumia o prefixo implícito.
2. Grid 4 colunas dentro de um `CommandCard variant="elevated"` único; cada painel é um
   sub-card no padrão visual dos alertas existentes da página.
3. Chip "Central Cordex: N" (tone `ai`) no header do painel Ações do dia → navega
   `/ai/triage`; some quando N=0.
4. Estados de erro por consulta (daily cobre 3 painéis, funnel o 4º) com "Tentar de novo".

## Pendências pro reconciler
1. Integração real: com os routers registrados (slots cockpit-api/funnel-api), abrir
   `/dashboard/executive` e conferir os 4 painéis com dado real.
2. Decisão de CTO no fechamento: ampliar acesso da rota `/dashboard/executive` pra
   SALESPERSON/RECEPTIONIST (endpoints já aceitam; página hoje é OWNER/MANAGER).
