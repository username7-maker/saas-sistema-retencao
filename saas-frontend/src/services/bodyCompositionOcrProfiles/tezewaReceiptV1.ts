import type {
  BodyCompositionOcrResult,
  BodyCompositionOcrValues,
  BodyCompositionRangeValue,
  BodyCompositionOcrWarning,
} from "../bodyCompositionOcr";

type SectionName = "body_composition" | "body_parameters" | "comprehensive_evaluation" | "general";

interface FieldSpec {
  key: keyof BodyCompositionOcrValues;
  aliases: string[];
  sections: SectionName[];
  disallow?: string[];
}

interface SectionLine {
  text: string;
  normalized: string;
  section: SectionName;
}

interface FieldCandidate extends SectionLine {
  alias: string;
  index: number;
}

interface ParsedMeasurement {
  parsed: { value?: number; range: BodyCompositionRangeValue };
  index: number;
}

const SECTION_ALIASES: Record<SectionName, string[]> = {
  general: [],
  body_composition: ["body composition"],
  body_parameters: ["body parameters"],
  comprehensive_evaluation: ["comprehensive evaluation"],
};

const FIELD_SPECS: FieldSpec[] = [
  { key: "body_fat_percent", aliases: ["body fat ratio", "body fat %", "% body fat", "fat ratio"], sections: ["body_composition", "body_parameters", "general"], disallow: ["kg"] },
  { key: "body_fat_kg", aliases: ["body fat kg", "body fat (kg)", "body fat", "fat mass"], sections: ["body_composition", "general"], disallow: ["ratio", "%"] },
  { key: "weight_kg", aliases: ["weight"], sections: ["body_composition", "general"], disallow: ["target", "control", "fat free", "fat-free"] },
  { key: "waist_hip_ratio", aliases: ["waist hip ratio", "waist hip", "waist-hip ratio", "waist hi"], sections: ["body_composition", "body_parameters", "general"] },
  { key: "fat_free_mass_kg", aliases: ["fat free mass", "fat free weight", "fat free", "lean mass", "lean body mass"], sections: ["body_composition", "general"] },
  { key: "inorganic_salt_kg", aliases: ["inorganic salt", "norganic salt", "inorg salt", "inorganic sait"], sections: ["body_composition", "general"] },
  { key: "muscle_mass_kg", aliases: ["muscle mass"], sections: ["body_composition", "general"] },
  { key: "protein_kg", aliases: ["protein"], sections: ["body_composition", "general"] },
  { key: "body_water_kg", aliases: ["body water", "body moisture", "total body water", "water content", "tbw"], sections: ["body_composition", "general"], disallow: ["%", "ratio"] },
  { key: "visceral_fat_level", aliases: ["visceral fat"], sections: ["body_parameters", "general"] },
  { key: "basal_metabolic_rate_kcal", aliases: ["basal metabolic rate", "basal metabolism", "basal metabolic", "bmr"], sections: ["body_parameters", "general"] },
  { key: "bmi", aliases: ["body mass index", "bmi"], sections: ["body_parameters", "general"] },
  { key: "skeletal_muscle_percent", aliases: ["skeletal muscle"], sections: ["body_parameters", "general"] },
  { key: "target_weight_kg", aliases: ["target weight"], sections: ["comprehensive_evaluation", "general"] },
  { key: "weight_control_kg", aliases: ["weight control"], sections: ["comprehensive_evaluation", "general"] },
  { key: "muscle_control_kg", aliases: ["muscle control"], sections: ["comprehensive_evaluation", "general"] },
  { key: "fat_control_kg", aliases: ["fat control"], sections: ["comprehensive_evaluation", "general"] },
  { key: "total_energy_kcal", aliases: ["total energy", "total energy kcal", "energy consumption"], sections: ["comprehensive_evaluation", "general"] },
  { key: "physical_age", aliases: ["physical age"], sections: ["comprehensive_evaluation", "general"] },
  { key: "health_score", aliases: ["health score"], sections: ["comprehensive_evaluation", "general"] },
];

