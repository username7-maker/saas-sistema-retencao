import { PieChart as PieChartIcon } from "lucide-react";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

import { EmptyState } from "../ui";
import { getChartSeriesState } from "./chartState";

const COLORS = ["hsl(var(--lovable-success))", "hsl(var(--lovable-warning))", "hsl(var(--lovable-danger))"];

interface PieRiskChartProps {
  data: Array<{ name: string; value: number }>;
}

export function PieRiskChart({ data }: PieRiskChartProps) {
  const chartState = getChartSeriesState(data, ["value"]);

  return (
    <div className="h-72 w-full rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
      {!chartState.hasMeaningfulValues ? (
        <div className="flex h-full items-center justify-center rounded-xl border border-dashed border-lovable-border">
          <EmptyState
            icon={PieChartIcon}
            title="Sem distribuicao util para o grafico"
            description="Quando a base tiver volumes reais por faixa de risco, a pizza aparece aqui."
          />
        </div>
      ) : (
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie data={data} dataKey="value" nameKey="name" innerRadius={64} outerRadius={100}>
              {data.map((entry, index) => (
                <Cell key={entry.name} fill={COLORS[index % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{
                background: "hsl(var(--lovable-surface))",
                border: "1px solid hsl(var(--lovable-border))",
                borderRadius: "0.75rem",
              }}
              labelStyle={{ color: "hsl(var(--lovable-ink-muted))", fontSize: "12px" }}
              itemStyle={{ color: "hsl(var(--lovable-ink))", fontWeight: 600 }}
            />
          </PieChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
