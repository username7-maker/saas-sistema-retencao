import type { ReactNode } from "react";

import { Badge } from "../ui2";

interface SectionHeaderProps {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
  count?: number;
}

export function SectionHeader({ title, subtitle, actions, count }: SectionHeaderProps) {
  return (
    <div className="mb-4 flex items-center justify-between gap-3">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-lovable-ink-muted">{title}</p>
          {typeof count === "number" ? (
            <Badge variant="neutral" size="sm" className="normal-case tracking-normal">
              {count}
            </Badge>
          ) : null}
        </div>
        {subtitle ? <p className="mt-1 text-sm text-lovable-ink-muted">{subtitle}</p> : null}
      </div>

      {actions ? <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div> : null}
    </div>
  );
}
