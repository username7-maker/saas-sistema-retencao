import type { CalculationOrigin } from "../types";

export const CALCULATION_ORIGIN_LABELS: Record<CalculationOrigin, string> = {
  reported: "Medido pelo aparelho",
  schofield_hw_1985: "TMB por Schofield",
  mifflin_st_jeor_1990: "TMB por Mifflin",
  lee_2000: "Estimado por Lee",
  poortmans_2005: "Estimado por Poortmans",
  legacy_unknown: "Origem histórica não identificada",
  unavailable: "Indisponível",
};

const CALCULATION_ORIGINS = new Set<CalculationOrigin>(
  Object.keys(CALCULATION_ORIGIN_LABELS) as CalculationOrigin[],
);

export function asCalculationOrigin(value: unknown): CalculationOrigin | null {
  return typeof value === "string" && CALCULATION_ORIGINS.has(value as CalculationOrigin)
    ? (value as CalculationOrigin)
    : null;
}

export function calculationOriginLabel(value: unknown): string {
  const origin = asCalculationOrigin(value);
  return origin ? CALCULATION_ORIGIN_LABELS[origin] : "Origem não informada";
}

export function stripReadOnlyCalculationOrigins<T extends object>(payload: T): T {
  const sanitized = { ...payload } as T & Record<string, unknown>;
  delete sanitized.basal_metabolic_rate_origin;
  delete sanitized.muscle_mass_origin;
  return sanitized;
}
