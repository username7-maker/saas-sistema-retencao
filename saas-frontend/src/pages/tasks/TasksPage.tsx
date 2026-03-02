import { useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import toast from "react-hot-toast";

import { LoadingPanel } from "../../components/common/LoadingPanel";
import { Badge, Button, Card, CardContent, CardHeader, CardTitle, Input } from "../../components/ui2";
import { memberService } from "../../services/memberService";
import { taskService, type CreateTaskPayload } from "../../services/taskService";
import type { Member, Task } from "../../types";

// ─── Constants ───────────────────────────────────────────────────────────────

const statusSequence: Task["status"][] = ["todo", "doing", "done"];

const STATUS_LABELS: Record<Task["status"], string> = {
  todo: "A fazer",
  doing: "Em andamento",
  done: "Concluída",
  cancelled: "Cancelada",
};

const PRIORITY_LABELS: Record<Task["priority"], string> = {
  low: "Baixa",
  medium: "Média",
  high: "Alta",
  urgent: "Urgente",
};

type SourceFilter = "all" | "onboarding" | "plan_followup" | "automation" | "manual";
type PlanFilter = "all" | "mensal" | "semestral" | "anual";

const SOURCE_FILTER_LABELS: Record<SourceFilter, string> = {
  all: "Todas",
  onboarding: "Onboarding",
  plan_followup: "Follow-up",
  automation: "Automação",
  manual: "Manual",
};

const PLAN_FILTER_LABELS: Record<PlanFilter, string> = {
  all: "Todos planos",
  mensal: "Mensal",
  semestral: "Semestral",
  anual: "Anual",
};

// ─── Helpers ─────────────────────────────────────────────────────────────────

function nextStatus(current: Task["status"]): Task["status"] {
  const idx = statusSequence.indexOf(current);
  if (idx === -1 || idx === statusSequence.length - 1) return "done";
  return statusSequence[idx + 1];
}

function taskSource(task: Task): string {
  const src = task.extra_data?.source;
  return typeof src === "string" ? src : "manual";
}

function taskPlanType(task: Task): string {
  const pt = task.extra_data?.plan_type;
  return typeof pt === "string" ? pt : "";
}

function normalizePlanType(val: string | null | undefined): "mensal" | "semestral" | "anual" | null {
  const v = (val ?? "").toLowerCase();
  if (v.includes("anual")) return "anual";
  if (v.includes("semestral")) return "semestral";
  if (v.includes("mensal")) return "mensal";
  return null;
}

function detectPlanFromMember(planName: string | null | undefined): "mensal" | "semestral" | "anual" {
  return normalizePlanType(planName) ?? "mensal";
}

function getTodayKey(): string {
  const now = new Date();
  return new Date(now.getTime() - now.getTimezoneOffset() * 60_000).toISOString().slice(0, 10);
}

function getDueDateKey(val: string | null): string | null {
  return val && val.length >= 10 ? val.slice(0, 10) : null;
}

function formatDueDate(val: string | null): string {
  const key = getDueDateKey(val);
  if (!key) return "Sem vencimento";
  const [y, m, d] = key.split("-");
  return `${d}/${m}/${y}`;
}

function isOverdue(task: Task, todayKey: string): boolean {
  if (task.status === "done" || task.status === "cancelled") return false;
  const key = getDueDateKey(task.due_date);
  return key !== null && key < todayKey;
}

function isDueTodayOrPast(task: Task, todayKey: string): boolean {
  const key = getDueDateKey(task.due_date);
  if (!key) return true;
  return key <= todayKey;
}

function statusVariant(s: Task["status"]): "neutral" | "success" | "warning" | "danger" {
  if (s === "done") return "success";
  if (s === "doing") return "warning";
  if (s === "cancelled") return "danger";
  return "neutral";
}

function priorityVariant(p: Task["priority"]): "neutral" | "success" | "warning" | "danger" {
  if (p === "urgent") return "danger";
  if (p === "high") return "warning";
  if (p === "low") return "success";
  return "neutral";
}

function formatPlanLabel(planType: string): string {
  if (!planType) return "Mensal";
  return planType.charAt(0).toUpperCase() + planType.slice(1);
}

async function listAllMembers(): Promise<Member[]> {
  const PAGE = 200;
  const first = await memberService.listMembers({ page: 1, page_size: PAGE });
  const pages = Math.ceil(first.total / PAGE);
  if (pages <= 1) return first.items;
  const rest = await Promise.all(
    Array.from({ length: pages - 1 }, (_, i) =>
      memberService.listMembers({ page: i + 2, page_size: PAGE }).then((r) => r.items),
    ),
  );
  return [...first.items, ...rest.flat()];
}

// ─── Interfaces ───────────────────────────────────────────────────────────────

interface TaskGroup {
  key: string;
  label: string;
  memberId: string | null;
  leadId: string | null;
  planType: "mensal" | "semestral" | "anual" | null;
  tasks: Task[];
  todoCount: number;
  doingCount: number;
  doneCount: number;
}

// ─── Create Task Modal ────────────────────────────────────────────────────────

interface CreateModalProps {
  members: Member[];
  onClose: () => void;
  onSubmit: (payload: CreateTaskPayload) => void;
  isPending: boolean;
}

function CreateTaskModal({ members, onClose, onSubmit, isPending }: CreateModalProps) {
  const formRef = useRef<HTMLFormElement>(null);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!formRef.current) return;
    const fd = new FormData(formRef.current);
    const title = (fd.get("title") as string).trim();
    if (!title) return;
    const memberId = (fd.get("member_id") as string) || undefined;
    const description = (fd.get("description") as string).trim() || undefined;
    const priority = (fd.get("priority") as Task["priority"]) || "medium";
    const dueDate = (fd.get("due_date") as string) || undefined;
    onSubmit({
      title,
      description,
      member_id: memberId,
      priority,
      status: "todo",
      due_date: dueDate ? `${dueDate}T00:00:00Z` : null,
    });
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" onClick={onClose}>
      <div
        className="w-full max-w-md rounded-2xl border border-lovable-border bg-lovable-surface p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="mb-4 text-lg font-bold text-lovable-ink">Nova Tarefa</h3>
        <form ref={formRef} onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="mb-1 block text-xs font-medium text-lovable-ink-muted">Título *</label>
            <Input name="title" required minLength={3} maxLength={160} placeholder="Título da tarefa" />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-lovable-ink-muted">Descrição</label>
            <textarea
              name="description"
              rows={2}
              className="w-full rounded-xl border border-lovable-border bg-lovable-surface-soft px-3 py-2 text-sm text-lovable-ink placeholder:text-lovable-ink-muted focus:outline-none focus:ring-2 focus:ring-lovable-primary"
              placeholder="Detalhes da tarefa (opcional)"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-lovable-ink-muted">Aluno</label>
            <select
              name="member_id"
              className="w-full rounded-xl border border-lovable-border bg-lovable-surface-soft px-3 py-2 text-sm text-lovable-ink focus:outline-none focus:ring-2 focus:ring-lovable-primary"
            >
              <option value="">— Nenhum —</option>
              {members.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.full_name}
                </option>
              ))}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-xs font-medium text-lovable-ink-muted">Prioridade</label>
              <select
                name="priority"
                defaultValue="medium"
                className="w-full rounded-xl border border-lovable-border bg-lovable-surface-soft px-3 py-2 text-sm text-lovable-ink focus:outline-none focus:ring-2 focus:ring-lovable-primary"
              >
                <option value="low">Baixa</option>
                <option value="medium">Média</option>
                <option value="high">Alta</option>
                <option value="urgent">Urgente</option>
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-lovable-ink-muted">Vencimento</label>
              <input
                type="date"
                name="due_date"
                className="w-full rounded-xl border border-lovable-border bg-lovable-surface-soft px-3 py-2 text-sm text-lovable-ink focus:outline-none focus:ring-2 focus:ring-lovable-primary"
              />
            </div>
          </div>
          <div className="flex gap-2 pt-2">
            <Button type="button" variant="ghost" size="sm" onClick={onClose} disabled={isPending}>
              Cancelar
            </Button>
            <Button type="submit" variant="primary" size="sm" disabled={isPending}>
              {isPending ? "Salvando..." : "Criar tarefa"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export function TasksPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [search, setSearch] = useState("");
  const [showDone, setShowDone] = useState(false);
  const [planFilter, setPlanFilter] = useState<PlanFilter>("all");
  const [sourceFilter, setSourceFilter] = useState<SourceFilter>("all");
  const [createOpen, setCreateOpen] = useState(false);
  const [expandedMessages, setExpandedMessages] = useState<Set<string>>(new Set());
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null);

  // ── Queries ────────────────────────────────────────────────────────────────
  const tasksQuery = useQuery({
    queryKey: ["tasks"],
    queryFn: taskService.listTasks,
    staleTime: 5 * 60 * 1000,
  });

  const membersQuery = useQuery({
    queryKey: ["members", "all-index"],
    queryFn: listAllMembers,
    staleTime: 10 * 60 * 1000,
  });

  // ── Mutations ──────────────────────────────────────────────────────────────
  const updateMutation = useMutation({
    mutationFn: ({ taskId, status }: { taskId: string; status: Task["status"] }) =>
      taskService.updateTask(taskId, { status }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["tasks"] }),
    onError: () => toast.error("Erro ao atualizar tarefa."),
  });

  const deleteMutation = useMutation({
    mutationFn: (taskId: string) => taskService.deleteTask(taskId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["tasks"] });
      setPendingDeleteId(null);
      toast.success("Tarefa excluída.");
    },
    onError: () => toast.error("Erro ao excluir tarefa."),
  });

  const createMutation = useMutation({
    mutationFn: (payload: CreateTaskPayload) => taskService.createTask(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["tasks"] });
      setCreateOpen(false);
      toast.success("Tarefa criada.");
    },
    onError: () => toast.error("Erro ao criar tarefa."),
  });

  // ── Derived data ───────────────────────────────────────────────────────────
  const memberPlanById = useMemo(() => {
    const map = new Map<string, "mensal" | "semestral" | "anual">();
    for (const m of membersQuery.data ?? []) {
      map.set(m.id, detectPlanFromMember(m.plan_name));
    }
    return map;
  }, [membersQuery.data]);

  const allTasks = tasksQuery.data?.items ?? [];
  const todayKey = useMemo(() => getTodayKey(), []);

  const pendingDeleteTask = useMemo(
    () => (pendingDeleteId ? allTasks.find((t) => t.id === pendingDeleteId) : null),
    [pendingDeleteId, allTasks],
  );

  const hiddenFutureCount = useMemo(
    () => allTasks.filter((t) => !isDueTodayOrPast(t, todayKey)).length,
    [allTasks, todayKey],
  );

  const filtered = useMemo(() => {
    let list = allTasks.filter((t) => isDueTodayOrPast(t, todayKey));
    if (!showDone) list = list.filter((t) => t.status !== "done");
    if (sourceFilter !== "all") list = list.filter((t) => taskSource(t) === sourceFilter);
    return list;
  }, [allTasks, showDone, sourceFilter, todayKey]);

  const groups = useMemo(() => {
    const draft = new Map<string, TaskGroup>();

    for (const task of filtered) {
      const key = task.member_id ? `member:${task.member_id}` : task.lead_id ? `lead:${task.lead_id}` : "unlinked";

      const label =
        task.member_name ??
        task.lead_name ??
        (task.member_id ? `Aluno ${task.member_id.slice(0, 8)}` : task.lead_id ? "Lead (CRM)" : "Sem vínculo");

      const current = draft.get(key) ?? {
        key,
        label,
        memberId: task.member_id,
        leadId: task.lead_id,
        planType: task.member_id
          ? (memberPlanById.get(task.member_id) ?? normalizePlanType(taskPlanType(task)))
          : normalizePlanType(taskPlanType(task)),
        tasks: [],
        todoCount: 0,
        doingCount: 0,
        doneCount: 0,
      };

      current.tasks.push(task);
      if (task.status === "todo") current.todoCount += 1;
      if (task.status === "doing") current.doingCount += 1;
      if (task.status === "done") current.doneCount += 1;
      draft.set(key, current);
    }

    const normalizedSearch = search.trim().toLowerCase();

    return [...draft.values()]
      .map((g) => ({
        ...g,
        tasks: [...g.tasks].sort((a, b) => {
          const aDue = a.due_date ? new Date(a.due_date).getTime() : Number.MAX_SAFE_INTEGER;
          const bDue = b.due_date ? new Date(b.due_date).getTime() : Number.MAX_SAFE_INTEGER;
          return aDue - bDue;
        }),
      }))
      .filter((g) => {
        if (planFilter !== "all" && g.planType !== planFilter) return false;
        if (!normalizedSearch) return true;
        if (g.label.toLowerCase().includes(normalizedSearch)) return true;
        return g.tasks.some((t) => t.title.toLowerCase().includes(normalizedSearch));
      })
      .sort((a, b) => {
        const pendA = a.todoCount + a.doingCount;
        const pendB = b.todoCount + b.doingCount;
        if (pendA !== pendB) return pendB - pendA;
        return a.label.localeCompare(b.label);
      });
  }, [filtered, memberPlanById, planFilter, search]);

  // ── Handlers ───────────────────────────────────────────────────────────────
  function toggleMessage(taskId: string) {
    setExpandedMessages((prev) => {
      const next = new Set(prev);
      if (next.has(taskId)) next.delete(taskId);
      else next.add(taskId);
      return next;
    });
  }

  function groupDestination(group: TaskGroup): string {
    if (group.memberId) return `/assessments/members/${group.memberId}`;
    return "/crm";
  }

  // ── Loading / Error states ─────────────────────────────────────────────────
  if (tasksQuery.isLoading) return <LoadingPanel text="Carregando tarefas..." />;
  if (tasksQuery.isError) return <LoadingPanel text="Erro ao carregar tarefas. Tente novamente." />;

  const totalTasks = allTasks.length;
  const pendingTasks = allTasks.filter((t) => t.status !== "done" && t.status !== "cancelled").length;
  const overdueTasks = allTasks.filter((t) => isOverdue(t, todayKey)).length;

  return (
    <>
      <section className="space-y-6">
        {/* ── Header ── */}
        <header className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="font-heading text-3xl font-bold text-lovable-ink">Tarefas</h2>
              <p className="text-sm text-lovable-ink-muted">
                Acompanhamento de onboarding, follow-up e ações de retenção por aluno.
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="neutral">Total: {totalTasks}</Badge>
              <Badge variant="warning">Pendentes: {pendingTasks}</Badge>
              {overdueTasks > 0 ? <Badge variant="danger">Atrasadas: {overdueTasks}</Badge> : null}
              {hiddenFutureCount > 0 ? <Badge variant="neutral">Futuras ocultas: {hiddenFutureCount}</Badge> : null}
              <Button variant={showDone ? "secondary" : "ghost"} size="sm" onClick={() => setShowDone((p) => !p)}>
                {showDone ? "Ocultar concluídas" : "Mostrar concluídas"}
              </Button>
              <Button variant="primary" size="sm" onClick={() => setCreateOpen(true)}>
                + Nova Tarefa
              </Button>
            </div>
          </div>

          {/* Search */}
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Buscar por nome do aluno ou título da tarefa..."
            className="max-w-xl"
          />

          {/* Source filter */}
          <div className="flex flex-wrap gap-2">
            {(Object.keys(SOURCE_FILTER_LABELS) as SourceFilter[]).map((k) => (
              <Button
                key={k}
                variant={sourceFilter === k ? "secondary" : "ghost"}
                size="sm"
                onClick={() => setSourceFilter(k)}
              >
                {SOURCE_FILTER_LABELS[k]}
              </Button>
            ))}
          </div>

          {/* Plan filter */}
          <div className="flex flex-wrap gap-2">
            {(Object.keys(PLAN_FILTER_LABELS) as PlanFilter[]).map((k) => (
              <Button
                key={k}
                variant={planFilter === k ? "secondary" : "ghost"}
                size="sm"
                onClick={() => setPlanFilter(k)}
              >
                {PLAN_FILTER_LABELS[k]}
              </Button>
            ))}
          </div>
        </header>

        {/* ── Task Groups ── */}
        {groups.length === 0 ? (
          <Card>
            <CardContent className="py-10 text-center text-sm text-lovable-ink-muted">
              Nenhuma tarefa encontrada para os filtros atuais.
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-4">
            {groups.map((group) => {
              const total = group.todoCount + group.doingCount + group.doneCount;
              const progress = total > 0 ? Math.round((group.doneCount / total) * 100) : 0;

              return (
                <Card key={group.key}>
                  <CardHeader className="pb-3">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div className="min-w-0 flex-1">
                        <CardTitle className="flex items-center gap-2">
                          {group.label}
                          {group.planType ? (
                            <Badge variant="neutral">{formatPlanLabel(group.planType)}</Badge>
                          ) : null}
                        </CardTitle>
                        <p className="mt-1 text-xs text-lovable-ink-muted">
                          {group.tasks.length} tarefa{group.tasks.length !== 1 ? "s" : ""} · {group.todoCount} a
                          fazer · {group.doingCount} em andamento · {group.doneCount} concluída
                          {group.doneCount !== 1 ? "s" : ""}
                        </p>
                        {/* Progress bar */}
                        <div className="mt-2 h-1.5 w-full max-w-xs rounded-full bg-lovable-border">
                          <div
                            className="h-full rounded-full bg-lovable-success transition-all"
                            style={{ width: `${progress}%` }}
                          />
                        </div>
                        <p className="mt-0.5 text-xs text-lovable-ink-muted">{progress}% concluído</p>
                      </div>
                      <Button variant="secondary" size="sm" onClick={() => navigate(groupDestination(group))}>
                        Ver perfil
                      </Button>
                    </div>
                  </CardHeader>

                  <CardContent className="space-y-2 pt-0">
                    {group.tasks.map((task) => {
                      const overdue = isOverdue(task, todayKey);
                      const src = taskSource(task);
                      const planType = taskPlanType(task);
                      const msgExpanded = expandedMessages.has(task.id);

                      return (
                        <article
                          key={task.id}
                          className={`rounded-xl border p-3 transition ${
                            overdue
                              ? "border-red-300 bg-red-50 dark:border-red-800 dark:bg-red-950/30"
                              : "border-lovable-border bg-lovable-surface-soft hover:bg-lovable-primary-soft/20"
                          }`}
                        >
                          {/* Title row */}
                          <div className="flex flex-wrap items-start justify-between gap-2">
                            <div className="min-w-0 flex-1">
                              <p className="text-sm font-semibold text-lovable-ink">{task.title}</p>
                              {task.description ? (
                                <p className="mt-0.5 text-xs text-lovable-ink-muted">{task.description}</p>
                              ) : null}
                            </div>
                            <div className="flex flex-wrap items-center gap-1">
                              <Badge variant={statusVariant(task.status)}>{STATUS_LABELS[task.status]}</Badge>
                              <Badge variant={priorityVariant(task.priority)}>{PRIORITY_LABELS[task.priority]}</Badge>
                              {src === "onboarding" ? <Badge variant="neutral">Onboarding</Badge> : null}
                              {src === "plan_followup" && planType ? (
                                <Badge variant="neutral">Follow-up {formatPlanLabel(planType)}</Badge>
                              ) : null}
                              {src === "automation" ? <Badge variant="neutral">Automação</Badge> : null}
                              {overdue ? <Badge variant="danger">Atrasada</Badge> : null}
                            </div>
                          </div>

                          {/* Suggested message */}
                          {task.suggested_message ? (
                            <div className="mt-2">
                              <button
                                type="button"
                                className="text-xs font-medium text-lovable-primary hover:underline"
                                onClick={() => toggleMessage(task.id)}
                              >
                                {msgExpanded ? "▲ Ocultar mensagem sugerida" : "▼ Ver mensagem sugerida"}
                              </button>
                              {msgExpanded ? (
                                <p className="mt-1 rounded-lg bg-lovable-primary-soft/20 p-2 text-xs text-lovable-ink">
                                  {task.suggested_message}
                                </p>
                              ) : null}
                            </div>
                          ) : null}

                          {/* Footer row */}
                          <div className="mt-2 flex flex-wrap items-center justify-between gap-2">
                            <span
                              className={`text-xs ${overdue ? "font-semibold text-red-600 dark:text-red-400" : "text-lovable-ink-muted"}`}
                            >
                              {overdue ? "⚠ " : ""}Vencimento: {formatDueDate(task.due_date)}
                            </span>
                            <div className="flex items-center gap-1">
                              {task.status !== "done" && task.status !== "cancelled" ? (
                                <>
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    disabled={updateMutation.isPending}
                                    onClick={() => updateMutation.mutate({ taskId: task.id, status: nextStatus(task.status) })}
                                  >
                                    Avançar
                                  </Button>
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    disabled={updateMutation.isPending}
                                    onClick={() => updateMutation.mutate({ taskId: task.id, status: "cancelled" })}
                                  >
                                    Cancelar
                                  </Button>
                                </>
                              ) : null}
                              <Button
                                variant="ghost"
                                size="sm"
                                disabled={deleteMutation.isPending}
                                onClick={() => setPendingDeleteId(task.id)}
                              >
                                Excluir
                              </Button>
                            </div>
                          </div>
                        </article>
                      );
                    })}
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
      </section>

      {/* ── Create Modal ── */}
      {createOpen ? (
        <CreateTaskModal
          members={membersQuery.data ?? []}
          onClose={() => setCreateOpen(false)}
          onSubmit={(p) => createMutation.mutate(p)}
          isPending={createMutation.isPending}
        />
      ) : null}

      {/* ── Delete Confirm Modal ── */}
      {pendingDeleteId ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-sm rounded-2xl border border-lovable-border bg-lovable-surface p-6 shadow-xl">
            <h3 className="mb-2 text-base font-bold text-lovable-ink">Excluir tarefa?</h3>
            <p className="mb-4 text-sm text-lovable-ink-muted">
              <strong>{pendingDeleteTask?.title}</strong>
              <br />
              Esta ação não pode ser desfeita.
            </p>
            <div className="flex gap-2">
              <Button variant="ghost" size="sm" onClick={() => setPendingDeleteId(null)} disabled={deleteMutation.isPending}>
                Cancelar
              </Button>
              <Button
                variant="primary"
                size="sm"
                disabled={deleteMutation.isPending}
                onClick={() => deleteMutation.mutate(pendingDeleteId)}
              >
                {deleteMutation.isPending ? "Excluindo..." : "Confirmar exclusão"}
              </Button>
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}
