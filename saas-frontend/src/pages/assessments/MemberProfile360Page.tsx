import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { AssessmentTimeline } from "../../components/assessments/AssessmentTimeline";
import { ConstraintsAlert } from "../../components/assessments/ConstraintsAlert";
import { EvolutionCharts } from "../../components/assessments/EvolutionCharts";
import { GoalsProgress } from "../../components/assessments/GoalsProgress";
import { LoadingPanel } from "../../components/common/LoadingPanel";
import { StatCard } from "../../components/common/StatCard";
import { assessmentService } from "../../services/assessmentService";

type ProfileTab = "summary" | "evolution" | "constraints" | "goals" | "training";

const tabs: Array<{ key: ProfileTab; label: string }> = [
  { key: "summary", label: "Resumo" },
  { key: "evolution", label: "Evolucao" },
  { key: "constraints", label: "Restricoes" },
  { key: "goals", label: "Objetivos" },
  { key: "training", label: "Treino" },
];

export function MemberProfile360Page() {
  const { memberId } = useParams<{ memberId: string }>();
  const [activeTab, setActiveTab] = useState<ProfileTab>("summary");

  const profileQuery = useQuery({
    queryKey: ["assessments", "profile360", memberId],
    queryFn: () => assessmentService.profile360(memberId ?? ""),
    enabled: Boolean(memberId),
    staleTime: 60 * 1000,
  });

  const assessmentsQuery = useQuery({
    queryKey: ["assessments", "list", memberId],
    queryFn: () => assessmentService.list(memberId ?? ""),
    enabled: Boolean(memberId),
    staleTime: 60 * 1000,
  });

  const evolutionQuery = useQuery({
    queryKey: ["assessments", "evolution", memberId],
    queryFn: () => assessmentService.evolution(memberId ?? ""),
    enabled: Boolean(memberId),
    staleTime: 60 * 1000,
  });

  if (!memberId) {
    return <LoadingPanel text="Membro nao informado." />;
  }

  if (profileQuery.isLoading || assessmentsQuery.isLoading || evolutionQuery.isLoading) {
    return <LoadingPanel text="Carregando perfil 360..." />;
  }

  if (!profileQuery.data) {
    return <LoadingPanel text="Perfil 360 indisponivel." />;
  }

  const profile = profileQuery.data;
  const latest = profile.latest_assessment;
  const assessments = assessmentsQuery.data ?? [];
  const evolution = evolutionQuery.data;

  return (
    <section className="space-y-6">
      <header className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="font-heading text-3xl font-bold text-lovable-ink">{profile.member.full_name}</h2>
          <p className="text-sm text-lovable-ink-muted">
            Plano {profile.member.plan_name} | Risco {profile.member.risk_level.toUpperCase()} ({profile.member.risk_score})
          </p>
        </div>
        <div className="flex gap-2">
          <Link
            to="/assessments"
            className="rounded-full border border-lovable-border px-3 py-1.5 text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted hover:bg-lovable-surface-soft"
          >
            Voltar
          </Link>
          <Link
            to={`/assessments/new/${memberId}`}
            className="rounded-full bg-lovable-primary px-3 py-1.5 text-xs font-semibold uppercase tracking-wider text-white hover:brightness-105"
          >
            Nova avaliacao
          </Link>
        </div>
      </header>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Ultima Avaliacao" value={latest ? `#${latest.assessment_number}` : "-"} tone="neutral" />
        <StatCard label="Peso Atual" value={latest?.weight_kg !== null && latest?.weight_kg !== undefined ? `${latest.weight_kg} kg` : "-"} tone="success" />
        <StatCard label="BF Atual" value={latest?.body_fat_pct !== null && latest?.body_fat_pct !== undefined ? `${latest.body_fat_pct}%` : "-"} tone="warning" />
        <StatCard label="Proxima Avaliacao" value={latest?.next_assessment_due ? new Date(latest.next_assessment_due).toLocaleDateString("pt-BR") : "-"} tone="danger" />
      </div>

      {profile.insight_summary && (
        <section className="rounded-2xl border border-lovable-border bg-lovable-primary-soft p-4 shadow-panel">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-lovable-primary">Insight da avaliacao</h3>
          <p className="mt-1 text-sm text-lovable-ink">{profile.insight_summary}</p>
        </section>
      )}

      <nav className="flex flex-wrap gap-2">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            type="button"
            onClick={() => setActiveTab(tab.key)}
            className={`rounded-full px-3 py-1.5 text-xs font-semibold uppercase tracking-wider ${
              activeTab === tab.key
                ? "bg-lovable-primary-soft text-lovable-primary"
                : "bg-lovable-surface-soft text-lovable-ink-muted hover:bg-lovable-surface-soft"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </nav>

      {activeTab === "summary" && <AssessmentTimeline assessments={assessments} />}

      {activeTab === "evolution" && (
        evolution ? (
          <EvolutionCharts evolution={evolution} />
        ) : (
          <section className="rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
            <p className="text-sm text-lovable-ink-muted">Sem dados de evolucao.</p>
          </section>
        )
      )}

      {activeTab === "constraints" && <ConstraintsAlert constraints={profile.constraints} />}

      {activeTab === "goals" && <GoalsProgress goals={profile.goals} />}

      {activeTab === "training" && (
        <section className="rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
          <h3 className="text-sm font-semibold uppercase tracking-wider text-lovable-ink-muted">Plano de treino ativo</h3>
          {profile.active_training_plan ? (
            <div className="mt-3 space-y-2 text-sm text-lovable-ink">
              <p>
                <span className="font-semibold">Nome:</span> {profile.active_training_plan.name}
              </p>
              {profile.active_training_plan.objective && (
                <p>
                  <span className="font-semibold">Objetivo:</span> {profile.active_training_plan.objective}
                </p>
              )}
              <p>
                <span className="font-semibold">Sessoes/semana:</span> {profile.active_training_plan.sessions_per_week}
              </p>
              {profile.active_training_plan.split_type && (
                <p>
                  <span className="font-semibold">Split:</span> {profile.active_training_plan.split_type}
                </p>
              )}
              <p>
                <span className="font-semibold">Periodo:</span>{" "}
                {new Date(profile.active_training_plan.start_date).toLocaleDateString("pt-BR")}
                {profile.active_training_plan.end_date
                  ? ` ate ${new Date(profile.active_training_plan.end_date).toLocaleDateString("pt-BR")}`
                  : ""}
              </p>
              {profile.active_training_plan.notes && (
                <p className="rounded-lg bg-lovable-surface-soft px-3 py-2 text-xs text-lovable-ink-muted">{profile.active_training_plan.notes}</p>
              )}
            </div>
          ) : (
            <p className="mt-2 text-sm text-lovable-ink-muted">Sem plano de treino ativo.</p>
          )}
        </section>
      )}
    </section>
  );
}
