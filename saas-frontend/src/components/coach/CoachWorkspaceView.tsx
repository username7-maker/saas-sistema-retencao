import { useDeferredValue, useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bot, CheckCircle2, ExternalLink, Search, Video } from "lucide-react";
import { useNavigate } from "react-router-dom";
import toast from "react-hot-toast";

import { EmptyState, SkeletonList } from "../ui";
import { Badge, Button, Input, Textarea, cn } from "../ui2";
import { coachWorkspaceService, type CoachWorkspaceItem, type CoachWorkspaceShift, type CoachWorkspaceState } from "../../services/coachWorkspaceService";
import { movementVideoService } from "../../services/movementVideoService";
import { personalAiService } from "../../services/personalAiService";
import { workQueueService } from "../../services/workQueueService";
import { useAuth } from "../../hooks/useAuth";
import type { MovementVideoReview, WorkQueueOutcome } from "../../types";
import { getPreferredShiftLabel } from "../../utils/preferredShift";

type QueueMode = "do_now" | "awaiting_outcome" | "all";

const shiftFilters: CoachWorkspaceShift[] = ["my_shift", "morning", "afternoon", "evening", "overnight", "unassigned"];

const outcomeLabels: Partial<Record<WorkQueueOutcome, string>> = {
  training_delivered: "Treino entregue",
  training_missing: "Treino faltando",
  training_adjusted: "Treino ajustado",
  feedback_positive: "Feedback positivo",
  needs_training_adjustment: "Precisa ajuste",
  reassessment_scheduled: "Reavaliacao agendada",
  scheduled_assessment: "Avaliacao agendada",
  postponed: "Adiar",
  forwarded_to_reception: "Encaminhar recepcao",
  completed: "Concluir",
  no_response: "Sem resposta",
};

function itemKey(item: CoachWorkspaceItem): string {
  return `${item.source_type}:${item.source_id}`;
}

function severityVariant(severity: string): "danger" | "warning" | "info" | "neutral" {
  if (severity === "critical" || severity === "high") return "danger";
  if (severity === "medium") return "warning";
  if (severity === "low") return "info";
  return "neutral";
}

function getShiftLabel(shift: string | null): string {
  if (shift === "all") return "Todos os turnos";
  if (shift === "my_shift") return "Meu turno";
  if (!shift || shift === "unassigned") return "Sem turno";
  return getPreferredShiftLabel(shift) || shift;
}

function formatDueAt(value: string | null): string {
  if (!value) return "Sem prazo";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Prazo informado";
  return new Intl.DateTimeFormat("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" }).format(date);
}

function filterItems(items: CoachWorkspaceItem[], search: string): CoachWorkspaceItem[] {
  const normalized = search.trim().toLowerCase();
  if (!normalized) return items;
  return items.filter((item) =>
    [item.subject_name, item.lane_label, item.next_action_label, item.reason, getShiftLabel(item.preferred_shift)]
      .join(" ")
      .toLowerCase()
      .includes(normalized),
  );
}

function laneVariant(lane: CoachWorkspaceItem["lane"]): "success" | "info" | "warning" | "neutral" {
  if (lane === "training_delivery" || lane === "training_feedback") return "success";
  if (lane === "reassessment" || lane === "body_composition_review") return "info";
  if (lane === "assessment_pending") return "warning";
  return "neutral";
}

function CoachCard({
  item,
  selected,
  onSelect,
}: {
  item: CoachWorkspaceItem;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={cn(
        "w-full rounded-[22px] border px-4 py-4 text-left transition",
        selected
          ? "border-[hsl(var(--lovable-primary)/0.55)] bg-[linear-gradient(135deg,hsl(var(--lovable-primary)/0.18),hsl(var(--lovable-info)/0.07))] shadow-panel"
          : "border-lovable-border bg-lovable-surface/84 hover:border-lovable-border-strong hover:bg-lovable-surface",
      )}
    >
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant={severityVariant(item.severity)} size="sm">
          {item.severity}
        </Badge>
        <Badge variant={laneVariant(item.lane)} size="sm">
          {item.lane_label}
        </Badge>
        <Badge variant="neutral" size="sm">
          Turno {getShiftLabel(item.preferred_shift)}
        </Badge>
      </div>
      <div className="mt-3 space-y-1">
        <p className="truncate text-base font-semibold text-lovable-ink">{item.subject_name}</p>
        <p className="text-sm font-semibold text-lovable-ink">Fazer agora: {item.next_action_label}</p>
        <p className="line-clamp-2 text-sm text-lovable-ink-muted">{item.reason}</p>
      </div>
      <div className="mt-3 flex items-center justify-between gap-3 text-xs text-lovable-ink-muted">
        <span>{item.technical_ladder_step_label || item.lane_label}</span>
        <span>{formatDueAt(item.due_at)}</span>
      </div>
    </button>
  );
}

