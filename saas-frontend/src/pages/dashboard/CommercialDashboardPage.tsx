import { useMemo } from "react";
import { Link } from "react-router-dom";

import { BarSeriesChart } from "../../components/charts/BarSeriesChart";
import { LoadingPanel } from "../../components/common/LoadingPanel";
import { StatCard } from "../../components/common/StatCard";
import { useCommercialDashboard } from "../../hooks/useDashboard";

export function CommercialDashboardPage() {
  const query = useCommercialDashboard();

  const pipelineData = useMemo(() => {
    if (!query.data) return [];
    return Object.entries(query.data.pipeline).map(([stage, total]) => ({ stage, total }));
  }, [query.data]);

  if (query.isLoading) {
    return <LoadingPanel text="Carregando dashboard comercial..." />;
  }

  if (!query.data) {
    return <LoadingPanel text="Sem dados comerciais." />;
  }

  return (
    <section className="space-y-6">
      <header className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
        <div>
          <h2 className="font-heading text-3xl font-bold text-slate-900">Dashboard Comercial</h2>
          <p className="text-sm text-slate-500">Pipeline, conversao por origem e CAC.</p>
        </div>
        <Link to="/crm" className="rounded-full bg-brand-500 px-4 py-2 text-xs font-semibold uppercase tracking-wider text-white hover:bg-brand-700">
          Abrir CRM Kanban
        </Link>
      </header>

      <div className="grid gap-4 md:grid-cols-3">
        <StatCard label="CAC" value={`R$ ${query.data.cac.toFixed(2)}`} tone="warning" />
        <StatCard label="Leads em proposta" value={String(query.data.pipeline.proposal ?? 0)} tone="neutral" />
        <StatCard label="Fechados" value={String(query.data.pipeline.won ?? 0)} tone="success" />
      </div>

      <BarSeriesChart data={pipelineData} xKey="stage" yKey="total" />

      <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-panel">
        <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-600">Conversao por origem</h3>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="text-left text-xs uppercase tracking-wider text-slate-500">
              <tr>
                <th className="px-2 py-2">Origem</th>
                <th className="px-2 py-2">Total</th>
                <th className="px-2 py-2">Fechados</th>
                <th className="px-2 py-2">Conversao</th>
              </tr>
            </thead>
            <tbody>
              {query.data.conversion_by_source.map((row) => (
                <tr key={row.source} className="border-t border-slate-100">
                  <td className="px-2 py-2 font-medium text-slate-700">{row.source}</td>
                  <td className="px-2 py-2">{row.total}</td>
                  <td className="px-2 py-2">{row.won}</td>
                  <td className="px-2 py-2">{row.conversion_rate}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </section>
  );
}
