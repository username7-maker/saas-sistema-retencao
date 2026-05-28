import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import { ArrowDownRight, ArrowRight, ArrowUpRight } from "lucide-react";

import { cn } from "../cn";

type MetricTone = "neutral" | "info" | "success" | "warning" | "danger" | "ai";
type TrendDirection = "up" | "down" | "flat";

interface MetricCardProps {
  label: string;
  value: ReactNode;
  subtitle?: ReactNode;
  trend?: ReactNode;
  trendDirection?: TrendDirection;
  icon?: LucideIcon;
  tone?: MetricTone;
  className?: string;
  footer?: ReactNode;
}

const toneClasses: Record<MetricTone, { icon: string; value: string }> = {
  neutral: {
    icon: "text-lovable-ink bg-lovable-surface-soft border-lovable-border",
    value: "text-lovable-ink",
  },
  info: {
    icon: "text-cyan-200 bg-[hsl(var(--lovable-primary)/0.18)] border-[hsl(var(--lovable-primary)/0.26)]",
    value: "text-lovable-ink",
  },
  success: {
    icon: "text-emerald-200 bg-[hsl(var(--lovable-success)/0.18)] border-[hsl(var(--lovable-success)/0.25)]",
    value: "text-lovable-ink",
  },
  warning: {
    icon: "text-amber-200 bg-[hsl(var(--lovable-warning)/0.18)] border-[hsl(var(--lovable-warning)/0.28)]",
    value: "text-lovable-ink",
  },
  danger: {
    icon: "text-rose-200 bg-[hsl(var(--lovable-danger)/0.18)] border-[hsl(var(--lovable-danger)/0.28)]",
    value: "text-lovable-ink",
  },
  ai: {
    icon: "text-violet-200 bg-[hsl(var(--lovable-ai)/0.18)] border-[hsl(var(--lovable-ai)/0.32)]",
    value: "text-lovable-ink",
  },
};

const trendClasses: Record<TrendDirection, string> = {
  up: "text-emerald-300",
  down: "text-rose-300",
  flat: "text-lovable-ink-muted",
};

const trendIcons: Record<TrendDirection, LucideIcon> = {
  up: ArrowUpRight,
  down: ArrowDownRight,
  flat: ArrowRight,
};

export function MetricCard({
  label,
  value,
  subtitle,
  trend,
  trendDirection = "flat",
  icon: Icon,
  tone = "neutral",
  className,
  footer,
}: MetricCardProps) {
  const toneConfig = toneClasses[tone];
  const TrendIcon = trendIcons[trendDirection];

  return (
    <div
      className={cn(
        "group relative overflow-hidden rounded-[24px] border border-lovable-border/72 bg-[linear-gradient(145deg,hsl(var(--lovable-surface)/0.92),hsl(var(--lovable-bg-muted)/0.7))] p-4 shadow-panel backdrop-blur-xl",
        "transition duration-200 hover:-translate-y-0.5 hover:border-[hsl(var(--lovable-primary)/0.34)]",
        className,
      )}
    >
      <div className="relative flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs font-medium text-lovable-ink-muted">{label}</p>
          <div className={cn("mt-2 font-display text-3xl font-bold tracking-tight", toneConfig.value)}>{value}</div>
        </div>
        {Icon ? (
          <div className={cn("flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl border shadow-[0_18px_42px_-24px_currentColor]", toneConfig.icon)}>
            <Icon size={20} />
          </div>
        ) : null}
      </div>
      {trend || subtitle ? (
        <div className="relative mt-3 space-y-1">
          {trend ? (
            <p className={cn("inline-flex items-center gap-1 text-xs font-semibold", trendClasses[trendDirection])}>
              <TrendIcon size={13} />
              {trend}
            </p>
          ) : null}
          {subtitle ? <p className="text-xs leading-relaxed text-lovable-ink-muted">{subtitle}</p> : null}
        </div>
      ) : null}
      {footer ? <div className="relative mt-3">{footer}</div> : null}
    </div>
  );
}
