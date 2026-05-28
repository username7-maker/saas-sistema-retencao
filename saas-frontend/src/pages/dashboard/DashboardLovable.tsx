import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  BarChart3,
  CalendarCheck,
  CheckSquare,
  DollarSign,
  ShieldAlert,
  Target,
  TrendingDown,
  UserPlus,
  Users,
  Wallet,
  Zap,
} from "lucide-react";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { getChartSeriesState } from "../../components/charts/chartState";
import {
  ActionQueue,
  AIInsightPanel,
  Button,
  CommandCard,
  MetricCard,
  PremiumEmptyState,
  PremiumSkeleton,
  RiskMatrix,
  SectionHeader,
  StatusPill,
  cn,
} from "../../components/ui2";
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
type ActionPriority = "critical" | "high" | "medium";
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

function percentOf(count: number, total: number): number {
  if (total <= 0) return 0;
  return (count / total) * 100;
}

function DashboardHero({
  insight,
  redCount,
  inactiveCount,
  mrrAtRisk,
}: {
  insight: string;
  redCount: number;
  inactiveCount: number;
  mrrAtRisk: number;
}) {
  return (
    <CommandCard variant="elevated" className="min-h-[210px] overflow-hidden">
      <div className="relative grid gap-6">
        <div>
          <p className="text-[11px] font-bold uppercase tracking-[0.34em] text-blue-400">Performance Intelligence</p>
          <h1 className="mt-4 font-heading text-5xl font-extrabold tracking-tight md:text-6xl">
            <span className="bg-gradient-to-r from-white via-white to-blue-300 bg-clip-text text-transparent">
              IA de risco em tempo real
            </span>
          </h1>
          <p className="mt-4 max-w-3xl text-sm leading-7 text-lovable-ink-muted md:text-base">{insight}</p>
          <div className="mt-5 flex flex-wrap gap-2">
            <StatusPill tone={redCount > 0 ? "critical" : "normal"} dot>
              Prioridade: retenção
            </StatusPill>
            <StatusPill tone={inactiveCount > 0 ? "alert" : "normal"}>
              Foco: alunos inativos
            </StatusPill>
            <StatusPill tone={mrrAtRisk > 0 ? "warning" : "sync"}>
              Oportunidade: {mrrAtRisk > 0 ? currency(mrrAtRisk) : "sem MRR em risco"}
            </StatusPill>
          </div>
        </div>
      </div>
    </CommandCard>
  );
}

