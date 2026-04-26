import { useDeferredValue, useEffect, useMemo, useState } from "react";
import { AlertTriangle, ArrowRight, Bot, ClipboardList, Loader2, RefreshCw, Search, Sparkles, XCircle } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import toast from "react-hot-toast";

import { EmptyState, KPIStrip, PageHeader, SectionHeader, SkeletonList } from "../../components/ui";
import { MemberIntelligenceMiniCard } from "../../components/common/MemberIntelligenceMiniCard";
import { Badge, Button, Input, Textarea, cn } from "../../components/ui2";
import { useAuth } from "../../hooks/useAuth";
import { aiTriageService } from "../../services/aiTriageService";
import { memberService } from "../../services/memberService";
import type {
  AITriageOutcomeState,
  AITriageRecommendation,
  AITriageSafeActionResult,
  AITriageSafeActionType,
  LeadToMemberIntelligenceContext,
} from "../../types";
import { getPreferredShiftLabel, matchesPreferredShift } from "../../utils/preferredShift";

type WorkflowFilter = "do_now" | "awaiting_outcome" | "all";
type ResolvedActionType = AITriageSafeActionType | null;

function getPriorityTone(priorityBucket: string): "danger" | "warning" | "info" | "neutral" {
  if (priorityBucket === "critical") return "danger";
  if (priorityBucket === "high") return "warning";
  if (priorityBucket === "medium") return "info";
  return "neutral";
}

function formatDomainLabel(domain: string): string {
  if (domain === "retention") return "Retencao";
  if (domain === "onboarding") return "Onboarding";
  return domain;
}

function formatChannelLabel(channel: string | null): string {
  if (!channel) return "Definir manualmente";
  if (channel === "whatsapp") return "WhatsApp";
  if (channel === "call") return "Ligacao";
  if (channel === "task") return "Tarefa";
  if (channel === "in_app") return "Interno";
  return channel;
}

function formatOutcomeLabel(outcomeState: string): string {
  if (outcomeState === "positive") return "Positivo";
  if (outcomeState === "neutral") return "Neutro";
  if (outcomeState === "negative") return "Negativo";
  if (outcomeState === "dismissed") return "Descartado";
  return "Pendente";
}

function formatPercentage(value: number | null | undefined): string {
  if (typeof value !== "number") return "--";
  return `${Math.round(value * 100)}%`;
}

function formatApprovalTime(value: number | null | undefined): string {
  if (typeof value !== "number") return "--";
  const minutes = Math.max(Math.round(value / 60), 0);
  return `${minutes} min`;
}

function formatMetadataLabel(key: string): string {
  return key
    .replace(/_/g, " ")
    .replace(/\b\w/g, (value: string) => value.toUpperCase());
}

