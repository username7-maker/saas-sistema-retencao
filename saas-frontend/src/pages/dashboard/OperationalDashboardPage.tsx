import { startTransition, useDeferredValue, useEffect, useMemo, useRef, useState } from "react";
import { AlertTriangle, ArrowRight, Filter, Search } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { AiInsightCard } from "../../components/common/AiInsightCard";
import { DashboardActions } from "../../components/common/DashboardActions";
import { LoadingPanel } from "../../components/common/LoadingPanel";
import { StatCard } from "../../components/common/StatCard";
import { EmptyState } from "../../components/ui";
import { Badge, Button } from "../../components/ui2";
import { useActionCenter } from "../../hooks/useDashboard";
import { telemetryService } from "../../services/telemetryService";
import { getPermissionAwareMessage } from "../../utils/httpErrors";

const SOURCE_OPTIONS = [
  { value: "all", label: "Todas as origens" },
  { value: "task", label: "Tarefas" },
  { value: "retention", label: "Retenção" },
  { value: "assessment", label: "Avaliações" },
  { value: "crm", label: "CRM" },
] as const;

const SEVERITY_OPTIONS = [
  { value: "all", label: "Todas as prioridades" },
  { value: "critical", label: "Críticas" },
  { value: "high", label: "Altas" },
  { value: "medium", label: "Médias" },
  { value: "low", label: "Baixas" },
] as const;

const SEVERITY_BADGE: Record<string, "danger" | "warning" | "success" | "neutral"> = {
  critical: "danger",
  high: "warning",
  medium: "neutral",
  low: "success",
};

function money(value: number): string {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
    maximumFractionDigits: 0,
  }).format(value);
}

