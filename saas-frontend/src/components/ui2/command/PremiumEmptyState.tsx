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
        "flex min-h-[180px] flex-col items-center justify-center rounded-[24px] border border-dashed border-white/[0.07] bg-[linear-gradient(145deg,rgba(14,16,24,0.60),rgba(10,11,15,0.50))] px-6 py-8 text-center",
        className,
      )}
    >
      <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-[rgba(59,130,246,0.22)] bg-[rgba(59,130,246,0.07)] text-blue-400">
        <Icon size={20} />
      </div>
      <h3 className="mt-4 font-ui text-sm font-semibold text-lovable-ink">{title}</h3>
      {description ? <p className="mt-2 max-w-lg text-sm leading-relaxed text-lovable-ink-muted">{description}</p> : null}
      {action ? <div className="mt-5">{action}</div> : null}
    </div>
  );
}
