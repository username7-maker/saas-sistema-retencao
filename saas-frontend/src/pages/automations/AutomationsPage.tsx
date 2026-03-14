import { useEffect, useState } from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Zap, Play, Plus, ToggleLeft, ToggleRight, Trash2, Pencil,
  ChevronRight, Sparkles, Clock, CheckCircle2, XCircle,
  AlertTriangle, ArrowRight, Activity, LayoutTemplate,
  ChevronDown, ChevronUp, MessageSquare, Bell, ListTodo, Mail,
  Timer, Eye,
} from "lucide-react";
import toast from "react-hot-toast";
import clsx from "clsx";

import { LoadingPanel } from "../../components/common/LoadingPanel";
import { automationService, type AutomationRule } from "../../services/automationService";
import { Button, Drawer, FormField, Input, Select, Textarea } from "../../components/ui2";

// ─── Metadata ────────────────────────────────────────────────────────────────

const TRIGGER_META: Record<string, { label: string; icon: string; color: string; bg: string }> = {
  inactivity_days:   { label: "Inatividade",      icon: "⏸", color: "#E24B4A", bg: "#FCEBEB" },
  risk_level_change: { label: "Mudança de Risco",  icon: "⚠", color: "#BA7517", bg: "#FAEEDA" },
  nps_score:         { label: "NPS Baixo",          icon: "📉", color: "#185FA5", bg: "#E6F1FB" },
  lead_stale:        { label: "Lead Parado",         icon: "🧊", color: "#5E5B52", bg: "#EDEBE3" },
  birthday:          { label: "Aniversário",         icon: "🎂", color: "#7C3DB3", bg: "#F3ECFC" },
  checkin_streak:    { label: "Sequência",           icon: "🔥", color: "#0F7553", bg: "#E1F5EE" },
  ai_evaluate:       { label: "IA Avalia",           icon: "✦", color: "#0F6E56", bg: "#D7F2E8" },
};

const ACTION_META: Record<string, { label: string; Icon: React.ElementType; color: string; bg: string }> = {
  create_task:   { label: "Criar Tarefa", Icon: ListTodo,      color: "#185FA5", bg: "#E6F1FB" },
  send_whatsapp: { label: "WhatsApp",     Icon: MessageSquare, color: "#0F7553", bg: "#E1F5EE" },
  send_email:    { label: "E-mail",       Icon: Mail,          color: "#5E5B52", bg: "#EDEBE3" },
  notify:        { label: "Notificação",  Icon: Bell,          color: "#BA7517", bg: "#FAEEDA" },
};

const TEMPLATES = [
  { id: "reengagement_7d", name: "Reengajamento 7 dias", emoji: "😴",
    desc: "WhatsApp quando aluno some por 7 dias",
    trigger_type: "inactivity_days", trigger_config: { days: 7 },
    action_type: "send_whatsapp", action_config: { template: "reengagement_7d", message: "" } },
  { id: "red_alert", name: "Alerta Risco Vermelho", emoji: "🚨",
    desc: "Task urgente quando aluno vai para vermelho",
    trigger_type: "risk_level_change", trigger_config: { level: "red" },
    action_type: "create_task", action_config: { title: "🔴 Ligar para {nome} — risco crítico", priority: "urgent", description: "Aluno em risco vermelho. Ligar hoje." } },
  { id: "nps_rescue", name: "Resgate NPS Baixo", emoji: "💔",
    desc: "WhatsApp quando NPS ≤ 6 (detrator)",
    trigger_type: "nps_score", trigger_config: { max_score: 6 },
    action_type: "send_whatsapp", action_config: { template: "nps_low", message: "" } },
  { id: "birthday", name: "Surpresa de Aniversário", emoji: "🎂",
    desc: "Mensagem especial no dia do aniversário",
    trigger_type: "birthday", trigger_config: {},
    action_type: "send_whatsapp", action_config: { template: "birthday", message: "" } },
  { id: "ai_vip", name: "IA — VIP em Risco", emoji: "✦",
    desc: "Claude avalia se aluno VIP (6+ meses) precisa de atenção",
    trigger_type: "ai_evaluate", trigger_config: { min_loyalty_months: 6 },
    action_type: "create_task", action_config: { title: "✦ Atenção VIP — {nome}", priority: "urgent", description: "Identificado por IA como VIP em risco de churn." } },
  { id: "checkin_celebrate", name: "Celebrar Sequência 10x", emoji: "🔥",
    desc: "Mensagem motivacional ao atingir 10 treinos seguidos",
    trigger_type: "checkin_streak", trigger_config: { streak_days: 10 },
    action_type: "send_whatsapp", action_config: { template: "custom", message: "🔥 {nome}, você atingiu 10 treinos seguidos! Isso é dedicação de verdade." } },
];

// ─── Schema ───────────────────────────────────────────────────────────────────

