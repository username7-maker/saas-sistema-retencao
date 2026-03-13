import { useMemo, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Download, FileUp } from "lucide-react";
import toast from "react-hot-toast";

import { importExportService } from "../../services/importExportService";
import type { ImportSummary, MissingMemberEntry } from "../../types";
import {
  getIgnoredRowsHint,
  getImportSummaryNotice,
  getVisibleImportErrors,
  isDuplicateOnlyImport,
} from "./importSummary";

function downloadCsv(filename: string, rows: string[][]): void {
  const content = rows
    .map((row) =>
      row
        .map((cell) => {
          const escaped = cell.replace(/"/g, '""');
          return /[",\n]/.test(escaped) ? `"${escaped}"` : escaped;
        })
        .join(","),
    )
    .join("\n");

  const blob = new Blob([content], { type: "text/csv;charset=utf-8;" });
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

function exportMissingMembers(summary: ImportSummary): void {
  const rows: string[][] = [["nome", "ocorrencias", "plano_exemplo"]];
  for (const item of summary.missing_members) {
    rows.push([item.name, String(item.occurrences), item.sample_plan ?? ""]);
  }
  downloadCsv("pendencias-catraca.csv", rows);
}

function MissingMembersPanel({ missingMembers }: { missingMembers: MissingMemberEntry[] }) {
  if (missingMembers.length === 0) return null;

  return (
    <div className="mt-3 rounded-lg border border-amber-300 bg-amber-50 p-3 text-amber-950">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="font-semibold">Nomes presentes na catraca, mas ausentes na base de alunos</p>
          <p className="text-xs text-amber-900/80">
            Esses nomes nao foram encontrados no cadastro atual. Voce pode exportar a lista ou reimportar usando cadastro provisiorio.
          </p>
        </div>
      </div>
      <ul className="mt-2 grid gap-1 text-sm md:grid-cols-2">
        {missingMembers.slice(0, 16).map((item) => (
          <li key={item.name} className="rounded-md bg-white/70 px-2 py-1">
            <span className="font-medium">{item.name}</span>
            <span className="ml-2 text-xs text-amber-900/80">{item.occurrences} registros</span>
            {item.sample_plan ? <span className="ml-2 text-xs text-amber-900/80">Plano: {item.sample_plan}</span> : null}
          </li>
        ))}
      </ul>
      {missingMembers.length > 16 ? (
        <p className="mt-2 text-xs text-amber-900/80">Mostrando 16 de {missingMembers.length} nomes pendentes.</p>
      ) : null}
    </div>
  );
}

function CreatedMembersPanel({ names }: { names: string[] }) {
  if (names.length === 0) return null;

  return (
    <div className="mt-3 rounded-lg border border-emerald-300 bg-emerald-50 p-3 text-emerald-950">
      <p className="font-semibold">Cadastros provisórios criados nesta importação</p>
      <ul className="mt-2 grid gap-1 text-sm md:grid-cols-2">
        {names.slice(0, 16).map((name) => (
          <li key={name} className="rounded-md bg-white/70 px-2 py-1">
            {name}
          </li>
        ))}
      </ul>
      {names.length > 16 ? (
        <p className="mt-2 text-xs text-emerald-900/80">Mostrando 16 de {names.length} nomes criados.</p>
      ) : null}
    </div>
  );
}

function ImportResult({
  summary,
  allowMissingExport = false,
}: {
  summary: ImportSummary | null;
  allowMissingExport?: boolean;
}) {
  if (!summary) return null;
  const visibleErrors = getVisibleImportErrors(summary);
  const notice = getImportSummaryNotice(summary);
  const ignoredRowsHint = getIgnoredRowsHint(summary);

  return (
    <div className="mt-3 rounded-xl border border-lovable-border bg-lovable-surface-soft p-3 text-xs text-lovable-ink">
      {notice ? (
        <div
          className={`mb-3 rounded-lg border px-3 py-2 ${
            notice.tone === "info"
              ? "border-sky-300 bg-sky-50 text-sky-950"
              : "border-emerald-300 bg-emerald-50 text-emerald-950"
          }`}
        >
          <p className="font-semibold">{notice.title}</p>
          <p className="mt-1 text-[11px] leading-relaxed">{notice.description}</p>
        </div>
      ) : null}

      <p>Importados: {summary.imported}</p>
      <p>Duplicados ignorados: {summary.skipped_duplicates}</p>
      <p>Linhas ignoradas: {summary.ignored_rows}</p>
      {summary.provisional_members_created > 0 ? <p>Cadastros provisorios criados: {summary.provisional_members_created}</p> : null}
      <p>Erros tecnicos: {visibleErrors.length}</p>
      {summary.missing_members.length > 0 ? <p>Pendencias de cadastro: {summary.missing_members.length}</p> : null}
      {ignoredRowsHint ? <p className="mt-2 text-[11px] text-lovable-ink-muted">{ignoredRowsHint}</p> : null}

      <CreatedMembersPanel names={summary.provisional_members} />
      <MissingMembersPanel missingMembers={summary.missing_members} />

      {allowMissingExport && summary.missing_members.length > 0 ? (
        <button
          type="button"
          onClick={() => exportMissingMembers(summary)}
          className="mt-3 inline-flex items-center gap-1 rounded-lg border border-amber-400 px-3 py-2 text-xs font-semibold uppercase tracking-wider text-amber-900 hover:bg-amber-100"
        >
          <Download size={14} />
          Exportar pendentes CSV
        </button>
      ) : null}

      {visibleErrors.length > 0 ? (
        <ul className="mt-3 max-h-36 list-disc space-y-1 overflow-auto pl-5 text-lovable-danger">
          {visibleErrors.slice(0, 20).map((error, index) => (
            <li key={`${error.row_number}-${index}`}>
              Linha {error.row_number}: {error.reason}
            </li>
          ))}
        </ul>
      ) : null}
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

function hasInvalidDateRange(dateFrom: string, dateTo: string): boolean {
  if (!dateFrom || !dateTo) return false;
  return new Date(dateFrom).getTime() > new Date(dateTo).getTime();
}

export function ImportsPage() {
  const queryClient = useQueryClient();
  const [membersFile, setMembersFile] = useState<File | null>(null);
  const [checkinsFile, setCheckinsFile] = useState<File | null>(null);
  const [membersSummary, setMembersSummary] = useState<ImportSummary | null>(null);
  const [checkinsSummary, setCheckinsSummary] = useState<ImportSummary | null>(null);
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [autoCreateMissingMembers, setAutoCreateMissingMembers] = useState(false);

  const hasMissingMembers = useMemo(() => (checkinsSummary?.missing_members.length ?? 0) > 0, [checkinsSummary]);

  const refreshImportedDataViews = () => {
    void Promise.all([
      queryClient.invalidateQueries({ queryKey: ["members"] }),
      queryClient.invalidateQueries({ queryKey: ["dashboard"] }),
      queryClient.invalidateQueries({ queryKey: ["assessments"] }),
      queryClient.invalidateQueries({ queryKey: ["member-timeline"] }),
      queryClient.invalidateQueries({ queryKey: ["risk-alerts"] }),
      queryClient.invalidateQueries({ queryKey: ["roi-summary"] }),
      queryClient.invalidateQueries({ queryKey: ["insights"] }),
      queryClient.invalidateQueries({ queryKey: ["tasks"] }),
    ]);
  };

  const importMembersMutation = useMutation({
    mutationFn: (file: File) => importExportService.importMembers(file),
    onSuccess: (summary) => {
      setMembersSummary(summary);
      refreshImportedDataViews();
      toast.success("Importacao de alunos concluida.");
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });

  const importCheckinsMutation = useMutation({
    mutationFn: ({ file, autoCreate }: { file: File; autoCreate: boolean }) =>
      importExportService.importCheckins(file, autoCreate),
    onSuccess: (summary) => {
      setCheckinsSummary(summary);
      refreshImportedDataViews();
      if (isDuplicateOnlyImport(summary)) {
        toast.success("Esse arquivo ja tinha sido importado antes. Nenhum check-in novo foi duplicado.");
        return;
      }
      if (summary.provisional_members_created > 0) {
        toast.success(`Importacao concluida com ${summary.provisional_members_created} cadastros provisorios.`);
        return;
      }
      toast.success("Importacao de check-ins concluida.");
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });

  const exportMembersMutation = useMutation({
    mutationFn: () => importExportService.exportMembersCsv(),
    onSuccess: () => toast.success("Exportacao de membros concluida."),
    onError: (error) => toast.error(getErrorMessage(error)),
  });

  const exportCheckinsMutation = useMutation({
    mutationFn: () => importExportService.exportCheckinsCsv(dateFrom || undefined, dateTo || undefined),
    onSuccess: () => toast.success("Exportacao de catraca/check-ins concluida."),
    onError: (error) => toast.error(getErrorMessage(error)),
  });

  const templateMembersMutation = useMutation({
    mutationFn: () => importExportService.downloadMembersTemplateCsv(),
    onError: (error) => toast.error(getErrorMessage(error)),
  });

  const templateCheckinsMutation = useMutation({
    mutationFn: () => importExportService.downloadCheckinsTemplateCsv(),
    onError: (error) => toast.error(getErrorMessage(error)),
  });

  return (
    <section className="space-y-6">
      <header>
        <h2 className="font-heading text-3xl font-bold text-lovable-ink">Importacoes e Exportacoes (CSV/XLSX)</h2>
        <p className="text-sm text-lovable-ink-muted">
          Envie planilhas de alunos/catraca em CSV ou XLSX e exporte dados do sistema em CSV.
        </p>
      </header>

      <section className="grid gap-4 lg:grid-cols-2">
        <article className="rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
          <h3 className="text-sm font-semibold uppercase tracking-wider text-lovable-ink-muted">Importar alunos</h3>
          <p className="mt-1 text-xs text-lovable-ink-muted">
            Colunas aceitas: nome/full_name, email, telefone, cpf, matricula, plano, mensalidade, data_matricula.
          </p>
          <input
            type="file"
            accept=".csv,.xlsx,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            onChange={(event) => setMembersFile(event.target.files?.[0] ?? null)}
            className="mt-3 w-full rounded-lg border border-lovable-border bg-lovable-surface px-3 py-2 text-sm text-lovable-ink"
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
              className="inline-flex items-center gap-1 rounded-lg border border-lovable-border px-3 py-2 text-xs font-semibold uppercase tracking-wider text-lovable-ink hover:border-lovable-border-strong disabled:opacity-60"
            >
              <Download size={14} />
              Template alunos
            </button>
          </div>
          <ImportResult summary={membersSummary} />
        </article>

        <article className="rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
          <h3 className="text-sm font-semibold uppercase tracking-wider text-lovable-ink-muted">Importar catraca/check-ins</h3>
          <p className="mt-1 text-xs text-lovable-ink-muted">
            Match automatico por member_id, email, matricula, cpf ou nome.
          </p>
          <input
            type="file"
            accept=".csv,.xlsx,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            onChange={(event) => setCheckinsFile(event.target.files?.[0] ?? null)}
            className="mt-3 w-full rounded-lg border border-lovable-border bg-lovable-surface px-3 py-2 text-sm text-lovable-ink"
          />
          <label className="mt-3 flex items-start gap-2 text-sm text-lovable-ink">
            <input
              type="checkbox"
              checked={autoCreateMissingMembers}
              onChange={(event) => setAutoCreateMissingMembers(event.target.checked)}
              className="mt-1 h-4 w-4 rounded border-lovable-border text-brand-500 focus:ring-brand-500"
            />
            <span>
              Criar cadastro provisorio quando o nome estiver na catraca, mas ainda nao existir na base de alunos.
              <span className="block text-xs text-lovable-ink-muted">
                Use isso apenas quando o arquivo da catraca trouxer pessoas validas que ainda nao foram importadas como alunos.
              </span>
            </span>
          </label>
          <div className="mt-3 flex flex-wrap gap-2">
            <button
              type="button"
              disabled={!checkinsFile || importCheckinsMutation.isPending}
              onClick={() =>
                checkinsFile &&
                importCheckinsMutation.mutate({ file: checkinsFile, autoCreate: autoCreateMissingMembers })
              }
              className="inline-flex items-center gap-1 rounded-lg bg-brand-500 px-3 py-2 text-xs font-semibold uppercase tracking-wider text-white hover:bg-brand-700 disabled:opacity-60"
            >
              <FileUp size={14} />
              {importCheckinsMutation.isPending ? "Importando..." : "Importar arquivo"}
            </button>
            <button
              type="button"
              disabled={templateCheckinsMutation.isPending}
              onClick={() => templateCheckinsMutation.mutate()}
              className="inline-flex items-center gap-1 rounded-lg border border-lovable-border px-3 py-2 text-xs font-semibold uppercase tracking-wider text-lovable-ink hover:border-lovable-border-strong disabled:opacity-60"
            >
              <Download size={14} />
              Template check-ins
            </button>
            <button
              type="button"
              disabled={!hasMissingMembers || !checkinsSummary}
              onClick={() => checkinsSummary && exportMissingMembers(checkinsSummary)}
              className="inline-flex items-center gap-1 rounded-lg border border-amber-400 px-3 py-2 text-xs font-semibold uppercase tracking-wider text-amber-900 hover:bg-amber-100 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <Download size={14} />
              Exportar pendentes
            </button>
          </div>
          <ImportResult summary={checkinsSummary} allowMissingExport />
        </article>
      </section>

      <section className="rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-lovable-ink-muted">Exportar CSV</h3>
        <p className="mt-1 text-xs text-lovable-ink-muted">Baixe alunos e check-ins para auditoria e BI externo.</p>
        <div className="mt-3 grid gap-3 md:grid-cols-[1fr_1fr_auto_auto]">
          <input
            type="date"
            value={dateFrom}
            onChange={(event) => setDateFrom(event.target.value)}
            className="rounded-lg border border-lovable-border bg-lovable-surface px-3 py-2 text-sm text-lovable-ink"
          />
          <input
            type="date"
            value={dateTo}
            onChange={(event) => setDateTo(event.target.value)}
            className="rounded-lg border border-lovable-border bg-lovable-surface px-3 py-2 text-sm text-lovable-ink"
          />
          <button
            type="button"
            disabled={exportMembersMutation.isPending}
            onClick={() => exportMembersMutation.mutate()}
            className="inline-flex items-center justify-center gap-1 rounded-lg border border-lovable-border px-3 py-2 text-xs font-semibold uppercase tracking-wider text-lovable-ink hover:border-lovable-border-strong disabled:opacity-60"
          >
            <Download size={14} />
            {exportMembersMutation.isPending ? "Exportando..." : "Exportar membros CSV"}
          </button>
          <button
            type="button"
            disabled={exportCheckinsMutation.isPending}
            onClick={() => {
              if (hasInvalidDateRange(dateFrom, dateTo)) {
                toast.error("Periodo invalido: data inicial maior que data final.");
                return;
              }
              exportCheckinsMutation.mutate();
            }}
            className="inline-flex items-center justify-center gap-1 rounded-lg bg-brand-500 px-3 py-2 text-xs font-semibold uppercase tracking-wider text-white hover:bg-brand-700 disabled:opacity-60"
          >
            <Download size={14} />
            {exportCheckinsMutation.isPending ? "Exportando..." : "Exportar catraca CSV"}
          </button>
        </div>
      </section>
    </section>
  );
}
