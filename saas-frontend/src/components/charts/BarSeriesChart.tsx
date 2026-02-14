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
  fill = "#1d9a7f",
}: BarSeriesChartProps<T>) {
  return (
    <div className="h-72 w-full rounded-2xl border border-slate-200 bg-white p-4 shadow-panel">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis dataKey={xKey} stroke="#64748b" />
          <YAxis stroke="#64748b" />
          <Tooltip />
          <Bar dataKey={yKey} fill={fill} radius={[8, 8, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
