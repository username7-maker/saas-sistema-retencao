import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";

import { PageHeader, SkeletonList } from "../../components/ui";
import { Badge, Button, Tabs, TabsContent, TabsList, TabsTrigger } from "../../components/ui2";
import { useAuth } from "../../hooks/useAuth";
import { memberService } from "../../services/memberService";
import { taskService, type CreateTaskPayload, type UpdateTaskPayload } from "../../services/taskService";
import { userService } from "../../services/userService";
import type { Member } from "../../types";
import { TasksOnboardingTab } from "../../components/tasks/TasksOnboardingTab";
import { TasksOperationalView } from "../../components/tasks/TasksOperationalView";
import { isOnboardingActiveMember, type SourceFilter } from "../../components/tasks/taskUtils";

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
  const [page, setPage] = useState(1);
  const [createOpen, setCreateOpen] = useState(false);
  const [sourcePreset, setSourcePreset] = useState<SourceFilter | null>(null);
  const [sourcePresetToken, setSourcePresetToken] = useState(0);

  const tasksQuery = useQuery({
    queryKey: ["tasks", page],
    queryFn: () => taskService.listTasks({ page, page_size: 50 }),
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

  const tasks = tasksQuery.data?.items ?? [];
  const members = membersQuery.data ?? [];
  const users = usersQuery.data ?? [];
  const totalTasks = tasksQuery.data?.total ?? 0;
  const pageSize = tasksQuery.data?.page_size ?? 50;
  const onboardingCount = members.filter((member) => isOnboardingActiveMember(member)).length;

  function openOnboardingQueue() {
    setSourcePreset("onboarding");
    setSourcePresetToken((value) => value + 1);
    setWorkspaceTab("operations");
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Tarefas"
        subtitle="Acompanhamento de acoes e follow-ups pendentes"
        actions={
          <Button
            variant="primary"
            onClick={() => {
              setWorkspaceTab("operations");
              setCreateOpen(true);
            }}
          >
            + Nova Tarefa
          </Button>
        }
      />

      <Tabs value={workspaceTab} onValueChange={(value) => setWorkspaceTab(value as WorkspaceTab)} className="space-y-6">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <TabsList className="w-full sm:w-auto">
            <TabsTrigger value="operations" className="min-w-[150px]">
              Operacao
            </TabsTrigger>
            <TabsTrigger value="onboarding" className="min-w-[150px]">
              Onboarding
            </TabsTrigger>
          </TabsList>

          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="neutral">Tasks: {totalTasks}</Badge>
            <Badge variant="warning">Onboarding ativo: {onboardingCount}</Badge>
          </div>
        </div>

        <TabsContent value="operations">
          {tasksQuery.isLoading ? (
            <div className="rounded-2xl border border-lovable-border bg-lovable-surface px-4 py-3">
              <SkeletonList rows={8} cols={4} />
            </div>
          ) : tasksQuery.isError || !tasksQuery.data ? (
            <div className="rounded-2xl border border-lovable-border bg-lovable-surface px-4 py-10 text-center text-sm text-lovable-danger">
              Erro ao carregar tarefas. Tente novamente.
            </div>
          ) : (
            <TasksOperationalView
              tasks={tasks}
              totalTasks={totalTasks}
              currentPage={page}
              pageSize={pageSize}
              members={members}
              users={users}
              currentUserId={user?.id ?? null}
              sourcePreset={sourcePreset}
              sourcePresetToken={sourcePresetToken}
              isLoading={false}
              createOpen={createOpen}
              isCreating={createMutation.isPending}
              isUpdating={updateMutation.isPending}
              isDeleting={deleteMutation.isPending}
              onCreateOpen={() => setCreateOpen(true)}
              onCreateClose={() => setCreateOpen(false)}
              onPageChange={setPage}
              onCreateTask={(payload) => createMutation.mutate(payload)}
              onUpdateTask={(taskId, payload) => updateMutation.mutate({ taskId, payload })}
              onDeleteTask={(taskId) => deleteMutation.mutate(taskId)}
            />
          )}
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
      </Tabs>
    </div>
  );
}
