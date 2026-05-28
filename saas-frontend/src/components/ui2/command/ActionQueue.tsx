import type { ReactNode } from "react";
import { ChevronRight } from "lucide-react";

import { Button } from "../Button";
import { cn } from "../cn";
import { StatusPill } from "./StatusPill";

type ActionPriority = "critical" | "high" | "medium" | "low";

export interface ActionQueueItem {
  id: string;
  title: string;
  subtitle?: ReactNode;
  priority?: ActionPriority;
  owner?: string;
  status?: string;
  ctaLabel?: string;
  onClick?: () => void;
}

interface ActionQueueProps {
  items: ActionQueueItem[];
  className?: string;
  empty?: ReactNode;
}

const priorityTone: Record<ActionPriority, "critical" | "danger" | "warning" | "sync"> = {
  critical: "critical",
  high: "danger",
  medium: "warning",
  low: "sync",
};

const priorityLabel: Record<ActionPriority, string> = {
  critical: "Crítico",
  high: "Alto",
  medium: "Médio",
  low: "Baixo",
};

export function ActionQueue({ items, className, empty }: ActionQueueProps) {
  if (items.length === 0) {
    return <>{empty ?? <p className="text-sm text-lovable-ink-muted">Nenhuma ação sugerida agora.</p>}</>;
  }

  return (
    <div className={cn("space-y-2", className)}>
      {items.map((item) => {
        const priority = item.priority ?? "medium";
        return (
          <div key={item.id} className="rounded-[18px] border border-lovable-border/65 bg-lovable-surface/58 px-3 py-3">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="text-sm font-semibold text-lovable-ink">{item.title}</p>
                  <StatusPill tone={priorityTone[priority]}>{priorityLabel[priority]}</StatusPill>
                </div>
                {item.subtitle ? <p className="mt-1 text-xs leading-relaxed text-lovable-ink-muted">{item.subtitle}</p> : null}
                {(item.owner || item.status) ? (
                  <p className="mt-2 text-[11px] uppercase tracking-[0.14em] text-lovable-ink-muted">
                    {[item.owner, item.status].filter(Boolean).join(" · ")}
                  </p>
                ) : null}
              </div>
              {item.onClick ? (
                <Button size="sm" variant="ghost" onClick={item.onClick} className="shrink-0">
                  {item.ctaLabel ?? "Abrir"}
                  <ChevronRight size={13} />
                </Button>
              ) : null}
            </div>
          </div>
        );
      })}
    </div>
  );
}
