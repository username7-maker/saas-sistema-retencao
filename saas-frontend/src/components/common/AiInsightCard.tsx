import { useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, RefreshCw, Sparkles } from "lucide-react";

import { api } from "../../services/api";

interface InsightResponse {
  dashboard: string;
  insight: string;
  source: string;
}

type DashboardType = "executive" | "retention" | "operational" | "commercial" | "financial";

interface AiInsightCardProps {
  dashboard: DashboardType;
  theme?: "default" | "dark";
}

export function AiInsightCard({ dashboard, theme = "default" }: AiInsightCardProps) {
  const queryClient = useQueryClient();
  const isDark = theme === "dark";

  const query = useQuery({
    queryKey: ["insights", dashboard],
    queryFn: async () => {
      const { data } = await api.get<InsightResponse>(`/api/v1/dashboards/insights/${dashboard}`);
      return data;
    },
    staleTime: 60 * 60 * 1000,
    retry: 1,
  });

  if (query.isLoading) {
    return (
      <div
        className={
          isDark
            ? "animate-pulse rounded-2xl border border-zinc-800 bg-zinc-900/80 p-4"
            : "animate-pulse rounded-2xl border border-lovable-border bg-lovable-primary-soft p-4"
        }
      >
        <div className={isDark ? "h-4 w-32 rounded bg-zinc-700" : "h-4 w-32 rounded bg-lovable-border"} />
        <div className="mt-3 space-y-2">
          <div className={isDark ? "h-3 w-full rounded bg-zinc-800" : "h-3 w-full rounded bg-lovable-surface-soft"} />
          <div className={isDark ? "h-3 w-3/4 rounded bg-zinc-800" : "h-3 w-3/4 rounded bg-lovable-surface-soft"} />
        </div>
      </div>
    );
  }

  if (query.isError || !query.data) {
    return (
      <article
        className={
          isDark
            ? "rounded-2xl border border-zinc-800 bg-zinc-900/75 p-4"
            : "rounded-2xl border border-lovable-border bg-lovable-surface p-4"
        }
      >
        <div className={isDark ? "flex items-center gap-2 text-zinc-400" : "flex items-center gap-2 text-lovable-ink-muted"}>
          <AlertTriangle size={16} />
          <span className="text-xs">Insights indisponiveis no momento.</span>
        </div>
      </article>
    );
  }

  return (
    <article
      className={
        isDark
          ? "rounded-2xl border border-emerald-500/20 bg-emerald-500/10 p-4 shadow-sm"
          : "rounded-2xl border border-lovable-border bg-lovable-primary-soft p-4 shadow-sm"
      }
    >
      <div className="mb-2 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sparkles size={16} className={isDark ? "text-emerald-300" : "text-lovable-primary"} />
          <h3
            className={
              isDark
                ? "text-xs font-semibold uppercase tracking-wider text-emerald-300"
                : "text-xs font-semibold uppercase tracking-wider text-lovable-primary"
            }
          >
            Insights {query.data.source === "ai" ? "da IA" : "Automaticos"}
          </h3>
        </div>
        <button
          type="button"
          onClick={() => void queryClient.invalidateQueries({ queryKey: ["insights", dashboard] })}
          className={
            isDark
              ? "rounded-md p-1 text-zinc-400 transition-colors hover:bg-zinc-800 hover:text-zinc-100"
              : "rounded-md p-1 text-lovable-ink-muted transition-colors hover:bg-lovable-surface-soft hover:text-lovable-ink"
          }
          title="Atualizar insight"
        >
          <RefreshCw size={14} className={query.isFetching ? "animate-spin" : ""} />
        </button>
      </div>
      <p className={isDark ? "text-sm leading-relaxed text-zinc-100" : "text-sm leading-relaxed text-lovable-ink"}>
        {query.data.insight}
      </p>
    </article>
  );
}
