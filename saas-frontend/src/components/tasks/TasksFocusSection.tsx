import { AlertTriangle } from "lucide-react";

import { SectionHeader } from "../ui";
import type { Task } from "../../types";
import { TaskListItem } from "./TaskListItem";

interface TasksFocusSectionProps {
  tasks: Task[];
  todayKey: string;
  userNameById: Map<string, string>;
  currentUserId: string | null;
  isUpdating: boolean;
  onOpenDetails: (task: Task) => void;
  onStart: (task: Task) => void;
  onComplete: (taskId: string) => void;
  onAssignToMe: (taskId: string) => void;
}

export function TasksFocusSection({
  tasks,
  todayKey,
  userNameById,
  currentUserId,
  isUpdating,
  onOpenDetails,
  onStart,
  onComplete,
  onAssignToMe,
}: TasksFocusSectionProps) {
  return (
    <section className="rounded-2xl border border-lovable-border bg-lovable-surface px-4 py-4">
      <SectionHeader
        title="Precisa de atencao agora"
        subtitle="Subconjunto priorizado com atraso, prazo do dia, criticidade e falta de responsavel."
        count={tasks.length}
      />

      {tasks.length === 0 ? (
        <div className="flex items-center justify-between gap-3 rounded-xl border border-dashed border-lovable-border bg-lovable-surface-soft px-4 py-3">
          <div>
            <p className="text-sm font-medium text-lovable-ink">Nenhuma task critica no momento.</p>
            <p className="text-sm text-lovable-ink-muted">A fila esta sob controle.</p>
          </div>
          <AlertTriangle size={18} className="text-lovable-ink-muted/40" />
        </div>
      ) : (
        <div className="space-y-2">
          {tasks.map((task) => (
            <TaskListItem
              key={task.id}
              task={task}
              todayKey={todayKey}
              userNameById={userNameById}
              currentUserId={currentUserId}
              isUpdating={isUpdating}
              onOpenDetails={onOpenDetails}
              onStart={onStart}
              onComplete={onComplete}
              onAssignToMe={onAssignToMe}
            />
          ))}
        </div>
      )}
    </section>
  );
}