const ruleSchema = z.object({
  name: z.string().min(3, "Mínimo 3 caracteres"),
  description: z.string().optional(),
  trigger_type: z.string().min(1, "Selecione um gatilho"),
  risk_level_target: z.enum(["red", "yellow", "green"]).optional(),
  threshold_value: z.coerce.number().min(0).optional(),
  action_type: z.string().min(1, "Selecione uma ação"),
  message: z.string().optional(),
  is_active: z.boolean().default(true),
});
type RuleFormValues = z.infer<typeof ruleSchema>;

// ─── Helpers ──────────────────────────────────────────────────────────────────

function buildTriggerConfig(v: RuleFormValues): Record<string, unknown> {
  const n = v.threshold_value ?? 7;
  switch (v.trigger_type) {
    case "inactivity_days":   return { days: n };
    case "nps_score":         return { max_score: n };
    case "lead_stale":        return { stale_days: n };
    case "checkin_streak":    return { streak_days: n };
    case "risk_level_change": return { level: v.risk_level_target ?? "red" };
    default:                  return {};
  }
}

function buildActionConfig(v: RuleFormValues): Record<string, unknown> {
  const m = v.message ?? "";
  switch (v.action_type) {
    case "send_whatsapp": return { template: "custom", message: m, extra_vars: { mensagem: m || "Olá {nome}!" } };
    case "send_email":    return { subject: v.name, body: m };
    case "create_task":   return { title: v.name, description: m || "Tarefa criada por automação.", priority: "high" };
    case "notify":        return { title: v.name, message: m || "Ação necessária para {nome}" };
    default:              return {};
  }
}

function thresholdFromConfig(type: string, cfg: Record<string, unknown>): number {
  const raw = type === "inactivity_days" ? cfg.days : type === "nps_score" ? cfg.max_score
    : type === "lead_stale" ? cfg.stale_days : type === "checkin_streak" ? cfg.streak_days : 7;
  return typeof raw === "number" ? raw : 7;
}

function msgFromActionConfig(type: string, cfg: Record<string, unknown>): string {
  if (type === "send_whatsapp") return typeof cfg.message === "string" ? cfg.message : "";
  if (type === "send_email") return typeof cfg.body === "string" ? cfg.body : "";
  return typeof cfg.description === "string" ? cfg.description : "";
}

function ruleWhen(rule: AutomationRule): string {
  const tc = rule.trigger_config;
  switch (rule.trigger_type) {
    case "inactivity_days":   return `≥ ${tc.days ?? "?"} dias inativo`;
    case "risk_level_change": return `risco → ${tc.level === "red" ? "Vermelho" : tc.level === "yellow" ? "Amarelo" : "Verde"}`;
    case "nps_score":         return `NPS ≤ ${tc.max_score ?? "?"}`;
    case "lead_stale":        return `lead ${tc.stale_days ?? "?"} dias parado`;
    case "birthday":          return "no aniversário";
    case "checkin_streak":    return `${tc.streak_days ?? "?"} check-ins seguidos`;
    case "ai_evaluate":       return "Claude avalia o aluno";
    default:                  return rule.trigger_type;
  }
}

function formatDate(iso: string | null): string | null {
  if (!iso) return null;
  const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 60000);
  if (diff < 60) return `${diff}min atrás`;
  if (diff < 1440) return `${Math.floor(diff / 60)}h atrás`;
  return new Date(iso).toLocaleDateString("pt-BR", { day: "2-digit", month: "short" });
}
// ─── RulePipelineCard ─────────────────────────────────────────────────────────