const KNOWN_PHRASES = [
  ...Object.values(SECTION_ALIASES).flat(),
  ...FIELD_SPECS.flatMap((field) => field.aliases),
];

const PLAUSIBLE_RANGES: Partial<Record<keyof BodyCompositionOcrValues, { min: number; max: number }>> = {
  weight_kg: { min: 30, max: 300 },
  body_fat_kg: { min: 1, max: 80 },
  body_fat_percent: { min: 2, max: 75 },
  waist_hip_ratio: { min: 0.5, max: 1.5 },
  fat_free_mass_kg: { min: 20, max: 200 },
  inorganic_salt_kg: { min: 1, max: 10 },
  muscle_mass_kg: { min: 10, max: 100 },
  protein_kg: { min: 1, max: 40 },
  body_water_kg: { min: 10, max: 100 },
  visceral_fat_level: { min: 1, max: 30 },
  bmi: { min: 10, max: 80 },
  basal_metabolic_rate_kcal: { min: 500, max: 4000 },
  skeletal_muscle_percent: { min: 1, max: 100 },
  target_weight_kg: { min: 30, max: 300 },
  weight_control_kg: { min: -100, max: 100 },
  muscle_control_kg: { min: -100, max: 100 },
  fat_control_kg: { min: -100, max: 100 },
  total_energy_kcal: { min: 500, max: 7000 },
  physical_age: { min: 1, max: 120 },
  health_score: { min: 1, max: 100 },
};
export function parseTezewaReceiptV1(rawText: string): BodyCompositionOcrResult {
  const normalizedText = normalizeOcrText(rawText);
  const mergedLines = mergeBrokenLines(normalizedText.split("\n").filter(Boolean));
  const sectionLines = assignSections(mergedLines);
  const warnings: BodyCompositionOcrWarning[] = [];
  const values: BodyCompositionOcrValues = {};
  const ranges: Record<string, BodyCompositionRangeValue> = {};
  const usedLineIndexes = new Map<string, number>();

  const evaluationDate = extractEvaluationDate(normalizedText);
  if (evaluationDate) {
    values.evaluation_date = evaluationDate;
  }

  for (const spec of FIELD_SPECS) {
    const candidate = findFieldCandidate(sectionLines, spec);
    if (!candidate) {
      continue;
    }

    const measurement = extractFieldMeasurement(sectionLines, spec, candidate);
    const parsed = measurement.parsed;
    if (parsed.range.min !== null || parsed.range.max !== null) {
      ranges[spec.key] = parsed.range;
      usedLineIndexes.set(`range:${String(spec.key)}`, measurement.index);
    }
    if (parsed.value == null) {
      warnings.push({
        field: String(spec.key),
        message: `Nao foi possivel isolar o valor principal de ${spec.aliases[0]}.`,
        severity: "critical",
      });
      continue;
    }

    if (plausibilityScore(spec.key, parsed.value) === 0) {
      warnings.push({
        field: String(spec.key),
        message: `${spec.aliases[0]} gerou valor fora dos limites plausiveis e foi descartado.`,
        severity: "critical",
      });
      continue;
    }

    (values as Record<string, number | string | undefined>)[String(spec.key)] = parsed.value;
    usedLineIndexes.set(String(spec.key), measurement.index);

    if (spec.key === "body_fat_kg" && candidate.normalized.includes("ratio")) {
      warnings.push({
        field: String(spec.key),
        message: "Linha de gordura corporal em kg parece ambigua com body fat ratio. Revisar manualmente.",
        severity: "critical",
      });
    }
    if (spec.key === "body_fat_percent" && !candidate.normalized.includes("ratio") && !candidate.normalized.includes("%")) {
      warnings.push({
        field: String(spec.key),
        message: "Percentual de gordura foi identificado sem marcador claro de ratio/%. Revisar manualmente.",
        severity: "critical",
      });
    }
  }

  if (!hasExpectedTezewaStructure(normalizedText)) {
    warnings.push({
      field: null,
      message: "Layout diferente do recibo de bioimpedância detectado. A leitura assistida por IA é obrigatória para esta imagem.",
      severity: "critical",
    });
  }

  const fatKgLine = usedLineIndexes.get("body_fat_kg");
  const fatPercentLine = usedLineIndexes.get("body_fat_percent");
  if (fatKgLine !== undefined && fatPercentLine !== undefined && fatKgLine === fatPercentLine) {
    warnings.push({
      field: "body_fat_percent",
      message: "Mesma linha foi usada para body fat kg e body fat ratio. Revisao manual obrigatoria.",
      severity: "critical",
    });
  }

  if (values.body_fat_kg == null) {
    warnings.push({
      field: "body_fat_kg",
      message: "Body fat (kg) nao foi identificado com seguranca.",
      severity: "critical",
    });
  }
  if (values.body_fat_percent == null) {
    warnings.push({
      field: "body_fat_percent",
      message: "Body fat ratio (%) nao foi identificado com seguranca.",
      severity: "critical",
    });
  }
  if (!values.evaluation_date) {
    warnings.push({
      field: "evaluation_date",
      message: "Data da avaliacao nao identificada. Revisar antes de salvar.",
      severity: "warning",
    });
  }

  const extractedCount = Object.values(values).filter((value) => value !== undefined).length;
  const baseConfidence = Math.min(0.99, extractedCount / (FIELD_SPECS.length + 1));
  const criticalWarnings = warnings.filter((warning) => warning.severity === "critical").length;
  const confidence = Math.max(0.2, Number((baseConfidence - criticalWarnings * 0.08).toFixed(2)));
  const needsReview = criticalWarnings > 0 || confidence < 0.75;

  return {
    device_profile: "tezewa_receipt_v1",
    device_model: detectDeviceModel(normalizedText),
    values,
    ranges,
    warnings,
    confidence,
    raw_text: normalizedText,
    needs_review: needsReview,
  };
}

