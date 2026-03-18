import { Filter, RotateCcw, Search, SlidersHorizontal } from "lucide-react";

import { Badge, Button, Card, CardContent, Input, Select, Tabs, TabsList, TabsTrigger } from "../ui2";
import type { StaffUser } from "../../services/userService";
import type { AssigneeFilter, OperationalFilters, OperationalViewMode, PlanFilter, PriorityFilter, SourceFilter, StatusFilter } from "./taskUtils";

interface TasksFiltersBarProps {
  filters: OperationalFilters;
  hasActiveFilters: boolean;
  advancedOpen: boolean;
  viewMode: OperationalViewMode;
  users: StaffUser[];
  onViewModeChange: (value: OperationalViewMode) => void;
  onAdvancedToggle: () => void;
  onReset: () => void;
  onSearchChange: (value: string) => void;
  onFilterChange: <K extends keyof OperationalFilters>(key: K, value: OperationalFilters[K]) => void;
}

function QuickToggle({
  active,
  label,
  onClick,
}: {
  active: boolean;
  label: string;
  onClick: () => void;
}) {
  return (
    <Button size="sm" variant={active ? "secondary" : "ghost"} onClick={onClick}>
      {label}
    </Button>
  );
}

export function TasksFiltersBar({
  filters,
  hasActiveFilters,
  advancedOpen,
  viewMode,
  users,
  onViewModeChange,
  onAdvancedToggle,
  onReset,
  onSearchChange,
  onFilterChange,
}: TasksFiltersBarProps) {
  return (
    <Card>
      <CardContent className="space-y-4 p-4">
        <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
          <div className="flex min-w-0 flex-1 items-center gap-2">
            <div className="relative min-w-0 flex-1">
              <Search size={14} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-lovable-ink-muted" />
              <Input
                value={filters.search}
                onChange={(event) => onSearchChange(event.target.value)}
                placeholder="Buscar por titulo, contexto ou origem..."
                className="pl-9"
              />
            </div>

            <Button size="sm" variant={advancedOpen ? "secondary" : "ghost"} onClick={onAdvancedToggle}>
              <SlidersHorizontal size={14} />
              Filtros
            </Button>

            {hasActiveFilters ? (
              <Button size="sm" variant="ghost" onClick={onReset}>
                <RotateCcw size={14} />
                Limpar
              </Button>
            ) : null}
          </div>

          <Tabs value={viewMode} onValueChange={(value) => onViewModeChange(value as OperationalViewMode)}>
            <TabsList>
              <TabsTrigger value="due">Por prazo</TabsTrigger>
              <TabsTrigger value="status">Por status</TabsTrigger>
            </TabsList>
          </Tabs>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <QuickToggle
            active={filters.onlyMine}
            label="So minhas"
            onClick={() => onFilterChange("onlyMine", !filters.onlyMine)}
          />
          <QuickToggle
            active={filters.overdueOnly}
            label="Atrasadas"
            onClick={() => onFilterChange("overdueOnly", !filters.overdueOnly)}
          />
          <QuickToggle
            active={filters.dueTodayOnly}
            label="Vence hoje"
            onClick={() => onFilterChange("dueTodayOnly", !filters.dueTodayOnly)}
          />
          <QuickToggle
            active={filters.unassignedOnly}
            label="Sem responsavel"
            onClick={() => onFilterChange("unassignedOnly", !filters.unassignedOnly)}
          />

          {hasActiveFilters ? <Badge variant="neutral">Filtros ativos</Badge> : null}
        </div>

        {advancedOpen ? (
          <div className="grid gap-3 rounded-2xl border border-lovable-border bg-lovable-surface-soft p-4 md:grid-cols-2 xl:grid-cols-4">
            <div>
              <label className="mb-1 block text-xs font-medium text-lovable-ink-muted">Status</label>
              <Select value={filters.status} onChange={(event) => onFilterChange("status", event.target.value as StatusFilter)}>
                <option value="all">Todos</option>
                <option value="todo">A fazer</option>
                <option value="doing">Em andamento</option>
                <option value="done">Concluidas</option>
                <option value="cancelled">Canceladas</option>
              </Select>
            </div>

            <div>
              <label className="mb-1 block text-xs font-medium text-lovable-ink-muted">Prioridade</label>
              <Select value={filters.priority} onChange={(event) => onFilterChange("priority", event.target.value as PriorityFilter)}>
                <option value="all">Todas</option>
                <option value="low">Baixa</option>
                <option value="medium">Media</option>
                <option value="high">Alta</option>
                <option value="urgent">Critica</option>
              </Select>
            </div>

            <div>
              <label className="mb-1 block text-xs font-medium text-lovable-ink-muted">Responsavel</label>
              <Select value={filters.assignee} onChange={(event) => onFilterChange("assignee", event.target.value as AssigneeFilter)}>
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
              <label className="mb-1 block text-xs font-medium text-lovable-ink-muted">Origem</label>
              <Select value={filters.source} onChange={(event) => onFilterChange("source", event.target.value as SourceFilter)}>
                <option value="all">Todas</option>
                <option value="manual">Manual</option>
                <option value="onboarding">Onboarding</option>
                <option value="plan_followup">Follow-up</option>
                <option value="automation">Automacao</option>
              </Select>
            </div>

            <div>
              <label className="mb-1 block text-xs font-medium text-lovable-ink-muted">Plano</label>
              <Select value={filters.plan} onChange={(event) => onFilterChange("plan", event.target.value as PlanFilter)}>
                <option value="all">Todos</option>
                <option value="mensal">Mensal</option>
                <option value="semestral">Semestral</option>
                <option value="anual">Anual</option>
              </Select>
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-2 text-xs text-lovable-ink-muted">
            <Filter size={13} />
            Filtros avancados recolhidos para manter a fila limpa.
          </div>
        )}
      </CardContent>
    </Card>
  );
}
