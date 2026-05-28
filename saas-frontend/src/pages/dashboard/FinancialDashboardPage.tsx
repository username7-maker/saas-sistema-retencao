import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { LineSeriesChart } from "../../components/charts/LineSeriesChart";
import { getChartSeriesState } from "../../components/charts/chartState";
import { EmptyState, SectionHeader, SkeletonList } from "../../components/ui";
import { AiInsightCard } from "../../components/common/AiInsightCard";
import { DashboardActions } from "../../components/common/DashboardActions";
import { LoadingPanel } from "../../components/common/LoadingPanel";
import {
  Badge,
  Button,
  Card,
  CardContent,
  CommandCard,
  FormField,
  Input,
  MetricCard,
  PremiumEmptyState,
  Select,
  Textarea,
} from "../../components/ui2";
import { AlertTriangle, Banknote, CircleDollarSign, FileText, TrendingUp } from "lucide-react";
import { useFinancialDashboard } from "../../hooks/useDashboard";
import { financeService } from "../../services/financeService";
import type { FinancialEntryPayload, FinancialEntryStatus, FinancialEntryType } from "../../types";

const BRL = (value: number) =>
  new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 }).format(value);

const ENTRY_TYPE_LABEL: Record<FinancialEntryType, string> = {
  receivable: "Conta a receber",
  payable: "Conta a pagar",
  cash_in: "Entrada de caixa",
  cash_out: "Saída de caixa",
};

const STATUS_LABEL: Record<FinancialEntryStatus, string> = {
  open: "Aberto",
  paid: "Pago",
  overdue: "Atrasado",
  cancelled: "Cancelado",
};

function todayInputValue(): string {
  return new Date().toISOString().slice(0, 10);
}

