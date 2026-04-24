import clsx from "clsx";
import { ArrowRight, Check, Clock3, Pencil, TriangleAlert, UserRound } from "lucide-react";

import { PreferredShiftBadge } from "../common/PreferredShiftBadge";
import { StatusBadge } from "../ui";
import { Button } from "../ui2";
import type { Task } from "../../types";
import {
  PRIORITY_LABELS,
  STATUS_LABELS,
  getTaskSlaMeta,
  getAssigneeLabel,
  getPriorityAccentClass,
  getTaskSourceContext,
  getTaskContextLabel,
  isOverdue,
} from "./taskUtils";

interface TaskListItemProps {
  task: Task;
  todayKey: string;
  userNameById: Map<string, string>;
  currentUserId: string | null;
  onOpenDetails: (task: Task) => void;
  onStart: (task: Task) => void;
  onComplete: (taskId: string) => void;
  onAssignToMe: (taskId: string) => void;
  isUpdating: boolean;
}

const PRIORITY_BADGE_MAP = {
  low: { label: PRIORITY_LABELS.low, variant: "success" as const },
  medium: { label: PRIORITY_LABELS.medium, variant: "neutral" as const },
  high: { label: PRIORITY_LABELS.high, variant: "warning" as const },
  urgent: { label: PRIORITY_LABELS.urgent, variant: "danger" as const },
};

const STATUS_BADGE_MAP = {
  todo: { label: STATUS_LABELS.todo, variant: "neutral" as const },
  doing: { label: STATUS_LABELS.doing, variant: "warning" as const },
  done: { label: STATUS_LABELS.done, variant: "success" as const },
  cancelled: { label: STATUS_LABELS.cancelled, variant: "danger" as const },
};

export function TaskListItem({
  task,
  todayKey,
  userNameById,
  currentUserId,
  onOpenDetails,
  onStart,
  onComplete,
  onAssignToMe,
  isUpdating,
}: TaskListItemProps) {
  const overdue = isOverdue(task, todayKey);
  const assigneeLabel = getAssigneeLabel(task, userNameById);
  const slaMeta = getTaskSlaMeta(task, todayKey);
  const canStart = task.status === "todo";
  const canComplete = task.status === "doing";
  const canAssignToMe = !task.assigned_to_user_id && Boolean(currentUserId);

  function handleOpenDetails() {
    onOpenDetails(task);
  }

  function handleKeyDown(event: React.KeyboardEvent<HTMLElement>) {
    if (event.key !== "Enter" && event.key !== " ") return;
    event.preventDefault();
    handleOpenDetails();
  }

  return (
    <article
      role="button"
      tabIndex={0}
      onClick={handleOpenDetails}
      onKeyDown={handleKeyDown}
      className={clsx(
        "rounded-xl border border-lovable-border bg-lovable-surface px-3 py-2.5 text-left transition hover:border-lovable-border-strong hover:bg-lovable-surface-soft focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lovable-primary/30",
        "border-l-4",
        getPriorityAccentClass(task.priority),
        overdue && "bg-rose-500/5",
      )}
    >
      <div className="flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <p className="truncate text-sm font-semibold text-lovable-ink">{getTaskContextLabel(task)}</p>
            {!task.assigned_to_user_id ? (
              <span className="inline-flex items-center rounded-full border border-amber-500/30 bg-amber-500/12 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-amber-200">
                Sem responsavel
              </span>
            ) : null}
            {slaMeta.tone === "danger" ? (
              <span className="inline-flex items-center gap-1 rounded-full border border-rose-500/30 bg-rose-500/12 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-rose-200">
                <TriangleAlert size={10} />
                {slaMeta.label}
              </span>
            ) : null}
          </div>

          <div className="mt-1 flex flex-wrap items-center gap-2">
            <p className="truncate text-sm text-lovable-ink-muted">{task.title}</p>
            <StatusBadge status={task.priority} map={PRIORITY_BADGE_MAP} />
            <StatusBadge status={task.status} map={STATUS_BADGE_MAP} />
          </div>

          <div className="mt-1 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-lovable-ink-muted">
            <span className={clsx("inline-flex items-center gap-1", !task.assigned_to_user_id && "font-semibold text-amber-200")}>
              <UserRound size={12} />
              {assigneeLabel}
            </span>
            <span
              className={clsx(
                "inline-flex items-center gap-1",
                slaMeta.tone === "danger" && "font-semibold text-lovable-danger",
                slaMeta.tone === "warning" && "font-semibold text-amber-200",
              )}
            >
              {slaMeta.tone === "danger" ? <TriangleAlert size={12} /> : <Clock3 size={12} />}
              {slaMeta.label}
            </span>
            <PreferredShiftBadge preferredShift={task.preferred_shift} prefix />
            <span className="truncate">{getTaskSourceContext(task)}</span>
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-2">
          {canAssignToMe ? (
            <Button
              size="sm"
              variant="secondary"
              className="rounded-lg"
              title="Assumir tarefa"
              aria-label={`Assumir ${task.title}`}
              disabled={isUpdating}
              onClick={(event) => {
                event.stopPropagation();
                onAssignToMe(task.id);
              }}
            >
              Assumir
            </Button>
          ) : null}

          {canStart ? (
            <Button
              size="sm"
              variant="secondary"
              className="w-8 rounded-lg px-0"
              title="Iniciar tarefa"
              aria-label={`Iniciar ${task.title}`}
              disabled={isUpdating}
              onClick={(event) => {
                event.stopPropagation();
                onStart(task);
              }}
            >
              <ArrowRight size={14} />
            </Button>
          ) : null}

          {canComplete ? (
            <Button
              size="sm"
              variant="primary"
              className="w-8 rounded-lg px-0"
              title="Concluir tarefa"
              aria-label={`Concluir ${task.title}`}
              disabled={isUpdating}
              onClick={(event) => {
                event.stopPropagation();
                onComplete(task.id);
              }}
            >
              <Check size={14} />
            </Button>
          ) : null}

          <Button
            size="sm"
            variant="ghost"
            className="w-8 rounded-lg px-0"
            title="Editar tarefa"
            aria-label={`Editar ${task.title}`}
            onClick={(event) => {
              event.stopPropagation();
              handleOpenDetails();
            }}
          >
            <Pencil size={14} />
          </Button>
        </div>
      </div>
    </article>
  );
}
