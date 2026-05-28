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
  normal: "border-[rgba(34,197,94,0.28)] bg-[rgba(34,197,94,0.1)] text-[var(--pi-green)]",
  alert: "border-[rgba(249,115,22,0.3)] bg-[rgba(249,115,22,0.1)] text-[var(--pi-orange)]",
  critical: "border-[rgba(255,59,48,0.34)] bg-[rgba(255,59,48,0.12)] text-[var(--pi-red)]",
  ai: "border-violet-400/24 bg-violet-400/12 text-violet-200",
  integration: "border-[rgba(0,200,255,0.28)] bg-[rgba(0,200,255,0.1)] text-[var(--pi-cyan)]",
  sync: "border-blue-400/22 bg-blue-400/10 text-blue-200",
  retention: "border-sky-400/22 bg-sky-400/10 text-sky-200",
  success: "border-[rgba(34,197,94,0.28)] bg-[rgba(34,197,94,0.1)] text-[var(--pi-green)]",
  warning: "border-[rgba(249,115,22,0.3)] bg-[rgba(249,115,22,0.1)] text-[var(--pi-orange)]",
  danger: "border-[rgba(255,59,48,0.34)] bg-[rgba(255,59,48,0.12)] text-[var(--pi-red)]",
  neutral: "border-lovable-border bg-lovable-surface-soft/75 text-lovable-ink-muted",
};

const dotClasses: Record<StatusPillTone, string> = {
  normal: "bg-[var(--pi-green)]",
  alert: "bg-[var(--pi-orange)]",
  critical: "bg-[var(--pi-red)]",
  ai: "bg-violet-300",
  integration: "bg-[var(--pi-cyan)]",
  sync: "bg-blue-300",
  retention: "bg-sky-300",
  success: "bg-[var(--pi-green)]",
  warning: "bg-[var(--pi-orange)]",
  danger: "bg-[var(--pi-red)]",
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
            tone === "normal" || tone === "success" || tone === "integration" ? "pi-pulse-green" : "",
          )}
        />
      ) : null}
      {children}
    </span>
  );
}
