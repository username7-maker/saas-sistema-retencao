import { AIAssistantPanel } from "../common/AIAssistantPanel";
import { KPIStrip, SectionHeader } from "../ui";
import { Badge, Button, Card, CardContent } from "../ui2";
import type { Assessment, AssessmentSummary360, Profile360 } from "../../services/assessmentService";
import type { BodyCompositionEvaluation } from "../../types";
import type { AssessmentWorkspaceTab } from "./assessmentWorkspaceUtils";
import {
  daysSince,
  formatDate,
  formatDateTime,
  formatGoalType,
  riskBadgeVariant,
  riskLabel,
  statusBadgeVariant,
  statusLabel,
  summarizeBodyComposition,
  summarizeConstraints,
  summarizeGoals,
  summarizeLatestAssessment,
  summarizeTrainingPlan,
} from "./assessmentWorkspaceUtils";

interface NoteSummary {
  text: string;
  created_at: string;
}

interface AssessmentWorkspaceOverviewProps {
  profile: Profile360;
  summary: AssessmentSummary360;
  assessments: Assessment[];
  latestBodyComposition: BodyCompositionEvaluation | null;
  latestNote: NoteSummary | null;
  notesCount: number;
  onAddNote: () => void;
  onOpenHistory: () => void;
  onOpenTab: (tab: AssessmentWorkspaceTab) => void;
}

function buildPrimaryActionLabel(summary: AssessmentSummary360): string {
  if (summary.status === "critical") return "Intervencao imediata";
  if (summary.status === "attention") return "Ajuste operacional";
  return "Manter consistencia";
}

