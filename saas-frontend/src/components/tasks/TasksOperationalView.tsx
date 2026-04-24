import { useDeferredValue, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Filter, FolderSearch, Inbox, SearchX, SlidersHorizontal } from "lucide-react";

import { EmptyState, FilterBar, KPIStrip, SectionHeader, SkeletonList } from "../ui";
import { Button, Dialog, Select, Tabs, TabsList, TabsTrigger } from "../ui2";
import type { CreateTaskPayload, UpdateTaskPayload } from "../../services/taskService";
import type { StaffUser } from "../../services/userService";
import type { Member, Task } from "../../types";
import { getPreferredShiftLabel } from "../../utils/preferredShift";
import { CreateTaskModal } from "../../pages/tasks/CreateTaskModal";
import { TaskDetailDrawer } from "./TaskDetailDrawer";
import { TaskListItem } from "./TaskListItem";
import { TasksFocusSection } from "./TasksFocusSection";
import {
  DEFAULT_OPERATIONAL_FILTERS,
  type OperationalFilters,
  type OperationalViewMode,
  type SourceFilter,
  filterOperationalTasks,
  getOperationStats,
  getTodayKey,
  groupTasksByTriage,
  groupTasksByStatus,
} from "./taskUtils";

interface TasksOperationalViewProps {
  tasks: Task[];
  totalTasks: number;
  members: Member[];
  users: StaffUser[];
  currentUserId: string | null;
  currentUserShift: "morning" | "afternoon" | "evening" | null;
  initialSearch: string;
  sourcePreset: SourceFilter | null;
  sourcePresetToken: number;
  isLoading: boolean;
  createOpen: boolean;
  isCreating: boolean;
  isUpdating: boolean;
  isDeleting: boolean;
  onCreateOpen: () => void;
  onCreateClose: () => void;
  onSearchChange: (value: string) => void;
  onCreateTask: (payload: CreateTaskPayload) => void;
  onUpdateTask: (taskId: string, payload: UpdateTaskPayload) => void;
  onDeleteTask: (taskId: string) => void;
}

function countActiveFilters(filters: OperationalFilters): number {
  let count = 0;

  if (filters.search.trim()) count += 1;
  if (filters.status !== DEFAULT_OPERATIONAL_FILTERS.status) count += 1;
  if (filters.priority !== DEFAULT_OPERATIONAL_FILTERS.priority) count += 1;
  if (filters.assignee !== DEFAULT_OPERATIONAL_FILTERS.assignee) count += 1;
  if (filters.source !== DEFAULT_OPERATIONAL_FILTERS.source) count += 1;
  if (filters.plan !== DEFAULT_OPERATIONAL_FILTERS.plan) count += 1;
  if (filters.preferredShift !== DEFAULT_OPERATIONAL_FILTERS.preferredShift) count += 1;
  if (filters.onlyMine) count += 1;
  if (filters.overdueOnly) count += 1;
  if (filters.dueTodayOnly) count += 1;
  if (filters.unassignedOnly) count += 1;

  return count;
}

function ToggleChip({
  active,
  label,
  onClick,
}: {
  active: boolean;
  label: string;
  onClick: () => void;
}) {
  return (
    <Button size="sm" variant={active ? "secondary" : "ghost"} onClick={onClick} className="rounded-lg">
      {label}
    </Button>
  );
}

