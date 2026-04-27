import { useDeferredValue, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, CalendarClock, CheckCircle2, ClipboardCheck, Clock3, ExternalLink, Forward, MessageCircle, Search, XCircle } from "lucide-react";
import { useNavigate } from "react-router-dom";
import toast from "react-hot-toast";

import { EmptyState, SkeletonList } from "../ui";
import { Badge, Button, Input, Textarea, cn } from "../ui2";
import { useAuth } from "../../hooks/useAuth";
import {
  workQueueService,
  type WorkQueueListState,
  type WorkQueueShiftFilter,
  type WorkQueueSourceFilter,
} from "../../services/workQueueService";
import type { WorkQueueItem, WorkQueueOutcome } from "../../types";
import { getPreferredShiftLabel } from "../../utils/preferredShift";

type QueueMode = "do_now" | "awaiting_outcome" | "all";

interface WorkExecutionViewProps {
  source?: WorkQueueSourceFilter;
  title?: string;
  subtitle?: string;
  compact?: boolean;
}

const outcomeOptions: Array<{ value: WorkQueueOutcome; label: string; icon: typeof CheckCircle2 }> = [
  { value: "responded", label: "Respondeu", icon: MessageCircle },
  { value: "scheduled_assessment", label: "Agendou avaliacao", icon: CalendarClock },
  { value: "will_return", label: "Vai retornar", icon: CheckCircle2 },
  { value: "no_response", label: "Sem resposta", icon: Clock3 },
  { value: "postponed", label: "Adiar", icon: Clock3 },
  { value: "forwarded_to_trainer", label: "Encaminhar professor", icon: Forward },
  { value: "forwarded_to_reception", label: "Encaminhar recepcao", icon: Forward },
  { value: "not_interested", label: "Sem interesse", icon: XCircle },
  { value: "invalid_number", label: "Numero invalido", icon: XCircle },
  { value: "completed", label: "Concluido", icon: ClipboardCheck },
];

function itemKey(item: WorkQueueItem): string {
  return `${item.source_type}:${item.source_id}`;
}

function severityVariant(severity: string): "danger" | "warning" | "info" | "success" | "neutral" {
  if (severity === "critical" || severity === "high") return "danger";
  if (severity === "medium") return "warning";
  if (severity === "low") return "info";
  return "neutral";
}

function formatDomain(domain: string): string {
  if (domain === "retention") return "Retencao";
  if (domain === "onboarding") return "Onboarding";
  if (domain === "assessment") return "Avaliacao";
  if (domain === "commercial") return "Comercial";
  if (domain === "manual") return "Manual";
  return domain;
}

function formatDueAt(value: string | null): string {
  if (!value) return "Sem prazo";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Prazo informado";
  return new Intl.DateTimeFormat("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" }).format(date);
}

function getShiftLabel(shift: string | null): string {
  if (!shift || shift === "unassigned") return "Sem turno";
  return getPreferredShiftLabel(shift) || shift;
}

function normalizePhoneForAction(phone: string | null): string | null {
  const digits = (phone || "").replace(/\D/g, "");
  if (digits.length < 8) return null;
  if (digits.startsWith("55")) return digits;
  if (digits.length === 10 || digits.length === 11) return `55${digits}`;
  return digits;
}

function buildWhatsAppUrl(item: WorkQueueItem): string | null {
  const phone = normalizePhoneForAction(item.subject_phone);
  if (!phone) return null;
  const message = item.suggested_message || item.primary_action_label || "";
  return `https://wa.me/${phone}${message ? `?text=${encodeURIComponent(message)}` : ""}`;
}

function buildTelUrl(item: WorkQueueItem): string | null {
  const phone = normalizePhoneForAction(item.subject_phone);
  return phone ? `tel:+${phone}` : null;
}

function getHttpDetail(error: unknown): string {
  if (typeof error === "object" && error !== null && "response" in error) {
    const response = (error as { response?: { data?: { detail?: string }; status?: number } }).response;
    if (typeof response?.data?.detail === "string") return response.data.detail;
    if (typeof response?.status === "number") return `Erro ${response.status}`;
  }
  return "Operacao nao concluida.";
}

function filterItems(items: WorkQueueItem[], search: string): WorkQueueItem[] {
  const normalizedSearch = search.trim().toLowerCase();
  if (!normalizedSearch) return items;
  return items.filter((item) => {
    const haystack = [
      item.subject_name,
      item.reason,
      item.primary_action_label,
      item.domain,
      item.severity,
      item.suggested_message ?? "",
      getShiftLabel(item.preferred_shift),
    ]
      .join(" ")
      .toLowerCase();
    return haystack.includes(normalizedSearch);
  });
}

