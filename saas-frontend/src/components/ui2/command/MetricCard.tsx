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
    icon: "text-zinc-300 bg-white/[0.04] border-white/[0.08]",
    value: "text-lovable-ink",
    card: "hover:border-white/[0.14]",
  },
  info: {
    // Blue = primary / navigation accent
    icon: "text-blue-400 bg-[rgba(59,130,246,0.14)] border-[rgba(59,130,246,0.28)]",
    value: "text-lovable-ink",
    card: "hover:border-[rgba(59,130,246,0.44)] hover:shadow-[var(--glow-blue)]",
  },
  success: {
    icon: "text-emerald-400 bg-[rgba(16,185,129,0.12)] border-[rgba(16,185,129,0.26)]",
    value: "text-lovable-ink",
    card: "hover:border-[rgba(16,185,129,0.42)] hover:shadow-[0_0_20px_rgba(16,185,129,0.14)]",
  },
  warning: {
    icon: "text-amber-400 bg-[rgba(245,158,11,0.12)] border-[rgba(245,158,11,0.30)]",
    value: "text-amber-300",
    card: "hover:border-[rgba(245,158,11,0.46)] hover:shadow-[0_0_20px_rgba(245,158,11,0.12)]",
  },
  danger: {
    icon: "text-rose-400 bg-[rgba(255,59,59,0.12)] border-[rgba(255,59,59,0.30)]",
    value: "text-rose-300",
    card: "hover:border-[rgba(255,59,59,0.44)] hover:shadow-[var(--glow-danger)]",
  },
  ai: {
    // Violet = IA identity
    icon: "text-violet-400 bg-[rgba(139,92,246,0.14)] border-[rgba(139,92,246,0.30)]",
    value: "text-violet-300",
    card: "hover:border-[rgba(139,92,246,0.46)] hover:shadow-[var(--glow-violet)]",
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
        // Surface uses new depth token; before: adds subtle top-edge gradient
        "group relative overflow-hidden rounded-[18px] border border-white/[0.07]",
        "bg-[linear-gradient(145deg,rgba(14,16,24,0.97),rgba(10,11,15,0.92))]",
        "p-4 shadow-card backdrop-blur-xl",
        "transition-all duration-200 hover:-translate-y-[1px]",
        "before:pointer-events-none before:absolute before:inset-x-0 before:top-0 before:h-16",
        "before:bg-[linear-gradient(180deg,rgba(255,255,255,0.025),transparent_60%)]",
        toneConfig.card,
        className,
      )}
    >
      <div className="relative flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-[11px] font-medium uppercase tracking-[0.12em] text-lovable-ink-muted">{label}</p>
          <div className={cn("num pi-count-in mt-2 text-4xl font-semibold md:text-5xl", toneConfig.value)}>
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
