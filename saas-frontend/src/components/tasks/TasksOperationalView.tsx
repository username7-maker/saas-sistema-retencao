import { useDeferredValue, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { FolderSearch } from "lucide-react";

import { Button, Dialog, Card, CardContent } from "../ui2";
import type { CreateTaskPayload, UpdateTaskPayload } from "../../services/taskService";
import type { StaffUser } from "../../services/userService";
import type { Member, Task } from "../../types";
import { TaskCreateDrawer } from "./TaskCreateDrawer";
import { TaskDetailDrawer } from "./TaskDetailDrawer";
import { TaskListItem } from "./TaskListItem";
import { TasksEmptyState } from "./TasksEmptyState";
import { TasksFiltersBar } from "./TasksFiltersBar";
import { TasksFocusSection } from "./TasksFocusSection";
import { TasksOperationalHeader } from "./TasksOperationalHeader";
import {
  DEFAULT_OPERATIONAL_FILTERS,
  type OperationalFilters,
  type OperationalViewMode,
  type SourceFilter,
  filterOperationalTasks,
  getAttentionNowTasks,
  getOperationStats,
  getTodayKey,
  groupTasksByDue,
  groupTasksByStatus,
} from "./taskUtils";

interface TasksOperationalViewProps {
  tasks: Task[];
  members: Member[];
  users: StaffUser[];
  currentUserId: string | null;
  sourcePreset: SourceFilter | null;
  sourcePresetToken: number;
  isCreating: boolean;
  isUpdating: boolean;
  isDeleting: boolean;
  onCreateTask: (payload: CreateTaskPayload) => void;
  onUpdateTask: (taskId: string, payload: UpdateTaskPayload) => void;
  onDeleteTask: (taskId: string) => void;
}

function hasFilters(filters: OperationalFilters): boolean {
  return JSON.stringify(filters) !== JSON.stringify(DEFAULT_OPERATIONAL_FILTERS);
}

export function TasksOperationalView({
  tasks,
  members,
  users,
  currentUserId,
  sourcePreset,
  sourcePresetToken,
  isCreating,
  isUpdating,
  isDeleting,
  onCreateTask,
  onUpdateTask,
  onDeleteTask,
}: TasksOperationalViewProps) {
  const navigate = useNavigate();

  const [filters, setFilters] = useState<OperationalFilters>(DEFAULT_OPERATIONAL_FILTERS);
  const [viewMode, setViewMode] = useState<OperationalViewMode>("due");
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null);

  const todayKey = useMemo(() => getTodayKey(), []);
  const deferredSearch = useDeferredValue(filters.search);

  useEffect(() => {
    if (!sourcePresetToken || !sourcePreset) return;
    setFilters((previous) => ({ ...previous, source: sourcePreset }));
    setAdvancedOpen(true);
    setViewMode("due");
  }, [sourcePreset, sourcePresetToken]);

  const membersById = useMemo(() => {
    const map = new Map<string, Member>();
    members.forEach((member) => map.set(member.id, member));
    return map;
  }, [members]);

  const userNameById = useMemo(() => {
    const map = new Map<string, string>();
    users.forEach((user) => map.set(user.id, user.full_name));
    return map;
  }, [users]);

  const effectiveFilters = useMemo(
    () => ({
      ...filters,
      search: deferredSearch,
    }),
    [deferredSearch, filters],
  );

  const filteredTasks = useMemo(
    () => filterOperationalTasks(tasks, membersById, effectiveFilters, currentUserId, todayKey),
    [currentUserId, effectiveFilters, membersById, tasks, todayKey],
  );

  const stats = useMemo(
    () => getOperationStats(filteredTasks, currentUserId, todayKey),
    [currentUserId, filteredTasks, todayKey],
  );

  const attentionTasks = useMemo(
    () => getAttentionNowTasks(filteredTasks, membersById, todayKey),
    [filteredTasks, membersById, todayKey],
  );

  const groups = useMemo(
    () => (viewMode === "due" ? groupTasksByDue(filteredTasks, membersById, todayKey) : groupTasksByStatus(filteredTasks, membersById, todayKey)),
    [filteredTasks, membersById, todayKey, viewMode],
  );

  const selectedTask = useMemo(
    () => filteredTasks.find((task) => task.id === selectedTaskId) ?? tasks.find((task) => task.id === selectedTaskId) ?? null,
    [filteredTasks, selectedTaskId, tasks],
  );

  const pendingDeleteTask = useMemo(
    () => tasks.find((task) => task.id === pendingDeleteId) ?? null,
    [pendingDeleteId, tasks],
  );

  function handleFilterChange<K extends keyof OperationalFilters>(key: K, value: OperationalFilters[K]) {
    setFilters((previous) => ({ ...previous, [key]: value }));
  }

  function handleResetFilters() {
    setFilters(DEFAULT_OPERATIONAL_FILTERS);
    setAdvancedOpen(false);
  }

  function openTaskDetails(task: Task) {
    setSelectedTaskId(task.id);
  }

  function openTaskContext(task: Task) {
    if (task.member_id) {
      navigate(`/assessments/members/${task.member_id}`);
      return;
    }
    navigate("/crm");
  }

  function handleStart(taskId: string) {
    onUpdateTask(taskId, { status: "doing" });
  }

  function handleComplete(taskId: string) {
    onUpdateTask(taskId, { status: "done" });
  }

  const hasActiveFilters = hasFilters(filters);
  const noTasksAtAll = tasks.length === 0;

  return (
    <div className="space-y-4">
      <TasksOperationalHeader stats={stats} onCreateTask={() => setCreateOpen(true)} />

      <TasksFiltersBar
        filters={filters}
        hasActiveFilters={hasActiveFilters}
        advancedOpen={advancedOpen}
        viewMode={viewMode}
        users={users}
        onViewModeChange={setViewMode}
        onAdvancedToggle={() => setAdvancedOpen((value) => !value)}
        onReset={handleResetFilters}
        onSearchChange={(value) => handleFilterChange("search", value)}
        onFilterChange={handleFilterChange}
      />

      <TasksFocusSection
        tasks={attentionTasks}
        todayKey={todayKey}
        userNameById={userNameById}
        isUpdating={isUpdating}
        onOpenDetails={openTaskDetails}
        onStart={handleStart}
        onComplete={handleComplete}
      />

      {noTasksAtAll ? (
        <TasksEmptyState
          title="Sem tarefas ainda"
          description="Crie a primeira task para começar a organizar a operacao diaria."
          actionLabel="Nova tarefa"
          onAction={() => setCreateOpen(true)}
        />
      ) : groups.length === 0 ? (
        <TasksEmptyState
          title="Nenhum resultado para os filtros"
          description="Tente limpar a busca ou afrouxar os filtros para reencontrar tarefas."
          actionLabel="Limpar filtros"
          onAction={handleResetFilters}
          mode="search"
        />
      ) : (
        <div className="space-y-4">
          {groups.map((group) => (
            <Card key={group.key}>
              <CardContent className="space-y-3 p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-lovable-ink">{group.label}</p>
                    <p className="text-sm text-lovable-ink-muted">{group.description}</p>
                  </div>
                  <div className="rounded-full bg-lovable-surface-soft px-3 py-1 text-xs font-semibold uppercase tracking-wide text-lovable-ink-muted">
                    {group.tasks.length} item{group.tasks.length !== 1 ? "s" : ""}
                  </div>
                </div>

                <div className="space-y-2">
                  {group.tasks.map((task) => (
                    <TaskListItem
                      key={task.id}
                      task={task}
                      todayKey={todayKey}
                      userNameById={userNameById}
                      isUpdating={isUpdating}
                      onOpenDetails={openTaskDetails}
                      onStart={handleStart}
                      onComplete={handleComplete}
                    />
                  ))}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <TaskCreateDrawer
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        members={members}
        users={users}
        isPending={isCreating}
        onSubmit={(payload) => {
          onCreateTask(payload);
          setCreateOpen(false);
        }}
      />

      <TaskDetailDrawer
        task={selectedTask}
        open={Boolean(selectedTask)}
        users={users}
        userNameById={userNameById}
        isSaving={isUpdating}
        isDeleting={isDeleting}
        onClose={() => setSelectedTaskId(null)}
        onSave={onUpdateTask}
        onDeleteRequest={(taskId) => setPendingDeleteId(taskId)}
        onStatusChange={(taskId, status) => onUpdateTask(taskId, { status })}
        onOpenContext={openTaskContext}
      />

      <Dialog
        open={Boolean(pendingDeleteTask)}
        onClose={() => setPendingDeleteId(null)}
        title="Excluir tarefa?"
        description={pendingDeleteTask ? `Esta acao remove "${pendingDeleteTask.title}" em definitivo.` : undefined}
      >
        <div className="flex items-start gap-3 rounded-2xl border border-lovable-border bg-lovable-surface-soft p-3 text-sm text-lovable-ink-muted">
          <FolderSearch size={18} className="mt-0.5 text-lovable-ink-muted" />
          <p>Use exclusao so quando a task nao fizer mais sentido. Se ela apenas nao for seguir, prefira cancelar.</p>
        </div>

        <div className="mt-5 flex items-center justify-end gap-2">
          <Button variant="ghost" size="sm" onClick={() => setPendingDeleteId(null)} disabled={isDeleting}>
            Cancelar
          </Button>
          <Button
            variant="danger"
            size="sm"
            disabled={isDeleting || !pendingDeleteId}
            onClick={() => {
              if (!pendingDeleteId) return;
              setSelectedTaskId(null);
              setPendingDeleteId(null);
              onDeleteTask(pendingDeleteId);
            }}
          >
            {isDeleting ? "Excluindo..." : "Excluir tarefa"}
          </Button>
        </div>
      </Dialog>
    </div>
  );
}
