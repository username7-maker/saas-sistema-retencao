import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

import { LoadingPanel } from "../../components/common/LoadingPanel";
import { Badge, Button, Card, CardContent, CardDescription, CardHeader, CardTitle, Input } from "../../components/ui2";
import { memberService } from "../../services/memberService";
import { taskService } from "../../services/taskService";
import type { Member, Task } from "../../types";

const statusSequence: Task["status"][] = ["todo", "doing", "done"];

const STATUS_LABELS: Record<Task["status"], string> = {
  todo: "A fazer",
  doing: "Em andamento",
  done: "Concluida",
  cancelled: "Cancelada",
};

const PRIORITY_LABELS: Record<Task["priority"], string> = {
  low: "Baixa",
  medium: "Media",
  high: "Alta",
  urgent: "Urgente",
};

type PlanType = "mensal" | "semestral" | "anual";
type PlanFilter = "all" | PlanType;

const PLAN_FILTER_LABELS: Record<PlanFilter, string> = {
  all: "Todos",
  mensal: "Mensal",
  semestral: "Semestral",
  anual: "Anual",
};

function nextStatus(currentStatus: Task["status"]): Task["status"] {
  const index = statusSequence.indexOf(currentStatus);
  if (index === -1 || index === statusSequence.length - 1) return "done";
  return statusSequence[index + 1];
}

function taskSource(task: Task): string {
  const source = task.extra_data?.source;
  return typeof source === "string" ? source : "";
}

function taskPlanType(task: Task): string {
  const planType = task.extra_data?.plan_type;
  return typeof planType === "string" ? planType : "";
}

function normalizePlanType(rawValue: string | null | undefined): PlanType | null {
  const value = (rawValue ?? "").toLowerCase();
  if (value.includes("anual")) return "anual";
  if (value.includes("semestral")) return "semestral";
  if (value.includes("mensal")) return "mensal";
  return null;
}

function detectPlanTypeFromName(planName: string | null | undefined): PlanType {
  return normalizePlanType(planName) ?? "mensal";
}

function formatPlanType(planType: string): string {
  if (!planType) return "Mensal";
  return planType.charAt(0).toUpperCase() + planType.slice(1);
}

function formatDueDate(value: string | null): string {
  if (!value) return "Sem vencimento";
  const dueDateKey = getDueDateKey(value);
  if (!dueDateKey) return "Sem vencimento";
  const [year, month, day] = dueDateKey.split("-");
  if (!year || !month || !day) return "Sem vencimento";
  return `${day}/${month}/${year}`;
}

function statusVariant(status: Task["status"]): "neutral" | "success" | "warning" | "danger" {
  if (status === "done") return "success";
  if (status === "doing") return "warning";
  if (status === "cancelled") return "danger";
  return "neutral";
}

function priorityVariant(priority: Task["priority"]): "neutral" | "success" | "warning" | "danger" {
  if (priority === "urgent") return "danger";
  if (priority === "high") return "warning";
  if (priority === "low") return "success";
  return "neutral";
}

function getTodayKey(): string {
  const now = new Date();
  const offsetMs = now.getTimezoneOffset() * 60_000;
  return new Date(now.getTime() - offsetMs).toISOString().slice(0, 10);
}

function getDueDateKey(value: string | null): string | null {
  if (!value) return null;
  if (value.length >= 10) {
    return value.slice(0, 10);
  }
  return null;
}

function isTaskDueTodayOrPast(task: Task, todayKey: string): boolean {
  const dueDateKey = getDueDateKey(task.due_date);
  if (!dueDateKey) return true;
  return dueDateKey <= todayKey;
}

async function listAllMembers(): Promise<Member[]> {
  const pageSize = 200;
  const firstPage = await memberService.listMembers({ page: 1, page_size: pageSize });
  const totalPages = Math.ceil(firstPage.total / pageSize);

  if (totalPages <= 1) {
    return firstPage.items;
  }

  const promises: Array<Promise<Awaited<ReturnType<typeof memberService.listMembers>>>> = [];
  for (let page = 2; page <= totalPages; page += 1) {
    promises.push(memberService.listMembers({ page, page_size: pageSize }));
  }

  const rest = await Promise.all(promises);
  return [...firstPage.items, ...rest.flatMap((page) => page.items)];
}

interface TaskGroup {
  key: string;
  label: string;
  memberId: string | null;
  leadId: string | null;
  planType: PlanType | null;
  tasks: Task[];
  todoCount: number;
  doingCount: number;
  doneCount: number;
}

