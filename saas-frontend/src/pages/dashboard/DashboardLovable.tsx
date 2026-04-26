import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import type { LucideIcon } from "lucide-react";
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  BarChart3,
  Briefcase,
  ShieldAlert,
  TrendingDown,
  TrendingUp,
  UserPlus,
  Wallet,
} from "lucide-react";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { AiInsightCard } from "../../components/common/AiInsightCard";
import { RoiSummaryCard } from "../../components/dashboard/RoiSummaryCard";
import { getChartSeriesState } from "../../components/charts/chartState";
import { EmptyState, KPIStrip, PageHeader, SectionHeader, SkeletonList, StatusBadge } from "../../components/ui";
import { Button, Skeleton, cn } from "../../components/ui2";
import {
  useChurnDashboard,
  useCommercialDashboard,
  useExecutiveDashboard,
  useOperationalDashboard,
  useRetentionDashboard,
  useWeeklySummary,
} from "../../hooks/useDashboard";
import { buildLovableDashboardViewModel } from "./dashboardAdapters";

type ActionSource = "retention" | "commercial" | "operational";
type ActionPriority = "high" | "medium";
type ChartRange = "all" | "6m" | "3m";

interface ActionRow {
  id: string;
  source: ActionSource;
  name: string;
  subtitle: string;
  status: string;
  priority: ActionPriority;
  lastEventAt: string | null;
  href: string;
}

const SOURCE_META: Record<ActionSource, { label: string; icon: LucideIcon }> = {
  retention: { label: "Retencao", icon: ShieldAlert },
  commercial: { label: "Comercial", icon: Briefcase },
  operational: { label: "Operacional", icon: Activity },
};

const SOURCE_BADGE_MAP = {
  retention: { label: SOURCE_META.retention.label, variant: "danger" as const },
  commercial: { label: SOURCE_META.commercial.label, variant: "warning" as const },
  operational: { label: SOURCE_META.operational.label, variant: "success" as const },
};

const PRIORITY_BADGE_MAP = {
  high: { label: "Alta", variant: "danger" as const },
  medium: { label: "Media", variant: "warning" as const },
};

function currency(value: number): string {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
    maximumFractionDigits: 0,
  }).format(value);
}

function percent(value: number): string {
  return `${value.toFixed(1)}%`;
}

function formatDateLabel(value: string): string {
  const normalized = value.match(/^\d{4}-\d{2}$/) ? `${value}-01` : value;
  const date = new Date(normalized);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString("pt-BR", {
    month: "short",
    year: "2-digit",
  });
}

function formatDateTime(value: string | null): string {
  if (!value) return "Sem registro";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Sem registro";
  return date.toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function DashboardZone({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section
      className={cn(
        "rounded-[26px] border border-lovable-border bg-lovable-surface/92 p-5 shadow-panel backdrop-blur-xl",
        className,
      )}
    >
      {children}
    </section>
  );
}

function ZoneHeader({
  title,
  subtitle,
  actions,
}: {
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
}) {
  return (
    <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
      <div>
        <h2 className="font-heading text-lg font-bold tracking-tight text-lovable-ink">{title}</h2>
        {subtitle ? <p className="mt-1 text-sm text-lovable-ink-muted">{subtitle}</p> : null}
      </div>
      {actions ? <div className="flex shrink-0 items-center gap-2">{actions}</div> : null}
    </div>
  );
}

function KpiStripSkeleton() {
  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
      {Array.from({ length: 4 }, (_, index) => (
        <div key={index} className="rounded-[22px] border border-lovable-border bg-lovable-surface/92 px-4 py-3 shadow-panel">
          <Skeleton className="h-3 w-20 rounded" />
          <Skeleton className="mt-3 h-8 w-24 rounded" />
        </div>
      ))}
    </div>
  );
}

