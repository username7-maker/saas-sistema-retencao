import { PieRiskChart } from "../../components/charts/PieRiskChart";
import { LineSeriesChart } from "../../components/charts/LineSeriesChart";
import { LoadingPanel } from "../../components/common/LoadingPanel";
import { StatCard } from "../../components/common/StatCard";
import {
  useChurnDashboard,
  useExecutiveDashboard,
  useGrowthDashboard,
  useLtvDashboard,
  useMrrDashboard,
} from "../../hooks/useDashboard";

export function ExecutiveDashboardPage() {
  const executive = useExecutiveDashboard();
  const mrr = useMrrDashboard();
  const churn = useChurnDashboard();
  const ltv = useLtvDashboard();
  const growth = useGrowthDashboard();

  if (executive.isLoading || mrr.isLoading || churn.isLoading || ltv.isLoading || growth.isLoading) {
    return <LoadingPanel text="Carregando dashboard executivo..." />;
  }

  if (!executive.data || !mrr.data || !churn.data || !ltv.data || !growth.data) {
    return <LoadingPanel text="Nao foi possivel carregar dados executivos." />;
  }

  const riskData = [
    { name: "Green", value: executive.data.risk_distribution.green },
    { name: "Yellow", value: executive.data.risk_distribution.yellow },
    { name: "Red", value: executive.data.risk_distribution.red },
  ];

  return (
    <section className="space-y-6">
      <header>
        <h2 className="font-heading text-3xl font-bold text-slate-900">Dashboard Executivo</h2>
        <p className="text-sm text-slate-500">Visao consolidada de MRR, churn e saude da base.</p>
      </header>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        <StatCard label="Total de Alunos" value={String(executive.data.total_members)} tone="neutral" />
        <StatCard label="Ativos" value={String(executive.data.active_members)} tone="success" />
        <StatCard label="MRR" value={`R$ ${executive.data.mrr.toFixed(2)}`} tone="neutral" />
        <StatCard label="Churn" value={`${executive.data.churn_rate.toFixed(2)}%`} tone="danger" />
        <StatCard label="NPS Medio" value={executive.data.nps_avg.toFixed(2)} tone="warning" />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <LineSeriesChart data={mrr.data} xKey="month" yKey="value" />
        <PieRiskChart data={riskData} />
        <LineSeriesChart data={churn.data} xKey="month" yKey="churn_rate" stroke="#e11d48" />
        <LineSeriesChart data={ltv.data} xKey="month" yKey="ltv" stroke="#f59e0b" />
        <LineSeriesChart data={growth.data} xKey="month" yKey="growth_mom" stroke="#0f766e" />
      </div>
    </section>
  );
}