function taskDestination(task: Task): string {
  if (task.member_id) {
    return `/assessments/members/${task.member_id}`;
  }
  if (task.lead_id) {
    return `/crm?leadId=${task.lead_id}`;
  }
  return "/tasks";
}

function groupDestination(group: TaskGroup): string {
  if (group.memberId) {
    return `/assessments/members/${group.memberId}`;
  }
  return "/crm";
}

export function TasksPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [showDone, setShowDone] = useState(false);
  const [planFilter, setPlanFilter] = useState<PlanFilter>("all");

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

  const updateMutation = useMutation({
    mutationFn: ({ taskId, status }: { taskId: string; status: Task["status"] }) => taskService.updateTask(taskId, status),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["tasks"] });
    },
  });

  const memberNameById = useMemo(() => {
    const map = new Map<string, string>();
    for (const member of membersQuery.data ?? []) {
      map.set(member.id, member.full_name);
    }
    return map;
  }, [membersQuery.data]);

  const memberPlanTypeById = useMemo(() => {
    const map = new Map<string, PlanType>();
    for (const member of membersQuery.data ?? []) {
      map.set(member.id, detectPlanTypeFromName(member.plan_name));
    }
    return map;
  }, [membersQuery.data]);

  const allTasks = tasksQuery.data?.items ?? [];
  const todayKey = useMemo(() => getTodayKey(), []);
  const hiddenFutureCount = useMemo(
    () => allTasks.filter((task) => !isTaskDueTodayOrPast(task, todayKey)).length,
    [allTasks, todayKey],
  );
  const filteredByStatus = useMemo(() => {
    const visibleByDueDate = allTasks.filter((task) => isTaskDueTodayOrPast(task, todayKey));
    if (showDone) return visibleByDueDate;
    return visibleByDueDate.filter((task) => task.status !== "done");
  }, [allTasks, showDone, todayKey]);

  const groups = useMemo(() => {
    const draft = new Map<string, TaskGroup>();

    for (const task of filteredByStatus) {
      const key = task.member_id
        ? `member:${task.member_id}`
        : task.lead_id
          ? `lead:${task.lead_id}`
          : "unlinked";

      const label = task.member_id
        ? memberNameById.get(task.member_id) ?? `Aluno ${task.member_id.slice(0, 8)}`
        : task.lead_id
          ? "Leads sem aluno (CRM)"
          : "Tasks sem vinculo";

      const current = draft.get(key) ?? {
        key,
        label,
        memberId: task.member_id,
        leadId: task.lead_id,
        planType: task.member_id
          ? (memberPlanTypeById.get(task.member_id) ?? normalizePlanType(taskPlanType(task)))
          : normalizePlanType(taskPlanType(task)),
        tasks: [],
        todoCount: 0,
        doingCount: 0,
        doneCount: 0,
      };

      if (!current.planType) {
        current.planType = normalizePlanType(taskPlanType(task));
      }
      if (!current.planType && task.member_id) {
        current.planType = memberPlanTypeById.get(task.member_id) ?? null;
      }

      current.tasks.push(task);
      if (task.status === "todo") current.todoCount += 1;
      if (task.status === "doing") current.doingCount += 1;
      if (task.status === "done") current.doneCount += 1;

      draft.set(key, current);
    }

    const normalizedSearch = search.trim().toLowerCase();

    return [...draft.values()]
      .map((group) => ({
        ...group,
        tasks: [...group.tasks].sort((a, b) => {
          const aDue = a.due_date ? new Date(a.due_date).getTime() : Number.MAX_SAFE_INTEGER;
          const bDue = b.due_date ? new Date(b.due_date).getTime() : Number.MAX_SAFE_INTEGER;
          return aDue - bDue;
        }),
      }))
      .filter((group) => {
        if (planFilter !== "all") {
          if (!group.memberId) return false;
          if (group.planType !== planFilter) return false;
        }
        if (!normalizedSearch) return true;
        if (group.label.toLowerCase().includes(normalizedSearch)) return true;
        return group.tasks.some((task) => task.title.toLowerCase().includes(normalizedSearch));
      })
      .sort((a, b) => {
        const pendingA = a.todoCount + a.doingCount;
        const pendingB = b.todoCount + b.doingCount;
        if (pendingA !== pendingB) return pendingB - pendingA;
        return a.label.localeCompare(b.label);
      });
  }, [filteredByStatus, memberNameById, memberPlanTypeById, planFilter, search]);

  if (tasksQuery.isLoading) {
    return <LoadingPanel text="Carregando tasks..." />;
  }

  if (!tasksQuery.data) {
    return <LoadingPanel text="Nao foi possivel carregar tasks." />;
  }

  const totalTasks = allTasks.length;
  const pendingTasks = allTasks.filter((task) => task.status !== "done").length;

  return (
    <section className="space-y-6">
      <header className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="font-heading text-3xl font-bold text-lovable-ink">Tasks por Aluno</h2>
            <p className="text-sm text-lovable-ink-muted">
              Visual mais limpo: cada bloco representa um aluno. Clique na task para abrir o destino correto.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="neutral">Total: {totalTasks}</Badge>
            <Badge variant="warning">Pendentes: {pendingTasks}</Badge>
            {hiddenFutureCount > 0 ? <Badge variant="neutral">Futuras ocultas: {hiddenFutureCount}</Badge> : null}
            <Button variant={showDone ? "secondary" : "ghost"} size="sm" onClick={() => setShowDone((prev) => !prev)}>
              {showDone ? "Ocultar concluidas" : "Mostrar concluidas"}
            </Button>
          </div>
        </div>

        <Input
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Buscar por nome do aluno ou titulo da task..."
          className="max-w-xl"
        />

        <div className="flex flex-wrap gap-2">
          {(Object.keys(PLAN_FILTER_LABELS) as PlanFilter[]).map((filterKey) => (
            <Button
              key={filterKey}
              variant={planFilter === filterKey ? "secondary" : "ghost"}
              size="sm"
              onClick={() => setPlanFilter(filterKey)}
            >
              {PLAN_FILTER_LABELS[filterKey]}
            </Button>
          ))}
        </div>
      </header>

      {!groups.length ? (
        <Card>
          <CardContent className="py-10 text-center text-sm text-lovable-ink-muted">
            Nenhuma task encontrada para os filtros atuais.
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {groups.map((group) => (
            <Card key={group.key}>
              <CardHeader className="pb-3">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <CardTitle>{group.label}</CardTitle>
                    <CardDescription>
                      {group.tasks.length} tasks | {group.todoCount} a fazer | {group.doingCount} em andamento
                    </CardDescription>
                  </div>
                  <div className="flex items-center gap-2">
                    {group.planType ? <Badge variant="neutral">Plano {formatPlanType(group.planType)}</Badge> : null}
                    <Badge variant="neutral">Todo {group.todoCount}</Badge>
                    <Badge variant="warning">Doing {group.doingCount}</Badge>
                    {showDone ? <Badge variant="success">Done {group.doneCount}</Badge> : null}
                    <Button variant="secondary" size="sm" onClick={() => navigate(groupDestination(group))}>
                      Abrir destino
                    </Button>
                  </div>
                </div>
              </CardHeader>

              <CardContent className="space-y-2 pt-0">
                {group.tasks.map((task) => {
                  const source = taskSource(task);
                  const planType = taskPlanType(task);

                  return (
                    <article
                      key={task.id}
                      className="cursor-pointer rounded-xl border border-lovable-border bg-lovable-surface-soft p-3 transition hover:bg-lovable-primary-soft/30"
                      onClick={() => navigate(taskDestination(task))}
                    >
                      <div className="flex flex-wrap items-start justify-between gap-2">
                        <div>
                          <p className="text-sm font-semibold text-lovable-ink">{task.title}</p>
                          {task.description ? (
                            <p className="mt-1 text-xs text-lovable-ink-muted">{task.description}</p>
                          ) : null}
                        </div>
                        <div className="flex flex-wrap gap-1">
                          <Badge variant={statusVariant(task.status)}>{STATUS_LABELS[task.status]}</Badge>
                          <Badge variant={priorityVariant(task.priority)}>{PRIORITY_LABELS[task.priority]}</Badge>
                          {source === "onboarding" ? <Badge variant="neutral">Onboarding</Badge> : null}
                          {source === "plan_followup" ? (
                            <Badge variant="neutral">Plano {formatPlanType(planType)}</Badge>
                          ) : null}
                        </div>
                      </div>

                      <div className="mt-2 flex flex-wrap items-center justify-between gap-2 text-xs text-lovable-ink-muted">
                        <span>Vencimento: {formatDueDate(task.due_date)}</span>
                        {task.status !== "done" ? (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={(event) => {
                              event.stopPropagation();
                              updateMutation.mutate({ taskId: task.id, status: nextStatus(task.status) });
                            }}
                            disabled={updateMutation.isPending}
                          >
                            Avancar
                          </Button>
                        ) : null}
                      </div>
                    </article>
                  );
                })}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </section>
  );
}
