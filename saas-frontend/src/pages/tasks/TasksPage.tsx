import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";

import { LoadingPanel } from "../../components/common/LoadingPanel";
import { Badge, Tabs, TabsContent, TabsList, TabsTrigger } from "../../components/ui2";
import { useAuth } from "../../hooks/useAuth";
import { memberService } from "../../services/memberService";
import { taskService, type CreateTaskPayload, type UpdateTaskPayload } from "../../services/taskService";
import { userService } from "../../services/userService";
import type { Member } from "../../types";
import { TasksOnboardingTab } from "../../components/tasks/TasksOnboardingTab";
import { TasksOperationalView } from "../../components/tasks/TasksOperationalView";
import type { SourceFilter } from "../../components/tasks/taskUtils";

type WorkspaceTab = "operations" | "onboarding";

async function listAllMembers(): Promise<Member[]> {
  const pageSize = 100;
  const firstPage = await memberService.listMembers({ page: 1, page_size: pageSize });
  const totalPages = Math.ceil(firstPage.total / pageSize);
  if (totalPages <= 1) return firstPage.items;

  const nextPages = await Promise.all(
    Array.from({ length: totalPages - 1 }, (_, index) =>
      memberService.listMembers({ page: index + 2, page_size: pageSize }).then((response) => response.items),
    ),
  );

  return [...firstPage.items, ...nextPages.flat()];
}

export function TasksPage() {
  const queryClient = useQueryClient();
  const { user } = useAuth();

  const [workspaceTab, setWorkspaceTab] = useState<WorkspaceTab>("operations");
  const [sourcePreset, setSourcePreset] = useState<SourceFilter | null>(null);
  const [sourcePresetToken, setSourcePresetToken] = useState(0);

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

  const usersQuery = useQuery({
    queryKey: ["users"],
    queryFn: userService.listUsers,
    staleTime: 15 * 60 * 1000,
  });

  const createMutation = useMutation({
    mutationFn: (payload: CreateTaskPayload) => taskService.createTask(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["tasks"] });
      toast.success("Tarefa criada.");
    },
    onError: () => toast.error("Erro ao criar tarefa."),
  });

  const updateMutation = useMutation({
    mutationFn: ({ taskId, payload }: { taskId: string; payload: UpdateTaskPayload }) =>
      taskService.updateTask(taskId, payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["tasks"] });
      toast.success("Tarefa atualizada.");
    },
    onError: () => toast.error("Erro ao atualizar tarefa."),
  });

  const deleteMutation = useMutation({
    mutationFn: (taskId: string) => taskService.deleteTask(taskId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["tasks"] });
      toast.success("Tarefa excluida.");
    },
    onError: () => toast.error("Erro ao excluir tarefa."),
  });

  if (tasksQuery.isLoading) {
    return <LoadingPanel text="Carregando tarefas..." />;
  }

  if (tasksQuery.isError || !tasksQuery.data) {
    return <LoadingPanel text="Erro ao carregar tarefas. Tente novamente." />;
  }

  const tasks = tasksQuery.data.items;
  const members = membersQuery.data ?? [];
  const users = usersQuery.data ?? [];
  const onboardingCount = members.filter(
    (member) => member.status === "active" && (member.onboarding_status === "active" || member.onboarding_status === "at_risk"),
  ).length;

  function openOnboardingQueue() {
    setSourcePreset("onboarding");
    setSourcePresetToken((value) => value + 1);
    setWorkspaceTab("operations");
  }

  return (
    <Tabs value={workspaceTab} onValueChange={(value) => setWorkspaceTab(value as WorkspaceTab)} className="space-y-6">
      <section className="space-y-4">
        <header className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
          <div>
            <h1 className="font-heading text-3xl font-bold text-lovable-ink">Tasks</h1>
            <p className="mt-1 text-sm text-lovable-ink-muted">
              Fila operacional e onboarding preservado em visoes separadas, mais claras e menos caoticas.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <TabsList className="w-full sm:w-auto">
              <TabsTrigger value="operations" className="min-w-[150px]">
                Operacao
              </TabsTrigger>
              <TabsTrigger value="onboarding" className="min-w-[150px]">
                Onboarding
              </TabsTrigger>
            </TabsList>
            <Badge variant="neutral">Tasks: {tasks.length}</Badge>
            <Badge variant="warning">Onboarding ativo: {onboardingCount}</Badge>
          </div>
        </header>

        <TabsContent value="operations">
          <TasksOperationalView
            tasks={tasks}
            members={members}
            users={users}
            currentUserId={user?.id ?? null}
            sourcePreset={sourcePreset}
            sourcePresetToken={sourcePresetToken}
            isCreating={createMutation.isPending}
            isUpdating={updateMutation.isPending}
            isDeleting={deleteMutation.isPending}
            onCreateTask={(payload) => createMutation.mutate(payload)}
            onUpdateTask={(taskId, payload) => updateMutation.mutate({ taskId, payload })}
            onDeleteTask={(taskId) => deleteMutation.mutate(taskId)}
          />
        </TabsContent>

        <TabsContent value="onboarding">
          <TasksOnboardingTab
            members={members}
            membersLoading={membersQuery.isLoading}
            membersError={membersQuery.isError}
            tasks={tasks}
            onOpenOnboardingQueue={openOnboardingQueue}
          />
        </TabsContent>
      </section>
    </Tabs>
  );
}
