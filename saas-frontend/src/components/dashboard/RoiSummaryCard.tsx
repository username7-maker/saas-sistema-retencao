import { DollarSign, TrendingUp, Users } from "lucide-react";

import { useRoiSummary } from "../../hooks/useDashboard";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui2";
import { Skeleton } from "../ui2/Skeleton";

export function RoiSummaryCard() {
  const { data, isLoading } = useRoiSummary(30);

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-4 w-40" />
        </CardHeader>
        <CardContent>
          <Skeleton className="h-20 w-full" />
        </CardContent>
      </Card>
    );
  }

  const hasData = Boolean(data && data.actions_executed > 0);

  return (
    <Card className="border border-lovable-border bg-[linear-gradient(135deg,hsl(var(--lovable-surface)),hsl(var(--lovable-surface-soft)))]">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-xl">
          <TrendingUp size={18} className="text-lovable-primary" />
          ROI operacional
        </CardTitle>
        <CardDescription>
          Estimativa operacional de recuperacao e receita preservada nos ultimos 30 dias
        </CardDescription>
      </CardHeader>
      <CardContent>
        {hasData && data ? (
          <div className="space-y-4">
            <div className="grid grid-cols-3 gap-4">
              <div className="text-center">
                <p className="text-2xl font-bold text-lovable-ink">
                  {new Intl.NumberFormat("pt-BR", {
                    style: "currency",
                    currency: "BRL",
                    maximumFractionDigits: 0,
                  }).format(data.preserved_revenue)}
                </p>
                <p className="flex items-center justify-center gap-1 text-xs text-lovable-ink-muted">
                  <DollarSign size={12} /> Receita preservada
                </p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-lovable-ink">{data.actions_executed}</p>
                <p className="flex items-center justify-center gap-1 text-xs text-lovable-ink-muted">
                  <Users size={12} /> Acoes executadas
                </p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-lovable-ink">{data.recovery_rate}%</p>
                <p className="text-xs text-lovable-ink-muted">Taxa de recuperacao</p>
              </div>
            </div>

            <div className="grid gap-3 md:grid-cols-3">
              <MiniRanking
                label="Top playbook"
                value={data.top_playbooks[0]?.playbook_key ?? "Sem dados"}
                helper={data.top_playbooks[0] ? `${data.top_playbooks[0].recovered_members} recuperados` : "Aguardando outcomes"}
              />
              <MiniRanking
                label="Top canal"
                value={data.top_channels[0]?.channel ?? "Sem dados"}
                helper={data.top_channels[0] ? `${data.top_channels[0].actions_executed} acoes` : "Aguardando outcomes"}
              />
              <MiniRanking
                label="Top operador"
                value={data.top_operators[0]?.label ?? "Sistema"}
                helper={data.top_operators[0] ? `${data.top_operators[0].recovered_members} recuperados` : "Sem operador dominante"}
              />
            </div>
          </div>
        ) : (
          <p className="text-sm text-lovable-ink-muted">
            O ROI operacional aparece quando a equipe comeca a gerar outcomes e reengajamentos rastreados.
            Use o Action Center para alimentar essa camada.
          </p>
        )}
      </CardContent>
    </Card>
  );
}

function MiniRanking({ label, value, helper }: { label: string; value: string; helper: string }) {
  return (
    <div className="rounded-xl border border-lovable-border bg-lovable-surface-soft px-3 py-2">
      <p className="text-[11px] uppercase tracking-[0.2em] text-lovable-ink-muted">{label}</p>
      <p className="mt-2 truncate text-sm font-semibold text-lovable-ink">{value}</p>
      <p className="mt-1 text-xs text-lovable-ink-muted">{helper}</p>
    </div>
  );
}
