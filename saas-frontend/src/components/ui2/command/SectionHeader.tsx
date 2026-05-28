import type { ReactNode } from "react";

import { cn } from "../cn";
import { StatusPill } from "./StatusPill";

interface SectionHeaderProps {
  eyebrow?: string;
  title: string;
  subtitle?: ReactNode;
  actions?: ReactNode;
  count?: ReactNode;
  className?: string;
}

export function SectionHeader({ eyebrow, title, subtitle, actions, count, className }: SectionHeaderProps) {
  return (
    <div className={cn("mb-4 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between", className)}>
      <div className="min-w-0">
        {eyebrow ? <p className="text-[11px] font-bold uppercase tracking-[0.28em] text-lovable-ink-muted">{eyebrow}</p> : null}
        <div className="mt-1 flex flex-wrap items-center gap-2">
          <h2 className="font-heading text-xl font-bold tracking-tight text-lovable-ink">{title}</h2>
          {count !== undefined ? <StatusPill tone="neutral">{count}</StatusPill> : null}
        </div>
        {subtitle ? <p className="mt-1 max-w-2xl text-sm leading-relaxed text-lovable-ink-muted">{subtitle}</p> : null}
      </div>
      {actions ? <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div> : null}
    </div>
  );
}
