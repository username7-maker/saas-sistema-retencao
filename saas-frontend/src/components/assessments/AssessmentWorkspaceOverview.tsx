import type { ReactNode } from "react";
import { AIAssistantPanel } from "../common/AIAssistantPanel";
import { SectionHeader } from "../ui";
import { Badge, Button, Card, CardContent } from "../ui2";
import type { Assessment, AssessmentSummary360, Profile360 } from "../../services/assessmentService";
import type { BodyCompositionEvaluation, LeadToMemberIntelligenceContext } from "../../types";
import type { AssessmentWorkspaceTab } from "./assessmentWorkspaceUtils";
import { CoachWorkspacePanel } from "./CoachWorkspacePanel";
import { MemberIntelligenceContextPanel } from "./MemberIntelligenceContextPanel";
import {
  daysSince,
  formatDate,
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

interface ConversionHandoffSummary {
  plan_name?: string | null;
  join_date?: string | null;
  notes?: string | null;
  email_confirmed?: boolean | null;
  phone_confirmed?: boolean | null;
  converted_at?: string | null;
}

interface AssessmentWorkspaceOverviewProps {
  profile: Profile360;
  summary: AssessmentSummary360;
  assessments: Assessment[];
  latestBodyComposition: BodyCompositionEvaluation | null;
  latestNote: NoteSummary | null;
  notesCount: number;
  conversionHandoff: ConversionHandoffSummary | null;
  intelligenceContext: LeadToMemberIntelligenceContext | null;
  isIntelligenceLoading: boolean;
  isIntelligenceError: boolean;
  canCreateAssessment: boolean;
  canViewContextTab: boolean;
  canManageInternalNotes: boolean;
  visibleTabs: AssessmentWorkspaceTab[];
  onAddNote: () => void;
  onOpenHistory: () => void;
  onOpenTab: (tab: AssessmentWorkspaceTab) => void;
  onRetryIntelligence: () => void;
}

interface OverviewSummaryCardProps {
  title: string;
  eyebrow?: string;
  primary: string;
  secondary: string;
  tertiary?: string | null;
  actionLabel?: string;
  onAction?: () => void;
  actionVariant?: "ghost" | "secondary" | "primary";
  footer?: ReactNode;
}

function buildPrimaryActionLabel(summary: AssessmentSummary360): string {
  if (summary.status === "critical") return "Intervencao imediata";
  if (summary.status === "attention") return "Ajuste operacional";
  return "Manter consistencia";
}

function OverviewSummaryCard({
  title,
  eyebrow,
  primary,
  secondary,
  tertiary,
  actionLabel,
  onAction,
  actionVariant = "ghost",
  footer,
}: OverviewSummaryCardProps) {
  return (
    <Card>
      <CardContent className="space-y-3 pt-5">
        <div>
          {eyebrow ? <p className="text-[11px] font-semibold uppercase tracking-wider text-lovable-ink-muted">{eyebrow}</p> : null}
          <p className="mt-1 text-base font-semibold text-lovable-ink">{title}</p>
        </div>
        <div className="space-y-2">
          <p className="text-sm font-medium text-lovable-ink">{primary}</p>
          <p className="text-xs text-lovable-ink-muted">{secondary}</p>
          {tertiary ? <p className="text-xs text-lovable-ink-muted">{tertiary}</p> : null}
        </div>
        {footer}
        {actionLabel && onAction ? (
          <Button size="sm" variant={actionVariant} className="justify-start px-0" onClick={onAction}>
            {actionLabel}
          </Button>
        ) : null}
      </CardContent>
    </Card>
  );
}

export function AssessmentWorkspaceOverview({
  profile,
  summary,
  assessments,
  latestBodyComposition,
  latestNote,
  notesCount,
  conversionHandoff,
  intelligenceContext,
  isIntelligenceLoading,
  isIntelligenceError,
  canCreateAssessment,
  canViewContextTab,
  canManageInternalNotes,
  visibleTabs,
  onAddNote,
  onOpenHistory,
  onOpenTab,
  onRetryIntelligence,
}: AssessmentWorkspaceOverviewProps) {
  const latestAssessmentSummary = summarizeLatestAssessment(profile.latest_assessment);
  const highlightedActions = summary.actions.slice(0, 2);
  const lastCheckinDays = daysSince(profile.member.last_checkin_at ?? null);
  const canViewPlanTab = visibleTabs.includes("plano");
  const canViewEvolutionTab = visibleTabs.includes("evolucao");
  const canViewBodyCompositionTab = visibleTabs.includes("bioimpedancia");
  const statusTone = statusBadgeVariant(summary.status);
  const riskTone = riskBadgeVariant(profile.member.risk_level);

  const checkinLabel =
    lastCheckinDays === null ? "Sem check-in recente" : lastCheckinDays === 0 ? "Check-in hoje" : `${lastCheckinDays} dias sem check-in`;
  const consistencyLabel = `${summary.recent_weekly_checkins.toFixed(1)} / ${summary.target_frequency_per_week}x por semana`;

  return (
    <div className="space-y-5">
      <section className="grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
        <Card className="border-lovable-primary/20 bg-lovable-primary-soft/70">
          <CardContent className="space-y-4 pt-5">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="space-y-2">
                <p className="text-[11px] font-semibold uppercase tracking-wider text-lovable-ink-muted">Leitura do momento</p>
                <h2 className="text-xl font-semibold text-lovable-ink">{summary.narratives.coach_summary}</h2>
                <p className="max-w-3xl text-sm text-lovable-ink-muted">{summary.next_best_action.reason}</p>
              </div>
              <div className="flex flex-wrap gap-2">
                <Badge variant={statusTone}>{statusLabel(summary.status)}</Badge>
                <Badge variant={riskTone}>{riskLabel(profile.member.risk_level)}</Badge>
              </div>
            </div>

            <div className="rounded-2xl border border-lovable-border bg-lovable-surface px-4 py-4">
              <p className="text-[11px] font-semibold uppercase tracking-wider text-lovable-ink-muted">Proxima melhor acao</p>
              <p className="mt-2 text-lg font-semibold text-lovable-ink">{summary.next_best_action.title}</p>
              <p className="mt-2 text-sm text-lovable-ink-muted">{summary.next_best_action.suggested_message}</p>
              <p className="mt-3 text-xs text-lovable-ink-muted">
                Foco atual: {buildPrimaryActionLabel(summary)} - meta {formatGoalType(summary.goal_type)}
              </p>
            </div>

            <div className="grid gap-3 md:grid-cols-2">
              <article className="rounded-2xl border border-lovable-border bg-lovable-surface px-4 py-3">
                <p className="text-[11px] font-semibold uppercase tracking-wider text-lovable-ink-muted">Resumo para o aluno</p>
                <p className="mt-2 text-sm text-lovable-ink">{summary.narratives.member_summary}</p>
              </article>
              <article className="rounded-2xl border border-lovable-border bg-lovable-surface px-4 py-3">
                <p className="text-[11px] font-semibold uppercase tracking-wider text-lovable-ink-muted">Resumo para retencao</p>
                <p className="mt-2 text-sm text-lovable-ink">{summary.narratives.retention_summary}</p>
              </article>
            </div>

            {(canCreateAssessment || canViewContextTab) && (
              <div className="flex flex-wrap gap-2">
                {canCreateAssessment ? (
                  <Button size="sm" variant="primary" onClick={() => onOpenTab("registro")}>
                    Registrar avaliacao
                  </Button>
                ) : null}
                {canViewContextTab ? (
                  <Button size="sm" variant="secondary" onClick={() => onOpenTab("contexto")}>
                    Abrir contexto
                  </Button>
                ) : null}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardContent className="space-y-4 pt-5">
            <SectionHeader title="Radar rapido" subtitle="O essencial para decidir o proximo passo sem percorrer a tela inteira." />
            <div className="grid gap-3">
              <div className="rounded-2xl border border-lovable-border bg-lovable-surface-soft px-4 py-3">
                <p className="text-[11px] font-semibold uppercase tracking-wider text-lovable-ink-muted">Check-in e consistencia</p>
                <p className="mt-2 text-sm font-semibold text-lovable-ink">{checkinLabel}</p>
                <p className="mt-1 text-xs text-lovable-ink-muted">{consistencyLabel}</p>
              </div>
              <div className="rounded-2xl border border-lovable-border bg-lovable-surface-soft px-4 py-3">
                <p className="text-[11px] font-semibold uppercase tracking-wider text-lovable-ink-muted">Ultima avaliacao</p>
                <p className="mt-2 text-sm font-semibold text-lovable-ink">{latestAssessmentSummary}</p>
                <p className="mt-1 text-xs text-lovable-ink-muted">
                  {profile.latest_assessment?.next_assessment_due
                    ? `Proxima janela: ${formatDate(profile.latest_assessment.next_assessment_due)}`
                    : "Sem proxima janela definida"}
                </p>
              </div>
              <div className="grid gap-3 md:grid-cols-2">
                <div className="rounded-2xl border border-lovable-border bg-lovable-surface-soft px-4 py-3">
                  <p className="text-[11px] font-semibold uppercase tracking-wider text-lovable-ink-muted">Chance em 60 dias</p>
                  <p className="mt-2 text-2xl font-semibold text-lovable-ink">{summary.forecast.probability_60d}%</p>
                  <p className="mt-1 text-xs text-lovable-ink-muted">chance de atingir a meta atual</p>
                </div>
                <div className="rounded-2xl border border-lovable-border bg-lovable-surface-soft px-4 py-3">
                  <p className="text-[11px] font-semibold uppercase tracking-wider text-lovable-ink-muted">Benchmark</p>
                  <p className="mt-2 text-sm font-semibold text-lovable-ink">{summary.benchmark.position_label}</p>
                  <p className="mt-1 text-xs text-lovable-ink-muted">{summary.benchmark.percentile} percentil no cohort</p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </section>

      <AIAssistantPanel
        assistant={summary.assistant}
        title="IA operacional"
        subtitle="O que mudou, por que importa e qual deve ser a proxima acao para este aluno."
      />

      <CoachWorkspacePanel
        summary={summary}
        intelligenceContext={intelligenceContext}
        latestBodyComposition={latestBodyComposition}
        canCreateAssessment={canCreateAssessment}
        canManageInternalNotes={canManageInternalNotes}
        visibleTabs={visibleTabs}
        onOpenTab={onOpenTab}
        onAddNote={onAddNote}
      />

      <MemberIntelligenceContextPanel
        context={intelligenceContext}
        isLoading={isIntelligenceLoading}
        isError={isIntelligenceError}
        onRetry={onRetryIntelligence}
      />

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        <OverviewSummaryCard
          eyebrow="Planejamento"
          title="Plano e objetivos"
          primary={summarizeGoals(profile.goals)}
          secondary={summarizeTrainingPlan(profile.active_training_plan)}
          tertiary={highlightedActions.length > 0 ? `Acao sugerida: ${highlightedActions[0].title}` : null}
          actionLabel={canViewPlanTab ? "Abrir plano e objetivos" : undefined}
          onAction={canViewPlanTab ? () => onOpenTab("plano") : undefined}
        />

        <OverviewSummaryCard
          eyebrow="Contexto"
          title="Restricoes e observacoes"
          primary={summarizeConstraints(profile.constraints)}
          secondary={
            notesCount > 0
              ? `${notesCount} nota(s) interna(s) registrada(s)`
              : "Sem notas internas registradas ainda"
          }
          tertiary={latestNote ? latestNote.text : conversionHandoff?.notes ?? null}
          actionLabel={canViewContextTab ? "Abrir contexto completo" : canManageInternalNotes ? "Adicionar nota" : undefined}
          onAction={
            canViewContextTab
              ? () => onOpenTab("contexto")
              : canManageInternalNotes
                ? onAddNote
                : undefined
          }
          footer={
            conversionHandoff ? (
              <div className="rounded-xl border border-lovable-primary/20 bg-lovable-primary-soft/40 px-3 py-2 text-xs text-lovable-ink-muted">
                Handoff: plano {conversionHandoff.plan_name || "nao informado"} - inicio{" "}
                {conversionHandoff.join_date ? formatDate(conversionHandoff.join_date) : "nao informado"}
              </div>
            ) : undefined
          }
        />

        <OverviewSummaryCard
          eyebrow="Historico"
          title="Bioimpedancia e evolucao"
          primary={summarizeBodyComposition(latestBodyComposition)}
          secondary={
            assessments.length > 0
              ? `${assessments.length} avaliacao(oes) registrada(s)`
              : "Sem historico estruturado ainda"
          }
          tertiary={
            latestBodyComposition
              ? `Ultimo registro em ${formatDate(latestBodyComposition.evaluation_date)}`
              : "Use o registro estruturado para ativar a leitura evolutiva"
          }
          actionLabel={
            canViewBodyCompositionTab
              ? "Abrir bioimpedancia"
              : canViewEvolutionTab
                ? "Abrir evolucao"
                : undefined
          }
          onAction={
            canViewBodyCompositionTab
              ? () => onOpenTab("bioimpedancia")
              : canViewEvolutionTab
                ? () => onOpenTab("evolucao")
                : undefined
          }
          footer={
            canManageInternalNotes && notesCount > 0 ? (
              <div className="flex flex-wrap gap-2">
                <Button size="sm" variant="secondary" onClick={onOpenHistory}>
                  Historico de notas
                </Button>
              </div>
            ) : undefined
          }
        />
      </section>
    </div>
  );
}
