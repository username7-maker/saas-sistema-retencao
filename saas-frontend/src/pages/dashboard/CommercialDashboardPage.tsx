import { useMemo } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { BarSeriesChart } from "../../components/charts/BarSeriesChart";
import { DashboardActions } from "../../components/common/DashboardActions";
import { LoadingPanel } from "../../components/common/LoadingPanel";
import { QuickLeadActions } from "../../components/common/QuickLeadActions";
import { StatCard } from "../../components/common/StatCard";
import { useCommercialDashboard } from "../../hooks/useDashboard";

export function CommercialDashboardPage() {
  const queryClient = useQueryClient();
  const query = useCommercialDashboard();

  const pipelineData = useMemo(() => {
    if (!query.data) return [];
    return Object.entries(query.data.pipeline).map(([stage, total]) => ({ stage, total }));
  }, [query.data]);

  const handleActionComplete = () => {
    void queryClient.invalidateQueries({ queryKey: ["dashboard", "commercial"] });
  };

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
        <div className="flex flex-wrap gap-2">
          <DashboardActions dashboard="commercial" />
          <Link to="/crm" className="rounded-full bg-brand-500 px-4 py-2 text-xs font-semibold uppercase tracking-wider text-white hover:bg-brand-700">
            Abrir CRM Kanban
          </Link>
        </div>
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

      <section className="rounded-2xl border border-amber-200 bg-white p-4 shadow-panel">
        <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-amber-700">
          Leads parados 3+ dias ({query.data.stale_leads_total})
        </h3>
        {query.data.stale_leads.length === 0 ? (
          <p className="text-sm text-slate-500">Nenhum lead parado no momento.</p>
        ) : (
          <ul className="space-y-3">
            {query.data.stale_leads.map((lead) => (
              <li key={lead.id} className="rounded-lg border border-slate-200 px-3 py-3 text-sm">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="font-medium text-slate-700">{lead.full_name}</p>
                    <p className="text-xs text-slate-500">
                      Estagio: {lead.stage} | Origem: {lead.source}
                      {lead.last_contact_at && (
                        <> | Ultimo contato: {new Date(lead.last_contact_at).toLocaleDateString()}</>
                      )}
                    </p>
                  </div>
                </div>
                <div className="mt-2">
                  <QuickLeadActions lead={lead} onActionComplete={handleActionComplete} />
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </section>
  );
}
