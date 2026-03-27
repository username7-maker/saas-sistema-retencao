export interface ChartSeriesState {
  hasPoints: boolean;
  finiteCount: number;
  hasMeaningfulValues: boolean;
  isAllZero: boolean;
  isFlat: boolean;
}

function toNumericValue(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string" && value.trim() !== "") {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) return parsed;
  }
  return null;
}

export function getChartSeriesState<T extends object>(
  data: T[] | null | undefined,
  keys: Array<keyof T & string>,
): ChartSeriesState {
  if (!data || data.length === 0) {
    return {
      hasPoints: false,
      finiteCount: 0,
      hasMeaningfulValues: false,
      isAllZero: false,
      isFlat: false,
    };
  }

  const values = data.flatMap((point) => {
    const rawPoint = point as Record<string, unknown>;
    return keys
      .map((key) => toNumericValue(rawPoint[key]))
      .filter((value): value is number => value !== null);
  });

  if (values.length === 0) {
    return {
      hasPoints: true,
      finiteCount: 0,
      hasMeaningfulValues: false,
      isAllZero: false,
      isFlat: false,
    };
  }

  const nonZeroValues = values.filter((value) => Math.abs(value) > Number.EPSILON);
  const firstValue = values[0];
  const isFlat = values.every((value) => Math.abs(value - firstValue) <= Number.EPSILON);

  return {
    hasPoints: true,
    finiteCount: values.length,
    hasMeaningfulValues: nonZeroValues.length > 0,
    isAllZero: nonZeroValues.length === 0,
    isFlat,
  };
}
