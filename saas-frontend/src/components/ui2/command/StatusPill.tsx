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
  normal: "border-[hsl(var(--lovable-success)/0.28)] bg-[hsl(var(--lovable-success)/0.1)] text-[hsl(var(--lovable-success))]",
  alert: "border-[hsl(var(--lovable-warning)/0.3)] bg-[hsl(var(--lovable-warning)/0.1)] text-[hsl(var(--lovable-warning))]",
  critical: "border-[hsl(var(--lovable-danger)/0.34)] bg-[hsl(var(--lovable-danger)/0.12)] text-[hsl(var(--lovable-danger))]",
  ai: "border-[hsl(var(--lovable-ai)/0.24)] bg-[hsl(var(--lovable-ai)/0.12)] text-[hsl(var(--lovable-ai))]",
  /* Integration tone shares the ai token (IA identity) — cyan removed from system */
  integration: "border-[hsl(var(--lovable-ai)/0.24)] bg-[hsl(var(--lovable-ai)/0.12)] text-[hsl(var(--lovable-ai))]",
  sync: "border-[hsl(var(--lovable-primary)/0.22)] bg-[hsl(var(--lovable-primary)/0.1)] text-[hsl(var(--lovable-primary))]",
  retention: "border-[hsl(var(--lovable-primary)/0.22)] bg-[hsl(var(--lovable-primary)/0.1)] text-[hsl(var(--lovable-primary))]",
  success: "border-[hsl(var(--lovable-success)/0.28)] bg-[hsl(var(--lovable-success)/0.1)] text-[hsl(var(--lovable-success))]",
  warning: "border-[hsl(var(--lovable-warning)/0.3)] bg-[hsl(var(--lovable-warning)/0.1)] text-[hsl(var(--lovable-warning))]",
  danger: "border-[hsl(var(--lovable-danger)/0.34)] bg-[hsl(var(--lovable-danger)/0.12)] text-[hsl(var(--lovable-danger))]",
  neutral: "border-lovable-border bg-lovable-surface-soft/75 text-lovable-ink-muted",
};

const dotClasses: Record<StatusPillTone, string> = {
  normal: "bg-[hsl(var(--lovable-success))]",
  alert: "bg-[hsl(var(--lovable-warning))]",
  critical: "bg-[hsl(var(--lovable-danger))]",
  ai: "bg-[hsl(var(--lovable-ai))]",
  integration: "bg-[hsl(var(--lovable-ai))]",
  sync: "bg-[hsl(var(--lovable-primary))]",
  retention: "bg-[hsl(var(--lovable-primary))]",
  success: "bg-[hsl(var(--lovable-success))]",
  warning: "bg-[hsl(var(--lovable-warning))]",
  danger: "bg-[hsl(var(--lovable-danger))]",
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
      {dot ? (
        <span
          className={cn(
            "h-1.5 w-1.5 rounded-full",
            dotClasses[tone],
            tone === "critical" || tone === "danger" ? "pi-pulse" : "",
          )}
        />
      ) : null}
      {children}
    </span>
  );
}