function normalizeOcrText(rawText: string): string {
  return rawText
    .replace(/\r/g, "\n")
    .replace(/[|]/g, " ")
    .replace(/[â€“â€”~˜]/g, "-")
    .replace(/(\d),(\d)/g, "$1.$2")
    .replace(/[^\S\n]+/g, " ")
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => Boolean(line) && !/^[=\-_.]{3,}$/.test(line) && !isNoiseLine(line))
    .join("\n");
}

function mergeBrokenLines(lines: string[]): string[] {
  const merged: string[] = [];
  let index = 0;

  while (index < lines.length) {
    let current = lines[index];
    let nextIndex = index + 1;

    while (nextIndex < lines.length) {
      const separator = getMergeSeparator(current, lines[nextIndex]);
      if (separator == null) break;
      current = `${current}${separator}${lines[nextIndex]}`.replace(/\s+/g, " ").trim();
      nextIndex += 1;
    }

    merged.push(current);
    index = nextIndex;
  }

  return merged;
}

function getMergeSeparator(current: string, next: string): "" | " " | null {
  const currentNormalized = normalizeLabel(current);
  const combinedNormalized = normalizeLabel(`${current} ${next}`);
  const currentCompact = currentNormalized.replace(/ /g, "");
  const combinedCompact = normalizeLabel(`${current}${next}`).replace(/ /g, "");

  if (!currentNormalized || isNoiseLine(current) || isNoiseLine(next)) return null;
  if (currentNormalized.includes("body composition") || currentNormalized.includes("body parameters") || currentNormalized.includes("comprehensive evaluation")) {
    return null;
  }

  for (const phrase of KNOWN_PHRASES) {
    const normalizedPhrase = normalizeLabel(phrase);
    const phraseCompact = normalizedPhrase.replace(/ /g, "");
    if (normalizedPhrase.startsWith(currentNormalized) && combinedNormalized.startsWith(normalizedPhrase)) {
      return " ";
    }
    if (!/\d/.test(currentNormalized) && currentCompact.length <= 12 && phraseCompact.startsWith(currentCompact) && combinedCompact.startsWith(phraseCompact)) {
      return "";
    }
  }

  return null;
}

