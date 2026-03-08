import { useState } from "react";
import { Download, Mail } from "lucide-react";
import toast from "react-hot-toast";

import type { DashboardReportType } from "../../services/reportService";
import { reportService } from "../../services/reportService";

interface DashboardActionsProps {
  dashboard: DashboardReportType;
  showMonthlyDispatch?: boolean;
  theme?: "default" | "dark";
}

export function DashboardActions({ dashboard, showMonthlyDispatch = false, theme = "default" }: DashboardActionsProps) {
  const [exporting, setExporting] = useState(false);
  const [dispatching, setDispatching] = useState(false);
  const isDark = theme === "dark";

  const handleExport = async () => {
    setExporting(true);
    try {
      await reportService.exportDashboardPdf(dashboard);
    } finally {
      setExporting(false);
    }
  };

  const handleDispatch = async () => {
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
      {showMonthlyDispatch && (
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
      )}
    </div>
  );
}
