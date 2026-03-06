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
            ? "inline-flex items-center gap-1 rounded-full border border-zinc-700 bg-zinc-900 px-3 py-1.5 text-xs font-semibold uppercase tracking-wider text-zinc-100 hover:border-zinc-600 hover:bg-zinc-800 disabled:opacity-60"
            : "inline-flex items-center gap-1 rounded-full border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold uppercase tracking-wider text-slate-700 hover:border-slate-400 disabled:opacity-60"
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
              ? "inline-flex items-center gap-1 rounded-full bg-emerald-500 px-3 py-1.5 text-xs font-semibold uppercase tracking-wider text-zinc-950 hover:bg-emerald-400 disabled:opacity-60"
              : "inline-flex items-center gap-1 rounded-full bg-brand-500 px-3 py-1.5 text-xs font-semibold uppercase tracking-wider text-white hover:bg-brand-700 disabled:opacity-60"
          }
        >
          <Mail size={14} />
          {dispatching ? "Enviando..." : "Disparo mensal"}
        </button>
      )}
    </div>
  );
}
