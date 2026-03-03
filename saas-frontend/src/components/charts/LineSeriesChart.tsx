import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

interface LineSeriesChartProps<T> {
  data: T[];
  xKey: keyof T & string;
  yKey: keyof T & string;
  stroke?: string;
}

export function LineSeriesChart<T extends object>({
  data,
  xKey,
  yKey,
  stroke = "hsl(var(--lovable-primary))",
}: LineSeriesChartProps<T>) {
  return (
    <div className="h-72 w-full rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data}>
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
            cursor={{ stroke: "hsl(var(--lovable-border-strong))", strokeDasharray: "3 3" }}
          />
          <Line type="monotone" dataKey={yKey} stroke={stroke} strokeWidth={2.5} dot={{ r: 3 }} activeDot={{ r: 4 }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
