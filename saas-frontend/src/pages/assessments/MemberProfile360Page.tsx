import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AxiosError } from "axios";
import { AlertTriangle, ArrowLeft, Bot, CalendarDays, Clock3, ListTodo, MessageCircle, Phone, TriangleAlert, Video } from "lucide-react";
import toast from "react-hot-toast";
import { Link, useParams, useSearchParams } from "react-router-dom";

import { AssessmentRegistrationComposer } from "../../components/assessments/AssessmentRegistrationComposer";
import { AssessmentTimeline } from "../../components/assessments/AssessmentTimeline";
import { AssessmentWorkspaceOverview } from "../../components/assessments/AssessmentWorkspaceOverview";
import {
  ASSESSMENT_WORKSPACE_TABS,
  daysSince,
  formatDateTime,
  formatBirthdayDayMonth,
  getAge,
  getBirthdayCountdownLabel,
  getInitials,
  normalizeAssessmentWorkspaceTab,
  riskLabel,
  statusBadgeVariant,
  statusLabel,
  type AssessmentWorkspaceTab,
} from "../../components/assessments/assessmentWorkspaceUtils";
import { EvolutionCharts } from "../../components/assessments/EvolutionCharts";
import { GoalsProgress } from "../../components/assessments/GoalsProgress";
import { MemberBodyCompositionTab } from "../../components/assessments/MemberBodyCompositionTab";
import { MemberConstraintsEditor } from "../../components/assessments/MemberConstraintsEditor";
import { MemberGoalsEditor } from "../../components/assessments/MemberGoalsEditor";
import { MemberTrainingPlanEditor } from "../../components/assessments/MemberTrainingPlanEditor";
import { EmptyState, SectionHeader, SkeletonList, StatusBadge } from "../../components/ui";
import { MemberTimeline360Content } from "../../components/common/MemberTimeline360Content";
import { Badge, Button, Card, CardContent, Dialog, Input, Skeleton, Tabs, TabsContent, TabsList, TabsTrigger, Textarea } from "../../components/ui2";
import { CreateTaskModal } from "../tasks/CreateTaskModal";
import { bodyCompositionService } from "../../services/bodyCompositionService";
import { assessmentService, type AssessmentSummary360 } from "../../services/assessmentService";
import { memberTimelineService } from "../../services/memberTimelineService";
import { memberService } from "../../services/memberService";
import { movementVideoService } from "../../services/movementVideoService";
import { personalAiService } from "../../services/personalAiService";
import { taskService, type CreateTaskPayload } from "../../services/taskService";
import { userService } from "../../services/userService";
import { useAuth } from "../../hooks/useAuth";
import type { MovementVideoReview, Task } from "../../types";
import {
  canAddAssessmentInternalNote,
  canCreateAssessment,
  canCreateAssessmentTasks,
  canUpdateAssessmentTasks,
  canViewAssessmentTasks,
  canViewAssessmentTimeline,
  getVisibleAssessmentWorkspaceTabs,
} from "../../utils/roleAccess";
import { buildWhatsAppHref, formatPhoneDisplay, normalizeWhatsAppPhone } from "../../utils/whatsapp";
import {
  formatDueDate,
  getTaskOperationalScore,
  getTodayKey,
  isOverdue,
  PRIORITY_LABELS,
  STATUS_LABELS,
} from "../../components/tasks/taskUtils";

interface InternalNote {
  id: string;
  text: string;
  created_at: string;
}

interface ApiErrorPayload {
  detail?: string;
}

const MEMBER_STATUS_MAP = {
  active: { label: "Ativo", variant: "success" as const },
  paused: { label: "Pausado", variant: "warning" as const },
  cancelled: { label: "Cancelado", variant: "danger" as const },
};

const RISK_STATUS_MAP = {
  green: { label: "Estavel", variant: "success" as const },
  yellow: { label: "Atencao", variant: "warning" as const },
  red: { label: "Risco alto", variant: "danger" as const },
};

const TASK_PRIORITY_MAP = {
  low: { label: PRIORITY_LABELS.low, variant: "success" as const },
  medium: { label: PRIORITY_LABELS.medium, variant: "neutral" as const },
  high: { label: PRIORITY_LABELS.high, variant: "warning" as const },
  urgent: { label: PRIORITY_LABELS.urgent, variant: "danger" as const },
};

const TASK_STATUS_MAP = {
  todo: { label: STATUS_LABELS.todo, variant: "neutral" as const },
  doing: { label: STATUS_LABELS.doing, variant: "warning" as const },
  done: { label: STATUS_LABELS.done, variant: "success" as const },
  cancelled: { label: STATUS_LABELS.cancelled, variant: "danger" as const },
};

type PersonalAiDomain =
  | "routine_support"
  | "training_guidance"
  | "assessment_explanation"
  | "body_composition_explanation";

const PERSONAL_AI_DOMAIN_OPTIONS: Array<{ value: PersonalAiDomain; label: string }> = [
  { value: "routine_support", label: "Rotina do aluno" },
  { value: "training_guidance", label: "Orientacao de treino" },
  { value: "assessment_explanation", label: "Explicar avaliacao" },
  { value: "body_composition_explanation", label: "Explicar bioimpedancia" },
];

const PERSONAL_AI_BLOCKER_LABELS: Record<string, string> = {
  member_not_active: "Aluno nao esta ativo para orientacao de treino/rotina.",
  missing_active_training_plan: "Cadastre ou ative um treino antes de orientar rotina.",
  missing_technical_baseline: "Registre avaliacao ou bioimpedancia antes de explicar resultado tecnico.",
  personal_ai_disabled: "Cordex Coach esta desligado nas configuracoes.",
  domain_disabled: "Este tipo de rascunho esta desativado.",
  daily_draft_limit_reached: "Limite diario de rascunhos atingido.",
  autonomous_prescription_not_allowed: "A IA nao pode prescrever treino novo sozinha.",
};

function personalAiBlockerLabel(reason: string): string {
  return PERSONAL_AI_BLOCKER_LABELS[reason] ?? reason;
}

function createNoteId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function parseInternalNotes(extraData: Record<string, unknown>): InternalNote[] {
  const parsed: InternalNote[] = [];
  const raw = extraData.profile360_notes;

  if (Array.isArray(raw)) {
    for (const entry of raw) {
      if (!entry || typeof entry !== "object") continue;
      const noteObj = entry as Record<string, unknown>;
      const text = typeof noteObj.text === "string" ? noteObj.text.trim() : "";
      if (!text) continue;
      const createdAt =
        typeof noteObj.created_at === "string" && !Number.isNaN(Date.parse(noteObj.created_at))
          ? noteObj.created_at
          : new Date().toISOString();
      parsed.push({
        id: typeof noteObj.id === "string" ? noteObj.id : createNoteId(),
        text,
        created_at: createdAt,
      });
    }
  }

  const legacy = typeof extraData.profile360_internal_notes === "string" ? extraData.profile360_internal_notes.trim() : "";
  if (parsed.length === 0 && legacy) {
    parsed.push({
      id: "legacy-note",
      text: legacy,
      created_at: new Date().toISOString(),
    });
  }

  return parsed.sort((a, b) => Date.parse(b.created_at) - Date.parse(a.created_at));
}

function openTabWithSearchParams(
  current: URLSearchParams,
  nextTab: AssessmentWorkspaceTab,
  setSearchParams: ReturnType<typeof useSearchParams>[1],
) {
  const next = new URLSearchParams(current);
  next.set("tab", nextTab);
  setSearchParams(next, { replace: true });
}

function DetailMetric({ label, value, helper }: { label: string; value: string; helper: string }) {
  return (
    <div className="rounded-2xl border border-lovable-border/70 bg-lovable-surface px-4 py-3">
      <p className="text-[10px] font-semibold uppercase tracking-wider text-lovable-ink-muted">{label}</p>
      <p className="mt-2 text-lg font-semibold text-lovable-ink">{value}</p>
      <p className="mt-1 text-xs leading-relaxed text-lovable-ink-muted">{helper}</p>
    </div>
  );
}

