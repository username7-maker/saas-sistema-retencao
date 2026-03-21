import type { LucideIcon } from "lucide-react";

import { Button } from "../ui2";

interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description?: string;
  action?: { label: string; onClick: () => void };
}

export function EmptyState({ icon: Icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      {Icon ? (
        <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl border border-lovable-border bg-lovable-surface-soft text-lovable-ink-muted">
          <Icon size={26} aria-hidden="true" />
        </div>
      ) : null}
      <p className="text-base font-semibold text-lovable-ink">{title}</p>
      {description ? <p className="mt-1 max-w-xs text-sm text-lovable-ink-muted">{description}</p> : null}
      {action ? (
        <Button size="sm" variant="primary" onClick={action.onClick} className="mt-4">
          {action.label}
        </Button>
      ) : null}
    </div>
  );
}