function assignSections(lines: string[]): SectionLine[] {
  let currentSection: SectionName = "general";
  return lines.map((line) => {
    const normalized = normalizeLabel(line);
    const matchedSection = (Object.entries(SECTION_ALIASES) as Array<[SectionName, string[]]>).find(([, aliases]) =>
      aliases.some((alias) => normalized.includes(normalizeLabel(alias))),
    )?.[0];
    if (matchedSection) {
      currentSection = matchedSection;
    }
    return {
      text: line,
      normalized,
      section: matchedSection ?? currentSection,
    };
  });
}

function findFieldCandidate(lines: SectionLine[], spec: FieldSpec): FieldCandidate | null {
  const candidates = lines.map((line, index) => ({ ...line, index }));

  for (const line of candidates) {
    if (!spec.sections.includes(line.section) && line.section !== "general") continue;
    if (isNoiseLine(line.text)) continue;
    for (const alias of spec.aliases) {
      const normalizedAlias = normalizeLabel(alias);
      if (!line.normalized.includes(normalizedAlias)) continue;
      if (spec.disallow?.some((token) => line.normalized.includes(normalizeLabel(token)))) continue;
      return { ...line, alias, index: line.index };
    }
  }

  return null;
}

function parseValueAndRange(text: string, alias?: string): { value?: number; range: BodyCompositionRangeValue } {
  const normalizedText = text.replace(/,/g, ".");
  const scopedText = alias ? sliceAfterAlias(normalizedText, alias) : normalizedText;

  const collapsedRangeMatch = scopedText.match(/(-?\d{1,4}\.\d{1,2})(\d{1,4}\.\d{1,2})\s*(?:-|~|°|–|—)\s*(\d{1,4}\.\d{1,2})/);
  if (collapsedRangeMatch) {
    return {
      value: Number(collapsedRangeMatch[1]),
      range: { min: Number(collapsedRangeMatch[2]), max: Number(collapsedRangeMatch[3]) },
    };
  }

  const explicitRangeMatch = scopedText.match(/(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)\s*(?:-|~|°|–|—)\s*(-?\d+(?:\.\d+)?)/);
  if (explicitRangeMatch) {
    return {
      value: Number(explicitRangeMatch[1]),
      range: { min: Number(explicitRangeMatch[2]), max: Number(explicitRangeMatch[3]) },
    };
  }

  const allNumbers = scopedText.match(/-?\d+(?:\.\d+)?/g) ?? [];
  const rangeMatch = scopedText.match(/(-?\d+(?:\.\d+)?)\s*(?:-|~|°|–|—)\s*(-?\d+(?:\.\d+)?)/);
  const range: BodyCompositionRangeValue = { min: null, max: null };
  if (rangeMatch) {
    range.min = Number(rangeMatch[1]);
    range.max = Number(rangeMatch[2]);
    const outsideRange = `${scopedText.slice(0, rangeMatch.index)} ${scopedText.slice((rangeMatch.index ?? 0) + rangeMatch[0].length)}`;
    if (!/-?\d+(?:\.\d+)?/.test(outsideRange)) {
      return { range };
    }
  }
  if (allNumbers.length === 0) {
    return { range };
  }
  if (!rangeMatch && allNumbers.length >= 3 && allNumbers.length <= 4) {
    const [value, min, max] = allNumbers.slice(0, 3).map(Number);
    if (Number.isFinite(value) && Number.isFinite(min) && Number.isFinite(max) && min <= max) {
      return {
        value,
        range: { min, max },
      };
    }
  }
  return {
    value: Number(allNumbers[0]),
    range,
  };
}

