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
import { Button, Dialog, Drawer, FormField, Input, Select, Textarea } from "../../components/ui2";

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
  send_email: "Enviar E-mail",
  notify: "Notificar",
};

const ACTION_COLORS: Record<string, string> = {
  create_task: "bg-lovable-primary-soft text-lovable-primary",
  send_whatsapp: "bg-[hsl(var(--lovable-success)/0.15)] text-[hsl(var(--lovable-success))]",
  send_email: "bg-lovable-surface-soft text-lovable-ink",
  notify: "bg-[hsl(var(--lovable-warning)/0.15)] text-[hsl(var(--lovable-warning))]",
};

const TRIGGER_OPTIONS = Object.entries(TRIGGER_LABELS).map(([value, label]) => ({ value, label }));
const ACTION_OPTIONS = Object.entries(ACTION_LABELS).map(([value, label]) => ({ value, label }));

const ruleSchema = z.object({
  name: z.string().min(3, "Nome deve ter pelo menos 3 caracteres"),
  description: z.string().optional(),
  trigger_type: z.string().min(1, "Selecione um gatilho"),
  threshold_value: z.coerce.number().min(0).optional(),
  action_type: z.string().min(1, "Selecione uma acao"),
  message: z.string().optional(),
  is_active: z.boolean().default(true),
});

type RuleFormValues = z.infer<typeof ruleSchema>;

function buildTriggerConfig(values: RuleFormValues): Record<string, unknown> {
  const amount = values.threshold_value ?? 7;

  switch (values.trigger_type) {
    case "inactivity_days":
      return { threshold_days: amount };
    case "nps_score":
      return { max_score: amount };
    case "lead_stale":
      return { stale_days: amount };
    case "checkin_streak":
      return { streak_days: amount };
    case "risk_level_change":
      return { level: "high" };
    case "birthday":
      return {};
    default:
      return {};
  }
}

function buildActionConfig(values: RuleFormValues): Record<string, unknown> {
  const message = values.message ?? "";

  switch (values.action_type) {
    case "send_whatsapp":
      return { template_name: "custom", message };
    case "send_email":
      return { subject: values.name, body: message };
    case "create_task":
      return { title: values.name, priority: "high" };
    case "notify":
      return { message: message || values.name };
    default:
      return {};
  }
}

function thresholdLabel(triggerType: string): string {
  switch (triggerType) {
    case "inactivity_days":
      return "Dias sem atividade";
    case "nps_score":
      return "Pontuacao maxima NPS";
    case "lead_stale":
      return "Dias sem atualizacao (lead)";
    case "checkin_streak":
      return "Dias consecutivos de check-in";
    default:
      return "";
  }
}

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
    <Drawer open={open} onClose={onClose} title="Nova Regra de Automacao">
      <form onSubmit={handleSubmit((values) => createMutation.mutate(values))} className="flex flex-col gap-4 p-1">
        <FormField label="Nome" required error={errors.name?.message}>
          <Input {...register("name")} placeholder="Ex: Reengajamento 30 dias" />
        </FormField>

        <FormField label="Descricao">
          <Input {...register("description")} placeholder="Opcional - descreva o objetivo da regra" />
        </FormField>

        <FormField label="Gatilho" required error={errors.trigger_type?.message}>
          <Select {...register("trigger_type")}>
            <option value="">Selecione um gatilho...</option>
            {TRIGGER_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </Select>
        </FormField>

        {needsThreshold ? (
          <FormField label={thresholdLabel(triggerType)}>
            <Input {...register("threshold_value")} type="number" min={1} />
          </FormField>
        ) : null}

        <FormField label="Acao" required error={errors.action_type?.message}>
          <Select {...register("action_type")}>
            <option value="">Selecione uma acao...</option>
            {ACTION_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </Select>
        </FormField>

        {needsMessage ? (
          <FormField label="Mensagem / Conteudo">
            <Textarea
              {...register("message")}
              rows={3}
              placeholder="Ola {nome}, sentimos sua falta! Que tal retomar seus treinos?"
            />
          </FormField>
        ) : null}

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
            <span className={clsx("rounded-full px-2 py-0.5 text-[10px] font-bold", ACTION_COLORS[rule.action_type] ?? "bg-lovable-surface-soft text-lovable-ink-muted")}>
              {ACTION_LABELS[rule.action_type] ?? rule.action_type}
            </span>
            {!rule.is_active ? (
              <span className="rounded-full bg-lovable-surface-soft px-2 py-0.5 text-[10px] font-bold text-lovable-ink-muted">
                INATIVA
              </span>
            ) : null}
          </div>
          {rule.description ? <p className="mt-1 text-xs text-lovable-ink-muted">{rule.description}</p> : null}
          <div className="mt-2 flex flex-wrap gap-3 text-[10px] uppercase tracking-wider text-lovable-ink-muted">
            <span>Gatilho: {TRIGGER_LABELS[rule.trigger_type] ?? rule.trigger_type}</span>
            <span>Execucoes: {rule.executions_count}</span>
            {rule.last_executed_at ? <span>Ultima: {new Date(rule.last_executed_at).toLocaleString("pt-BR")}</span> : null}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => onToggle(!rule.is_active)}
            disabled={isToggling}
            className="text-lovable-ink-muted transition hover:text-lovable-primary disabled:opacity-50"
            title={rule.is_active ? "Desativar" : "Ativar"}
          >
            {rule.is_active ? <ToggleRight size={24} className="text-lovable-primary" /> : <ToggleLeft size={24} />}
          </button>
          <button
            type="button"
            onClick={onDelete}
            className="text-lovable-ink-muted/60 transition hover:text-[hsl(var(--lovable-danger))]"
            title="Excluir regra"
          >
            <Trash2 size={16} />
          </button>
        </div>
      </div>
    </article>
  );
}