export function FinancialDashboardPage() {
  const query = useFinancialDashboard();
  const queryClient = useQueryClient();
  const [form, setForm] = useState<FinancialEntryPayload>({
    entry_type: "receivable",
    status: "open",
    category: "mensalidade",
    amount: 0,
    due_date: todayInputValue(),
    description: "",
    notes: "",
  });

  const entriesQuery = useQuery({
    queryKey: ["finance", "entries", "recent"],
    queryFn: () => financeService.listEntries({ page_size: 12 }),
    staleTime: 60_000,
  });

  const delinquencySummaryQuery = useQuery({
    queryKey: ["finance", "delinquency", "summary"],
    queryFn: financeService.getDelinquencySummary,
    staleTime: 60_000,
  });

  const createEntryMutation = useMutation({
    mutationFn: financeService.createEntry,
    onSuccess: () => {
      toast.success("Lançamento financeiro registrado.");
      setForm({
        entry_type: "receivable",
        status: "open",
        category: "mensalidade",
        amount: 0,
        due_date: todayInputValue(),
        description: "",
        notes: "",
      });
      void queryClient.invalidateQueries({ queryKey: ["finance", "entries"] });
      void queryClient.invalidateQueries({ queryKey: ["dashboard", "financial"] });
    },
    onError: () => toast.error("Não foi possível registrar o lançamento financeiro."),
  });

  const materializeDelinquencyMutation = useMutation({
    mutationFn: financeService.materializeDelinquencyTasks,
    onSuccess: (result) => {
      toast.success(`Régua atualizada: ${result.created_count} criada(s), ${result.updated_count} atualizada(s).`);
      void queryClient.invalidateQueries({ queryKey: ["finance", "delinquency"] });
      void queryClient.invalidateQueries({ queryKey: ["work-queue"] });
      void queryClient.invalidateQueries({ queryKey: ["tasks"] });
    },
    onError: () => toast.error("Não foi possível atualizar a régua de inadimplência."),
  });

  function updateForm<K extends keyof FinancialEntryPayload>(key: K, value: FinancialEntryPayload[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  function handleCreateEntry(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!form.amount || form.amount <= 0) {
      toast.error("Informe um valor maior que zero.");
      return;
    }
    createEntryMutation.mutate({
      ...form,
      category: form.category || "geral",
      source: "manual",
      due_date: form.due_date || undefined,
      occurred_at: form.status === "paid" ? new Date().toISOString() : undefined,
      description: form.description?.trim() || undefined,
      notes: form.notes?.trim() || undefined,
    });
  }

  if (query.isLoading) {
    return <LoadingPanel text="Carregando dashboard financeiro..." />;
  }

  if (!query.data) {
    return (
      <section className="space-y-6">
        <header>
          <h2 className="font-heading text-3xl font-bold text-lovable-ink">Dashboard Financeiro</h2>
          <p className="text-sm text-lovable-ink-muted">Receita mensal, inadimplência e projeção 3/6/12 meses.</p>
        </header>
        <div className="rounded-2xl border border-dashed border-lovable-border bg-lovable-surface p-8 text-center text-sm text-lovable-ink-muted">
          Sem dados financeiros disponíveis. Importe histórico de receita para ativar este painel.
        </div>
      </section>
    );
  }

  const proj12 = query.data.projections.find((projection) => projection.horizon_months === 12);
  const revenueState = getChartSeriesState(query.data.monthly_revenue, ["value"]);
  const hasFinancialBase = revenueState.hasMeaningfulValues;
  const flags = query.data.data_quality_flags ?? [];
  const dailyNetCash = query.data.daily_net_cash ?? 0;
  const openReceivables = query.data.open_receivables ?? 0;
  const openPayables = query.data.open_payables ?? 0;
  const overdueReceivables = query.data.overdue_receivables ?? 0;
  const revenueAtRisk = query.data.revenue_at_risk ?? 0;

  return (
    <section className="space-y-6">
      <header className="flex flex-col gap-4 rounded-[28px] border border-lovable-border/70 bg-[linear-gradient(135deg,hsl(var(--lovable-surface)/0.96),hsl(var(--lovable-bg-muted)/0.78))] p-5 shadow-panel md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-[11px] font-bold uppercase tracking-[0.3em] text-lovable-ink-muted">Financeiro</p>
          <h2 className="mt-2 font-heading text-3xl font-bold text-lovable-ink">Dashboard Financeiro</h2>
          <p className="mt-1 text-sm text-lovable-ink-muted">Receita mensal, inadimplência, caixa e projeção operacional.</p>
        </div>
        <DashboardActions dashboard="financial" />
      </header>

      <AiInsightCard dashboard="financial" />

      {flags.length > 0 ? (
        <Card>
          <CardContent className="pt-5">
            <SectionHeader
              title="Qualidade da base financeira"
              subtitle="O painel diferencia dados reais de falta de importação para evitar decisão com número falso."
            />
            <div className="mt-3 flex flex-wrap gap-2">
              {flags.map((flag) => (
                <Badge key={flag} variant="warning">{flag}</Badge>
              ))}
            </div>
          </CardContent>
        </Card>
      ) : null}

      <div className="grid gap-4 md:grid-cols-4">
        <MetricCard label="Inadimplência" value={`${query.data.delinquency_rate.toFixed(1)}%`} subtitle="Alunos com cobrança em atraso" icon={AlertTriangle} tone="danger" />
        <MetricCard label="Caixa líquido hoje" value={BRL(dailyNetCash)} subtitle="Resultado do dia" icon={CircleDollarSign} tone={dailyNetCash >= 0 ? "success" : "danger"} />
        <MetricCard label="Recebíveis abertos" value={BRL(openReceivables)} subtitle="Entradas ainda pendentes" icon={Banknote} tone="warning" />
        <MetricCard label="Receita em risco" value={BRL(revenueAtRisk)} subtitle="MRR sob atenção financeira" icon={TrendingUp} tone="danger" />
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <MetricCard label="DRE: Receita do mês" value={BRL(query.data.dre_basic?.revenue ?? 0)} subtitle="Receita reconhecida" icon={CircleDollarSign} tone="success" />
        <MetricCard label="DRE: Despesas do mês" value={BRL(query.data.dre_basic?.expenses ?? 0)} subtitle="Saídas reconhecidas" icon={FileText} tone="warning" />
        <MetricCard label="DRE: Resultado" value={BRL(query.data.dre_basic?.net_result ?? 0)} subtitle="Resultado operacional" icon={TrendingUp} tone={(query.data.dre_basic?.net_result ?? 0) >= 0 ? "success" : "danger"} />
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <MetricCard label="A receber atrasado" value={BRL(overdueReceivables)} subtitle="Valor vencido" icon={AlertTriangle} tone="danger" />
        <MetricCard label="A pagar aberto" value={BRL(openPayables)} subtitle="Compromissos pendentes" icon={Banknote} tone="warning" />
        <MetricCard
          label="Projeção 12 meses"
          value={proj12 && hasFinancialBase ? BRL(proj12.projected_revenue) : "Sem base"}
          subtitle="Forecast financeiro"
          icon={TrendingUp}
          tone="success"
        />
      </div>

      <Card>
        <CardContent className="pt-5">
          <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
            <SectionHeader
              title="Regua de inadimplencia"
              subtitle="Rotina operacional para transformar recebíveis vencidos em tasks de cobrança assistida."
            />
            <Button
              size="sm"
              variant="secondary"
              onClick={() => materializeDelinquencyMutation.mutate()}
              disabled={materializeDelinquencyMutation.isPending}
            >
              {materializeDelinquencyMutation.isPending ? "Atualizando..." : "Atualizar régua"}
            </Button>
          </div>
          {delinquencySummaryQuery.isLoading ? (
            <div className="mt-4"><SkeletonList rows={2} cols={4} /></div>
          ) : delinquencySummaryQuery.isError ? (
            <div className="mt-4 rounded-xl border border-lovable-danger/40 bg-lovable-danger/10 p-4 text-sm text-lovable-danger">
              Erro ao carregar a régua. Isso não significa ausência de inadimplência.
            </div>
          ) : delinquencySummaryQuery.data ? (
            <div className="mt-4 space-y-4">
              <div className="grid gap-3 md:grid-cols-4">
                <MetricCard label="Valor vencido" value={BRL(delinquencySummaryQuery.data.overdue_amount)} icon={AlertTriangle} tone="danger" />
                <MetricCard label="Alunos inadimplentes" value={String(delinquencySummaryQuery.data.delinquent_members_count)} icon={Banknote} tone="warning" />
                <MetricCard label="Tasks abertas" value={String(delinquencySummaryQuery.data.open_task_count)} icon={FileText} tone="neutral" />
                <MetricCard label="Recuperado 30 dias" value={BRL(delinquencySummaryQuery.data.recovered_30d)} icon={TrendingUp} tone="success" />
              </div>
              <div className="grid gap-2 md:grid-cols-5">
                {delinquencySummaryQuery.data.by_stage.map((stage) => (
                  <article key={stage.stage} className="rounded-xl border border-lovable-border bg-lovable-surface-soft/45 p-3">
                    <p className="text-xs font-semibold uppercase tracking-[0.2em] text-lovable-ink-muted">{stage.label}</p>
                    <p className="mt-2 text-lg font-bold text-lovable-ink">{stage.members_count}</p>
                    <p className="text-xs text-lovable-ink-muted">{BRL(stage.overdue_amount)}</p>
                  </article>
                ))}
              </div>
            </div>
          ) : (
            <EmptyState
              title="Sem dados de inadimplência"
              description="Quando houver recebíveis vencidos de alunos ativos, a régua mostrará estágios e tasks abertas."
            />
          )}
        </CardContent>
      </Card>

      <Card>
        <CardContent className="pt-5">
          <SectionHeader
            title="Registrar lançamento"
            subtitle="Use para contas a receber, contas a pagar e caixa diário. Não substitui integração bancária."
          />
          <form onSubmit={handleCreateEntry} className="mt-4 grid gap-4 lg:grid-cols-[1fr_1fr_1fr_1fr]">
            <FormField label="Tipo">
              <Select
                value={form.entry_type}
                onChange={(event) => updateForm("entry_type", event.target.value as FinancialEntryType)}
              >
                {Object.entries(ENTRY_TYPE_LABEL).map(([value, label]) => (
                  <option key={value} value={value}>{label}</option>
                ))}
              </Select>
            </FormField>
            <FormField label="Status">
              <Select
                value={form.status}
                onChange={(event) => updateForm("status", event.target.value as FinancialEntryStatus)}
              >
                {Object.entries(STATUS_LABEL).map(([value, label]) => (
                  <option key={value} value={value}>{label}</option>
                ))}
              </Select>
            </FormField>
            <FormField label="Categoria">
              <Input
                value={form.category}
                onChange={(event) => updateForm("category", event.target.value)}
                placeholder="mensalidade, aluguel, folha..."
              />
            </FormField>
            <FormField label="Valor">
              <Input
                type="number"
                min={0}
                step={0.01}
                value={form.amount}
                onChange={(event) => updateForm("amount", Number(event.target.value))}
              />
            </FormField>
            <FormField label="Vencimento">
              <Input
                type="date"
                value={form.due_date ?? ""}
                onChange={(event) => updateForm("due_date", event.target.value)}
              />
            </FormField>
            <div className="lg:col-span-2">
              <FormField label="Descricao">
                <Input
                  value={form.description ?? ""}
                  onChange={(event) => updateForm("description", event.target.value)}
                  placeholder="Ex: mensalidade abril, aluguel, fornecedor..."
                />
              </FormField>
            </div>
            <div className="lg:col-span-4">
              <FormField label="Observação">
                <Textarea
                  value={form.notes ?? ""}
                  onChange={(event) => updateForm("notes", event.target.value)}
                  rows={2}
                  placeholder="Contexto operacional para a gestão."
                />
              </FormField>
            </div>
            <div className="lg:col-span-4 flex justify-end">
              <Button type="submit" variant="primary" disabled={createEntryMutation.isPending}>
                {createEntryMutation.isPending ? "Salvando..." : "Salvar lançamento"}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      {hasFinancialBase ? (
        <LineSeriesChart data={query.data.monthly_revenue} xKey="month" yKey="value" />
      ) : (
        <CommandCard>
          <PremiumEmptyState
            title="Receita histórica ainda sem base útil"
            description="As mensalidades e recebimentos ainda não geraram uma série financeira confiável. Assim que a base financeira for consolidada, o gráfico passa a mostrar a curva mensal."
          />
        </CommandCard>
      )}

      <section className="rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
        <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-lovable-ink-muted">Projeções inteligentes</h3>
        <div className="grid gap-3 md:grid-cols-3">
          {query.data.projections.map((projection) => (
            <article
              key={projection.horizon_months}
              className="rounded-xl border border-lovable-border bg-lovable-surface-soft p-3"
            >
              <p className="text-xs uppercase tracking-wider text-lovable-ink-muted">Horizonte</p>
              <p className="text-lg font-semibold text-lovable-ink">{projection.horizon_months} meses</p>
              <p className="text-sm font-medium text-lovable-primary">
                {hasFinancialBase ? BRL(projection.projected_revenue) : "Sem base"}
              </p>
            </article>
          ))}
        </div>
      </section>

      <Card>
        <CardContent className="pt-5">
          <SectionHeader title="Lançamentos recentes" subtitle="Últimos registros usados pela foundation financeira." />
          {entriesQuery.isLoading ? (
            <div className="mt-4"><SkeletonList rows={5} cols={4} /></div>
          ) : entriesQuery.data?.items.length ? (
            <div className="mt-4 space-y-2">
              {entriesQuery.data.items.map((entry) => (
                <article
                  key={entry.id}
                  className="grid gap-3 rounded-xl border border-lovable-border bg-lovable-surface-soft/35 px-4 py-3 md:grid-cols-[1.2fr_1fr_1fr_auto]"
                >
                  <div>
                    <p className="text-sm font-semibold text-lovable-ink">{entry.description || entry.category}</p>
                    <p className="text-xs text-lovable-ink-muted">{ENTRY_TYPE_LABEL[entry.entry_type as FinancialEntryType] ?? entry.entry_type}</p>
                  </div>
                  <div>
                    <p className="text-xs uppercase tracking-widest text-lovable-ink-muted">Vencimento</p>
                    <p className="text-sm text-lovable-ink">{entry.due_date ? new Date(`${entry.due_date}T00:00:00`).toLocaleDateString("pt-BR") : "Sem data"}</p>
                  </div>
                  <div>
                    <p className="text-xs uppercase tracking-widest text-lovable-ink-muted">Valor</p>
                    <p className="text-sm font-semibold text-lovable-ink">{BRL(Number(entry.amount))}</p>
                  </div>
                  <div className="flex items-center justify-start md:justify-end">
                    <Badge variant={entry.status === "paid" ? "success" : entry.status === "overdue" ? "danger" : "warning"}>
                      {STATUS_LABEL[entry.status as FinancialEntryStatus] ?? entry.status}
                    </Badge>
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <EmptyState
              title="Nenhum lançamento financeiro registrado"
              description="Registre recebíveis, pagáveis ou caixa para transformar o dashboard financeiro em base real."
            />
          )}
        </CardContent>
      </Card>
    </section>
  );
}
