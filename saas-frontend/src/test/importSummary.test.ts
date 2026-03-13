import { describe, expect, it } from "vitest";

import type { ImportSummary } from "../types";
import {
  getIgnoredRowsHint,
  getImportSummaryNotice,
  getVisibleImportErrors,
  isDuplicateOnlyImport,
} from "../pages/imports/importSummary";

function makeSummary(overrides: Partial<ImportSummary> = {}): ImportSummary {
  return {
    imported: 0,
    skipped_duplicates: 0,
    ignored_rows: 0,
    provisional_members_created: 0,
    provisional_members: [],
    missing_members: [],
    errors: [],
    ...overrides,
  };
}

describe("import summary helpers", () => {
  it("detects when a file only contains existing check-ins", () => {
    const summary = makeSummary({
      skipped_duplicates: 4446,
    });

    expect(isDuplicateOnlyImport(summary)).toBe(true);
    expect(getImportSummaryNotice(summary)).toEqual({
      tone: "info",
      title: "Nenhum novo check-in foi adicionado",
      description:
        "Os 4.446 registros validos deste arquivo ja estavam salvos no sistema. Os dados continuam disponiveis em Membros e na exportacao de catraca.",
    });
  });

  it("keeps missing-member errors out of the technical error list", () => {
    const summary = makeSummary({
      errors: [
        {
          row_number: 10,
          reason: "Membro nao encontrado na base de alunos importada (use member_id, email, matricula, cpf ou nome)",
          payload: {},
        },
        {
          row_number: 11,
          reason: "Formato de data invalido",
          payload: {},
        },
      ],
    });

    expect(getVisibleImportErrors(summary)).toEqual([
      {
        row_number: 11,
        reason: "Formato de data invalido",
        payload: {},
      },
    ]);
  });

  it("explains ignored rows when present", () => {
    const summary = makeSummary({
      ignored_rows: 432,
    });

    expect(getIgnoredRowsHint(summary)).toBe(
      "Algumas linhas foram ignoradas por nao representarem um check-in valido de membro, como registros manuais ou linhas de totalizacao.",
    );
  });
});
