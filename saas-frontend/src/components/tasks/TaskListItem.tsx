import clsx from "clsx";
import { Check, Clock3, Pencil, TriangleAlert, UserRound } from "lucide-react";

import { StatusBadge } from "../ui";
import { Button } from "../ui2";
import type { Task } from "../../types";
import {
  PRIORITY_LABELS,
  STATUS_LABELS,
  formatDueDate,
  getAssigneeLabel,
  getPriorityAccentClass,
  getTaskContextLabel,
  isOverdue,
} from "./taskUtils";

interface TaskListItemProps {
  task: Task;
  todayKey: string;
  userNameById: Map<string, string>;
  onOpenDetails: (task: Task) => void;
  onComplete: (taskId: string) => void;
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
  onOpenDetails,
  onComplete,
  isUpdating,
}: TaskListItemProps) {
  const overdue = isOverdue(task, todayKey);
  const assigneeLabel = getAssigneeLabel(task, userNameById);
  const canComplete = task.status === "todo" || task.status === "doing";

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
            <p className="truncate text-sm font-semibold text-lovable-ink">{task.title}</p>
            <StatusBadge status={task.priority} map={PRIORITY_BADGE_MAP} />
            <StatusBadge status={task.status} map={STATUS_BADGE_MAP} />
          </div>

          <div className="mt-1 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-lovable-ink-muted">
            <span className="truncate">{getTaskContextLabel(task)}</span>
            <span className="inline-flex items-center gap-1">
              <UserRound size={12} />
              {assigneeLabel}
            </span>
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-2">
          <span
            className={clsx(
              "hidden items-center gap-1 text-xs text-lovable-ink-muted sm:inline-flex",
              overdue && "font-semibold text-lovable-danger",
            )}
          >
            {overdue ? <TriangleAlert size={12} /> : <Clock3 size={12} />}
            {formatDueDate(task.due_date)}
          </span>

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

      <div
        className={clsx(
          "mt-2 inline-flex items-center gap-1 text-xs text-lovable-ink-muted sm:hidden",
          overdue && "font-semibold text-lovable-danger",
        )}
      >
        {overdue ? <TriangleAlert size={12} /> : <Clock3 size={12} />}
        {formatDueDate(task.due_date)}
      </div>
    </article>
  );
}
