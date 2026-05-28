import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import { Inbox } from "lucide-react";

import { cn } from "../cn";

interface PremiumEmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description?: ReactNode;
  action?: ReactNode;
  className?: string;
}

export function PremiumEmptyState({ icon: Icon = Inbox, title, description, action, className }: PremiumEmptyStateProps) {
  return (
    <div
      className={cn(
        "flex min-h-[180px] flex-col items-center justify-center rounded-[24px] border border-dashed border-lovable-border/80 bg-[linear-gradient(145deg,hsl(var(--lovable-surface)/0.54),hsl(var(--lovable-bg-muted)/0.44))] px-6 py-8 text-center",
        className,
      )}
    >
      <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-lovable-border/70 bg-lovable-surface-soft/72 text-[hsl(var(--lovable-primary))] shadow-panel">
        <Icon size={20} />
      </div>
      <h3 className="mt-4 font-heading text-base font-bold text-lovable-ink">{title}</h3>
      {description ? <p className="mt-2 max-w-lg text-sm leading-relaxed text-lovable-ink-muted">{description}</p> : null}
      {action ? <div className="mt-5">{action}</div> : null}
    </div>
  );
}