export function AssessmentWorkspaceOverview({
  profile,
  summary,
  assessments,
  latestBodyComposition,
  latestNote,
  notesCount,
  onAddNote,
  onOpenHistory,
  onOpenTab,
}: AssessmentWorkspaceOverviewProps) {
  const latestAssessmentSummary = summarizeLatestAssessment(profile.latest_assessment);
  const actions = summary.actions.slice(0, 3);
  const lastCheckinDays = daysSince(profile.member.last_checkin_at ?? null);
  const kpiItems = [
    {
      label: "Ultimo check-in",
      value:
        lastCheckinDays === null ? "Sem registro" : lastCheckinDays === 0 ? "Hoje" : `${lastCheckinDays} dias`,
      tone: lastCheckinDays !== null && lastCheckinDays >= 7 ? ("warning" as const) : ("neutral" as const),
    },
    { label: "Avaliacoes", value: assessments.length, tone: "neutral" as const },
    { label: "Risco", value: `${profile.member.risk_score}`, tone: riskBadgeVariant(profile.member.risk_level) },
    {
      label: "Presenca",
      value: `${summary.forecast.adherence_score}%`,
      tone: summary.forecast.adherence_score >= 70 ? ("success" as const) : ("warning" as const),
    },
  ];

  return (
    <div className="space-y-6">
      <KPIStrip items={kpiItems} />
      <AIAssistantPanel
        assistant={summary.assistant}
        title="IA operacional"
        subtitle="O que mudou, por que importa e qual deve ser a proxima acao para este aluno."
      />

      <section className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <Card className="border-lovable-primary/20 bg-lovable-primary-soft/70">
          <CardContent className="space-y-4 pt-5">
            <SectionHeader title="Diagnostico IA" subtitle="Leitura sintetica para equipe, aluno e retencao." />
            <div className="-mt-1">
              <p className="mt-2 text-base font-semibold text-lovable-ink">{summary.narratives.coach_summary}</p>
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              <article className="rounded-xl border border-lovable-border bg-lovable-surface px-4 py-3">
                <p className="text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">Resumo para o aluno</p>
                <p className="mt-2 text-sm text-lovable-ink">{summary.narratives.member_summary}</p>
              </article>
              <article className="rounded-xl border border-lovable-border bg-lovable-surface px-4 py-3">
                <p className="text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">Resumo para retencao</p>
                <p className="mt-2 text-sm text-lovable-ink">{summary.narratives.retention_summary}</p>
              </article>
            </div>
            {profile.insight_summary ? (
              <article className="rounded-xl border border-lovable-border bg-lovable-surface px-4 py-3">
                <p className="text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">Insight consolidado</p>
                <p className="mt-2 text-sm text-lovable-ink">{profile.insight_summary}</p>
              </article>
            ) : null}
          </CardContent>
        </Card>

        <Card>
          <CardContent className="space-y-4 pt-5">
            <SectionHeader
              title="Proxima melhor acao"
              subtitle="Prioridade operacional imediata para este aluno."
              actions={
                <Badge variant={statusBadgeVariant(summary.status)}>
                  {statusLabel(summary.status)}
                </Badge>
              }
            />
            <div>
              <p className="text-lg font-semibold text-lovable-ink">{summary.next_best_action.title}</p>
              <p className="mt-1 text-sm text-lovable-ink-muted">{summary.next_best_action.reason}</p>
              <p className="mt-3 text-xs text-lovable-primary">{summary.next_best_action.suggested_message}</p>
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              <article className="rounded-xl border border-lovable-border bg-lovable-surface-soft px-4 py-3">
                <p className="text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">Ultima avaliacao</p>
                <p className="mt-2 text-sm font-semibold text-lovable-ink">{latestAssessmentSummary}</p>
                <p className="mt-2 text-xs text-lovable-ink-muted">
                  {profile.latest_assessment?.next_assessment_due
                    ? `Proxima janela: ${formatDate(profile.latest_assessment.next_assessment_due)}`
                    : "Sem proxima janela definida"}
                </p>
              </article>
              <article className="rounded-xl border border-lovable-border bg-lovable-surface-soft px-4 py-3">
                <p className="text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">Consistencia atual</p>
                <p className="mt-2 text-sm font-semibold text-lovable-ink">
                  {summary.recent_weekly_checkins.toFixed(1)} / {summary.target_frequency_per_week}x
                </p>
                <p className="mt-2 text-xs text-lovable-ink-muted">
                  Meta: {formatGoalType(summary.goal_type)} - foco: {buildPrimaryActionLabel(summary)}
                </p>
              </article>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button size="sm" variant="primary" onClick={() => onOpenTab("registro")}>
                Registrar agora
              </Button>
              <Button size="sm" variant="secondary" onClick={() => onOpenTab("contexto")}>
                Abrir contexto
              </Button>
            </div>
            <div className="rounded-xl border border-lovable-border bg-lovable-surface-soft px-4 py-3">
              <p className="text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">Acoes recomendadas</p>
              {actions.length > 0 ? (
                <ul className="mt-3 space-y-2">
                  {actions.map((action) => (
                    <li key={action.key} className="rounded-lg border border-lovable-border bg-lovable-surface px-3 py-2">
                      <p className="text-sm font-medium text-lovable-ink">{action.title}</p>
                      <p className="mt-1 text-xs text-lovable-ink-muted">{action.reason}</p>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="mt-2 text-sm text-lovable-ink-muted">Sem acoes adicionais no momento.</p>
              )}
            </div>
          </CardContent>
        </Card>
      </section>

      <section className="grid gap-4 xl:grid-cols-[1.05fr_0.95fr]">
        <Card>
          <CardContent className="space-y-4 pt-5">
            <SectionHeader
              title="Notas internas"
              subtitle="Contexto da equipe e observacoes comportamentais."
              count={notesCount}
              actions={
                <div className="flex flex-wrap gap-2">
                  <Button size="sm" variant="primary" onClick={onAddNote}>
                    + Adicionar nota
                  </Button>
                  <Button size="sm" variant="secondary" onClick={onOpenHistory}>
                    Historico
                  </Button>
                </div>
              }
            />

            {latestNote ? (
              <div className="rounded-xl border border-lovable-border bg-lovable-surface-soft px-4 py-3">
                <p className="text-sm text-lovable-ink">{latestNote.text}</p>
                <p className="mt-2 text-xs text-lovable-ink-muted">{formatDateTime(latestNote.created_at)}</p>
              </div>
            ) : (
              <div className="rounded-xl border border-dashed border-lovable-border px-4 py-4 text-sm text-lovable-ink-muted">
                Nenhuma nota registrada ainda.
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardContent className="space-y-4 pt-5">
            <SectionHeader title="Status do aluno" subtitle="Leitura consolidada do momento atual." />
            <div className="flex flex-wrap gap-2">
              <Badge variant={statusBadgeVariant(summary.status)}>{statusLabel(summary.status)}</Badge>
              <Badge variant={riskBadgeVariant(profile.member.risk_level)}>{riskLabel(profile.member.risk_level)}</Badge>
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              <article className="rounded-xl border border-lovable-border bg-lovable-surface-soft px-4 py-3">
                <p className="text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">Chance em 60 dias</p>
                <p className="mt-2 text-2xl font-semibold text-lovable-ink">{summary.forecast.probability_60d}%</p>
                <p className="mt-1 text-xs text-lovable-ink-muted">chance de meta em 60 dias</p>
              </article>
              <article className="rounded-xl border border-lovable-border bg-lovable-surface-soft px-4 py-3">
                <p className="text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">Benchmark</p>
                <p className="mt-2 text-sm font-semibold text-lovable-ink">{summary.benchmark.position_label}</p>
                <p className="mt-1 text-xs text-lovable-ink-muted">{summary.benchmark.percentile} percentil no cohort</p>
              </article>
            </div>
          </CardContent>
        </Card>
      </section>

      <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <Card>
          <CardContent className="pt-5">
            <p className="text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">Plano e objetivos</p>
            <p className="mt-3 text-sm font-semibold text-lovable-ink">{summarizeGoals(profile.goals)}</p>
            <p className="mt-2 text-xs text-lovable-ink-muted">{summarizeTrainingPlan(profile.active_training_plan)}</p>
            <Button size="sm" variant="ghost" className="mt-3 px-0" onClick={() => onOpenTab("plano")}>
              Abrir plano e objetivos
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-5">
            <p className="text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">Restricoes e contexto</p>
            <p className="mt-3 text-sm font-semibold text-lovable-ink">{summarizeConstraints(profile.constraints)}</p>
            <p className="mt-2 text-xs text-lovable-ink-muted">
              Gargalo dominante: {summary.diagnosis.primary_bottleneck_label}
            </p>
            <Button size="sm" variant="ghost" className="mt-3 px-0" onClick={() => onOpenTab("contexto")}>
              Abrir contexto completo
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-5">
            <p className="text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">Bioimpedancia</p>
            <p className="mt-3 text-sm font-semibold text-lovable-ink">{summarizeBodyComposition(latestBodyComposition)}</p>
            <p className="mt-2 text-xs text-lovable-ink-muted">
              {latestBodyComposition ? `Ultimo registro: ${formatDate(latestBodyComposition.evaluation_date)}` : "Historico disponivel na aba dedicada"}
            </p>
            <Button size="sm" variant="ghost" className="mt-3 px-0" onClick={() => onOpenTab("bioimpedancia")}>
              Abrir bioimpedancia
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-5">
            <p className="text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">Acompanhamento</p>
            <p className="mt-3 text-sm font-semibold text-lovable-ink">
              {assessments.length > 0 ? `${assessments.length} avaliacao(oes) registradas` : "Sem historico estruturado"}
            </p>
            <p className="mt-2 text-xs text-lovable-ink-muted">
              {assessments.length > 0 ? "Use a aba de evolucao para comparar historico e timeline." : "Comece pelo registro estruturado para ativar o historico."}
            </p>
            <Button size="sm" variant="ghost" className="mt-3 px-0" onClick={() => onOpenTab("evolucao")}>
              Abrir evolucao
            </Button>
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
