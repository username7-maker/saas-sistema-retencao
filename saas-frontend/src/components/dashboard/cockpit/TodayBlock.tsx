import { RefreshCw } from "lucide-react";

import { useDailyCockpit, useWeeklyFunnel } from "../../../hooks/useCockpit";
import type { DailyCockpitResponse, FunnelStage, WeeklyFunnelResponse } from "../../../types/cockpit";
import { CommandCard, PremiumSkeleton, SectionHeader, StatusPill } from "../../ui2";
import { ActionsTodayPanel } from "./ActionsTodayPanel";
import { AttentionPanel } from "./AttentionPanel";
import { FollowupsPanel } from "./FollowupsPanel";
import { WeeklyFunnelPanel } from "./WeeklyFunnelPanel";

const emptyStage = (key: string, label: string): FunnelStage => ({
  key,
  label,
  value: 0,
  previous_value: 0,
});

function finiteNumber(value: unknown, fallback = 0): number {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

function normalizeStage(stage: FunnelStage | undefined, key: string, label: string): FunnelStage {
  return {
    key: stage?.key ?? key,
    label: stage?.label ?? label,
    value: finiteNumber(stage?.value),
    previous_value: finiteNumber(stage?.previous_value),
  };
}

function normalizeDailyCockpit(data: DailyCockpitResponse | undefined): DailyCockpitResponse | null {
  if (!data) return null;

  const leadsFollowup = Array.isArray(data.leads_followup) ? data.leads_followup : [];
  const membersAttention = Array.isArray(data.members_attention) ? data.members_attention : [];
  const actionsToday = Array.isArray(data.actions_today) ? data.actions_today : [];
  const counts = data.counts ?? {
    leads_followup: leadsFollowup.length,
    members_attention: membersAttention.length,
    actions_today: actionsToday.length,
  };

  return {
    generated_at: data.generated_at ?? new Date().toISOString(),
    leads_followup: leadsFollowup,
    members_attention: membersAttention,
    actions_today: actionsToday,
    triage_pending_count: finiteNumber(data.triage_pending_count),
    counts: {
      leads_followup: finiteNumber(counts.leads_followup, leadsFollowup.length),
      members_attention: finiteNumber(counts.members_attention, membersAttention.length),
      actions_today: finiteNumber(counts.actions_today, actionsToday.length),
    },
  };
}

function normalizeWeeklyFunnel(data: WeeklyFunnelResponse | undefined): WeeklyFunnelResponse | null {
  if (!data) return null;

  return {
    week_start: data.week_start ?? "",
    week_end: data.week_end ?? "",
    week_offset: finiteNumber(data.week_offset),
    contacts: normalizeStage(data.contacts ?? emptyStage("contacts", "Contatos"), "contacts", "Contatos"),
    responses: normalizeStage(data.responses ?? emptyStage("responses", "Respostas"), "responses", "Respostas"),
    conversions: normalizeStage(data.conversions ?? emptyStage("conversions", "Conversoes"), "conversions", "Conversoes"),
    conversion_breakdown: {
      leads_won: finiteNumber(data.conversion_breakdown?.leads_won),
      members_joined: finiteNumber(data.conversion_breakdown?.members_joined),
      risk_recovered: finiteNumber(data.conversion_breakdown?.risk_recovered),
    },
  };
}

function PanelError({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="flex min-h-[180px] flex-col items-center justify-center gap-3 rounded-[24px] border border-dashed border-lovable-border bg-lovable-surface/50 p-4 text-center">
      <p className="text-sm text-lovable-ink-muted">{message}</p>
      <button
        type="button"
        onClick={onRetry}
        className="flex items-center gap-2 rounded-xl border border-lovable-border px-3 py-1.5 text-xs font-semibold text-lovable-ink transition hover:border-lovable-border-strong/70 hover:bg-lovable-surface-soft/62"
      >
        <RefreshCw size={13} /> Tentar de novo
      </button>
    </div>
  );
}

export function TodayBlock() {
  const daily = useDailyCockpit();
  const funnel = useWeeklyFunnel();
  const dailyData = normalizeDailyCockpit(daily.data);
  const funnelData = normalizeWeeklyFunnel(funnel.data);

  const generatedAt = dailyData
    ? new Date(dailyData.generated_at).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })
    : null;

  return (
    <CommandCard variant="elevated">
      <SectionHeader
        eyebrow="Hoje"
        title="Rotina comercial do dia"
        subtitle="Leads esperando resposta, alunos em atenção, ações do dia e o resultado da semana — sem planilha."
        actions={generatedAt ? <StatusPill tone="sync">Atualizado às {generatedAt}</StatusPill> : undefined}
      />
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-4">
        {daily.isLoading ? (
          <>
            <PremiumSkeleton className="h-[220px]" />
            <PremiumSkeleton className="h-[220px]" />
            <PremiumSkeleton className="h-[220px]" />
          </>
        ) : daily.isError || !dailyData ? (
          <div className="xl:col-span-3">
            <PanelError message="Não foi possível carregar a rotina do dia." onRetry={() => daily.refetch()} />
          </div>
        ) : (
          <>
            <FollowupsPanel items={dailyData.leads_followup} total={dailyData.counts.leads_followup} />
            <AttentionPanel items={dailyData.members_attention} total={dailyData.counts.members_attention} />
            <ActionsTodayPanel
              items={dailyData.actions_today}
              total={dailyData.counts.actions_today}
              triagePendingCount={dailyData.triage_pending_count}
            />
          </>
        )}
        {funnel.isLoading ? (
          <PremiumSkeleton className="h-[220px]" />
        ) : funnel.isError || !funnelData ? (
          <PanelError message="Não foi possível carregar o funil da semana." onRetry={() => funnel.refetch()} />
        ) : (
          <WeeklyFunnelPanel funnel={funnelData} />
        )}
      </div>
    </CommandCard>
  );
}
