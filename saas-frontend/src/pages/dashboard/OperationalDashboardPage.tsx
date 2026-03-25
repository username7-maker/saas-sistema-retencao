import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, CalendarDays } from "lucide-react";

import { HeatmapGrid } from "../../components/charts/HeatmapGrid";
import { AiInsightCard } from "../../components/common/AiInsightCard";
import { DashboardActions } from "../../components/common/DashboardActions";
import { LoadingPanel } from "../../components/common/LoadingPanel";
import { QuickActions } from "../../components/common/QuickActions";
import { EmptyState } from "../../components/ui";
import { StatCard } from "../../components/common/StatCard";
import { Badge } from "../../components/ui2";
import { useOperationalDashboard } from "../../hooks/useDashboard";
import { tokenStorage } from "../../services/storage";
import type { RiskLevel } from "../../types";
import { getPermissionAwareMessage } from "../../utils/httpErrors";

const RISK_BADGE: Record<RiskLevel, "danger" | "warning" | "success"> = {
  red: "danger",
  yellow: "warning",
  green: "success",
};

const RISK_LABELS: Record<RiskLevel, string> = {
  red: "Alto",
  yellow: "Medio",
  green: "Baixo",
};

export function OperationalDashboardPage() {
  const queryClient = useQueryClient();
  const [isRealtimeConnected, setIsRealtimeConnected] = useState(false);
  const [realtimeEvents, setRealtimeEvents] = useState(0);
  const query = useOperationalDashboard();

  const handleActionComplete = () => {
    void queryClient.invalidateQueries({ queryKey: ["dashboard", "operational"] });
  };

  useEffect(() => {
    const token = tokenStorage.getAccessToken();
    if (!token) return;

    const apiBaseEnv = import.meta.env.VITE_API_BASE_URL?.trim();
    const wsBaseEnv = (import.meta.env.VITE_WS_BASE_URL as string | undefined)?.trim();
    const apiBase = apiBaseEnv || "http://127.0.0.1:8000";
    const wsBase = wsBaseEnv || apiBase.replace(/^http/, "ws");
    const wsUrl = `${wsBase.replace(/\/$/, "")}/ws/updates?token=${encodeURIComponent(token)}`;
    const socket = new WebSocket(wsUrl);

    socket.onopen = () => setIsRealtimeConnected(true);
    socket.onclose = () => setIsRealtimeConnected(false);
    socket.onerror = () => setIsRealtimeConnected(false);
    socket.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data) as { event?: string };
        if (message.event === "checkin_created" || message.event === "risk_alert_created" || message.event === "risk_alert_updated") {
          setRealtimeEvents((current) => current + 1);
          void queryClient.invalidateQueries({ queryKey: ["dashboard", "operational"] });
        }
      } catch {
        // Ignore malformed websocket messages.
      }
    };

    return () => {
      socket.close();
    };
  }, [queryClient]);

  if (query.isLoading) {
    return <LoadingPanel text="Carregando dashboard operacional..." />;
  }

  if (query.isError || !query.data) {
    return (
      <EmptyState
        icon={AlertTriangle}
        title="Nao foi possivel carregar o dashboard operacional"
        description={getPermissionAwareMessage(query.error, "Tente novamente para recuperar os indicadores operacionais.")}
        action={{ label: "Tentar novamente", onClick: () => void query.refetch() }}
      />
    );
  }

  return (
    <section className="space-y-6">
      <header className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
        <div>
          <h2 className="font-heading text-3xl font-bold text-lovable-ink">Dashboard Operacional</h2>
          <p className="text-sm text-lovable-ink-muted">Check-ins em tempo real, heatmap por horario e inativos 7+ dias.</p>
          <p className="mt-1 flex items-center gap-1.5 text-xs text-lovable-ink-muted">
            <span
              className={`inline-block h-2 w-2 rounded-full ${
                isRealtimeConnected
                  ? "animate-pulse bg-lovable-success"
                  : "bg-lovable-ink-muted/40"
              }`}
            />
            {isRealtimeConnected ? "Tempo real: conectado" : "Tempo real: desconectado"}
            {realtimeEvents > 0 && (
              <span className="ml-1 rounded-full bg-lovable-primary/15 px-1.5 py-0.5 font-medium text-lovable-primary">
                {realtimeEvents} evento{realtimeEvents !== 1 ? "s" : ""}
              </span>
            )}
          </p>
        </div>
        <DashboardActions dashboard="operational" />
      </header>

      <AiInsightCard dashboard="operational" />

      <div className="grid gap-4 md:grid-cols-2">
        <StatCard label="Check-ins ultima hora" value={String(query.data.realtime_checkins)} tone="success" />
        <StatCard label="Inativos 7+ dias" value={String(query.data.inactive_7d_total)} tone="warning" />
      </div>

      <section className="rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
        <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
          <div>
            <h3 className="text-sm font-semibold uppercase tracking-wider text-lovable-ink-muted">Aniversariantes de hoje</h3>
            <p className="mt-1 text-sm text-lovable-ink-muted">
              Visibilidade rápida para contato, surpresa e validação da automação de aniversário.
            </p>
          </div>
          <Badge variant={query.data.birthday_today_total > 0 ? "warning" : "neutral"}>
            {query.data.birthday_today_total} hoje
          </Badge>
        </div>

        {query.data.birthday_today_items.length > 0 ? (
          <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {query.data.birthday_today_items.map((member) => (
              <div
                key={member.id}
                className="rounded-xl border border-lovable-border bg-lovable-surface-soft px-4 py-3"
              >
                <div className="flex items-center justify-between gap-3">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold text-lovable-ink">{member.full_name}</p>
                    <p className="truncate text-xs text-lovable-ink-muted">{member.plan_name}</p>
                  </div>
                  <span className="inline-flex h-9 w-9 items-center justify-center rounded-full bg-amber-400/12 text-amber-300">
                    <CalendarDays size={16} />
                  </span>
                </div>
                <div className="mt-3">
                  <QuickActions member={member} onActionComplete={handleActionComplete} />
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="mt-4 rounded-xl border border-dashed border-lovable-border px-4 py-4 text-sm text-lovable-ink-muted">
            Nenhum aniversariante hoje.
          </div>
        )}
      </section>

      <HeatmapGrid data={query.data.heatmap ?? []} />

      <section className="rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
        <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-lovable-ink-muted">Lista 7+ dias sem treino</h3>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="text-left text-xs uppercase tracking-wider text-lovable-ink-muted">
              <tr>
                <th className="px-2 py-2">Aluno</th>
                <th className="px-2 py-2">Risco</th>
                <th className="px-2 py-2">Ultimo check-in</th>
                <th className="px-2 py-2">Acoes</th>
              </tr>
            </thead>
            <tbody>
              {query.data.inactive_7d_items.map((member) => (
                <tr key={member.id} className="border-t border-lovable-border">
                  <td className="px-2 py-2 font-medium text-lovable-ink">{member.full_name}</td>
                  <td className="px-2 py-2">
                    <Badge variant={RISK_BADGE[member.risk_level as RiskLevel]}>
                      {RISK_LABELS[member.risk_level as RiskLevel] ?? member.risk_level}
                    </Badge>
                  </td>
                  <td className="px-2 py-2 text-lovable-ink-muted">{member.last_checkin_at ? new Date(member.last_checkin_at).toLocaleString() : "Sem registro"}</td>
                  <td className="px-2 py-2">
                    <QuickActions member={member} onActionComplete={handleActionComplete} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </section>
  );
}
