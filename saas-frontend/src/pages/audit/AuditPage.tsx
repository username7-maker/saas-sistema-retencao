import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";
import clsx from "clsx";

import { LoadingPanel } from "../../components/common/LoadingPanel";
import { auditService } from "../../services/auditService";

type ActionBadgeVariant = "danger" | "warning" | "success" | "primary" | "default";

function getActionVariant(action: string): ActionBadgeVariant {
  if (action.startsWith("login_failed") || action.includes("delete") || action.includes("anonymize")) return "danger";
  if (action.startsWith("automation_") || action.startsWith("nps_") || action.startsWith("manager_alert")) return "warning";
  if (action.includes("created") || action.includes("converted") || action.includes("resolved")) return "success";
  if (action.startsWith("login") || action.includes("updated") || action.includes("stage_changed")) return "primary";
  return "default";
}

const BADGE_CLASSES: Record<ActionBadgeVariant, string> = {
  danger: "bg-lovable-danger/15 text-lovable-danger",
  warning: "bg-lovable-warning/15 text-lovable-warning",
  success: "bg-lovable-success/15 text-lovable-success",
  primary: "bg-lovable-primary/15 text-lovable-primary",
  default: "bg-lovable-surface-soft text-lovable-ink-muted",
};

function DetailsCell({ details }: { details: Record<string, unknown> }) {
  const [expanded, setExpanded] = useState(false);
  if (Object.keys(details).length === 0) return <span className="text-lovable-ink-muted">—</span>;

  const preview = Object.entries(details)
    .slice(0, 2)
    .map(([k, v]) => `${k}: ${String(v)}`)
    .join(", ");

  return (
    <div>
      <button
        type="button"
        onClick={() => setExpanded((prev) => !prev)}
        className="text-left text-xs text-lovable-ink-muted hover:text-lovable-ink"
        title={expanded ? "Recolher" : "Expandir"}
      >
        {expanded ? null : <span className="truncate">{preview}{Object.keys(details).length > 2 ? "…" : ""}</span>}
      </button>
      {expanded && (
        <pre className="mt-1 max-h-40 overflow-auto rounded-md border border-lovable-border bg-lovable-surface-soft p-2 text-[10px] text-lovable-ink">
          {JSON.stringify(details, null, 2)}
        </pre>
      )}
      {!expanded && (
        <button
          type="button"
          onClick={() => setExpanded(true)}
          className="text-[10px] text-lovable-ink-muted underline hover:text-lovable-ink"
        >
          ver JSON
        </button>
      )}
    </div>
  );
}

const ENTITY_OPTIONS = ["", "member", "lead", "user", "task", "automation_rule", "nps", "gym"];

export function AuditPage() {
  const [search, setSearch] = useState("");
  const [entityFilter, setEntityFilter] = useState("");

  const query = useQuery({
    queryKey: ["audit", "logs"],
    queryFn: () => auditService.listLogs(200),
    staleTime: 60 * 1000,
  });

  if (query.isLoading) {
    return <LoadingPanel text="Carregando logs de auditoria..." />;
  }

  const allLogs = query.data ?? [];

  const logs = allLogs.filter((log) => {
    const matchesSearch = !search || log.action.toLowerCase().includes(search.toLowerCase());
    const matchesEntity = !entityFilter || log.entity === entityFilter;
    return matchesSearch && matchesEntity;
  });

  return (
    <section className="space-y-6">
      <header>
        <h2 className="font-heading text-3xl font-bold text-lovable-ink">Auditoria</h2>
        <p className="text-sm text-lovable-ink-muted">Registro completo de ações realizadas no sistema.</p>
      </header>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <div className="relative flex-1 min-w-[200px]">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-lovable-ink-muted" />
          <input
            type="text"
            placeholder="Filtrar por ação…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-lg border border-lovable-border bg-lovable-surface py-2 pl-8 pr-3 text-sm text-lovable-ink placeholder:text-lovable-ink-muted focus:border-lovable-primary focus:outline-none focus:ring-1 focus:ring-lovable-primary"
          />
        </div>
        <select
          value={entityFilter}
          onChange={(e) => setEntityFilter(e.target.value)}
          className="rounded-lg border border-lovable-border bg-lovable-surface px-3 py-2 text-sm text-lovable-ink focus:border-lovable-primary focus:outline-none"
        >
          <option value="">Todas as entidades</option>
          {ENTITY_OPTIONS.filter(Boolean).map((e) => (
            <option key={e} value={e}>{e}</option>
          ))}
        </select>
        <span className="self-center text-xs text-lovable-ink-muted">
          {logs.length} de {allLogs.length} eventos
        </span>
      </div>

      <div className="rounded-2xl border border-lovable-border bg-lovable-surface shadow-panel">
        {logs.length === 0 ? (
          <p className="px-4 py-6 text-sm text-lovable-ink-muted">
            {allLogs.length === 0 ? "Nenhum evento registrado." : "Nenhum evento corresponde aos filtros."}
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="border-b border-lovable-border bg-lovable-surface-soft">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">Data</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">Ação</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">Entidade</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">Detalhes</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-lovable-border">
                {logs.map((log) => (
                  <tr key={log.id} className="hover:bg-lovable-surface-soft">
                    <td className="whitespace-nowrap px-4 py-3 text-xs text-lovable-ink-muted">
                      {new Date(log.created_at).toLocaleString("pt-BR")}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={clsx(
                          "rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider",
                          BADGE_CLASSES[getActionVariant(log.action)]
                        )}
                      >
                        {log.action}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs text-lovable-ink-muted">{log.entity}</td>
                    <td className="px-4 py-3">
                      <DetailsCell details={log.details} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </section>
  );
}
