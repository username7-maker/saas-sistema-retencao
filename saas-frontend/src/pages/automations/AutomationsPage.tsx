import { useState } from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Zap, Play, Plus, ToggleLeft, ToggleRight, Trash2 } from "lucide-react";
import toast from "react-hot-toast";
import clsx from "clsx";

import { LoadingPanel } from "../../components/common/LoadingPanel";
import { automationService, type AutomationRule } from "../../services/automationService";
import { Button, Drawer, Input } from "../../components/ui2";

// ─── Constants ────────────────────────────────────────────────────────────────

const TRIGGER_LABELS: Record<string, string> = {
  risk_level_change: "Mudança de Risco",
  inactivity_days: "Dias Inativo",
  nps_score: "NPS Baixo",
  lead_stale: "Lead Parado",
  birthday: "Aniversário",
  checkin_streak: "Sequência Check-in",
};

const ACTION_LABELS: Record<string, string> = {
  create_task: "Criar Tarefa",
  send_whatsapp: "Enviar WhatsApp",
  send_email: "Enviar E-mail",
  notify: "Notificar",
};

const ACTION_COLORS: Record<string, string> = {
  create_task: "bg-violet-100 text-violet-700",
  send_whatsapp: "bg-emerald-100 text-emerald-700",
  send_email: "bg-blue-100 text-blue-700",
  notify: "bg-amber-100 text-amber-700",
};

const TRIGGER_OPTIONS = Object.entries(TRIGGER_LABELS).map(([value, label]) => ({ value, label }));
const ACTION_OPTIONS = Object.entries(ACTION_LABELS).map(([value, label]) => ({ value, label }));

// ─── Rule form schema ─────────────────────────────────────────────────────────

const ruleSchema = z.object({
  name: z.string().min(3, "Nome deve ter pelo menos 3 caracteres"),
  description: z.string().optional(),
  trigger_type: z.string().min(1, "Selecione um gatilho"),
  threshold_value: z.coerce.number().min(0).optional(),
  action_type: z.string().min(1, "Selecione uma ação"),
  message: z.string().optional(),
  is_active: z.boolean().default(true),
});

type RuleFormValues = z.infer<typeof ruleSchema>;

// ─── Helper — build trigger_config and action_config from flat form ───────────

function buildTriggerConfig(values: RuleFormValues): Record<string, unknown> {
  const n = values.threshold_value ?? 7;
  switch (values.trigger_type) {
    case "inactivity_days": return { threshold_days: n };
    case "nps_score": return { max_score: n };
    case "lead_stale": return { stale_days: n };
    case "checkin_streak": return { streak_days: n };
    case "risk_level_change": return { level: "high" };
    case "birthday": return {};
    default: return {};
  }
}

function buildActionConfig(values: RuleFormValues): Record<string, unknown> {
  const msg = values.message ?? "";
  switch (values.action_type) {
    case "send_whatsapp": return { template_name: "custom", message: msg };
    case "send_email": return { subject: values.name, body: msg };
    case "create_task": return { title: values.name, priority: "high" };
    case "notify": return { message: msg || values.name };
    default: return {};
  }
}

// ─── Threshold label helper ───────────────────────────────────────────────────

function thresholdLabel(triggerType: string): string {
  switch (triggerType) {
    case "inactivity_days": return "Dias sem atividade";
    case "nps_score": return "Pontuação máxima NPS";
    case "lead_stale": return "Dias sem atualização (lead)";
    case "checkin_streak": return "Dias consecutivos de check-in";
    default: return "";
  }
}

// ─── Rule creation drawer ─────────────────────────────────────────────────────

interface RuleFormDrawerProps {
  open: boolean;
  onClose: () => void;
  onSaved: () => void;
}

