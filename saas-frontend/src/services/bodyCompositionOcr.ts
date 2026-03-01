export interface BodyCompositionOcrValues {
  evaluation_date?: string;
  weight_kg?: number;
  body_fat_percent?: number;
  lean_mass_kg?: number;
  muscle_mass_kg?: number;
  body_water_percent?: number;
  visceral_fat_level?: number;
  bmi?: number;
  basal_metabolic_rate_kcal?: number;
}

export interface BodyCompositionOcrResult {
  values: BodyCompositionOcrValues;
  warnings: string[];
  confidence: number;
  raw_text: string;
}

function parseNumber(raw: string): number | undefined {
  const normalized = raw.replace(",", ".").trim();
  const parsed = Number(normalized);
  if (Number.isNaN(parsed)) return undefined;
  return parsed;
}

function extractByPatterns(text: string, patterns: RegExp[]): number | undefined {
  for (const pattern of patterns) {
    const match = pattern.exec(text);
    if (!match?.[1]) continue;
    const parsed = parseNumber(match[1]);
    if (parsed !== undefined) return parsed;
  }
  return undefined;
}

function extractEvaluationDate(text: string): string | undefined {
  const br = /(\d{2})[\/\-](\d{2})[\/\-](\d{4})/.exec(text);
  if (br) {
    const day = br[1];
    const month = br[2];
    const year = br[3];
    return `${year}-${month}-${day}`;
  }

  const iso = /(\d{4})[\/\-](\d{2})[\/\-](\d{2})/.exec(text);
  if (iso) {
    return `${iso[1]}-${iso[2]}-${iso[3]}`;
  }

  return undefined;
}

export function extractBodyCompositionFromText(rawText: string): BodyCompositionOcrResult {
  const text = rawText
    .replace(/\r/g, "\n")
    .replace(/[^\S\n]+/g, " ")
    .trim();

  const values: BodyCompositionOcrValues = {
    evaluation_date: extractEvaluationDate(text),
    weight_kg: extractByPatterns(text, [
      /(?:peso|weight)\s*[:\-]?\s*(\d{2,3}(?:[.,]\d+)?)/i,
    ]),
    body_fat_percent: extractByPatterns(text, [
      /(?:gordura(?: corporal)?|body fat|bf)\s*[:\-]?\s*(\d{1,2}(?:[.,]\d+)?)/i,
      /(?:% gordura|%fat)\s*[:\-]?\s*(\d{1,2}(?:[.,]\d+)?)/i,
    ]),
    lean_mass_kg: extractByPatterns(text, [
      /(?:massa magra|lean mass)\s*[:\-]?\s*(\d{2,3}(?:[.,]\d+)?)/i,
    ]),
    muscle_mass_kg: extractByPatterns(text, [
      /(?:massa muscular|muscle mass)\s*[:\-]?\s*(\d{2,3}(?:[.,]\d+)?)/i,
    ]),
    body_water_percent: extractByPatterns(text, [
      /(?:agua corporal|body water|% agua)\s*[:\-]?\s*(\d{1,2}(?:[.,]\d+)?)/i,
    ]),
    visceral_fat_level: extractByPatterns(text, [
      /(?:gordura visceral|visceral fat)\s*[:\-]?\s*(\d{1,2}(?:[.,]\d+)?)/i,
    ]),
    bmi: extractByPatterns(text, [
      /(?:imc|bmi)\s*[:\-]?\s*(\d{1,2}(?:[.,]\d+)?)/i,
    ]),
    basal_metabolic_rate_kcal: extractByPatterns(text, [
      /(?:tmb|bmr|metabolismo basal)\s*[:\-]?\s*(\d{3,4}(?:[.,]\d+)?)/i,
    ]),
  };

  const extractedCount = Object.values(values).filter((value) => value !== undefined).length;
  const totalFields = 9;
  const confidence = Math.min(1, extractedCount / totalFields);

  const warnings: string[] = [];
  if (!values.evaluation_date) {
    warnings.push("Nao foi possivel identificar a data da avaliacao. Usando data atual.");
  }
  if (extractedCount <= 2) {
    warnings.push("Poucos campos foram reconhecidos. Revise os dados manualmente.");
  }

  return {
    values,
    warnings,
    confidence,
    raw_text: rawText,
  };
}