function extractFieldMeasurement(lines: SectionLine[], spec: FieldSpec, candidate: FieldCandidate): ParsedMeasurement {
  const base = { parsed: parseValueAndRange(candidate.text, candidate.alias), index: candidate.index };

  const candidateNumbers = sliceAfterAlias(candidate.text.replace(/,/g, "."), candidate.alias)
    .match(/-?\d+(?:\.\d+)?/g) ?? [];
  const plausibleRangePair = candidateNumbers.length === 2
    && candidateNumbers.every((value) => plausibilityScore(spec.key, Number(value)) > 0);
  const hasPrintedRange = base.parsed.range.min !== null || base.parsed.range.max !== null;
  if (plausibleRangePair && !hasPrintedRange) {
    base.parsed = { range: base.parsed.range };
  }
  if (base.parsed.value == null && (hasPrintedRange || plausibleRangePair)) {
    return base;
  }
  if (base.parsed.value != null) return base;

  // A wrapped label may be followed by one isolated Value token and then by
  // a printed range. Never search backwards or skip across another field.
  const next = lines[candidate.index + 1];
  const following = lines[candidate.index + 2];
  const isolatedNumber = next?.text.match(/^\(?(?:kg|%)?\)?\s*(-?\d+(?:[.,]\d+)?)\s*(?:kg|%)?$/i);
  const rangeOnlyLine = following?.section === candidate.section &&
    /^\s*-?\d+(?:[.,]\d+)?\s*[-~°º–—]\s*-?\d+(?:[.,]\d+)?\s*$/.test(following.text);
  const followingRange = rangeOnlyLine ? parseValueAndRange(following.text).range : null;
  const isSingleColumn = candidate.section === "comprehensive_evaluation";
  if (
    next?.section === candidate.section && isolatedNumber &&
    (isSingleColumn || (followingRange?.min != null && followingRange.max != null))
  ) {
    return {
      parsed: {
        value: Number(isolatedNumber[1].replace(",", ".")),
        range: followingRange ?? { min: null, max: null },
      },
      index: candidate.index + 1,
    };
  }
  return base;
}

function extractEvaluationDate(text: string): string | undefined {
  const br = /(\d{2})[\/-](\d{2})[\/-](\d{4})/.exec(text);
  if (br) {
    return `${br[3]}-${br[2]}-${br[1]}`;
  }

  const iso = /(\d{4})[\/-](\d{2})[\/-](\d{2})/.exec(text);
  if (iso) {
    return `${iso[1]}-${iso[2]}-${iso[3]}`;
  }
  return undefined;
}

function detectDeviceModel(text: string): string | undefined {
  const normalized = normalizeLabel(text);
  if (normalized.includes("tezewa")) {
    return "Tezewa";
  }
  if (normalized.includes("inbody")) {
    return "InBody";
  }
  return undefined;
}

function hasExpectedTezewaStructure(text: string): boolean {
  const normalized = normalizeLabel(text);
  const expectedSections = ["body composition", "body parameters", "comprehensive evaluation"];
  return expectedSections.filter((section) => normalized.includes(section)).length >= 2;
}

function sliceAfterAlias(text: string, alias: string): string {
  const tokens = alias.toLowerCase().match(/[a-z0-9%]+/g) ?? [];
  if (!tokens.length) return text;

  const aliasPattern = new RegExp(tokens.map((token) => escapeRegExp(token)).join("(?:\\W|_)*"), "i");
  const match = aliasPattern.exec(text);
  if (!match) return text;
  return text.slice(match.index + match[0].length).trim();
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function isNoiseLine(value: string): boolean {
  const normalized = normalizeLabel(value);
  return (
    normalized === "project" ||
    normalized === "value" ||
    normalized === "range" ||
    normalized === "project value" ||
    normalized === "project value range" ||
    normalized === "kg" ||
    normalized === "%" ||
    normalized === "consumption"
  );
}

function plausibilityScore(field: keyof BodyCompositionOcrValues, value: number): number {
  const range = PLAUSIBLE_RANGES[field];
  if (!range) return 0.5;
  if (value < range.min || value > range.max) return 0;
  return 1;
}

function normalizeLabel(value: string): string {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9% ]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}
