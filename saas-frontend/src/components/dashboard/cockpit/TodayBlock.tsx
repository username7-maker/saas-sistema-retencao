import { RefreshCw } from "lucide-react";

import { useDailyCockpit, useWeeklyFunnel } from "../../../hooks/useCockpit";
import { CommandCard, PremiumSkeleton, SectionHeader, StatusPill } from "../../ui2";
import { ActionsTodayPanel } from "./ActionsTodayPanel";
import { AttentionPanel } from "./AttentionPanel";
import { FollowupsPanel } from "./FollowupsPanel";
import { WeeklyFunnelPanel } from "./WeeklyFunnelPanel";

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

  const generatedAt = daily.data
    ? new Date(daily.data.generated_at).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })
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
        ) : daily.isError || !daily.data ? (
          <div className="xl:col-span-3">
            <PanelError message="Não foi possível carregar a rotina do dia." onRetry={() => daily.refetch()} />
          </div>
        ) : (
          <>
            <FollowupsPanel items={daily.data.leads_followup} total={daily.data.counts.leads_followup} />
            <AttentionPanel items={daily.data.members_attention} total={daily.data.counts.members_attention} />
            <ActionsTodayPanel
              items={daily.data.actions_today}
              total={daily.data.counts.actions_today}
              triagePendingCount={daily.data.triage_pending_count}
            />
          </>
        )}
        {funnel.isLoading ? (
          <PremiumSkeleton className="h-[220px]" />
        ) : funnel.isError || !funnel.data ? (
          <PanelError message="Não foi possível carregar o funil da semana." onRetry={() => funnel.refetch()} />
        ) : (
          <WeeklyFunnelPanel funnel={funnel.data} />
        )}
      </div>
    </CommandCard>
  );
}
