import { useNavigate } from "react-router-dom";
import { AlertTriangle, ArrowRight, BarChart3, Users, Wallet, Zap } from "lucide-react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import {
  useChurnDashboard,
  useCommercialDashboard,
  useExecutiveDashboard,
  useOperationalDashboard,
  useRetentionDashboard,
} from "../../hooks/useDashboard";
import { AiInsightCard } from "../../components/common/AiInsightCard";
import { DashboardActions } from "../../components/common/DashboardActions";
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  ChartCard,
  Skeleton,
} from "../../components/ui2";
import { buildLovableDashboardViewModel } from "./dashboardAdapters";

function currency(value: number): string {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
    maximumFractionDigits: 0,
  }).format(value);
}

function compactNumber(value: number): string {
  return new Intl.NumberFormat("pt-BR", { notation: "compact", maximumFractionDigits: 1 }).format(value);
}

function CardSkeleton() {
  return (
    <Card>
      <CardHeader>
        <Skeleton className="h-3 w-36" />
        <Skeleton className="h-9 w-24" />
      </CardHeader>
    </Card>
  );
}

export function DashboardLovable() {
  const navigate = useNavigate();
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

  const cardsLoading = executive.isLoading || commercial.isLoading || operational.isLoading || retention.isLoading;
  const alertsLoading = commercial.isLoading || operational.isLoading || retention.isLoading;
  const chartLoading = churn.isLoading || retention.isLoading;
  const quickActionsLoading = commercial.isLoading || operational.isLoading || retention.isLoading;
  const insightLoading = executive.isLoading || commercial.isLoading || operational.isLoading || retention.isLoading || churn.isLoading;

  return (
    <section className="space-y-6">
      <header className="flex flex-col gap-4 rounded-2xl border border-lovable-border bg-lovable-surface p-5 shadow-lovable lg:flex-row lg:items-center lg:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.2em] text-lovable-ink-muted">Dashboard Inteligente</p>
          <p className="text-sm font-semibold text-lovable-primary">Dashboard Executivo</p>
          <h2 className="font-display text-3xl font-bold text-lovable-ink">Visao Executiva Integrada</h2>
          <p className="mt-1 text-sm text-lovable-ink-muted">Retencao, comercial e operacao reunidos em um painel de acao.</p>
        </div>
        <DashboardActions dashboard="executive" showMonthlyDispatch />
      </header>

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
            <Card>
              <CardHeader>
                <CardDescription className="flex items-center gap-2 uppercase tracking-wider">
                  <Wallet size={14} /> Receita mensal
                </CardDescription>
                <CardTitle className="text-3xl">{currency(viewModel.cards.revenue)}</CardTitle>
              </CardHeader>
            </Card>
            <Card>
              <CardHeader>
                <CardDescription className="flex items-center gap-2 uppercase tracking-wider">
                  <Users size={14} /> Leads no pipeline
                </CardDescription>
                <CardTitle className="text-3xl">{compactNumber(viewModel.cards.leads)}</CardTitle>
              </CardHeader>
            </Card>
            <Card>
              <CardHeader>
                <CardDescription className="flex items-center gap-2 uppercase tracking-wider">
                  <Zap size={14} /> Check-ins em tempo real
                </CardDescription>
                <CardTitle className="text-3xl">{compactNumber(viewModel.cards.checkins)}</CardTitle>
              </CardHeader>
            </Card>
            <Card>
              <CardHeader>
                <CardDescription className="flex items-center gap-2 uppercase tracking-wider">
                  <AlertTriangle size={14} /> Risco alto
                </CardDescription>
                <CardTitle className="text-3xl">{compactNumber(viewModel.cards.highRiskMembers)}</CardTitle>
              </CardHeader>
            </Card>
          </>
        )}
      </div>

      <div className="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
        <Card className="border-l-4 border-l-lovable-warning">
          <CardHeader>
            <CardTitle className="text-xl">Alertas inteligentes</CardTitle>
            <CardDescription>Acione a equipe com base nos eventos criticos do dia.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {alertsLoading ? (
              <>
                <Skeleton className="h-16 w-full rounded-xl" />
                <Skeleton className="h-16 w-full rounded-xl" />
                <Skeleton className="h-16 w-full rounded-xl" />
              </>
            ) : viewModel.alerts.length === 0 ? (
              <div className="rounded-xl border border-dashed border-lovable-border p-4 text-sm text-lovable-ink-muted">
                Nenhum alerta critico no momento.
              </div>
            ) : (
              viewModel.alerts.map((alert) => (
                <button
                  key={alert.id}
                  type="button"
                  onClick={() => navigate(alert.href)}
                  className="w-full rounded-xl border border-lovable-border bg-lovable-surface-soft p-3 text-left transition hover:border-lovable-border-strong hover:bg-lovable-primary-soft/40"
                >
                  <div className="mb-2 flex items-center justify-between gap-3">
                    <p className="font-semibold text-lovable-ink">{alert.title}</p>
                    <Badge variant={alert.tone === "danger" ? "danger" : alert.tone === "warning" ? "warning" : "neutral"}>
                      {alert.tone === "danger" ? "alta" : alert.tone === "warning" ? "media" : "informativo"}
                    </Badge>
                  </div>
                  <p className="text-sm text-lovable-ink-muted">{alert.description}</p>
                </button>
              ))
            )}
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-lovable-surface to-lovable-primary-soft/35">
          <CardHeader>
            <CardTitle className="text-xl">Insight da semana</CardTitle>
            <CardDescription>Resumo tatico gerado a partir dos dados consolidados.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {insightLoading ? (
              <>
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-5/6" />
                <Skeleton className="h-10 w-full rounded-xl" />
              </>
            ) : (
              <>
                <p className="text-sm leading-relaxed text-lovable-ink">{viewModel.insight}</p>
                <Button variant="secondary" className="w-full justify-between" onClick={() => navigate("/dashboard/retention")}>
                  Ver plano de retencao
                  <ArrowRight size={15} />
                </Button>
              </>
            )}
            <AiInsightCard dashboard="executive" />
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-[1.35fr_0.65fr]">
        <ChartCard title="Evolucao de Retencao" description="Comparativo de churn mensal e NPS medio">
          {chartLoading ? (
            <div className="space-y-2 p-2">
              <Skeleton className="h-56 w-full rounded-xl" />
            </div>
          ) : viewModel.retentionChart.length === 0 ? (
            <div className="flex h-full items-center justify-center rounded-xl border border-dashed border-lovable-border text-sm text-lovable-ink-muted">
              Sem dados suficientes ainda. Importe historico para visualizar tendencia.
            </div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={viewModel.retentionChart}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--lovable-border))" />
                <XAxis dataKey="month" stroke="hsl(var(--lovable-ink-muted))" />
                <YAxis yAxisId="left" stroke="hsl(var(--lovable-danger))" />
                <YAxis yAxisId="right" orientation="right" stroke="hsl(var(--lovable-primary))" />
                <Tooltip />
                <Legend />
                <Line yAxisId="left" type="monotone" dataKey="churn_rate" name="Churn (%)" stroke="hsl(var(--lovable-danger))" strokeWidth={2.5} />
                <Line yAxisId="right" type="monotone" dataKey="nps_avg" name="NPS Medio" stroke="hsl(var(--lovable-primary))" strokeWidth={2.5} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </ChartCard>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-xl">
              <BarChart3 size={18} />
              Acoes rapidas
            </CardTitle>
            <CardDescription>Atalhos para executar o que mais impacta receita e retencao.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            {quickActionsLoading
              ? [0, 1, 2, 3].map((item) => <Skeleton key={item} className="h-14 w-full rounded-xl" />)
              : viewModel.quickActions.map((action) => (
                  <button
                    key={action.id}
                    type="button"
                    onClick={() => navigate(action.href)}
                    className="w-full rounded-xl border border-lovable-border bg-lovable-surface-soft px-3 py-3 text-left transition hover:border-lovable-border-strong hover:bg-lovable-primary-soft/45"
                  >
                    <p className="text-sm font-semibold text-lovable-ink">{action.label}</p>
                    <p className="text-xs text-lovable-ink-muted">{action.description}</p>
                  </button>
                ))}
          </CardContent>
        </Card>
      </div>

      {!insightLoading && !viewModel.hasData ? (
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-start gap-3 py-6">
            <p className="text-sm text-lovable-ink-muted">
              Sem dados suficientes ainda para preencher o dashboard. Envie os CSVs de membros e check-ins para ativar o painel.
            </p>
            <Button onClick={() => navigate("/imports")}>Importar dados agora</Button>
          </CardContent>
        </Card>
      ) : null}
    </section>
  );
}
