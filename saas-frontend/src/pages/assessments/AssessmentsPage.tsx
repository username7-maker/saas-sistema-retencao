import { useMemo, useState } from "react";
import clsx from "clsx";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { AiInsightCard } from "../../components/common/AiInsightCard";
import { LoadingPanel } from "../../components/common/LoadingPanel";
import { StatCard } from "../../components/common/StatCard";
import { Card, CardContent, Input } from "../../components/ui2";
import type { MemberMini } from "../../services/assessmentService";
import { assessmentService } from "../../services/assessmentService";

type AssessmentFilter = "total" | "assessed_90" | "overdue" | "never" | "upcoming";

type FilterConfig = {
  label: string;
  count: number;
  listTitle: string;
  emptyMessage: string;
  members: MemberMini[];
};

function normalizeText(value: string): string {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .trim();
}

export function AssessmentsPage() {
  const [activeFilter, setActiveFilter] = useState<AssessmentFilter>("overdue");
  const [searchQuery, setSearchQuery] = useState("");
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
        label: "Total membros",
        count: data.total_members,
        listTitle: "Todos os membros (prioridade por risco)",
        emptyMessage: "Nenhum membro encontrado.",
        members: data.total_members_items ?? [],
      },
      assessed_90: {
        label: "Avaliados (90d)",
        count: data.assessed_last_90_days,
        listTitle: "Membros avaliados nos ultimos 90 dias",
        emptyMessage: "Nenhum membro avaliado nos ultimos 90 dias.",
        members: data.assessed_members ?? [],
      },
      overdue: {
        label: "Atrasados",
        count: data.overdue_assessments,
        listTitle: "Membros com avaliacao atrasada",
        emptyMessage: "Nenhum membro atrasado. Otimo trabalho.",
        members: data.overdue_members ?? [],
      },
      never: {
        label: "Nunca avaliados",
        count: data.never_assessed,
        listTitle: "Membros nunca avaliados",
        emptyMessage: "Nenhum membro sem avaliacao.",
        members: data.never_assessed_members ?? [],
      },
      upcoming: {
        label: "Proximos 7 dias",
        count: data.upcoming_7_days,
        listTitle: "Membros com avaliacao nos proximos 7 dias",
        emptyMessage: "Nenhum membro com avaliacao prevista para os proximos 7 dias.",
        members: data.upcoming_members ?? [],
      },
    }),
    [data],
  );
  const selectedFilter = filterConfig[activeFilter];
  const coverageRatio = data.total_members > 0 ? Math.round((data.assessed_last_90_days / data.total_members) * 100) : 0;
  const overduePressure = data.total_members > 0 ? Math.round((data.overdue_assessments / data.total_members) * 100) : 0;
  const firstAssessmentGap = data.total_members > 0 ? Math.round((data.never_assessed / data.total_members) * 100) : 0;

  const filteredMembers = useMemo(() => {
    const normalized = normalizeText(searchQuery);
    if (!normalized) {
      return selectedFilter.members;
    }
    return selectedFilter.members.filter((member) => normalizeText(member.full_name).includes(normalized));
  }, [searchQuery, selectedFilter.members]);

  return (
    <section className="space-y-6">
      <AiInsightCard dashboard="executive" />

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="Cobertura 90 dias"
          value={`${coverageRatio}%`}
          tone={coverageRatio >= 60 ? "success" : coverageRatio >= 35 ? "warning" : "danger"}
          tooltip="Percentual da base que recebeu avaliacao nos ultimos 90 dias. Mede cobertura real do acompanhamento."
        />
        <StatCard
          label="Pressao operacional"
          value={`${overduePressure}%`}
          tone={overduePressure >= 30 ? "danger" : overduePressure >= 15 ? "warning" : "success"}
          tooltip="Parcela da academia com avaliacao atrasada. Quanto maior, maior o risco de perder narrativa de progresso."
        />
        <StatCard
          label="Gap de primeira avaliacao"
          value={`${firstAssessmentGap}%`}
          tone={firstAssessmentGap >= 25 ? "danger" : firstAssessmentGap >= 10 ? "warning" : "success"}
          tooltip="Percentual de alunos que ainda nao passaram pela primeira leitura estruturada de evolucao."
        />
        <StatCard
          label="Agenda da semana"
          value={String(data.upcoming_7_days)}
          tone={data.upcoming_7_days === 0 ? "warning" : "neutral"}
          tooltip="Quantidade de membros com avaliacao prevista nos proximos 7 dias. Serve para distribuir carga da equipe."
        />
      </section>

      <section className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <article className="rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
          <p className="text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">Leitura executiva do modulo</p>
          <div className="mt-3 space-y-3 text-sm text-lovable-ink-muted">
            <p>
              {coverageRatio >= 60
                ? "A cobertura de avaliacoes esta sustentando narrativa de progresso para boa parte da base."
                : "A cobertura ainda esta baixa. O risco aqui nao e tecnico, e de valor percebido: aluno treina sem prova clara de evolucao."}
            </p>
            <p>
              {data.overdue_assessments > data.upcoming_7_days
                ? "Ha mais alunos atrasados do que avaliacoes planejadas para os proximos 7 dias. Isso indica fila reprimida de acompanhamento."
                : "A agenda dos proximos 7 dias cobre a maior parte da fila atrasada, o que ajuda a recuperar visibilidade do progresso."}
            </p>
            <p>
              {data.never_assessed > 0
                ? `${data.never_assessed} aluno(s) ainda nao passaram por uma leitura estruturada. Esses casos devem entrar primeiro no radar da equipe.`
                : "Nao ha alunos sem avaliacao registrada no momento."}
            </p>
          </div>
        </article>

        <article className="rounded-2xl border border-lovable-border bg-lovable-primary-soft p-4 shadow-panel">
          <p className="text-xs font-semibold uppercase tracking-wider text-lovable-primary">Como usar este modulo agora</p>
          <ol className="mt-3 space-y-2 text-sm text-lovable-ink">
            <li>1. Priorize atrasados e nunca avaliados para aumentar cobertura real.</li>
            <li>2. Dentro do Perfil 360, leia Diagnostico IA e Forecast antes de decidir a abordagem.</li>
            <li>3. Use Acoes para transformar a avaliacao em task, narrativa e retencao, nao so em medidas.</li>
          </ol>
        </article>
      </section>

      <Card>
        <CardContent className="pt-4">
          <div className="flex flex-wrap items-end gap-3">
            <div className="min-w-[260px] flex-1">
              <label className="mb-1 block text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">Buscar</label>
              <Input
                value={searchQuery}
                onChange={(event) => setSearchQuery(event.target.value)}
                placeholder="Buscar por nome do membro..."
              />
            </div>

            <div className="flex min-h-10 flex-wrap gap-2">
              {Object.entries(filterConfig).map(([key, config]) => {
                const typedKey = key as AssessmentFilter;
                return (
                  <button
                    key={typedKey}
                    type="button"
                    onClick={() => setActiveFilter(typedKey)}
                    className={clsx(
                      "inline-flex items-center gap-2 rounded-xl border px-3 py-2 text-xs font-semibold uppercase tracking-wide transition",
                      activeFilter === typedKey
                        ? "border-lovable-primary bg-lovable-primary-soft text-lovable-primary"
                        : "border-lovable-border bg-lovable-surface-soft text-lovable-ink-muted hover:border-lovable-border-strong hover:text-lovable-ink",
                    )}
                  >
                    <span>{config.label}</span>
                    <span className="rounded-full bg-lovable-surface px-2 py-0.5 text-[10px] text-lovable-ink-muted">
                      {config.count}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          <p className="mt-3 text-xs text-lovable-ink-muted">
            {filteredMembers.length} membro(s) exibido(s) em <strong>{selectedFilter.label}</strong>
            {searchQuery.trim() ? ` para a busca "${searchQuery.trim()}"` : ""}.
          </p>
        </CardContent>
      </Card>

      <section className="rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-sm font-semibold uppercase tracking-wider text-lovable-ink-muted">{selectedFilter.listTitle}</h3>
          <span className="rounded-full bg-lovable-primary-soft px-2 py-0.5 text-[10px] font-bold text-lovable-primary">
            {filteredMembers.length} exibidos
          </span>
        </div>

        {filteredMembers.length === 0 ? (
          <p className="text-sm text-lovable-ink-muted">{selectedFilter.emptyMessage}</p>
        ) : (
          <ul className="space-y-3">
            {filteredMembers.map((member) => (
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
