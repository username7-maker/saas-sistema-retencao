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
  stroke = "#1d9a7f",
}: LineSeriesChartProps<T>) {
  return (
    <div className="h-72 w-full rounded-2xl border border-slate-200 bg-white p-4 shadow-panel">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis dataKey={xKey} stroke="#64748b" />
          <YAxis stroke="#64748b" />
          <Tooltip />
          <Line type="monotone" dataKey={yKey} stroke={stroke} strokeWidth={2.5} dot={{ r: 3 }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
