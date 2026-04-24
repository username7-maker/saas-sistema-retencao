import type { Member, Task } from "../../types";
import { getPreferredShiftLabel, matchesPreferredShift } from "../../utils/preferredShift";

export const STATUS_LABELS: Record<Task["status"], string> = {
  todo: "A fazer",
  doing: "Em andamento",
  done: "Concluida",
  cancelled: "Cancelada",
};

export const PRIORITY_LABELS: Record<Task["priority"], string> = {
  low: "Baixa",
  medium: "Media",
  high: "Alta",
  urgent: "Critica",
};

export type SourceFilter = "all" | "onboarding" | "plan_followup" | "automation" | "manual";
export type StatusFilter = "all" | Task["status"];
export type PriorityFilter = "all" | Task["priority"];
export type AssigneeFilter = "all" | "unassigned" | string;
export type OperationalViewMode = "triage" | "status";
export type PlanFilter = "all" | "mensal" | "semestral" | "anual";
export type PreferredShiftFilter = "all" | "morning" | "afternoon" | "evening";
export type OnboardingPlaybookKey = "engajado" | "atencao" | "critico";

export interface OperationalFilters {
  search: string;
  status: StatusFilter;
  priority: PriorityFilter;
  assignee: AssigneeFilter;
  source: SourceFilter;
  plan: PlanFilter;
  preferredShift: PreferredShiftFilter;
  onlyMine: boolean;
  overdueOnly: boolean;
  dueTodayOnly: boolean;
  unassignedOnly: boolean;
}

export interface TaskGroup {
  key: string;
  label: string;
  description: string;
  tasks: Task[];
  emptyMessage: string;
}

export interface TaskSlaMeta {
  label: string;
  tone: "neutral" | "warning" | "danger";
}

export interface OperationStats {
  open: number;
  overdue: number;
  highPriority: number;
  mine: number;
  completedToday: number;
}

export const DEFAULT_OPERATIONAL_FILTERS: OperationalFilters = {
  search: "",
  status: "all",
  priority: "all",
  assignee: "all",
  source: "all",
  plan: "all",
  preferredShift: "all",
  onlyMine: false,
  overdueOnly: false,
  dueTodayOnly: false,
  unassignedOnly: false,
};

export const PLAYBOOK_META: Record<
  OnboardingPlaybookKey,
  { label: string; description: string; accentClass: string; surfaceClass: string }
> = {
  engajado: {
    label: "Engajados",
    description: "Score alto e rotina estavel",
    accentClass: "text-emerald-300",
    surfaceClass: "border-emerald-500/20 bg-emerald-500/10",
  },
  atencao: {
    label: "Atencao",
    description: "Precisa de acompanhamento",
    accentClass: "text-amber-300",
    surfaceClass: "border-amber-500/20 bg-amber-500/10",
  },
  critico: {
    label: "Criticos",
    description: "Intervencao humana primeiro",
    accentClass: "text-rose-300",
    surfaceClass: "border-rose-500/20 bg-rose-500/10",
  },
};

export function taskSource(task: Task): string {
  const source = task.extra_data?.source;
  return typeof source === "string" ? source : "manual";
}

export function taskSourceLabel(task: Task): string {
  const source = taskSource(task);
  if (source === "onboarding") return "Onboarding";
  if (source === "plan_followup") return "Follow-up";
  if (source === "automation") return "Automacao";
  if (source === "manual") return "Manual";
  return source;
}

export function taskPlanType(task: Task): string {
  const value = task.extra_data?.plan_type;
  return typeof value === "string" ? value : "";
}

export function normalizePlanType(value: string | null | undefined): "mensal" | "semestral" | "anual" | null {
  const normalized = (value ?? "").toLowerCase();
  if (normalized.includes("anual") || normalized.includes("annual")) return "anual";
  if (normalized.includes("semestral") || normalized.includes("semi")) return "semestral";
  if (normalized.includes("mensal") || normalized.includes("month")) return "mensal";
  return null;
}

export function detectPlanFromMember(planName: string | null | undefined): "mensal" | "semestral" | "anual" {
  return normalizePlanType(planName) ?? "mensal";
}

export function formatPlanLabel(planType: string): string {
  if (!planType) return "Mensal";
  return planType.charAt(0).toUpperCase() + planType.slice(1);
}

export function getTodayKey(): string {
  const now = new Date();
  return new Date(now.getTime() - now.getTimezoneOffset() * 60_000).toISOString().slice(0, 10);
}

export function getDateKey(value: string | null): string | null {
  return value && value.length >= 10 ? value.slice(0, 10) : null;
}

function getDaysBetween(dateKey: string, todayKey: string): number {
  const left = new Date(`${dateKey}T00:00:00Z`).getTime();
  const right = new Date(`${todayKey}T00:00:00Z`).getTime();
  return Math.floor((right - left) / 86_400_000);
}

