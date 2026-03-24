import { useState } from "react";
import { Download, Mail } from "lucide-react";
import toast from "react-hot-toast";

import { useAuth } from "../../hooks/useAuth";
import type { DashboardReportType } from "../../services/reportService";
import { reportService } from "../../services/reportService";
import { canDispatchMonthlyReports, canExportDashboardReport } from "../../utils/roleAccess";

interface DashboardActionsProps {
  dashboard: DashboardReportType;
  showMonthlyDispatch?: boolean;
  theme?: "default" | "dark";
}

export function DashboardActions({ dashboard, showMonthlyDispatch = false, theme = "default" }: DashboardActionsProps) {
  const { user } = useAuth();
  const [exporting, setExporting] = useState(false);
  const [dispatching, setDispatching] = useState(false);
  const isDark = theme === "dark";
  const canExport = canExportDashboardReport(user?.role);
  const canDispatch = canDispatchMonthlyReports(user?.role);

  const handleExport = async () => {
    if (!canExport) {
      toast.error("Exportacao disponivel apenas para gestao.");
      return;
    }
    setExporting(true);
    try {
      await reportService.exportDashboardPdf(dashboard);
    } catch {
      toast.error("Falha ao exportar o dashboard.");
    } finally {
      setExporting(false);
    }
  };

  const handleDispatch = async () => {
    if (!canDispatch) {
      toast.error("Disparo mensal disponivel apenas para gestao.");
      return;
    }
    setDispatching(true);
    try {
      await reportService.dispatchMonthlyReports();
      toast.success("Disparo mensal iniciado com sucesso.");
    } catch {
      toast.error("Falha ao disparar relatórios mensais.");
    } finally {
      setDispatching(false);
    }
  };

  return (
    <div className="flex flex-wrap gap-2">
      {canExport ? (
        <button
          type="button"
          onClick={handleExport}
          disabled={exporting}
          className={
            isDark
              ? "inline-flex items-center gap-1 rounded-full border border-lovable-border-strong bg-lovable-surface px-3 py-1.5 text-xs font-semibold uppercase tracking-wider text-lovable-ink hover:border-lovable-border-strong/90 hover:bg-lovable-surface-soft disabled:opacity-60"
              : "inline-flex items-center gap-1 rounded-full border border-lovable-border bg-lovable-surface px-3 py-1.5 text-xs font-semibold uppercase tracking-wider text-lovable-ink hover:border-lovable-border-strong disabled:opacity-60"
          }
        >
          <Download size={14} />
          {exporting ? "Exportando..." : "Exportar PDF"}
        </button>
      ) : null}
      {showMonthlyDispatch && canDispatch ? (
        <button
          type="button"
          onClick={handleDispatch}
          disabled={dispatching}
          className={
            isDark
              ? "inline-flex items-center gap-1 rounded-full bg-lovable-success px-3 py-1.5 text-xs font-semibold uppercase tracking-wider text-white hover:brightness-110 disabled:opacity-60"
              : "inline-flex items-center gap-1 rounded-full bg-lovable-primary px-3 py-1.5 text-xs font-semibold uppercase tracking-wider text-white hover:brightness-110 disabled:opacity-60"
          }
        >
          <Mail size={14} />
          {dispatching ? "Enviando..." : "Disparo mensal"}
        </button>
      ) : null}
    </div>
  );
}
