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
  active?: boolean;
}

const toneStyles: Record<NonNullable<StatCardProps["tone"]>, string> = {
  neutral: "border-lovable-border-strong/40 bg-[linear-gradient(180deg,hsl(var(--lovable-surface-soft)),hsl(var(--lovable-surface)))]",
  success: "border-[hsl(var(--lovable-success)/0.22)] bg-[linear-gradient(180deg,hsl(var(--lovable-surface-soft)),hsl(var(--lovable-surface)))]",
  warning: "border-[hsl(var(--lovable-warning)/0.22)] bg-[linear-gradient(180deg,hsl(var(--lovable-surface-soft)),hsl(var(--lovable-surface)))]",
  danger: "border-[hsl(var(--lovable-danger)/0.22)] bg-[linear-gradient(180deg,hsl(var(--lovable-surface-soft)),hsl(var(--lovable-surface)))]",
};

export function StatCard({ label, value, tone = "neutral", trend, tooltip, onClick, active = false }: StatCardProps) {
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
        "group relative rounded-[24px] border p-5 text-lovable-ink shadow-panel transition hover:-translate-y-1",
        toneStyles[tone],
        active && "ring-2 ring-[hsl(var(--lovable-primary)/0.7)]",
        onClick && "cursor-pointer",
      )}
      onClick={onClick}
      onKeyDown={(event) => {
        if (!onClick) return;
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          onClick();
        }
      }}
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
      aria-pressed={onClick ? active : undefined}
      title={tooltip}
    >
      <p className="text-xs uppercase tracking-[0.2em] text-lovable-ink-muted">{label}</p>

      <div className="mt-3 flex items-end justify-between gap-2">
        <p className="text-3xl font-heading font-bold text-lovable-ink">{value}</p>

        {trend && (
          <div
            className={clsx(
              "flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold",
              isTrendPositive && "bg-emerald-400/20 text-emerald-300",
              isTrendNegative && "bg-rose-400/20 text-rose-300",
              !isTrendPositive && !isTrendNegative && "bg-lovable-surface-soft text-lovable-ink-muted",
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
        <p className="mt-1 text-[10px] text-lovable-ink-muted">{trend.label}</p>
      )}

      {tooltip && (
        <div className="pointer-events-none absolute inset-x-0 -bottom-12 z-10 mx-2 rounded-lg border border-lovable-border bg-lovable-surface px-3 py-2 text-xs text-lovable-ink opacity-0 shadow-panel transition group-hover:opacity-100">
          {tooltip}
        </div>
      )}
    </article>
  );
}
