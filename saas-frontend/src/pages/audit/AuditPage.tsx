import { useQuery } from "@tanstack/react-query";

import { LoadingPanel } from "../../components/common/LoadingPanel";
import { auditService } from "../../services/auditService";

export function AuditPage() {
  const query = useQuery({
    queryKey: ["audit", "logs"],
    queryFn: () => auditService.listLogs(200),
    staleTime: 60 * 1000,
  });

  if (query.isLoading) {
    return <LoadingPanel text="Carregando logs de auditoria..." />;
  }

  const logs = query.data ?? [];

  return (
    <section className="space-y-6">
      <header>
        <h2 className="font-heading text-3xl font-bold text-lovable-ink">Auditoria</h2>
        <p className="text-sm text-lovable-ink-muted">Registro completo de ações realizadas no sistema.</p>
      </header>

      <div className="rounded-2xl border border-lovable-border bg-lovable-surface shadow-panel">
        {logs.length === 0 ? (
          <p className="px-4 py-6 text-sm text-lovable-ink-muted">Nenhum evento registrado.</p>
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
                    <td className="px-4 py-3 text-xs text-lovable-ink-muted whitespace-nowrap">
                      {new Date(log.created_at).toLocaleString("pt-BR")}
                    </td>
                    <td className="px-4 py-3 font-medium text-lovable-ink">
                      <code className="rounded bg-lovable-primary-soft px-1.5 py-0.5 text-xs text-lovable-primary">
                        {log.action}
                      </code>
                    </td>
                    <td className="px-4 py-3 text-lovable-ink-muted">{log.entity}</td>
                    <td className="px-4 py-3 text-xs text-lovable-ink-muted">
                      {Object.keys(log.details).length > 0
                        ? JSON.stringify(log.details)
                        : "—"}
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
