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
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--lovable-chart-grid) / 0.6)" />
                <XAxis dataKey="label" tickFormatter={shortMonthLabel} stroke="hsl(var(--lovable-ink-muted))" />
                <YAxis stroke="hsl(var(--lovable-ink-muted))" />
                <Tooltip
                  labelFormatter={(value) => shortMonthLabel(String(value))}
                  formatter={(value) => [`${value} check-ins`, "Frequencia"]}
                  contentStyle={{
                    background: "rgba(14,16,24,0.97)",
                    border: "1px solid rgba(255,255,255,0.08)",
                    borderRadius: "12px",
                    padding: "10px 14px",
                    boxShadow: "0 8px 32px rgba(0,0,0,0.48)",
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
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--lovable-chart-grid) / 0.6)" />
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
                      background: "rgba(14,16,24,0.97)",
                      border: "1px solid rgba(255,255,255,0.08)",
                      borderRadius: "12px",
                      padding: "10px 14px",
                      boxShadow: "0 8px 32px rgba(0,0,0,0.48)",
                    }}
                    labelStyle={{ color: "hsl(var(--lovable-ink-muted))", fontSize: "11px" }}
                    itemStyle={{ fontFamily: "'JetBrains Mono',monospace", fontSize: "13px", fontWeight: 600 }}
                    cursor={{ stroke: "rgba(255,255,255,0.10)", strokeDasharray: "3 3" }}
                  />
                  <Legend />
                  <Line
                    type="monotone"
                    dataKey="lean_mass"
                    name="Massa magra"
                    stroke="hsl(var(--lovable-success))"
                    strokeWidth={2.5}
                    connectNulls
                    dot={{ r: 3 }}
                  />
                  <Line
                    type="monotone"
                    dataKey="body_fat"
                    name="% gordura"
                    stroke="hsl(var(--lovable-danger))"
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
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--lovable-chart-grid) / 0.6)" />
                <XAxis dataKey="label" tickFormatter={shortMonthLabel} stroke="hsl(var(--lovable-ink-muted))" />
                <YAxis stroke="hsl(var(--lovable-ink-muted))" />
                <Tooltip
                  labelFormatter={(value) => shortMonthLabel(String(value))}
                  formatter={(value) => {
                    if (value === null || value === undefined) return ["-", "Carga"];
                    return [`${Number(value).toFixed(1)}`, "Carga"];
                  }}
                  contentStyle={{
                    background: "rgba(14,16,24,0.97)",
                    border: "1px solid rgba(255,255,255,0.08)",
                    borderRadius: "12px",
                    padding: "10px 14px",
                    boxShadow: "0 8px 32px rgba(0,0,0,0.48)",
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
