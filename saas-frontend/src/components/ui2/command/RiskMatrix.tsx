import type { ReactNode } from "react";

import { cn } from "../cn";
import { StatusPill } from "./StatusPill";

type RiskLevel = "critical" | "high" | "medium" | "low";

export interface RiskMatrixSegment {
  id: string;
  label: string;
  count: number;
  rate?: number;
  helper?: ReactNode;
  level: RiskLevel;
}

interface RiskMatrixProps {
  segments: RiskMatrixSegment[];
  className?: string;
}

const riskTone: Record<RiskLevel, "critical" | "danger" | "warning" | "sync"> = {
  critical: "critical",
  high: "danger",
  medium: "warning",
  low: "sync",
};

const riskLabel: Record<RiskLevel, string> = {
  critical: "Crítico",
  high: "Alto",
  medium: "Médio",
  low: "Baixo",
};

const barClass: Record<RiskLevel, string> = {
  critical: "bg-rose-400",
  high: "bg-orange-400",
  medium: "bg-amber-400",
  low: "bg-emerald-400",
};

export function RiskMatrix({ segments, className }: RiskMatrixProps) {
  return (
    <div className={cn("space-y-2", className)}>
      {segments.map((segment) => {
        const clampedRate = Math.max(0, Math.min(100, segment.rate ?? 0));
        return (
          <div key={segment.id} className="rounded-[18px] border border-lovable-border/65 bg-lovable-surface/58 px-3 py-3">
            <div className="grid gap-3 md:grid-cols-[auto_1fr_auto] md:items-center">
              <StatusPill tone={riskTone[segment.level]}>{riskLabel[segment.level]}</StatusPill>
              <div className="min-w-0">
                <div className="flex flex-wrap items-baseline gap-2">
                  <p className="font-semibold text-lovable-ink">{segment.label}</p>
                  <span className="text-sm text-lovable-ink-muted">{segment.count.toLocaleString("pt-BR")} alunos</span>
                </div>
                {segment.helper ? <p className="mt-1 text-xs text-lovable-ink-muted">{segment.helper}</p> : null}
                <div className="mt-2 h-2 overflow-hidden rounded-full bg-lovable-bg-muted">
                  <div className={cn("h-full rounded-full", barClass[segment.level])} style={{ width: `${clampedRate}%` }} />
                </div>
              </div>
              <p className="text-right font-display text-lg font-bold text-lovable-ink">{clampedRate.toFixed(1)}%</p>
            </div>
          </div>
        );
      })}
    </div>
  );
}
