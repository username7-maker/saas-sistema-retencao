import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import type { LucideIcon } from "lucide-react";
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  BarChart3,
  Briefcase,
  CalendarDays,
  Search,
  ShieldAlert,
  TrendingDown,
  TrendingUp,
  UserPlus,
  Users,
  Wallet,
  Zap,
} from "lucide-react";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import {
  useChurnDashboard,
  useCommercialDashboard,
  useExecutiveDashboard,
  useOperationalDashboard,
  useRetentionDashboard,
  useWeeklySummary,
} from "../../hooks/useDashboard";
import { AiInsightCard } from "../../components/common/AiInsightCard";
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  Input,
  Skeleton,
  cn,
} from "../../components/ui2";
import { RoiSummaryCard } from "../../components/dashboard/RoiSummaryCard";
import { buildLovableDashboardViewModel } from "./dashboardAdapters";

type ActionSource = "retention" | "commercial" | "operational";
type ActionPriority = "high" | "medium";
type ChartRange = "all" | "6m" | "3m" | "custom";

const DASH_H2 = "text-[15px] leading-[1.25] font-body";
const DASH_H3 = "text-[13px] leading-[1.3]  font-body";
const DASH_H4 = "text-[12px] leading-[1.35] font-body";
const DASH_H5 = "text-[10px] leading-[1.4]  font-body uppercase tracking-[0.12em]";

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

function currency(value: number): string {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
    maximumFractionDigits: 0,
  }).format(value);
}

