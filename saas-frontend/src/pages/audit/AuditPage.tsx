import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";
import clsx from "clsx";

import { LoadingPanel } from "../../components/common/LoadingPanel";
import { EmptyState } from "../../components/ui";
import {
  CommandCard,
  Input,
  Select,
  Table,
  TableInner,
  TableHead,
  TableBody,
  TableRow,
  TableHeaderCell,
  TableCell,
} from "../../components/ui2";
import { auditService } from "../../services/auditService";
import { getPermissionAwareMessage } from "../../utils/httpErrors";

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

  if (query.isError) {
    return (
      <EmptyState
        icon={Search}
        title="Nao foi possivel carregar a auditoria"
        description={getPermissionAwareMessage(query.error, "Tente novamente para recuperar os eventos do sistema.")}
        action={{ label: "Tentar novamente", onClick: () => void query.refetch() }}
      />
    );
  }

  const allLogs = query.data ?? [];

  const logs = allLogs.filter((log) => {
    const matchesSearch = !search || log.action.toLowerCase().includes(search.toLowerCase());
    const matchesEntity = !entityFilter || log.entity === entityFilter;
    return matchesSearch && matchesEntity;
  });

  return (
    <section className="space-y-6">
      <CommandCard variant="elevated">
        <div>
          <p className="text-[11px] font-bold uppercase tracking-[0.3em] text-blue-400">Sistema</p>
          <h2 className="mt-1 font-heading text-3xl font-bold md:text-4xl">
            <span className="bg-gradient-to-r from-white via-white to-blue-300 bg-clip-text text-transparent">
              Auditoria
            </span>
          </h2>
          <p className="mt-1 text-sm text-lovable-ink-muted">Registro completo de ações realizadas no sistema.</p>
        </div>
      </CommandCard>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <div className="relative flex-1 min-w-[200px]">
          <Search size={14} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-lovable-ink-muted" />
          <Input
            type="text"
            placeholder="Filtrar por ação…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-8"
          />
        </div>
        <Select
          value={entityFilter}
          onChange={(e) => setEntityFilter(e.target.value)}
        >
          <option value="">Todas as entidades</option>
          {ENTITY_OPTIONS.filter(Boolean).map((e) => (
            <option key={e} value={e}>{e}</option>
          ))}
        </Select>
        <span className="self-center text-xs text-lovable-ink-muted">
          {logs.length} de {allLogs.length} eventos
        </span>
      </div>

      <Table>
        {logs.length === 0 ? (
          <p className="px-4 py-6 text-sm text-lovable-ink-muted">
            {allLogs.length === 0 ? "Nenhum evento registrado." : "Nenhum evento corresponde aos filtros."}
          </p>
        ) : (
          <div className="overflow-x-auto">
            <TableInner>
              <TableHead>
                <TableRow>
                  <TableHeaderCell>Data</TableHeaderCell>
                  <TableHeaderCell>Ação</TableHeaderCell>
                  <TableHeaderCell>Entidade</TableHeaderCell>
                  <TableHeaderCell>Detalhes</TableHeaderCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {logs.map((log) => (
                  <TableRow key={log.id}>
                    <TableCell className="whitespace-nowrap text-xs text-lovable-ink-muted">
                      {new Date(log.created_at).toLocaleString("pt-BR")}
                    </TableCell>
                    <TableCell>
                      <span
                        className={clsx(
                          "rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider",
                          BADGE_CLASSES[getActionVariant(log.action)]
                        )}
                      >
                        {log.action}
                      </span>
                    </TableCell>
                    <TableCell className="text-xs text-lovable-ink-muted">{log.entity}</TableCell>
                    <TableCell>
                      <DetailsCell details={log.details} />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </TableInner>
          </div>
        )}
      </Table>
    </section>
  );
}
