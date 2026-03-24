import { useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, RefreshCw, Sparkles } from "lucide-react";

import { useAuth } from "../../hooks/useAuth";
import { api } from "../../services/api";
import { getPermissionAwareMessage } from "../../utils/httpErrors";
import { canViewAiInsight } from "../../utils/roleAccess";

interface InsightResponse {
  dashboard: string;
  insight: string;
  source: string;
}

type DashboardType = "executive" | "retention" | "operational" | "commercial" | "financial";

interface AiInsightCardProps {
  dashboard: DashboardType;
}

export function AiInsightCard({ dashboard }: AiInsightCardProps) {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const canSeeInsight = canViewAiInsight(user?.role, dashboard);

  const query = useQuery({
    queryKey: ["insights", dashboard],
    queryFn: async () => {
      const { data } = await api.get<InsightResponse>(`/api/v1/dashboards/insights/${dashboard}`);
      return data;
    },
    staleTime: 60 * 60 * 1000,
    retry: 1,
    enabled: canSeeInsight,
  });

  if (!canSeeInsight) {
    return null;
  }

  if (query.isLoading) {
    return (
      <div className="animate-pulse rounded-[24px] border border-lovable-border bg-lovable-surface/92 p-4 shadow-panel">
        <div className="h-4 w-32 rounded bg-lovable-border" />
        <div className="mt-3 space-y-2">
          <div className="h-3 w-full rounded bg-lovable-border" />
          <div className="h-3 w-3/4 rounded bg-lovable-border" />
        </div>
      </div>
    );
  }

  if (query.isError || !query.data) {
    return (
      <article className="rounded-[24px] border border-lovable-border bg-lovable-surface/92 p-4 shadow-panel">
        <div className="flex items-center gap-2 text-lovable-ink-muted">
          <AlertTriangle size={16} />
          <span className="text-xs">
            {getPermissionAwareMessage(query.error, "Insights indisponiveis no momento.", "Insights disponiveis apenas para gestao.")}
          </span>
        </div>
      </article>
    );
  }

  return (
    <article className="rounded-[24px] border border-lovable-border bg-lovable-surface/92 p-4 shadow-panel">
      <div className="mb-2 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sparkles size={16} className="text-lovable-primary" />
          <h3 className="text-xs font-semibold uppercase tracking-wider text-lovable-primary">
            Insights {query.data.source === "ai" ? "da IA" : "Automaticos"}
          </h3>
        </div>
        <button
          type="button"
          onClick={() => void queryClient.invalidateQueries({ queryKey: ["insights", dashboard] })}
          className="rounded-lg p-1.5 text-lovable-ink-muted transition-colors hover:bg-lovable-surface-soft hover:text-lovable-ink"
          title="Atualizar insight"
        >
          <RefreshCw size={14} className={query.isFetching ? "animate-spin" : ""} />
        </button>
      </div>
      <p className="text-sm leading-relaxed text-lovable-ink">{query.data.insight}</p>
    </article>
  );
}
