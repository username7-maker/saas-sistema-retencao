import { LineSeriesChart } from "../../components/charts/LineSeriesChart";
import { LoadingPanel } from "../../components/common/LoadingPanel";
import { StatCard } from "../../components/common/StatCard";
import { useRetentionDashboard } from "../../hooks/useDashboard";

export function RetentionDashboardPage() {
  const query = useRetentionDashboard();

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
    </section>
  );
}
