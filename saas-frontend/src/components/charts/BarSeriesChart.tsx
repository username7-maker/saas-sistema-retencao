import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

interface BarSeriesChartProps<T> {
  data: T[];
  xKey: keyof T & string;
  yKey: keyof T & string;
  fill?: string;
}

export function BarSeriesChart<T extends object>({
  data,
  xKey,
  yKey,
  fill = "hsl(var(--lovable-primary))",
}: BarSeriesChartProps<T>) {
  return (
    <div className="h-72 w-full rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
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
    </div>
  );
}
