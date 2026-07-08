# DESIGN-SPEC — cockpit-ui

> Ref design: `docs/design/DESIGN-OVERVIEW.md` (o produto vivo é a fonte visual — não há
> raw/). Replicar o padrão do próprio Dashboard Executivo: componentes `ui2`/`ui2/command`,
> tokens Dark Intelligence, headings `font-heading`.

## Tipos — `saas-frontend/src/types/cockpit.ts`
Espelho 1:1 dos contratos (snake_case, como `RetentionQueueItem` já faz):
```ts
export interface CockpitLeadFollowup {
  lead_id: string; full_name: string; phone: string | null; stage: string;
  days_since_contact: number | null; reason: string; href: string;
}
export interface CockpitMemberAttention {
  member_id: string; full_name: string; risk_level: "red" | "yellow";
  retention_stage: string | null; days_without_checkin: number | null;
  reason: string; href: string;
}
export interface CockpitActionToday {
  task_id: string; title: string; priority: string; due_date: string | null;
  overdue: boolean; target_name: string | null; href: string;
}
export interface CockpitCounts { leads_followup: number; members_attention: number; actions_today: number; }
export interface DailyCockpitResponse {
  generated_at: string;
  leads_followup: CockpitLeadFollowup[];
  members_attention: CockpitMemberAttention[];
  actions_today: CockpitActionToday[];
  triage_pending_count: number;
  counts: CockpitCounts;
}
export interface FunnelStage { key: string; label: string; value: number; previous_value: number; }
export interface ConversionBreakdown { leads_won: number; members_joined: number; risk_recovered: number; }
export interface WeeklyFunnelResponse {
  week_start: string; week_end: string; week_offset: number;
  contacts: FunnelStage; responses: FunnelStage; conversions: FunnelStage;
  conversion_breakdown: ConversionBreakdown;
}
```

## Hooks — `saas-frontend/src/hooks/useCockpit.ts`
Padrão de `useDashboard.ts` (React Query + api client). Fetchers no próprio arquivo
(NÃO editar `src/services/*`):
```ts
import { api } from "../services/api";
const ONE_MINUTE = 60 * 1000;

export function useDailyCockpit() {
  return useQuery({
    queryKey: ["cockpit", "daily"],
    queryFn: async () => (await api.get<DailyCockpitResponse>("/cockpit/daily")).data,
    staleTime: ONE_MINUTE,
    refetchInterval: ONE_MINUTE,   // cockpit operacional: dado fresco na recepção
  });
}
export function useWeeklyFunnel() {
  return useQuery({
    queryKey: ["cockpit", "weekly-funnel"],
    queryFn: async () => (await api.get<WeeklyFunnelResponse>("/cockpit/weekly-funnel")).data,
    staleTime: 5 * ONE_MINUTE,
  });
}
```
(Conferir a assinatura exata do `api` client em `src/services/api*` antes — se
`api.get<T>` já devolve `T` direto, como em `dashboardService.ts`, seguir esse padrão.)

## Componentes — `saas-frontend/src/components/dashboard/cockpit/`
```
index.ts                # barrel interno da pasta (permitido — território próprio)
TodayBlock.tsx          # container: usa os 2 hooks, layout, estados de carga/erro
FollowupsPanel.tsx      # painel 1 — Follow-ups de leads
AttentionPanel.tsx      # painel 2 — Alunos em atenção
ActionsTodayPanel.tsx   # painel 3 — Ações do dia (+ chip Central Cordex com triage_pending_count)
WeeklyFunnelPanel.tsx   # painel 4 — Funil da semana
```
- **`TodayBlock`** (export default nomeado `TodayBlock`, sem props):
  - `SectionHeader` título **"Hoje"**, subtítulo "A rotina comercial do dia — leads,
    alunos, ações e resultado da semana." + horário de `generated_at`.
  - Grid: `grid grid-cols-1 gap-4 xl:grid-cols-4` (desktop recepção ≥1280px = 4 colunas;
    empilha abaixo). Painéis em `CommandCard`.
  - Carregando: `PremiumSkeleton` (1 por painel). Erro: painel com mensagem + botão
    "Tentar de novo" chamando `refetch` (padrão da tela).
- **Painéis de lista** (props tipadas):
  ```ts
  interface FollowupsPanelProps { items: CockpitLeadFollowup[]; total: number; }
  interface AttentionPanelProps { items: CockpitMemberAttention[]; total: number; }
  interface ActionsTodayPanelProps { items: CockpitActionToday[]; total: number; triagePendingCount: number; }
  ```
  - Cada item: nome + `reason` + `StatusPill` (follow-up: stage; atenção: risk_level
    red→danger/yellow→warning; ações: priority, overdue com `animate-pi-pulse`).
  - Clique no item → `useNavigate()(item.href)`. Rodapé "Ver todos (N)" → mesma rota.
  - Vazio: `PremiumEmptyState` — textos exatos: "Nenhum lead esperando resposta" /
    "Nenhum aluno em atenção agora" / "Nenhuma ação pendente pra hoje".
- **`WeeklyFunnelPanel`** (props `{ funnel: WeeklyFunnelResponse }`):
  - 3 linhas (Contatos feitos / Respostas recebidas / Conversões): valor grande
    (`font-heading`), delta vs. `previous_value` (↑ verde `pi-green`, ↓ vermelho `pi-red`,
    = neutro muted).
  - Sub-linha de conversões: "2 vendas · 2 novos alunos · 1 recuperado" (breakdown).
  - Vazio (tudo zero): PremiumEmptyState "Sem atividade registrada nesta semana".

## Integração — `saas-frontend/src/pages/dashboard/DashboardLovable.tsx`
- Renderizar `<TodayBlock />` como PRIMEIRA seção do dashboard, acima do "Mapa de
  Inteligência Operacional". Nada do conteúdo atual é removido.
- `dashboardAdapters.ts`: só se precisar expor helper compartilhado — preferir não tocar.

## Estados visuais (obrigatórios)
vazio | carregando | erro | sucesso — por painel, nunca quebrando o grid.

## Smoke
- `npm run build` em `saas-frontend/` (TypeScript estrito + Vite verdes).
- `py -3.12 -m pytest saas-backend -q` continua verde (não toca backend).

## Território
- `saas-frontend/src/pages/dashboard/DashboardLovable.tsx`
- `saas-frontend/src/pages/dashboard/dashboardAdapters.ts`
- `saas-frontend/src/components/dashboard/cockpit/**` (pasta nova)
- `saas-frontend/src/hooks/useCockpit.ts`
- `saas-frontend/src/types/cockpit.ts`

**Neutro proibido:** `App.tsx`, `src/components/ui2/**`, `src/services/**` (importar
apenas), `src/types/index.ts` (barrel — importar de `../types/cockpit` direto),
`package.json`, outras páginas, CI.