export function formatDueDate(value: string | null): string {
  const key = getDateKey(value);
  if (!key) return "Sem prazo";
  const [year, month, day] = key.split("-");
  return `${day}/${month}/${year}`;
}

export function formatDateTime(value: string | null): string {
  if (!value) return "Sem registro";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "Sem registro";
  return parsed.toLocaleString("pt-BR");
}

export function isTaskClosed(task: Task): boolean {
  return task.status === "done" || task.status === "cancelled";
}

export function isOverdue(task: Task, todayKey: string): boolean {
  if (isTaskClosed(task)) return false;
  const dueKey = getDateKey(task.due_date);
  return dueKey !== null && dueKey < todayKey;
}

export function isDueToday(task: Task, todayKey: string): boolean {
  if (isTaskClosed(task)) return false;
  const dueKey = getDateKey(task.due_date);
  return dueKey === todayKey;
}

export function isCompletedToday(task: Task, todayKey: string): boolean {
  if (task.status !== "done") return false;
  const completedKey = getDateKey(task.completed_at ?? task.updated_at);
  return completedKey === todayKey;
}

export function isRecentlyCompleted(task: Task, todayKey: string): boolean {
  if (task.status !== "done") return false;
  const completedKey = getDateKey(task.completed_at ?? task.updated_at);
  if (!completedKey) return false;
  return dayDiff(completedKey, todayKey) <= 7;
}

export function isRecentlyCancelled(task: Task, todayKey: string): boolean {
  if (task.status !== "cancelled") return false;
  const key = getDateKey(task.updated_at);
  if (!key) return false;
  return dayDiff(key, todayKey) <= 7;
}

function dayDiff(dateKey: string, todayKey: string): number {
  return Math.abs(getDaysBetween(dateKey, todayKey));
}

function daysUntil(task: Task, todayKey: string): number | null {
  const dueKey = getDateKey(task.due_date);
  if (!dueKey) return null;
  const due = new Date(`${dueKey}T00:00:00Z`).getTime();
  const today = new Date(`${todayKey}T00:00:00Z`).getTime();
  return Math.round((due - today) / 86_400_000);
}

export function getTaskSlaMeta(task: Task, todayKey: string): TaskSlaMeta {
  if (isOverdue(task, todayKey)) {
    const dueKey = getDateKey(task.due_date);
    const days = dueKey ? getDaysBetween(dueKey, todayKey) : 0;
    return {
      label: days <= 1 ? "1 dia atrasada" : `${days} dias atrasada`,
      tone: "danger",
    };
  }

  if (isDueToday(task, todayKey)) {
    return { label: "Vence hoje", tone: "warning" };
  }

  const days = daysUntil(task, todayKey);
  if (days === null) {
    return { label: "Sem prazo", tone: "neutral" };
  }

  if (days <= 7) {
    return {
      label: days === 1 ? "Vence em 1 dia" : `Vence em ${days} dias`,
      tone: "warning",
    };
  }

  return {
    label: days === 1 ? "Vence em 1 dia" : `Vence em ${days} dias`,
    tone: "neutral",
  };
}

function memberPriorityBoost(member: Member | undefined): number {
  if (!member) return 0;
  if (member.risk_level === "red") return 38;
  if (member.risk_level === "yellow") return 18;
  if (member.onboarding_status === "at_risk") return 26;
  return 0;
}

function priorityWeight(priority: Task["priority"]): number {
  if (priority === "urgent") return 110;
  if (priority === "high") return 75;
  if (priority === "medium") return 40;
  return 10;
}

export function getTaskOperationalScore(task: Task, member: Member | undefined, todayKey: string): number {
  if (task.status === "cancelled") return -500;
  if (task.status === "done") return -250;

  let score = priorityWeight(task.priority);

  if (isOverdue(task, todayKey)) {
    score += 180;
  } else if (isDueToday(task, todayKey)) {
    score += 120;
  } else {
    const days = daysUntil(task, todayKey);
    if (days !== null && days > 0) {
      score += Math.max(0, 30 - days * 3);
    }
  }

  if (!task.assigned_to_user_id) score += 34;
  if (task.status === "doing") score += 12;
  if (taskSource(task) === "onboarding") score += 8;

  return score + memberPriorityBoost(member);
}

export function getOperationStats(tasks: Task[], currentUserId: string | null, todayKey: string): OperationStats {
  const openTasks = tasks.filter((task) => !isTaskClosed(task));
  return {
    open: openTasks.length,
    overdue: openTasks.filter((task) => isOverdue(task, todayKey)).length,
    highPriority: openTasks.filter((task) => task.priority === "high" || task.priority === "urgent").length,
    mine: currentUserId ? openTasks.filter((task) => task.assigned_to_user_id === currentUserId).length : 0,
    completedToday: tasks.filter((task) => isCompletedToday(task, todayKey)).length,
  };
}

