import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Activity, AlertTriangle, CalendarDays, Clock } from "lucide-react";

import { HeatmapGrid } from "../../components/charts/HeatmapGrid";
import { AiInsightCard } from "../../components/common/AiInsightCard";
import { DashboardActions } from "../../components/common/DashboardActions";
import { LoadingPanel } from "../../components/common/LoadingPanel";
import { QuickActions } from "../../components/common/QuickActions";
import { EmptyState } from "../../components/ui";
import {
  CommandCard,
  MetricCard,
  PremiumEmptyState,
  PremiumTable,
  PremiumTableBody,
  PremiumTableCell,
  PremiumTableHead,
  PremiumTableHeader,
  PremiumTableRow,
  SectionHeader,
  StatusPill,
} from "../../components/ui2";
import { useOperationalDashboard } from "../../hooks/useDashboard";
import { WS_BASE_URL } from "../../services/runtimeConfig";
import { tokenStorage } from "../../services/storage";
import type { RiskLevel } from "../../types";
import { getPermissionAwareMessage } from "../../utils/httpErrors";

const RISK_LABELS: Record<RiskLevel, string> = {
  red: "Alto",
  yellow: "Médio",
  green: "Baixo",
};

const RISK_TONE: Record<RiskLevel, "danger" | "warning" | "success"> = {
  red: "danger",
  yellow: "warning",
  green: "success",
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

    const wsUrl = `${WS_BASE_URL.replace(/\/$/, "")}/ws/updates`;
    const socket = new WebSocket(wsUrl);

    socket.onopen = () => {
      socket.send(JSON.stringify({ type: "auth", token }));
    };
    socket.onclose = () => setIsRealtimeConnected(false);
    socket.onerror = () => setIsRealtimeConnected(false);
    socket.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data) as { event?: string };
        if (message.event === "connected") {
          setIsRealtimeConnected(true);
          return;
        }
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
        title="Não foi possível carregar o dashboard operacional"
        description={getPermissionAwareMessage(query.error, "Tente novamente para recuperar os indicadores operacionais.")}
        action={{ label: "Tentar novamente", onClick: () => void query.refetch() }}
      />
    );
  }

  return (
    <section className="space-y-6">
      <CommandCard variant="elevated">
        <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-[11px] font-bold uppercase tracking-[0.3em] text-blue-400">Operação</p>
            <h2 className="mt-2 font-heading text-3xl font-bold md:text-4xl">
              <span className="bg-gradient-to-r from-white via-white to-blue-300 bg-clip-text text-transparent">
                Dashboard Operacional
              </span>
            </h2>
            <p className="mt-1 text-sm text-lovable-ink-muted">Check-ins em tempo real, mapa por horário e alunos inativos há 7+ dias.</p>
            <p className="mt-2 flex items-center gap-1.5 text-xs text-lovable-ink-muted">
              <span className={`inline-block h-2 w-2 rounded-full ${isRealtimeConnected ? "animate-pulse bg-lovable-success" : "bg-lovable-ink-muted/40"}`} />
              {isRealtimeConnected ? "Tempo real: conectado" : "Tempo real: desconectado"}
              {realtimeEvents > 0 ? (
                <span className="ml-1 rounded-full bg-[rgba(59,130,246,0.15)] px-1.5 py-0.5 font-medium text-blue-300">
                  {realtimeEvents} evento{realtimeEvents !== 1 ? "s" : ""}
                </span>
              ) : null}
            </p>
          </div>
          <DashboardActions dashboard="operational" />
        </div>
      </CommandCard>

      <AiInsightCard dashboard="operational" />

      <div className="grid gap-4 md:grid-cols-2">
        <MetricCard
          label="Check-ins em tempo real"
          value={String(query.data.realtime_checkins)}
          subtitle="Movimento registrado na operação"
          trend={isRealtimeConnected ? "websocket conectado" : "modo consulta"}
          trendDirection={isRealtimeConnected ? "up" : "flat"}
          icon={Activity}
          tone="success"
          className="stagger-1"
        />
        <MetricCard
          label="Inativos 7+ dias"
          value={String(query.data.inactive_7d_total)}
          subtitle="Fila operacional de atenção"
          trend={query.data.inactive_7d_total > 0 ? "precisa ação" : "sem fila crítica"}
          trendDirection={query.data.inactive_7d_total > 0 ? "down" : "up"}
          icon={Clock}
          tone={query.data.inactive_7d_total > 0 ? "warning" : "success"}
          className="stagger-2"
        />
      </div>

      <CommandCard>
        <SectionHeader
          title="Aniversariantes de hoje"
          subtitle="Visibilidade rápida para contato, surpresa e validação da automação de aniversário."
          actions={<StatusPill tone={query.data.birthday_today_total > 0 ? "warning" : "neutral"}>{query.data.birthday_today_total} hoje</StatusPill>}
        />

        {query.data.birthday_today_items.length > 0 ? (
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {query.data.birthday_today_items.map((member) => (
              <div key={member.id} className="rounded-[20px] border border-lovable-border/70 bg-lovable-surface/58 px-4 py-3">
                <div className="flex items-center justify-between gap-3">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold text-lovable-ink">{member.full_name}</p>
                    <p className="truncate text-xs text-lovable-ink-muted">{member.plan_name}</p>
                  </div>
                  <span className="inline-flex h-9 w-9 items-center justify-center rounded-full bg-lovable-warning/12 text-lovable-warning">
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
          <PremiumEmptyState
            icon={CalendarDays}
            title="Nenhum aniversariante hoje"
            description="A operação não tem ação de relacionamento por aniversário neste recorte."
            className="min-h-[150px]"
          />
        )}
      </CommandCard>

      <HeatmapGrid data={query.data.heatmap ?? []} />

      <CommandCard>
        <SectionHeader title="Lista 7+ dias sem treino" subtitle="Alunos que precisam de leitura operacional antes de virar problema de retenção." />
        {query.data.inactive_7d_items.length > 0 ? (
          <PremiumTable>
            <PremiumTableHead>
              <PremiumTableRow>
                <PremiumTableHeader>Aluno</PremiumTableHeader>
                <PremiumTableHeader>Risco</PremiumTableHeader>
                <PremiumTableHeader>Último check-in</PremiumTableHeader>
                <PremiumTableHeader>Ações</PremiumTableHeader>
              </PremiumTableRow>
            </PremiumTableHead>
            <PremiumTableBody>
              {query.data.inactive_7d_items.map((member) => {
                const riskLevel = member.risk_level as RiskLevel;
                return (
                  <PremiumTableRow key={member.id}>
                    <PremiumTableCell className="font-medium text-lovable-ink">{member.full_name}</PremiumTableCell>
                    <PremiumTableCell>
                      <StatusPill tone={RISK_TONE[riskLevel]}>{RISK_LABELS[riskLevel] ?? member.risk_level}</StatusPill>
                    </PremiumTableCell>
                    <PremiumTableCell className="text-lovable-ink-muted">
                      {member.last_checkin_at ? new Date(member.last_checkin_at).toLocaleString("pt-BR") : "Sem registro"}
                    </PremiumTableCell>
                    <PremiumTableCell>
                      <QuickActions member={member} onActionComplete={handleActionComplete} />
                    </PremiumTableCell>
                  </PremiumTableRow>
                );
              })}
            </PremiumTableBody>
          </PremiumTable>
        ) : (
          <PremiumEmptyState
            icon={Activity}
            title="Nenhum aluno inativo há 7+ dias"
            description="A frequência está saudável neste recorte operacional."
          />
        )}
      </CommandCard>
    </section>
  );
}
