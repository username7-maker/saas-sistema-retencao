import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";

import { autopilotService } from "../../services/autopilotService";
import type { AutopilotSettings } from "../../types";
import { Badge, Button, Card, CardContent, CardHeader, CardTitle, FormField, Input } from "../ui2";
import { SkeletonList } from "../ui";

type ToggleKey =
  | "autopilot_enabled"
  | "autopilot_auto_close_enabled"
  | "autopilot_auto_send_enabled"
  | "retention_enabled"
  | "finance_enabled"
  | "sales_enabled"
  | "onboarding_enabled"
  | "assessment_enabled"
  | "nps_enabled";

const toggleLabels: Array<{ key: ToggleKey; label: string; description: string; warning?: boolean }> = [
  { key: "autopilot_enabled", label: "Autopilot ativo", description: "Liga a camada de auto-resolucao e escalonamento auditavel." },
  { key: "autopilot_auto_close_enabled", label: "Auto-fechamento", description: "Permite fechar tasks por eventos reais como check-in, pagamento e resposta." },
  {
    key: "autopilot_auto_send_enabled",
    label: "Auto-envio WhatsApp",
    description: "Envia automaticamente somente quando consentimento, horario e cooldown passam.",
    warning: true,
  },
  { key: "retention_enabled", label: "Retencao", description: "Permite politicas de ausencia e recuperacao." },
  { key: "finance_enabled", label: "Financeiro", description: "Permite resolver/acompanhar tasks financeiras." },
  { key: "sales_enabled", label: "Comercial", description: "Permite fluxo assistido de leads. Auto-send para leads fica bloqueado na V1." },
  { key: "onboarding_enabled", label: "Onboarding", description: "Permite boas-vindas e acompanhamento inicial." },
  { key: "assessment_enabled", label: "Avaliacoes", description: "Permite resolver tasks de avaliacao por eventos reais." },
  { key: "nps_enabled", label: "NPS / suporte", description: "Casos sensiveis sempre escalam para humano." },
];

const safeDefaults: AutopilotSettings = {
  autopilot_enabled: false,
  autopilot_auto_close_enabled: true,
  autopilot_auto_send_enabled: false,
  retention_enabled: true,
  finance_enabled: true,
  sales_enabled: false,
  onboarding_enabled: true,
  assessment_enabled: true,
  nps_enabled: true,
  business_hours_start: "08:00",
  business_hours_end: "20:00",
  max_auto_messages_per_member_per_week: 2,
  max_auto_messages_per_lead_per_week: 3,
  max_auto_actions_per_day: 100,
  max_human_tasks_created_by_autopilot_per_day: 25,
  default_timeout_hours: 48,
  human_recent_activity_cooldown_hours: 24,
  extra_data: {},
};

function ToggleRow({
  settings,
  toggleKey,
  label,
  description,
  warning,
  onChange,
}: {
  settings: AutopilotSettings;
  toggleKey: ToggleKey;
  label: string;
  description: string;
  warning?: boolean;
  onChange: (key: ToggleKey, value: boolean) => void;
}) {
  return (
    <label className="flex cursor-pointer items-start justify-between gap-4 rounded-2xl border border-lovable-border bg-lovable-bg-muted/70 p-4">
      <span>
        <span className="flex items-center gap-2 text-sm font-bold text-lovable-ink">
          {label}
          {warning ? <Badge variant="warning">cuidado</Badge> : null}
        </span>
        <span className="mt-1 block text-xs text-lovable-ink-muted">{description}</span>
      </span>
      <input
        type="checkbox"
        checked={Boolean(settings[toggleKey])}
        onChange={(event) => onChange(toggleKey, event.target.checked)}
        className="mt-1 h-5 w-5 accent-[hsl(var(--lovable-primary))]"
      />
    </label>
  );
}

