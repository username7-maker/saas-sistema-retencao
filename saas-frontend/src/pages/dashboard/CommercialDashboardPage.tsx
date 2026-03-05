import { useMemo } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { AiInsightCard } from "../../components/common/AiInsightCard";
import { DashboardActions } from "../../components/common/DashboardActions";
import { LoadingPanel } from "../../components/common/LoadingPanel";
import { QuickLeadActions } from "../../components/common/QuickLeadActions";
import { StatCard } from "../../components/common/StatCard";
import { Badge } from "../../components/ui2";
import { useCommercialDashboard } from "../../hooks/useDashboard";

const STAGE_LABELS: Record<string, string> = {
  new: "Novo",
  contacted: "Contactado",
  proposal: "Proposta",
  won: "Fechado",
  lost: "Perdido",
};

function stageColor(stage: string): string {
  if (stage === "won") return "hsl(var(--lovable-success))";
  if (stage === "lost") return "hsl(var(--lovable-danger))";
  if (stage === "proposal") return "hsl(var(--lovable-warning))";
  return "hsl(var(--lovable-primary))";
}

function daysSince(isoDate: string | null | undefined): number | null {
  if (!isoDate) return null;
  return Math.floor((Date.now() - new Date(isoDate).getTime()) / 86_400_000);
}

export function CommercialDashboardPage() {
  const queryClient = useQueryClient();
  const query = useCommercialDashboard();

  const pipelineData = useMemo(() => {
    if (!query.data) return [];
    return Object.entries(query.data.pipeline).map(([stage, total]) => ({
      stage,
      label: STAGE_LABELS[stage] ?? stage,
      total,
    }));
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
          <h2 className="font-heading text-3xl font-bold text-lovable-ink">Dashboard Comercial</h2>
          <p className="text-sm text-lovable-ink-muted">Pipeline, conversão por origem e CAC.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <DashboardActions dashboard="commercial" />
          <Link
            to="/crm"
            className="rounded-full bg-lovable-primary px-4 py-2 text-xs font-semibold uppercase tracking-wider text-white hover:opacity-90"
          >
            Abrir CRM Kanban
          </Link>
        </div>
      </header>

      <AiInsightCard dashboard="commercial" />

      <div className="grid gap-4 md:grid-cols-3">
        <StatCard label="CAC" value={`R$ ${query.data.cac.toFixed(2)}`} tone="warning" />
        <StatCard label="Leads em proposta" value={String(query.data.pipeline.proposal ?? 0)} tone="neutral" />
        <StatCard label="Fechados" value={String(query.data.pipeline.won ?? 0)} tone="success" />
      </div>

      {/* Pipeline chart — bars colored by stage */}
      <div className="h-72 w-full rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
        <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">Pipeline por estágio</p>
        <ResponsiveContainer width="100%" height="90%">
          <BarChart data={pipelineData}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--lovable-border))" />
            <XAxis dataKey="label" stroke="hsl(var(--lovable-ink-muted))" tick={{ fontSize: 11 }} />
            <YAxis stroke="hsl(var(--lovable-ink-muted))" />
            <Tooltip
              contentStyle={{
                background: "hsl(var(--lovable-surface))",
                border: "1px solid hsl(var(--lovable-border))",
                borderRadius: "0.75rem",
              }}
              labelStyle={{ color: "hsl(var(--lovable-ink-muted))", fontSize: 12 }}
              itemStyle={{ color: "hsl(var(--lovable-ink))", fontWeight: 600 }}
            />
            <Bar dataKey="total" radius={[8, 8, 0, 0]}>
              {pipelineData.map((entry) => (
                <Cell key={entry.stage} fill={stageColor(entry.stage)} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      <section className="rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
        <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-lovable-ink-muted">Conversão por origem</h3>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="text-left text-xs uppercase tracking-wider text-lovable-ink-muted">
              <tr>
                <th className="px-2 py-2">Origem</th>
                <th className="px-2 py-2">Total</th>
                <th className="px-2 py-2">Fechados</th>
                <th className="px-2 py-2">Conversão</th>
              </tr>
            </thead>
            <tbody>
              {query.data.conversion_by_source.map((row) => (
                <tr key={row.source} className="border-t border-lovable-border">
                  <td className="px-2 py-2 font-medium text-lovable-ink">{row.source}</td>
                  <td className="px-2 py-2 text-lovable-ink-muted">{row.total}</td>
                  <td className="px-2 py-2 text-lovable-ink-muted">{row.won}</td>
                  <td className="px-2 py-2 font-medium text-lovable-ink">{row.conversion_rate}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="rounded-2xl border border-lovable-warning/30 bg-lovable-surface p-4 shadow-panel">
        <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-lovable-warning">
          Leads parados 3+ dias ({query.data.stale_leads_total})
        </h3>
        {query.data.stale_leads.length === 0 ? (
          <p className="text-sm text-lovable-ink-muted">Nenhum lead parado no momento.</p>
        ) : (
          <ul className="space-y-3">
            {query.data.stale_leads.map((lead) => {
              const dias = daysSince(lead.last_contact_at);
              return (
                <li key={lead.id} className="rounded-lg border border-lovable-border px-3 py-3 text-sm">
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0 flex-1">
                      <p className="font-medium text-lovable-ink">{lead.full_name}</p>
                      <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-lovable-ink-muted">
                        <span>Estágio: {STAGE_LABELS[lead.stage] ?? lead.stage}</span>
                        <span>Origem: {lead.source}</span>
                        {dias !== null && (
                          <Badge variant={dias > 7 ? "danger" : "warning"}>
                            {dias}d sem contato
                          </Badge>
                        )}
                      </div>
                    </div>
                  </div>
                  <div className="mt-2">
                    <QuickLeadActions lead={lead} onActionComplete={handleActionComplete} />
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </section>
    </section>
  );
}