export function TasksOperationalView({
  tasks,
  totalTasks,
  members,
  users,
  currentUserId,
  currentUserShift,
  initialSearch,
  sourcePreset,
  sourcePresetToken,
  isLoading,
  createOpen,
  isCreating,
  isUpdating,
  isDeleting,
  onCreateOpen,
  onCreateClose,
  onSearchChange,
  onCreateTask,
  onUpdateTask,
  onDeleteTask,
}: TasksOperationalViewProps) {
  const navigate = useNavigate();

  const [filters, setFilters] = useState<OperationalFilters>({ ...DEFAULT_OPERATIONAL_FILTERS, search: initialSearch });
  const [useCurrentShift, setUseCurrentShift] = useState(Boolean(currentUserShift));
  const [shiftPreferenceTouched, setShiftPreferenceTouched] = useState(false);
  const [viewMode, setViewMode] = useState<OperationalViewMode>("triage");
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null);
  const [expandedGroups, setExpandedGroups] = useState<Record<string, boolean>>({});

  const todayKey = useMemo(() => getTodayKey(), []);
  const deferredSearch = useDeferredValue(filters.search);

  useEffect(() => {
    if (!sourcePresetToken || !sourcePreset) return;
    setFilters((previous) => ({ ...previous, source: sourcePreset }));
    setAdvancedOpen(true);
    setViewMode("triage");
  }, [sourcePreset, sourcePresetToken]);

  useEffect(() => {
    setFilters((previous) => (previous.search === initialSearch ? previous : { ...previous, search: initialSearch }));
  }, [initialSearch]);

  useEffect(() => {
    if (shiftPreferenceTouched) return;
    setUseCurrentShift(Boolean(currentUserShift));
  }, [currentUserShift, shiftPreferenceTouched]);

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
      preferredShift: useCurrentShift && currentUserShift ? currentUserShift : filters.preferredShift,
    }),
    [currentUserShift, deferredSearch, filters, useCurrentShift],
  );

  const filteredTasks = useMemo(
    () => filterOperationalTasks(tasks, membersById, effectiveFilters, currentUserId, todayKey),
    [currentUserId, effectiveFilters, membersById, tasks, todayKey],
  );

  const stats = useMemo(
    () => getOperationStats(filteredTasks, currentUserId, todayKey),
    [currentUserId, filteredTasks, todayKey],
  );

  const groups = useMemo(
    () => (viewMode === "triage" ? groupTasksByTriage(filteredTasks, membersById, todayKey) : groupTasksByStatus(filteredTasks, membersById, todayKey)),
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

  const activeFilterCount = countActiveFilters({
    ...filters,
    preferredShift: useCurrentShift && currentUserShift ? currentUserShift : filters.preferredShift,
  });
  const noTasksAtAll = totalTasks === 0;
  const noFilteredTasks = filteredTasks.length === 0;
  const currentShiftLabel = getPreferredShiftLabel(currentUserShift);

  function handleFilterChange<K extends keyof OperationalFilters>(key: K, value: OperationalFilters[K]) {
    setFilters((previous) => ({ ...previous, [key]: value }));
  }

  function handlePreferredShiftChange(value: OperationalFilters["preferredShift"]) {
    setShiftPreferenceTouched(true);
    setUseCurrentShift(false);
    handleFilterChange("preferredShift", value);
  }

  function handleSearchChange(value: string) {
    handleFilterChange("search", value);
    onSearchChange(value);
  }

  function handleResetFilters() {
    setFilters(DEFAULT_OPERATIONAL_FILTERS);
    setUseCurrentShift(Boolean(currentUserShift));
    setShiftPreferenceTouched(false);
    setAdvancedOpen(false);
    onSearchChange("");
  }

  function openTaskDetails(task: Task) {
    setSelectedTaskId(task.id);
  }

  function openTaskContext(task: Task) {
    if (task.member_id) {
      navigate(`/assessments/members/${task.member_id}?tab=acoes`);
      return;
    }
    if (task.lead_id) {
      navigate(`/crm?leadId=${task.lead_id}`);
      return;
    }
    navigate("/crm");
  }

  function handleStart(task: Task) {
    onUpdateTask(task.id, { status: "doing" });
    openTaskContext(task);
  }

  function handleComplete(taskId: string) {
    onUpdateTask(taskId, { status: "done" });
  }

  function handleAssignToMe(taskId: string) {
    if (!currentUserId) return;
    onUpdateTask(taskId, { assigned_to_user_id: currentUserId });
  }

  function toggleGroup(groupKey: string) {
    setExpandedGroups((previous) => ({ ...previous, [groupKey]: !previous[groupKey] }));
  }

  const kpiItems = [
    { label: "Total visiveis", value: filteredTasks.length, tone: "neutral" as const },
    { label: "Pendentes", value: stats.open, tone: "warning" as const },
    { label: "Vencidas", value: stats.overdue, tone: "danger" as const },
    { label: "Concluidas hoje", value: stats.completedToday, tone: "success" as const },
  ];

  return (
    <div className="space-y-6">
      <KPIStrip items={kpiItems} />

      <section className="sticky top-4 z-20 space-y-3 rounded-2xl border border-lovable-border bg-lovable-bg/95 px-3 py-3 backdrop-blur">
        <FilterBar
          search={{
            value: filters.search,
            onChange: handleSearchChange,
            placeholder: "Buscar por titulo, aluno, lead ou playbook...",
          }}
          filters={[
            {
              key: "status",
              label: "Status",
              value: filters.status,
              onChange: (value) => handleFilterChange("status", value as OperationalFilters["status"]),
              options: [
                { value: "all", label: "Todos os status" },
                { value: "todo", label: "A fazer" },
                { value: "doing", label: "Em andamento" },
                { value: "done", label: "Concluidas" },
                { value: "cancelled", label: "Canceladas" },
              ],
            },
            {
              key: "priority",
              label: "Prioridade",
              value: filters.priority,
              onChange: (value) => handleFilterChange("priority", value as OperationalFilters["priority"]),
              options: [
                { value: "all", label: "Todas as prioridades" },
                { value: "low", label: "Baixa" },
                { value: "medium", label: "Media" },
                { value: "high", label: "Alta" },
                { value: "urgent", label: "Critica" },
              ],
            },
            {
              key: "source",
              label: "Origem",
              value: filters.source,
              onChange: (value) => handleFilterChange("source", value as SourceFilter),
              options: [
                { value: "all", label: "Todas as origens" },
                { value: "manual", label: "Manual" },
                { value: "onboarding", label: "Onboarding" },
                { value: "plan_followup", label: "Follow-up" },
                { value: "automation", label: "Automacao" },
              ],
            },
          ]}
          activeCount={activeFilterCount}
          onClear={handleResetFilters}
        />

        <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
          <div className="flex flex-wrap items-center gap-2">
            {currentUserShift && currentShiftLabel ? (
              <ToggleChip
                active={useCurrentShift}
                label={useCurrentShift ? `Meu turno: ${currentShiftLabel}` : `Mostrar meu turno: ${currentShiftLabel}`}
                onClick={() => {
                  setShiftPreferenceTouched(true);
                  setUseCurrentShift((value) => !value);
                }}
              />
            ) : null}
            <ToggleChip active={filters.onlyMine} label="So minhas" onClick={() => handleFilterChange("onlyMine", !filters.onlyMine)} />
            <ToggleChip active={filters.overdueOnly} label="Atrasadas" onClick={() => handleFilterChange("overdueOnly", !filters.overdueOnly)} />
            <ToggleChip active={filters.dueTodayOnly} label="Vence hoje" onClick={() => handleFilterChange("dueTodayOnly", !filters.dueTodayOnly)} />
            <ToggleChip active={filters.unassignedOnly} label="Sem responsavel" onClick={() => handleFilterChange("unassignedOnly", !filters.unassignedOnly)} />

            <Button
              size="sm"
              variant={advancedOpen ? "secondary" : "ghost"}
              onClick={() => setAdvancedOpen((value) => !value)}
              className="rounded-lg"
            >
              <SlidersHorizontal size={14} />
              Filtros avancados
            </Button>
          </div>

          <Tabs value={viewMode} onValueChange={(value) => setViewMode(value as OperationalViewMode)}>
            <TabsList>
              <TabsTrigger value="triage">Triage</TabsTrigger>
              <TabsTrigger value="status">Por status</TabsTrigger>
            </TabsList>
          </Tabs>
        </div>

        {advancedOpen ? (
          <div className="grid gap-3 rounded-2xl border border-lovable-border bg-lovable-surface px-4 py-4 md:grid-cols-2 xl:grid-cols-3">
            <div>
              <label className="mb-1 block text-xs font-medium text-lovable-ink-muted">Responsavel</label>
              <Select value={filters.assignee} onChange={(event) => handleFilterChange("assignee", event.target.value)}>
                <option value="all">Todos</option>
                <option value="unassigned">Sem responsavel</option>
                {users.map((user) => (
                  <option key={user.id} value={user.id}>
                    {user.full_name}
                  </option>
                ))}
              </Select>
            </div>

            <div>
              <label className="mb-1 block text-xs font-medium text-lovable-ink-muted">Plano</label>
              <Select value={filters.plan} onChange={(event) => handleFilterChange("plan", event.target.value as OperationalFilters["plan"])}>
                <option value="all">Todos</option>
                <option value="mensal">Mensal</option>
                <option value="semestral">Semestral</option>
                <option value="anual">Anual</option>
              </Select>
            </div>

            <div>
              <label className="mb-1 block text-xs font-medium text-lovable-ink-muted">Turno por check-in</label>
              <Select
                value={useCurrentShift && currentUserShift ? currentUserShift : filters.preferredShift}
                onChange={(event) => handlePreferredShiftChange(event.target.value as OperationalFilters["preferredShift"])}
              >
                <option value="all">Todos os turnos</option>
                <option value="morning">Manha</option>
                <option value="afternoon">Tarde</option>
                <option value="evening">Noite</option>
              </Select>
              {useCurrentShift && currentShiftLabel ? (
                <p className="mt-1 text-[11px] text-lovable-ink-muted">O filtro do login esta ativo: {currentShiftLabel}.</p>
              ) : null}
            </div>

            <div className="flex items-end">
              <p className="inline-flex items-center gap-2 text-xs text-lovable-ink-muted">
                <Filter size={13} />
                Ajustes adicionais sem poluir a fila principal.
              </p>
            </div>
          </div>
        ) : null}
      </section>

      {isLoading ? (
        <div className="rounded-2xl border border-lovable-border bg-lovable-surface px-4 py-3">
          <SkeletonList rows={8} cols={4} />
        </div>
      ) : noTasksAtAll ? (
        <div className="rounded-2xl border border-lovable-border bg-lovable-surface px-4">
          <EmptyState
            icon={Inbox}
            title="Nenhuma tarefa cadastrada"
            description="Crie a primeira task para comecar a organizar os follow-ups do time."
            action={{ label: "Nova tarefa", onClick: onCreateOpen }}
          />
        </div>
      ) : noFilteredTasks ? (
        <div className="rounded-2xl border border-lovable-border bg-lovable-surface px-4">
          <EmptyState
            icon={SearchX}
            title="Nenhum resultado para os filtros"
            description="Tente limpar a busca ou afrouxar os filtros para reencontrar tarefas."
            action={{ label: "Limpar filtros", onClick: handleResetFilters }}
          />
        </div>
      ) : (
        <div className="space-y-4">
          {groups.map((group, index) =>
            index === 0 && viewMode === "triage" ? (
              <TasksFocusSection
                key={group.key}
                tasks={group.tasks}
                todayKey={todayKey}
                userNameById={userNameById}
                currentUserId={currentUserId}
                isUpdating={isUpdating}
                onOpenDetails={openTaskDetails}
                onStart={handleStart}
                onComplete={handleComplete}
                onAssignToMe={handleAssignToMe}
              />
            ) : (
            <section key={group.key} className="rounded-2xl border border-lovable-border bg-lovable-surface px-4 py-4">
              <SectionHeader
                title={group.label}
                subtitle={group.description}
                count={group.tasks.length}
                actions={
                  group.tasks.length > 8 ? (
                    <Button size="sm" variant="ghost" onClick={() => toggleGroup(group.key)}>
                      {expandedGroups[group.key] ? "Recolher" : `Mostrar mais ${group.tasks.length - 8}`}
                    </Button>
                  ) : null
                }
              />

              {group.tasks.length === 0 ? (
                <div className="rounded-xl border border-dashed border-lovable-border bg-lovable-surface-soft px-4 py-3 text-sm text-lovable-ink-muted">
                  {group.emptyMessage}
                </div>
              ) : (
                <div className="space-y-2">
                  {(expandedGroups[group.key] ? group.tasks : group.tasks.slice(0, 8)).map((task) => (
                    <TaskListItem
                      key={task.id}
                      task={task}
                      todayKey={todayKey}
                      userNameById={userNameById}
                      currentUserId={currentUserId}
                      isUpdating={isUpdating}
                      onOpenDetails={openTaskDetails}
                      onStart={handleStart}
                      onComplete={handleComplete}
                      onAssignToMe={handleAssignToMe}
                    />
                  ))}
                </div>
              )}
            </section>
            ),
          )}
        </div>
      )}

      <CreateTaskModal
        open={createOpen}
        onClose={onCreateClose}
        members={members}
        users={users}
        isPending={isCreating}
        onSubmit={(payload) => {
          onCreateTask(payload);
          onCreateClose();
        }}
      />

      <TaskDetailDrawer
        task={selectedTask}
        relatedMember={selectedTask?.member_id ? membersById.get(selectedTask.member_id) ?? null : null}
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
