import { LineSeriesChart } from "../charts/LineSeriesChart";
import type { EvolutionData } from "../../services/assessmentService";

interface EvolutionChartsProps {
  evolution: EvolutionData;
}

interface ChartPoint {
  label: string;
  value: number | null;
}

function buildSeries(labels: string[], values: Array<number | null>): ChartPoint[] {
  return labels.map((label, index) => ({
    label,
    value: values[index] ?? null,
  }));
}

export function EvolutionCharts({ evolution }: EvolutionChartsProps) {
  const weightSeries = buildSeries(evolution.labels, evolution.weight);
  const bodyFatSeries = buildSeries(evolution.labels, evolution.body_fat);
  const bmiSeries = buildSeries(evolution.labels, evolution.bmi);
  const strengthSeries = buildSeries(evolution.labels, evolution.strength);
  const flexibilitySeries = buildSeries(evolution.labels, evolution.flexibility);
  const cardioSeries = buildSeries(evolution.labels, evolution.cardio);

  return (
    <section className="space-y-4">
      <div className="grid gap-4 lg:grid-cols-2">
        <LineSeriesChart data={weightSeries} xKey="label" yKey="value" stroke="#2563eb" />
        <LineSeriesChart data={bodyFatSeries} xKey="label" yKey="value" stroke="#dc2626" />
        <LineSeriesChart data={bmiSeries} xKey="label" yKey="value" stroke="#9333ea" />
        <LineSeriesChart data={strengthSeries} xKey="label" yKey="value" stroke="#059669" />
        <LineSeriesChart data={flexibilitySeries} xKey="label" yKey="value" stroke="#d97706" />
        <LineSeriesChart data={cardioSeries} xKey="label" yKey="value" stroke="#0891b2" />
      </div>
      <div className="rounded-2xl border border-slate-200 bg-white p-4 text-xs text-slate-500 shadow-panel">
        <p>Peso delta: {evolution.deltas.weight ?? "-"} | BF delta: {evolution.deltas.body_fat ?? "-"} | BMI delta: {evolution.deltas.bmi ?? "-"}</p>
        <p className="mt-1">
          Forca delta: {evolution.deltas.strength ?? "-"} | Flex delta: {evolution.deltas.flexibility ?? "-"} | Cardio delta: {evolution.deltas.cardio ?? "-"}
        </p>
      </div>
    </section>
  );
}
