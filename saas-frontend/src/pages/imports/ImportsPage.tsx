import { useMemo, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Download, FileUp, Link2 } from "lucide-react";
import toast from "react-hot-toast";

import { importExportService } from "../../services/importExportService";
import type { ImportMappingOption, ImportPreview, ImportSummary, MissingMemberEntry } from "../../types";
import {
  getIgnoredRowsHint,
  getImportSummaryNotice,
  getVisibleImportErrors,
  isDuplicateOnlyImport,
} from "./importSummary";

const IGNORE_MAPPING_VALUE = "__ignore__";

type ColumnMappingState = Record<string, string | null>;

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
  exportMissingMembersEntries(summary.missing_members);
}

function exportMissingMembersEntries(missingMembers: MissingMemberEntry[]): void {
  const rows: string[][] = [["nome", "ocorrencias", "plano_exemplo"]];
  for (const item of missingMembers) {
    rows.push([item.name, String(item.occurrences), item.sample_plan ?? ""]);
  }
  downloadCsv("pendencias-catraca.csv", rows);
}

function normalizeMapping(mapping: ColumnMappingState | null | undefined): ColumnMappingState {
  const normalized: ColumnMappingState = {};
  for (const [key, value] of Object.entries(mapping ?? {})) {
    if (!key) continue;
    normalized[key] = value ?? null;
  }
  return normalized;
}

function areMappingsEqual(current: ColumnMappingState | null | undefined, baseline: ColumnMappingState | null | undefined): boolean {
  const currentNormalized = normalizeMapping(current);
  const baselineNormalized = normalizeMapping(baseline);
  const allKeys = Array.from(new Set([...Object.keys(currentNormalized), ...Object.keys(baselineNormalized)])).sort();
  return allKeys.every((key) => (currentNormalized[key] ?? null) === (baselineNormalized[key] ?? null));
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
      <p className="font-semibold">Cadastros provisorios criados nesta importacao</p>
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

function formatPreviewValue(value: unknown): string {
  if (value === null || value === undefined) return "-";
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  if (Array.isArray(value)) {
    return value.map((item) => formatPreviewValue(item)).join(", ");
  }
  return JSON.stringify(value);
}

function ColumnMappingEditor({
  preview,
  mapping,
  onChange,
  isDirty,
}: {
  preview: ImportPreview | null;
  mapping: ColumnMappingState;
  onChange: (mapping: ColumnMappingState) => void;
  isDirty: boolean;
}) {
  if (!preview || preview.detected_columns.length === 0) return null;

  const optionsByValue = new Map<string, ImportMappingOption>(
    preview.mapping_options.map((option) => [option.value, option]),
  );

  return (
    <div className="mt-3 rounded-xl border border-lovable-border bg-lovable-surface-soft p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold uppercase tracking-wider text-lovable-ink-muted">Mapeamento de colunas</p>
          <p className="mt-1 text-xs text-lovable-ink-muted">
            Confirme para onde cada coluna da planilha deve apontar antes da importacao final.
          </p>
        </div>
        {isDirty ? (
          <span className="rounded-full border border-amber-300 bg-amber-50 px-3 py-1 text-[11px] font-semibold uppercase tracking-wider text-amber-900">
            Revalidacao pendente
          </span>
        ) : preview.mapping_ready ? (
          <span className="rounded-full border border-emerald-300 bg-emerald-50 px-3 py-1 text-[11px] font-semibold uppercase tracking-wider text-emerald-900">
            Mapeamento valido
          </span>
        ) : (
          <span className="rounded-full border border-rose-300 bg-rose-50 px-3 py-1 text-[11px] font-semibold uppercase tracking-wider text-rose-900">
            Mapeamento incompleto
          </span>
        )}
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-2">
        {preview.detected_columns.map((column) => {
          const selectedValue = mapping[column] ?? "";
          const selectedOption = selectedValue ? optionsByValue.get(selectedValue) : null;
          return (
            <label key={column} className="space-y-1 rounded-lg border border-lovable-border bg-lovable-surface px-3 py-3">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-lovable-ink-muted">{column}</span>
              <select
                value={selectedValue}
                onChange={(event) =>
                  onChange({
                    ...mapping,
                    [column]: event.target.value === "" ? null : event.target.value,
                  })
                }
                className="w-full rounded-lg border border-lovable-border bg-lovable-surface px-3 py-2 text-sm text-lovable-ink"
              >
                <option value="">Selecione um destino</option>
                <option value={IGNORE_MAPPING_VALUE}>Ignorar coluna</option>
                {preview.mapping_options.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                    {option.required ? " (obrigatorio)" : ""}
                  </option>
                ))}
              </select>
              {selectedOption ? (
                <span className="text-[11px] text-lovable-ink-muted">Destino: {selectedOption.label}</span>
              ) : selectedValue === IGNORE_MAPPING_VALUE ? (
                <span className="text-[11px] text-lovable-ink-muted">Essa coluna sera ignorada no processamento.</span>
              ) : (
                <span className="text-[11px] text-lovable-ink-muted">Sem destino definido ainda.</span>
              )}
            </label>
          );
        })}
      </div>

      {preview.missing_required_fields.length > 0 ? (
        <div className="mt-3 rounded-lg border border-rose-300 bg-rose-50 px-3 py-2 text-xs text-rose-950">
          <p className="font-semibold">Campos obrigatorios ainda sem mapeamento</p>
          <p className="mt-1">{preview.missing_required_fields.join(", ")}</p>
        </div>
      ) : null}

      {preview.duplicate_target_fields.length > 0 ? (
        <div className="mt-3 rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-950">
          <p className="font-semibold">Destinos duplicados</p>
          <p className="mt-1">{preview.duplicate_target_fields.join(", ")}</p>
        </div>
      ) : null}

      {isDirty ? (
        <p className="mt-3 text-xs text-amber-900">
          O mapeamento foi alterado depois do preview. Clique em <strong>Revalidar mapeamento</strong> antes de confirmar a importacao.
        </p>
      ) : null}
    </div>
  );
}