function RulePipelineCard({ rule, onToggle, onEdit, onDelete, isToggling }: {
  rule: AutomationRule;
  onToggle: (v: boolean) => void;
  onEdit: () => void;
  onDelete: () => void;
  isToggling: boolean;
}) {
  const [confirmDel, setConfirmDel] = useState(false);
  const tm = TRIGGER_META[rule.trigger_type];
  const am = ACTION_META[rule.action_type];
  const ActionIcon = am?.Icon ?? Zap;
  const isAI = rule.trigger_type === "ai_evaluate";
  const lastRun = formatDate(rule.last_executed_at);

  return (
    <article className={clsx(
      "group relative rounded-2xl border bg-lovable-surface transition-all duration-150",
      rule.is_active
        ? "border-lovable-border hover:border-lovable-ink/20 hover:shadow-sm"
        : "border-lovable-border/40 opacity-55",
      isAI && rule.is_active && "shadow-[inset_0_0_0_1.5px_#1D9E7522]"
    )}>
      <div className="flex items-center gap-3 p-4">
        {/* Trigger chip */}
        <div className="flex items-center gap-2 rounded-xl px-3 py-2 shrink-0"
          style={{ background: tm?.bg ?? "#F0EEE8", color: tm?.color ?? "#888" }}>
          <span className="text-base leading-none">{tm?.icon ?? "◆"}</span>
          <div className="hidden sm:block">
            <p className="text-[9px] font-semibold uppercase tracking-wider opacity-60 leading-none mb-0.5">
              {isAI ? "IA" : "Quando"}
            </p>
            <p className="text-[11px] font-semibold leading-none whitespace-nowrap">{ruleWhen(rule)}</p>
          </div>
        </div>

        <ArrowRight size={13} className="text-lovable-ink-muted/30 shrink-0" />

        {/* Action chip */}
        <div className="flex items-center gap-1.5 rounded-xl px-3 py-2 shrink-0"
          style={{ background: am?.bg ?? "#F0EEE8", color: am?.color ?? "#888" }}>
          <ActionIcon size={13} />
          <span className="text-[11px] font-semibold hidden sm:inline whitespace-nowrap">{am?.label ?? rule.action_type}</span>
        </div>

        {/* Name & meta */}
        <div className="flex-1 min-w-0 ml-1">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="text-sm font-semibold text-lovable-ink truncate">{rule.name}</h3>
            {isAI && (
              <span className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[9px] font-bold uppercase tracking-wide"
                style={{ background: "#D7F2E8", color: "#0F6E56" }}>
                <Sparkles size={8} />IA
              </span>
            )}
            {!rule.is_active && (
              <span className="rounded-full bg-lovable-surface-soft px-2 py-0.5 text-[9px] font-bold uppercase text-lovable-ink-muted">INATIVA</span>
            )}
          </div>
          {rule.description && <p className="text-xs text-lovable-ink-muted truncate mt-0.5">{rule.description}</p>}
          <div className="flex items-center gap-3 mt-1.5 flex-wrap">
            {rule.executions_count > 0 && (
              <span className="flex items-center gap-1 text-[10px] text-lovable-ink-muted">
                <Activity size={9} />{rule.executions_count.toLocaleString("pt-BR")} exec.
              </span>
            )}
            {lastRun && (
              <span className="flex items-center gap-1 text-[10px] text-lovable-ink-muted">
                <Clock size={9} />{lastRun}
              </span>
            )}
          </div>
        </div>

        {/* Controls */}
        <div className="flex items-center gap-1 shrink-0">
          <button type="button" onClick={() => onToggle(!rule.is_active)} disabled={isToggling}
            className="p-1.5 rounded-lg text-lovable-ink-muted hover:bg-lovable-surface-soft transition disabled:opacity-40">
            {rule.is_active
              ? <ToggleRight size={22} className="text-lovable-primary" />
              : <ToggleLeft size={22} />}
          </button>
          <button type="button" onClick={onEdit}
            className="p-1.5 rounded-lg text-lovable-ink-muted hover:bg-lovable-surface-soft transition opacity-0 group-hover:opacity-100">
            <Pencil size={14} />
          </button>
          <button type="button" onClick={() => setConfirmDel(true)}
            className="p-1.5 rounded-lg text-lovable-ink-muted hover:text-red-500 hover:bg-red-50 transition opacity-0 group-hover:opacity-100">
            <Trash2 size={14} />
          </button>
        </div>
      </div>

      {confirmDel && (
        <div className="border-t border-lovable-border px-4 py-3 bg-lovable-surface-soft rounded-b-2xl flex items-center justify-between gap-2">
          <p className="text-xs text-lovable-ink-muted">Excluir <strong>{rule.name}</strong>?</p>
          <div className="flex gap-2">
            <button type="button" onClick={() => setConfirmDel(false)}
              className="text-xs px-3 py-1 rounded-full border border-lovable-border hover:bg-white transition">Cancelar</button>
            <button type="button" onClick={() => { onDelete(); setConfirmDel(false); }}
              className="text-xs px-3 py-1 rounded-full bg-red-500 text-white hover:bg-red-600 transition">Excluir</button>
          </div>
        </div>
      )}
    </article>
  );
}

// ─── Stats strip ──────────────────────────────────────────────────────────────

function StatsStrip({ rules }: { rules: AutomationRule[] }) {
  const active    = rules.filter(r => r.is_active).length;
  const execTotal = rules.reduce((s, r) => s + r.executions_count, 0);
  const aiRules   = rules.filter(r => r.trigger_type === "ai_evaluate").length;
  const lastExec  = rules
    .filter(r => r.last_executed_at)
    .sort((a, b) => new Date(b.last_executed_at!).getTime() - new Date(a.last_executed_at!).getTime())[0];

  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
      {[
        { label: "Regras ativas", value: `${active}/${rules.length}`, icon: Zap, accent: "#1D9E75" },
        { label: "Total execuções", value: execTotal.toLocaleString("pt-BR"), icon: Activity, accent: "#185FA5" },
        { label: "Regras com IA", value: String(aiRules), icon: Sparkles, accent: "#0F6E56" },
        { label: "Última execução", value: lastExec ? formatDate(lastExec.last_executed_at) ?? "—" : "—", icon: Clock, accent: "#BA7517" },
      ].map(s => (
        <div key={s.label} className="rounded-2xl border border-lovable-border bg-lovable-surface px-4 py-3 flex items-center gap-3">
          <div className="rounded-xl p-2" style={{ background: s.accent + "18" }}>
            <s.icon size={16} style={{ color: s.accent }} />
          </div>
          <div>
            <p className="text-[10px] uppercase tracking-wider text-lovable-ink-muted font-medium">{s.label}</p>
            <p className="text-lg font-bold text-lovable-ink leading-tight">{s.value}</p>
          </div>
        </div>
      ))}
    </div>
  );
}