export function filterOperationalTasks(
  tasks: Task[],
  membersById: Map<string, Member>,
  filters: OperationalFilters,
  currentUserId: string | null,
  todayKey: string,
): Task[] {
  const query = filters.search.trim().toLowerCase();

  return tasks.filter((task) => {
    if (filters.status !== "all" && task.status !== filters.status) return false;
    if (filters.priority !== "all" && task.priority !== filters.priority) return false;
    if (filters.source !== "all" && taskSource(task) !== filters.source) return false;

    const planType = task.member_id
      ? normalizePlanType(membersById.get(task.member_id)?.plan_name) ?? normalizePlanType(taskPlanType(task))
      : normalizePlanType(taskPlanType(task));
    if (filters.plan !== "all" && planType !== filters.plan) return false;
    if (filters.preferredShift !== "all" && task.preferred_shift && !matchesPreferredShift(task.preferred_shift, filters.preferredShift)) {
      return false;
    }

    if (filters.assignee === "unassigned" && task.assigned_to_user_id) return false;
    if (filters.assignee !== "all" && filters.assignee !== "unassigned" && task.assigned_to_user_id !== filters.assignee) {
      return false;
    }

    if (filters.onlyMine && (!currentUserId || task.assigned_to_user_id !== currentUserId)) return false;
    if (filters.overdueOnly && !isOverdue(task, todayKey)) return false;
    if (filters.dueTodayOnly && !isDueToday(task, todayKey)) return false;
    if (filters.unassignedOnly && Boolean(task.assigned_to_user_id)) return false;

    if (!query) return true;
    const haystack = [
      task.title,
      task.description ?? "",
      task.member_name ?? "",
      getPreferredShiftLabel(task.preferred_shift) ?? "",
      task.lead_name ?? "",
      taskSourceLabel(task),
    ]
      .join(" ")
      .toLowerCase();
    return haystack.includes(query);
  });
}

export function getAttentionNowTasks(tasks: Task[], membersById: Map<string, Member>, todayKey: string): Task[] {
  return tasks
    .filter((task) => {
      if (isTaskClosed(task)) return false;
      const member = task.member_id ? membersById.get(task.member_id) : undefined;
      return (
        isOverdue(task, todayKey) ||
        isDueToday(task, todayKey) ||
        task.priority === "high" ||
        task.priority === "urgent" ||
        !task.assigned_to_user_id ||
        member?.risk_level === "red" ||
        member?.risk_level === "yellow" ||
        member?.onboarding_status === "at_risk"
      );
    })
    .sort((left, right) => compareOperationalTasks(left, right, membersById, todayKey))
    .slice(0, 8);
}

function compareOperationalTasks(left: Task, right: Task, membersById: Map<string, Member>, todayKey: string): number {
  const scoreDiff =
    getTaskOperationalScore(right, right.member_id ? membersById.get(right.member_id) : undefined, todayKey) -
    getTaskOperationalScore(left, left.member_id ? membersById.get(left.member_id) : undefined, todayKey);
  if (scoreDiff !== 0) return scoreDiff;

  const leftDue = getDateKey(left.due_date) ?? "9999-99-99";
  const rightDue = getDateKey(right.due_date) ?? "9999-99-99";
  if (leftDue !== rightDue) return leftDue.localeCompare(rightDue);
  return left.title.localeCompare(right.title);
}

export function groupTasksByTriage(tasks: Task[], membersById: Map<string, Member>, todayKey: string): TaskGroup[] {
  const orderedTasks = [...tasks]
    .filter((task) => !isTaskClosed(task))
    .sort((left, right) => compareOperationalTasks(left, right, membersById, todayKey));

  const attentionTasks = getAttentionNowTasks(orderedTasks, membersById, todayKey);
  const consumedTaskIds = new Set(attentionTasks.map((task) => task.id));
  const remainingTasks = orderedTasks.filter((task) => !consumedTaskIds.has(task.id));
  const upcomingLimitKey = new Date(new Date(`${todayKey}T00:00:00Z`).getTime() + 7 * 86_400_000).toISOString().slice(0, 10);

  function takeGroup(
    key: string,
    label: string,
    description: string,
    emptyMessage: string,
    predicate: (task: Task) => boolean,
  ): TaskGroup {
    const groupTasks = remainingTasks.filter((task) => {
      if (consumedTaskIds.has(task.id)) return false;
      return predicate(task);
    });

    groupTasks.forEach((task) => consumedTaskIds.add(task.id));

    return {
      key,
      label,
      description,
      tasks: groupTasks,
      emptyMessage,
    };
  }

  const groups = [
    {
      key: "attention-now",
      label: "Precisa de atencao agora",
      description: "Inbox priorizada sem repetir tarefas nos blocos abaixo.",
      tasks: attentionTasks,
      emptyMessage: "Nenhuma task critica no momento.",
    },
    takeGroup(
      "unassigned",
      "Sem responsavel",
      "Tasks que exigem ownership antes de qualquer outra acao.",
      "Nenhuma task sem responsavel.",
      (task) => !task.assigned_to_user_id,
    ),
    takeGroup(
      "overdue",
      "Atrasadas",
      "Tasks abertas fora do prazo e ja sem cobertura da inbox priorizada.",
      "Nenhuma tarefa atrasada.",
      (task) => isOverdue(task, todayKey),
    ),
    takeGroup(
      "today",
      "Hoje",
      "Tasks que vencem hoje e ainda nao entraram em outra fila mais critica.",
      "Nada vence hoje.",
      (task) => isDueToday(task, todayKey),
    ),
    takeGroup(
      "upcoming",
      "Proximas 7 dias",
      "Planejamento de curto prazo, incluindo itens sem prazo.",
      "Nenhuma task prevista para os proximos 7 dias.",
      (task) => {
        const dueKey = getDateKey(task.due_date);
        if (!dueKey) return true;
        return dueKey > todayKey && dueKey <= upcomingLimitKey;
      },
    ),
  ];

  return groups;
}

