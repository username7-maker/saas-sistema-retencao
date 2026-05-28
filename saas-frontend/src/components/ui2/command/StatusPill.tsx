import type { HTMLAttributes, ReactNode } from "react";

import { cn } from "../cn";

type StatusPillTone =
  | "normal"
  | "alert"
  | "critical"
  | "ai"
  | "integration"
  | "sync"
  | "retention"
  | "success"
  | "warning"
  | "danger"
  | "neutral";

interface StatusPillProps extends HTMLAttributes<HTMLSpanElement> {
  tone?: StatusPillTone;
  children: ReactNode;
  dot?: boolean;
}

const toneClasses: Record<StatusPillTone, string> = {
  normal: "border-emerald-400/20 bg-emerald-400/10 text-emerald-200",
  alert: "border-amber-400/22 bg-amber-400/10 text-amber-200",
  critical: "border-rose-400/25 bg-rose-400/12 text-rose-200",
  ai: "border-violet-400/24 bg-violet-400/12 text-violet-200",
  integration: "border-cyan-400/22 bg-cyan-400/10 text-cyan-200",
  sync: "border-blue-400/22 bg-blue-400/10 text-blue-200",
  retention: "border-sky-400/22 bg-sky-400/10 text-sky-200",
  success: "border-emerald-400/20 bg-emerald-400/10 text-emerald-200",
  warning: "border-amber-400/22 bg-amber-400/10 text-amber-200",
  danger: "border-rose-400/25 bg-rose-400/12 text-rose-200",
  neutral: "border-lovable-border bg-lovable-surface-soft/75 text-lovable-ink-muted",
};

const dotClasses: Record<StatusPillTone, string> = {
  normal: "bg-emerald-300",
  alert: "bg-amber-300",
  critical: "bg-rose-300",
  ai: "bg-violet-300",
  integration: "bg-cyan-300",
  sync: "bg-blue-300",
  retention: "bg-sky-300",
  success: "bg-emerald-300",
  warning: "bg-amber-300",
  danger: "bg-rose-300",
  neutral: "bg-lovable-ink-muted",
};

export function StatusPill({ tone = "neutral", dot = false, className, children, ...props }: StatusPillProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-bold uppercase tracking-[0.12em]",
        toneClasses[tone],
        className,
      )}
      {...props}
    >
      {dot ? <span className={cn("h-1.5 w-1.5 rounded-full", dotClasses[tone])} /> : null}
      {children}
    </span>
  );
}
