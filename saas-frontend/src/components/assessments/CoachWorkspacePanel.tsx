import { ClipboardCheck, Dumbbell, FilePenLine, ListChecks } from "lucide-react";

import type { AssessmentSummary360 } from "../../services/assessmentService";
import type { BodyCompositionEvaluation, LeadToMemberIntelligenceContext } from "../../types";
import { Badge, Button, Card, CardContent } from "../ui2";
import type { AssessmentWorkspaceTab } from "./assessmentWorkspaceUtils";
import { formatDateTime } from "./assessmentWorkspaceUtils";

interface CoachWorkspacePanelProps {
  summary: AssessmentSummary360;
  intelligenceContext: LeadToMemberIntelligenceContext | null;
  latestBodyComposition: BodyCompositionEvaluation | null;
  canCreateAssessment: boolean;
  canManageInternalNotes: boolean;
  visibleTabs: AssessmentWorkspaceTab[];
  onOpenTab: (tab: AssessmentWorkspaceTab) => void;
  onAddNote: () => void;
}

function formatDays(days: number | null | undefined): string {
  if (days === null || days === undefined) return "Sem registro";
  if (days === 0) return "Hoje";
  if (days === 1) return "1 dia";
  return `${days} dias`;
}

function buildCoachSignals(
  summary: AssessmentSummary360,
  context: LeadToMemberIntelligenceContext | null,
  latestBodyComposition: BodyCompositionEvaluation | null,
) {
  const signals = [
    {
      label: "Aderencia recente",
      value: `${summary.recent_weekly_checkins.toFixed(1)} / ${summary.target_frequency_per_week}x semana`,
      helper: "Compare frequencia real com a meta semanal antes de aumentar carga.",
    },
    {
      label: "Ultimo check-in",
      value: formatDays(context?.activity.days_without_checkin),
      helper: context?.activity.last_checkin_at ? formatDateTime(context.activity.last_checkin_at) : "Sem historico recente consolidado.",
    },
    {
      label: "Bioimpedancia",
      value: latestBodyComposition ? "Disponivel" : "Pendente",
      helper: latestBodyComposition
        ? `Ultimo peso: ${latestBodyComposition.weight_kg ?? "-"} kg`
        : "Sem composicao corporal real para apoiar ajuste tecnico.",
    },
    {
      label: "Pendencias operacionais",
      value: `${context?.operations.open_tasks_total ?? 0} abertas`,
      helper: `${context?.operations.overdue_tasks_total ?? 0} atrasada(s) no contexto canonico.`,
    },
  ];

  return signals;
}

function buildDataBadges(context: LeadToMemberIntelligenceContext | null, latestBodyComposition: BodyCompositionEvaluation | null) {
  return [
    { label: "Check-ins", ok: Boolean(context && (context.activity.checkins_30d > 0 || context.activity.last_checkin_at)) },
    { label: "Avaliacao", ok: Boolean(context && context.assessment.assessments_total > 0) },
    { label: "Bioimpedancia", ok: Boolean(latestBodyComposition) },
    { label: "Tasks", ok: Boolean(context && context.operations.open_tasks_total >= 0) },
    { label: "Risco", ok: Boolean(context?.risk.risk_level) },
    { label: "Origem", ok: Boolean(context?.lead?.source) },
  ];
}

export function CoachWorkspacePanel({
  summary,
  intelligenceContext,
  latestBodyComposition,
  canCreateAssessment,
  canManageInternalNotes,
  visibleTabs,
  onOpenTab,
  onAddNote,
}: CoachWorkspacePanelProps) {
  const coachSignals = buildCoachSignals(summary, intelligenceContext, latestBodyComposition);
  const dataBadges = buildDataBadges(intelligenceContext, latestBodyComposition);
  const canOpenPlan = visibleTabs.includes("plano");
  const canOpenActions = visibleTabs.includes("acoes");

  return (
    <Card className="border-lovable-info/25 bg-gradient-to-br from-lovable-info/10 via-lovable-surface to-lovable-surface">
      <CardContent className="space-y-5 pt-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-lovable-info">Coach staff-first</p>
            <h3 className="mt-1 text-lg font-semibold text-lovable-ink">Decisao do professor com apoio de dados</h3>
            <p className="mt-1 max-w-3xl text-sm text-lovable-ink-muted">
              O sistema sugere a proxima acao, mas nao ajusta treino sozinho. O professor revisa, aplica ou registra override humano.
            </p>
          </div>
          <Badge variant={summary.status === "critical" ? "danger" : summary.status === "attention" ? "warning" : "success"} size="sm">
            {summary.status === "critical" ? "Prioridade alta" : summary.status === "attention" ? "Acompanhar" : "Na curva"}
          </Badge>
        </div>

        <div className="rounded-2xl border border-lovable-border bg-lovable-surface/80 px-4 py-4">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-lovable-ink-muted">Recomendacao assistida</p>
          <p className="mt-2 text-base font-semibold text-lovable-ink">{summary.next_best_action.title}</p>
          <p className="mt-2 text-sm text-lovable-ink-muted">{summary.next_best_action.suggested_message}</p>
          <p className="mt-3 text-xs text-lovable-ink-muted">{summary.next_best_action.reason}</p>
        </div>

        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          {coachSignals.map((signal) => (
            <div key={signal.label} className="rounded-2xl border border-lovable-border bg-lovable-surface/75 px-4 py-3">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-lovable-ink-muted">{signal.label}</p>
              <p className="mt-2 text-sm font-semibold text-lovable-ink">{signal.value}</p>
              <p className="mt-1 text-xs leading-relaxed text-lovable-ink-muted">{signal.helper}</p>
            </div>
          ))}
        </div>

        <div className="flex flex-wrap gap-2">
          {dataBadges.map((badge) => (
            <Badge key={badge.label} variant={badge.ok ? "success" : "neutral"} size="sm">
              {badge.label}: {badge.ok ? "ok" : "sem base"}
            </Badge>
          ))}
        </div>

        <div className="flex flex-wrap gap-2">
          {canCreateAssessment ? (
            <Button size="sm" variant="primary" onClick={() => onOpenTab("registro")}>
              <ClipboardCheck size={14} />
              Registrar avaliacao
            </Button>
          ) : null}
          {canOpenPlan ? (
            <Button size="sm" variant="secondary" onClick={() => onOpenTab("plano")}>
              <Dumbbell size={14} />
              Ajustar plano
            </Button>
          ) : null}
          {canOpenActions ? (
            <Button size="sm" variant="secondary" onClick={() => onOpenTab("acoes")}>
              <ListChecks size={14} />
              Abrir acoes
            </Button>
          ) : null}
          {canManageInternalNotes ? (
            <Button size="sm" variant="ghost" onClick={onAddNote}>
              <FilePenLine size={14} />
              Registrar decisao/override
            </Button>
          ) : null}
        </div>
      </CardContent>
    </Card>
  );
}