export function groupTasksByStatus(tasks: Task[], membersById: Map<string, Member>, todayKey: string): TaskGroup[] {
  return [
    { key: "todo", label: "A fazer", description: "Fila pronta para iniciar", tasks: tasks.filter((task) => task.status === "todo"), emptyMessage: "Nenhuma tarefa a fazer." },
    { key: "doing", label: "Em andamento", description: "Execucao em curso", tasks: tasks.filter((task) => task.status === "doing"), emptyMessage: "Nenhuma tarefa em andamento." },
    { key: "done", label: "Concluidas recentemente", description: "Entregas recentes", tasks: tasks.filter((task) => isRecentlyCompleted(task, todayKey)), emptyMessage: "Nenhuma tarefa concluida recentemente." },
    { key: "cancelled", label: "Canceladas", description: "Encerradas sem execucao", tasks: tasks.filter((task) => task.status === "cancelled"), emptyMessage: "Nenhuma tarefa cancelada." },
  ]
    .map((group) => ({
      ...group,
      tasks: [...group.tasks].sort((left, right) => compareOperationalTasks(left, right, membersById, todayKey)),
    }))
    .filter((group) => group.tasks.length > 0);
}

export function getTaskContextLabel(task: Task): string {
  if (task.member_name) return task.member_name;
  if (task.lead_name) return `Lead: ${task.lead_name}`;
  return "Sem vinculo";
}

export function getTaskSourceContext(task: Task): string {
  const sourceLabel = taskSourceLabel(task);
  const planType = normalizePlanType(taskPlanType(task));
  if (planType) {
    return `${sourceLabel} - ${formatPlanLabel(planType)}`;
  }
  return sourceLabel;
}

export function getAssigneeLabel(task: Task, userNameById: Map<string, string>): string {
  if (!task.assigned_to_user_id) return "Sem responsavel";
  return userNameById.get(task.assigned_to_user_id) ?? "Responsavel";
}

export function getPriorityAccentClass(priority: Task["priority"]): string {
  if (priority === "urgent") return "border-l-rose-500";
  if (priority === "high") return "border-l-amber-500";
  if (priority === "medium") return "border-l-sky-500";
  return "border-l-emerald-500";
}

export function getPriorityBadgeVariant(priority: Task["priority"]): "neutral" | "success" | "warning" | "danger" {
  if (priority === "urgent") return "danger";
  if (priority === "high") return "warning";
  if (priority === "low") return "success";
  return "neutral";
}

export function getStatusBadgeVariant(status: Task["status"]): "neutral" | "success" | "warning" | "danger" {
  if (status === "done") return "success";
  if (status === "doing") return "warning";
  if (status === "cancelled") return "danger";
  return "neutral";
}

export function getMainActionLabel(task: Task): string {
  if (task.status === "todo") return "Iniciar";
  if (task.status === "doing") return "Concluir";
  return "Detalhes";
}

export function isOnboardingActiveMember(member: Member): boolean {
  if (member.status !== "active") return false;
  const joinKey = getDateKey(member.join_date);
  if (!joinKey) return false;
  const daysSinceJoin = getDaysBetween(joinKey, getTodayKey());
  if (daysSinceJoin < 0 || daysSinceJoin > 30) return false;
  return member.onboarding_status === "active" || member.onboarding_status === "at_risk";
}

export function memberToPlaybook(member: Member, resolvedScore?: number | null): OnboardingPlaybookKey {
  const score = resolvedScore ?? member.onboarding_score ?? 0;
  if (score >= 70) return "engajado";
  if (score >= 40) return "atencao";
  return "critico";
}
