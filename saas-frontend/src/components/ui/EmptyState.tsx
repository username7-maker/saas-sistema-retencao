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
    <div className="flex min-h-[180px] flex-col items-center justify-center rounded-[24px] border border-dashed border-white/[0.07] bg-[linear-gradient(145deg,rgba(14,16,24,0.60),rgba(10,11,15,0.50))] px-6 py-10 text-center">
      {Icon ? (
        <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-2xl border border-[rgba(59,130,246,0.22)] bg-[rgba(59,130,246,0.07)] text-blue-400">
          <Icon size={22} aria-hidden="true" />
        </div>
      ) : null}
      <p className="text-sm font-semibold text-lovable-ink">{title}</p>
      {description ? <p className="mt-1.5 max-w-sm text-sm leading-relaxed text-lovable-ink-muted">{description}</p> : null}
      {action ? (
        <Button size="sm" variant="secondary" onClick={action.onClick} className="mt-5">
          {action.label}
        </Button>
      ) : null}
    </div>
  );
}
