import { AlertTriangle } from "lucide-react";

import { Card, CardContent } from "../ui2";
import type { Task } from "../../types";
import { TaskListItem } from "./TaskListItem";

interface TasksFocusSectionProps {
  tasks: Task[];
  todayKey: string;
  userNameById: Map<string, string>;
  isUpdating: boolean;
  onOpenDetails: (task: Task) => void;
  onStart: (taskId: string) => void;
  onComplete: (taskId: string) => void;
}

export function TasksFocusSection({
  tasks,
  todayKey,
  userNameById,
  isUpdating,
  onOpenDetails,
  onStart,
  onComplete,
}: TasksFocusSectionProps) {
  if (tasks.length === 0) {
    return (
      <Card>
        <CardContent className="flex items-center justify-between gap-3 p-4">
          <div>
            <p className="text-sm font-semibold text-lovable-ink">Precisa de atencao agora</p>
            <p className="text-sm text-lovable-ink-muted">Nenhuma task critica no momento. A fila esta sob controle.</p>
          </div>
          <AlertTriangle size={18} className="text-lovable-ink-muted/40" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent className="space-y-3 p-4">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-sm font-semibold text-lovable-ink">Precisa de atencao agora</p>
            <p className="text-sm text-lovable-ink-muted">
              Subconjunto priorizado com atraso, prazo do dia, criticidade e falta de responsavel.
            </p>
          </div>
          <div className="rounded-full bg-lovable-warning/15 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-lovable-warning">
            Top {tasks.length}
          </div>
        </div>

        <div className="space-y-2">
          {tasks.map((task) => (
            <TaskListItem
              key={task.id}
              task={task}
              todayKey={todayKey}
              userNameById={userNameById}
              isUpdating={isUpdating}
              onOpenDetails={onOpenDetails}
              onStart={onStart}
              onComplete={onComplete}
            />
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
