import { useDeferredValue, useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, ExternalLink, Search } from "lucide-react";
import { useNavigate } from "react-router-dom";
import toast from "react-hot-toast";

import { EmptyState, SkeletonList } from "../ui";
import { Badge, Button, Input, cn } from "../ui2";
import { coachWorkspaceService, type CoachWorkspaceItem, type CoachWorkspaceShift, type CoachWorkspaceState } from "../../services/coachWorkspaceService";
import { workQueueService } from "../../services/workQueueService";
import { useAuth } from "../../hooks/useAuth";
import type { WorkQueueOutcome } from "../../types";
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
