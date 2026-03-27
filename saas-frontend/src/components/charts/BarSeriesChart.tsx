import { BarChart3 } from "lucide-react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { EmptyState } from "../ui";
import { getChartSeriesState } from "./chartState";

interface BarSeriesChartProps<T> {
  data: T[];
  xKey: keyof T & string;
  yKey: keyof T & string;
  fill?: string;
  emptyTitle?: string;
  emptyDescription?: string;
}

export function BarSeriesChart<T extends object>({
  data,
  xKey,
  yKey,
  fill = "hsl(var(--lovable-primary))",
  emptyTitle = "Sem base historica util para o grafico",
  emptyDescription = "Assim que houver volume suficiente, este grafico passa a mostrar a distribuicao real.",
}: BarSeriesChartProps<T>) {
  const chartState = getChartSeriesState(data, [yKey]);

  return (
    <div className="h-72 w-full rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
      {!chartState.hasMeaningfulValues ? (
        <div className="flex h-full items-center justify-center rounded-xl border border-dashed border-lovable-border">
          <EmptyState icon={BarChart3} title={emptyTitle} description={emptyDescription} />
        </div>
      ) : (
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--lovable-border))" />
            <XAxis dataKey={xKey} stroke="hsl(var(--lovable-ink-muted))" />
            <YAxis stroke="hsl(var(--lovable-ink-muted))" />
            <Tooltip
              contentStyle={{
                background: "hsl(var(--lovable-surface))",
                border: "1px solid hsl(var(--lovable-border))",
                borderRadius: "0.75rem",
              }}
              labelStyle={{ color: "hsl(var(--lovable-ink-muted))", fontSize: "12px" }}
              itemStyle={{ color: "hsl(var(--lovable-ink))", fontWeight: 600 }}
              cursor={{ fill: "hsl(var(--lovable-primary-soft) / 0.35)" }}
            />
            <Bar dataKey={yKey} fill={fill} radius={[8, 8, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
