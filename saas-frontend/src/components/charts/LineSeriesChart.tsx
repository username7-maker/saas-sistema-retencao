import { BarChart3 } from "lucide-react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { EmptyState } from "../ui";
import { getChartSeriesState } from "./chartState";

interface LineSeriesChartProps<T> {
  data: T[];
  xKey: keyof T & string;
  yKey: keyof T & string;
  stroke?: string;
  emptyTitle?: string;
  emptyDescription?: string;
}

export function LineSeriesChart<T extends object>({
  data,
  xKey,
  yKey,
  stroke = "hsl(var(--lovable-primary))",
  emptyTitle = "Sem base historica util para o grafico",
  emptyDescription = "Assim que a serie ganhar variacao real, este grafico passa a mostrar a evolucao.",
}: LineSeriesChartProps<T>) {
  const chartState = getChartSeriesState(data, [yKey]);

  return (
    <div className="h-72 w-full rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-card">
      {!chartState.hasMeaningfulValues ? (
        <div className="flex h-full items-center justify-center rounded-xl border border-dashed border-lovable-border">
          <EmptyState icon={BarChart3} title={emptyTitle} description={emptyDescription} />
        </div>
      ) : (
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--lovable-chart-grid) / 0.6)" />
            <XAxis dataKey={xKey} tick={{ fill: "hsl(var(--lovable-ink-muted))", fontSize: 11 }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fill: "hsl(var(--lovable-ink-muted))", fontSize: 11 }} axisLine={false} tickLine={false} />
            <Tooltip
              contentStyle={{
                background: "rgba(14,16,24,0.97)",
                border: "1px solid rgba(255,255,255,0.08)",
                borderRadius: "12px",
                padding: "10px 14px",
                boxShadow: "0 8px 32px rgba(0,0,0,0.48)",
              }}
              labelStyle={{ color: "hsl(var(--lovable-ink-muted))", fontSize: "11px", marginBottom: "4px" }}
              itemStyle={{ color: "hsl(var(--lovable-ink))", fontWeight: 600, fontFamily: "'JetBrains Mono',monospace", fontSize: "13px" }}
              cursor={{ stroke: "rgba(255,255,255,0.12)", strokeDasharray: "3 3" }}
            />
            <Line type="monotone" dataKey={yKey} stroke={stroke} strokeWidth={2} dot={false} activeDot={{ r: 4, strokeWidth: 0 }} />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