function PreviewResult({
  preview,
  allowMissingExport = false,
  mappingDirty = false,
}: {
  preview: ImportPreview | null;
  allowMissingExport?: boolean;
  mappingDirty?: boolean;
}) {
  if (!preview) return null;

  return (
    <div className="mt-3 rounded-xl border border-sky-300 bg-sky-50 p-3 text-xs text-sky-950">
      <div className="rounded-lg border border-sky-200 bg-white/80 px-3 py-2">
        <p className="font-semibold">Preview validado. Nada foi gravado ainda.</p>
        <p className="mt-1 text-[11px] leading-relaxed text-sky-900/80">
          Revise o impacto previsto antes de confirmar a importacao final.
        </p>
      </div>

      {mappingDirty ? (
        <div className="mt-3 rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-amber-950">
          <p className="font-semibold">Mapeamento alterado apos a ultima validacao</p>
          <p className="mt-1 text-[11px] leading-relaxed">
            Revalide o arquivo para que a pre-analise reflita o mapeamento atual.
          </p>
        </div>
      ) : null}

      <div className="mt-3 grid gap-2 md:grid-cols-2">
        <p>Total de linhas: {preview.total_rows}</p>
        <p>Linhas validas: {preview.valid_rows}</p>
        <p>Serao criados: {preview.would_create}</p>
        {preview.would_update > 0 ? <p>Serao atualizados: {preview.would_update}</p> : null}
        <p>Serao ignorados: {preview.would_skip}</p>
        {preview.ignored_rows > 0 ? <p>Linhas ignoradas: {preview.ignored_rows}</p> : null}
        {preview.provisional_members_possible > 0 ? (
          <p>Cadastros provisorios possiveis: {preview.provisional_members_possible}</p>
        ) : null}
      </div>

      {preview.recognized_columns.length > 0 ? (
        <div className="mt-3">
          <p className="font-semibold">Colunas reconhecidas</p>
          <p className="mt-1 text-[11px] text-sky-900/80">{preview.recognized_columns.join(", ")}</p>
        </div>
      ) : null}

      {preview.unrecognized_columns.length > 0 ? (
        <div className="mt-3 rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-amber-950">
          <p className="font-semibold">Colunas ainda fora do dicionario padrao</p>
          <p className="mt-1 text-[11px] leading-relaxed">{preview.unrecognized_columns.join(", ")}</p>
        </div>
      ) : null}

      {preview.warnings.length > 0 ? (
        <ul className="mt-3 space-y-1 rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-[11px] text-amber-950">
          {preview.warnings.map((warning) => (
            <li key={warning}>- {warning}</li>
          ))}
        </ul>
      ) : null}

      {preview.sample_rows.length > 0 ? (
        <div className="mt-3">
          <p className="font-semibold">Amostra do impacto</p>
          <ul className="mt-2 space-y-2">
            {preview.sample_rows.map((row) => (
              <li key={`${row.row_number}-${row.action}`} className="rounded-lg border border-sky-200 bg-white/80 px-3 py-2">
                <p className="font-medium">
                  Linha {row.row_number} - {row.action}
                </p>
                <div className="mt-1 grid gap-1 text-[11px] text-sky-900/80">
                  {Object.entries(row.preview).map(([key, value]) => (
                    <p key={key}>
                      <span className="font-medium">{key}:</span> {formatPreviewValue(value)}
                    </p>
                  ))}
                </div>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <MissingMembersPanel missingMembers={preview.missing_members} />

      {allowMissingExport && preview.missing_members.length > 0 ? (
        <button
          type="button"
          onClick={() => exportMissingMembersEntries(preview.missing_members)}
          className="mt-3 inline-flex items-center gap-1 rounded-lg border border-amber-400 px-3 py-2 text-xs font-semibold uppercase tracking-wider text-amber-900 hover:bg-amber-100"
        >
          <Download size={14} />
          Exportar pendentes CSV
        </button>
      ) : null}

      {preview.errors.length > 0 ? (
        <ul className="mt-3 max-h-36 list-disc space-y-1 overflow-auto pl-5 text-lovable-danger">
          {preview.errors.slice(0, 20).map((error, index) => (
            <li key={`${error.row_number}-${index}`}>
              Linha {error.row_number}: {error.reason}
            </li>
          ))}
        </ul>
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

function getValidateButtonLabel(preview: ImportPreview | null, pending: boolean): string {
  if (pending) return "Validando...";
  return preview ? "Revalidar mapeamento" : "Validar arquivo";
}

export function ImportsPage() {
  const queryClient = useQueryClient();
  const [membersFile, setMembersFile] = useState<File | null>(null);
  const [checkinsFile, setCheckinsFile] = useState<File | null>(null);
  const [assessmentsFile, setAssessmentsFile] = useState<File | null>(null);
  const [membersPreview, setMembersPreview] = useState<ImportPreview | null>(null);
  const [checkinsPreview, setCheckinsPreview] = useState<ImportPreview | null>(null);
  const [assessmentsPreview, setAssessmentsPreview] = useState<ImportPreview | null>(null);
  const [membersSummary, setMembersSummary] = useState<ImportSummary | null>(null);
  const [checkinsSummary, setCheckinsSummary] = useState<ImportSummary | null>(null);
  const [assessmentsSummary, setAssessmentsSummary] = useState<ImportSummary | null>(null);
  const [membersMapping, setMembersMapping] = useState<ColumnMappingState>({});
  const [checkinsMapping, setCheckinsMapping] = useState<ColumnMappingState>({});
  const [assessmentsMapping, setAssessmentsMapping] = useState<ColumnMappingState>({});
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [autoCreateMissingMembers, setAutoCreateMissingMembers] = useState(false);

  const hasMissingMembers = useMemo(() => (checkinsSummary?.missing_members.length ?? 0) > 0, [checkinsSummary]);
  const membersMappingDirty = useMemo(
    () => !areMappingsEqual(membersMapping, membersPreview?.suggested_mapping),
    [membersMapping, membersPreview],
  );
  const checkinsMappingDirty = useMemo(
    () => !areMappingsEqual(checkinsMapping, checkinsPreview?.suggested_mapping),
    [checkinsMapping, checkinsPreview],
  );
  const assessmentsMappingDirty = useMemo(
    () => !areMappingsEqual(assessmentsMapping, assessmentsPreview?.suggested_mapping),
    [assessmentsMapping, assessmentsPreview],
  );

  const refreshImportedDataViews = () => {
    void Promise.all([
      queryClient.invalidateQueries({ queryKey: ["members"] }),
      queryClient.invalidateQueries({ queryKey: ["dashboard"] }),
      queryClient.invalidateQueries({ queryKey: ["dashboard", "action-center"] }),
      queryClient.invalidateQueries({ queryKey: ["assessments"] }),
      queryClient.invalidateQueries({ queryKey: ["member-timeline"] }),
      queryClient.invalidateQueries({ queryKey: ["risk-alerts"] }),
      queryClient.invalidateQueries({ queryKey: ["roi-summary"] }),
      queryClient.invalidateQueries({ queryKey: ["insights"] }),
      queryClient.invalidateQueries({ queryKey: ["tasks"] }),
    ]);
  };

  const importMembersMutation = useMutation({
    mutationFn: ({ file, mapping }: { file: File; mapping: ColumnMappingState }) =>
      importExportService.importMembers(file, mapping),
    onSuccess: (summary) => {
      setMembersSummary(summary);
      setMembersPreview(null);
      refreshImportedDataViews();
      toast.success("Importacao de alunos concluida.");
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });

  const previewMembersMutation = useMutation({
    mutationFn: ({ file, mapping }: { file: File; mapping: ColumnMappingState }) =>
      importExportService.previewMembers(file, mapping),
    onSuccess: (preview) => {
      setMembersPreview(preview);
      setMembersMapping(preview.suggested_mapping);
      setMembersSummary(null);
      toast.success("Preview de alunos gerado. Revise o impacto antes de confirmar.");
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });

  const importCheckinsMutation = useMutation({
    mutationFn: ({ file, autoCreate, mapping }: { file: File; autoCreate: boolean; mapping: ColumnMappingState }) =>
      importExportService.importCheckins(file, autoCreate, mapping),
    onSuccess: (summary) => {
      setCheckinsSummary(summary);
      setCheckinsPreview(null);
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

  const previewCheckinsMutation = useMutation({
    mutationFn: ({ file, autoCreate, mapping }: { file: File; autoCreate: boolean; mapping: ColumnMappingState }) =>
      importExportService.previewCheckins(file, autoCreate, mapping),
    onSuccess: (preview) => {
      setCheckinsPreview(preview);
      setCheckinsMapping(preview.suggested_mapping);
      setCheckinsSummary(null);
      toast.success("Preview de check-ins gerado. Revise o impacto antes de confirmar.");
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });

  const importAssessmentsMutation = useMutation({
    mutationFn: ({ file, mapping }: { file: File; mapping: ColumnMappingState }) =>
      importExportService.importAssessments(file, mapping),
    onSuccess: (summary) => {
      setAssessmentsSummary(summary);
      setAssessmentsPreview(null);
      refreshImportedDataViews();
      toast.success("Historico de avaliacoes importado.");
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });

  const previewAssessmentsMutation = useMutation({
    mutationFn: ({ file, mapping }: { file: File; mapping: ColumnMappingState }) =>
      importExportService.previewAssessments(file, mapping),
    onSuccess: (preview) => {
      setAssessmentsPreview(preview);
      setAssessmentsMapping(preview.suggested_mapping);
      setAssessmentsSummary(null);
      toast.success("Preview do historico de avaliacoes gerado.");
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

  const canImportMembers =
    !!membersFile &&
    !!membersPreview &&
    membersPreview.valid_rows > 0 &&
    membersPreview.mapping_ready &&
    !membersMappingDirty &&
    !importMembersMutation.isPending;
  const canImportCheckins =
    !!checkinsFile &&
    !!checkinsPreview &&
    checkinsPreview.valid_rows > 0 &&
    checkinsPreview.mapping_ready &&
    !checkinsMappingDirty &&
    !importCheckinsMutation.isPending;
  const canImportAssessments =
    !!assessmentsFile &&
    !!assessmentsPreview &&
    assessmentsPreview.valid_rows > 0 &&
    assessmentsPreview.mapping_ready &&
    !assessmentsMappingDirty &&
    !importAssessmentsMutation.isPending;

  return (
    <section className="space-y-6">
      <header>
        <h2 className="font-heading text-3xl font-bold text-lovable-ink">Importacoes e Exportacoes (CSV/XLSX)</h2>
        <p className="text-sm text-lovable-ink-muted">
          Envie planilhas de alunos/catraca em CSV ou XLSX, revise o mapeamento das colunas e exporte dados do sistema em CSV.
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
            onChange={(event) => {
              setMembersFile(event.target.files?.[0] ?? null);
              setMembersPreview(null);
              setMembersSummary(null);
              setMembersMapping({});
            }}
            className="mt-3 w-full rounded-lg border border-lovable-border bg-lovable-surface px-3 py-2 text-sm text-lovable-ink"
          />
          <div className="mt-3 flex flex-wrap gap-2">
            <button
              type="button"
              disabled={!membersFile || previewMembersMutation.isPending}
              onClick={() => membersFile && previewMembersMutation.mutate({ file: membersFile, mapping: membersMapping })}
              className="inline-flex items-center gap-1 rounded-lg bg-brand-500 px-3 py-2 text-xs font-semibold uppercase tracking-wider text-white hover:bg-brand-700 disabled:opacity-60"
            >
              <FileUp size={14} />
              {getValidateButtonLabel(membersPreview, previewMembersMutation.isPending)}
            </button>
            <button
              type="button"
              disabled={!canImportMembers}
              onClick={() => membersFile && importMembersMutation.mutate({ file: membersFile, mapping: membersMapping })}
              className="inline-flex items-center gap-1 rounded-lg border border-emerald-400 bg-emerald-50 px-3 py-2 text-xs font-semibold uppercase tracking-wider text-emerald-900 hover:bg-emerald-100 disabled:opacity-60"
            >
              <FileUp size={14} />
              {importMembersMutation.isPending ? "Confirmando..." : "Confirmar importacao"}
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
          <ColumnMappingEditor preview={membersPreview} mapping={membersMapping} onChange={setMembersMapping} isDirty={membersMappingDirty} />
          <PreviewResult preview={membersPreview} mappingDirty={membersMappingDirty} />
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
            onChange={(event) => {
              setCheckinsFile(event.target.files?.[0] ?? null);
              setCheckinsPreview(null);
              setCheckinsSummary(null);
              setCheckinsMapping({});
            }}
            className="mt-3 w-full rounded-lg border border-lovable-border bg-lovable-surface px-3 py-2 text-sm text-lovable-ink"
          />
          <label className="mt-3 flex items-start gap-2 text-sm text-lovable-ink">
            <input
              type="checkbox"
              checked={autoCreateMissingMembers}
              onChange={(event) => {
                setAutoCreateMissingMembers(event.target.checked);
                setCheckinsPreview(null);
              }}
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
              disabled={!checkinsFile || previewCheckinsMutation.isPending}
              onClick={() =>
                checkinsFile &&
                previewCheckinsMutation.mutate({
                  file: checkinsFile,
                  autoCreate: autoCreateMissingMembers,
                  mapping: checkinsMapping,
                })
              }
              className="inline-flex items-center gap-1 rounded-lg bg-brand-500 px-3 py-2 text-xs font-semibold uppercase tracking-wider text-white hover:bg-brand-700 disabled:opacity-60"
            >
              <FileUp size={14} />
              {getValidateButtonLabel(checkinsPreview, previewCheckinsMutation.isPending)}
            </button>
            <button
              type="button"
              disabled={!canImportCheckins}
              onClick={() =>
                checkinsFile &&
                importCheckinsMutation.mutate({
                  file: checkinsFile,
                  autoCreate: autoCreateMissingMembers,
                  mapping: checkinsMapping,
                })
              }
              className="inline-flex items-center gap-1 rounded-lg border border-emerald-400 bg-emerald-50 px-3 py-2 text-xs font-semibold uppercase tracking-wider text-emerald-900 hover:bg-emerald-100 disabled:opacity-60"
            >
              <FileUp size={14} />
              {importCheckinsMutation.isPending ? "Confirmando..." : "Confirmar importacao"}
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
          <ColumnMappingEditor preview={checkinsPreview} mapping={checkinsMapping} onChange={setCheckinsMapping} isDirty={checkinsMappingDirty} />
          <PreviewResult preview={checkinsPreview} allowMissingExport mappingDirty={checkinsMappingDirty} />
          <ImportResult summary={checkinsSummary} allowMissingExport />
        </article>
      </section>

      <section className="rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-lovable-ink-muted">Importar historico de avaliacoes</h3>
        <p className="mt-1 text-xs text-lovable-ink-muted">
          Use CSV/XLSX estruturado com identificador do aluno e assessment_date. Campos opcionais: peso, gordura, medidas e proxima avaliacao.
        </p>
        <input
          type="file"
          accept=".csv,.xlsx,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
          onChange={(event) => {
            setAssessmentsFile(event.target.files?.[0] ?? null);
            setAssessmentsPreview(null);
            setAssessmentsSummary(null);
            setAssessmentsMapping({});
          }}
          className="mt-3 w-full rounded-lg border border-lovable-border bg-lovable-surface px-3 py-2 text-sm text-lovable-ink"
        />
        <div className="mt-3 flex flex-wrap gap-2">
          <button
            type="button"
            disabled={!assessmentsFile || previewAssessmentsMutation.isPending}
            onClick={() =>
              assessmentsFile && previewAssessmentsMutation.mutate({ file: assessmentsFile, mapping: assessmentsMapping })
            }
            className="inline-flex items-center gap-1 rounded-lg bg-brand-500 px-3 py-2 text-xs font-semibold uppercase tracking-wider text-white hover:bg-brand-700 disabled:opacity-60"
          >
            <FileUp size={14} />
            {getValidateButtonLabel(assessmentsPreview, previewAssessmentsMutation.isPending)}
          </button>
          <button
            type="button"
            disabled={!canImportAssessments}
            onClick={() =>
              assessmentsFile && importAssessmentsMutation.mutate({ file: assessmentsFile, mapping: assessmentsMapping })
            }
            className="inline-flex items-center gap-1 rounded-lg border border-emerald-400 bg-emerald-50 px-3 py-2 text-xs font-semibold uppercase tracking-wider text-emerald-900 hover:bg-emerald-100 disabled:opacity-60"
          >
            <FileUp size={14} />
            {importAssessmentsMutation.isPending ? "Confirmando..." : "Confirmar importacao"}
          </button>
        </div>
        <ColumnMappingEditor preview={assessmentsPreview} mapping={assessmentsMapping} onChange={setAssessmentsMapping} isDirty={assessmentsMappingDirty} />
        <PreviewResult preview={assessmentsPreview} mappingDirty={assessmentsMappingDirty} />
        <ImportResult summary={assessmentsSummary} />
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

      <section className="rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
        <div className="flex items-start gap-3">
          <Link2 className="mt-0.5 text-brand-500" size={18} />
          <div>
            <h3 className="text-sm font-semibold uppercase tracking-wider text-lovable-ink-muted">Fluxo recomendado</h3>
            <p className="mt-1 text-xs text-lovable-ink-muted">
              Valide o arquivo, ajuste o mapeamento quando necessario, revalide e so depois confirme a importacao final.
            </p>
          </div>
        </div>
      </section>
    </section>
  );
}
