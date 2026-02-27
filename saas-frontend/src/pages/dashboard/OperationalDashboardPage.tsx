import { useEffect, useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { BarSeriesChart } from "../../components/charts/BarSeriesChart";
import { DashboardActions } from "../../components/common/DashboardActions";
import { LoadingPanel } from "../../components/common/LoadingPanel";
import { QuickActions } from "../../components/common/QuickActions";
import { StatCard } from "../../components/common/StatCard";
import { useOperationalDashboard } from "../../hooks/useDashboard";
import { tokenStorage } from "../../services/storage";

const weekdays = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sab"];

export function OperationalDashboardPage() {
  const queryClient = useQueryClient();
  const [isRealtimeConnected, setIsRealtimeConnected] = useState(false);
  const [realtimeEvents, setRealtimeEvents] = useState(0);
  const query = useOperationalDashboard();

  const heatmapData = useMemo(
    () =>
      (query.data?.heatmap ?? []).map((point) => ({
        slot: `${weekdays[point.weekday]} ${String(point.hour_bucket).padStart(2, "0")}h`,
        total: point.total_checkins,
      })),
    [query.data],
  );

  const handleActionComplete = () => {
    void queryClient.invalidateQueries({ queryKey: ["dashboard", "operational"] });
  };

  useEffect(() => {
    const token = tokenStorage.getAccessToken();
    if (!token) return;

    const apiBase = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";
    const wsBase = (import.meta.env.VITE_WS_BASE_URL as string | undefined) ?? apiBase.replace(/^http/, "ws");
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

  if (!query.data) {
    return <LoadingPanel text="Sem dados operacionais disponiveis." />;
  }

  return (
    <section className="space-y-6">
      <header className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
        <div>
          <h2 className="font-heading text-3xl font-bold text-lovable-ink">Dashboard Operacional</h2>
          <p className="text-sm text-lovable-ink-muted">Check-ins em tempo real, heatmap por horario e inativos 7+ dias.</p>
          <p className="mt-1 text-xs text-lovable-ink-muted">
            Tempo real: {isRealtimeConnected ? "conectado" : "desconectado"} | eventos: {realtimeEvents}
          </p>
        </div>
        <DashboardActions dashboard="operational" />
      </header>

      <div className="grid gap-4 md:grid-cols-2">
        <StatCard label="Check-ins ultima hora" value={String(query.data.realtime_checkins)} tone="success" />
        <StatCard label="Inativos 7+ dias" value={String(query.data.inactive_7d_total)} tone="warning" />
      </div>

      <BarSeriesChart data={heatmapData} xKey="slot" yKey="total" />

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
                  <td className="px-2 py-2 uppercase text-lovable-ink-muted">{member.risk_level}</td>
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