function CoachPersonalAiPanel({ memberId, subjectName }: { memberId: string | null; subjectName: string }) {
  const queryClient = useQueryClient();
  const [question, setQuestion] = useState("Como orientar este aluno para resolver esta etapa tecnica?");

  const draftsQuery = useQuery({
    queryKey: ["personal-ai", "coach-workspace-drafts", memberId],
    queryFn: () => personalAiService.listDrafts({ member_id: memberId ?? undefined }),
    enabled: Boolean(memberId),
    staleTime: 30_000,
  });

  const createMutation = useMutation({
    mutationFn: () =>
      personalAiService.createDraft(memberId ?? "", {
        question: question.trim(),
        domain: "routine_support",
        channel: "internal",
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["personal-ai", "coach-workspace-drafts", memberId] });
      toast.success("Personal IA gerou um rascunho tecnico.");
    },
    onError: () => toast.error("Nao foi possivel gerar o rascunho do Personal IA."),
  });

  const prepareMutation = useMutation({
    mutationFn: (draftId: string) => personalAiService.prepareKommo(draftId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["personal-ai", "coach-workspace-drafts", memberId] });
      toast.success("Rascunho preparado na Kommo para revisao.");
    },
    onError: () => toast.error("Nao foi possivel preparar na Kommo."),
  });

  if (!memberId) {
    return (
      <div className="mt-5 rounded-2xl border border-lovable-border bg-lovable-surface/70 p-4">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-lovable-ink-muted">Personal IA</p>
        <p className="mt-2 text-sm text-lovable-ink-muted">Sem aluno vinculado para gerar orientacao tecnica.</p>
      </div>
    );
  }

  const latestDraft = draftsQuery.data?.[0] ?? null;
  const canGenerate = question.trim().length >= 3 && !createMutation.isPending;

  return (
    <div className="mt-5 rounded-2xl border border-lovable-primary/20 bg-lovable-primary/8 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Bot size={16} className="text-lovable-primary" />
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-lovable-ink-muted">Personal IA</p>
        </div>
        <Badge variant="info">Coach review</Badge>
      </div>
      <p className="mt-2 text-sm text-lovable-ink-muted">
        Gere um rascunho para {subjectName}. O professor revisa; nao ha envio automatico.
      </p>
      <Textarea
        rows={3}
        className="mt-3"
        value={question}
        onChange={(event) => setQuestion(event.target.value)}
        placeholder="Ex: Como orientar o aluno nesta etapa?"
      />
      <div className="mt-3 flex flex-wrap justify-end gap-2">
        <Button size="sm" variant="primary" onClick={() => createMutation.mutate()} disabled={!canGenerate}>
          {createMutation.isPending ? "Gerando..." : "Gerar rascunho"}
        </Button>
      </div>

      {latestDraft ? (
        <div className="mt-3 rounded-xl border border-lovable-border bg-lovable-surface/80 p-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant={latestDraft.status === "draft_ready" ? "success" : latestDraft.status === "blocked" ? "warning" : "neutral"}>
                {latestDraft.status === "draft_ready" ? "Rascunho pronto" : latestDraft.status}
              </Badge>
              <Badge variant="neutral">{latestDraft.intent}</Badge>
            </div>
            {latestDraft.status === "draft_ready" ? (
              <Button size="sm" variant="secondary" onClick={() => prepareMutation.mutate(latestDraft.id)} disabled={prepareMutation.isPending}>
                Kommo
              </Button>
            ) : null}
          </div>
          {latestDraft.draft_reply ? <p className="mt-3 text-sm text-lovable-ink">{latestDraft.draft_reply}</p> : null}
          {latestDraft.blocked_reasons.length > 0 ? (
            <p className="mt-2 text-xs text-lovable-warning">Bloqueios: {latestDraft.blocked_reasons.join(", ")}</p>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

function reviewStatusLabel(review: MovementVideoReview): string {
  if (review.status === "blocked") return "Bloqueado";
  if (review.status === "needs_coach_review") return "Revisar";
  if (review.status === "approved") return "Aprovado";
  if (review.status === "rejected") return "Rejeitado";
  return "Pendente";
}

function reviewStatusVariant(review: MovementVideoReview): "warning" | "success" | "danger" | "info" {
  if (review.status === "blocked") return "warning";
  if (review.status === "approved") return "success";
  if (review.status === "rejected") return "danger";
  return "info";
}

function getReviewRejectionReason(review: MovementVideoReview): string | null {
  const reason = review.metadata_json?.rejection_reason;
  return typeof reason === "string" && reason.trim() ? reason.trim() : null;
}

function CoachMovementVideoPanel({ memberId }: { memberId: string | null }) {
  const queryClient = useQueryClient();
  const [exerciseName, setExerciseName] = useState("");
  const [videoUrl, setVideoUrl] = useState("");
  const [coachObservation, setCoachObservation] = useState("");
  const [coachFeedback, setCoachFeedback] = useState("");
  const [rejectReason, setRejectReason] = useState("");

  const reviewsQuery = useQuery({
    queryKey: ["movement-video", "coach-workspace-reviews", memberId],
    queryFn: () => movementVideoService.listReviews(memberId ?? ""),
    enabled: Boolean(memberId),
    staleTime: 30_000,
  });

  const invalidateReviews = async () => {
    await queryClient.invalidateQueries({ queryKey: ["movement-video", "coach-workspace-reviews", memberId] });
  };

  const createMutation = useMutation({
    mutationFn: () =>
      movementVideoService.createReview(memberId ?? "", {
        exercise_name: exerciseName.trim(),
        video_asset_url: videoUrl.trim(),
      }),
    onSuccess: async (review) => {
      await invalidateReviews();
      setExerciseName("");
      setVideoUrl("");
      toast.success(review.status === "blocked" ? "Review criado com bloqueio explicavel." : "Review de video criado.");
    },
    onError: () => toast.error("Nao foi possivel criar o review de video."),
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
      toast.success("Review preparado para revisao do professor.");
    },
    onError: () => toast.error("Nao foi possivel analisar o review."),
  });

  const approveMutation = useMutation({
    mutationFn: ({ reviewId, feedback }: { reviewId: string; feedback: string }) =>
      movementVideoService.approveReview(reviewId, {
        coach_feedback: feedback,
      }),
    onSuccess: async () => {
      await invalidateReviews();
      toast.success("Feedback aprovado. Agora pode preparar na Kommo.");
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
      toast.success("Review rejeitado com motivo registrado.");
    },
    onError: () => toast.error("Nao foi possivel rejeitar o review."),
  });

  const prepareMutation = useMutation({
    mutationFn: (reviewId: string) => movementVideoService.prepareKommo(reviewId),
    onSuccess: async () => {
      await invalidateReviews();
      toast.success("Feedback de video preparado na Kommo.");
    },
    onError: () => toast.error("Nao foi possivel preparar o feedback na Kommo."),
  });

  const latestReview = reviewsQuery.data?.[0] ?? null;
  const effectiveCoachFeedback = coachFeedback.trim() || latestReview?.suggested_feedback?.trim() || "";
  const rejectionReason = latestReview ? getReviewRejectionReason(latestReview) : null;

  useEffect(() => {
    if (latestReview?.suggested_feedback) {
      setCoachFeedback(latestReview.suggested_feedback);
    }
    setRejectReason("");
  }, [latestReview?.id, latestReview?.suggested_feedback]);

  if (!memberId) {
    return null;
  }

  const canReviewLatest = Boolean(latestReview && latestReview.status !== "blocked" && latestReview.status !== "approved" && latestReview.status !== "rejected");
  const canCreate = exerciseName.trim().length >= 2 && videoUrl.trim().length >= 8 && !createMutation.isPending;
  const canApprove = Boolean(canReviewLatest && effectiveCoachFeedback.length >= 3 && !approveMutation.isPending);
  const canReject = Boolean(
    canReviewLatest && rejectReason.trim().length >= 3 && !rejectMutation.isPending,
  );

  return (
    <div className="mt-5 rounded-2xl border border-lovable-info/20 bg-lovable-info/8 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Video size={16} className="text-lovable-info" />
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-lovable-ink-muted">Video de movimento</p>
        </div>
        <Badge variant="info">Coach review</Badge>
      </div>
      <p className="mt-2 text-sm text-lovable-ink-muted">
        Cole uma referencia segura do video. O sistema organiza o review, mas o professor decide o feedback.
      </p>

      <div className="mt-3 grid gap-2 md:grid-cols-[0.8fr,1.2fr]">
        <Input value={exerciseName} onChange={(event) => setExerciseName(event.target.value)} placeholder="Exercicio, ex.: agachamento" />
        <Input value={videoUrl} onChange={(event) => setVideoUrl(event.target.value)} placeholder="URL segura do video" />
      </div>
      <div className="mt-3 flex justify-end">
        <Button size="sm" variant="secondary" onClick={() => createMutation.mutate()} disabled={!canCreate}>
          {createMutation.isPending ? "Criando..." : "Criar review"}
        </Button>
      </div>

      {reviewsQuery.isLoading ? <p className="mt-3 text-xs text-lovable-ink-muted">Carregando reviews...</p> : null}

      {latestReview ? (
        <div className="mt-4 rounded-xl border border-lovable-border bg-lovable-surface/80 p-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant={reviewStatusVariant(latestReview)}>{reviewStatusLabel(latestReview)}</Badge>
              <Badge variant="neutral">{latestReview.exercise_name}</Badge>
            </div>
            {latestReview.status === "approved" ? (
              <Button size="sm" variant="secondary" onClick={() => prepareMutation.mutate(latestReview.id)} disabled={prepareMutation.isPending}>
                Kommo
              </Button>
            ) : null}
          </div>

          {latestReview.blocked_reasons.length > 0 ? (
            <p className="mt-3 text-xs text-lovable-warning">Bloqueios: {latestReview.blocked_reasons.join(", ")}</p>
          ) : null}
          {rejectionReason ? <p className="mt-3 text-xs text-lovable-danger">Rejeitado: {rejectionReason}</p> : null}

          {canReviewLatest ? (
            <>
              <Textarea
                rows={2}
                className="mt-3"
                value={coachObservation}
                onChange={(event) => setCoachObservation(event.target.value)}
                placeholder="Observacao inicial do professor antes de preparar feedback..."
              />
              <div className="mt-2 flex justify-end">
                <Button size="sm" variant="ghost" onClick={() => analyzeMutation.mutate(latestReview.id)} disabled={analyzeMutation.isPending}>
                  {analyzeMutation.isPending ? "Preparando..." : "Preparar revisao"}
                </Button>
              </div>
            </>
          ) : null}

          {canReviewLatest ? (
            <div className="mt-3 rounded-xl border border-lovable-danger/20 bg-lovable-danger/10 p-3">
              <Textarea
                rows={2}
                value={rejectReason}
                onChange={(event) => setRejectReason(event.target.value)}
                placeholder="Motivo da rejeicao, ex.: video sem angulo suficiente ou precisa refazer o envio..."
              />
              <div className="mt-2 flex justify-end">
                <Button size="sm" variant="danger" onClick={() => rejectMutation.mutate(latestReview.id)} disabled={!canReject}>
                  {rejectMutation.isPending ? "Rejeitando..." : "Rejeitar review"}
                </Button>
              </div>
            </div>
          ) : null}

          {canReviewLatest && (latestReview.suggested_feedback || latestReview.status === "needs_coach_review") ? (
            <>
              <Textarea
                rows={3}
                className="mt-3"
                value={coachFeedback}
                onChange={(event) => setCoachFeedback(event.target.value)}
                placeholder="Feedback final que o professor aprova..."
              />
              <div className="mt-2 flex justify-end">
                <Button
                  size="sm"
                  variant="primary"
                  onClick={() => approveMutation.mutate({ reviewId: latestReview.id, feedback: effectiveCoachFeedback })}
                  disabled={!canApprove}
                >
                  {approveMutation.isPending ? "Aprovando..." : "Aprovar feedback"}
                </Button>
              </div>
            </>
          ) : null}

          {latestReview.summary ? <p className="mt-3 text-xs text-lovable-ink-muted">{latestReview.summary}</p> : null}
        </div>
      ) : null}
    </div>
  );
}

export function CoachWorkspaceView() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const [mode, setMode] = useState<QueueMode>("do_now");
  const [shift, setShift] = useState<CoachWorkspaceShift>("my_shift");
  const [search, setSearch] = useState("");
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const deferredSearch = useDeferredValue(search);
  const canSeeAllShifts = user?.role === "owner" || user?.role === "manager";
  const availableShiftFilters = useMemo<CoachWorkspaceShift[]>(
    () => (canSeeAllShifts ? ["all", ...shiftFilters] : shiftFilters),
    [canSeeAllShifts],
  );

  useEffect(() => {
    const hasShiftScope = Boolean(user?.work_shift) || Boolean(user?.work_shift_scope?.length);
    if (canSeeAllShifts && !hasShiftScope && shift === "my_shift") {
      setShift("all");
    }
  }, [canSeeAllShifts, shift, user?.work_shift, user?.work_shift_scope]);

  const query = useQuery({
    queryKey: ["coach-workspace", mode, shift],
    queryFn: () => coachWorkspaceService.getWorkspace({ state: mode as CoachWorkspaceState, shift, page: 1, page_size: 25 }),
    staleTime: 60 * 1000,
  });

  const items = query.data?.items ?? [];
  const filteredItems = useMemo(() => filterItems(items, deferredSearch), [deferredSearch, items]);
  const selectedItem = useMemo(
    () => filteredItems.find((item) => itemKey(item) === selectedKey) ?? filteredItems[0] ?? null,
    [filteredItems, selectedKey],
  );

  const outcomeMutation = useMutation({
    mutationFn: ({ item, outcome }: { item: CoachWorkspaceItem; outcome: WorkQueueOutcome }) =>
      workQueueService.updateOutcome(item.source_type, item.source_id, { outcome }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["coach-workspace"] });
      void queryClient.invalidateQueries({ queryKey: ["work-queue"] });
      void queryClient.invalidateQueries({ queryKey: ["tasks"] });
      toast.success("Resultado tecnico registrado.");
    },
    onError: () => toast.error("Erro ao registrar resultado tecnico."),
  });

  return (
    <section className="rounded-[28px] border border-lovable-border bg-lovable-surface/72 p-4 shadow-panel md:p-6">
      <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.32em] text-lovable-ink-muted">Coach Workspace</p>
          <h2 className="mt-2 text-2xl font-bold text-lovable-ink">Fila tecnica do professor</h2>
          <p className="mt-1 max-w-2xl text-sm text-lovable-ink-muted">
            Avaliacao, bioimpedancia, entrega de treino, feedback e reavaliacao por turno. Retencao e recepcao ficam fora desta fila.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Badge variant="neutral">Total: {query.data?.total ?? 0}</Badge>
          <Badge variant="warning">Vencidas: {query.data?.summary.overdue ?? 0}</Badge>
          <Badge variant="info">Aguardando: {query.data?.summary.awaiting_outcome ?? 0}</Badge>
        </div>
      </div>

      <div className="mt-5 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="relative w-full lg:max-w-xl">
          <Search className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-lovable-ink-muted" />
          <Input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Buscar aluno, etapa ou motivo..."
            className="pl-11"
          />
        </div>
        <div className="flex flex-wrap gap-2">
          {(["do_now", "awaiting_outcome", "all"] as QueueMode[]).map((value) => (
            <Button key={value} size="sm" variant={mode === value ? "secondary" : "ghost"} onClick={() => setMode(value)}>
              {value === "do_now" ? "Fazer agora" : value === "awaiting_outcome" ? "Aguardando" : "Todos"}
            </Button>
          ))}
        </div>
      </div>

      <div className="mt-3 flex flex-wrap gap-2">
        {availableShiftFilters.map((value) => (
          <Button key={value} size="sm" variant={shift === value ? "secondary" : "ghost"} onClick={() => setShift(value)}>
            {getShiftLabel(value)}
          </Button>
        ))}
      </div>

      {query.isLoading ? (
        <div className="mt-6 rounded-2xl border border-lovable-border bg-lovable-surface px-4 py-3">
          <SkeletonList rows={5} cols={3} />
        </div>
      ) : query.isError ? (
        <div className="mt-6 rounded-2xl border border-lovable-border bg-lovable-surface px-4 py-10 text-center text-sm text-lovable-danger">
          Erro ao carregar Coach Workspace.
        </div>
      ) : filteredItems.length === 0 ? (
        <div className="mt-6">
          <EmptyState
            icon={CheckCircle2}
            title="Nenhuma acao tecnica nesta fila"
            description={canSeeAllShifts ? "Troque o turno ou abra Todos os turnos para revisar o restante da fila tecnica." : "Troque o turno ou revise se seu login tem turno configurado."}
          />
        </div>
      ) : (
        <div className="mt-6 grid gap-4 xl:grid-cols-[minmax(0,0.9fr)_minmax(420px,1fr)]">
          <div className="space-y-3">
            {filteredItems.map((item) => (
              <CoachCard
                key={itemKey(item)}
                item={item}
                selected={selectedItem ? itemKey(selectedItem) === itemKey(item) : false}
                onSelect={() => setSelectedKey(itemKey(item))}
              />
            ))}
          </div>

          {selectedItem ? (
            <aside className="rounded-[24px] border border-lovable-border bg-lovable-bg-muted/60 p-5">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant={severityVariant(selectedItem.severity)}>{selectedItem.severity}</Badge>
                <Badge variant={laneVariant(selectedItem.lane)}>{selectedItem.lane_label}</Badge>
                <Badge variant="neutral">Turno {getShiftLabel(selectedItem.preferred_shift)}</Badge>
              </div>
              <h3 className="mt-4 text-2xl font-bold text-lovable-ink">{selectedItem.subject_name}</h3>
              <p className="mt-1 text-sm text-lovable-ink-muted">{formatDueAt(selectedItem.due_at)}</p>

              <div className="mt-5 rounded-2xl border border-lovable-border bg-lovable-surface/70 p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.24em] text-lovable-ink-muted">Fazer agora</p>
                <p className="mt-2 text-base font-semibold text-lovable-ink">{selectedItem.next_action_label}</p>
                <p className="mt-2 text-sm text-lovable-ink-muted">{selectedItem.reason}</p>
              </div>

              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                {selectedItem.evidence.map((entry) => (
                  <div key={`${entry.label}-${entry.value}`} className="rounded-2xl border border-lovable-border bg-lovable-surface/70 p-3">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-lovable-ink-muted">{entry.label}</p>
                    <p className="mt-1 text-sm font-semibold text-lovable-ink">{entry.value}</p>
                  </div>
                ))}
              </div>

              <CoachPersonalAiPanel memberId={selectedItem.member_id} subjectName={selectedItem.subject_name} />
              <CoachMovementVideoPanel memberId={selectedItem.member_id} />

              <div className="mt-5 flex flex-wrap gap-2">
                {selectedItem.allowed_outcomes.slice(0, 5).map((outcome) => (
                  <Button
                    key={outcome}
                    size="sm"
                    variant={outcome === "no_response" || outcome === "postponed" ? "ghost" : "secondary"}
                    disabled={outcomeMutation.isPending}
                    onClick={() => outcomeMutation.mutate({ item: selectedItem, outcome })}
                  >
                    {outcomeLabels[outcome] || outcome}
                  </Button>
                ))}
              </div>

              <div className="mt-5">
                <Button variant="ghost" onClick={() => navigate(selectedItem.context_path)}>
                  <ExternalLink className="h-4 w-4" />
                  Abrir contexto do aluno
                </Button>
              </div>
            </aside>
          ) : null}
        </div>
      )}
    </section>
  );
}
