import { CheckCircle2, ListTodo, OctagonAlert, UserCheck, Zap } from "lucide-react";

import { Button, Card, CardContent } from "../ui2";
import type { OperationStats } from "./taskUtils";

interface TasksOperationalHeaderProps {
  stats: OperationStats;
  onCreateTask: () => void;
}

const KPI_ITEMS = [
  { key: "open", label: "Abertas", icon: ListTodo },
  { key: "overdue", label: "Atrasadas", icon: OctagonAlert },
  { key: "highPriority", label: "Alta/critica", icon: Zap },
  { key: "mine", label: "Minhas", icon: UserCheck },
  { key: "completedToday", label: "Concluidas hoje", icon: CheckCircle2 },
] as const;

export function TasksOperationalHeader({ stats, onCreateTask }: TasksOperationalHeaderProps) {
  return (
    <Card>
      <CardContent className="space-y-4 p-4">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-wider text-lovable-primary">Central operacional</p>
            <h2 className="mt-1 text-2xl font-bold text-lovable-ink">Tasks</h2>
            <p className="mt-1 text-sm text-lovable-ink-muted">
              Veja o que precisa de acao agora, sem perder o contexto do resto da fila.
            </p>
          </div>
          <Button variant="primary" size="sm" onClick={onCreateTask}>
            + Nova tarefa
          </Button>
        </div>

        <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-5">
          {KPI_ITEMS.map((item) => {
            const Icon = item.icon;
            const value = stats[item.key];
            return (
              <div key={item.key} className="rounded-2xl border border-lovable-border bg-lovable-surface-soft px-3 py-3">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-[11px] font-semibold uppercase tracking-wider text-lovable-ink-muted">{item.label}</p>
                  <Icon size={14} className="text-lovable-ink-muted" />
                </div>
                <p className="mt-2 text-2xl font-bold text-lovable-ink">{value}</p>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