function IntelligenceMap({
  activeMembers,
  checkins7d,
  churnRate,
  actionCount,
  mrr,
}: {
  activeMembers: number;
  checkins7d: number;
  churnRate: number;
  actionCount: number;
  mrr: number;
}) {
  const nodes = [
    { id: "active", title: "Alunos ativos", value: activeMembers.toLocaleString("pt-BR"), icon: Users, tone: "info" as const },
    { id: "freq", title: "Frequência", value: checkins7d.toLocaleString("pt-BR"), icon: Activity, tone: "success" as const },
    { id: "risk", title: "Risco de churn", value: percent(churnRate), icon: ShieldAlert, tone: churnRate > 5 ? "danger" as const : "success" as const },
    { id: "actions", title: "Ações de retenção", value: actionCount.toLocaleString("pt-BR"), icon: Target, tone: actionCount > 0 ? "ai" as const : "neutral" as const },
    { id: "revenue", title: "Receita MRR", value: currency(mrr), icon: DollarSign, tone: mrr > 0 ? "success" as const : "neutral" as const },
  ];

  return (
    <CommandCard>
      <SectionHeader
        title="Mapa de Inteligência Operacional"
        subtitle="Como os principais indicadores se conectam para proteger frequência, retenção e receita."
        actions={<StatusPill tone="integration">Fluxo de decisão</StatusPill>}
      />
      <div className="grid gap-3 xl:grid-cols-[1fr_auto_1fr_auto_1fr] xl:items-center">
        {nodes.slice(0, 3).map((node, index) => {
          const Icon = node.icon;
          return (
            <div key={node.id} className="contents">
              <div className="rounded-[22px] border border-lovable-border/70 bg-lovable-surface/62 p-4">
                <div className="flex items-center gap-3">
                  <span className={cn("flex h-10 w-10 items-center justify-center rounded-2xl border", node.tone === "danger" ? "border-rose-400/24 bg-rose-400/12 text-rose-200" : "border-blue-400/18 bg-blue-400/10 text-blue-300")}>
                    <Icon size={18} />
                  </span>
                  <div>
                    <p className="text-xs text-lovable-ink-muted">{node.title}</p>
                    <p className="font-display text-xl font-bold text-lovable-ink">{node.value}</p>
                  </div>
                </div>
              </div>
              {index < 2 ? (
                <div className="hidden h-px w-16 bg-[linear-gradient(90deg,hsl(var(--lovable-primary)/0.15),hsl(var(--lovable-primary)/0.75))] xl:block" />
              ) : null}
            </div>
          );
        })}
      </div>
      <div className="mt-4 grid gap-3 md:grid-cols-2">
        {nodes.slice(3).map((node) => {
          const Icon = node.icon;
          return (
            <div key={node.id} className="rounded-[22px] border border-lovable-border/70 bg-lovable-surface/54 p-4">
              <div className="flex items-center gap-3">
                <span className="flex h-10 w-10 items-center justify-center rounded-2xl border border-[rgba(59,130,246,0.22)] bg-[rgba(59,130,246,0.10)] text-blue-300">
                  <Icon size={18} />
                </span>
                <div>
                  <p className="text-xs text-lovable-ink-muted">{node.title}</p>
                  <p className="font-display text-xl font-bold text-lovable-ink">{node.value}</p>
                </div>
              </div>
            </div>
          );
        })}
      </div>
      <div className="mt-4 flex flex-wrap gap-3 text-xs text-lovable-ink-muted">
        <span className="inline-flex items-center gap-2"><span className="h-2 w-8 rounded-full bg-emerald-400" /> Influência positiva</span>
        <span className="inline-flex items-center gap-2"><span className="h-2 w-8 rounded-full bg-amber-400" /> Atenção necessária</span>
        <span className="inline-flex items-center gap-2"><span className="h-2 w-8 rounded-full bg-rose-400" /> Alto risco</span>
      </div>
    </CommandCard>
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
  const weeklySummary = useWeeklySummary();

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
        subtitle: `${member.plan_name} · score ${member.risk_score}`,
        status: "Risco vermelho",
        priority: "critical" as const,
        lastEventAt: member.last_checkin_at,
        href: "/dashboard/retention",
      })) ?? [];

    const operationalRows =
      operational.data?.inactive_7d_items.map((member) => ({
        id: `operational-${member.id}`,
        source: "operational" as const,
        name: member.full_name,
        subtitle: `${member.plan_name} · ${member.loyalty_months} meses`,
        status: "Inativo 7+ dias",
        priority: "high" as const,
        lastEventAt: member.last_checkin_at,
        href: "/dashboard/operational",
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

    return [...retentionRows, ...operationalRows, ...commercialRows].sort((a, b) => {
      const priorityOrder: Record<ActionPriority, number> = { critical: 0, high: 1, medium: 2 };
      if (a.priority !== b.priority) return priorityOrder[a.priority] - priorityOrder[b.priority];
      const aTime = a.lastEventAt ? new Date(a.lastEventAt).getTime() : Number.MAX_SAFE_INTEGER;
      const bTime = b.lastEventAt ? new Date(b.lastEventAt).getTime() : Number.MAX_SAFE_INTEGER;
      return aTime - bTime;
    });
  }, [commercial.data?.stale_leads, operational.data?.inactive_7d_items, retention.data?.red.items]);

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

  const activeMembers = executive.data?.active_members ?? 0;
  const totalMembers = executive.data?.total_members ?? 0;
  const churnRate = executive.data?.churn_rate ?? 0;
  const mrr = executive.data?.mrr ?? 0;
  const redCount = retention.data?.red.total ?? executive.data?.risk_distribution.red ?? 0;
  const yellowCount = retention.data?.yellow.total ?? executive.data?.risk_distribution.yellow ?? 0;
  const inactiveCount = operational.data?.inactive_7d_total ?? 0;
  const checkins7d = weeklySummary.data?.checkins_this_week ?? operational.data?.realtime_checkins ?? 0;
  const newAtRisk = weeklySummary.data?.new_at_risk ?? 0;
  const mrrAtRisk = weeklySummary.data?.mrr_at_risk ?? retention.data?.mrr_at_risk ?? 0;
  const isDashboardLoading =
    executive.isLoading || operational.isLoading || retention.isLoading || weeklySummary.isLoading;

  const metricCards = [
    {
      label: "Total de membros",
      value: totalMembers.toLocaleString("pt-BR"),
      subtitle: "Base total da academia",
      trend: totalMembers > 0 ? "base importada" : "aguardando dados",
      trendDirection: "flat" as const,
      icon: Users,
      tone: "info" as const,
    },
    {
      label: "Alunos ativos",
      value: activeMembers.toLocaleString("pt-BR"),
      subtitle: "Praticaram ou permanecem ativos",
      trend: activeMembers > 0 ? `${percentOf(activeMembers, Math.max(totalMembers, 1)).toFixed(1)}% da base` : "sem base ativa",
      trendDirection: activeMembers > 0 ? "up" as const : "flat" as const,
      icon: Activity,
      tone: "success" as const,
    },
    {
      label: "Churn médio",
      value: totalMembers > 0 ? percent(churnRate) : "Sem base",
      subtitle: totalMembers > 0 ? "Indicador consolidado" : "Depende de histórico",
      trend: churnRate > 5 ? "acima do ideal" : "sob controle",
      trendDirection: churnRate > 5 ? "down" as const : "up" as const,
      icon: TrendingDown,
      tone: churnRate > 5 ? "danger" as const : "success" as const,
    },
    {
      label: "Receita / MRR",
      value: mrr > 0 ? currency(mrr) : "Sem base",
      subtitle: "Receita recorrente",
      trend: mrr > 0 ? "financeiro conectado" : "sem dados financeiros",
      trendDirection: mrr > 0 ? "up" as const : "flat" as const,
      icon: DollarSign,
      tone: mrr > 0 ? "success" as const : "neutral" as const,
    },
    {
      label: "Check-ins 7D",
      value: checkins7d.toLocaleString("pt-BR"),
      subtitle: "Movimento operacional recente",
      trend:
        weeklySummary.data?.checkins_delta_pct !== undefined
          ? `${weeklySummary.data.checkins_delta_pct >= 0 ? "+" : ""}${weeklySummary.data.checkins_delta_pct.toFixed(1)}% vs. semana ant.`
          : "sem comparação",
      trendDirection: (weeklySummary.data?.checkins_delta_pct ?? 0) >= 0 ? "up" as const : "down" as const,
      icon: CalendarCheck,
      tone: "info" as const,
    },
    {
      label: "Novos alunos",
      value: (weeklySummary.data?.new_registrations ?? 0).toLocaleString("pt-BR"),
      subtitle: "Cadastros nos últimos 7 dias",
      trend: "onboarding monitora ativação",
      trendDirection: "flat" as const,
      icon: UserPlus,
      tone: "ai" as const,
    },
    {
      label: "Novos em risco",
      value: newAtRisk.toLocaleString("pt-BR"),
      subtitle: "Precisam de atenção",
      trend: newAtRisk > 0 ? "agir nas próximas 24h" : "sem alerta novo",
      trendDirection: newAtRisk > 0 ? "down" as const : "up" as const,
      icon: AlertTriangle,
      tone: newAtRisk > 0 ? "warning" as const : "success" as const,
    },
    {
      label: "MRR em risco",
      value: mrrAtRisk > 0 ? currency(mrrAtRisk) : "R$ 0",
      subtitle: activeMembers > 0 ? `de ${activeMembers.toLocaleString("pt-BR")} alunos ativos` : "sem base ativa",
      trend: mrrAtRisk > 0 ? "proteger receita" : "sem risco financeiro",
      trendDirection: mrrAtRisk > 0 ? "down" as const : "up" as const,
      icon: Wallet,
      tone: mrrAtRisk > 0 ? "danger" as const : "success" as const,
    },
  ];

  const riskSegments = [
    {
      id: "red",
      label: "Risco vermelho",
      count: redCount,
      rate: percentOf(redCount, Math.max(activeMembers, totalMembers)),
      helper: "Contato humano imediato",
      level: "critical" as const,
    },
    {
      id: "inactive",
      label: "Há 7+ dias sem treino",
      count: inactiveCount,
      rate: percentOf(inactiveCount, Math.max(activeMembers, totalMembers)),
      helper: "Sinal forte de queda de frequência",
      level: "high" as const,
    },
    {
      id: "yellow",
      label: "Risco amarelo",
      count: yellowCount,
      rate: percentOf(yellowCount, Math.max(activeMembers, totalMembers)),
      helper: "Prevenção e acompanhamento",
      level: "medium" as const,
    },
    {
      id: "active",
      label: "Base ativa protegida",
      count: Math.max(activeMembers - redCount - yellowCount, 0),
      rate: percentOf(Math.max(activeMembers - redCount - yellowCount, 0), Math.max(activeMembers, 1)),
      helper: "Alunos sem alerta crítico no recorte atual",
      level: "low" as const,
    },
  ];

  const alertNodes = viewModel.alerts.slice(0, 3).map((alert) => (
    <button
      key={alert.id}
      type="button"
      onClick={() => navigate(alert.href)}
      className="flex w-full items-start justify-between gap-3 rounded-2xl border border-lovable-border/65 bg-lovable-surface/58 px-3 py-3 text-left transition hover:border-lovable-border-strong/70 hover:bg-lovable-surface-soft/62"
    >
      <span>
        <span className={cn("text-sm font-semibold", alert.tone === "danger" ? "text-rose-200" : alert.tone === "warning" ? "text-amber-200" : "text-lovable-ink")}>
          {alert.title}
        </span>
        <span className="mt-1 block text-xs leading-relaxed text-lovable-ink-muted">{alert.description}</span>
      </span>
      <ArrowRight size={14} className="mt-1 shrink-0 text-lovable-ink-muted" />
    </button>
  ));

  return (
    <section className="space-y-5 text-lovable-ink">
      <div className="grid gap-5 xl:grid-cols-[1fr_390px]">
        <div className="space-y-5">
          <DashboardHero
            insight={viewModel.insight}
            redCount={redCount}
            inactiveCount={inactiveCount}
            mrrAtRisk={mrrAtRisk}
          />

          {isDashboardLoading ? (
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              {Array.from({ length: 8 }, (_, index) => (
                <PremiumSkeleton key={index} className="h-[150px]" />
              ))}
            </div>
          ) : (
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              {metricCards.map((card, i) => (
                <MetricCard key={card.label} {...card} className={`stagger-${Math.min(i + 1, 4)}`} />
              ))}
            </div>
          )}

          <IntelligenceMap
            activeMembers={activeMembers}
            checkins7d={checkins7d}
            churnRate={churnRate}
            actionCount={actionRows.length}
            mrr={mrr}
          />
        </div>

        <div className="space-y-4">
          <AIInsightPanel
            summary={viewModel.insight}
            updatedAt="Atualizado a partir dos dados atuais do workspace."
            alerts={alertNodes}
            items={[
              redCount > 0 ? `${redCount} aluno(s) em risco vermelho devem entrar primeiro na fila.` : "Sem risco vermelho ativo no recorte atual.",
              inactiveCount > 0 ? `${inactiveCount} aluno(s) estão há 7+ dias sem treino.` : "Inatividade longa sem alerta relevante.",
              newAtRisk > 0 ? `${newAtRisk} novo(s) aluno(s) entraram em risco na semana.` : "Sem novos alunos em risco na semana.",
            ]}
          />

          <CommandCard>
            <SectionHeader
              eyebrow="Próximas 24h"
              title="Fila de ações sugeridas"
              actions={<Button size="sm" variant="ghost" onClick={() => navigate("/tasks")}>Ver tasks</Button>}
            />
            <ActionQueue
              items={actionRows.slice(0, 4).map((row) => ({
                id: row.id,
                title: row.name,
                subtitle: row.subtitle,
                priority: row.priority,
                owner: row.source === "retention" ? "Recepção" : row.source === "commercial" ? "Comercial" : "Operação",
                status: row.status,
                ctaLabel: "Abrir",
                onClick: () => navigate(row.href),
              }))}
              empty={
                <PremiumEmptyState
                  icon={CheckSquare}
                  title="Nenhuma ação urgente"
                  description="A operação não tem fila crítica no recorte atual."
                  className="min-h-[140px]"
                />
              }
            />
          </CommandCard>
        </div>
      </div>

      <div className="grid gap-5 xl:grid-cols-[1fr_0.92fr]">
        <CommandCard>
          <SectionHeader
            title="Churn e NPS"
            subtitle="Evolução consolidada com leitura de tendência e lacunas explícitas."
            actions={
              <div className="flex items-center gap-1">
                {[
                  { value: "all", label: "Tudo" },
                  { value: "6m", label: "6 meses" },
                  { value: "3m", label: "3 meses" },
                ].map((option) => (
                  <Button
                    key={option.value}
                    size="sm"
                    variant={chartRange === option.value ? "secondary" : "ghost"}
                    onClick={() => setChartRange(option.value as ChartRange)}
                  >
                    {option.label}
                  </Button>
                ))}
              </div>
            }
          />

          <div className="h-80">
            {churn.isLoading || retention.isLoading ? (
              <PremiumSkeleton className="h-full w-full" />
            ) : chartData.length === 0 || !retentionChartState.hasMeaningfulValues ? (
              <PremiumEmptyState
                icon={BarChart3}
                title="Sem base histórica suficiente"
                description="Assim que houver NPS, check-ins e cancelamentos registrados, a curva de tendência aparece aqui."
                className="h-full"
              />
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData}>
                  <defs>
                    <linearGradient id="commandNpsGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="hsl(var(--lovable-primary))" stopOpacity={0.42} />
                      <stop offset="95%" stopColor="hsl(var(--lovable-primary))" stopOpacity={0.02} />
                    </linearGradient>
                    <linearGradient id="commandChurnGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="hsl(var(--lovable-danger))" stopOpacity={0.28} />
                      <stop offset="95%" stopColor="hsl(var(--lovable-danger))" stopOpacity={0.02} />
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
                      border: "1px solid rgba(255,255,255,0.08)",
                      background: "rgba(14,16,24,0.97)",
                      color: "hsl(var(--lovable-ink))",
                      padding: "10px 14px",
                      boxShadow: "0 8px 32px rgba(0,0,0,0.48)",
                    }}
                    labelStyle={{ color: "hsl(var(--lovable-ink-muted))", fontSize: "11px", marginBottom: "4px" }}
                    itemStyle={{ fontFamily: "'JetBrains Mono',monospace", fontSize: "13px", fontWeight: 600 }}
                    cursor={{ stroke: "rgba(255,255,255,0.10)", strokeDasharray: "3 3" }}
                    formatter={(value, key) => {
                      const parsedValue = typeof value === "number" ? value : Number(value);
                      if (!Number.isFinite(parsedValue)) return ["-", String(key)];
                      if (key === "churn_rate") return [`${parsedValue.toFixed(2)}%`, "Churn"];
                      return [parsedValue.toFixed(2), "NPS médio"];
                    }}
                    labelFormatter={(label) => formatDateLabel(String(label))}
                  />
                  <Area
                    type="monotone"
                    dataKey="nps_avg"
                    name="NPS médio"
                    stroke="hsl(var(--lovable-primary))"
                    fill="url(#commandNpsGradient)"
                    strokeWidth={2.5}
                    connectNulls
                  />
                  <Area
                    type="monotone"
                    dataKey="churn_rate"
                    name="Churn"
                    stroke="hsl(var(--lovable-danger))"
                    fill="url(#commandChurnGradient)"
                    strokeWidth={2.1}
                    connectNulls
                  />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </div>
        </CommandCard>

        <CommandCard>
          <SectionHeader
            title="Matriz de risco"
            subtitle="Segmentos prioritários para decisão de retenção."
            actions={<StatusPill tone="retention">Retenção</StatusPill>}
          />
          <RiskMatrix segments={riskSegments} />
        </CommandCard>
      </div>

      {!executive.isLoading && !viewModel.hasData ? (
        <CommandCard variant="warning">
          <PremiumEmptyState
            icon={Zap}
            title="Base operacional ainda insuficiente"
            description="Importe membros, check-ins e eventos financeiros para ativar o Command Center com leitura completa."
            action={<Button onClick={() => navigate("/imports")}>Importar dados agora</Button>}
          />
        </CommandCard>
      ) : null}
    </section>
  );
}
