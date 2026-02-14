import { useMemo } from "react";

import { BarSeriesChart } from "../../components/charts/BarSeriesChart";
import { LoadingPanel } from "../../components/common/LoadingPanel";
import { StatCard } from "../../components/common/StatCard";
import { useOperationalDashboard } from "../../hooks/useDashboard";

const weekdays = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sab"];

export function OperationalDashboardPage() {
  const query = useOperationalDashboard();

  const heatmapData = useMemo(
    () =>
      (query.data?.heatmap ?? []).map((point) => ({
        slot: `${weekdays[point.weekday]} ${String(point.hour_bucket).padStart(2, "0")}h`,
        total: point.total_checkins,
      })),
    [query.data],
  );

  if (query.isLoading) {
    return <LoadingPanel text="Carregando dashboard operacional..." />;
  }

  if (!query.data) {
    return <LoadingPanel text="Sem dados operacionais disponiveis." />;
  }

  return (
    <section className="space-y-6">
      <header>
        <h2 className="font-heading text-3xl font-bold text-slate-900">Dashboard Operacional</h2>
        <p className="text-sm text-slate-500">Check-ins em tempo real, heatmap por horario e inativos 7+ dias.</p>
      </header>

      <div className="grid gap-4 md:grid-cols-2">
        <StatCard label="Check-ins ultima hora" value={String(query.data.realtime_checkins)} tone="success" />
        <StatCard label="Inativos 7+ dias" value={String(query.data.inactive_7d_total)} tone="warning" />
      </div>

      <BarSeriesChart data={heatmapData} xKey="slot" yKey="total" />

      <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-panel">
        <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-600">Lista 7+ dias sem treino</h3>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="text-left text-xs uppercase tracking-wider text-slate-500">
              <tr>
                <th className="px-2 py-2">Aluno</th>
                <th className="px-2 py-2">Risco</th>
                <th className="px-2 py-2">Ultimo check-in</th>
              </tr>
            </thead>
            <tbody>
              {query.data.inactive_7d_items.map((member) => (
                <tr key={member.id} className="border-t border-slate-100">
                  <td className="px-2 py-2 font-medium text-slate-700">{member.full_name}</td>
                  <td className="px-2 py-2 uppercase text-slate-600">{member.risk_level}</td>
                  <td className="px-2 py-2 text-slate-500">{member.last_checkin_at ? new Date(member.last_checkin_at).toLocaleString() : "Sem registro"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </section>
  );
}
