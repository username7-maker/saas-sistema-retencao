import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { LineSeriesChart } from "../../components/charts/LineSeriesChart";
import { AiInsightCard } from "../../components/common/AiInsightCard";
import { DashboardActions } from "../../components/common/DashboardActions";
import { LoadingPanel } from "../../components/common/LoadingPanel";
import { MemberTimeline } from "../../components/common/MemberTimeline";
import { QuickActions } from "../../components/common/QuickActions";
import { StatCard } from "../../components/common/StatCard";
import { useRetentionDashboard } from "../../hooks/useDashboard";
import { riskAlertService } from "../../services/riskAlertService";
import type { Member } from "../../types";

export function RetentionDashboardPage() {
  const queryClient = useQueryClient();
  const [selectedMember, setSelectedMember] = useState<Member | null>(null);
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

  const handleActionComplete = () => {
    void queryClient.invalidateQueries({ queryKey: ["dashboard", "retention"] });
  };

  if (query.isLoading) {
    return <LoadingPanel text="Carregando dashboard de retencao..." />;
  }

  if (!query.data) {
    return <LoadingPanel text="Sem dados de retencao." />;
  }

  const totalRisk = query.data.red.total + query.data.yellow.total;

  return (
    <section className="space-y-6">
      <header className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
        <div>
          <h2 className="font-heading text-3xl font-bold text-lovable-ink">Dashboard de Retencao</h2>
          <p className="text-sm text-lovable-ink-muted">Lista de risco vermelho/amarelo e evolucao NPS.</p>
        </div>
        <DashboardActions dashboard="retention" />
      </header>

      <AiInsightCard dashboard="retention" />

      {totalRisk > 0 && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3">
          <p className="text-sm font-semibold text-rose-700">
            {query.data.red.total > 0 && `${query.data.red.total} aluno(s) em risco vermelho`}
            {query.data.red.total > 0 && query.data.yellow.total > 0 && " e "}
            {query.data.yellow.total > 0 && `${query.data.yellow.total} em risco amarelo`}
            {" precisam de atencao hoje."}
          </p>
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        <StatCard label="Risco Vermelho" value={String(query.data.red.total)} tone="danger" />
        <StatCard label="Risco Amarelo" value={String(query.data.yellow.total)} tone="warning" />
      </div>

      <LineSeriesChart data={query.data.nps_trend} xKey="month" yKey="average_score" />

      <div className="grid gap-4 xl:grid-cols-2">
        <section className="rounded-2xl border border-rose-200 bg-lovable-surface p-4 shadow-panel">
          <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-rose-700">
            Alunos em vermelho ({query.data.red.total})
          </h3>
          <ul className="space-y-3">
            {query.data.red.items.map((member) => (
              <li key={member.id} className="rounded-lg border border-lovable-border px-3 py-3 text-sm">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="font-medium text-lovable-ink">{member.full_name}</p>
                    <p className="text-xs text-lovable-ink-muted">
                      Score: {member.risk_score} | Plano: {member.plan_name}
                      {member.last_checkin_at && (
                        <> | Ultimo check-in: {new Date(member.last_checkin_at).toLocaleDateString()}</>
                      )}
                    </p>
                  </div>
                  <span className="rounded-full bg-rose-100 px-2 py-0.5 text-[10px] font-bold text-rose-700">
                    {member.risk_score}
                  </span>
                </div>
                <div className="mt-2">
                  <button
                    type="button"
                    onClick={() => setSelectedMember(member)}
                    className="mb-2 rounded-full border border-slate-300 px-3 py-1 text-[10px] font-semibold uppercase tracking-wider text-lovable-ink-muted hover:border-slate-400 hover:text-lovable-ink"
                  >
                    Ver timeline 360
                  </button>
                  <QuickActions member={member} onActionComplete={handleActionComplete} />
                </div>
              </li>
            ))}
          </ul>
        </section>

        <section className="rounded-2xl border border-amber-200 bg-lovable-surface p-4 shadow-panel">
          <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-amber-700">
            Alunos em amarelo ({query.data.yellow.total})
          </h3>
          <ul className="space-y-3">
            {query.data.yellow.items.map((member) => (
              <li key={member.id} className="rounded-lg border border-lovable-border px-3 py-3 text-sm">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="font-medium text-lovable-ink">{member.full_name}</p>
                    <p className="text-xs text-lovable-ink-muted">
                      Score: {member.risk_score} | Plano: {member.plan_name}
                      {member.last_checkin_at && (
                        <> | Ultimo check-in: {new Date(member.last_checkin_at).toLocaleDateString()}</>
                      )}
                    </p>
                  </div>
                  <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-bold text-amber-700">
                    {member.risk_score}
                  </span>
                </div>
                <div className="mt-2">
                  <button
                    type="button"
                    onClick={() => setSelectedMember(member)}
                    className="mb-2 rounded-full border border-slate-300 px-3 py-1 text-[10px] font-semibold uppercase tracking-wider text-lovable-ink-muted hover:border-slate-400 hover:text-lovable-ink"
                  >
                    Ver timeline 360
                  </button>
                  <QuickActions member={member} onActionComplete={handleActionComplete} />
                </div>
              </li>
            ))}
          </ul>
        </section>
      </div>

      <section className="rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
        <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-lovable-ink-muted">Risk Alerts Ativos (Vermelho)</h3>
        {alertsQuery.isLoading ? (
          <p className="text-sm text-lovable-ink-muted">Carregando alertas...</p>
        ) : (
          <div className="space-y-2">
            {(alertsQuery.data?.items ?? []).map((alert) => (
              <article key={alert.id} className="rounded-lg border border-lovable-border p-3">
                <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                  <div>
                    <p className="text-sm font-semibold text-lovable-ink">Alerta {alert.id.slice(0, 8)} | Score {alert.score}</p>
                    <p className="text-xs text-lovable-ink-muted">
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

      {selectedMember && (
        <MemberTimeline member={selectedMember} onClose={() => setSelectedMember(null)} />
      )}
    </section>
  );
}