function compactNumber(value: number): string {
  return new Intl.NumberFormat("pt-BR", {
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(value);
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

function parseChartMonth(value: string): Date | null {
  const normalized = value.match(/^\d{4}-\d{2}$/) ? `${value}-01` : value;
  const date = new Date(normalized);
  return Number.isNaN(date.getTime()) ? null : date;
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

function MetricCard({
  label,
  value,
  helper,
  icon: Icon,
  badge,
  tone = "neutral",
}: {
  label: string;
  value: string;
  helper: string;
  icon: LucideIcon;
  badge: string;
  tone?: "neutral" | "green" | "red" | "cyan" | "orange";
}) {
  const iconColors: Record<string, string> = {
    neutral: "text-zinc-400",
    green:   "text-[#22c55e]",
    red:     "text-[#ff3b30]",
    cyan:    "text-[#00c8ff]",
    orange:  "text-[#f97316]",
  };
  const badgeColors: Record<string, string> = {
    neutral: "border-zinc-700/60  bg-zinc-800/60  text-zinc-300",
    green:   "border-[#22c55e]/40 bg-[#22c55e]/10 text-[#4ade80]",
    red:     "border-[#ff3b30]/40 bg-[#ff3b30]/10 text-[#ff6b6b]",
    cyan:    "border-[#00c8ff]/40 bg-[#00c8ff]/10 text-[#67e8f9]",
    orange:  "border-[#f97316]/40 bg-[#f97316]/10 text-[#fb923c]",
  };
  const glowBorders: Record<string, string> = {
    neutral: "hover:border-zinc-600",
    green:   "hover:border-[#22c55e]/50 hover:shadow-[0_0_20px_rgba(34,197,94,0.12)]",
    red:     "hover:border-[#ff3b30]/50 hover:shadow-[0_0_20px_rgba(255,59,48,0.15)]",
    cyan:    "hover:border-[#00c8ff]/50 hover:shadow-[0_0_20px_rgba(0,200,255,0.12)]",
    orange:  "hover:border-[#f97316]/50 hover:shadow-[0_0_20px_rgba(249,115,22,0.12)]",
  };

  return (
    <Card className={cn(
      "!border-zinc-800 !bg-black/60 !shadow-none transition-all duration-200 cursor-default backdrop-blur-sm",
      glowBorders[tone],
    )}>
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-2">
          <CardDescription className={cn("flex items-center gap-1.5 !text-zinc-500", DASH_H5)}>
            <Icon size={12} className={iconColors[tone]} />
            {label}
          </CardDescription>
          <span className={cn("rounded-full border px-2 py-0.5 font-semibold", badgeColors[tone], DASH_H5)}>
            {badge}
          </span>
        </div>
        <CardTitle className={cn(
          "font-heading text-5xl font-bold tracking-tight !text-zinc-50 pi-count-in",
          tone === "red" && "!text-[#ff6b6b]",
        )}>
          {value}
        </CardTitle>
        <p className={cn("text-zinc-500", DASH_H4)}>{helper}</p>
      </CardHeader>
    </Card>
  );
}

function CardSkeleton() {
  return (
    <Card className="!border-white/[0.06] !bg-black/60 !shadow-none">
      <CardHeader className="pb-2">
        <Skeleton className="h-3 w-32 rounded bg-zinc-900" />
        <Skeleton className="h-12 w-28 rounded bg-zinc-900" />
        <Skeleton className="h-3 w-40 rounded bg-zinc-900" />
      </CardHeader>
    </Card>
  );
}

function FilterChip({
  active,
  label,
  onClick,
}: {
  active: boolean;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "cursor-pointer rounded-lg border px-2.5 py-1 font-body font-semibold uppercase tracking-wider transition-all duration-150",
        active
          ? "border-[#22c55e]/50 bg-[#22c55e]/15 text-[#4ade80]"
          : "border-transparent bg-transparent text-zinc-500 hover:text-zinc-300",
        DASH_H5,
      )}
    >
      {label}
    </button>
  );
}

function WeeklySummaryCard() {
  const { data, isLoading } = useWeeklySummary();

  if (isLoading) {
    return (
      <Card className="!border-zinc-800 !bg-zinc-900/65 !shadow-none">
        <CardHeader>
          <Skeleton className="h-4 w-48 rounded bg-zinc-800" />
          <Skeleton className="h-3 w-64 rounded bg-zinc-800" />
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {[0, 1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-16 rounded-xl bg-zinc-800" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!data) return null;

  const deltaPositive = data.checkins_delta_pct >= 0;
  const DeltaIcon = deltaPositive ? TrendingUp : TrendingDown;

  const items = [
    {
      label: "Check-ins (7d)",
      value: data.checkins_this_week.toLocaleString("pt-BR"),
      sub: `${deltaPositive ? "+" : ""}${data.checkins_delta_pct.toFixed(1)}% vs semana anterior`,
      icon: Zap,
      tone: deltaPositive ? "text-emerald-400" : "text-amber-400",
    },
    {
      label: "Novos Alunos",
      value: data.new_registrations.toLocaleString("pt-BR"),
      sub: "cadastros nos ultimos 7 dias",
      icon: UserPlus,
      tone: "text-cyan-400",
    },
    {
      label: "Novos em Risco",
      value: data.new_at_risk.toLocaleString("pt-BR"),
      sub: "entraram em risco esta semana",
      icon: AlertTriangle,
      tone: data.new_at_risk > 5 ? "text-rose-400" : "text-amber-400",
    },
    {
      label: "MRR em Risco",
      value: new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 }).format(data.mrr_at_risk),
      sub: `de ${data.total_active} alunos ativos`,
      icon: Wallet,
      tone: data.mrr_at_risk > 0 ? "text-rose-400" : "text-emerald-400",
    },
  ];

  return (
    <Card className="!border-white/[0.06] !bg-black/60 !shadow-none backdrop-blur-sm">
      <CardHeader>
        <CardTitle className={cn("flex items-center gap-2 !text-zinc-100 font-heading", DASH_H2)}>
          <CalendarDays size={16} className="text-[#00c8ff]" />
          Resumo Semanal
        </CardTitle>
        <CardDescription className={cn("!text-zinc-500", DASH_H4)}>
          Comparativo dos últimos 7 dias com a semana anterior.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid gap-2.5 sm:grid-cols-2 lg:grid-cols-4">
          {items.map((item) => {
            const Icon = item.icon;
            return (
              <div
                key={item.label}
                className="rounded-xl border border-white/[0.05] bg-white/[0.02] p-3 transition-colors duration-200 hover:border-white/[0.1]"
              >
                <div className="mb-2 flex items-center gap-1.5">
                  <Icon size={12} className={item.tone} />
                  <span className={cn("text-zinc-500", DASH_H5)}>{item.label}</span>
                </div>
                <p className="font-heading text-2xl font-bold tracking-tight text-zinc-50">{item.value}</p>
                <p className={cn("mt-0.5 text-zinc-600", DASH_H5)}>{item.sub}</p>
              </div>
            );
          })}
        </div>
        {data.checkins_delta_pct < -10 && (
          <div className="mt-3 flex items-center gap-2 rounded-xl border border-[#f97316]/30 bg-[#f97316]/8 px-3 py-2">
            <DeltaIcon size={13} className="text-[#f97316]" />
            <p className={cn("text-[#fb923c]", DASH_H4)}>
              Queda significativa nos check-ins. Considere acionar campanha de reengajamento.
            </p>
          </div>
        )}
        {data.new_at_risk > 5 && (
          <div className="mt-3 flex items-center gap-2 rounded-xl border border-[#ff3b30]/30 bg-[#ff3b30]/8 px-3 py-2">
            <AlertTriangle size={13} className="text-[#ff3b30]" />
            <p className={cn("text-[#ff6b6b]", DASH_H4)}>
              Aumento de alunos em risco. Priorize ligações de retenção esta semana.
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export function DashboardLovable() {
  const navigate = useNavigate();
  const [activeSource, setActiveSource] = useState<"all" | ActionSource>("all");
  const [search, setSearch] = useState("");
  const [chartRange, setChartRange] = useState<ChartRange>("6m");
  const [customStartDate, setCustomStartDate] = useState("");
  const [customEndDate, setCustomEndDate] = useState("");
  const [appliedCustomStartDate, setAppliedCustomStartDate] = useState("");
  const [appliedCustomEndDate, setAppliedCustomEndDate] = useState("");
  const [customRangeError, setCustomRangeError] = useState<string | null>(null);

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

  const filteredRows = useMemo(() => {
    const normalizedSearch = search.trim().toLowerCase();
    return actionRows.filter((row) => {
      const matchesSource = activeSource === "all" || row.source === activeSource;
      const matchesSearch =
        normalizedSearch.length === 0 ||
        row.name.toLowerCase().includes(normalizedSearch) ||
        row.subtitle.toLowerCase().includes(normalizedSearch) ||
        row.status.toLowerCase().includes(normalizedSearch);
      return matchesSource && matchesSearch;
    });
  }, [actionRows, activeSource, search]);

  const visibleRows = filteredRows.slice(0, 18);
  const sourceCounters = {
    retention: actionRows.filter((row) => row.source === "retention").length,
    commercial: actionRows.filter((row) => row.source === "commercial").length,
    operational: actionRows.filter((row) => row.source === "operational").length,
  };

  const chartData = useMemo(() => {
    const points = viewModel.retentionChart;
    if (chartRange === "custom") {
      if (!appliedCustomStartDate && !appliedCustomEndDate) return points;

      const start = appliedCustomStartDate ? new Date(`${appliedCustomStartDate}T00:00:00`) : null;
      const end = appliedCustomEndDate ? new Date(`${appliedCustomEndDate}T23:59:59.999`) : null;
      if ((start && Number.isNaN(start.getTime())) || (end && Number.isNaN(end.getTime()))) return points;
      if (start && end && start > end) return [];

      return points.filter((point) => {
        const pointDate = parseChartMonth(point.month);
        if (!pointDate) return false;

        const monthStart = new Date(pointDate.getFullYear(), pointDate.getMonth(), 1, 0, 0, 0, 0);
        const monthEnd = new Date(pointDate.getFullYear(), pointDate.getMonth() + 1, 0, 23, 59, 59, 999);
        return (!start || monthEnd >= start) && (!end || monthStart <= end);
      });
    }

    if (chartRange === "3m") return points.slice(-3);
    if (chartRange === "6m") return points.slice(-6);
    return points;
  }, [chartRange, appliedCustomStartDate, appliedCustomEndDate, viewModel.retentionChart]);

  const invalidCustomRange =
    chartRange === "custom" &&
    customStartDate.length > 0 &&
    customEndDate.length > 0 &&
    new Date(`${customStartDate}T00:00:00`) > new Date(`${customEndDate}T23:59:59.999`);

  function applyCustomRange() {
    if (invalidCustomRange) {
      setCustomRangeError("Periodo invalido: a data final deve ser maior ou igual a data inicial.");
      return;
    }

    setAppliedCustomStartDate(customStartDate);
    setAppliedCustomEndDate(customEndDate);
    setCustomRangeError(null);
  }

  const cardsLoading = executive.isLoading || commercial.isLoading || operational.isLoading || retention.isLoading;
  const alertsLoading = commercial.isLoading || operational.isLoading || retention.isLoading;
  const insightLoading = executive.isLoading || commercial.isLoading || operational.isLoading || retention.isLoading || churn.isLoading;
  const chartLoading = churn.isLoading || retention.isLoading;
  const actionsLoading = commercial.isLoading || operational.isLoading || retention.isLoading;

  return (
    <section className="relative overflow-hidden rounded-[24px] border border-white/[0.06] bg-black p-4 text-zinc-100 shadow-[0_32px_140px_-40px_rgba(0,0,0,0.98)] sm:p-6">
      {/* Ambient glows — Performance Intelligence identity */}
      <div className="pointer-events-none absolute -left-32 top-10  h-80 w-80 rounded-full bg-[#22c55e]/10 blur-[80px]" />
      <div className="pointer-events-none absolute right-0  top-0   h-64 w-64 rounded-full bg-[#00c8ff]/08 blur-[60px]" />
      <div className="pointer-events-none absolute bottom-0 left-1/2 h-48 w-96 -translate-x-1/2 rounded-full bg-[#f97316]/05 blur-[80px]" />
      <div className="relative space-y-6">
        <RoiSummaryCard />
        <WeeklySummaryCard />

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {cardsLoading ? (
            <>
              <CardSkeleton />
              <CardSkeleton />
              <CardSkeleton />
              <CardSkeleton />
            </>
          ) : (
            <>
              <MetricCard
                label="Receita Mensal"
                value={currency(viewModel.cards.revenue)}
                helper="Crescimento consolidado dos últimos ciclos."
                icon={Wallet}
                badge="MRR"
                tone="green"
              />
              <MetricCard
                label="Leads no Pipeline"
                value={compactNumber(viewModel.cards.leads)}
                helper="Oportunidades ativas no funil comercial."
                icon={Users}
                badge="CRM"
                tone="cyan"
              />
              <MetricCard
                label="Check-ins 7 dias"
                value={compactNumber(viewModel.cards.checkins)}
                helper="Frequência operacional em tempo real."
                icon={Zap}
                badge="Ao vivo"
                tone="orange"
              />
              <MetricCard
                label="Risco Alto"
                value={compactNumber(viewModel.cards.highRiskMembers)}
                helper="Casos críticos — ação imediata necessária."
                icon={AlertTriangle}
                badge={viewModel.cards.highRiskMembers > 0 ? "Urgente" : "OK"}
                tone={viewModel.cards.highRiskMembers > 0 ? "red" : "green"}
              />
            </>
          )}
        </div>

        <div className="grid gap-4 lg:grid-cols-[1.05fr_0.95fr]">
          {/* Alertas Prioritários */}
          <Card className="!border-white/[0.07] !bg-black/70 !shadow-none backdrop-blur-sm">
            <CardHeader>
              <CardTitle className={cn("flex items-center gap-2 !text-zinc-100 font-heading", DASH_H2)}>
                <span className="inline-block h-2 w-2 rounded-full bg-[#ff3b30] pi-pulse" />
                Alertas Prioritários
              </CardTitle>
              <CardDescription className={cn("!text-zinc-500", DASH_H4)}>
                Acione rapidamente os pontos que mais impactam churn.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-2.5">
              {alertsLoading ? (
                <>
                  <Skeleton className="h-16 w-full rounded-xl bg-zinc-900" />
                  <Skeleton className="h-16 w-full rounded-xl bg-zinc-900" />
                  <Skeleton className="h-16 w-full rounded-xl bg-zinc-900" />
                </>
              ) : viewModel.alerts.length === 0 ? (
                <div className="rounded-xl border border-dashed border-zinc-800 p-4 text-sm text-zinc-500">
                  Nenhum alerta crítico no momento.
                </div>
              ) : (
                viewModel.alerts.map((alert) => (
                  <button
                    key={alert.id}
                    type="button"
                    onClick={() => navigate(alert.href)}
                    className={cn(
                      "w-full cursor-pointer rounded-xl border p-3 text-left transition-all duration-200",
                      alert.tone === "danger"
                        ? "border-[#ff3b30]/25 bg-[#ff3b30]/5 hover:border-[#ff3b30]/50 hover:bg-[#ff3b30]/10"
                        : alert.tone === "warning"
                          ? "border-[#f97316]/25 bg-[#f97316]/5 hover:border-[#f97316]/50 hover:bg-[#f97316]/10"
                          : "border-zinc-800 bg-zinc-900/50 hover:border-zinc-600 hover:bg-zinc-900",
                    )}
                  >
                    <div className="mb-1.5 flex items-center justify-between gap-3">
                      <p className={cn("font-semibold text-zinc-100", DASH_H3)}>{alert.title}</p>
                      <Badge variant={alert.tone === "danger" ? "danger" : alert.tone === "warning" ? "warning" : "neutral"}>
                        {alert.tone === "danger" ? "alta" : alert.tone === "warning" ? "média" : "info"}
                      </Badge>
                    </div>
                    <p className={cn("text-zinc-400", DASH_H4)}>{alert.description}</p>
                  </button>
                ))
              )}
            </CardContent>
          </Card>

          {/* IA — Inteligência da Semana */}
          <Card className="!border-[#00c8ff]/15 !bg-gradient-to-br !from-[#00c8ff]/5 !via-black/80 !to-black/90 !shadow-none backdrop-blur-sm">
            <CardHeader>
              <CardTitle className={cn("flex items-center gap-2 !text-zinc-100 font-heading", DASH_H2)}>
                <span className="inline-block h-2 w-2 rounded-full bg-[#00c8ff] pi-pulse-green" />
                IA · Insight da Semana
              </CardTitle>
              <CardDescription className={cn("!text-zinc-500", DASH_H4)}>
                Resumo automático com base no consolidado dos módulos.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {insightLoading ? (
                <>
                  <Skeleton className="h-4 w-full rounded bg-zinc-900" />
                  <Skeleton className="h-4 w-5/6 rounded bg-zinc-900" />
                  <Skeleton className="h-10 w-full rounded-xl bg-zinc-900" />
                </>
              ) : (
                <>
                  <p className={cn("leading-relaxed text-zinc-200", DASH_H3)}>{viewModel.insight}</p>
                  <button
                    type="button"
                    onClick={() => navigate("/dashboard/retention")}
                    className={cn(
                      "inline-flex w-full cursor-pointer items-center justify-between rounded-xl border border-[#00c8ff]/30 bg-[#00c8ff]/8 px-3 py-2 font-semibold text-[#67e8f9] transition-all duration-200 hover:border-[#00c8ff]/60 hover:bg-[#00c8ff]/15",
                      DASH_H3,
                    )}
                  >
                    Ver plano de retenção
                    <ArrowRight size={15} />
                  </button>
                </>
              )}
              <AiInsightCard dashboard="executive" theme="dark" />
            </CardContent>
          </Card>
        </div>

        <div className="grid gap-4 xl:grid-cols-[1.15fr_1.2fr]">
          <Card className="!border-white/[0.06] !bg-black/60 !shadow-none backdrop-blur-sm">
            <CardHeader className="flex-row items-start justify-between gap-3">
              <div>
                <CardTitle className={cn("flex items-center gap-2 !text-zinc-100 font-heading", DASH_H2)}>
                  <BarChart3 size={16} className="text-[#22c55e]" />
                  Churn e NPS
                </CardTitle>
                <CardDescription className={cn("!text-zinc-500", DASH_H4)}>Comparativo mensal de churn e NPS.</CardDescription>
              </div>
              <div className="flex gap-1 rounded-xl border border-white/[0.06] bg-white/[0.03] p-1">
                <FilterChip active={chartRange === "3m"} label="3m" onClick={() => setChartRange("3m")} />
                <FilterChip active={chartRange === "6m"} label="6m" onClick={() => setChartRange("6m")} />
                <FilterChip active={chartRange === "all"} label="Tudo" onClick={() => setChartRange("all")} />
                <FilterChip active={chartRange === "custom"} label="Custom" onClick={() => setChartRange("custom")} />
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              {chartRange === "custom" ? (
                <div className="grid gap-2 sm:grid-cols-3">
                  <label className="flex flex-col gap-1 text-[11px] font-semibold uppercase tracking-wider text-zinc-500">
                    Data inicial
                    <Input
                      type="date"
                      value={customStartDate}
                      onChange={(event) => {
                        setCustomStartDate(event.target.value);
                        setCustomRangeError(null);
                      }}
                      className="h-9 border-zinc-700 bg-zinc-900/70 text-zinc-100 [color-scheme:dark]"
                    />
                  </label>
                  <label className="flex flex-col gap-1 text-[11px] font-semibold uppercase tracking-wider text-zinc-500">
                    Data final
                    <Input
                      type="date"
                      value={customEndDate}
                      onChange={(event) => {
                        setCustomEndDate(event.target.value);
                        setCustomRangeError(null);
                      }}
                      className="h-9 border-zinc-700 bg-zinc-900/70 text-zinc-100 [color-scheme:dark]"
                    />
                  </label>
                  <div className="flex items-end gap-2">
                    <button
                      type="button"
                      onClick={() => {
                        setCustomStartDate("");
                        setCustomEndDate("");
                        setAppliedCustomStartDate("");
                        setAppliedCustomEndDate("");
                        setCustomRangeError(null);
                      }}
                      className="h-9 w-full rounded-xl border border-zinc-700 bg-zinc-900 px-3 text-xs font-semibold uppercase tracking-wider text-zinc-300 transition hover:border-zinc-500 hover:text-zinc-100"
                    >
                      Limpar periodo
                    </button>
                    <button
                      type="button"
                      onClick={applyCustomRange}
                      className="h-9 w-full rounded-xl border border-emerald-500/50 bg-emerald-500/20 px-3 text-xs font-semibold uppercase tracking-wider text-emerald-200 transition hover:border-emerald-400 hover:bg-emerald-500/30"
                    >
                      Confirmar
                    </button>
                  </div>
                </div>
              ) : null}

              {customRangeError || invalidCustomRange ? (
                <p className="text-xs text-rose-400">{customRangeError ?? "Periodo invalido: a data final deve ser maior ou igual a data inicial."}</p>
              ) : null}

              <div className={cn(chartRange === "custom" ? "h-72" : "h-80")}>
                {chartLoading ? (
                  <Skeleton className="h-full w-full rounded-xl bg-zinc-800" />
                ) : chartData.length === 0 ? (
                  <div className="flex h-full items-center justify-center rounded-xl border border-dashed border-zinc-700 text-sm text-zinc-400">
                    Sem dados para o período selecionado.
                  </div>
                ) : (
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={chartData}>
                      <defs>
                        <linearGradient id="npsGradient" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#22c55e" stopOpacity={0.48} />
                          <stop offset="95%" stopColor="#22c55e" stopOpacity={0.04} />
                        </linearGradient>
                        <linearGradient id="churnGradient" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.34} />
                          <stop offset="95%" stopColor="#f59e0b" stopOpacity={0.02} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                      <XAxis
                        dataKey="month"
                        tickFormatter={formatDateLabel}
                        tick={{ fill: "#a1a1aa", fontSize: 12 }}
                        axisLine={false}
                        tickLine={false}
                      />
                      <YAxis
                        tick={{ fill: "#a1a1aa", fontSize: 12 }}
                        axisLine={false}
                        tickLine={false}
                      />
                      <Tooltip
                        contentStyle={{
                          borderRadius: 12,
                          border: "1px solid #3f3f46",
                          background: "rgba(24,24,27,0.95)",
                          color: "#f4f4f5",
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
                        stroke="#4ade80"
                        fill="url(#npsGradient)"
                        strokeWidth={2.5}
                        connectNulls
                      />
                      <Area
                        type="monotone"
                        dataKey="churn_rate"
                        name="Churn"
                        stroke="#f59e0b"
                        fill="url(#churnGradient)"
                        strokeWidth={2.1}
                        connectNulls
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                )}
              </div>
            </CardContent>
          </Card>

          <Card className="!border-zinc-800 !bg-zinc-900/65 !shadow-none">
            <CardHeader>
              <CardTitle className={cn("!text-zinc-100", DASH_H2)}>Action Center</CardTitle>
              <CardDescription className={cn("!text-zinc-400", DASH_H4)}>
                Filtros por origem e busca rapida para reproduzir o comportamento do dashboard referencia.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-2 sm:grid-cols-3">
                <button
                  type="button"
                  onClick={() => setActiveSource("all")}
                  className={cn(
                    "rounded-xl border p-3 text-left transition",
                    activeSource === "all"
                      ? "border-emerald-400/60 bg-emerald-400/12"
                      : "border-zinc-700 bg-zinc-900/70 hover:border-zinc-500",
                  )}
                >
                  <p className={cn("uppercase tracking-wider text-zinc-500", DASH_H4)}>Total</p>
                  <p className="mt-1 text-2xl font-bold text-zinc-100">{actionRows.length}</p>
                </button>
                <button
                  type="button"
                  onClick={() => setActiveSource("operational")}
                  className={cn(
                    "rounded-xl border p-3 text-left transition",
                    activeSource === "operational"
                      ? "border-emerald-400/60 bg-emerald-400/12"
                      : "border-zinc-700 bg-zinc-900/70 hover:border-zinc-500",
                  )}
                >
                  <p className={cn("uppercase tracking-wider text-zinc-500", DASH_H4)}>Inativos 7d</p>
                  <p className="mt-1 text-2xl font-bold text-zinc-100">{sourceCounters.operational}</p>
                </button>
                <button
                  type="button"
                  onClick={() => setActiveSource("commercial")}
                  className={cn(
                    "rounded-xl border p-3 text-left transition",
                    activeSource === "commercial"
                      ? "border-emerald-400/60 bg-emerald-400/12"
                      : "border-zinc-700 bg-zinc-900/70 hover:border-zinc-500",
                  )}
                >
                  <p className={cn("uppercase tracking-wider text-zinc-500", DASH_H4)}>Leads sem contato</p>
                  <p className="mt-1 text-2xl font-bold text-zinc-100">{sourceCounters.commercial}</p>
                </button>
              </div>

              <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                <div className="flex flex-wrap gap-1.5">
                  <FilterChip
                    active={activeSource === "all"}
                    label={`Tudo (${actionRows.length})`}
                    onClick={() => setActiveSource("all")}
                  />
                  <FilterChip
                    active={activeSource === "retention"}
                    label={`Retencao (${sourceCounters.retention})`}
                    onClick={() => setActiveSource("retention")}
                  />
                  <FilterChip
                    active={activeSource === "commercial"}
                    label={`Comercial (${sourceCounters.commercial})`}
                    onClick={() => setActiveSource("commercial")}
                  />
                  <FilterChip
                    active={activeSource === "operational"}
                    label={`Operacional (${sourceCounters.operational})`}
                    onClick={() => setActiveSource("operational")}
                  />
                </div>
                <div className="relative w-full max-w-xs">
                  <Search size={14} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" />
                  <Input
                    value={search}
                    onChange={(event) => setSearch(event.target.value)}
                    placeholder="Buscar por nome ou status"
                    className="border-zinc-700 bg-zinc-900/70 pl-9 text-zinc-100 placeholder:text-zinc-500 focus:border-zinc-500 focus:ring-zinc-500/20"
                  />
                </div>
              </div>

              <div className="overflow-hidden rounded-2xl border border-zinc-800 bg-zinc-950/60">
                <table className="min-w-full divide-y divide-zinc-800">
                  <thead className="bg-zinc-900/90">
                    <tr>
                      <th className={cn("px-4 py-3 text-left font-semibold uppercase tracking-wider text-zinc-500", DASH_H5)}>Nome</th>
                      <th className={cn("px-4 py-3 text-left font-semibold uppercase tracking-wider text-zinc-500", DASH_H5)}>Origem</th>
                      <th className={cn("px-4 py-3 text-left font-semibold uppercase tracking-wider text-zinc-500", DASH_H5)}>Status</th>
                      <th className={cn("px-4 py-3 text-left font-semibold uppercase tracking-wider text-zinc-500", DASH_H5)}>Prioridade</th>
                      <th className={cn("px-4 py-3 text-left font-semibold uppercase tracking-wider text-zinc-500", DASH_H5)}>Ultimo evento</th>
                      <th className={cn("px-4 py-3 text-right font-semibold uppercase tracking-wider text-zinc-500", DASH_H5)}>Acao</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-800">
                    {actionsLoading ? (
                      [0, 1, 2, 3, 4].map((row) => (
                        <tr key={row}>
                          <td colSpan={6} className="px-4 py-3">
                            <Skeleton className="h-6 w-full rounded bg-zinc-800" />
                          </td>
                        </tr>
                      ))
                    ) : visibleRows.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="px-4 py-10 text-center text-sm text-zinc-500">
                          Nenhum resultado para o filtro aplicado.
                        </td>
                      </tr>
                    ) : (
                      visibleRows.map((row) => {
                        const SourceIcon = SOURCE_META[row.source].icon;
                        return (
                          <tr key={row.id} className="transition hover:bg-zinc-900/70">
                            <td className="px-4 py-3">
                              <p className={cn("font-semibold text-zinc-100", DASH_H3)}>{row.name}</p>
                              <p className={cn("text-zinc-500", DASH_H4)}>{row.subtitle}</p>
                            </td>
                            <td className="px-4 py-3">
                              <span className={cn("inline-flex items-center gap-1.5 font-semibold text-zinc-400", DASH_H4)}>
                                <SourceIcon size={13} />
                                {SOURCE_META[row.source].label}
                              </span>
                            </td>
                            <td className={cn("px-4 py-3 text-zinc-300", DASH_H3)}>{row.status}</td>
                            <td className="px-4 py-3">
                              <Badge variant={row.priority === "high" ? "danger" : "warning"}>
                                {row.priority === "high" ? "Alta" : "Media"}
                              </Badge>
                            </td>
                            <td className={cn("px-4 py-3 text-zinc-500", DASH_H4)}>{formatDateTime(row.lastEventAt)}</td>
                            <td className="px-4 py-3 text-right">
                              <button
                                type="button"
                                onClick={() => navigate(row.href)}
                                className={cn("inline-flex items-center rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-1.5 font-semibold uppercase tracking-wider text-zinc-200 transition hover:border-zinc-500 hover:bg-zinc-800", DASH_H4)}
                              >
                                Abrir
                              </button>
                            </td>
                          </tr>
                        );
                      })
                    )}
                  </tbody>
                </table>
              </div>

              {!actionsLoading && filteredRows.length > visibleRows.length ? (
                <p className={cn("text-zinc-500", DASH_H4)}>
                  Mostrando {visibleRows.length} de {filteredRows.length} registros.
                </p>
              ) : null}
            </CardContent>
          </Card>
        </div>

        {!insightLoading && !viewModel.hasData ? (
          <Card className="!border-zinc-700 !bg-zinc-900/60 !shadow-none">
            <CardContent className="flex flex-col items-start gap-3 py-6">
              <p className={cn("text-zinc-400", DASH_H3)}>
                Sem dados suficientes para preencher o dashboard. Importe membros e check-ins para ativar o painel.
              </p>
              <Button
                onClick={() => navigate("/imports")}
                className="!bg-emerald-500 !text-zinc-950 hover:brightness-110"
              >
                Importar dados agora
              </Button>
            </CardContent>
          </Card>
        ) : null}
      </div>
    </section>
  );
}