function formatDate(value: string | null): string {
  if (!value) return "Sem registro";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Sem registro";
  return date.toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function OperationalDashboardPage() {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [searchInput, setSearchInput] = useState("");
  const [source, setSource] = useState<(typeof SOURCE_OPTIONS)[number]["value"]>("all");
  const [severity, setSeverity] = useState<(typeof SEVERITY_OPTIONS)[number]["value"]>("all");
  const telemetrySnapshotRef = useRef("");

  const deferredSearch = useDeferredValue(searchInput.trim());
  const query = useActionCenter({
    page,
    page_size: 25,
    search: deferredSearch || undefined,
    source,
    severity,
  });

  const summary = query.data?.summary;
  const criticalCount = summary?.by_severity?.critical ?? 0;
  const retentionCount = summary?.by_source?.retention ?? 0;
  const assessmentCount = summary?.by_source?.assessment ?? 0;
  const totalPages = query.data ? Math.max(1, Math.ceil(query.data.total / query.data.page_size)) : 1;

  const rangeLabel = useMemo(() => {
    if (!query.data || query.data.total === 0) return "Mostrando 0 de 0";
    const start = (query.data.page - 1) * query.data.page_size + 1;
    const end = Math.min(query.data.total, start + query.data.items.length - 1);
    return `Mostrando ${start}-${end} de ${query.data.total}`;
  }, [query.data]);

  useEffect(() => {
    if (!query.data) return;

    const snapshot = [page, source, severity, deferredSearch || "", query.data.total].join("|");
    if (telemetrySnapshotRef.current === snapshot) return;
    telemetrySnapshotRef.current = snapshot;

    void telemetryService.track({
      event_name: "action_center_viewed",
      surface: "action_center",
      details: {
        page,
        source,
        severity,
        search: deferredSearch || null,
        total_items: query.data.total,
        visible_items: query.data.items.length,
      },
    });
  }, [deferredSearch, page, query.data, severity, source]);

  const handleFilterChange = (next: { source?: typeof source; severity?: typeof severity }) => {
    startTransition(() => {
      if (next.source) setSource(next.source);
      if (next.severity) setSeverity(next.severity);
      setPage(1);
    });
  };

  if (query.isLoading) {
    return <LoadingPanel text="Carregando Action Center..." />;
  }

  if (query.isError || !query.data) {
    return (
      <EmptyState
        icon={AlertTriangle}
        title="Não foi possível carregar o Action Center"
        description={getPermissionAwareMessage(query.error, "Tente novamente para recuperar a fila única de execução.")}
        action={{ label: "Tentar novamente", onClick: () => void query.refetch() }}
      />
    );
  }

  const handleOpenItem = (item: (typeof query.data.items)[number]) => {
    void telemetryService.track({
      event_name: "action_center_cta_clicked",
      surface: "action_center",
      details: {
        item_id: item.id,
        source: item.source,
        severity: item.severity,
        cta_target: item.cta_target,
      },
    });
    navigate(item.cta_target);
  };

  return (
    <section className="space-y-6">
      <header className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
        <div>
          <h2 className="font-heading text-3xl font-bold text-lovable-ink">Action Center</h2>
          <p className="text-sm text-lovable-ink-muted">
            Fila única de execução com tarefas, retenção, avaliações críticas e CRM parado.
          </p>
        </div>
        <DashboardActions dashboard="operational" />
      </header>

      <AiInsightCard dashboard="operational" />

      <div className="grid gap-4 md:grid-cols-4">
        <StatCard label="Itens abertos" value={String(query.data.total)} tone="neutral" />
        <StatCard label="Críticos" value={String(criticalCount)} tone="danger" />
        <StatCard label="Retenção" value={String(retentionCount)} tone="warning" />
        <StatCard label="Avaliações" value={String(assessmentCount)} tone="success" />
      </div>

      <section className="rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h3 className="text-sm font-semibold uppercase tracking-wider text-lovable-ink-muted">Fila operacional</h3>
            <p className="mt-1 text-xs text-lovable-ink-muted">Prioridade por risco, atraso, falta de contato e valor financeiro.</p>
          </div>
          <p className="text-xs text-lovable-ink-muted">{rangeLabel}</p>
        </div>

        <div className="mt-4 grid gap-3 lg:grid-cols-[minmax(0,1fr)_220px_220px]">
          <label className="flex items-center gap-2 rounded-xl border border-lovable-border bg-lovable-surface-soft px-3 py-2 text-sm text-lovable-ink-muted">
            <Search size={15} />
            <input
              value={searchInput}
              onChange={(event) => {
                const nextValue = event.target.value;
                startTransition(() => {
                  setSearchInput(nextValue);
                  setPage(1);
                });
              }}
              placeholder="Buscar por nome, e-mail, etapa ou título..."
              className="w-full bg-transparent text-sm text-lovable-ink outline-none placeholder:text-lovable-ink-muted"
            />
          </label>

          <label className="flex items-center gap-2 rounded-xl border border-lovable-border bg-lovable-surface-soft px-3 py-2 text-sm text-lovable-ink">
            <Filter size={14} className="text-lovable-ink-muted" />
            <select
              value={source}
              onChange={(event) => handleFilterChange({ source: event.target.value as typeof source })}
              className="w-full bg-transparent text-sm outline-none"
            >
              {SOURCE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>

          <label className="flex items-center gap-2 rounded-xl border border-lovable-border bg-lovable-surface-soft px-3 py-2 text-sm text-lovable-ink">
            <Filter size={14} className="text-lovable-ink-muted" />
            <select
              value={severity}
              onChange={(event) => handleFilterChange({ severity: event.target.value as typeof severity })}
              className="w-full bg-transparent text-sm outline-none"
            >
              {SEVERITY_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
        </div>

        {query.data.items.length === 0 ? (
          <div className="mt-4">
            <EmptyState
              icon={AlertTriangle}
              title="Nenhum item na fila operacional"
              description="Ajuste os filtros ou continue monitorando: não há ações urgentes neste recorte."
            />
          </div>
        ) : (
          <div className="mt-4 overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="text-left text-xs uppercase tracking-wider text-lovable-ink-muted">
                <tr>
                  <th className="px-2 py-2">Item</th>
                  <th className="px-2 py-2">Origem</th>
                  <th className="px-2 py-2">Prioridade</th>
                  <th className="px-2 py-2">Valor</th>
                  <th className="px-2 py-2">Dado recente</th>
                  <th className="px-2 py-2">Owner</th>
                  <th className="px-2 py-2 text-right">Ação</th>
                </tr>
              </thead>
              <tbody>
                {query.data.items.map((item) => (
                  <tr key={item.id} className="border-t border-lovable-border align-top">
                    <td className="px-2 py-3">
                      <p className="font-medium text-lovable-ink">{item.title}</p>
                      <p className="mt-1 text-xs text-lovable-ink-muted">{item.subtitle}</p>
                    </td>
                    <td className="px-2 py-3 text-lovable-ink-muted">{item.source_label}</td>
                    <td className="px-2 py-3">
                      <Badge variant={SEVERITY_BADGE[item.severity] ?? "neutral"}>
                        {item.severity === "critical" ? "Crítica" : item.severity === "high" ? "Alta" : item.severity === "medium" ? "Média" : "Baixa"}
                      </Badge>
                    </td>
                    <td className="px-2 py-3 text-lovable-ink">{money(item.value_amount)}</td>
                    <td className="px-2 py-3 text-xs text-lovable-ink-muted">
                      <p>{item.last_contact_at ? `Contato: ${formatDate(item.last_contact_at)}` : item.last_checkin_at ? `Check-in: ${formatDate(item.last_checkin_at)}` : "Sem histórico recente"}</p>
                      <p className="mt-1">{item.stale_days > 0 ? `${item.stale_days} dia(s) de atraso` : "Dentro da janela"}</p>
                    </td>
                    <td className="px-2 py-3 text-lovable-ink-muted">{item.owner_label ?? "Sem owner"}</td>
                    <td className="px-2 py-3 text-right">
                      <Button size="sm" variant="secondary" onClick={() => handleOpenItem(item)}>
                        {item.cta_label}
                        <ArrowRight size={14} />
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className="mt-4 flex flex-col gap-3 border-t border-lovable-border pt-4 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-xs text-lovable-ink-muted">{rangeLabel}</p>
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="ghost"
              disabled={page <= 1}
              onClick={() => startTransition(() => setPage((current) => Math.max(1, current - 1)))}
            >
              Anterior
            </Button>
            <span className="text-xs font-medium text-lovable-ink">
              Página {page} de {totalPages}
            </span>
            <Button
              size="sm"
              variant="ghost"
              disabled={page >= totalPages}
              onClick={() => startTransition(() => setPage((current) => current + 1))}
            >
              Próxima
            </Button>
          </div>
        </div>
      </section>
    </section>
  );
}
