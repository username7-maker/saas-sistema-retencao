import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { AiInsightCard } from "../../components/common/AiInsightCard";
import { LoadingPanel } from "../../components/common/LoadingPanel";
import { StatCard } from "../../components/common/StatCard";
import { assessmentService } from "../../services/assessmentService";

export function AssessmentsPage() {
  const dashboardQuery = useQuery({
    queryKey: ["assessments", "dashboard"],
    queryFn: () => assessmentService.dashboard(),
    staleTime: 5 * 60 * 1000,
  });

  if (dashboardQuery.isLoading) {
    return <LoadingPanel text="Carregando dashboard de avaliações..." />;
  }

  if (dashboardQuery.isError) {
    return <LoadingPanel text="Erro ao carregar avaliações. Tente novamente." />;
  }

  if (!dashboardQuery.data) {
    return <LoadingPanel text="Sem dados de avaliações." />;
  }

  const data = dashboardQuery.data;

  return (
    <section className="space-y-6">
      <header>
        <h2 className="font-heading text-3xl font-bold text-lovable-ink">Avaliações Físicas</h2>
        <p className="text-sm text-lovable-ink-muted">Controle trimestral, perfil 360 e acompanhamento de evolução física.</p>
      </header>

      <AiInsightCard dashboard="executive" />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        <StatCard label="Total Membros" value={String(data.total_members)} tone="neutral" />
        <StatCard label="Avaliados (90d)" value={String(data.assessed_last_90_days)} tone="success" />
        <StatCard label="Atrasados" value={String(data.overdue_assessments)} tone="danger" />
        <StatCard label="Nunca Avaliados" value={String(data.never_assessed)} tone="warning" />
        <StatCard label="Próximos 7 dias" value={String(data.upcoming_7_days)} tone="neutral" />
      </div>

      <section className="rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-sm font-semibold uppercase tracking-wider text-lovable-ink-muted">Membros com avaliação atrasada</h3>
          <span className="rounded-full bg-[hsl(var(--lovable-danger)/0.15)] px-2 py-0.5 text-[10px] font-bold text-[hsl(var(--lovable-danger))]">
            {data.overdue_members.length} exibidos
          </span>
        </div>

        {data.overdue_members.length === 0 ? (
          <p className="text-sm text-lovable-ink-muted">Nenhum membro atrasado. Ótimo trabalho.</p>
        ) : (
          <ul className="space-y-3">
            {data.overdue_members.map((member) => (
              <li key={member.id} className="rounded-xl border border-lovable-border px-3 py-3">
                <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                  <div>
                    <p className="text-sm font-semibold text-lovable-ink">{member.full_name}</p>
                    <p className="text-xs text-lovable-ink-muted">
                      Plano: {member.plan_name} | Risco: {member.risk_level.toUpperCase()} ({member.risk_score})
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <Link
                      to={`/assessments/members/${member.id}`}
                      className="rounded-full border border-lovable-border px-3 py-1 text-[10px] font-semibold uppercase tracking-wider text-lovable-ink-muted hover:bg-lovable-surface-soft"
                    >
                      Perfil 360
                    </Link>
                    <Link
                      to={`/assessments/new/${member.id}`}
                      className="rounded-full bg-lovable-primary px-3 py-1 text-[10px] font-semibold uppercase tracking-wider text-white hover:brightness-105"
                    >
                      Nova avaliação
                    </Link>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </section>
  );
}