function NotesSummaryCard({
  latestNote,
  notesCount,
  onAdd,
  onHistory,
}: {
  latestNote: InternalNote | null;
  notesCount: number;
  onAdd: () => void;
  onHistory: () => void;
}) {
  return (
    <Card>
      <CardContent className="space-y-3 pt-5">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">Notas internas</p>
            <p className="text-sm text-lovable-ink-muted">Contexto da equipe e observacoes comportamentais.</p>
          </div>
          <Badge variant="neutral">{notesCount} nota(s)</Badge>
        </div>
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
        <div className="flex flex-wrap gap-2">
          <Button size="sm" variant="primary" onClick={onAdd}>
            + Adicionar nota
          </Button>
          <Button size="sm" variant="secondary" onClick={onHistory}>
            Historico
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

function ContextSupportPanel({ summary }: { summary: AssessmentSummary360 }) {
  const hasDiagnosisFactors = summary.diagnosis.factors.length > 0;
  const hasActions = summary.actions.length > 0;

  return (
    <div className="space-y-4">
      <Card>
        <CardContent className="space-y-4 pt-5">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">Leitura causal</p>
            <p className="mt-2 text-lg font-semibold text-lovable-ink">{summary.diagnosis.primary_bottleneck_label}</p>
            <p className="mt-1 text-sm text-lovable-ink-muted">
              Secundario: {summary.diagnosis.secondary_bottleneck_label}
            </p>
            <p className="mt-3 text-sm text-lovable-ink">{summary.diagnosis.explanation}</p>
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            <DetailMetric
              label="Risco de frustracao"
              value={String(summary.diagnosis.frustration_risk)}
              helper={`Confianca: ${summary.diagnosis.confidence}`}
            />
            <DetailMetric
              label="Benchmark"
              value={summary.benchmark.position_label}
              helper={`${summary.benchmark.percentile} percentil no cohort`}
            />
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">Fatores avaliados</p>
            {hasDiagnosisFactors ? (
              <ul className="mt-3 space-y-2">
                {summary.diagnosis.factors.map((factor) => (
                  <li key={factor.key} className="rounded-xl border border-lovable-border bg-lovable-surface-soft px-4 py-3">
                    <div className="flex items-center justify-between gap-3">
                      <p className="text-sm font-medium text-lovable-ink">{factor.label}</p>
                      <Badge variant="neutral">{factor.score}</Badge>
                    </div>
                    <p className="mt-1 text-xs text-lovable-ink-muted">{factor.reason}</p>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-2 text-sm text-lovable-ink-muted">Sem fatores suficientes para detalhar esta leitura.</p>
            )}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="space-y-4 pt-5">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">Acoes recomendadas</p>
              <p className="text-sm text-lovable-ink-muted">Desdobramentos sugeridos a partir da leitura atual.</p>
            </div>
            <Badge variant={statusBadgeVariant(summary.status)}>{statusLabel(summary.status)}</Badge>
          </div>
          {hasActions ? (
            <ul className="space-y-3">
              {summary.actions.map((action) => (
                <li key={action.key} className="rounded-xl border border-lovable-border bg-lovable-surface-soft px-4 py-3">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-lovable-ink">{action.title}</p>
                      <p className="mt-1 text-xs text-lovable-ink-muted">{action.reason}</p>
                    </div>
                    <Badge variant="neutral">{action.priority}</Badge>
                  </div>
                  <p className="mt-3 text-xs text-lovable-primary">{action.suggested_message}</p>
                  <p className="mt-2 text-[11px] text-lovable-ink-muted">
                    Responsavel sugerido: {action.owner_role} - prazo: D+{action.due_in_days}
                  </p>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-lovable-ink-muted">Sem acoes recomendadas enquanto nao houver dados suficientes.</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function ProfileHeaderSkeleton() {
  return (
    <section className="space-y-6">
      <Skeleton className="h-4 w-20" />
      <section className="rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
        <div className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
          <div className="flex gap-4">
            <Skeleton className="h-24 w-24 rounded-2xl" />
            <div className="min-w-0 flex-1 space-y-3">
              <Skeleton className="h-8 w-56" />
              <Skeleton className="h-4 w-72" />
              <div className="flex flex-wrap gap-2">
                <Skeleton className="h-6 w-20 rounded-full" />
                <Skeleton className="h-6 w-24 rounded-full" />
              </div>
              <div className="grid gap-3 md:grid-cols-3">
                <Skeleton className="h-20 rounded-xl" />
                <Skeleton className="h-20 rounded-xl" />
                <Skeleton className="h-20 rounded-xl" />
              </div>
            </div>
          </div>
          <Card>
            <CardContent className="pt-5">
              <SkeletonList rows={3} cols={2} />
            </CardContent>
          </Card>
        </div>
      </section>
      <section className="rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
        <SkeletonList rows={8} cols={3} />
      </section>
    </section>
  );
}

function MemberTaskRow({
  task,
  todayKey,
  isPending,
  onSetStatus,
}: {
  task: Task;
  todayKey: string;
  isPending: boolean;
  onSetStatus?: (task: Task, status: Task["status"]) => void;
}) {
  const overdue = isOverdue(task, todayKey);
  const canStart = task.status === "todo";
  const canComplete = task.status !== "done" && task.status !== "cancelled";

  return (
    <li className="rounded-xl border border-lovable-border bg-lovable-surface-soft px-4 py-3">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-sm font-semibold text-lovable-ink">{task.title}</p>
            <StatusBadge status={task.priority} map={TASK_PRIORITY_MAP} />
            <StatusBadge status={task.status} map={TASK_STATUS_MAP} />
          </div>
          {task.description ? <p className="mt-1 text-xs text-lovable-ink-muted">{task.description}</p> : null}
        </div>

        <div className="flex shrink-0 flex-col items-start gap-2 md:items-end">
          <div
            className={`inline-flex items-center gap-1 text-xs ${
              overdue ? "font-semibold text-lovable-danger" : "text-lovable-ink-muted"
            }`}
          >
            {overdue ? <TriangleAlert size={12} /> : <Clock3 size={12} />}
            {formatDueDate(task.due_date)}
          </div>
          {onSetStatus ? (
            <div className="flex flex-wrap gap-2 md:justify-end">
              {canStart ? (
                <Button
                  type="button"
                  size="sm"
                  variant="secondary"
                  disabled={isPending}
                  onClick={() => onSetStatus(task, "doing")}
                >
                  {isPending ? "Atualizando..." : "Iniciar"}
                </Button>
              ) : null}
              {canComplete ? (
                <Button
                  type="button"
                  size="sm"
                  variant="primary"
                  disabled={isPending}
                  onClick={() => onSetStatus(task, "done")}
                >
                  {isPending ? "Atualizando..." : "Concluir"}
                </Button>
              ) : null}
            </div>
          ) : null}
        </div>
      </div>
    </li>
  );
}

function PersonalAiProfilePanel({
  memberId,
  memberName,
  enabled,
  onOpenTab,
}: {
  memberId: string;
  memberName: string;
  enabled: boolean;
  onOpenTab?: (tab: AssessmentWorkspaceTab) => void;
}) {
  const queryClient = useQueryClient();
  const [question, setQuestion] = useState("Como orientar este aluno no proximo contato tecnico?");
  const [domain, setDomain] = useState<PersonalAiDomain>("routine_support");

  const draftsQuery = useQuery({
    queryKey: ["personal-ai", "drafts", memberId],
    queryFn: () => personalAiService.listDrafts({ member_id: memberId }),
    enabled,
    staleTime: 30_000,
  });
  const contextQuery = useQuery({
    queryKey: ["personal-ai", "context", memberId],
    queryFn: () => personalAiService.getContext(memberId),
    enabled,
    staleTime: 60_000,
  });

  const createMutation = useMutation({
    mutationFn: () => personalAiService.createDraft(memberId, { question: question.trim(), domain, channel: "internal" }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["personal-ai", "drafts", memberId] });
      toast.success("Cordex Coach gerou um rascunho para revisao.");
    },
    onError: () => toast.error("Nao foi possivel gerar o rascunho do Cordex Coach."),
  });

  const prepareMutation = useMutation({
    mutationFn: (draftId: string) => personalAiService.prepareKommo(draftId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["personal-ai", "drafts", memberId] });
      toast.success("Rascunho preparado na Kommo para revisao do professor.");
    },
    onError: () => toast.error("Nao foi possivel preparar o rascunho na Kommo."),
  });

  if (!enabled) return null;

  const latestDraft = draftsQuery.data?.[0] ?? null;
  const context = contextQuery.data;
  const canGenerate = question.trim().length >= 3 && !createMutation.isPending;
  const hasBioComposition = Boolean(context?.latest_body_composition);
  const hasAssessment = Boolean(context?.latest_assessment);
  const needsTrainingPlan = Boolean(latestDraft?.blocked_reasons.includes("missing_active_training_plan"));
  const canSwitchToTechnicalExplanation = hasBioComposition || hasAssessment;

  function useBestTechnicalExplanation() {
    if (hasBioComposition) {
      setDomain("body_composition_explanation");
      setQuestion("Como explicar a bioimpedancia mais recente deste aluno de forma simples e segura?");
      return;
    }
    setDomain("assessment_explanation");
    setQuestion("Como explicar a avaliacao mais recente deste aluno de forma simples e segura?");
  }

  return (
    <Card>
      <CardContent className="space-y-4 pt-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <SectionHeader
            title="Cordex Coach"
            subtitle="Rascunho tecnico para professor revisar. Nao prescreve treino novo e nao envia sozinho."
          />
          <Badge variant="info">Coach review</Badge>
        </div>

        <div className="rounded-2xl border border-lovable-border bg-lovable-surface-soft p-4">
          <div className="flex flex-wrap items-center gap-2">
            <Bot size={16} className="text-lovable-primary" />
            <p className="text-sm font-semibold text-lovable-ink">{memberName}</p>
            {context?.active_training_plan ? <Badge variant="success">Treino ativo</Badge> : <Badge variant="warning">Sem treino ativo</Badge>}
            {context?.latest_body_composition ? <Badge variant="neutral">Bioimpedancia</Badge> : null}
            {context?.latest_assessment ? <Badge variant="neutral">Avaliacao</Badge> : null}
          </div>
          {context?.missing_data?.length ? (
            <p className="mt-2 text-xs text-lovable-ink-muted">Lacunas: {context.missing_data.join(", ")}</p>
          ) : null}
        </div>

        <div className="grid gap-3 md:grid-cols-[220px,1fr]">
          <label className="space-y-1">
            <span className="text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">Tipo</span>
            <select
              value={domain}
              onChange={(event) => setDomain(event.target.value as PersonalAiDomain)}
              className="h-11 w-full rounded-xl border border-lovable-border bg-lovable-surface px-3 text-sm text-lovable-ink outline-none transition focus:border-lovable-primary"
            >
              {PERSONAL_AI_DOMAIN_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <label className="space-y-1">
            <span className="text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">Pergunta para o Cordex Coach</span>
            <Textarea
              rows={3}
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="Ex: Como explicar a bioimpedancia e orientar a rotina desta semana?"
            />
          </label>
        </div>

        <div className="flex flex-wrap justify-end gap-2">
          <Button size="sm" variant="primary" onClick={() => createMutation.mutate()} disabled={!canGenerate}>
            {createMutation.isPending ? "Gerando..." : "Gerar rascunho"}
          </Button>
        </div>

        {draftsQuery.isLoading ? (
          <div className="rounded-2xl border border-lovable-border bg-lovable-bg-muted/60 p-4 text-sm text-lovable-ink-muted">
            Carregando rascunhos do aluno...
          </div>
        ) : null}

        {latestDraft ? (
          <div className="rounded-2xl border border-lovable-border bg-lovable-bg-muted/60 p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant={latestDraft.status === "draft_ready" ? "success" : latestDraft.status === "blocked" ? "warning" : "info"}>
                  {latestDraft.status === "draft_ready" ? "Rascunho pronto" : latestDraft.status}
                </Badge>
                <Badge variant={latestDraft.sensitivity === "sensitive" ? "danger" : "neutral"}>{latestDraft.intent}</Badge>
              </div>
              {latestDraft.status === "draft_ready" ? (
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => prepareMutation.mutate(latestDraft.id)}
                  disabled={prepareMutation.isPending}
                >
                  Preparar na Kommo
                </Button>
              ) : null}
            </div>
            <p className="mt-3 text-sm font-semibold text-lovable-ink">{latestDraft.summary}</p>
            {latestDraft.draft_reply ? (
              <div className="mt-3 rounded-xl border border-lovable-primary/20 bg-lovable-primary/10 p-3 text-sm text-lovable-ink">
                {latestDraft.draft_reply}
              </div>
            ) : null}
            {latestDraft.blocked_reasons.length > 0 ? (
              <div className="mt-3 rounded-xl border border-lovable-warning/25 bg-lovable-warning/10 p-3">
                <p className="text-xs font-semibold uppercase tracking-wider text-lovable-warning">Como liberar</p>
                <ul className="mt-2 space-y-1 text-xs text-lovable-ink-muted">
                  {latestDraft.blocked_reasons.map((reason) => (
                    <li key={reason}>- {personalAiBlockerLabel(reason)}</li>
                  ))}
                </ul>
                <div className="mt-3 flex flex-wrap gap-2">
                  {needsTrainingPlan && onOpenTab ? (
                    <Button size="sm" variant="secondary" onClick={() => onOpenTab("plano")}>
                      Abrir plano de treino
                    </Button>
                  ) : null}
                  {canSwitchToTechnicalExplanation ? (
                    <Button size="sm" variant="ghost" onClick={useBestTechnicalExplanation}>
                      Usar explicacao tecnica
                    </Button>
                  ) : null}
                </div>
              </div>
            ) : null}
            {latestDraft.evidence.length > 0 ? (
              <p className="mt-2 text-xs text-lovable-ink-muted">Evidencias: {latestDraft.evidence.join(", ")}</p>
            ) : null}
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}

function movementVideoStatusLabel(review: MovementVideoReview): string {
  if (review.status === "blocked") return "Bloqueado";
  if (review.status === "needs_coach_review") return "Revisar";
  if (review.status === "approved") return "Aprovado";
  if (review.status === "rejected") return "Rejeitado";
  return "Pendente";
}

function movementVideoStatusVariant(review: MovementVideoReview): "neutral" | "success" | "warning" | "danger" | "info" {
  if (review.status === "blocked") return "warning";
  if (review.status === "approved") return "success";
  if (review.status === "rejected") return "danger";
  if (review.status === "needs_coach_review") return "info";
  return "neutral";
}

function getMovementVideoRejectionReason(review: MovementVideoReview): string | null {
  const reason = review.metadata_json?.rejection_reason;
  return typeof reason === "string" && reason.trim() ? reason.trim() : null;
}

function MovementVideoProfilePanel({ memberId, enabled }: { memberId: string; enabled: boolean }) {
  const queryClient = useQueryClient();
  const [exerciseName, setExerciseName] = useState("");
  const [videoUrl, setVideoUrl] = useState("");
  const [coachObservation, setCoachObservation] = useState("");
  const [coachFeedback, setCoachFeedback] = useState("");
  const [rejectReason, setRejectReason] = useState("");

  const reviewsQuery = useQuery({
    queryKey: ["movement-video", "profile-reviews", memberId],
    queryFn: () => movementVideoService.listReviews(memberId),
    enabled,
    staleTime: 60_000,
  });

  const reviews = reviewsQuery.data ?? [];
  const recentReviews = reviews.slice(0, 5);
  const latestReview = recentReviews[0] ?? null;
  const latestReviewCanBeReviewed = Boolean(
    latestReview && latestReview.status !== "blocked" && latestReview.status !== "approved" && latestReview.status !== "rejected",
  );
  const effectiveCoachFeedback = coachFeedback.trim() || latestReview?.suggested_feedback?.trim() || "";

  const invalidateReviews = async () => {
    await queryClient.invalidateQueries({ queryKey: ["movement-video", "profile-reviews", memberId] });
    await queryClient.invalidateQueries({ queryKey: ["movement-video", "coach-workspace-reviews", memberId] });
  };

  const createMutation = useMutation({
    mutationFn: () =>
      movementVideoService.createReview(memberId, {
        exercise_name: exerciseName.trim(),
        video_asset_url: videoUrl.trim(),
      }),
    onSuccess: async () => {
      await invalidateReviews();
      setExerciseName("");
      setVideoUrl("");
      toast.success("Video adicionado para review do professor.");
    },
    onError: () => toast.error("Nao foi possivel adicionar o video."),
  });

  const analyzeMutation = useMutation({
    mutationFn: (reviewId: string) =>
      movementVideoService.analyzeReview(reviewId, {
        coach_observation: coachObservation.trim() || null,
      }),
    onSuccess: async (review) => {
      await invalidateReviews();
      setCoachObservation("");
      setCoachFeedback(review.suggested_feedback ?? "");
      toast.success("Review preparado para revisao.");
    },
    onError: () => toast.error("Nao foi possivel preparar o review."),
  });

  const approveMutation = useMutation({
    mutationFn: (reviewId: string) =>
      movementVideoService.approveReview(reviewId, {
        coach_feedback: effectiveCoachFeedback,
      }),
    onSuccess: async () => {
      await invalidateReviews();
      toast.success("Feedback aprovado.");
    },
    onError: () => toast.error("Nao foi possivel aprovar o feedback."),
  });

  const rejectMutation = useMutation({
    mutationFn: (reviewId: string) =>
      movementVideoService.rejectReview(reviewId, {
        reason: rejectReason.trim(),
      }),
    onSuccess: async () => {
      await invalidateReviews();
      setRejectReason("");
      toast.success("Review rejeitado com motivo.");
    },
    onError: () => toast.error("Nao foi possivel rejeitar o review."),
  });

  const prepareMutation = useMutation({
    mutationFn: (reviewId: string) => movementVideoService.prepareKommo(reviewId),
    onSuccess: async () => {
      await invalidateReviews();
      toast.success("Feedback preparado na Kommo.");
    },
    onError: () => toast.error("Nao foi possivel preparar na Kommo."),
  });

  useEffect(() => {
    setCoachFeedback(latestReview?.suggested_feedback ?? "");
    setRejectReason("");
  }, [latestReview?.id, latestReview?.suggested_feedback]);

  if (!enabled) return null;

  const canCreate = exerciseName.trim().length >= 2 && videoUrl.trim().length >= 8 && !createMutation.isPending;
  const canApprove = Boolean(latestReviewCanBeReviewed && effectiveCoachFeedback.length >= 3 && !approveMutation.isPending);
  const canReject = Boolean(latestReviewCanBeReviewed && rejectReason.trim().length >= 3 && !rejectMutation.isPending);

  return (
    <Card>
      <CardContent className="space-y-4 pt-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <SectionHeader
            title="Video de movimento"
            subtitle="Historico de reviews supervisionados pelo professor. Sem correcao automatica e sem envio autonomo."
            count={reviews.length}
          />
          <Badge variant="info">Coach review</Badge>
        </div>

        <div className="rounded-2xl border border-lovable-info/20 bg-lovable-info/8 p-4">
          <p className="text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">Adicionar video agora</p>
          <p className="mt-1 text-sm text-lovable-ink-muted">
            O professor pode registrar a referencia aqui mesmo. O feedback continua supervisionado.
          </p>
          <div className="mt-3 grid gap-2 md:grid-cols-[0.8fr,1.2fr]">
            <Input value={exerciseName} onChange={(event) => setExerciseName(event.target.value)} placeholder="Exercicio, ex.: supino" />
            <Input value={videoUrl} onChange={(event) => setVideoUrl(event.target.value)} placeholder="URL segura do video" />
          </div>
          <div className="mt-3 flex justify-end">
            <Button size="sm" variant="secondary" onClick={() => createMutation.mutate()} disabled={!canCreate}>
              {createMutation.isPending ? "Adicionando..." : "Adicionar video"}
            </Button>
          </div>
        </div>

        {reviewsQuery.isLoading ? (
          <div className="rounded-2xl border border-lovable-border bg-lovable-bg-muted/60 p-4 text-sm text-lovable-ink-muted">
            Carregando reviews de video...
          </div>
        ) : null}

        {reviewsQuery.isError ? (
          <div className="rounded-2xl border border-lovable-danger/25 bg-lovable-danger/10 p-4 text-sm text-lovable-danger">
            Nao foi possivel carregar o historico de videos.
          </div>
        ) : null}

        {!reviewsQuery.isLoading && !reviewsQuery.isError && recentReviews.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-lovable-border bg-lovable-surface-soft p-4 text-sm text-lovable-ink-muted">
            Nenhum video de movimento registrado para este aluno.
          </div>
        ) : null}

        {recentReviews.length > 0 ? (
          <ul className="space-y-3">
            {recentReviews.map((review) => {
              const rejectionReason = getMovementVideoRejectionReason(review);
              return (
                <li key={review.id} className="rounded-2xl border border-lovable-border bg-lovable-surface-soft p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <Video size={15} className="text-lovable-info" />
                        <p className="text-sm font-semibold text-lovable-ink">{review.exercise_name}</p>
                        <Badge variant={movementVideoStatusVariant(review)}>{movementVideoStatusLabel(review)}</Badge>
                      </div>
                      <p className="mt-1 text-xs text-lovable-ink-muted">
                        Criado em {formatDateTime(review.created_at)}
                        {review.reviewed_at ? ` - Revisado em ${formatDateTime(review.reviewed_at)}` : ""}
                      </p>
                    </div>
                    {review.video_asset_url ? (
                      <a
                        className="text-xs font-semibold text-lovable-primary hover:underline"
                        href={review.video_asset_url}
                        target="_blank"
                        rel="noreferrer"
                      >
                        Abrir video
                      </a>
                    ) : null}
                  </div>

                  {review.summary ? <p className="mt-3 text-sm text-lovable-ink-muted">{review.summary}</p> : null}
                  {review.coach_feedback ? (
                    <div className="mt-3 rounded-xl border border-lovable-success/20 bg-lovable-success/10 p-3 text-sm text-lovable-ink">
                      {review.coach_feedback}
                    </div>
                  ) : null}
                  {review.blocked_reasons.length > 0 ? (
                    <p className="mt-3 text-xs text-lovable-warning">Bloqueios: {review.blocked_reasons.join(", ")}</p>
                  ) : null}
                  {rejectionReason ? <p className="mt-3 text-xs text-lovable-danger">Rejeitado: {rejectionReason}</p> : null}
                </li>
              );
            })}
          </ul>
        ) : null}

        {latestReviewCanBeReviewed && latestReview ? (
          <div className="rounded-2xl border border-lovable-border bg-lovable-bg-muted/60 p-4">
            <p className="text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">Revisar ultimo video</p>
            <Textarea
              rows={2}
              className="mt-3"
              value={coachObservation}
              onChange={(event) => setCoachObservation(event.target.value)}
              placeholder="Observacao do professor antes de preparar o feedback..."
            />
            <div className="mt-2 flex justify-end">
              <Button size="sm" variant="ghost" onClick={() => analyzeMutation.mutate(latestReview.id)} disabled={analyzeMutation.isPending}>
                {analyzeMutation.isPending ? "Preparando..." : "Preparar review"}
              </Button>
            </div>

            {latestReview.suggested_feedback || latestReview.status === "needs_coach_review" ? (
              <>
                <Textarea
                  rows={3}
                  className="mt-3"
                  value={coachFeedback}
                  onChange={(event) => setCoachFeedback(event.target.value)}
                  placeholder="Feedback final aprovado pelo professor..."
                />
                <div className="mt-2 flex justify-end">
                  <Button size="sm" variant="primary" onClick={() => approveMutation.mutate(latestReview.id)} disabled={!canApprove}>
                    {approveMutation.isPending ? "Aprovando..." : "Aprovar feedback"}
                  </Button>
                </div>
              </>
            ) : null}

            <div className="mt-3 rounded-xl border border-lovable-danger/20 bg-lovable-danger/10 p-3">
              <Textarea
                rows={2}
                value={rejectReason}
                onChange={(event) => setRejectReason(event.target.value)}
                placeholder="Se o video estiver ruim, explique o motivo para o aluno reenviar..."
              />
              <div className="mt-2 flex justify-end">
                <Button size="sm" variant="danger" onClick={() => rejectMutation.mutate(latestReview.id)} disabled={!canReject}>
                  {rejectMutation.isPending ? "Rejeitando..." : "Rejeitar video"}
                </Button>
              </div>
            </div>
          </div>
        ) : null}

        {latestReview?.status === "approved" ? (
          <div className="flex justify-end">
            <Button size="sm" variant="secondary" onClick={() => prepareMutation.mutate(latestReview.id)} disabled={prepareMutation.isPending}>
              {prepareMutation.isPending ? "Preparando..." : "Preparar na Kommo"}
            </Button>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}

function MemberTasksPanel({
  tasks,
  todayKey,
  isLoading,
  isError,
  isCreating,
  isUpdating,
  onRetry,
  onCreate,
  onSetStatus,
}: {
  tasks: Task[];
  todayKey: string;
  isLoading: boolean;
  isError: boolean;
  isCreating: boolean;
  isUpdating: boolean;
  onRetry: () => void;
  onCreate?: () => void;
  onSetStatus?: (task: Task, status: Task["status"]) => void;
}) {
  const hasCreateAction = Boolean(onCreate);

  return (
    <Card>
      <CardContent className="pt-5">
        <SectionHeader
          title="Acoes do aluno"
          subtitle="Tarefas e follow-ups diretamente relacionados a este perfil."
          count={tasks.length}
          actions={hasCreateAction ? (
            <Button size="sm" variant="primary" onClick={onCreate} disabled={isCreating}>
              + Nova Tarefa
            </Button>
          ) : undefined}
        />

        {isLoading ? (
          <SkeletonList rows={6} cols={4} />
        ) : isError ? (
          <EmptyState
            icon={AlertTriangle}
            title="Nao foi possivel carregar as tarefas"
            description="Tente novamente para ver as acoes relacionadas a este aluno."
            action={{ label: "Tentar novamente", onClick: onRetry }}
          />
        ) : tasks.length === 0 ? (
          <EmptyState
            icon={ListTodo}
            title="Nenhuma tarefa relacionada"
            description={
              hasCreateAction
                ? "Crie uma tarefa para acompanhar este aluno de forma operacional."
                : "Nenhuma tarefa tecnica pendente para este aluno no momento."
            }
            action={hasCreateAction && onCreate ? { label: "Nova Tarefa", onClick: onCreate } : undefined}
          />
        ) : (
          <ul className="space-y-3">
            {tasks.map((task) => (
              <MemberTaskRow
                key={task.id}
                task={task}
                todayKey={todayKey}
                isPending={isUpdating}
                onSetStatus={onSetStatus}
              />
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}

export function MemberProfile360Page() {
  const { memberId } = useParams<{ memberId: string }>();
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const { user } = useAuth();

  const [noteDraft, setNoteDraft] = useState("");
  const [isAddNoteOpen, setIsAddNoteOpen] = useState(false);
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const [isCreateTaskOpen, setIsCreateTaskOpen] = useState(false);

  const activeTab = normalizeAssessmentWorkspaceTab(searchParams.get("tab"));
  const visibleTabs = getVisibleAssessmentWorkspaceTabs(user?.role);
  const canCreateAssessmentRecord = canCreateAssessment(user?.role);
  const canManageNotes = canAddAssessmentInternalNote(user?.role);
  const canViewTasks = canViewAssessmentTasks(user?.role);
  const canCreateTasks = canCreateAssessmentTasks(user?.role);
  const canUpdateTasks = canUpdateAssessmentTasks(user?.role);
  const canViewTimeline = canViewAssessmentTimeline(user?.role);
  const canUsePersonalAi = user?.role === "owner" || user?.role === "manager" || user?.role === "trainer";
  const canUseMovementVideo = canUsePersonalAi;

  const profileQuery = useQuery({
    queryKey: ["assessments", "profile360", memberId],
    queryFn: () => assessmentService.profile360(memberId ?? ""),
    enabled: Boolean(memberId),
    staleTime: 60 * 1000,
  });

  const memberQuery = useQuery({
    queryKey: ["members", memberId],
    queryFn: () => memberService.getMember(memberId ?? ""),
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

  const summary360Query = useQuery({
    queryKey: ["assessments", "summary360", memberId],
    queryFn: () => assessmentService.summary360(memberId ?? ""),
    enabled: Boolean(memberId),
    staleTime: 60 * 1000,
  });

  const intelligenceContextQuery = useQuery({
    queryKey: ["members", "intelligence-context", memberId],
    queryFn: () => memberService.getIntelligenceContext(memberId ?? ""),
    enabled: Boolean(memberId),
    staleTime: 60 * 1000,
  });

  const operationalProfileQuery = useQuery({
    queryKey: ["members", "operational-profile", memberId],
    queryFn: () => memberService.getOperationalProfile(memberId ?? ""),
    enabled: Boolean(memberId),
    staleTime: 60 * 1000,
  });

  const timelineQuery = useQuery({
    queryKey: ["member-timeline", memberId],
    queryFn: () => memberTimelineService.list(memberId ?? ""),
    enabled: Boolean(memberId) && canViewTimeline,
    staleTime: 60 * 1000,
  });

  const bodyCompositionQuery = useQuery({
    queryKey: ["body-composition", memberId],
    queryFn: () => bodyCompositionService.list(memberId ?? "", 5),
    enabled: Boolean(memberId),
    staleTime: 60 * 1000,
  });

  const memberTasksQuery = useQuery({
    queryKey: ["tasks", "member-workspace", memberId],
    queryFn: () => taskService.listAllTasks({ include_retention: true, member_id: memberId ?? undefined }),
    enabled: Boolean(memberId) && canViewTasks && (activeTab === "acoes" || isCreateTaskOpen),
    staleTime: 60 * 1000,
  });

  const usersQuery = useQuery({
    queryKey: ["users", "member-workspace-task-create"],
    queryFn: userService.listUsers,
    enabled: isCreateTaskOpen && canCreateTasks,
    staleTime: 10 * 60 * 1000,
  });

  const addNoteMutation = useMutation({
    mutationFn: async () => {
      if (!memberId) throw new Error("MEMBRO_INVALIDO");
      const text = noteDraft.trim();
      if (!text) throw new Error("NOTA_VAZIA");

      const created = await memberService.createNote(memberId, {
        note_type: user?.role === "trainer" ? "coach" : "internal",
        visibility: user?.role === "trainer" ? "coach" : "internal",
        body: text,
      });
      return created;
    },
    onSuccess: () => {
      toast.success("Nota adicionada.");
      setNoteDraft("");
      setIsAddNoteOpen(false);
      void queryClient.invalidateQueries({ queryKey: ["members"] });
      void queryClient.invalidateQueries({ queryKey: ["members", "operational-profile", memberId] });
    },
    onError: (error: unknown) => {
      if (error instanceof Error && error.message === "NOTA_VAZIA") {
        toast.error("Digite uma nota antes de adicionar.");
        return;
      }
      if (error instanceof Error && error.message === "MEMBRO_INVALIDO") {
        toast.error("Membro invalido para salvar nota.");
        return;
      }
      if (error instanceof AxiosError) {
        const detail = (error.response?.data as ApiErrorPayload | undefined)?.detail;
        if (detail) {
          toast.error(`Falha ao salvar nota: ${detail}`);
          return;
        }
      }
      toast.error("Nao foi possivel salvar a nota. Verifique permissao e tente novamente.");
    },
  });

  const createTaskMutation = useMutation({
    mutationFn: (payload: CreateTaskPayload) => taskService.createTask(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["tasks"] });
      void queryClient.invalidateQueries({ queryKey: ["tasks", "member-workspace", memberId] });
      toast.success("Tarefa criada.");
      setIsCreateTaskOpen(false);
    },
    onError: () => {
      toast.error("Erro ao criar tarefa.");
    },
  });

  const updateTaskMutation = useMutation({
    mutationFn: ({ taskId, status }: { taskId: string; status: Task["status"] }) =>
      taskService.updateTask(taskId, { status }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["tasks"] });
      void queryClient.invalidateQueries({ queryKey: ["tasks", "member-workspace", memberId] });
      toast.success("Tarefa atualizada.");
    },
    onError: () => {
      toast.error("Nao foi possivel atualizar a tarefa.");
    },
  });

  function openTab(tab: AssessmentWorkspaceTab) {
    openTabWithSearchParams(searchParams, tab, setSearchParams);
  }

  useEffect(() => {
    if (!visibleTabs.includes(activeTab)) {
      openTab(visibleTabs[0] ?? "overview");
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab, visibleTabs.join("|")]);

  async function handleRetryWorkspace() {
    await Promise.all([
      profileQuery.refetch(),
      memberQuery.refetch(),
      assessmentsQuery.refetch(),
      evolutionQuery.refetch(),
      summary360Query.refetch(),
      intelligenceContextQuery.refetch(),
    ]);
  }

  if (!memberId) {
    return (
      <EmptyState
        icon={AlertTriangle}
        title="Membro nao informado"
        description="Volte para a fila de avaliacoes e selecione um aluno para abrir o workspace."
      />
    );
  }

  if (
    profileQuery.isLoading ||
    memberQuery.isLoading ||
    assessmentsQuery.isLoading ||
    evolutionQuery.isLoading ||
    summary360Query.isLoading
  ) {
    return <ProfileHeaderSkeleton />;
  }

  if (
    profileQuery.isError ||
    memberQuery.isError ||
    assessmentsQuery.isError ||
    evolutionQuery.isError ||
    summary360Query.isError ||
    !profileQuery.data ||
    !summary360Query.data ||
    !memberQuery.data
  ) {
    return (
      <section className="rounded-2xl border border-lovable-border bg-lovable-surface p-6 shadow-panel">
        <EmptyState
          icon={AlertTriangle}
          title="Nao foi possivel carregar o perfil do aluno"
          description="Tente novamente para abrir o workspace completo de avaliacao."
          action={{ label: "Tentar novamente", onClick: () => void handleRetryWorkspace() }}
        />
      </section>
    );
  }

  const profile = profileQuery.data;
  const member = memberQuery.data;
  const assessments = assessmentsQuery.data ?? [];
  const evolution =
    evolutionQuery.data ?? {
      labels: [],
      weight: [],
      body_fat: [],
      lean_mass: [],
      bmi: [],
      strength: [],
      flexibility: [],
      cardio: [],
      checkins_labels: [],
      checkins_per_month: [],
      main_lift_load: [],
      main_lift_label: null,
      deltas: {},
    };
  const assessmentIntelligence = summary360Query.data;
  const latestBodyComposition = bodyCompositionQuery.data?.[0] ?? null;

  const mergedExtra = {
    ...(profile.member.extra_data ?? {}),
    ...(member.extra_data ?? {}),
  };
  const rawConversionHandoff =
    typeof mergedExtra.conversion_handoff === "object" && mergedExtra.conversion_handoff !== null
      ? (mergedExtra.conversion_handoff as Record<string, unknown>)
      : null;
  const conversionHandoff = rawConversionHandoff
    ? {
        plan_name: typeof rawConversionHandoff.plan_name === "string" ? rawConversionHandoff.plan_name : null,
        join_date: typeof rawConversionHandoff.join_date === "string" ? rawConversionHandoff.join_date : null,
        notes: typeof rawConversionHandoff.notes === "string" ? rawConversionHandoff.notes : null,
        email_confirmed:
          typeof rawConversionHandoff.email_confirmed === "boolean" ? rawConversionHandoff.email_confirmed : null,
        phone_confirmed:
          typeof rawConversionHandoff.phone_confirmed === "boolean" ? rawConversionHandoff.phone_confirmed : null,
        converted_at: typeof rawConversionHandoff.converted_at === "string" ? rawConversionHandoff.converted_at : null,
      }
    : null;
  const structuredNotes =
    operationalProfileQuery.data?.notes.map((note) => ({
      id: note.id,
      text: note.body,
      created_at: note.created_at,
    })) ?? [];
  const apiNotes = structuredNotes.length > 0 ? structuredNotes : parseInternalNotes(mergedExtra);
  const notes = apiNotes;
  const latestNote = notes[0] ?? null;
  const previousNotes = notes.slice(1);
  const age = getAge(mergedExtra);
  const photoUrl = typeof mergedExtra.photo_url === "string" ? mergedExtra.photo_url : null;
  const daysWithoutCheckin = daysSince(member.last_checkin_at ?? profile.member.last_checkin_at ?? null);
  const daysActive = daysSince(member.join_date);
  const hasStructuredAssessment = Boolean(assessmentIntelligence.latest_assessment);
  const operationalNextAction = operationalProfileQuery.data?.next_best_action ?? null;
  const nextActionTitle = operationalNextAction?.title || assessmentIntelligence.next_best_action.title;
  const nextActionReason = operationalNextAction?.reason || assessmentIntelligence.next_best_action.reason;
  const nextActionDomain = operationalNextAction?.domain ? String(operationalNextAction.domain) : "assessment";
  const autopilotState = operationalProfileQuery.data?.autopilot?.state;
  const openOperationalTasks = Number(operationalProfileQuery.data?.tasks?.open_total ?? memberTasksQuery.data?.total ?? 0);
  const hasEvolutionData = Boolean(evolution.labels.length);
  const todayKey = getTodayKey();
  const normalizedPhone = normalizeWhatsAppPhone(member.phone);
  const phoneDisplay = formatPhoneDisplay(member.phone);
  const whatsappHref = buildWhatsAppHref(
    member.phone,
    assessmentIntelligence.assistant?.suggested_message ?? assessmentIntelligence.next_best_action.suggested_message,
    member.full_name,
  );
  const importedBirthdayLabel =
    typeof mergedExtra.birthday_label === "string" && mergedExtra.birthday_label.trim()
      ? mergedExtra.birthday_label.trim()
      : null;
  const birthdayDayMonth = formatBirthdayDayMonth(member.birthdate);
  const birthdayCountdown = getBirthdayCountdownLabel(member.birthdate);
  const birthdayFullDate = member.birthdate ? new Date(`${member.birthdate}T12:00:00`).toLocaleDateString("pt-BR") : null;
  const birthdayDisplay = birthdayDayMonth ? birthdayDayMonth : importedBirthdayLabel;
  const birthdayMeta = birthdayDayMonth ? birthdayCountdown : importedBirthdayLabel ? "via importacao" : null;

  const memberTasks = (memberTasksQuery.data?.items ?? [])
    .filter((task) => task.member_id === memberId)
    .sort((left, right) => getTaskOperationalScore(right, member, todayKey) - getTaskOperationalScore(left, member, todayKey));

  const secondaryMeta = [member.plan_name, age !== null ? `${age} anos` : null, daysActive !== null ? `${daysActive} dias ativo` : null]
    .filter(Boolean)
    .join(" · ");

  return (
    <section className="space-y-6">
      <div className="flex items-center justify-between gap-3">
        <Link
          to="/assessments"
          className="inline-flex items-center gap-2 text-sm font-medium text-lovable-ink-muted transition hover:text-lovable-ink"
        >
          <ArrowLeft size={14} />
          Voltar
        </Link>

        <div className="flex flex-wrap gap-2">
          {canViewTasks && visibleTabs.includes("acoes") ? (
            <Button size="sm" variant="secondary" onClick={() => openTab("acoes")}>
              Ver Tarefas
            </Button>
          ) : null}
          {canCreateAssessmentRecord && visibleTabs.includes("registro") ? (
            <Button size="sm" variant="primary" onClick={() => openTab("registro")}>
              Nova Avaliacao
            </Button>
          ) : null}
        </div>
      </div>

      <section className="rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
        <div className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
          <div className="flex gap-4">
            <div className="h-24 w-24 overflow-hidden rounded-2xl border border-lovable-border bg-lovable-surface-soft">
              {photoUrl ? (
                <img src={photoUrl} alt={profile.member.full_name} className="h-full w-full object-cover" />
              ) : (
                <div className="flex h-full w-full items-center justify-center font-heading text-2xl font-bold text-lovable-ink-muted">
                  {getInitials(profile.member.full_name)}
                </div>
              )}
            </div>

            <div className="min-w-0 flex-1 space-y-3">
              <div>
                <h1 className="font-heading text-2xl font-bold text-lovable-ink">{profile.member.full_name}</h1>
                <div className="mt-2 flex flex-wrap items-center gap-2">
                  <StatusBadge status={member.status} map={MEMBER_STATUS_MAP} />
                  <StatusBadge status={profile.member.risk_level} map={RISK_STATUS_MAP} />
                </div>
                {secondaryMeta ? <p className="mt-2 text-sm text-lovable-ink-muted">{secondaryMeta}</p> : null}
                {member.email ? <p className="text-sm text-lovable-ink-muted">{member.email}</p> : null}
                <div className="mt-3 flex flex-wrap items-center gap-2">
                  {normalizedPhone && phoneDisplay ? (
                    <a
                      href={`tel:${normalizedPhone}`}
                      className="inline-flex items-center gap-2 rounded-full border border-lovable-border bg-lovable-surface px-3 py-1.5 text-xs font-medium text-lovable-ink transition hover:border-lovable-primary/40 hover:text-lovable-primary"
                    >
                      <Phone size={12} />
                      {phoneDisplay}
                    </a>
                  ) : (
                    <span className="inline-flex items-center gap-2 rounded-full border border-dashed border-lovable-border px-3 py-1.5 text-xs text-lovable-ink-muted">
                      <Phone size={12} />
                      Telefone nao informado
                    </span>
                  )}
                  {whatsappHref ? (
                    <a
                      href={whatsappHref}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-2 rounded-full border border-lovable-primary/30 bg-lovable-primary/12 px-3 py-1.5 text-xs font-semibold text-lovable-primary transition hover:bg-lovable-primary/18"
                    >
                      <MessageCircle size={12} />
                      WhatsApp
                    </a>
                  ) : (
                    <span className="inline-flex items-center gap-2 rounded-full border border-dashed border-lovable-border px-3 py-1.5 text-xs text-lovable-ink-muted">
                      <MessageCircle size={12} />
                      WhatsApp indisponivel
                    </span>
                  )}
                  {birthdayDisplay ? (
                    <span
                      title={birthdayFullDate ?? undefined}
                      className="inline-flex items-center gap-2 rounded-full border border-amber-400/25 bg-amber-400/10 px-3 py-1.5 text-xs font-medium text-amber-200"
                    >
                      <CalendarDays size={12} />
                      {`Aniversario ${birthdayDisplay}${birthdayMeta ? ` - ${birthdayMeta}` : ""}`}
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-2 rounded-full border border-dashed border-lovable-border px-3 py-1.5 text-xs text-lovable-ink-muted">
                      <CalendarDays size={12} />
                      Aniversario nao informado
                    </span>
                  )}
                </div>
              </div>

              <div className="grid gap-3 md:grid-cols-3">
                <DetailMetric
                  label="Check-in"
                  value={
                    daysWithoutCheckin === null
                      ? "Sem registro"
                      : daysWithoutCheckin === 0
                        ? "Hoje"
                        : `${daysWithoutCheckin} dias`
                  }
                  helper={daysWithoutCheckin !== null && daysWithoutCheckin >= 7 ? "Requer atencao operacional" : "Ritmo recente do aluno"}
                />
                <DetailMetric
                  label="Ultima avaliacao"
                  value={assessmentIntelligence.latest_assessment ? "Registrada" : "Pendente"}
                  helper={
                    assessmentIntelligence.latest_assessment
                      ? formatDateTime(assessmentIntelligence.latest_assessment.assessment_date)
                      : "Sem historico estruturado"
                  }
                />
                <DetailMetric
                  label="Proxima acao"
                  value={nextActionTitle}
                  helper={nextActionReason}
                />
              </div>
            </div>
          </div>

          <Card>
            <CardContent className="space-y-4 pt-5">
              <SectionHeader title="Status atual" subtitle="Leitura operacional consolidada para a equipe." />
              <div className="flex flex-wrap gap-2">
                <Badge variant={statusBadgeVariant(assessmentIntelligence.status)}>{statusLabel(assessmentIntelligence.status)}</Badge>
                <Badge variant="neutral">{riskLabel(profile.member.risk_level)}</Badge>
              </div>
              <div className="grid gap-3 md:grid-cols-2">
                <DetailMetric
                  label="Chance em 60 dias"
                  value={`${assessmentIntelligence.forecast.probability_60d}%`}
                  helper={`Meta: ${assessmentIntelligence.goal_type}`}
                />
                <DetailMetric label="Risco" value={`${profile.member.risk_score}`} helper="pontuacao operacional do aluno" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="space-y-4 pt-5">
              <SectionHeader title="Decisao operacional" subtitle="O que o sistema recomenda fazer agora, considerando tasks, risco, Cordex Autopilot e contexto 360." />
              <div className="rounded-2xl border border-lovable-border bg-lovable-surface-soft p-4">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant={nextActionDomain === "relationship" ? "danger" : nextActionDomain === "finance" ? "warning" : "neutral"}>
                    {nextActionDomain}
                  </Badge>
                  {operationalNextAction?.can_autopilot ? <Badge variant="success">Cordex Autopilot possivel</Badge> : null}
                  {autopilotState ? <Badge variant="neutral">Cordex Autopilot: {String(autopilotState)}</Badge> : null}
                </div>
                <h3 className="mt-3 font-heading text-lg font-bold text-lovable-ink">{nextActionTitle}</h3>
                <p className="mt-1 text-sm text-lovable-ink-muted">{nextActionReason}</p>
                <div className="mt-4 grid gap-3 md:grid-cols-3">
                  <DetailMetric label="Responsavel sugerido" value={operationalNextAction?.owner_role ?? "operacao"} helper="quem deve agir primeiro" />
                  <DetailMetric label="Tasks abertas" value={`${openOperationalTasks}`} helper="do perfil deste aluno" />
                  <DetailMetric
                    label="Modo"
                    value={operationalNextAction?.autopilot_mode ?? "manual"}
                    helper={operationalProfileQuery.isError ? "perfil operacional indisponivel" : "estado recomendado"}
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          <PersonalAiProfilePanel memberId={member.id} memberName={member.full_name} enabled={canUsePersonalAi} onOpenTab={openTab} />
          <MovementVideoProfilePanel memberId={member.id} enabled={canUseMovementVideo} />
        </div>
      </section>

      {!hasStructuredAssessment ? (
        <section className="rounded-2xl border border-lovable-border bg-lovable-primary-soft p-4 shadow-panel">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-lovable-primary">Sem avaliacao estruturada</h3>
          <p className="mt-1 text-sm text-lovable-ink">
            Este aluno ainda nao tem dados suficientes para leitura completa. O workspace continua funcional para registro,
            contexto, metas, treino, tarefas e bioimpedancia.
          </p>
        </section>
      ) : null}

      <Tabs value={activeTab} onValueChange={(value) => openTab(value as AssessmentWorkspaceTab)} className="space-y-4">
        <div className="overflow-x-auto pb-1">
          <TabsList className="min-w-max flex-nowrap gap-1">
            {ASSESSMENT_WORKSPACE_TABS.filter((tab) => visibleTabs.includes(tab.key)).map((tab) => (
              <TabsTrigger key={tab.key} value={tab.key} className="whitespace-nowrap">
                {tab.label}
              </TabsTrigger>
            ))}
          </TabsList>
        </div>

        <TabsContent value="overview">
          <AssessmentWorkspaceOverview
            profile={profile}
            summary={assessmentIntelligence}
            assessments={assessments}
            latestBodyComposition={latestBodyComposition}
            latestNote={latestNote}
            notesCount={notes.length}
            conversionHandoff={conversionHandoff}
            intelligenceContext={intelligenceContextQuery.data ?? null}
            isIntelligenceLoading={intelligenceContextQuery.isLoading}
            isIntelligenceError={intelligenceContextQuery.isError}
            canCreateAssessment={canCreateAssessmentRecord && visibleTabs.includes("registro")}
            canViewContextTab={visibleTabs.includes("contexto")}
            canManageInternalNotes={canManageNotes}
            visibleTabs={visibleTabs}
            onAddNote={() => setIsAddNoteOpen(true)}
            onOpenHistory={() => setIsHistoryOpen(true)}
            onOpenTab={openTab}
            onRetryIntelligence={() => void intelligenceContextQuery.refetch()}
          />
        </TabsContent>

        {visibleTabs.includes("registro") ? (
          <TabsContent value="registro">
            <AssessmentRegistrationComposer memberId={memberId} onSaved={() => openTab("overview")} />
          </TabsContent>
        ) : null}

        <TabsContent value="evolucao">
          <div className="space-y-4">
            {hasEvolutionData ? (
              <EvolutionCharts evolution={evolution} />
            ) : (
              <section className="rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
                <p className="text-sm text-lovable-ink-muted">Sem dados de evolucao consolidados ainda.</p>
              </section>
            )}

            <div className="grid gap-4 xl:grid-cols-[1fr_1fr]">
              <AssessmentTimeline assessments={assessments} />
              <Card>
                <CardContent className="space-y-4 pt-5">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">Ritmo operacional</p>
                    <p className="mt-2 text-sm text-lovable-ink-muted">
                      Compare a evolucao das metricas com o historico 360 e os registros de acompanhamento.
                    </p>
                  </div>
                  <div className="grid gap-3 md:grid-cols-2">
                    <DetailMetric
                      label="Check-ins recentes"
                      value={assessmentIntelligence.recent_weekly_checkins.toFixed(1)}
                      helper={`Meta semanal: ${assessmentIntelligence.target_frequency_per_week}x`}
                    />
                    <DetailMetric
                      label="Cenario corrigido"
                      value={`${assessmentIntelligence.forecast.corrected_probability_90d}%`}
                      helper="chance em 90 dias com ajuste do gargalo dominante"
                    />
                  </div>
                </CardContent>
              </Card>
            </div>

            {canViewTimeline ? (
              <MemberTimeline360Content
                member={profile.member}
                events={timelineQuery.data}
                isLoading={timelineQuery.isLoading}
                isError={timelineQuery.isError}
                showContextCard={false}
              />
            ) : null}
          </div>
        </TabsContent>

        {visibleTabs.includes("plano") ? (
          <TabsContent value="plano">
            <div className="space-y-4">
              <div className="grid gap-4 xl:grid-cols-[1.05fr_0.95fr]">
                <MemberGoalsEditor
                  memberId={memberId}
                  goals={profile.goals}
                  defaultAssessmentId={profile.latest_assessment?.id ?? null}
                />
                <MemberTrainingPlanEditor
                  memberId={memberId}
                  trainingPlan={profile.active_training_plan}
                  defaultAssessmentId={profile.latest_assessment?.id ?? null}
                />
              </div>
              <GoalsProgress goals={profile.goals} />
            </div>
          </TabsContent>
        ) : null}

        {visibleTabs.includes("contexto") ? (
          <TabsContent value="contexto">
            <div className="grid gap-4 xl:grid-cols-[1.05fr_0.95fr]">
              <div className="space-y-4">
                <MemberConstraintsEditor memberId={memberId} constraints={profile.constraints} />
                {canManageNotes ? (
                  <NotesSummaryCard
                    latestNote={latestNote}
                    notesCount={notes.length}
                    onAdd={() => setIsAddNoteOpen(true)}
                    onHistory={() => setIsHistoryOpen(true)}
                  />
                ) : null}
              </div>
              <ContextSupportPanel summary={assessmentIntelligence} />
            </div>
          </TabsContent>
        ) : null}

        {visibleTabs.includes("acoes") ? (
          <TabsContent value="acoes">
            <MemberTasksPanel
              tasks={memberTasks}
              todayKey={todayKey}
              isLoading={memberTasksQuery.isLoading}
              isError={memberTasksQuery.isError}
              isCreating={createTaskMutation.isPending}
              isUpdating={updateTaskMutation.isPending}
              onRetry={() => void memberTasksQuery.refetch()}
              onCreate={canCreateTasks ? () => setIsCreateTaskOpen(true) : undefined}
              onSetStatus={
                canUpdateTasks
                  ? (task, status) => updateTaskMutation.mutate({ taskId: task.id, status })
                  : undefined
              }
            />
          </TabsContent>
        ) : null}

        {visibleTabs.includes("bioimpedancia") ? (
          <TabsContent value="bioimpedancia">
            <MemberBodyCompositionTab memberId={memberId} memberName={member.full_name} memberPhone={member.phone} />
          </TabsContent>
        ) : null}
      </Tabs>

      {canCreateTasks ? (
        <CreateTaskModal
          open={isCreateTaskOpen}
          onClose={() => setIsCreateTaskOpen(false)}
          members={[member]}
          users={usersQuery.data ?? []}
          isPending={createTaskMutation.isPending}
          initialMemberId={member.id}
          onSubmit={(payload) => createTaskMutation.mutate(payload)}
        />
      ) : null}

      {canManageNotes ? (
        <Dialog
          open={isAddNoteOpen}
          onClose={() => setIsAddNoteOpen(false)}
          title="Adicionar nota interna"
          description="Ao salvar, esta nota vira a ultima nota registrada do aluno."
        >
          <div className="space-y-3">
            <Textarea
              value={noteDraft}
              onChange={(event) => setNoteDraft(event.target.value)}
              rows={5}
              placeholder="Ex: Prefere bike a esteira. Precisa de mais acompanhamento na adesao ao treino."
            />
            <div className="flex justify-end gap-2">
              <Button
                size="sm"
                variant="ghost"
                onClick={() => {
                  setIsAddNoteOpen(false);
                  setNoteDraft("");
                }}
                disabled={addNoteMutation.isPending}
              >
                Cancelar
              </Button>
              <Button
                size="sm"
                variant="primary"
                onClick={() => addNoteMutation.mutate()}
                disabled={addNoteMutation.isPending || noteDraft.trim().length === 0}
              >
                {addNoteMutation.isPending ? "Salvando..." : "Salvar nota"}
              </Button>
            </div>
          </div>
        </Dialog>
      ) : null}

      {canManageNotes ? (
        <Dialog
          open={isHistoryOpen}
          onClose={() => setIsHistoryOpen(false)}
          title="Historico de notas"
          description="Notas anteriores da equipe para este aluno."
          size="md"
        >
          {previousNotes.length === 0 ? (
            <p className="text-sm text-lovable-ink-muted">Sem notas anteriores.</p>
          ) : (
            <ul className="max-h-80 space-y-2 overflow-y-auto pr-1">
              {previousNotes.map((note) => (
                <li key={note.id} className="rounded-lg border border-lovable-border bg-lovable-surface-soft px-3 py-2">
                  <p className="text-sm text-lovable-ink">{note.text}</p>
                  <p className="mt-1 text-xs text-lovable-ink-muted">{formatDateTime(note.created_at)}</p>
                </li>
              ))}
            </ul>
          )}
        </Dialog>
      ) : null}
    </section>
  );
}
