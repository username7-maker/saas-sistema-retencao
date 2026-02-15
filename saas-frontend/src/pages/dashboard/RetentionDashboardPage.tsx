import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { LineSeriesChart } from "../../components/charts/LineSeriesChart";
import { LoadingPanel } from "../../components/common/LoadingPanel";
import { StatCard } from "../../components/common/StatCard";
import { useRetentionDashboard } from "../../hooks/useDashboard";
import { riskAlertService } from "../../services/riskAlertService";

export function RetentionDashboardPage() {
  const queryClient = useQueryClient();
  const query = useRetentionDashboard();
  const alertsQuery = useQuery({
    queryKey: ["risk-alerts", "unresolved-red"],
    queryFn: () => riskAlertService.listUnresolved("red"),
    staleTime: 60 * 1000,
  });
  const resolveMutation = useMutation({
    mutationFn: (alertId: string) => riskAlertService.resolve(alertId, "Resolvido no dashboard de retencao"),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["risk-alerts", "unresolved-red"] });
      void queryClient.invalidateQueries({ queryKey: ["dashboard", "retention"] });
    },
  });

  if (query.isLoading) {
    return <LoadingPanel text="Carregando dashboard de retencao..." />;
  }

  if (!query.data) {
    return <LoadingPanel text="Sem dados de retencao." />;
  }

  return (
    <section className="space-y-6">
      <header>
        <h2 className="font-heading text-3xl font-bold text-slate-900">Dashboard de Retencao</h2>
        <p className="text-sm text-slate-500">Lista de risco vermelho/amarelo e evolucao NPS.</p>
      </header>

      <div className="grid gap-4 md:grid-cols-2">
        <StatCard label="Risco Vermelho" value={String(query.data.red.total)} tone="danger" />
        <StatCard label="Risco Amarelo" value={String(query.data.yellow.total)} tone="warning" />
      </div>

      <LineSeriesChart data={query.data.nps_trend} xKey="month" yKey="average_score" />

      <div className="grid gap-4 xl:grid-cols-2">
        <section className="rounded-2xl border border-rose-200 bg-white p-4 shadow-panel">
          <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-rose-700">Alunos em vermelho</h3>
          <ul className="space-y-2">
            {query.data.red.items.map((member) => (
              <li key={member.id} className="rounded-lg border border-slate-200 px-3 py-2 text-sm">
                <p className="font-medium text-slate-700">{member.full_name}</p>
                <p className="text-xs text-slate-500">Score: {member.risk_score}</p>
              </li>
            ))}
          </ul>
        </section>

        <section className="rounded-2xl border border-amber-200 bg-white p-4 shadow-panel">
          <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-amber-700">Alunos em amarelo</h3>
          <ul className="space-y-2">
            {query.data.yellow.items.map((member) => (
              <li key={member.id} className="rounded-lg border border-slate-200 px-3 py-2 text-sm">
                <p className="font-medium text-slate-700">{member.full_name}</p>
                <p className="text-xs text-slate-500">Score: {member.risk_score}</p>
              </li>
            ))}
          </ul>
        </section>
      </div>

      <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-panel">
        <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-600">Risk Alerts Ativos (Vermelho)</h3>
        {alertsQuery.isLoading ? (
          <p className="text-sm text-slate-500">Carregando alertas...</p>
        ) : (
          <div className="space-y-2">
            {(alertsQuery.data?.items ?? []).map((alert) => (
              <article key={alert.id} className="rounded-lg border border-slate-200 p-3">
                <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                  <div>
                    <p className="text-sm font-semibold text-slate-700">Alerta {alert.id.slice(0, 8)} | Score {alert.score}</p>
                    <p className="text-xs text-slate-500">
                      Historico de acoes: {alert.action_history.length} | Criado em {new Date(alert.created_at).toLocaleString()}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => resolveMutation.mutate(alert.id)}
                    disabled={resolveMutation.isPending}
                    className="rounded-full bg-emerald-600 px-3 py-1 text-xs font-semibold uppercase tracking-wider text-white hover:bg-emerald-700 disabled:opacity-60"
                  >
                    Marcar resolvido
                  </button>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
    </section>
  );
}
