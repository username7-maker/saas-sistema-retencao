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
      {Icon ? <Icon size={40} className="mb-4 text-lovable-border" aria-hidden="true" /> : null}
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
