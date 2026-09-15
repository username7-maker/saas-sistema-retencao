import type { ImportErrorEntry, ImportSummary } from "../../types";

export interface ImportSummaryNotice {
  tone: "info" | "success";
  title: string;
  description: string;
}

function pendingCellValue(value: unknown): string {
  if (value === null || value === undefined) return "";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return JSON.stringify(value);
}

export function buildPendingImportCsvRows(errors: ImportErrorEntry[]): string[][] {
  const payloadColumns = Array.from(new Set(errors.flatMap((error) => Object.keys(error.payload)))).sort();
  return [
    ["linha", "motivo", ...payloadColumns],
    ...errors.map((error) => [
      String(error.row_number),
      error.reason,
      ...payloadColumns.map((column) => pendingCellValue(error.payload[column])),
    ]),
  ];
}

export function getVisibleImportErrors(summary: ImportSummary): ImportErrorEntry[] {
  return summary.errors;
}

export function isDuplicateOnlyImport(summary: ImportSummary): boolean {
  const visibleErrors = getVisibleImportErrors(summary);
  return (
    summary.imported === 0 &&
    summary.skipped_duplicates > 0 &&
    summary.missing_members.length === 0 &&
    visibleErrors.length === 0
  );
}

export function getIgnoredRowsHint(summary: ImportSummary): string | null {
  if (summary.ignored_rows === 0) {
    return null;
  }
  return "Algumas linhas foram ignoradas por nao representarem um check-in valido de membro, como registros manuais ou linhas de totalizacao.";
}

export function getImportSummaryNotice(summary: ImportSummary): ImportSummaryNotice | null {
  if (isDuplicateOnlyImport(summary)) {
    return {
      tone: "info",
      title: "Nenhum novo check-in foi adicionado",
      description: `Os ${summary.skipped_duplicates.toLocaleString("pt-BR")} registros validos deste arquivo ja estavam salvos no sistema. Os dados continuam disponiveis em Membros e na exportacao de catraca.`,
    };
  }

  if (summary.imported > 0 && summary.skipped_duplicates > 0) {
    return {
      tone: "success",
      title: "Arquivo processado com registros novos e existentes",
      description: `Foram salvos ${summary.imported.toLocaleString("pt-BR")} novos registros, e ${summary.skipped_duplicates.toLocaleString("pt-BR")} check-ins repetidos foram preservados sem duplicacao.`,
    };
  }

  return null;
}
