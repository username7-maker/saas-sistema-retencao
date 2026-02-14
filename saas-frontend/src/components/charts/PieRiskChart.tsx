import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

const COLORS = ["#1d9a7f", "#f59e0b", "#e11d48"];

interface PieRiskChartProps {
  data: Array<{ name: string; value: number }>;
}

export function PieRiskChart({ data }: PieRiskChartProps) {
  return (
    <div className="h-72 w-full rounded-2xl border border-slate-200 bg-white p-4 shadow-panel">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie data={data} dataKey="value" nameKey="name" innerRadius={64} outerRadius={100}>
            {data.map((entry, index) => (
              <Cell key={entry.name} fill={COLORS[index % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
