import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { useSearchParams } from "react-router-dom";

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
import { WorkExecutionView } from "../../components/workQueue/WorkExecutionView";
import { matchesPreferredShift } from "../../utils/preferredShift";

type WorkspaceTab = "execution" | "operations" | "onboarding";

async function listAllMembers(): Promise<Member[]> {
  return memberService.listMemberIndex();
}

export function TasksPage() {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const searchParamValue = searchParams.get("search") ?? "";

  const [workspaceTab, setWorkspaceTab] = useState<WorkspaceTab>("execution");
  const [createOpen, setCreateOpen] = useState(false);
  const [sourcePreset, setSourcePreset] = useState<SourceFilter | null>(null);
  const [sourcePresetToken, setSourcePresetToken] = useState(0);
  const [includeArchived, setIncludeArchived] = useState(false);
  const canManageOperations = user?.role === "owner" || user?.role === "manager";

  const tasksQuery = useQuery({
    queryKey: ["tasks", "all", { includeArchived }],
    queryFn: () => taskService.listAllTasks({ include_archived: includeArchived }),
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
  const metricsQuery = useQuery({
    queryKey: ["tasks", "metrics"],
    queryFn: () => taskService.getMetrics(),
    enabled: canManageOperations && typeof taskService.getMetrics === "function",
    staleTime: 2 * 60 * 1000,
  });
  const cleanupPreviewQuery = useQuery({
    queryKey: ["tasks", "operational-cleanup", "preview"],
    queryFn: () => taskService.getOperationalCleanupPreview(),
    enabled: canManageOperations,
    staleTime: 2 * 60 * 1000,
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
  const cleanupMutation = useMutation({
    mutationFn: () => taskService.applyOperationalCleanup(),
    onSuccess: (result) => {
      void queryClient.invalidateQueries({ queryKey: ["tasks"] });
      void queryClient.invalidateQueries({ queryKey: ["work-queue"] });
      toast.success(`${result.archived_total} tarefas arquivadas da fila diaria.`);
    },
    onError: () => toast.error("Erro ao arquivar ruido operacional."),
  });

  const tasks = tasksQuery.data?.items ?? [];
  const members = membersQuery.data ?? [];
  const users = usersQuery.data ?? [];
  const currentUserShift = user?.work_shift ?? null;
  const visibleTasks = currentUserShift
    ? tasks.filter((task) => !task.preferred_shift || matchesPreferredShift(task.preferred_shift, currentUserShift))
    : tasks;
  const visibleOnboardingMembers = currentUserShift
    ? members.filter((member) => isOnboardingActiveMember(member) && matchesPreferredShift(member.preferred_shift, currentUserShift))
    : members.filter((member) => isOnboardingActiveMember(member));
  const totalTasks = visibleTasks.length;
  const onboardingCount = visibleOnboardingMembers.length;

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
            <TabsTrigger value="execution" className="flex-1 sm:min-w-[150px]">
              Modo execucao
            </TabsTrigger>
            <TabsTrigger value="operations" className="flex-1 sm:min-w-[150px]">
              Lista completa
            </TabsTrigger>
            <TabsTrigger value="onboarding" className="flex-1 sm:min-w-[150px]">
              Onboarding
            </TabsTrigger>
          </TabsList>

          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="neutral">Tasks: {totalTasks}</Badge>
            <Badge variant="warning">Onboarding ativo: {onboardingCount}</Badge>
            {canManageOperations ? (
              <Button
                size="sm"
                variant={includeArchived ? "secondary" : "ghost"}
                onClick={() => setIncludeArchived((value) => !value)}
              >
                {includeArchived ? "Ocultar arquivadas" : "Mostrar arquivadas"}
              </Button>
            ) : null}
          </div>
        </div>

        {canManageOperations ? (
          <details className="rounded-[26px] border border-lovable-border bg-lovable-surface/72 p-4 shadow-panel">
            <summary className="cursor-pointer text-sm font-semibold text-lovable-ink">Produtividade das tarefas</summary>
            {metricsQuery.isLoading ? (
              <p className="mt-3 text-sm text-lovable-ink-muted">Carregando metricas...</p>
            ) : metricsQuery.isError || !metricsQuery.data ? (
              <p className="mt-3 text-sm text-lovable-danger">Erro ao carregar produtividade.</p>
            ) : (
              <div className="mt-4 space-y-4">
                <div className="grid gap-3 md:grid-cols-3 xl:grid-cols-6">
                  <div className="rounded-2xl border border-lovable-border bg-lovable-bg-muted/60 p-3">
                    <p className="text-xs text-lovable-ink-muted">Abertas</p>
                    <p className="mt-1 text-2xl font-bold text-lovable-ink">{metricsQuery.data.open_total}</p>
                  </div>
                  <div className="rounded-2xl border border-lovable-border bg-lovable-bg-muted/60 p-3">
                    <p className="text-xs text-lovable-ink-muted">Vencidas</p>
                    <p className="mt-1 text-2xl font-bold text-lovable-danger">{metricsQuery.data.overdue_total}</p>
                  </div>
                  <div className="rounded-2xl border border-lovable-border bg-lovable-bg-muted/60 p-3">
                    <p className="text-xs text-lovable-ink-muted">Vencem hoje</p>
                    <p className="mt-1 text-2xl font-bold text-lovable-warning">{metricsQuery.data.due_today_total}</p>
                  </div>
                  <div className="rounded-2xl border border-lovable-border bg-lovable-bg-muted/60 p-3">
                    <p className="text-xs text-lovable-ink-muted">Concluidas hoje</p>
                    <p className="mt-1 text-2xl font-bold text-lovable-success">{metricsQuery.data.completed_today_total}</p>
                  </div>
                  <div className="rounded-2xl border border-lovable-border bg-lovable-bg-muted/60 p-3">
                    <p className="text-xs text-lovable-ink-muted">7 dias</p>
                    <p className="mt-1 text-2xl font-bold text-lovable-ink">{metricsQuery.data.completed_7d_total}</p>
                  </div>
                  <div className="rounded-2xl border border-lovable-border bg-lovable-bg-muted/60 p-3">
                    <p className="text-xs text-lovable-ink-muted">No prazo</p>
                    <p className="mt-1 text-2xl font-bold text-lovable-ink">{metricsQuery.data.on_time_rate_pct ?? "-"}%</p>
                  </div>
                </div>

                <div className="grid gap-4 lg:grid-cols-3">
                  <div className="rounded-2xl border border-lovable-border p-4">
                    <p className="text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">Por responsavel</p>
                    <div className="mt-3 space-y-2">
                      {metricsQuery.data.by_owner.slice(0, 6).map((owner) => (
                        <div key={owner.user_id ?? "unassigned"} className="flex items-center justify-between gap-3 text-sm">
                          <span className="truncate text-lovable-ink">{owner.owner_name}</span>
                          <span className="text-lovable-ink-muted">{owner.open_total} abertas · {owner.overdue_total} vencidas</span>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div className="rounded-2xl border border-lovable-border p-4">
                    <p className="text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">Por origem</p>
                    <div className="mt-3 flex flex-wrap gap-2">
                      {metricsQuery.data.by_source.slice(0, 8).map((item) => (
                        <Badge key={item.key} variant="neutral">{item.label}: {item.total}</Badge>
                      ))}
                    </div>
                  </div>
                  <div className="rounded-2xl border border-lovable-border p-4">
                    <p className="text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">Por resultado</p>
                    <div className="mt-3 flex flex-wrap gap-2">
                      {metricsQuery.data.by_outcome.slice(0, 8).map((item) => (
                        <Badge key={item.key} variant="neutral">{item.label}: {item.total}</Badge>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </details>
        ) : null}

        {canManageOperations ? (
          <details className="rounded-[26px] border border-lovable-border bg-lovable-surface/72 p-4 shadow-panel">
            <summary className="cursor-pointer text-sm font-semibold text-lovable-ink">Saneamento da fila 24h</summary>
            <div className="mt-4 grid gap-4 lg:grid-cols-[1fr_auto] lg:items-center">
              <div>
                <p className="text-sm text-lovable-ink-muted">
                  Arquiva operacionalmente tarefas antigas sem prazo, sem resultado e fora das protecoes de inadimplencia,
                  jornadas e onboarding ativo. O historico fica preservado; o item apenas sai da rotina diaria.
                </p>
                {cleanupPreviewQuery.isLoading ? (
                  <p className="mt-3 text-sm text-lovable-ink-muted">Calculando preview...</p>
                ) : cleanupPreviewQuery.isError || !cleanupPreviewQuery.data ? (
                  <p className="mt-3 text-sm text-lovable-danger">Erro ao calcular saneamento.</p>
                ) : (
                  <div className="mt-3 flex flex-wrap gap-2">
                    <Badge variant="neutral">Elegiveis: {cleanupPreviewQuery.data.candidate_total}</Badge>
                    <Badge variant="neutral">Corte: {cleanupPreviewQuery.data.cutoff_days}+ dias</Badge>
                    {cleanupPreviewQuery.data.by_source.slice(0, 6).map((item) => (
                      <Badge key={item.key} variant="neutral">{item.label}: {item.total}</Badge>
                    ))}
                  </div>
                )}
              </div>
              <Button
                variant="secondary"
                disabled={
                  cleanupMutation.isPending ||
                  cleanupPreviewQuery.isLoading ||
                  !cleanupPreviewQuery.data ||
                  cleanupPreviewQuery.data.candidate_total === 0
                }
                onClick={() => cleanupMutation.mutate()}
              >
                {cleanupMutation.isPending ? "Arquivando..." : "Arquivar ruido operacional"}
              </Button>
            </div>
          </details>
        ) : null}

        <TabsContent value="execution">
          <WorkExecutionView
            source="all"
            title="Modo execucao operacional"
            subtitle="Fila unica de tasks e AI Inbox por turno. Comece a execucao, registre o resultado e avance sem abrir varias telas."
          />
        </TabsContent>

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
              members={members}
              users={users}
              currentUserId={user?.id ?? null}
              currentUserShift={currentUserShift}
              initialSearch={searchParamValue}
              sourcePreset={sourcePreset}
              sourcePresetToken={sourcePresetToken}
              isLoading={false}
              createOpen={createOpen}
              isCreating={createMutation.isPending}
              isUpdating={updateMutation.isPending}
              isDeleting={deleteMutation.isPending}
              onCreateOpen={() => setCreateOpen(true)}
              onCreateClose={() => setCreateOpen(false)}
              onSearchChange={(value) => {
                const nextParams = new URLSearchParams(searchParams);
                const trimmedValue = value.trim();
                if (trimmedValue) {
                  nextParams.set("search", trimmedValue);
                } else {
                  nextParams.delete("search");
                }
                setSearchParams(nextParams, { replace: true });
              }}
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
            currentUserShift={currentUserShift}
            onOpenOnboardingQueue={openOnboardingQueue}
          />
        </TabsContent>
      </Tabs>
    </div>
  );
}