export function AutopilotSettingsTab() {
  const queryClient = useQueryClient();
  const settingsQuery = useQuery({
    queryKey: ["autopilot", "settings"],
    queryFn: autopilotService.getSettings,
  });
  const metricsQuery = useQuery({
    queryKey: ["autopilot", "metrics"],
    queryFn: autopilotService.getMetrics,
    staleTime: 60_000,
  });
  const [draft, setDraft] = useState<AutopilotSettings>(safeDefaults);

  useEffect(() => {
    if (settingsQuery.data) setDraft(settingsQuery.data);
  }, [settingsQuery.data]);

  const updateMutation = useMutation({
    mutationFn: (payload: Partial<AutopilotSettings>) => autopilotService.updateSettings(payload),
    onSuccess: (settings) => {
      setDraft(settings);
      void queryClient.invalidateQueries({ queryKey: ["autopilot"] });
      toast.success("Autopilot atualizado.");
    },
    onError: () => toast.error("Nao foi possivel salvar Autopilot."),
  });

  function setToggle(key: ToggleKey, value: boolean) {
    setDraft((current) => ({ ...current, [key]: value }));
  }

  function setNumber(key: keyof AutopilotSettings, value: string) {
    const parsed = Number(value);
    setDraft((current) => ({ ...current, [key]: Number.isFinite(parsed) ? parsed : 0 }));
  }

  const metrics = metricsQuery.data;

  if (settingsQuery.isLoading) {
    return (
      <Card>
        <CardContent className="p-5">
          <SkeletonList rows={5} cols={2} />
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Task Autopilot</CardTitle>
          <p className="text-sm text-lovable-ink-muted">
            Comece pelo modo seguro: auto-fechamento ligado e auto-envio desligado. O sistema reduz tasks humanas sem atravessar atendimento sensivel.
          </p>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-3 lg:grid-cols-2">
            {toggleLabels.map((item) => (
              <ToggleRow
                key={item.key}
                settings={draft}
                toggleKey={item.key}
                label={item.label}
                description={item.description}
                warning={item.warning}
                onChange={setToggle}
              />
            ))}
          </div>

          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <FormField label="Inicio do horario permitido">
              <Input value={draft.business_hours_start} onChange={(event) => setDraft((current) => ({ ...current, business_hours_start: event.target.value }))} />
            </FormField>
            <FormField label="Fim do horario permitido">
              <Input value={draft.business_hours_end} onChange={(event) => setDraft((current) => ({ ...current, business_hours_end: event.target.value }))} />
            </FormField>
            <FormField label="Mensagens por aluno/semana">
              <Input
                type="number"
                value={draft.max_auto_messages_per_member_per_week}
                onChange={(event) => setNumber("max_auto_messages_per_member_per_week", event.target.value)}
              />
            </FormField>
            <FormField label="Timeout padrao (h)">
              <Input type="number" value={draft.default_timeout_hours} onChange={(event) => setNumber("default_timeout_hours", event.target.value)} />
            </FormField>
          </div>

          <div className="flex justify-end">
            <Button onClick={() => updateMutation.mutate(draft)} disabled={updateMutation.isPending}>
              {updateMutation.isPending ? "Salvando..." : "Salvar Autopilot"}
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Metricas operacionais</CardTitle>
          <p className="text-sm text-lovable-ink-muted">Leitura simples para o gestor acompanhar resolucao automatica e bloqueios.</p>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 md:grid-cols-4">
            <div className="rounded-2xl border border-lovable-border bg-lovable-bg-muted/70 p-4">
              <p className="text-xs uppercase tracking-[0.18em] text-lovable-ink-muted">Actions</p>
              <p className="mt-2 text-2xl font-bold text-lovable-ink">{metrics?.automation_actions.created ?? 0}</p>
            </div>
            <div className="rounded-2xl border border-lovable-border bg-lovable-bg-muted/70 p-4">
              <p className="text-xs uppercase tracking-[0.18em] text-lovable-ink-muted">Auto-resolvidas</p>
              <p className="mt-2 text-2xl font-bold text-lovable-ink">{metrics?.tasks.auto_closed ?? 0}</p>
            </div>
            <div className="rounded-2xl border border-lovable-border bg-lovable-bg-muted/70 p-4">
              <p className="text-xs uppercase tracking-[0.18em] text-lovable-ink-muted">Escaladas</p>
              <p className="mt-2 text-2xl font-bold text-lovable-ink">{metrics?.automation_actions.escalated ?? 0}</p>
            </div>
            <div className="rounded-2xl border border-lovable-border bg-lovable-bg-muted/70 p-4">
              <p className="text-xs uppercase tracking-[0.18em] text-lovable-ink-muted">Bloqueadas</p>
              <p className="mt-2 text-2xl font-bold text-lovable-ink">{metrics?.automation_actions.blocked ?? 0}</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
