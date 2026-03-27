import { LineSeriesChart } from "../../components/charts/LineSeriesChart";
import { getChartSeriesState } from "../../components/charts/chartState";
import { EmptyState } from "../../components/ui";
import { AiInsightCard } from "../../components/common/AiInsightCard";
import { DashboardActions } from "../../components/common/DashboardActions";
import { LoadingPanel } from "../../components/common/LoadingPanel";
import { StatCard } from "../../components/common/StatCard";
import { useFinancialDashboard } from "../../hooks/useDashboard";

const BRL = (value: number) =>
  new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 }).format(value);

export function FinancialDashboardPage() {
  const query = useFinancialDashboard();

  if (query.isLoading) {
    return <LoadingPanel text="Carregando dashboard financeiro..." />;
  }

  if (!query.data) {
    return (
      <section className="space-y-6">
        <header>
          <h2 className="font-heading text-3xl font-bold text-lovable-ink">Dashboard Financeiro</h2>
          <p className="text-sm text-lovable-ink-muted">Receita mensal, inadimplencia e projecao 3/6/12 meses.</p>
        </header>
        <div className="rounded-2xl border border-dashed border-lovable-border bg-lovable-surface p-8 text-center text-sm text-lovable-ink-muted">
          Sem dados financeiros disponiveis. Importe historico de receita para ativar este painel.
        </div>
      </section>
    );
  }

  const proj12 = query.data.projections.find((projection) => projection.horizon_months === 12);
  const revenueState = getChartSeriesState(query.data.monthly_revenue, ["value"]);
  const hasFinancialBase = revenueState.hasMeaningfulValues;

  return (
    <section className="space-y-6">
      <header className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
        <div>
          <h2 className="font-heading text-3xl font-bold text-lovable-ink">Dashboard Financeiro</h2>
          <p className="text-sm text-lovable-ink-muted">Receita mensal, inadimplencia e projecao 3/6/12 meses.</p>
        </div>
        <DashboardActions dashboard="financial" />
      </header>

      <AiInsightCard dashboard="financial" />

      <div className="grid gap-4 md:grid-cols-2">
        <StatCard label="Inadimplencia" value={`${query.data.delinquency_rate.toFixed(1)}%`} tone="danger" />
        <StatCard
          label="Projecao 12 meses"
          value={proj12 && hasFinancialBase ? BRL(proj12.projected_revenue) : "Sem base"}
          tone="success"
        />
      </div>

      {hasFinancialBase ? (
        <LineSeriesChart data={query.data.monthly_revenue} xKey="month" yKey="value" />
      ) : (
        <section className="rounded-2xl border border-dashed border-lovable-border bg-lovable-surface p-8 shadow-panel">
          <EmptyState
            title="Receita historica ainda sem base util"
            description="As mensalidades e recebimentos ainda nao geraram uma serie financeira confiavel. Assim que a base financeira for consolidada, o grafico passa a mostrar a curva mensal."
          />
        </section>
      )}

      <section className="rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
        <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-lovable-ink-muted">Projecoes inteligentes</h3>
        <div className="grid gap-3 md:grid-cols-3">
          {query.data.projections.map((projection) => (
            <article
              key={projection.horizon_months}
              className="rounded-xl border border-lovable-border bg-lovable-surface-soft p-3"
            >
              <p className="text-xs uppercase tracking-wider text-lovable-ink-muted">Horizonte</p>
              <p className="text-lg font-semibold text-lovable-ink">{projection.horizon_months} meses</p>
              <p className="text-sm font-medium text-lovable-primary">
                {hasFinancialBase ? BRL(projection.projected_revenue) : "Sem base"}
              </p>
            </article>
          ))}
        </div>
      </section>
    </section>
  );
}
