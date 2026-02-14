import { LineSeriesChart } from "../../components/charts/LineSeriesChart";
import { LoadingPanel } from "../../components/common/LoadingPanel";
import { StatCard } from "../../components/common/StatCard";
import { useFinancialDashboard } from "../../hooks/useDashboard";

export function FinancialDashboardPage() {
  const query = useFinancialDashboard();

  if (query.isLoading) {
    return <LoadingPanel text="Carregando dashboard financeiro..." />;
  }

  if (!query.data) {
    return <LoadingPanel text="Sem dados financeiros." />;
  }

  return (
    <section className="space-y-6">
      <header>
        <h2 className="font-heading text-3xl font-bold text-slate-900">Dashboard Financeiro</h2>
        <p className="text-sm text-slate-500">Receita mensal, inadimplencia e projecao 3/6/12 meses.</p>
      </header>

      <div className="grid gap-4 md:grid-cols-2">
        <StatCard label="Inadimplencia" value={`${query.data.delinquency_rate.toFixed(2)}%`} tone="danger" />
        <StatCard
          label="Projecao 12 meses"
          value={`R$ ${query.data.projections.find((p) => p.horizon_months === 12)?.projected_revenue.toFixed(2) ?? "0.00"}`}
          tone="success"
        />
      </div>

      <LineSeriesChart data={query.data.monthly_revenue} xKey="month" yKey="value" />

      <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-panel">
        <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-600">Projecoes inteligentes</h3>
        <div className="grid gap-3 md:grid-cols-3">
          {query.data.projections.map((projection) => (
            <article key={projection.horizon_months} className="rounded-xl border border-slate-200 bg-slate-50 p-3">
              <p className="text-xs uppercase tracking-wider text-slate-500">Horizonte</p>
              <p className="text-lg font-semibold text-slate-700">{projection.horizon_months} meses</p>
              <p className="text-sm text-brand-700">R$ {projection.projected_revenue.toFixed(2)}</p>
            </article>
          ))}
        </div>
      </section>
    </section>
  );
}
