import { useQuery } from "@tanstack/react-query";
import { Sparkles } from "lucide-react";
import clsx from "clsx";

import { api } from "../../services/api";

interface InsightResponse {
  dashboard: string;
  insight: string;
  source: string;
}

interface AiInsightCardProps {
  dashboard: "executive" | "retention";
}

export function AiInsightCard({ dashboard }: AiInsightCardProps) {
  const query = useQuery({
    queryKey: ["insights", dashboard],
    queryFn: async () => {
      const { data } = await api.get<InsightResponse>(`/api/v1/dashboards/insights/${dashboard}`);
      return data;
    },
    staleTime: 60 * 60 * 1000, // 1h cache
    retry: 1,
  });

  if (query.isLoading) {
    return (
      <div className="animate-pulse rounded-2xl border border-violet-200 bg-gradient-to-r from-violet-50 to-indigo-50 p-4">
        <div className="h-4 w-32 rounded bg-violet-200" />
        <div className="mt-3 space-y-2">
          <div className="h-3 w-full rounded bg-violet-100" />
          <div className="h-3 w-3/4 rounded bg-violet-100" />
        </div>
      </div>
    );
  }

  if (query.isError || !query.data) {
    return null;
  }

  return (
    <article className="rounded-2xl border border-violet-200 bg-gradient-to-r from-violet-50 to-indigo-50 p-4 shadow-sm">
      <div className="mb-2 flex items-center gap-2">
        <Sparkles size={16} className="text-violet-500" />
        <h3 className="text-xs font-semibold uppercase tracking-wider text-violet-600">
          Insights {query.data.source === "ai" ? "da IA" : "Automaticos"}
        </h3>
      </div>
      <p className="text-sm leading-relaxed text-slate-700">{query.data.insight}</p>
    </article>
  );
}