function formatMetadataValue(value: unknown): string {
  if (value === null || value === undefined) return "Nao informado";
  if (typeof value === "boolean") return value ? "Sim" : "Nao";
  if (Array.isArray(value)) return value.length ? value.join(", ") : "Nao informado";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function isAwaitingOutcome(item: AITriageRecommendation): boolean {
  if (item.show_outcome_step && item.outcome_state === "pending") {
    return true;
  }
  return ["prepared", "queued", "running", "completed"].includes(item.execution_state) && item.outcome_state === "pending";
}

function resolvePrimaryActionType(item: AITriageRecommendation): ResolvedActionType {
  if (item.primary_action_type) {
    return item.primary_action_type as ResolvedActionType;
  }
  if (item.recommended_channel && ["whatsapp", "call", "in_app"].includes(item.recommended_channel) && item.suggested_message) {
    return "prepare_outbound_message";
  }
  if (item.recommended_channel === "task") {
    return "create_task";
  }
  if (item.source_domain === "retention") {
    return "open_follow_up";
  }
  return "create_task";
}

function resolvePrimaryActionLabel(item: AITriageRecommendation, actionType: ResolvedActionType): string {
  if (item.primary_action_label) {
    return item.primary_action_label;
  }
  if (actionType === "prepare_outbound_message") {
    if (item.recommended_channel === "whatsapp") return "Preparar WhatsApp";
    if (item.recommended_channel === "call") return "Preparar ligacao";
    return "Preparar mensagem";
  }
  if (actionType === "open_follow_up") {
    return "Abrir follow-up";
  }
  if (actionType === "assign_owner") {
    return "Atribuir responsavel";
  }
  return "Criar tarefa";
}

function shouldOfferAssessmentShortcut(item: AITriageRecommendation): boolean {
  if (!item.member_id) {
    return false;
  }
  const text = `${item.recommended_action} ${item.operator_summary}`.toLowerCase();
  return text.includes("avaliacao");
}

function requiresExplicitApproval(item: AITriageRecommendation): boolean {
  if (item.approval_state === "approved") {
    return false;
  }
  if (item.requires_explicit_approval) {
    return true;
  }
  if (item.priority_bucket === "critical") {
    return true;
  }
  return !item.recommended_channel || !item.recommended_owner?.role;
}

function getHttpStatus(error: unknown): number | null {
  if (typeof error === "object" && error !== null && "response" in error) {
    const response = (error as { response?: { status?: number } }).response;
    return typeof response?.status === "number" ? response.status : null;
  }
  return null;
}

function getHttpDetail(error: unknown): string | null {
  if (typeof error === "object" && error !== null && "response" in error) {
    const response = (error as { response?: { data?: { detail?: string } } }).response;
    return typeof response?.data?.detail === "string" ? response.data.detail : null;
  }
  return null;
}

function matchesWorkflowFilter(item: AITriageRecommendation, filter: WorkflowFilter): boolean {
  if (filter === "all") {
    return true;
  }
  if (filter === "awaiting_outcome") {
    return isAwaitingOutcome(item);
  }
  return item.approval_state !== "rejected" && !isAwaitingOutcome(item);
}

function RecommendationListItem({
  item,
  isSelected,
  onSelect,
}: {
  item: AITriageRecommendation;
  isSelected: boolean;
  onSelect: () => void;
}) {
  const preferredShiftLabel = getPreferredShiftLabel(String(item.metadata?.preferred_shift ?? ""));
  const awaitingOutcome = isAwaitingOutcome(item);
  const primaryActionType = resolvePrimaryActionType(item);
  const primaryActionLabel = resolvePrimaryActionLabel(item, primaryActionType);

  return (
    <button
      type="button"
      onClick={onSelect}
      className={cn(
        "w-full rounded-[24px] border px-4 py-4 text-left transition",
        isSelected
          ? "border-[hsl(var(--lovable-primary)/0.45)] bg-[linear-gradient(135deg,hsl(var(--lovable-primary)/0.18),hsl(var(--lovable-info)/0.08))] shadow-panel"
          : "border-lovable-border bg-lovable-surface/88 hover:border-lovable-border-strong hover:bg-lovable-surface",
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant={getPriorityTone(item.priority_bucket)} size="sm">
              {item.priority_bucket}
            </Badge>
            <Badge variant="neutral" size="sm">
              {formatDomainLabel(item.source_domain)}
            </Badge>
            {preferredShiftLabel ? (
              <Badge variant="neutral" size="sm">
                Turno {preferredShiftLabel}
              </Badge>
            ) : null}
            {awaitingOutcome ? (
              <Badge variant="info" size="sm">
                Aguardando resultado
              </Badge>
            ) : null}
          </div>
          <div>
            <p className="truncate text-base font-semibold text-lovable-ink">{item.subject_name}</p>
            <p className="mt-1 text-sm font-medium text-lovable-ink">
              Fazer agora: {primaryActionLabel || item.recommended_action}
            </p>
            <p className="mt-1 line-clamp-2 text-sm text-lovable-ink-muted">{item.operator_summary}</p>
          </div>
        </div>
      </div>
    </button>
  );
}

function RecommendationInspector({
  item,
  intelligenceContext,
  isIntelligenceLoading,
  isIntelligenceError,
  operatorNote,
  onRetryIntelligence,
  onOperatorNoteChange,
  onReject,
  onPreparePrimaryAction,
  onConfirmPrimaryAction,
  onOutcomeChange,
  isMutating,
  lastActionResult,
}: {
  item: AITriageRecommendation;
  intelligenceContext: LeadToMemberIntelligenceContext | null;
  isIntelligenceLoading: boolean;
  isIntelligenceError: boolean;
  operatorNote: string;
  onRetryIntelligence: () => void;
  onOperatorNoteChange: (value: string) => void;
  onReject: () => void;
  onPreparePrimaryAction: () => void;
  onConfirmPrimaryAction: () => void;
  onOutcomeChange: (outcome: Extract<AITriageOutcomeState, "positive" | "neutral" | "negative">) => void;
  isMutating: boolean;
  lastActionResult: AITriageSafeActionResult | null;
}) {
  const navigate = useNavigate();
  const [confirmExplicitApproval, setConfirmExplicitApproval] = useState(false);
  const needsManualFallback = !item.recommended_channel || !item.recommended_owner?.role;
  const metadataEntries = Object.entries(item.metadata ?? {}).slice(0, 4);
  const awaitingOutcome = isAwaitingOutcome(item);
  const primaryActionType = resolvePrimaryActionType(item);
  const primaryActionLabel = resolvePrimaryActionLabel(item, primaryActionType);
  const canExecutePrimaryAction =
    !!primaryActionType && item.approval_state !== "rejected" && !awaitingOutcome;
  const needsExplicitApproval = requiresExplicitApproval(item);

  useEffect(() => {
    setConfirmExplicitApproval(false);
  }, [item.id]);

  return (
    <div className="rounded-[28px] border border-lovable-border bg-lovable-surface/90 p-5 shadow-panel backdrop-blur-xl">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant={getPriorityTone(item.priority_bucket)}>{item.priority_bucket}</Badge>
            <Badge variant="neutral">{formatDomainLabel(item.source_domain)}</Badge>
            {needsExplicitApproval ? <Badge variant="warning">Confirmacao obrigatoria</Badge> : null}
            {awaitingOutcome ? <Badge variant="info">Aguardando resultado</Badge> : null}
          </div>
          <div>
            <h2 className="font-heading text-2xl font-bold tracking-tight text-lovable-ink">{item.subject_name}</h2>
            <p className="mt-1 max-w-2xl text-sm text-lovable-ink-muted">{item.operator_summary}</p>
          </div>
        </div>
      </div>

      <div className="mt-6 space-y-5">
        <section className="space-y-3">
          <div className="rounded-[24px] border border-lovable-border bg-lovable-bg-muted/45 p-4">
            <p className="text-[11px] uppercase tracking-[0.18em] text-lovable-ink-muted">Fazer agora</p>
            <p className="mt-2 text-base font-semibold text-lovable-ink">{item.recommended_action}</p>
            <div className="mt-3 flex flex-wrap gap-2 text-xs text-lovable-ink-muted">
              <span>Canal: {formatChannelLabel(item.recommended_channel)}</span>
              <span>
                Responsavel: {item.recommended_owner?.label ?? item.recommended_owner?.role ?? "Definir manualmente"}
              </span>
            </div>
          </div>

          <div className="rounded-[24px] border border-lovable-border bg-lovable-bg-muted/45 p-4">
            <p className="text-[11px] uppercase tracking-[0.18em] text-lovable-ink-muted">
              {item.suggested_message ? "Mensagem pronta" : "Resumo da acao"}
            </p>
            <p className="mt-2 whitespace-pre-wrap text-sm text-lovable-ink">
              {item.suggested_message ?? item.expected_impact}
            </p>
          </div>

          {item.member_id ? (
            <MemberIntelligenceMiniCard
              context={intelligenceContext}
              isLoading={isIntelligenceLoading}
              isError={isIntelligenceError}
              onRetry={onRetryIntelligence}
              title="Contexto canonico para executar"
            />
          ) : null}
        </section>

        <section className="space-y-3">
          <div className="rounded-[24px] border border-lovable-border bg-lovable-bg-muted/45 p-4">
            <p className="text-[11px] uppercase tracking-[0.18em] text-lovable-ink-muted">Acao operacional</p>

            <div className="mt-4 space-y-3">
              {canExecutePrimaryAction ? (
                needsExplicitApproval ? (
                  confirmExplicitApproval ? (
                    <div className="rounded-[20px] border border-[hsl(var(--lovable-warning)/0.35)] bg-[hsl(var(--lovable-warning)/0.08)] p-4">
                      <p className="text-sm font-semibold text-lovable-ink">
                        Confirmar aprovacao e preparar a acao agora?
                      </p>
                      <p className="mt-1 text-sm text-lovable-ink-muted">
                        Este item esta em estado critico ou degradado e precisa de confirmacao humana antes da preparacao.
                      </p>
                      <div className="mt-4 flex flex-wrap gap-2">
                        <Button variant="primary" onClick={onConfirmPrimaryAction} disabled={isMutating}>
                          {isMutating ? <Loader2 size={15} className="animate-spin" /> : <ArrowRight size={15} />}
                          Confirmar e preparar
                        </Button>
                        <Button variant="secondary" onClick={() => setConfirmExplicitApproval(false)} disabled={isMutating}>
                          Cancelar
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <Button variant="primary" onClick={() => setConfirmExplicitApproval(true)} disabled={isMutating}>
                      {isMutating ? <Loader2 size={15} className="animate-spin" /> : <ArrowRight size={15} />}
                      Aprovar e preparar acao
                    </Button>
                  )
                  ) : (
                    <Button variant="primary" onClick={onPreparePrimaryAction} disabled={isMutating}>
                      {isMutating ? <Loader2 size={15} className="animate-spin" /> : <ArrowRight size={15} />}
                      {primaryActionLabel || "Executar proxima acao"}
                    </Button>
                  )
                ) : item.approval_state === "rejected" ? (
                <div className="rounded-[20px] border border-[hsl(var(--lovable-danger)/0.35)] bg-[hsl(var(--lovable-danger)/0.08)] p-4 text-sm text-lovable-ink-muted">
                  Este item foi rejeitado. Use o contexto detalhado para revisar antes de reabrir manualmente.
                </div>
              ) : awaitingOutcome ? (
                <div className="rounded-[20px] border border-lovable-border bg-lovable-surface/85 p-4 text-sm text-lovable-ink-muted">
                  A acao principal ja foi preparada. O proximo passo agora e registrar o resultado observado.
                </div>
              ) : null}

              <Textarea
                className="min-h-[92px]"
                placeholder="Observacao opcional para esta acao"
                value={operatorNote}
                onChange={(event) => onOperatorNoteChange(event.target.value)}
              />

              <div className="flex flex-wrap gap-2">
                <Button
                  variant="secondary"
                  onClick={() => {
                    if (item.member_id) {
                      navigate(`/assessments/members/${item.member_id}`);
                      return;
                    }
                    navigate("/tasks");
                  }}
                >
                  <ClipboardList size={15} />
                  Abrir contexto
                </Button>
                {shouldOfferAssessmentShortcut(item) ? (
                  <Button
                    variant="secondary"
                    onClick={() => {
                      if (item.member_id) {
                        navigate(`/assessments/members/${item.member_id}`);
                      }
                    }}
                  >
                    Abrir avaliacao
                  </Button>
                ) : null}
                {item.approval_state !== "rejected" ? (
                  <Button variant="danger" onClick={onReject} disabled={isMutating}>
                    <XCircle size={15} />
                    Rejeitar
                  </Button>
                ) : null}
              </div>

              {lastActionResult ? (
                <div className="rounded-[22px] border border-lovable-border bg-lovable-surface/85 px-4 py-3">
                  <p className="text-[11px] uppercase tracking-[0.18em] text-lovable-ink-muted">Ultima acao preparada</p>
                  <p className="mt-1 text-sm font-semibold text-lovable-ink">{lastActionResult.detail}</p>
                  {lastActionResult.prepared_message ? (
                    <p className="mt-3 whitespace-pre-wrap text-sm text-lovable-ink">{lastActionResult.prepared_message}</p>
                  ) : null}
                </div>
              ) : null}
            </div>
          </div>
        </section>

        {item.show_outcome_step ? (
          <section className="space-y-3">
            <div className="rounded-[24px] border border-lovable-border bg-lovable-bg-muted/45 p-4">
              <div className="flex flex-wrap items-center gap-2">
                <p className="text-[11px] uppercase tracking-[0.18em] text-lovable-ink-muted">Registrar resultado</p>
                <Badge variant="neutral">Atual: {formatOutcomeLabel(item.outcome_state)}</Badge>
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                <Button variant="primary" onClick={() => onOutcomeChange("positive")} disabled={isMutating}>
                  Marcar positivo
                </Button>
                <Button variant="secondary" onClick={() => onOutcomeChange("neutral")} disabled={isMutating}>
                  Marcar neutro
                </Button>
                <Button variant="danger" onClick={() => onOutcomeChange("negative")} disabled={isMutating}>
                  Marcar negativo
                </Button>
              </div>
            </div>
          </section>
        ) : null}

        <details className="rounded-[24px] border border-lovable-border bg-lovable-bg-muted/35 p-4">
          <summary className="cursor-pointer list-none text-sm font-semibold text-lovable-ink">Ver detalhes analiticos</summary>
          <div className="mt-4 space-y-4">
            <div className="rounded-[22px] border border-lovable-border bg-lovable-bg-muted/45 p-4">
              <p className="text-[11px] uppercase tracking-[0.18em] text-lovable-ink-muted">Por que entrou agora</p>
              <p className="mt-2 text-sm text-lovable-ink">{item.why_now_summary}</p>
              <ul className="mt-3 space-y-2 text-sm text-lovable-ink-muted">
                {item.why_now_details.map((detail, index) => (
                  <li key={`${detail}-${index}`} className="flex items-start gap-2">
                    <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-[hsl(var(--lovable-primary))]" />
                    <span>{detail}</span>
                  </li>
                ))}
              </ul>
            </div>

            {needsManualFallback ? (
              <div className="rounded-[22px] border border-[hsl(var(--lovable-warning)/0.35)] bg-[hsl(var(--lovable-warning)/0.08)] p-4">
                <div className="flex items-start gap-3">
                  <AlertTriangle size={18} className="mt-0.5 shrink-0 text-[hsl(var(--lovable-warning))]" />
                  <div>
                    <p className="text-sm font-semibold text-lovable-ink">Estado degradado</p>
                    <p className="mt-1 text-sm text-lovable-ink-muted">
                      Este item ainda depende de complemento humano para owner ou canal antes da execucao segura.
                    </p>
                  </div>
                </div>
              </div>
            ) : null}

            <div className="grid gap-3 xl:grid-cols-2">
              {metadataEntries.length ? (
                metadataEntries.map(([key, value]) => (
                  <div key={key} className="rounded-[22px] border border-lovable-border bg-lovable-bg-muted/45 px-4 py-3">
                    <p className="text-[11px] uppercase tracking-[0.18em] text-lovable-ink-muted">{formatMetadataLabel(key)}</p>
                    <p className="mt-1 text-sm font-medium text-lovable-ink">{formatMetadataValue(value)}</p>
                  </div>
                ))
              ) : (
                <div className="rounded-[22px] border border-lovable-border bg-lovable-bg-muted/45 px-4 py-3 text-sm text-lovable-ink-muted">
                  Nenhum metadado adicional foi anexado a esta recommendation.
                </div>
              )}
            </div>
          </div>
        </details>
      </div>
    </div>
  );
}

export default function AITriageInboxPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [workflowFilter, setWorkflowFilter] = useState<WorkflowFilter>("do_now");
  const [shiftScopeEnabled, setShiftScopeEnabled] = useState(true);
  const [operatorNote, setOperatorNote] = useState("");
  const [lastActionResult, setLastActionResult] = useState<AITriageSafeActionResult | null>(null);
  const deferredQuery = useDeferredValue(query.trim().toLowerCase());
  const currentUserShift = user?.work_shift ?? null;

  const metricsQuery = useQuery({
    queryKey: ["ai-triage", "metrics"],
    queryFn: () => aiTriageService.getMetricsSummary(),
    staleTime: 60_000,
  });

  const listQuery = useQuery({
    queryKey: ["ai-triage", "items"],
    queryFn: () => aiTriageService.listItems(),
    staleTime: 60_000,
  });

  const items = listQuery.data?.items ?? [];
  const scopedItems = useMemo(() => {
    if (!currentUserShift || !shiftScopeEnabled) {
      return items;
    }
    return items.filter((item) => {
      const preferredShift = String(item.metadata?.preferred_shift ?? "");
      return !preferredShift || matchesPreferredShift(preferredShift, currentUserShift);
    });
  }, [currentUserShift, items, shiftScopeEnabled]);

  const filteredItems = useMemo(() => {
    return scopedItems.filter((item) => {
      if (!matchesWorkflowFilter(item, workflowFilter)) {
        return false;
      }
      if (!deferredQuery) {
        return true;
      }
      const haystack = [
        item.subject_name,
        item.operator_summary,
        item.recommended_action,
        item.primary_action_label ?? "",
        formatDomainLabel(item.source_domain),
      ]
        .join(" ")
        .toLowerCase();
      return haystack.includes(deferredQuery);
    });
  }, [deferredQuery, scopedItems, workflowFilter]);

  useEffect(() => {
    if (!filteredItems.length) {
      setSelectedId(null);
      return;
    }
    if (!selectedId || !filteredItems.some((item) => item.id === selectedId)) {
      setSelectedId(filteredItems[0]?.id ?? null);
    }
  }, [filteredItems, selectedId]);

  useEffect(() => {
    setLastActionResult(null);
    setOperatorNote("");
  }, [selectedId]);

  const detailQuery = useQuery({
    queryKey: ["ai-triage", "item", selectedId],
    queryFn: () => aiTriageService.getItem(selectedId!),
    enabled: Boolean(selectedId),
    placeholderData: () => filteredItems.find((item) => item.id === selectedId),
    staleTime: 60_000,
  });

  const rejectMutation = useMutation({
    mutationFn: ({ recommendationId }: { recommendationId: string }) =>
      aiTriageService.updateApproval(recommendationId, {
        decision: "rejected",
        note: operatorNote.trim() || undefined,
      }),
    onSuccess: (item) => {
      toast.success("Recommendation rejeitada.");
      setOperatorNote("");
      setLastActionResult(null);
      void queryClient.invalidateQueries({ queryKey: ["ai-triage", "items"] });
      void queryClient.invalidateQueries({ queryKey: ["ai-triage", "item", item.id] });
      void queryClient.invalidateQueries({ queryKey: ["ai-triage", "metrics"] });
    },
    onError: () => {
      toast.error("Erro ao rejeitar a recommendation.");
    },
  });

  const prepareActionMutation = useMutation({
    mutationFn: ({
      recommendationId,
      action,
      autoApprove,
      confirmApproval,
    }: {
      recommendationId: string;
      action: AITriageSafeActionType;
      autoApprove?: boolean;
      confirmApproval?: boolean;
    }) => {
      const note = operatorNote.trim() || undefined;
      return aiTriageService
        .prepareAction(recommendationId, {
          action,
          operator_note: note,
          auto_approve: autoApprove,
          confirm_approval: confirmApproval,
        })
        .catch(async (error: unknown) => {
          if ((autoApprove || confirmApproval) && getHttpStatus(error) === 409) {
            await aiTriageService.updateApproval(recommendationId, {
              decision: "approved",
              note,
            });
            return aiTriageService.prepareAction(recommendationId, {
              action,
              operator_note: note,
            });
          }
          throw error;
        });
    },
    onSuccess: (result) => {
      setLastActionResult(result);
      setOperatorNote("");
      if (result.supported) {
        toast.success(result.detail);
      } else {
        toast.error(result.detail);
      }
      void queryClient.invalidateQueries({ queryKey: ["ai-triage", "items"] });
      void queryClient.invalidateQueries({ queryKey: ["ai-triage", "item", result.recommendation.id] });
      void queryClient.invalidateQueries({ queryKey: ["ai-triage", "metrics"] });
    },
    onError: (error: unknown) => {
      const message = getHttpDetail(error) || (error instanceof Error ? error.message : "Erro ao preparar a acao principal.");
      toast.error(message);
    },
  });

  const outcomeMutation = useMutation({
    mutationFn: ({
      recommendationId,
      outcome,
    }: {
      recommendationId: string;
      outcome: Extract<AITriageOutcomeState, "positive" | "neutral" | "negative">;
    }) =>
      aiTriageService.updateOutcome(recommendationId, {
        outcome,
        note: operatorNote.trim() || undefined,
      }),
    onSuccess: (item) => {
      toast.success("Resultado registrado.");
      setOperatorNote("");
      void queryClient.invalidateQueries({ queryKey: ["ai-triage", "items"] });
      void queryClient.invalidateQueries({ queryKey: ["ai-triage", "item", item.id] });
      void queryClient.invalidateQueries({ queryKey: ["ai-triage", "metrics"] });
    },
    onError: () => {
      toast.error("Erro ao registrar o resultado.");
    },
  });

  const selectedItem =
    detailQuery.data ??
    filteredItems.find((item) => item.id === selectedId) ??
    filteredItems[0] ??
    null;

  const intelligenceContextQuery = useQuery({
    queryKey: ["members", "intelligence-context", selectedItem?.member_id],
    queryFn: async () => {
      if (!selectedItem?.member_id) {
        throw new Error("MEMBRO_INVALIDO");
      }
      return memberService.getIntelligenceContext(selectedItem.member_id);
    },
    enabled: Boolean(selectedItem?.member_id),
    staleTime: 60_000,
  });

  const isMutating = rejectMutation.isPending || prepareActionMutation.isPending || outcomeMutation.isPending;
  const metrics = metricsQuery.data;

  const doNowCount = scopedItems.filter((item) => matchesWorkflowFilter(item, "do_now")).length;
  const awaitingOutcomeCount = scopedItems.filter((item) => matchesWorkflowFilter(item, "awaiting_outcome")).length;

  return (
    <div className="space-y-6">
      <PageHeader
        title="AI Triage Inbox"
        subtitle="Fila de execucao para agir rapido, preparar a acao certa e fechar o resultado depois."
        actions={
          <Button variant="secondary" onClick={() => void listQuery.refetch()} disabled={listQuery.isFetching}>
            {listQuery.isFetching ? <Loader2 size={15} className="animate-spin" /> : <RefreshCw size={15} />}
            Atualizar inbox
          </Button>
        }
      />

      <div className="rounded-[24px] border border-lovable-border bg-lovable-surface/88 p-4 shadow-panel">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div className="relative min-w-0 flex-1 lg:max-w-md">
            <Search size={15} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-lovable-ink-muted" />
            <Input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Buscar por aluno, motivo ou proxima acao..."
              className="pl-9"
            />
          </div>
          <div className="flex flex-wrap gap-2">
            {currentUserShift ? (
              <Button
                variant={shiftScopeEnabled ? "primary" : "secondary"}
                size="sm"
                onClick={() => setShiftScopeEnabled((value) => !value)}
              >
                {shiftScopeEnabled ? `Meu turno: ${getPreferredShiftLabel(currentUserShift)}` : "Todos os turnos"}
              </Button>
            ) : null}
            {([
              ["do_now", `Fazer agora (${doNowCount})`],
              ["awaiting_outcome", `Aguardando resultado (${awaitingOutcomeCount})`],
              ["all", `Todos (${scopedItems.length})`],
            ] as const).map(([value, label]) => (
              <Button
                key={value}
                variant={workflowFilter === value ? "primary" : "secondary"}
                size="sm"
                onClick={() => setWorkflowFilter(value)}
              >
                {label}
              </Button>
            ))}
          </div>
        </div>
      </div>

      <details className="rounded-[24px] border border-lovable-border bg-lovable-surface/88 p-4 shadow-panel">
        <summary className="cursor-pointer list-none text-sm font-semibold text-lovable-ink">
          Ver metricas da inbox
        </summary>
        <div className="mt-4">
          <KPIStrip
            items={[
              { label: "Pendentes", value: metrics?.pending_approval_total ?? items.filter((item) => item.approval_state === "pending").length, tone: "warning" },
              { label: "Aguardando resultado", value: awaitingOutcomeCount, tone: "neutral" },
              { label: "Preparadas", value: metrics?.prepared_action_total ?? 0, tone: "warning" },
              { label: "Aceitacao", value: formatPercentage(metrics?.acceptance_rate), tone: "success" },
              { label: "Tempo medio", value: formatApprovalTime(metrics?.average_time_to_approval_seconds), tone: "neutral" },
            ]}
          />
        </div>
      </details>

      {listQuery.isLoading ? (
        <div className="rounded-[28px] border border-lovable-border bg-lovable-surface px-4 py-3">
          <SkeletonList rows={8} cols={4} />
        </div>
      ) : listQuery.isError ? (
        <EmptyState
          icon={XCircle}
          title="Erro ao carregar a inbox AI-first"
          description="A camada de agregacao nao respondeu. Continue pelo fluxo manual enquanto a inbox e recarregada."
          action={{ label: "Tentar novamente", onClick: () => void listQuery.refetch() }}
        />
      ) : !items.length ? (
        <EmptyState
          icon={Bot}
          title="Nenhuma recommendation ativa"
          description="A inbox ainda nao encontrou sinais suficientes de retencao ou onboarding para sugerir acoes."
        />
      ) : (
        <div className="grid gap-5 xl:grid-cols-[minmax(340px,0.9fr)_minmax(0,1.1fr)]">
          <div className="space-y-4">
            <SectionHeader
              title="Fila de execucao"
              subtitle="Abra o item, prepare a proxima acao e registre o resultado depois."
              count={filteredItems.length}
            />
            {filteredItems.length ? (
              <div className="space-y-3">
                {filteredItems.map((item) => (
                  <RecommendationListItem
                    key={item.id}
                    item={item}
                    isSelected={item.id === selectedId}
                    onSelect={() => setSelectedId(item.id)}
                  />
                ))}
              </div>
            ) : (
              <EmptyState
                icon={Search}
                title="Nenhum item encontrado"
                description="Ajuste os filtros ou remova a busca para voltar a fila completa."
              />
            )}
          </div>

          <div>
            {!selectedItem && selectedId && detailQuery.isLoading ? (
              <div className="rounded-[28px] border border-lovable-border bg-lovable-surface px-4 py-3">
                <SkeletonList rows={10} cols={3} />
              </div>
            ) : detailQuery.isError && !selectedItem ? (
              <EmptyState
                icon={AlertTriangle}
                title="Erro ao carregar a recommendation"
                description="A fila esta disponivel, mas o detalhe selecionado nao respondeu."
                action={selectedId ? { label: "Recarregar detalhe", onClick: () => void detailQuery.refetch() } : undefined}
              />
            ) : selectedItem ? (
              <RecommendationInspector
                item={selectedItem}
                intelligenceContext={intelligenceContextQuery.data ?? null}
                isIntelligenceLoading={intelligenceContextQuery.isLoading}
                isIntelligenceError={intelligenceContextQuery.isError}
                operatorNote={operatorNote}
                onRetryIntelligence={() => void intelligenceContextQuery.refetch()}
                onOperatorNoteChange={setOperatorNote}
                onReject={() => rejectMutation.mutate({ recommendationId: selectedItem.id })}
                onPreparePrimaryAction={() =>
                  prepareActionMutation.mutate({
                    recommendationId: selectedItem.id,
                    action: resolvePrimaryActionType(selectedItem) as AITriageSafeActionType,
                    autoApprove: selectedItem.approval_state !== "approved" && !requiresExplicitApproval(selectedItem),
                  })
                }
                onConfirmPrimaryAction={() =>
                  prepareActionMutation.mutate({
                    recommendationId: selectedItem.id,
                    action: resolvePrimaryActionType(selectedItem) as AITriageSafeActionType,
                    confirmApproval: true,
                  })
                }
                onOutcomeChange={(outcome) => outcomeMutation.mutate({ recommendationId: selectedItem.id, outcome })}
                isMutating={isMutating}
                lastActionResult={lastActionResult}
              />
            ) : (
              <EmptyState
                icon={Sparkles}
                title="Selecione um item"
                description="Escolha uma recommendation na fila para abrir a proxima acao."
              />
            )}
          </div>
        </div>
      )}
    </div>
  );
}
