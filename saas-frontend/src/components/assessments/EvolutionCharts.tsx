import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { EvolutionData } from "../../services/assessmentService";

interface EvolutionChartsProps {
  evolution: EvolutionData;
}

interface FrequencyPoint {
  label: string;
  checkins: number;
}

interface CompositionPoint {
  label: string;
  lean_mass: number | null;
  body_fat: number | null;
}

interface LoadPoint {
  label: string;
  load: number | null;
}

function shortMonthLabel(value: string): string {
  const normalized = value.match(/^\d{4}-\d{2}$/) ? `${value}-01` : value;
  const date = new Date(normalized);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString("pt-BR", { month: "short" });
}

function hasAtLeastOneValue(values: Array<number | null>): boolean {
  return values.some((value) => value !== null && Number.isFinite(value));
}

export function EvolutionCharts({ evolution }: EvolutionChartsProps) {
  const labels = Array.isArray(evolution.labels) ? evolution.labels : [];
  const checkinsLabelsRaw =
    Array.isArray((evolution as Partial<EvolutionData>).checkins_labels) && evolution.checkins_labels.length > 0
      ? evolution.checkins_labels
      : labels.slice(-6).map((label) => label.slice(0, 7));
  const checkinsValuesRaw =
    Array.isArray((evolution as Partial<EvolutionData>).checkins_per_month) && evolution.checkins_per_month.length > 0
      ? evolution.checkins_per_month
      : new Array(checkinsLabelsRaw.length).fill(0);
  const leanMassRaw =
    Array.isArray((evolution as Partial<EvolutionData>).lean_mass) && evolution.lean_mass.length > 0
      ? evolution.lean_mass
      : labels.map(() => null);
  const bodyFatRaw = Array.isArray(evolution.body_fat) ? evolution.body_fat : labels.map(() => null);
  const mainLiftRaw =
    Array.isArray((evolution as Partial<EvolutionData>).main_lift_load) && evolution.main_lift_load.length > 0
      ? evolution.main_lift_load
      : labels.map(() => null);

  const frequencyData: FrequencyPoint[] = checkinsLabelsRaw.map((label, index) => ({
    label,
    checkins: checkinsValuesRaw[index] ?? 0,
  }));

  const compositionData: CompositionPoint[] = labels.map((label, index) => ({
    label,
    lean_mass: leanMassRaw[index] ?? null,
    body_fat: bodyFatRaw[index] ?? null,
  }));

  const loadData: LoadPoint[] = labels.map((label, index) => ({
    label,
    load: mainLiftRaw[index] ?? null,
  }));

  const hasCompositionData = hasAtLeastOneValue(leanMassRaw) || hasAtLeastOneValue(bodyFatRaw);
  const hasLoadData = hasAtLeastOneValue(mainLiftRaw);

  return (
    <section className="space-y-4">
      <div className="grid gap-4 xl:grid-cols-3">
        <article className="h-72 rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
          <h3 className="text-sm font-semibold uppercase tracking-wider text-lovable-ink-muted">Frequencia (6 meses)</h3>
          <p className="mt-1 text-xs text-lovable-ink-muted">Quantas vezes o aluno treinou por mes.</p>
          <div className="mt-3 h-[220px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={frequencyData}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--lovable-border))" />
                <XAxis dataKey="label" tickFormatter={shortMonthLabel} stroke="hsl(var(--lovable-ink-muted))" />
                <YAxis stroke="hsl(var(--lovable-ink-muted))" />
                <Tooltip
                  labelFormatter={(value) => shortMonthLabel(String(value))}
                  formatter={(value) => [`${value} check-ins`, "Frequencia"]}
                  contentStyle={{
                    background: "hsl(var(--lovable-surface))",
                    border: "1px solid hsl(var(--lovable-border))",
                    borderRadius: "0.75rem",
                  }}
                />
                <Bar dataKey="checkins" fill="hsl(var(--lovable-primary))" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </article>

        <article className="h-72 rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel xl:col-span-2">
          <h3 className="text-sm font-semibold uppercase tracking-wider text-lovable-ink-muted">Composicao corporal</h3>
          <p className="mt-1 text-xs text-lovable-ink-muted">Massa magra subindo e percentual de gordura descendo.</p>
          <div className="mt-3 h-[220px]">
            {hasCompositionData ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={compositionData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--lovable-border))" />
                  <XAxis dataKey="label" tickFormatter={shortMonthLabel} stroke="hsl(var(--lovable-ink-muted))" />
                  <YAxis stroke="hsl(var(--lovable-ink-muted))" />
                  <Tooltip
                    labelFormatter={(value) => shortMonthLabel(String(value))}
                    formatter={(value, key) => {
                      if (value === null || value === undefined) return ["-", String(key)];
                      return key === "lean_mass"
                        ? [`${Number(value).toFixed(1)} kg`, "Massa magra"]
                        : [`${Number(value).toFixed(1)}%`, "% gordura"];
                    }}
                    contentStyle={{
                      background: "hsl(var(--lovable-surface))",
                      border: "1px solid hsl(var(--lovable-border))",
                      borderRadius: "0.75rem",
                    }}
                  />
                  <Legend />
                  <Line
                    type="monotone"
                    dataKey="lean_mass"
                    name="Massa magra"
                    stroke="#22c55e"
                    strokeWidth={2.5}
                    connectNulls
                    dot={{ r: 3 }}
                  />
                  <Line
                    type="monotone"
                    dataKey="body_fat"
                    name="% gordura"
                    stroke="#ef4444"
                    strokeWidth={2.5}
                    connectNulls
                    dot={{ r: 3 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex h-full items-center justify-center rounded-xl border border-dashed border-lovable-border text-sm text-lovable-ink-muted">
                Sem dados suficientes de composicao corporal.
              </div>
            )}
          </div>
        </article>
      </div>

      <article className="rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-lovable-ink-muted">
          Evolucao de carga {evolution.main_lift_label ? `(${evolution.main_lift_label})` : ""}
        </h3>
        <p className="mt-1 text-xs text-lovable-ink-muted">
          Opcional: acompanha o exercicio principal. Quando nao houver carga, o sistema usa score de forca como referencia.
        </p>
        <div className="mt-3 h-64">
          {hasLoadData ? (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={loadData}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--lovable-border))" />
                <XAxis dataKey="label" tickFormatter={shortMonthLabel} stroke="hsl(var(--lovable-ink-muted))" />
                <YAxis stroke="hsl(var(--lovable-ink-muted))" />
                <Tooltip
                  labelFormatter={(value) => shortMonthLabel(String(value))}
                  formatter={(value) => {
                    if (value === null || value === undefined) return ["-", "Carga"];
                    return [`${Number(value).toFixed(1)}`, "Carga"];
                  }}
                  contentStyle={{
                    background: "hsl(var(--lovable-surface))",
                    border: "1px solid hsl(var(--lovable-border))",
                    borderRadius: "0.75rem",
                  }}
                />
                <Line type="monotone" dataKey="load" stroke="hsl(var(--lovable-primary))" strokeWidth={2.5} connectNulls dot={{ r: 3 }} />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex h-full items-center justify-center rounded-xl border border-dashed border-lovable-border text-sm text-lovable-ink-muted">
              Sem dados de carga principal para exibir.
            </div>
          )}
        </div>
      </article>
    </section>
  );
}
