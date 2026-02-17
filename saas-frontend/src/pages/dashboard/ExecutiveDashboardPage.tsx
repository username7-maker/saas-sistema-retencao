import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

import { PieRiskChart } from "../../components/charts/PieRiskChart";
import { LineSeriesChart } from "../../components/charts/LineSeriesChart";
import { AiInsightCard } from "../../components/common/AiInsightCard";
import { DashboardActions } from "../../components/common/DashboardActions";
import { LoadingPanel } from "../../components/common/LoadingPanel";
import { DashboardSkeleton } from "../../components/common/SkeletonCard";
import { StatCard } from "../../components/common/StatCard";
import {
  useChurnDashboard,
  useExecutiveDashboard,
  useGrowthDashboard,
  useLtvDashboard,
  useMrrDashboard,
} from "../../hooks/useDashboard";
import { goalService } from "../../services/goalService";

function computeTrend(data: { value?: number; churn_rate?: number; ltv?: number; growth_mom?: number }[], key: string): number {
  if (data.length < 2) return 0;
  const current = (data[data.length - 1] as Record<string, number>)[key] ?? 0;
  const previous = (data[data.length - 2] as Record<string, number>)[key] ?? 0;
  if (previous === 0) return 0;
  return ((current - previous) / Math.abs(previous)) * 100;
}

export function ExecutiveDashboardPage() {
  const navigate = useNavigate();
  const executive = useExecutiveDashboard();
  const mrr = useMrrDashboard();
  const churn = useChurnDashboard();
  const ltv = useLtvDashboard();
  const growth = useGrowthDashboard();
  const goalsProgress = useQuery({
    queryKey: ["goals", "progress", "executive-widget"],
    queryFn: () => goalService.progress(true),
    staleTime: 60 * 1000,
  });

  if (executive.isLoading || mrr.isLoading || churn.isLoading || ltv.isLoading || growth.isLoading) {
    return <DashboardSkeleton />;
  }

  if (!executive.data || !mrr.data || !churn.data || !ltv.data || !growth.data) {
    return <LoadingPanel text="Nao foi possivel carregar dados executivos." />;
  }

  const mrrTrend = computeTrend(mrr.data, "value");
  const churnTrend = computeTrend(churn.data, "churn_rate");

  const riskData = [
    { name: "Green", value: executive.data.risk_distribution.green },
    { name: "Yellow", value: executive.data.risk_distribution.yellow },
    { name: "Red", value: executive.data.risk_distribution.red },
  ];

  return (
    <section className="space-y-6">
      <header className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
        <div>
          <h2 className="font-heading text-3xl font-bold text-slate-900">Dashboard Executivo</h2>
          <p className="text-sm text-slate-500">Visao consolidada de MRR, churn e saude da base.</p>
        </div>
        <DashboardActions dashboard="executive" showMonthlyDispatch />
      </header>

      <AiInsightCard dashboard="executive" />

      {goalsProgress.data && goalsProgress.data.length > 0 && (
        <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-panel">
          <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-600">Metas ativas</h3>
          <div className="space-y-2">
            {goalsProgress.data.slice(0, 3).map((goal) => (
              <div key={goal.goal.id}>
                <div className="mb-1 flex items-center justify-between text-xs text-slate-600">
                  <span>{goal.goal.name}</span>
                  <span>{goal.progress_pct.toFixed(1)}%</span>
                </div>
                <div className="h-2 w-full rounded-full bg-slate-100">
                  <div
                    className={`h-2 rounded-full ${
                      goal.status === "achieved"
                        ? "bg-emerald-500"
                        : goal.status === "at_risk"
                          ? "bg-rose-500"
                          : "bg-amber-500"
                    }`}
                    style={{ width: `${Math.max(0, Math.min(100, goal.progress_pct))}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {executive.data.risk_distribution.red > 0 && (
        <div
          className="cursor-pointer rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 transition hover:bg-rose-100"
          onClick={() => navigate("/dashboard/retention")}
        >
          <p className="text-sm font-semibold text-rose-700">
            {executive.data.risk_distribution.red} aluno(s) em risco vermelho precisam de atencao imediata.
            <span className="ml-1 underline">Ver dashboard de retencao</span>
          </p>
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        <StatCard
          label="Total de Alunos"
          value={String(executive.data.total_members)}
          tone="neutral"
          tooltip="Numero total de alunos cadastrados (ativos + pausados)"
        />
        <StatCard
          label="Ativos"
          value={String(executive.data.active_members)}
          tone="success"
          tooltip="Alunos com status ativo no sistema"
        />
        <StatCard
          label="MRR"
          value={`R$ ${executive.data.mrr.toFixed(2)}`}
          tone="neutral"
          trend={{ value: mrrTrend, label: "vs mes anterior" }}
          tooltip="Receita Recorrente Mensal: soma das mensalidades dos alunos ativos"
        />
        <StatCard
          label="Churn"
          value={`${executive.data.churn_rate.toFixed(2)}%`}
          tone="danger"
          trend={{ value: churnTrend, label: "vs mes anterior", invertColor: true }}
          tooltip="Taxa de cancelamento: (cancelados no mes / ativos no inicio do mes) x 100"
          onClick={() => navigate("/dashboard/retention")}
        />
        <StatCard
          label="NPS Medio"
          value={executive.data.nps_avg.toFixed(2)}
          tone="warning"
          tooltip="Net Promoter Score medio das respostas coletadas (0-10)"
        />
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
