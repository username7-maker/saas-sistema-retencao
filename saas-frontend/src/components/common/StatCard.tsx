import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import clsx from "clsx";

interface StatCardProps {
  label: string;
  value: string;
  tone?: "neutral" | "success" | "warning" | "danger";
  trend?: {
    value: number;
    label?: string;
    invertColor?: boolean;
  };
  tooltip?: string;
  onClick?: () => void;
}

const toneStyles: Record<NonNullable<StatCardProps["tone"]>, string> = {
  neutral: "from-lovable-ink to-[hsl(var(--lovable-ink)/0.8)]",
  success: "from-lovable-primary to-[hsl(var(--lovable-primary)/0.7)]",
  warning: "from-amber-600 to-amber-500",
  danger: "from-rose-700 to-rose-500",
};

export function StatCard({ label, value, tone = "neutral", trend, tooltip, onClick }: StatCardProps) {
  const trendDirection = trend ? (trend.value > 0 ? "up" : trend.value < 0 ? "down" : "flat") : null;

  const isTrendPositive = trend
    ? trend.invertColor
      ? trend.value < 0
      : trend.value > 0
    : false;

  const isTrendNegative = trend
    ? trend.invertColor
      ? trend.value > 0
      : trend.value < 0
    : false;

  return (
    <article
      className={clsx(
        "group relative rounded-2xl bg-gradient-to-br p-5 text-white shadow-panel transition hover:-translate-y-1",
        toneStyles[tone],
        onClick && "cursor-pointer",
      )}
      onClick={onClick}
      title={tooltip}
    >
      <p className="text-xs uppercase tracking-[0.2em] text-white/70">{label}</p>

      <div className="mt-3 flex items-end justify-between gap-2">
        <p className="text-3xl font-heading font-bold">{value}</p>

        {trend && (
          <div
            className={clsx(
              "flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold",
              isTrendPositive && "bg-emerald-400/20 text-emerald-200",
              isTrendNegative && "bg-rose-400/20 text-rose-200",
              !isTrendPositive && !isTrendNegative && "bg-white/10 text-white/60",
            )}
          >
            {trendDirection === "up" && <TrendingUp size={12} />}
            {trendDirection === "down" && <TrendingDown size={12} />}
            {trendDirection === "flat" && <Minus size={12} />}
            <span>
              {trend.value > 0 ? "+" : ""}
              {trend.value.toFixed(1)}%
            </span>
          </div>
        )}
      </div>

      {trend?.label && (
        <p className="mt-1 text-[10px] text-white/50">{trend.label}</p>
      )}

      {tooltip && (
        <div className="pointer-events-none absolute inset-x-0 -bottom-12 z-10 mx-2 rounded-lg bg-lovable-ink px-3 py-2 text-xs text-white opacity-0 shadow-lg transition group-hover:opacity-100">
          {tooltip}
        </div>
      )}
    </article>
  );
}
