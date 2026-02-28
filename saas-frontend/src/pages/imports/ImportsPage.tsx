import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Download, FileUp } from "lucide-react";
import toast from "react-hot-toast";

import { importExportService } from "../../services/importExportService";
import type { ImportSummary } from "../../types";


function ImportResult({ summary }: { summary: ImportSummary | null }) {
  if (!summary) return null;
  return (
    <div className="mt-3 rounded-xl border border-lovable-border bg-lovable-surface-soft p-3 text-xs text-lovable-ink">
      <p>Importados: {summary.imported}</p>
      <p>Duplicados ignorados: {summary.skipped_duplicates}</p>
      <p>Erros: {summary.errors.length}</p>
      {summary.errors.length > 0 && (
        <ul className="mt-2 max-h-36 list-disc space-y-1 overflow-auto pl-5 text-rose-700">
          {summary.errors.slice(0, 20).map((error, index) => (
            <li key={`${error.row_number}-${index}`}>
              Linha {error.row_number}: {error.reason}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function getErrorMessage(error: unknown): string {
  if (typeof error === "object" && error !== null) {
    const maybeAxios = error as {
      response?: {
        data?: {
          detail?: string | Array<{ msg?: string }>;
          message?: string;
        } | string;
      };
    };
    const data = maybeAxios.response?.data;
    if (typeof data === "string" && data.trim()) {
      return data;
    }
    if (typeof data === "object" && data !== null) {
      const detail = data.detail;
      if (typeof detail === "string" && detail.trim()) {
        return detail;
      }
      if (Array.isArray(detail) && detail.length > 0) {
        const firstMessage = detail[0]?.msg;
        if (firstMessage) {
          return firstMessage;
        }
      }
      if (typeof data.message === "string" && data.message.trim()) {
        return data.message;
      }
    }
  }
  return "Falha ao processar arquivo. Verifique formato e colunas.";
}

export function ImportsPage() {
  const [membersFile, setMembersFile] = useState<File | null>(null);
  const [checkinsFile, setCheckinsFile] = useState<File | null>(null);
  const [membersSummary, setMembersSummary] = useState<ImportSummary | null>(null);
  const [checkinsSummary, setCheckinsSummary] = useState<ImportSummary | null>(null);
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  const importMembersMutation = useMutation({
    mutationFn: (file: File) => importExportService.importMembers(file),
    onSuccess: (summary) => {
      setMembersSummary(summary);
      toast.success("Importacao de alunos concluida.");
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });

  const importCheckinsMutation = useMutation({
    mutationFn: (file: File) => importExportService.importCheckins(file),
    onSuccess: (summary) => {
      setCheckinsSummary(summary);
      toast.success("Importacao de check-ins concluida.");
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });

  const exportMembersMutation = useMutation({
    mutationFn: () => importExportService.exportMembersCsv(),
  });

  const exportCheckinsMutation = useMutation({
    mutationFn: () => importExportService.exportCheckinsCsv(dateFrom || undefined, dateTo || undefined),
  });

  const templateMembersMutation = useMutation({
    mutationFn: () => importExportService.downloadMembersTemplateCsv(),
  });

  const templateCheckinsMutation = useMutation({
    mutationFn: () => importExportService.downloadCheckinsTemplateCsv(),
  });

  return (
    <section className="space-y-6">
      <header>
        <h2 className="font-heading text-3xl font-bold text-lovable-ink dark:text-slate-100">Importacoes e Exportacoes (CSV/XLSX)</h2>
        <p className="text-sm text-lovable-ink-muted dark:text-slate-400">
          Envie planilhas de alunos/catraca em CSV ou XLSX e exporte dados do sistema em CSV.
        </p>
      </header>

      <section className="grid gap-4 lg:grid-cols-2">
        <article className="rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel dark:border-slate-700 dark:bg-slate-900">
          <h3 className="text-sm font-semibold uppercase tracking-wider text-lovable-ink-muted dark:text-slate-300">Importar alunos</h3>
          <p className="mt-1 text-xs text-lovable-ink-muted dark:text-slate-400">
            Colunas aceitas: nome/full_name, email, telefone, cpf, matricula, plano, mensalidade, data_matricula.
          </p>
          <input
            type="file"
            accept=".csv,.xlsx,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            onChange={(event) => setMembersFile(event.target.files?.[0] ?? null)}
            className="mt-3 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800"
          />
          <div className="mt-3 flex flex-wrap gap-2">
            <button
              type="button"
              disabled={!membersFile || importMembersMutation.isPending}
              onClick={() => membersFile && importMembersMutation.mutate(membersFile)}
              className="inline-flex items-center gap-1 rounded-lg bg-brand-500 px-3 py-2 text-xs font-semibold uppercase tracking-wider text-white hover:bg-brand-700 disabled:opacity-60"
            >
              <FileUp size={14} />
              {importMembersMutation.isPending ? "Importando..." : "Importar arquivo"}
            </button>
            <button
              type="button"
              disabled={templateMembersMutation.isPending}
              onClick={() => templateMembersMutation.mutate()}
              className="inline-flex items-center gap-1 rounded-lg border border-slate-300 px-3 py-2 text-xs font-semibold uppercase tracking-wider text-lovable-ink hover:border-slate-400 disabled:opacity-60 dark:border-slate-600 dark:text-slate-200"
            >
              <Download size={14} />
              Template alunos
            </button>
          </div>
          <ImportResult summary={membersSummary} />
        </article>

        <article className="rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel dark:border-slate-700 dark:bg-slate-900">
          <h3 className="text-sm font-semibold uppercase tracking-wider text-lovable-ink-muted dark:text-slate-300">Importar catraca/check-ins</h3>
          <p className="mt-1 text-xs text-lovable-ink-muted dark:text-slate-400">
            Match automatico por member_id, email, matricula, cpf ou nome.
          </p>
          <input
            type="file"
            accept=".csv,.xlsx,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            onChange={(event) => setCheckinsFile(event.target.files?.[0] ?? null)}
            className="mt-3 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800"
          />
          <div className="mt-3 flex flex-wrap gap-2">
            <button
              type="button"
              disabled={!checkinsFile || importCheckinsMutation.isPending}
              onClick={() => checkinsFile && importCheckinsMutation.mutate(checkinsFile)}
              className="inline-flex items-center gap-1 rounded-lg bg-brand-500 px-3 py-2 text-xs font-semibold uppercase tracking-wider text-white hover:bg-brand-700 disabled:opacity-60"
            >
              <FileUp size={14} />
              {importCheckinsMutation.isPending ? "Importando..." : "Importar arquivo"}
            </button>
            <button
              type="button"
              disabled={templateCheckinsMutation.isPending}
              onClick={() => templateCheckinsMutation.mutate()}
              className="inline-flex items-center gap-1 rounded-lg border border-slate-300 px-3 py-2 text-xs font-semibold uppercase tracking-wider text-lovable-ink hover:border-slate-400 disabled:opacity-60 dark:border-slate-600 dark:text-slate-200"
            >
              <Download size={14} />
              Template check-ins
            </button>
          </div>
          <ImportResult summary={checkinsSummary} />
        </article>
      </section>

      <section className="rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel dark:border-slate-700 dark:bg-slate-900">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-lovable-ink-muted dark:text-slate-300">Exportar CSV</h3>
        <p className="mt-1 text-xs text-lovable-ink-muted dark:text-slate-400">Baixe alunos e check-ins para auditoria e BI externo.</p>
        <div className="mt-3 grid gap-3 md:grid-cols-[1fr_1fr_auto_auto]">
          <input
            type="date"
            value={dateFrom}
            onChange={(event) => setDateFrom(event.target.value)}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800"
          />
          <input
            type="date"
            value={dateTo}
            onChange={(event) => setDateTo(event.target.value)}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800"
          />
          <button
            type="button"
            disabled={exportMembersMutation.isPending}
            onClick={() => exportMembersMutation.mutate()}
            className="inline-flex items-center justify-center gap-1 rounded-lg border border-slate-300 px-3 py-2 text-xs font-semibold uppercase tracking-wider text-lovable-ink hover:border-slate-400 disabled:opacity-60 dark:border-slate-600 dark:text-slate-200"
          >
            <Download size={14} />
            {exportMembersMutation.isPending ? "Exportando..." : "Exportar membros CSV"}
          </button>
          <button
            type="button"
            disabled={exportCheckinsMutation.isPending}
            onClick={() => exportCheckinsMutation.mutate()}
            className="inline-flex items-center justify-center gap-1 rounded-lg bg-brand-500 px-3 py-2 text-xs font-semibold uppercase tracking-wider text-white hover:bg-brand-700 disabled:opacity-60"
          >
            <Download size={14} />
            {exportCheckinsMutation.isPending ? "Exportando..." : "Exportar check-ins CSV"}
          </button>
        </div>
      </section>
    </section>
  );
}