// ─── Template Gallery ─────────────────────────────────────────────────────────

function TemplateGallery({ onSelect }: { onSelect: (t: typeof TEMPLATES[0]) => void }) {
  return (
    <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
      {TEMPLATES.map(t => {
        const tm = TRIGGER_META[t.trigger_type];
        const am = ACTION_META[t.action_type];
        const ActionIcon = am?.Icon ?? Zap;
        const isAI = t.trigger_type === "ai_evaluate";
        return (
          <button key={t.id} type="button" onClick={() => onSelect(t)}
            className={clsx(
              "group text-left rounded-2xl border p-4 transition-all duration-150",
              "border-lovable-border bg-lovable-surface hover:border-lovable-ink/30 hover:shadow-sm",
              isAI && "border-[#1D9E7530] bg-[#F7FEF9]"
            )}>
            <div className="flex items-start justify-between mb-3">
              <span className="text-2xl">{t.emoji}</span>
              {isAI && (
                <span className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[9px] font-bold uppercase tracking-wide"
                  style={{ background: "#D7F2E8", color: "#0F6E56" }}>
                  <Sparkles size={8} />IA
                </span>
              )}
            </div>
            <p className="text-sm font-semibold text-lovable-ink mb-1">{t.name}</p>
            <p className="text-xs text-lovable-ink-muted mb-3 leading-relaxed">{t.desc}</p>
            <div className="flex items-center gap-1.5 flex-wrap">
              <span className="rounded-lg px-2 py-1 text-[10px] font-semibold"
                style={{ background: tm?.bg, color: tm?.color }}>
                {tm?.icon} {tm?.label}
              </span>
              <ArrowRight size={9} className="text-lovable-ink-muted/40" />
              <span className="flex items-center gap-1 rounded-lg px-2 py-1 text-[10px] font-semibold"
                style={{ background: am?.bg, color: am?.color }}>
                <ActionIcon size={10} />{am?.label}
              </span>
            </div>
          </button>
        );
      })}
    </div>
  );
}
// ─── ExecResultsPanel ─────────────────────────────────────────────────────────

interface ExecResult {
  rule_id?: string;
  member_id?: string;
  lead_id?: string;
  action?: string;
  status: string;
  reason?: string;
}

