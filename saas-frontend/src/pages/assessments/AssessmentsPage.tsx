import { useMemo, useState } from "react";
import clsx from "clsx";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { AiInsightCard } from "../../components/common/AiInsightCard";
import { LoadingPanel } from "../../components/common/LoadingPanel";
import { StatCard } from "../../components/common/StatCard";
import type { MemberMini } from "../../services/assessmentService";
import { assessmentService } from "../../services/assessmentService";

type AssessmentFilter = "total" | "assessed_90" | "overdue" | "never" | "upcoming";

type FilterConfig = {
  listTitle: string;
  emptyMessage: string;
  members: MemberMini[];
};

const badgeStyles: Record<AssessmentFilter, string> = {
  total: "bg-white/10 text-lovable-ink-muted",
  assessed_90: "bg-[hsl(var(--lovable-success)/0.16)] text-[hsl(var(--lovable-success))]",
  overdue: "bg-[hsl(var(--lovable-danger)/0.16)] text-[hsl(var(--lovable-danger))]",
  never: "bg-[hsl(var(--lovable-warning)/0.18)] text-[hsl(var(--lovable-warning))]",
  upcoming: "bg-[hsl(var(--lovable-primary)/0.16)] text-[hsl(var(--lovable-primary))]",
};

export function AssessmentsPage() {
  const [activeFilter, setActiveFilter] = useState<AssessmentFilter>("overdue");
  const dashboardQuery = useQuery({
    queryKey: ["assessments", "dashboard"],
    queryFn: () => assessmentService.dashboard(),
    staleTime: 5 * 60 * 1000,
  });

  if (dashboardQuery.isLoading) {
    return <LoadingPanel text="Carregando dashboard de avaliacoes..." />;
  }

  if (dashboardQuery.isError) {
    return <LoadingPanel text="Erro ao carregar avaliacoes. Tente novamente." />;
  }

  if (!dashboardQuery.data) {
    return <LoadingPanel text="Sem dados de avaliacoes." />;
  }

  const data = dashboardQuery.data;
  const filterConfig: Record<AssessmentFilter, FilterConfig> = useMemo(
    () => ({
      total: {
        listTitle: "Todos os membros (prioridade por risco)",
        emptyMessage: "Nenhum membro encontrado.",
        members: data.total_members_items ?? [],
      },
      assessed_90: {
        listTitle: "Membros avaliados nos ultimos 90 dias",
        emptyMessage: "Nenhum membro avaliado nos ultimos 90 dias.",
        members: data.assessed_members ?? [],
      },
      overdue: {
        listTitle: "Membros com avaliacao atrasada",
        emptyMessage: "Nenhum membro atrasado. Otimo trabalho.",
        members: data.overdue_members ?? [],
      },
      never: {
        listTitle: "Membros nunca avaliados",
        emptyMessage: "Nenhum membro sem avaliacao.",
        members: data.never_assessed_members ?? [],
      },
      upcoming: {
        listTitle: "Membros com avaliacao nos proximos 7 dias",
        emptyMessage: "Nenhum membro com avaliacao prevista para os proximos 7 dias.",
        members: data.upcoming_members ?? [],
      },
    }),
    [data],
  );
  const selected = filterConfig[activeFilter];

  return (
    <section className="space-y-6">
      <header>
        <h2 className="font-heading text-3xl font-bold text-lovable-ink">Avaliacoes Fisicas</h2>
        <p className="text-sm text-lovable-ink-muted">Controle trimestral, perfil 360 e acompanhamento de evolucao fisica.</p>
      </header>

      <AiInsightCard dashboard="executive" />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        <StatCard
          label="Total Membros"
          value={String(data.total_members)}
          tone="neutral"
          onClick={() => setActiveFilter("total")}
          active={activeFilter === "total"}
          tooltip="Clique para listar todos os membros."
        />
        <StatCard
          label="Avaliados (90d)"
          value={String(data.assessed_last_90_days)}
          tone="success"
          onClick={() => setActiveFilter("assessed_90")}
          active={activeFilter === "assessed_90"}
          tooltip="Clique para listar apenas avaliados nos ultimos 90 dias."
        />
        <StatCard
          label="Atrasados"
          value={String(data.overdue_assessments)}
          tone="danger"
          onClick={() => setActiveFilter("overdue")}
          active={activeFilter === "overdue"}
          tooltip="Clique para listar apenas membros com avaliacao atrasada."
        />
        <StatCard
          label="Nunca Avaliados"
          value={String(data.never_assessed)}
          tone="warning"
          onClick={() => setActiveFilter("never")}
          active={activeFilter === "never"}
          tooltip="Clique para listar apenas membros nunca avaliados."
        />
        <StatCard
          label="Proximos 7 dias"
          value={String(data.upcoming_7_days)}
          tone="neutral"
          onClick={() => setActiveFilter("upcoming")}
          active={activeFilter === "upcoming"}
          tooltip="Clique para listar apenas membros com avaliacao prevista nos proximos 7 dias."
        />
      </div>

      <p className="text-xs text-lovable-ink-muted">Clique nos cards coloridos para alternar o filtro da lista.</p>

      <section className="rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-sm font-semibold uppercase tracking-wider text-lovable-ink-muted">{selected.listTitle}</h3>
          <span className={clsx("rounded-full px-2 py-0.5 text-[10px] font-bold", badgeStyles[activeFilter])}>
            {selected.members.length} exibidos
          </span>
        </div>

        {selected.members.length === 0 ? (
          <p className="text-sm text-lovable-ink-muted">{selected.emptyMessage}</p>
        ) : (
          <ul className="space-y-3">
            {selected.members.map((member) => (
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
                      Nova avaliacao
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
