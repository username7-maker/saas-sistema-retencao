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
    <div className="mb-4 flex flex-col items-start gap-3 sm:flex-row sm:items-start sm:justify-between">
      <div className="min-w-0 flex-1">
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

      {actions ? <div className="flex w-full flex-wrap items-center gap-2 sm:w-auto sm:justify-end">{actions}</div> : null}
    </div>
  );
}