function QueueCard({ item, selected, onSelect }: { item: WorkQueueItem; selected: boolean; onSelect: () => void }) {
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
        <Badge variant="neutral" size="sm">
          {formatDomain(item.domain)}
        </Badge>
        <Badge variant="neutral" size="sm">
          Turno {getShiftLabel(item.preferred_shift)}
        </Badge>
      </div>

      <div className="mt-3 space-y-1">
        <p className="truncate text-base font-semibold text-lovable-ink">{item.subject_name}</p>
        <p className="text-sm font-semibold text-lovable-ink">Fazer agora: {item.primary_action_label}</p>
        <p className="line-clamp-2 text-sm text-lovable-ink-muted">{item.reason}</p>
      </div>

      <div className="mt-3 flex items-center justify-between gap-3 text-xs text-lovable-ink-muted">
        <span>{item.source_type === "ai_triage" ? "AI Inbox" : "Task"}</span>
        <span>{formatDueAt(item.due_at)}</span>
      </div>
    </button>
  );
}

export function WorkExecutionView({
  source = "all",
  title = "Modo execucao",
  subtitle = "Fila curta por turno: execute, registre o resultado e siga para o proximo aluno.",
  compact = false,
}: WorkExecutionViewProps) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const [mode, setMode] = useState<QueueMode>("do_now");
  const [shiftFilter, setShiftFilter] = useState<WorkQueueShiftFilter>("my_shift");
  const [search, setSearch] = useState("");
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [operatorNote, setOperatorNote] = useState("");
  const [confirmingKey, setConfirmingKey] = useState<string | null>(null);

  const deferredSearch = useDeferredValue(search);
  const canSeeAllShifts = user?.role === "owner" || user?.role === "manager";

  const sharedParams = {
    shift: shiftFilter,
    assignee: "all" as const,
    domain: "all" as const,
    source,
    page: 1,
    page_size: 25,
  };

  const doNowQuery = useQuery({
    queryKey: ["work-queue", "items", "do_now", source, shiftFilter],
    queryFn: () => workQueueService.listItems({ ...sharedParams, state: "do_now" }),
    staleTime: 60 * 1000,
  });

  const awaitingQuery = useQuery({
    queryKey: ["work-queue", "items", "awaiting_outcome", source, shiftFilter],
    queryFn: () => workQueueService.listItems({ ...sharedParams, state: "awaiting_outcome" }),
    staleTime: 60 * 1000,
  });

  const allQuery = useQuery({
    queryKey: ["work-queue", "items", "all", source, shiftFilter],
    queryFn: () => workQueueService.listItems({ ...sharedParams, state: "all" as WorkQueueListState }),
    enabled: mode === "all",
    staleTime: 60 * 1000,
  });

  const activeQuery = mode === "awaiting_outcome" ? awaitingQuery : mode === "all" ? allQuery : doNowQuery;
  const activeItems = activeQuery.data?.items ?? [];
  const filteredItems = useMemo(() => filterItems(activeItems, deferredSearch), [activeItems, deferredSearch]);
  const selectedItem = useMemo(
    () => filteredItems.find((item) => itemKey(item) === selectedKey) ?? filteredItems[0] ?? null,
    [filteredItems, selectedKey],
  );

  const executeMutation = useMutation({
    mutationFn: ({ item, confirmed }: { item: WorkQueueItem; confirmed: boolean }) =>
      workQueueService.executeItem(item.source_type, item.source_id, {
        auto_approve: !item.requires_confirmation,
        confirm_approval: confirmed,
        operator_note: operatorNote.trim() || null,
      }),
    onSuccess: (result) => {
      setConfirmingKey(null);
      setOperatorNote("");
      setSelectedKey(itemKey(result.item));
      void queryClient.invalidateQueries({ queryKey: ["work-queue"] });
      void queryClient.invalidateQueries({ queryKey: ["tasks"] });
      void queryClient.invalidateQueries({ queryKey: ["ai-triage"] });
      toast.success(result.detail || "Acao preparada.");
    },
    onError: (error) => toast.error(getHttpDetail(error)),
  });

  const outcomeMutation = useMutation({
    mutationFn: ({ item, outcome }: { item: WorkQueueItem; outcome: WorkQueueOutcome }) =>
      workQueueService.updateOutcome(item.source_type, item.source_id, {
        outcome,
        note: operatorNote.trim() || null,
      }),
    onSuccess: (result) => {
      setOperatorNote("");
      setSelectedKey(itemKey(result.item));
      void queryClient.invalidateQueries({ queryKey: ["work-queue"] });
      void queryClient.invalidateQueries({ queryKey: ["tasks"] });
      void queryClient.invalidateQueries({ queryKey: ["ai-triage"] });
      toast.success("Resultado registrado.");
    },
    onError: (error) => toast.error(getHttpDetail(error)),
  });

  function selectItem(item: WorkQueueItem) {
    setSelectedKey(itemKey(item));
    setConfirmingKey(null);
    setOperatorNote("");
  }

  function executeSelected() {
    if (!selectedItem) return;
    if (selectedItem.requires_confirmation && confirmingKey !== itemKey(selectedItem)) {
      setConfirmingKey(itemKey(selectedItem));
      return;
    }
    executeMutation.mutate({ item: selectedItem, confirmed: selectedItem.requires_confirmation });
  }

  const isLoading = activeQuery.isLoading || doNowQuery.isLoading || awaitingQuery.isLoading;
  const isError = activeQuery.isError || doNowQuery.isError || awaitingQuery.isError;
  const isMutating = executeMutation.isPending || outcomeMutation.isPending;
  const selectedRequiresConfirmation = selectedItem?.requires_confirmation && confirmingKey === itemKey(selectedItem);
  const selectedWhatsAppUrl = selectedItem ? buildWhatsAppUrl(selectedItem) : null;
  const selectedTelUrl = selectedItem ? buildTelUrl(selectedItem) : null;

  function markExecutionStartedForAction(item: WorkQueueItem) {
    if (item.state !== "do_now") return;
    if (item.requires_confirmation) {
      setConfirmingKey(itemKey(item));
      return;
    }
    executeMutation.mutate({ item, confirmed: false });
  }

  async function copySuggestedMessage(item: WorkQueueItem) {
    const message = item.suggested_message || item.primary_action_label;
    if (!message) {
      toast.error("Nao ha mensagem pronta para copiar.");
      return;
    }
    try {
      await navigator.clipboard.writeText(message);
      toast.success("Mensagem copiada.");
    } catch {
      toast.error("Nao foi possivel copiar a mensagem.");
    }
  }

  function openWhatsAppAction(item: WorkQueueItem) {
    const url = buildWhatsAppUrl(item);
    if (!url) {
      toast.error("Este aluno nao tem telefone valido para WhatsApp.");
      return;
    }
    window.open(url, "_blank", "noopener,noreferrer");
    markExecutionStartedForAction(item);
  }

  return (
    <section className={cn("space-y-5", compact ? "pt-1" : "")}>
      <div className="rounded-[28px] border border-lovable-border bg-lovable-surface/72 p-4 shadow-panel">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.35em] text-lovable-ink-muted">Fila unificada</p>
            <h2 className="mt-1 text-2xl font-bold text-lovable-ink">{title}</h2>
            <p className="mt-1 max-w-3xl text-sm text-lovable-ink-muted">{subtitle}</p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <Button size="sm" variant={mode === "do_now" ? "primary" : "secondary"} onClick={() => setMode("do_now")}>
              Fazer agora ({doNowQuery.data?.total ?? 0})
            </Button>
            <Button
              size="sm"
              variant={mode === "awaiting_outcome" ? "primary" : "secondary"}
              onClick={() => setMode("awaiting_outcome")}
            >
              Aguardando resultado ({awaitingQuery.data?.total ?? 0})
            </Button>
            <Button size="sm" variant={mode === "all" ? "primary" : "secondary"} onClick={() => setMode("all")}>
              Todos
            </Button>
            <Button
              size="sm"
              variant={shiftFilter === "my_shift" ? "secondary" : "ghost"}
              onClick={() => setShiftFilter("my_shift")}
            >
              Meu turno
            </Button>
            {canSeeAllShifts ? (
              <Button size="sm" variant={shiftFilter === "all" ? "secondary" : "ghost"} onClick={() => setShiftFilter("all")}>
                Todos os turnos
              </Button>
            ) : null}
          </div>
        </div>

        <div className="mt-4 flex max-w-2xl items-center gap-2 rounded-2xl border border-lovable-border bg-lovable-bg-muted/80 px-3">
          <Search className="h-4 w-4 text-lovable-ink-muted" />
          <Input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Buscar aluno, motivo ou acao..."
            className="border-0 bg-transparent px-0 shadow-none focus:ring-0"
          />
        </div>
      </div>

      {isLoading ? (
        <div className="rounded-[28px] border border-lovable-border bg-lovable-surface p-5">
          <SkeletonList rows={6} cols={3} />
        </div>
      ) : isError ? (
        <div className="rounded-[28px] border border-lovable-border bg-lovable-surface px-4 py-10 text-center text-sm text-lovable-danger">
          Erro ao carregar a fila operacional. Tente novamente.
        </div>
      ) : filteredItems.length === 0 ? (
        <EmptyState
          title="Nenhuma acao nessa fila"
          description="Troque o filtro de turno ou abra Todos para revisar o restante da operacao."
          icon={ClipboardCheck}
        />
      ) : (
        <div className="grid gap-5 xl:grid-cols-[minmax(340px,0.9fr)_minmax(460px,1.1fr)]">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.35em] text-lovable-ink-muted">
                  {mode === "awaiting_outcome" ? "Aguardando resultado" : mode === "all" ? "Fila completa" : "Fazer agora"}
                </p>
                <p className="mt-1 text-sm text-lovable-ink-muted">
                  Mostrando ate 25 acoes. Total disponivel: {activeQuery.data?.total ?? filteredItems.length}.
                </p>
              </div>
            </div>

            {filteredItems.map((item) => (
              <QueueCard
                key={itemKey(item)}
                item={item}
                selected={selectedItem ? itemKey(item) === itemKey(selectedItem) : false}
                onSelect={() => selectItem(item)}
              />
            ))}
          </div>

          {selectedItem ? (
            <aside className="sticky top-24 h-fit rounded-[28px] border border-lovable-border bg-lovable-surface/92 p-5 shadow-panel">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant={severityVariant(selectedItem.severity)}>{selectedItem.severity}</Badge>
                    <Badge variant="neutral">{formatDomain(selectedItem.domain)}</Badge>
                    {selectedItem.requires_confirmation ? <Badge variant="warning">Confirmacao</Badge> : null}
                  </div>
                  <h3 className="mt-3 text-2xl font-bold text-lovable-ink">{selectedItem.subject_name}</h3>
                  <p className="mt-1 text-sm text-lovable-ink-muted">
                    Turno {getShiftLabel(selectedItem.preferred_shift)} · {formatDueAt(selectedItem.due_at)}
                  </p>
                </div>
              </div>

              <div className="mt-5 space-y-4">
                <div className="rounded-2xl border border-lovable-border bg-lovable-bg-muted/70 p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.24em] text-lovable-ink-muted">Fazer agora</p>
                  <p className="mt-2 text-base font-bold text-lovable-ink">{selectedItem.primary_action_label}</p>
                  <p className="mt-2 text-sm text-lovable-ink-muted">{selectedItem.reason}</p>
                </div>

                <div className="rounded-2xl border border-lovable-border bg-lovable-bg-muted/70 p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.24em] text-lovable-ink-muted">Mensagem pronta</p>
                  <p className="mt-2 whitespace-pre-wrap text-sm font-medium text-lovable-ink">
                    {selectedItem.suggested_message || "Sem mensagem automatica. Use o contexto e registre o resultado da acao."}
                  </p>
                </div>

                <div className="rounded-2xl border border-lovable-border bg-lovable-bg-muted/70 p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.24em] text-lovable-ink-muted">Acao operacional</p>

                  <div className="mt-3 grid gap-2 sm:grid-cols-2">
                    <Button
                      size="sm"
                      className="justify-start"
                      onClick={() => openWhatsAppAction(selectedItem)}
                      disabled={isMutating || !selectedWhatsAppUrl}
                    >
                      <MessageCircle className="h-4 w-4" />
                      Abrir WhatsApp
                    </Button>
                    <Button
                      size="sm"
                      variant="secondary"
                      className="justify-start"
                      onClick={() => copySuggestedMessage(selectedItem)}
                      disabled={isMutating || !selectedItem.suggested_message}
                    >
                      <ClipboardCheck className="h-4 w-4" />
                      Copiar mensagem
                    </Button>
                    <Button
                      size="sm"
                      variant="secondary"
                      className="justify-start"
                      onClick={() => selectedTelUrl && window.open(selectedTelUrl, "_self")}
                      disabled={isMutating || !selectedTelUrl}
                    >
                      <MessageCircle className="h-4 w-4" />
                      Ligar agora
                    </Button>
                    {selectedItem.context_path ? (
                      <Button size="sm" variant="secondary" className="justify-start" onClick={() => navigate(selectedItem.context_path || "/tasks")}>
                        <ExternalLink className="h-4 w-4" />
                        Abrir contexto
                      </Button>
                    ) : null}
                  </div>

                  {selectedRequiresConfirmation ? (
                    <div className="mt-4 rounded-2xl border border-[hsl(var(--lovable-warning)/0.35)] bg-[hsl(var(--lovable-warning)/0.08)] p-4">
                      <p className="text-sm font-bold text-lovable-ink">Confirmar preparacao?</p>
                      <p className="mt-1 text-sm text-lovable-ink-muted">
                        Este item e critico ou degradado. A preparacao exige confirmacao humana curta.
                      </p>
                      <div className="mt-4 flex flex-wrap gap-2">
                        <Button size="sm" onClick={executeSelected} disabled={isMutating}>
                          <ArrowRight className="h-4 w-4" />
                          Confirmar e comecar
                        </Button>
                        <Button size="sm" variant="secondary" onClick={() => setConfirmingKey(null)} disabled={isMutating}>
                          Cancelar
                        </Button>
                      </div>
                    </div>
                  ) : selectedItem.state === "awaiting_outcome" ? (
                    <p className="mt-4 text-sm text-lovable-ink-muted">
                      Acao ja preparada. Registre o resultado assim que houver retorno.
                    </p>
                  ) : (
                    <Button className="mt-4" onClick={executeSelected} disabled={isMutating}>
                      <ArrowRight className="h-4 w-4" />
                      Comecar execucao
                    </Button>
                  )}

                  <Textarea
                    value={operatorNote}
                    onChange={(event) => setOperatorNote(event.target.value)}
                    placeholder="Observacao opcional para esta acao"
                    className="mt-4"
                  />

                  <div className="mt-4 grid gap-2 sm:grid-cols-3">
                    <Button
                      size="sm"
                      variant="secondary"
                      className="justify-start"
                      onClick={() => outcomeMutation.mutate({ item: selectedItem, outcome: "completed" })}
                      disabled={isMutating}
                    >
                      <CheckCircle2 className="h-4 w-4" />
                      Concluir
                    </Button>
                    <Button
                      size="sm"
                      variant="secondary"
                      className="justify-start"
                      onClick={() => outcomeMutation.mutate({ item: selectedItem, outcome: "no_response" })}
                      disabled={isMutating}
                    >
                      <Clock3 className="h-4 w-4" />
                      Sem resposta
                    </Button>
                    <Button
                      size="sm"
                      variant="secondary"
                      className="justify-start"
                      onClick={() => outcomeMutation.mutate({ item: selectedItem, outcome: "postponed" })}
                      disabled={isMutating}
                    >
                      <CalendarClock className="h-4 w-4" />
                      Adiar 2 dias
                    </Button>
                  </div>
                </div>

                <div className="rounded-2xl border border-lovable-border bg-lovable-bg-muted/70 p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.24em] text-lovable-ink-muted">Registrar resultado rapido</p>
                  <div className="mt-3 grid gap-2 sm:grid-cols-2">
                    {outcomeOptions.map((option) => {
                      const Icon = option.icon;
                      return (
                        <Button
                          key={option.value}
                          size="sm"
                          variant={["not_interested", "invalid_number"].includes(option.value) ? "danger" : "secondary"}
                          className="justify-start"
                          onClick={() => outcomeMutation.mutate({ item: selectedItem, outcome: option.value })}
                          disabled={isMutating}
                        >
                          <Icon className="h-4 w-4" />
                          {option.label}
                        </Button>
                      );
                    })}
                  </div>
                </div>

                <details className="rounded-2xl border border-lovable-border bg-lovable-bg-muted/55 p-4">
                  <summary className="cursor-pointer text-sm font-semibold text-lovable-ink">Ver detalhes</summary>
                  <dl className="mt-3 grid gap-2 text-xs text-lovable-ink-muted sm:grid-cols-2">
                    <div>
                      <dt className="uppercase tracking-[0.18em]">Origem</dt>
                      <dd className="mt-1 font-semibold text-lovable-ink">{selectedItem.source_type}</dd>
                    </div>
                    <div>
                      <dt className="uppercase tracking-[0.18em]">Estado</dt>
                      <dd className="mt-1 font-semibold text-lovable-ink">{selectedItem.state}</dd>
                    </div>
                    <div>
                      <dt className="uppercase tracking-[0.18em]">Acao</dt>
                      <dd className="mt-1 font-semibold text-lovable-ink">{selectedItem.primary_action_type}</dd>
                    </div>
                    <div>
                      <dt className="uppercase tracking-[0.18em]">Responsavel</dt>
                      <dd className="mt-1 font-semibold text-lovable-ink">{selectedItem.assigned_to_user_id || "Sem responsavel"}</dd>
                    </div>
                  </dl>
                </details>
              </div>
            </aside>
          ) : null}
        </div>
      )}
    </section>
  );
}
