const DECIMAL_NUMBER_RE = /^-?\d+(\.\d+)?$/;
const SUPPORTED_UNIT_RE = /(%|kg|kcal|cm|mm)$/i;

export function parseLocalizedNumber(value: unknown): number | null {
  if (value == null || value === "") return null;
  if (typeof value === "number") return Number.isFinite(value) ? value : null;
  if (typeof value !== "string") return null;

  const compact = value.trim().replace(/\s+/g, "");
  if (!compact) return null;

  const withoutUnit = compact.replace(SUPPORTED_UNIT_RE, "");
  if (!withoutUnit) return null;
  if (withoutUnit.includes(",") && withoutUnit.includes(".")) return null;

  const normalized = withoutUnit.replace(",", ".");
  if (!DECIMAL_NUMBER_RE.test(normalized)) return null;

  const parsed = Number(normalized);
  return Number.isFinite(parsed) ? parsed : null;
}

export function normalizeLocalizedNumberInput(value: unknown): number | null | unknown {
  if (value == null || value === "") return null;
  if (typeof value === "number") return Number.isFinite(value) ? value : value;
  if (typeof value !== "string") return value;

  const parsed = parseLocalizedNumber(value);
  return parsed == null ? value : parsed;
}