function RuleFormDrawer({ open, onClose, onSaved }: RuleFormDrawerProps) {
  const {
    register,
    handleSubmit,
    watch,
    control,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<RuleFormValues>({
    resolver: zodResolver(ruleSchema),
    defaultValues: { is_active: true, threshold_value: 7 },
  });

  const triggerType = watch("trigger_type");
  const actionType = watch("action_type");
  const needsThreshold = ["inactivity_days", "nps_score", "lead_stale", "checkin_streak"].includes(triggerType);
  const needsMessage = ["send_whatsapp", "send_email", "notify"].includes(actionType);

  const createMutation = useMutation({
    mutationFn: (values: RuleFormValues) =>
      automationService.createRule({
        name: values.name,
        description: values.description,
        trigger_type: values.trigger_type,
        trigger_config: buildTriggerConfig(values),
        action_type: values.action_type,
        action_config: buildActionConfig(values),
        is_active: values.is_active,
      }),
    onSuccess: () => {
      toast.success("Regra criada com sucesso!");
      reset();
      onSaved();
      onClose();
    },
    onError: () => toast.error("Erro ao criar regra. Tente novamente."),
  });

  const isPending = isSubmitting || createMutation.isPending;

  return (
    <Drawer open={open} onClose={onClose} title="Nova Regra de Automação">
      <form onSubmit={handleSubmit((v) => createMutation.mutate(v))} className="flex flex-col gap-4 p-1">
        <div>
          <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-lovable-ink-muted">
            Nome *
          </label>
          <Input {...register("name")} placeholder="Ex: Reengajamento 30 dias" />
          {errors.name && <p className="mt-1 text-xs text-red-500">{errors.name.message}</p>}
        </div>

        <div>
          <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-lovable-ink-muted">
            Descrição
          </label>
          <Input {...register("description")} placeholder="Opcional — descreva o objetivo da regra" />
        </div>

        <div>
          <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-lovable-ink-muted">
            Gatilho *
          </label>
          <select
            {...register("trigger_type")}
            className="w-full rounded-xl border border-lovable-border bg-lovable-surface px-3 py-2 text-sm text-lovable-ink focus:outline-none focus:ring-2 focus:ring-lovable-primary"
          >
            <option value="">Selecione um gatilho…</option>
            {TRIGGER_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
          {errors.trigger_type && <p className="mt-1 text-xs text-red-500">{errors.trigger_type.message}</p>}
        </div>

        {needsThreshold && (
          <div>
            <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-lovable-ink-muted">
              {thresholdLabel(triggerType)}
            </label>
            <Input {...register("threshold_value")} type="number" min={1} />
          </div>
        )}

        <div>
          <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-lovable-ink-muted">
            Ação *
          </label>
          <select
            {...register("action_type")}
            className="w-full rounded-xl border border-lovable-border bg-lovable-surface px-3 py-2 text-sm text-lovable-ink focus:outline-none focus:ring-2 focus:ring-lovable-primary"
          >
            <option value="">Selecione uma ação…</option>
            {ACTION_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
          {errors.action_type && <p className="mt-1 text-xs text-red-500">{errors.action_type.message}</p>}
        </div>

        {needsMessage && (
          <div>
            <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-lovable-ink-muted">
              Mensagem / Conteúdo
            </label>
            <textarea
              {...register("message")}
              rows={3}
              placeholder="Olá {nome}, sentimos sua falta! Que tal retomar seus treinos?"
              className="w-full rounded-xl border border-lovable-border bg-lovable-surface px-3 py-2 text-sm text-lovable-ink focus:outline-none focus:ring-2 focus:ring-lovable-primary resize-none"
            />
          </div>
        )}

        <div className="flex items-center gap-2">
          <Controller
            name="is_active"
            control={control}
            render={({ field }) => (
              <input
                type="checkbox"
                id="is_active"
                checked={field.value}
                onChange={field.onChange}
                className="h-4 w-4 rounded border-lovable-border text-lovable-primary"
              />
            )}
          />
          <label htmlFor="is_active" className="text-sm text-lovable-ink">
            Ativar regra imediatamente
          </label>
        </div>

        <div className="flex gap-2 pt-2">
          <Button type="submit" variant="primary" disabled={isPending} className="flex-1">
            {isPending ? "Criando..." : "Criar Regra"}
          </Button>
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancelar
          </Button>
        </div>
      </form>
    </Drawer>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

export function AutomationsPage() {
  const queryClient = useQueryClient();
  const [executing, setExecuting] = useState(false);
  const [ruleDrawerOpen, setRuleDrawerOpen] = useState(false);

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
    onError: () => toast.error("Não foi possível alterar a regra."),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => automationService.deleteRule(id),
    onSuccess: () => {
      toast.success("Regra excluída.");
      void queryClient.invalidateQueries({ queryKey: ["automations", "rules"] });
    },
    onError: () => toast.error("Erro ao excluir regra."),
  });

  const seedMutation = useMutation({
    mutationFn: () => automationService.seedDefaults(),
    onSuccess: (data) => {
      toast.success(`${data.length} regras padrão criadas!`);
      void queryClient.invalidateQueries({ queryKey: ["automations", "rules"] });
    },
    onError: () => toast.error("Erro ao criar regras padrão."),
  });

  const handleExecuteAll = async () => {
    setExecuting(true);
    try {
      const results = await automationService.executeAll();
      const executed = results.filter((r) => r["status"] !== "skipped" && r["status"] !== "error").length;
      toast.success(`${executed} ações realizadas de ${results.length} tentativas.`);
    } catch {
      toast.error("Erro ao executar automações.");
    } finally {
      setExecuting(false);
      void queryClient.invalidateQueries({ queryKey: ["automations", "rules"] });
    }
  };

  if (rulesQuery.isLoading) {
    return <LoadingPanel text="Carregando regras de automação..." />;
  }

  const rules = rulesQuery.data ?? [];

  return (
    <section className="space-y-6">
      <header className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="font-heading text-3xl font-bold text-lovable-ink">Automações</h2>
          <p className="text-sm text-lovable-ink-muted">Configure regras automáticas de retenção e engajamento.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          {rules.length === 0 && (
            <Button
              variant="ghost"
              onClick={() => seedMutation.mutate()}
              disabled={seedMutation.isPending}
            >
              <Plus size={14} />
              {seedMutation.isPending ? "Criando..." : "Criar Regras Padrão"}
            </Button>
          )}
          <Button
            variant="ghost"
            onClick={() => setRuleDrawerOpen(true)}
          >
            <Plus size={14} />
            Nova Regra
          </Button>
          <Button
            variant="primary"
            onClick={() => void handleExecuteAll()}
            disabled={executing || rules.length === 0}
          >
            <Play size={14} />
            {executing ? "Executando..." : "Executar Todas"}
          </Button>
        </div>
      </header>

      {rules.length === 0 ? (
        <div className="rounded-2xl border border-lovable-border bg-lovable-surface p-8 text-center">
          <Zap size={48} className="mx-auto mb-4 text-lovable-ink-muted/40" />
          <p className="text-lg font-semibold text-lovable-ink">Nenhuma regra configurada</p>
          <p className="mt-1 text-sm text-lovable-ink-muted">
            Clique em "Criar Regras Padrão" para começar com automações pré-configuradas, ou crie uma personalizada.
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

      <section className="rounded-2xl border border-lovable-border bg-lovable-surface p-4">
        <h3 className="mb-2 text-sm font-semibold uppercase tracking-wider text-lovable-ink">Como funciona</h3>
        <ul className="space-y-1 text-sm text-lovable-ink-muted">
          <li>As regras são executadas automaticamente após o processamento diário de risco (2h UTC).</li>
          <li>Você também pode executar manualmente clicando em "Executar Todas".</li>
          <li>Cada regra identifica alunos que atendem ao gatilho e executa a ação configurada.</li>
          <li>Tarefas duplicadas não são criadas (verificação automática).</li>
        </ul>
      </section>

      <RuleFormDrawer
        open={ruleDrawerOpen}
        onClose={() => setRuleDrawerOpen(false)}
        onSaved={() => void queryClient.invalidateQueries({ queryKey: ["automations", "rules"] })}
      />
    </section>
  );
}

// ─── Rule card ────────────────────────────────────────────────────────────────

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
    <article className="rounded-2xl border border-lovable-border bg-lovable-surface p-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold text-lovable-ink">{rule.name}</h3>
            <span className={clsx("rounded-full px-2 py-0.5 text-[10px] font-bold", ACTION_COLORS[rule.action_type] ?? "bg-slate-100 text-slate-600")}>
              {ACTION_LABELS[rule.action_type] ?? rule.action_type}
            </span>
            {!rule.is_active && (
              <span className="rounded-full bg-lovable-surface-soft px-2 py-0.5 text-[10px] font-bold text-lovable-ink-muted">
                INATIVA
              </span>
            )}
          </div>
          {rule.description && <p className="mt-1 text-xs text-lovable-ink-muted">{rule.description}</p>}
          <div className="mt-2 flex flex-wrap gap-3 text-[10px] uppercase tracking-wider text-lovable-ink-muted">
            <span>Gatilho: {TRIGGER_LABELS[rule.trigger_type] ?? rule.trigger_type}</span>
            <span>Execuções: {rule.executions_count}</span>
            {rule.last_executed_at && (
              <span>Última: {new Date(rule.last_executed_at).toLocaleString("pt-BR")}</span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => onToggle(!rule.is_active)}
            disabled={isToggling}
            className="text-lovable-ink-muted hover:text-lovable-primary disabled:opacity-50"
            title={rule.is_active ? "Desativar" : "Ativar"}
          >
            {rule.is_active
              ? <ToggleRight size={24} className="text-lovable-primary" />
              : <ToggleLeft size={24} />}
          </button>
          <button
            type="button"
            onClick={onDelete}
            className="text-lovable-ink-muted/40 hover:text-red-500"
            title="Excluir regra"
          >
            <Trash2 size={16} />
          </button>
        </div>
      </div>
    </article>
  );
}
