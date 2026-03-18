import clsx from "clsx";
import { ArrowRight, CheckCheck, Clock3, UserRound } from "lucide-react";

import { Badge, Button } from "../ui2";
import type { Task } from "../../types";
import {
  PRIORITY_LABELS,
  STATUS_LABELS,
  formatDueDate,
  getAssigneeLabel,
  getPriorityAccentClass,
  getPriorityBadgeVariant,
  getStatusBadgeVariant,
  getTaskContextLabel,
  getTaskSourceContext,
  isOverdue,
} from "./taskUtils";

interface TaskListItemProps {
  task: Task;
  todayKey: string;
  userNameById: Map<string, string>;
  onOpenDetails: (task: Task) => void;
  onStart: (taskId: string) => void;
  onComplete: (taskId: string) => void;
  isUpdating: boolean;
}

export function TaskListItem({
  task,
  todayKey,
  userNameById,
  onOpenDetails,
  onStart,
  onComplete,
  isUpdating,
}: TaskListItemProps) {
  const overdue = isOverdue(task, todayKey);
  const assigneeLabel = getAssigneeLabel(task, userNameById);

  return (
    <article
      className={clsx(
        "rounded-2xl border border-lovable-border bg-lovable-surface px-4 py-3 transition hover:border-lovable-primary/30 hover:bg-lovable-surface-soft",
        "border-l-4",
        getPriorityAccentClass(task.priority),
        overdue && "bg-rose-500/5",
      )}
    >
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <p className="truncate text-sm font-semibold text-lovable-ink">{task.title}</p>
            <Badge variant={getPriorityBadgeVariant(task.priority)}>{PRIORITY_LABELS[task.priority]}</Badge>
            <Badge variant={getStatusBadgeVariant(task.status)}>{STATUS_LABELS[task.status]}</Badge>
          </div>

          <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-lovable-ink-muted">
            <span>{getTaskContextLabel(task)}</span>
            <span>{getTaskSourceContext(task)}</span>
            <span className={clsx("inline-flex items-center gap-1", overdue && "font-semibold text-lovable-danger")}>
              <Clock3 size={12} />
              {overdue ? "Atrasada - " : ""}{formatDueDate(task.due_date)}
            </span>
            <span className="inline-flex items-center gap-1">
              <UserRound size={12} />
              {assigneeLabel}
            </span>
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-2">
          {task.status === "todo" ? (
            <Button size="sm" variant="secondary" disabled={isUpdating} onClick={() => onStart(task.id)}>
              <ArrowRight size={14} />
              Iniciar
            </Button>
          ) : null}

          {(task.status === "todo" || task.status === "doing") ? (
            <Button size="sm" variant="primary" disabled={isUpdating} onClick={() => onComplete(task.id)}>
              <CheckCheck size={14} />
              Concluir
            </Button>
          ) : null}

          <Button size="sm" variant="ghost" onClick={() => onOpenDetails(task)}>
            Detalhes
          </Button>
        </div>
      </div>
    </article>
  );
}
