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

const toneClasses: Record<MetricTone, { icon: string; value: string; card: string }> = {
  neutral: {
    icon: "text-zinc-200 bg-white/[0.04] border-white/[0.08]",
    value: "text-lovable-ink",
    card: "hover:border-white/20",
  },
  info: {
    icon: "text-[var(--pi-cyan)] bg-[rgba(0,200,255,0.12)] border-[rgba(0,200,255,0.28)]",
    value: "text-lovable-ink",
    card: "hover:border-[rgba(0,200,255,0.48)] hover:shadow-[0_0_24px_rgba(0,200,255,0.13)]",
  },
  success: {
    icon: "text-[var(--pi-green)] bg-[rgba(34,197,94,0.12)] border-[rgba(34,197,94,0.26)]",
    value: "text-lovable-ink",
    card: "hover:border-[rgba(34,197,94,0.44)] hover:shadow-[0_0_24px_rgba(34,197,94,0.12)]",
  },
  warning: {
    icon: "text-[var(--pi-orange)] bg-[rgba(249,115,22,0.12)] border-[rgba(249,115,22,0.3)]",
    value: "text-[var(--pi-orange)]",
    card: "hover:border-[rgba(249,115,22,0.48)] hover:shadow-[0_0_24px_rgba(249,115,22,0.12)]",
  },
  danger: {
    icon: "text-[var(--pi-red)] bg-[rgba(255,59,48,0.12)] border-[rgba(255,59,48,0.3)]",
    value: "text-[var(--pi-red)]",
    card: "hover:border-[rgba(255,59,48,0.48)] hover:shadow-[0_0_24px_rgba(255,59,48,0.14)]",
  },
  ai: {
    icon: "text-[var(--pi-cyan)] bg-[rgba(0,200,255,0.12)] border-[rgba(0,200,255,0.34)]",
    value: "text-[var(--pi-cyan)]",
    card: "hover:border-[rgba(0,200,255,0.5)] hover:shadow-[0_0_28px_rgba(0,200,255,0.16)]",
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
        "group relative overflow-hidden rounded-[18px] border border-white/[0.08] bg-[linear-gradient(145deg,rgba(16,16,16,0.96),rgba(3,3,3,0.88))] p-4 shadow-panel backdrop-blur-xl",
        "transition duration-200 hover:-translate-y-0.5",
        toneConfig.card,
        className,
      )}
    >
      <div className="relative flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs font-medium text-lovable-ink-muted">{label}</p>
          <div className={cn("pi-count-in mt-2 font-display text-4xl font-bold tracking-tight md:text-5xl", toneConfig.value)}>
            {value}
          </div>
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
