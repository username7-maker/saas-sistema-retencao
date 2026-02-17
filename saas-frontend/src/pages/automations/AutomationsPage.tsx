import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Zap, Play, Plus, ToggleLeft, ToggleRight, Trash2 } from "lucide-react";
import clsx from "clsx";

import { LoadingPanel } from "../../components/common/LoadingPanel";
import { automationService, type AutomationRule } from "../../services/automationService";

const TRIGGER_LABELS: Record<string, string> = {
  risk_level_change: "Mudanca de Risco",
  inactivity_days: "Dias Inativo",
  nps_score: "NPS Baixo",
  lead_stale: "Lead Parado",
  birthday: "Aniversario",
  checkin_streak: "Sequencia Check-in",
};

const ACTION_LABELS: Record<string, string> = {
  create_task: "Criar Tarefa",
  send_whatsapp: "Enviar WhatsApp",
  send_email: "Enviar Email",
  notify: "Notificar",
};

const ACTION_COLORS: Record<string, string> = {
  create_task: "bg-violet-100 text-violet-700",
  send_whatsapp: "bg-emerald-100 text-emerald-700",
  send_email: "bg-blue-100 text-blue-700",
  notify: "bg-amber-100 text-amber-700",
};

export function AutomationsPage() {
  const queryClient = useQueryClient();
  const [executing, setExecuting] = useState(false);

  const rulesQuery = useQuery({
    queryKey: ["automations", "rules"],
    queryFn: () => automationService.listRules(),
    staleTime: 30 * 1000,
  });

  const toggleMutation = useMutation({
    mutationFn: ({ id, is_active }: { id: string; is_active: boolean }) =>
      automationService.updateRule(id, { is_active }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["automations", "rules"] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => automationService.deleteRule(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["automations", "rules"] });
    },
  });

  const seedMutation = useMutation({
    mutationFn: () => automationService.seedDefaults(),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["automations", "rules"] });
    },
  });

  const handleExecuteAll = async () => {
    setExecuting(true);
    try {
      const results = await automationService.executeAll();
      const executed = results.filter((r) => r.status !== "skipped" && r.status !== "error").length;
      alert(`Automacoes executadas: ${executed} acoes realizadas de ${results.length} tentativas.`);
    } catch {
      alert("Erro ao executar automacoes.");
    } finally {
      setExecuting(false);
      void queryClient.invalidateQueries({ queryKey: ["automations", "rules"] });
    }
  };

  if (rulesQuery.isLoading) {
    return <LoadingPanel text="Carregando regras de automacao..." />;
  }

  const rules = rulesQuery.data ?? [];

  return (
    <section className="space-y-6">
      <header className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="font-heading text-3xl font-bold text-slate-900">Automacoes</h2>
          <p className="text-sm text-slate-500">Configure regras automaticas de retencao e engajamento.</p>
        </div>
        <div className="flex gap-2">
          {rules.length === 0 && (
            <button
              type="button"
              onClick={() => seedMutation.mutate()}
              disabled={seedMutation.isPending}
              className="flex items-center gap-1.5 rounded-full bg-brand-500 px-4 py-2 text-xs font-semibold uppercase tracking-wider text-white hover:bg-brand-600 disabled:opacity-50"
            >
              <Plus size={14} />
              Criar Regras Padrao
            </button>
          )}
          <button
            type="button"
            onClick={handleExecuteAll}
            disabled={executing || rules.length === 0}
            className="flex items-center gap-1.5 rounded-full bg-emerald-500 px-4 py-2 text-xs font-semibold uppercase tracking-wider text-white hover:bg-emerald-600 disabled:opacity-50"
          >
            <Play size={14} />
            {executing ? "Executando..." : "Executar Todas"}
          </button>
        </div>
      </header>

      {rules.length === 0 ? (
        <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-panel">
          <Zap size={48} className="mx-auto mb-4 text-slate-300" />
          <p className="text-lg font-semibold text-slate-600">Nenhuma regra configurada</p>
          <p className="mt-1 text-sm text-slate-400">
            Clique em "Criar Regras Padrao" para comecar com automacoes pre-configuradas.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {rules.map((rule) => (
            <RuleCard
              key={rule.id}
              rule={rule}
              onToggle={(active) => toggleMutation.mutate({ id: rule.id, is_active: active })}
              onDelete={() => {
                if (confirm(`Tem certeza que deseja excluir a regra "${rule.name}"?`)) {
                  deleteMutation.mutate(rule.id);
                }
              }}
              isToggling={toggleMutation.isPending}
            />
          ))}
        </div>
      )}

      <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-panel">
        <h3 className="mb-2 text-sm font-semibold uppercase tracking-wider text-slate-600">Como funciona</h3>
        <ul className="space-y-1 text-sm text-slate-500">
          <li>As regras sao executadas automaticamente apos o processamento diario de risco (2h UTC).</li>
          <li>Voce tambem pode executar manualmente clicando em "Executar Todas".</li>
          <li>Cada regra identifica alunos que atendem ao gatilho e executa a acao configurada.</li>
          <li>Tarefas duplicadas nao sao criadas (verificacao automatica).</li>
        </ul>
      </section>
    </section>
  );
}

function RuleCard({
  rule,
  onToggle,
  onDelete,
  isToggling,
}: {
  rule: AutomationRule;
  onToggle: (active: boolean) => void;
  onDelete: () => void;
  isToggling: boolean;
}) {
  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-4 shadow-panel">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold text-slate-700">{rule.name}</h3>
            <span className={clsx("rounded-full px-2 py-0.5 text-[10px] font-bold", ACTION_COLORS[rule.action_type] ?? "bg-slate-100 text-slate-600")}>
              {ACTION_LABELS[rule.action_type] ?? rule.action_type}
            </span>
            {!rule.is_active && (
              <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-bold text-slate-500">INATIVA</span>
            )}
          </div>
          {rule.description && <p className="mt-1 text-xs text-slate-500">{rule.description}</p>}
          <div className="mt-2 flex flex-wrap gap-3 text-[10px] text-slate-400 uppercase tracking-wider">
            <span>Gatilho: {TRIGGER_LABELS[rule.trigger_type] ?? rule.trigger_type}</span>
            <span>Execucoes: {rule.executions_count}</span>
            {rule.last_executed_at && (
              <span>Ultima: {new Date(rule.last_executed_at).toLocaleString()}</span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => onToggle(!rule.is_active)}
            disabled={isToggling}
            className="text-slate-400 hover:text-brand-500 disabled:opacity-50"
            title={rule.is_active ? "Desativar" : "Ativar"}
          >
            {rule.is_active ? <ToggleRight size={24} className="text-brand-500" /> : <ToggleLeft size={24} />}
          </button>
          <button
            type="button"
            onClick={onDelete}
            className="text-slate-300 hover:text-rose-500"
            title="Excluir regra"
          >
            <Trash2 size={16} />
          </button>
        </div>
      </div>
    </article>
  );
}
