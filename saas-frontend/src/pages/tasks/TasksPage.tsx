import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { LoadingPanel } from "../../components/common/LoadingPanel";
import { taskService } from "../../services/taskService";
import type { Task } from "../../types";

const statusSequence: Task["status"][] = ["todo", "doing", "done"];

function nextStatus(currentStatus: Task["status"]): Task["status"] {
  const index = statusSequence.indexOf(currentStatus);
  if (index === -1 || index === statusSequence.length - 1) return "done";
  return statusSequence[index + 1];
}

export function TasksPage() {
  const queryClient = useQueryClient();
  const tasksQuery = useQuery({
    queryKey: ["tasks"],
    queryFn: taskService.listTasks,
    staleTime: 5 * 60 * 1000,
  });

  const updateMutation = useMutation({
    mutationFn: ({ taskId, status }: { taskId: string; status: Task["status"] }) => taskService.updateTask(taskId, status),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["tasks"] });
    },
  });

  if (tasksQuery.isLoading) {
    return <LoadingPanel text="Carregando tasks..." />;
  }

  if (!tasksQuery.data) {
    return <LoadingPanel text="Nao foi possivel carregar tasks." />;
  }

  return (
    <section className="space-y-6">
      <header>
        <h2 className="font-heading text-3xl font-bold text-slate-900">Tasks Internas</h2>
        <p className="text-sm text-slate-500">Kanban simplificado para atendimento e retencao.</p>
      </header>

      <div className="grid gap-4 md:grid-cols-3">
        {statusSequence.map((status) => (
          <section key={status} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-panel">
            <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-600">{status}</h3>
            <div className="space-y-3">
              {tasksQuery.data.items
                .filter((task) => task.status === status)
                .map((task) => (
                  <article key={task.id} className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                    <p className="text-sm font-semibold text-slate-800">{task.title}</p>
                    <p className="mt-1 text-xs text-slate-500">Prioridade: {task.priority}</p>
                    {task.suggested_message && (
                      <p className="mt-2 rounded bg-brand-50 p-2 text-xs text-brand-700">
                        Sugestao WhatsApp: {task.suggested_message}
                      </p>
                    )}
                    {status !== "done" && (
                      <button
                        type="button"
                        onClick={() => updateMutation.mutate({ taskId: task.id, status: nextStatus(task.status) })}
                        className="mt-3 rounded-lg bg-brand-500 px-2 py-1 text-xs font-semibold text-white hover:bg-brand-700"
                      >
                        Avancar
                      </button>
                    )}
                  </article>
                ))}
            </div>
          </section>
        ))}
      </div>
    </section>
  );
}