function WeeklySummaryMini() {
  const weeklySummary = useWeeklySummary();

  if (weeklySummary.isLoading) {
    return (
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }, (_, index) => (
          <div key={index} className="rounded-[22px] border border-lovable-border bg-lovable-surface/92 px-4 py-3 shadow-panel">
            <Skeleton className="h-3 w-24 rounded" />
            <Skeleton className="mt-3 h-6 w-20 rounded" />
            <Skeleton className="mt-2 h-3 w-28 rounded" />
          </div>
        ))}
      </div>
    );
  }

  if (!weeklySummary.data) {
    return (
      <div className="rounded-[22px] border border-dashed border-lovable-border bg-lovable-surface/75 px-4 py-3 text-sm text-lovable-ink-muted">
        Resumo semanal indisponivel no momento.
      </div>
    );
  }

  const deltaPositive = weeklySummary.data.checkins_delta_pct >= 0;
  const deltaTone = deltaPositive ? "text-emerald-400" : "text-amber-400";
  const DeltaIcon = deltaPositive ? TrendingUp : TrendingDown;

  const items = [
    {
      label: "Check-ins 7d",
      value: weeklySummary.data.checkins_this_week.toLocaleString("pt-BR"),
      helper: `${deltaPositive ? "+" : ""}${weeklySummary.data.checkins_delta_pct.toFixed(1)}% vs semana anterior`,
      icon: DeltaIcon,
      tone: deltaTone,
    },
    {
      label: "Novos alunos",
      value: weeklySummary.data.new_registrations.toLocaleString("pt-BR"),
      helper: "cadastros nos ultimos 7 dias",
      icon: UserPlus,
      tone: "text-cyan-400",
    },
    {
      label: "Novos em risco",
      value: weeklySummary.data.new_at_risk.toLocaleString("pt-BR"),
      helper: "entraram em risco esta semana",
      icon: AlertTriangle,
      tone: weeklySummary.data.new_at_risk > 5 ? "text-rose-400" : "text-amber-400",
    },
    {
      label: "MRR em risco",
      value: currency(weeklySummary.data.mrr_at_risk),
      helper: `de ${weeklySummary.data.total_active} alunos ativos`,
      icon: Wallet,
      tone: weeklySummary.data.mrr_at_risk > 0 ? "text-rose-400" : "text-emerald-400",
    },
  ];

  return (
    <div className="space-y-3">
      <SectionHeader
        title="Resumo semanal"
        subtitle="Recorte rapido dos ultimos 7 dias para apoiar a leitura dos KPIs."
      />
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {items.map((item) => {
          const Icon = item.icon;
          return (
            <div key={item.label} className="rounded-[22px] border border-lovable-border bg-lovable-surface/92 px-4 py-3 shadow-panel">
              <div className="flex items-center gap-2">
                <Icon size={14} className={item.tone} />
                <p className="text-[11px] uppercase tracking-[0.22em] text-lovable-ink-muted">{item.label}</p>
              </div>
              <p className="mt-3 font-display text-xl font-bold tracking-tight text-lovable-ink">{item.value}</p>
              <p className="mt-1 text-xs text-lovable-ink-muted">{item.helper}</p>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export function DashboardLovable() {
  const navigate = useNavigate();
  const [chartRange, setChartRange] = useState<ChartRange>("6m");

  const executive = useExecutiveDashboard();
  const commercial = useCommercialDashboard();
  const operational = useOperationalDashboard();
  const retention = useRetentionDashboard();
  const churn = useChurnDashboard();

  const viewModel = buildLovableDashboardViewModel({
    executive: executive.data,
    commercial: commercial.data,
    operational: operational.data,
    retention: retention.data,
    churn: churn.data,
  });

  const actionRows = useMemo<ActionRow[]>(() => {
    const retentionRows =
      retention.data?.red.items.map((member) => ({
        id: `retention-${member.id}`,
        source: "retention" as const,
        name: member.full_name,
        subtitle: `${member.plan_name} | score ${member.risk_score}`,
        status: "Risco vermelho",
        priority: "high" as const,
        lastEventAt: member.last_checkin_at,
        href: "/dashboard/retention",
      })) ?? [];

    const commercialRows =
      commercial.data?.stale_leads.map((lead) => ({
        id: `commercial-${lead.id}`,
        source: "commercial" as const,
        name: lead.full_name,
        subtitle: lead.source ? `Origem: ${lead.source}` : "Lead sem origem",
        status: `Pipeline ${lead.stage}`,
        priority: "medium" as const,
        lastEventAt: lead.last_contact_at,
        href: "/crm",
      })) ?? [];

    const operationalRows =
      operational.data?.inactive_7d_items.map((member) => ({
        id: `operational-${member.id}`,
        source: "operational" as const,
        name: member.full_name,
        subtitle: `${member.plan_name} | ${member.loyalty_months} meses`,
        status: "Inativo 7+ dias",
        priority: "high" as const,
        lastEventAt: member.last_checkin_at,
        href: "/dashboard/operational",
      })) ?? [];

    return [...retentionRows, ...operationalRows, ...commercialRows].sort((a, b) => {
      if (a.priority !== b.priority) return a.priority === "high" ? -1 : 1;
      const aTime = a.lastEventAt ? new Date(a.lastEventAt).getTime() : Number.MAX_SAFE_INTEGER;
      const bTime = b.lastEventAt ? new Date(b.lastEventAt).getTime() : Number.MAX_SAFE_INTEGER;
      return aTime - bTime;
    });
  }, [commercial.data?.stale_leads, operational.data?.inactive_7d_items, retention.data?.red.items]);

  const visibleRows = useMemo(() => actionRows.slice(0, 8), [actionRows]);

  const chartData = useMemo(() => {
    const points = viewModel.retentionChart;
    if (chartRange === "3m") return points.slice(-3);
    if (chartRange === "6m") return points.slice(-6);
    return points;
  }, [chartRange, viewModel.retentionChart]);

  const retentionChartState = useMemo(
    () => getChartSeriesState(chartData, ["churn_rate", "nps_avg"]),
    [chartData],
  );
  const hasMemberBase = (executive.data?.total_members ?? 0) > 0;
  const hasFinancialBase = (executive.data?.mrr ?? 0) > 0;
  const hasChurnBase = chartData.some((point) => point.churn_rate !== null);

  const kpiItems = [
    {
      label: "Total membros",
      value: executive.data?.total_members?.toLocaleString("pt-BR") ?? "0",
      tone: "neutral" as const,
    },
    {
      label: "Ativos",
      value: executive.data?.active_members?.toLocaleString("pt-BR") ?? "0",
      tone: "success" as const,
    },
    {
      label: "Churn",
      value: hasChurnBase || hasMemberBase ? percent(executive.data?.churn_rate ?? 0) : "Sem base",
      tone: hasChurnBase || hasMemberBase ? ((executive.data?.churn_rate ?? 0) > 5 ? "danger" as const : "warning" as const) : "neutral" as const,
    },
    {
      label: "Receita",
      value: hasFinancialBase ? currency(executive.data?.mrr ?? 0) : "Sem base",
      tone: hasFinancialBase ? "success" as const : "neutral" as const,
    },
  ];

  const kpiLoading = executive.isLoading;
  const chartLoading = churn.isLoading || retention.isLoading;
  const actionLoading = commercial.isLoading || operational.isLoading || retention.isLoading;

  return (
    <section className="relative overflow-hidden rounded-[34px] border border-lovable-border bg-[linear-gradient(180deg,hsl(var(--lovable-surface)/0.98),hsl(var(--lovable-bg-muted)/0.92))] p-4 text-lovable-ink shadow-panel backdrop-blur-2xl sm:p-6">
      <div className="pointer-events-none absolute -left-28 top-10 h-80 w-80 rounded-full bg-[hsl(var(--lovable-primary)/0.2)] blur-[140px]" />
      <div className="pointer-events-none absolute right-0 top-0 h-64 w-64 rounded-full bg-[hsl(var(--lovable-info)/0.14)] blur-[140px]" />

      <div className="relative space-y-6">
        <PageHeader
          title="Dashboard"
          subtitle="Visao geral operacional e estrategica da academia"
        />

        <DashboardZone>
          <div className="space-y-4">
            {kpiLoading ? <KpiStripSkeleton /> : <KPIStrip items={kpiItems} />}
            <WeeklySummaryMini />
          </div>
        </DashboardZone>

        <div className="grid gap-4 lg:grid-cols-2">
          <DashboardZone>
            <ZoneHeader
              title="Churn e NPS"
              subtitle="Evolucao consolidada do churn e do NPS medio."
              actions={
                <div className="flex items-center gap-1">
                  {[
                    { value: "all", label: "Tudo" },
                    { value: "6m", label: "6M" },
                    { value: "3m", label: "3M" },
                  ].map((option) => (
                    <Button
                      key={option.value}
                      size="sm"
                      variant={chartRange === option.value ? "secondary" : "ghost"}
                      className="rounded-lg"
                      onClick={() => setChartRange(option.value as ChartRange)}
                    >
                      {option.label}
                    </Button>
                  ))}
                </div>
              }
            />

            <div className="h-80">
              {chartLoading ? (
                <Skeleton className="h-full w-full rounded-[22px]" />
              ) : chartData.length === 0 ? (
                <div className="flex h-full items-center justify-center rounded-[22px] border border-dashed border-lovable-border">
                  <EmptyState
                    icon={BarChart3}
                    title="Sem dados para o periodo"
                    description="Ajuste o intervalo ou aguarde mais historico para visualizar a evolucao."
                  />
                </div>
              ) : !retentionChartState.hasMeaningfulValues ? (
                <div className="flex h-full items-center justify-center rounded-[22px] border border-dashed border-lovable-border">
                  <EmptyState
                    icon={BarChart3}
                    title="Sem base historica util para o grafico"
                    description="O piloto ainda nao acumulou NPS ou churn com variacao suficiente. Assim que houver respostas e cancelamentos registrados, a curva aparece aqui com contexto real."
                  />
                </div>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={chartData}>
                    <defs>
                      <linearGradient id="npsGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="hsl(var(--lovable-primary))" stopOpacity={0.42} />
                        <stop offset="95%" stopColor="hsl(var(--lovable-primary))" stopOpacity={0.02} />
                      </linearGradient>
                      <linearGradient id="churnGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="hsl(var(--lovable-info))" stopOpacity={0.28} />
                        <stop offset="95%" stopColor="hsl(var(--lovable-info))" stopOpacity={0.01} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--lovable-chart-grid) / 0.55)" />
                    <XAxis
                      dataKey="month"
                      tickFormatter={formatDateLabel}
                      tick={{ fill: "hsl(var(--lovable-ink-muted))", fontSize: 12 }}
                      axisLine={false}
                      tickLine={false}
                    />
                    <YAxis
                      tick={{ fill: "hsl(var(--lovable-ink-muted))", fontSize: 12 }}
                      axisLine={false}
                      tickLine={false}
                    />
                    <Tooltip
                      contentStyle={{
                        borderRadius: 12,
                        border: "1px solid hsl(var(--lovable-border))",
                        background: "hsl(var(--lovable-surface) / 0.96)",
                        color: "hsl(var(--lovable-ink))",
                        boxShadow: "var(--shadow-panel)",
                      }}
                      formatter={(value, key) => {
                        const parsedValue = typeof value === "number" ? value : Number(value);
                        if (!Number.isFinite(parsedValue)) return ["-", String(key)];
                        if (key === "churn_rate") return [`${parsedValue.toFixed(2)}%`, "Churn"];
                        return [parsedValue.toFixed(2), "NPS medio"];
                      }}
                      labelFormatter={(label) => formatDateLabel(String(label))}
                    />
                    <Area
                      type="monotone"
                      dataKey="nps_avg"
                      name="NPS medio"
                      stroke="hsl(var(--lovable-primary))"
                      fill="url(#npsGradient)"
                      strokeWidth={2.5}
                      connectNulls
                    />
                    <Area
                      type="monotone"
                      dataKey="churn_rate"
                      name="Churn"
                      stroke="hsl(var(--lovable-info))"
                      fill="url(#churnGradient)"
                      strokeWidth={2.1}
                      connectNulls
                    />
                  </AreaChart>
                </ResponsiveContainer>
              )}
            </div>
            {retentionChartState.hasMeaningfulValues && retentionChartState.isFlat ? (
              <p className="mt-3 text-xs text-lovable-ink-muted">
                Serie praticamente estavel no periodo. Use Retencao e NPS para validar se a estabilidade reflete operacao real ou falta de novos eventos.
              </p>
            ) : null}
          </DashboardZone>

          <DashboardZone>
            <ZoneHeader
              title="Leitura executiva"
              subtitle="Resumo curto para orientar a proxima decisao operacional."
            />

            <div className="space-y-4">
              {viewModel.alerts[0] ? (
                <div className="flex items-start gap-2 rounded-[22px] border border-lovable-border bg-lovable-surface/84 px-4 py-3 shadow-panel">
                  <AlertTriangle
                    size={16}
                    className={cn(
                      "mt-0.5",
                      viewModel.alerts[0].tone === "danger"
                        ? "text-rose-400"
                        : viewModel.alerts[0].tone === "warning"
                          ? "text-amber-400"
                          : "text-lovable-ink-muted",
                    )}
                  />
                  <div>
                    <p className="text-sm font-semibold text-lovable-ink">{viewModel.alerts[0].title}</p>
                    <p className="mt-1 text-sm text-lovable-ink-muted">{viewModel.alerts[0].description}</p>
                  </div>
                </div>
              ) : null}

              <div className="rounded-[24px] border border-lovable-border bg-lovable-surface/90 px-4 py-4 shadow-panel">
                <p className="text-sm leading-relaxed text-lovable-ink">{viewModel.insight}</p>
                <div className="mt-4 flex flex-wrap items-center gap-2">
                  <Button size="sm" variant="secondary" onClick={() => navigate("/dashboard/retention")}>
                    Ver plano de retencao
                    <ArrowRight size={14} />
                  </Button>
                </div>
              </div>

              <AiInsightCard dashboard="executive" />
            </div>
          </DashboardZone>
        </div>

        <div className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
          <DashboardZone>
            <SectionHeader
              title="Acoes prioritarias"
              subtitle={
                actionRows.length > visibleRows.length
                  ? `Mostrando ${visibleRows.length} de ${actionRows.length} itens priorizados da fila.`
                  : "Fila operacional consolidada e ordenada por prioridade."
              }
              count={visibleRows.length}
            />

            {actionLoading ? (
              <SkeletonList rows={6} cols={4} />
            ) : visibleRows.length === 0 ? (
              <EmptyState
                icon={AlertTriangle}
                title="Nenhuma acao prioritaria no momento"
                description="A fila esta sob controle. Volte mais tarde para acompanhar novas oportunidades."
              />
            ) : (
              <div className="space-y-2">
                {visibleRows.map((row) => {
                  const SourceIcon = SOURCE_META[row.source].icon;

                  return (
                    <div
                      key={row.id}
                      className="flex flex-col gap-3 rounded-[22px] border border-lovable-border bg-lovable-surface/88 px-4 py-3 shadow-panel lg:flex-row lg:items-center lg:justify-between"
                    >
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <p className="truncate text-sm font-semibold text-lovable-ink">{row.name}</p>
                          <StatusBadge status={row.source} map={SOURCE_BADGE_MAP} />
                          <StatusBadge status={row.priority} map={PRIORITY_BADGE_MAP} />
                        </div>
                        <p className="mt-1 text-xs text-lovable-ink-muted">{row.subtitle}</p>
                        <div className="mt-2 flex flex-wrap items-center gap-3 text-xs text-lovable-ink-muted">
                          <span className="inline-flex items-center gap-1.5">
                            <SourceIcon size={12} />
                            {row.status}
                          </span>
                          <span>Ultimo evento: {formatDateTime(row.lastEventAt)}</span>
                        </div>
                      </div>

                      <div className="flex shrink-0 items-center">
                        <Button size="sm" variant="ghost" onClick={() => navigate(row.href)}>
                          Abrir
                        </Button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </DashboardZone>

          <div className="space-y-4">
            <RoiSummaryCard />
          </div>
        </div>

        {!executive.isLoading && !viewModel.hasData ? (
          <DashboardZone className="bg-lovable-surface/86">
            <div className="flex flex-col items-start gap-3 py-2">
              <p className="text-sm text-lovable-ink-muted">
                Sem dados suficientes para preencher o dashboard. Importe membros e check-ins para ativar o painel.
              </p>
              <Button onClick={() => navigate("/imports")}>Importar dados agora</Button>
            </div>
          </DashboardZone>
        ) : null}
      </div>
    </section>
  );
}