export function AutomationsPage() {
  const queryClient = useQueryClient();
  const [executing, setExecuting] = useState(false);
  const [ruleDrawerOpen, setRuleDrawerOpen] = useState(false);
  const [ruleToDelete, setRuleToDelete] = useState<AutomationRule | null>(null);

  const rulesQuery = useQuery({
    queryKey: ["automations", "rules"],
    queryFn: () => automationService.listRules(),
    staleTime: 30 * 1000,
  });

  const toggleMutation = useMutation({
    mutationFn: ({ id, is_active }: { id: string; is_active: boolean }) => automationService.updateRule(id, { is_active }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["automations", "rules"] });
    },
    onError: () => toast.error("Nao foi possivel alterar a regra."),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => automationService.deleteRule(id),
    onSuccess: () => {
      toast.success("Regra excluida.");
      setRuleToDelete(null);
      void queryClient.invalidateQueries({ queryKey: ["automations", "rules"] });
    },
    onError: () => toast.error("Erro ao excluir regra."),
  });

  const seedMutation = useMutation({
    mutationFn: () => automationService.seedDefaults(),
    onSuccess: (data) => {
      toast.success(`${data.length} regras padrao criadas!`);
      void queryClient.invalidateQueries({ queryKey: ["automations", "rules"] });
    },
    onError: () => toast.error("Erro ao criar regras padrao."),
  });

  const handleExecuteAll = async () => {
    setExecuting(true);
    try {
      const results = await automationService.executeAll();
      const executed = results.filter((result) => result["status"] !== "skipped" && result["status"] !== "error").length;
      toast.success(`${executed} acoes realizadas de ${results.length} tentativas.`);
    } catch {
      toast.error("Erro ao executar automacoes.");
    } finally {
      setExecuting(false);
      void queryClient.invalidateQueries({ queryKey: ["automations", "rules"] });
    }
  };

  if (rulesQuery.isLoading) {
    return <LoadingPanel text="Carregando regras de automacao..." />;
  }

  if (rulesQuery.isError) {
    return <LoadingPanel text="Erro ao carregar automacoes. Tente novamente." />;
  }

  const rules = rulesQuery.data ?? [];

  return (
    <section className="space-y-6">
      <header className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="font-heading text-3xl font-bold text-lovable-ink">Automacoes</h2>
          <p className="text-sm text-lovable-ink-muted">Configure regras automaticas de retencao e engajamento.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          {rules.length === 0 ? (
            <Button variant="ghost" onClick={() => seedMutation.mutate()} disabled={seedMutation.isPending}>
              <Plus size={14} />
              {seedMutation.isPending ? "Criando..." : "Criar Regras Padrao"}
            </Button>
          ) : null}
          <Button variant="ghost" onClick={() => setRuleDrawerOpen(true)}>
            <Plus size={14} />
            Nova Regra
          </Button>
          <Button variant="primary" onClick={() => void handleExecuteAll()} disabled={executing || rules.length === 0}>
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
            Clique em "Criar Regras Padrao" para comecar com automacoes pre-configuradas, ou crie uma personalizada.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {rules.map((rule) => (
            <RuleCard
              key={rule.id}
              rule={rule}
              onToggle={(active) => toggleMutation.mutate({ id: rule.id, is_active: active })}
              onDelete={() => setRuleToDelete(rule)}
              isToggling={toggleMutation.isPending}
            />
          ))}
        </div>
      )}

      <section className="rounded-2xl border border-lovable-border bg-lovable-surface p-4">
        <h3 className="mb-2 text-sm font-semibold uppercase tracking-wider text-lovable-ink">Como funciona</h3>
        <ul className="space-y-1 text-sm text-lovable-ink-muted">
          <li>As regras sao executadas automaticamente apos o processamento diario de risco (2h UTC).</li>
          <li>Voce tambem pode executar manualmente clicando em "Executar Todas".</li>
          <li>Cada regra identifica alunos que atendem ao gatilho e executa a acao configurada.</li>
          <li>Tarefas duplicadas nao sao criadas (verificacao automatica).</li>
        </ul>
      </section>

      <RuleFormDrawer
        open={ruleDrawerOpen}
        onClose={() => setRuleDrawerOpen(false)}
        onSaved={() => void queryClient.invalidateQueries({ queryKey: ["automations", "rules"] })}
      />

      <Dialog
        open={Boolean(ruleToDelete)}
        onClose={() => setRuleToDelete(null)}
        title="Excluir regra"
        description={
          ruleToDelete
            ? `Tem certeza que deseja excluir ${ruleToDelete.name}? Esta acao nao pode ser desfeita.`
            : "Tem certeza que deseja excluir esta regra?"
        }
      >
        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={() => setRuleToDelete(null)}>
            Cancelar
          </Button>
          <Button
            variant="danger"
            onClick={() => {
              if (ruleToDelete) {
                deleteMutation.mutate(ruleToDelete.id);
              }
            }}
            disabled={deleteMutation.isPending}
          >
            {deleteMutation.isPending ? "Excluindo..." : "Excluir"}
          </Button>
        </div>
      </Dialog>
    </section>
  );
}
