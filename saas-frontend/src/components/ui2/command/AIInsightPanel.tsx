import type { ReactNode } from "react";
import { Bot, Sparkles } from "lucide-react";

import { CommandCard } from "./CommandCard";
import { StatusPill } from "./StatusPill";

interface AIInsightPanelProps {
  title?: string;
  summary: ReactNode;
  updatedAt?: string;
  items?: ReactNode[];
  alerts?: ReactNode[];
  footer?: ReactNode;
}

export function AIInsightPanel({
  title = "Briefing inteligente",
  summary,
  updatedAt,
  items = [],
  alerts = [],
  footer,
}: AIInsightPanelProps) {
  return (
    <CommandCard variant="ai">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          {/* Violet = IA identity */}
          <div className="flex h-9 w-9 items-center justify-center rounded-2xl border border-[rgba(139,92,246,0.32)] bg-[rgba(139,92,246,0.12)] text-violet-400 shadow-[var(--glow-violet)]">
            <Bot size={17} />
          </div>
          <div>
            <p className="text-[11px] font-bold uppercase tracking-[0.24em] text-lovable-ink-muted">IA</p>
            <h3 className="font-heading text-base font-bold text-lovable-ink">{title}</h3>
          </div>
        </div>
        <StatusPill tone="ai" dot>Live</StatusPill>
      </div>

      <div className="rounded-[18px] border border-[rgba(139,92,246,0.18)] bg-[rgba(139,92,246,0.055)] p-4">
        <div className="flex items-start gap-3">
          <Sparkles size={16} className="mt-0.5 text-violet-400" />
          <div className="min-w-0">
            <p className="text-sm leading-relaxed text-lovable-ink">{summary}</p>
            {updatedAt ? <p className="mt-3 text-xs text-lovable-ink-muted">{updatedAt}</p> : null}
          </div>
        </div>
      </div>

      {alerts.length > 0 ? (
        <div className="mt-4 space-y-2">
          {alerts.map((alert, index) => (
            <div key={index} className="rounded-2xl border border-lovable-border/62 bg-lovable-surface/58 px-3 py-2 text-sm text-lovable-ink">
              {alert}
            </div>
          ))}
        </div>
      ) : null}

      {items.length > 0 ? (
        <div className="mt-4 space-y-2">
          {items.map((item, index) => (
            <div key={index} className="flex items-start gap-2 text-sm text-lovable-ink-muted">
              <span className="mt-[6px] h-1.5 w-1.5 shrink-0 rounded-full bg-violet-500/60" />
              <span>{item}</span>
            </div>
          ))}
        </div>
      ) : null}

      {footer ? <div className="mt-4">{footer}</div> : null}
    </CommandCard>
  );
}