function ExecResultsPanel({ results, rules, onClose }: {
  results: ExecResult[];
  rules: AutomationRule[];
  onClose: () => void;
}) {
  const ruleMap = Object.fromEntries(rules.map(r => [r.id, r]));
  const byRule: Record<string, ExecResult[]> = {};
  for (const r of results) {
    const k = r.rule_id ?? "unknown";
    if (!byRule[k]) byRule[k] = [];
    byRule[k].push(r);
  }
  const acted   = results.filter(r => !["skipped", "error"].includes(r.status)).length;
  const skipped = results.filter(r => r.status === "skipped").length;
  const errors  = results.filter(r => r.status === "error").length;
  const STATUS_ICON: Record<string, React.ReactNode> = {
    created:  <CheckCircle2 size={11} className="text-emerald-500" />,
    notified: <CheckCircle2 size={11} className="text-emerald-500" />,
    sent:     <CheckCircle2 size={11} className="text-emerald-500" />,
    skipped:  <ChevronRight size={11} className="text-lovable-ink-muted" />,
    error:    <XCircle      size={11} className="text-red-500" />,
  };

  return (
    <div className="rounded-2xl border border-lovable-border bg-lovable-surface overflow-hidden">
      <div className="flex items-center justify-between border-b border-lovable-border px-4 py-3 bg-lovable-surface-soft">
        <div className="flex items-center gap-2 flex-wrap">
          <p className="text-sm font-semibold text-lovable-ink">Resultado</p>
          <span className="flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-bold bg-emerald-100 text-emerald-700">
            <CheckCircle2 size={9} />{acted} ações
          </span>
          {skipped > 0 && <span className="rounded-full px-2 py-0.5 text-[10px] font-bold bg-lovable-surface-soft text-lovable-ink-muted">{skipped} ignorados</span>}
          {errors > 0 && <span className="flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-bold bg-red-100 text-red-600"><XCircle size={9} />{errors} erros</span>}
        </div>
        <button type="button" onClick={onClose}
          className="text-xs text-lovable-ink-muted hover:text-lovable-ink px-2 py-1 rounded-lg hover:bg-lovable-surface transition">
          Fechar
        </button>
      </div>
      {results.length === 0 ? (
        <div className="px-4 py-8 text-center">
          <AlertTriangle size={24} className="mx-auto mb-2 text-lovable-ink-muted/30" />
          <p className="text-sm text-lovable-ink-muted">Nenhum aluno correspondeu aos gatilhos ativos.</p>
        </div>
      ) : (
        <ul className="divide-y divide-lovable-border">
          {Object.entries(byRule).map(([ruleId, items]) => {
            const rule = ruleMap[ruleId];
            const actedCount = items.filter(i => !["skipped","error"].includes(i.status)).length;
            return (
              <li key={ruleId} className="px-4 py-3">
                <div className="flex items-center justify-between mb-2">
                  <p className="text-xs font-semibold text-lovable-ink">{rule?.name ?? ruleId}</p>
                  <span className={clsx("text-[10px] font-semibold rounded-full px-2 py-0.5",
                    actedCount > 0 ? "bg-emerald-100 text-emerald-700" : "bg-lovable-surface-soft text-lovable-ink-muted")}>
                    {actedCount > 0 ? `${actedCount} ações` : "sem ações"}
                  </span>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {items.map((item, i) => (
                    <span key={i} className="inline-flex items-center gap-1 rounded-full border border-lovable-border bg-lovable-surface px-2.5 py-1 text-[10px] font-medium text-lovable-ink">
                      {STATUS_ICON[item.status]}
                      {item.status}{item.reason ? ` · ${item.reason}` : ""}
                    </span>
                  ))}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

// ─── Rule Form Drawer ─────────────────────────────────────────────────────────

function RuleFormDrawer({ open, mode, rule, prefillTemplate, onClose, onSaved }: {
  open: boolean;
  mode: "create" | "edit";
  rule: AutomationRule | null;
  prefillTemplate: typeof TEMPLATES[0] | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const isEdit = mode === "edit" && rule !== null;
  const { register, handleSubmit, watch, reset, control, formState: { errors, isSubmitting } } =
    useForm<RuleFormValues>({ resolver: zodResolver(ruleSchema),
      defaultValues: { name: "", description: "", trigger_type: "", action_type: "", message: "", is_active: true, threshold_value: 7, risk_level_target: "red" } });

  useEffect(() => {
    if (!open) return;
    if (isEdit && rule) {
      reset({ name: rule.name, description: rule.description ?? "", trigger_type: rule.trigger_type,
        action_type: rule.action_type, message: msgFromActionConfig(rule.action_type, rule.action_config),
        threshold_value: thresholdFromConfig(rule.trigger_type, rule.trigger_config),
        risk_level_target: (rule.trigger_config.level as "red" | "yellow" | "green") ?? "red",
        is_active: rule.is_active });
      return;
    }
    if (prefillTemplate) {
      reset({ name: prefillTemplate.name, description: prefillTemplate.desc,
        trigger_type: prefillTemplate.trigger_type, action_type: prefillTemplate.action_type,
        message: msgFromActionConfig(prefillTemplate.action_type, prefillTemplate.action_config),
        threshold_value: thresholdFromConfig(prefillTemplate.trigger_type, prefillTemplate.trigger_config),
        is_active: true });
      return;
    }
    reset({ name: "", description: "", trigger_type: "", action_type: "", message: "", is_active: true, threshold_value: 7, risk_level_target: "red" });
  }, [open, isEdit, rule, prefillTemplate, reset]);

  const triggerType = watch("trigger_type");
  const actionType  = watch("action_type");
  const msgValue    = watch("message");

  const needsThreshold = ["inactivity_days","nps_score","lead_stale","checkin_streak"].includes(triggerType);
  const needsRiskLevel = triggerType === "risk_level_change";
  const isAITrigger    = triggerType === "ai_evaluate";

  const createMutation = useMutation({
    mutationFn: (v: RuleFormValues) => automationService.createRule({
      name: v.name, description: v.description?.trim() || undefined,
      trigger_type: v.trigger_type, trigger_config: buildTriggerConfig(v),
      action_type: v.action_type, action_config: buildActionConfig(v), is_active: v.is_active }),
    onSuccess: () => { toast.success("Regra criada!"); reset(); onSaved(); onClose(); },
    onError: () => toast.error("Erro ao criar regra."),
  });

  const updateMutation = useMutation({
    mutationFn: (v: RuleFormValues) => {
      if (!rule) throw new Error();
      return automationService.updateRule(rule.id, {
        name: v.name, description: v.description?.trim() || "",
        trigger_config: { ...rule.trigger_config, ...buildTriggerConfig(v) },
        action_config: { ...rule.action_config, ...buildActionConfig(v) },
        is_active: v.is_active });
    },
    onSuccess: () => { toast.success("Regra atualizada!"); onSaved(); onClose(); },
    onError: () => toast.error("Erro ao atualizar."),
  });

  const isPending = isSubmitting || createMutation.isPending || updateMutation.isPending;

  return (
    <Drawer open={open} onClose={onClose} title={isEdit ? "Editar Regra" : "Nova Regra de Automação"}>
      <form onSubmit={handleSubmit(v => isEdit ? updateMutation.mutate(v) : createMutation.mutate(v))}
        className="flex flex-col gap-4 p-1">

        <FormField label="Nome" required error={errors.name?.message}>
          <Input {...register("name")} placeholder="Ex: Reengajamento 7 dias" />
        </FormField>

        <FormField label="Descrição">
          <Input {...register("description")} placeholder="Objetivo da regra (opcional)" />
        </FormField>

        <div className="grid grid-cols-2 gap-3">
          <FormField label="Gatilho" required error={errors.trigger_type?.message}>
            <Select {...register("trigger_type")} disabled={isEdit}>
              <option value="">Selecione...</option>
              {Object.entries(TRIGGER_META).map(([v, m]) => (
                <option key={v} value={v}>{m.icon} {m.label}</option>
              ))}
            </Select>
          </FormField>
          <FormField label="Ação" required error={errors.action_type?.message}>
            <Select {...register("action_type")}>
              <option value="">Selecione...</option>
              {Object.entries(ACTION_META).map(([v, m]) => (
                <option key={v} value={v}>{m.label}</option>
              ))}
            </Select>
          </FormField>
        </div>

        {needsThreshold && (
          <FormField label={
            triggerType === "inactivity_days" ? "Dias sem atividade"
              : triggerType === "nps_score" ? "NPS máximo (inclusive)"
              : triggerType === "lead_stale" ? "Dias sem atualização"
              : "Check-ins consecutivos necessários"
          }>
            <Input type="number" min={1} {...register("threshold_value")} />
          </FormField>
        )}

        {needsRiskLevel && (
          <FormField label="Nível de risco alvo">
            <Select {...register("risk_level_target")}>
              <option value="red">⛔ Vermelho — crítico</option>
              <option value="yellow">⚠️ Amarelo — atenção</option>
              <option value="green">✅ Verde — saudável</option>
            </Select>
          </FormField>
        )}

        {isAITrigger && (
          <div className="rounded-xl border p-3" style={{ background: "#D7F2E8", borderColor: "#1D9E7540" }}>
            <div className="flex items-center gap-2 mb-1.5" style={{ color: "#0F6E56" }}>
              <Sparkles size={13} />
              <span className="text-xs font-semibold">Gatilho Inteligente — Claude decide</span>
            </div>
            <p className="text-xs leading-relaxed" style={{ color: "#0F6E56" }}>
              Antes de disparar a ação, Claude analisa o perfil 360 do aluno e avalia se a intervenção
              é realmente necessária. Elimina falsos positivos e notificações desnecessárias.
              Requer API key configurada — usa inatividade como fallback.
            </p>
          </div>
        )}
        {["send_whatsapp","send_email","notify","create_task"].includes(actionType) && (
          <FormField label={actionType === "create_task" ? "Descrição da tarefa" : "Mensagem"}>
            <Textarea
              {...register("message")}
              rows={3}
              placeholder={
                actionType === "send_whatsapp"
                  ? "Use {nome}, {plano}, {dias} como variáveis dinâmicas..."
                  : actionType === "create_task"
                  ? "Descrição da tarefa criada automaticamente..."
                  : "Conteúdo da mensagem..."
              }
            />
            {actionType === "send_whatsapp" && msgValue && (
              <div className="mt-2 rounded-xl p-3" style={{ background: "#E8F9F0", border: "1px solid #1D9E7530" }}>
                <p className="text-[10px] font-semibold uppercase tracking-wide mb-1" style={{ color: "#0F6E56" }}>Preview</p>
                <p className="text-xs" style={{ color: "#0F6E56" }}>
                  {msgValue
                    .replace(/\{nome\}/g, "Ana Silva")
                    .replace(/\{plano\}/g, "Mensal")
                    .replace(/\{dias\}/g, "7")}
                </p>
              </div>
            )}
          </FormField>
        )}

        <div className="flex items-center justify-between rounded-xl border border-lovable-border bg-lovable-surface-soft px-3 py-2.5">
          <div>
            <p className="text-sm font-medium text-lovable-ink">Ativar agora</p>
            <p className="text-xs text-lovable-ink-muted">Começa a rodar no próximo ciclo diário</p>
          </div>
          <Controller name="is_active" control={control}
            render={({ field }) => (
              <button type="button" onClick={() => field.onChange(!field.value)} className="transition">
                {field.value
                  ? <ToggleRight size={28} className="text-lovable-primary" />
                  : <ToggleLeft size={28} className="text-lovable-ink-muted" />}
              </button>
            )}
          />
        </div>

        <Button type="submit" variant="primary" disabled={isPending} className="w-full">
          {isPending
            ? (isEdit ? "Salvando..." : "Criando...")
            : (isEdit ? "Salvar Alterações" : "Criar Regra")}
        </Button>
      </form>
    </Drawer>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export function AutomationsPage() {
  const queryClient = useQueryClient();
  const [executing, setExecuting]         = useState(false);
  const [execResults, setExecResults]     = useState<ExecResult[] | null>(null);
  const [drawerOpen, setDrawerOpen]       = useState(false);
  const [ruleToEdit, setRuleToEdit]       = useState<AutomationRule | null>(null);
  const [prefill, setPrefill]             = useState<typeof TEMPLATES[0] | null>(null);
  const [showTemplates, setShowTemplates] = useState(false);

  const rulesQuery = useQuery({
    queryKey: ["automations", "rules"],
    queryFn:  () => automationService.listRules(),
    staleTime: 30_000,
  });

  const toggleMutation = useMutation({
    mutationFn: ({ id, is_active }: { id: string; is_active: boolean }) =>
      automationService.updateRule(id, { is_active }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["automations", "rules"] }),
    onError: () => toast.error("Não foi possível alterar a regra."),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => automationService.deleteRule(id),
    onSuccess: () => {
      toast.success("Regra excluída.");
      void queryClient.invalidateQueries({ queryKey: ["automations", "rules"] });
    },
    onError: () => toast.error("Erro ao excluir."),
  });

  const seedMutation = useMutation({
    mutationFn: () => automationService.seedDefaults(),
    onSuccess: (data) => {
      toast.success(`${data.length} regras criadas!`);
      void queryClient.invalidateQueries({ queryKey: ["automations", "rules"] });
    },
    onError: () => toast.error("Erro ao criar regras padrão."),
  });

  const handleExecuteAll = async () => {
    setExecuting(true);
    setExecResults(null);
    try {
      const results = await automationService.executeAll();
      const typed = results as unknown as ExecResult[];
      const acted = typed.filter(r => !["skipped","error"].includes(r.status)).length;
      setExecResults(typed);
      toast.success(`${acted} ações realizadas.`);
    } catch {
      toast.error("Erro ao executar automações.");
    } finally {
      setExecuting(false);
      void queryClient.invalidateQueries({ queryKey: ["automations", "rules"] });
    }
  };

  const openCreate = () => {
    setRuleToEdit(null);
    setPrefill(null);
    setDrawerOpen(true);
    setShowTemplates(false);
  };

  if (rulesQuery.isLoading) return <LoadingPanel text="Carregando automações..." />;
  if (rulesQuery.isError)   return <LoadingPanel text="Erro ao carregar automações." />;

  const rules    = rulesQuery.data ?? [];
  const active   = rules.filter(r => r.is_active);
  const inactive = rules.filter(r => !r.is_active);

  // Group active rules by trigger type
  const triggerGroups: Record<string, AutomationRule[]> = {};
  for (const r of active) {
    if (!triggerGroups[r.trigger_type]) triggerGroups[r.trigger_type] = [];
    triggerGroups[r.trigger_type].push(r);
  }

  return (
    <section className="space-y-6">
      {/* Header */}
      <header className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Zap size={20} className="text-lovable-primary" />
            <h2 className="font-heading text-3xl font-bold text-lovable-ink">Automações</h2>
          </div>
          <p className="text-sm text-lovable-ink-muted">
            Regras executadas automaticamente após o processamento diário de risco (2h UTC).
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {rules.length === 0 && (
            <Button variant="ghost" onClick={() => seedMutation.mutate()} disabled={seedMutation.isPending}>
              <LayoutTemplate size={14} />
              {seedMutation.isPending ? "Criando..." : "Regras Padrão"}
            </Button>
          )}
          <Button variant="ghost" onClick={() => setShowTemplates(v => !v)}>
            <LayoutTemplate size={14} />
            Templates
            {showTemplates ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
          </Button>
          <Button variant="ghost" onClick={openCreate}>
            <Plus size={14} />Nova Regra
          </Button>
          <Button variant="primary" onClick={() => void handleExecuteAll()}
            disabled={executing || active.length === 0}>
            {executing
              ? <><Timer size={14} className="animate-spin" />Executando...</>
              : <><Play size={14} />Executar Agora</>}
          </Button>
        </div>
      </header>
      {/* Stats */}
      {rules.length > 0 && <StatsStrip rules={rules} />}

      {/* Template Gallery */}
      {showTemplates && (
        <div className="rounded-2xl border border-lovable-border bg-lovable-surface overflow-hidden">
          <div className="flex items-center justify-between border-b border-lovable-border px-4 py-3 bg-lovable-surface-soft">
            <div>
              <p className="text-sm font-semibold text-lovable-ink">Templates prontos</p>
              <p className="text-xs text-lovable-ink-muted">Clique para criar uma regra pré-configurada</p>
            </div>
            <button type="button" onClick={() => setShowTemplates(false)}
              className="text-xs text-lovable-ink-muted hover:text-lovable-ink px-2 py-1 rounded-lg hover:bg-lovable-surface transition">
              Fechar
            </button>
          </div>
          <div className="p-4">
            <TemplateGallery onSelect={t => { setPrefill(t); setRuleToEdit(null); setDrawerOpen(true); setShowTemplates(false); }} />
          </div>
        </div>
      )}

      {/* Empty state */}
      {rules.length === 0 && (
        <div className="rounded-2xl border border-dashed border-lovable-border bg-lovable-surface p-12 text-center">
          <Zap size={48} className="mx-auto mb-4 text-lovable-ink-muted/30" />
          <p className="text-lg font-semibold text-lovable-ink mb-1">Nenhuma regra configurada</p>
          <p className="text-sm text-lovable-ink-muted mb-4">
            Use os templates prontos ou crie sua primeira regra personalizada.
          </p>
          <div className="flex gap-2 justify-center">
            <Button variant="ghost" onClick={() => seedMutation.mutate()} disabled={seedMutation.isPending}>
              <LayoutTemplate size={14} />{seedMutation.isPending ? "Criando..." : "Regras Padrão"}
            </Button>
            <Button variant="primary" onClick={openCreate}><Plus size={14} />Nova Regra</Button>
          </div>
        </div>
      )}

      {/* Active rules grouped by trigger */}
      {Object.entries(triggerGroups).map(([triggerType, groupRules]) => {
        const meta = TRIGGER_META[triggerType];
        return (
          <div key={triggerType}>
            <div className="flex items-center gap-2 mb-2 px-0.5">
              <span className="text-sm" style={{ color: meta?.color }}>{meta?.icon}</span>
              <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: meta?.color }}>
                {meta?.label ?? triggerType}
              </span>
              <span className="text-xs text-lovable-ink-muted">
                — {groupRules.length} regra{groupRules.length !== 1 ? "s" : ""}
              </span>
            </div>
            <div className="space-y-2">
              {groupRules.map(rule => (
                <RulePipelineCard
                  key={rule.id}
                  rule={rule}
                  onToggle={v => toggleMutation.mutate({ id: rule.id, is_active: v })}
                  onEdit={() => { setRuleToEdit(rule); setPrefill(null); setDrawerOpen(true); }}
                  onDelete={() => deleteMutation.mutate(rule.id)}
                  isToggling={toggleMutation.isPending}
                />
              ))}
            </div>
          </div>
        );
      })}

      {/* Inactive rules */}
      {inactive.length > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-2 px-0.5">
            <span className="text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">
              Inativas — {inactive.length}
            </span>
          </div>
          <div className="space-y-2">
            {inactive.map(rule => (
              <RulePipelineCard
                key={rule.id}
                rule={rule}
                onToggle={v => toggleMutation.mutate({ id: rule.id, is_active: v })}
                onEdit={() => { setRuleToEdit(rule); setPrefill(null); setDrawerOpen(true); }}
                onDelete={() => deleteMutation.mutate(rule.id)}
                isToggling={toggleMutation.isPending}
              />
            ))}
          </div>
        </div>
      )}

      {/* Exec results */}
      {execResults !== null && (
        <ExecResultsPanel results={execResults} rules={rules} onClose={() => setExecResults(null)} />
      )}

      {/* Info */}
      <div className="rounded-2xl border border-lovable-border bg-lovable-surface-soft p-4">
        <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted flex items-center gap-2">
          <Eye size={12} />Como funciona
        </h3>
        <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
          {[
            { icon: Timer,        text: "Execução automática diária às 2h UTC, após o processamento de risco." },
            { icon: Activity,     text: "Cada regra filtra alunos pelo gatilho e executa a ação configurada." },
            { icon: CheckCircle2, text: "Tasks duplicadas não são criadas — verificação automática por título." },
            { icon: Sparkles,     text: "Gatilho ✦ IA: Claude analisa o contexto do aluno antes de disparar, eliminando falsos positivos." },
          ].map((item, i) => (
            <div key={i} className="flex items-start gap-2">
              <item.icon size={12} className="text-lovable-ink-muted mt-0.5 shrink-0" />
              <p className="text-xs text-lovable-ink-muted leading-relaxed">{item.text}</p>
            </div>
          ))}
        </div>
      </div>

      <RuleFormDrawer
        open={drawerOpen}
        mode={ruleToEdit ? "edit" : "create"}
        rule={ruleToEdit}
        prefillTemplate={prefill}
        onClose={() => { setDrawerOpen(false); setRuleToEdit(null); setPrefill(null); }}
        onSaved={() => void queryClient.invalidateQueries({ queryKey: ["automations", "rules"] })}
      />
    </section>
  );
}
