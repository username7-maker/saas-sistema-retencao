import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bot, Loader2, MessageSquareText, ShieldAlert } from "lucide-react";
import toast from "react-hot-toast";

import { aiServiceAgentService } from "../../services/aiServiceAgentService";
import type { AiServiceAgentSettings } from "../../types";
import { Badge, Button, Card, CardContent, CardHeader, CardTitle, FormField, Input } from "../ui2";

const safeDefaults: AiServiceAgentSettings = {
  enabled: false,
  mode: "draft_only",
  auto_send_enabled: false,
  sensitive_escalation_enabled: true,
  kommo_required: true,
  max_drafts_per_day: 100,
  human_recent_activity_cooldown_hours: 24,
  allowed_intents: ["general", "onboarding", "retention", "assessment", "finance", "sales", "support"],
};

export function AiServiceAgentSettingsTab() {
  const queryClient = useQueryClient();
  const settingsQuery = useQuery({
    queryKey: ["ai-service-agent", "settings"],
    queryFn: () => aiServiceAgentService.getSettings(),
  });
  const draftsQuery = useQuery({
    queryKey: ["ai-service-agent", "drafts"],
    queryFn: () => aiServiceAgentService.listDrafts(),
    staleTime: 30_000,
  });
  const [draft, setDraft] = useState<AiServiceAgentSettings>(safeDefaults);

  useEffect(() => {
    if (settingsQuery.data) setDraft(settingsQuery.data);
  }, [settingsQuery.data]);

  const saveMutation = useMutation({
    mutationFn: () => aiServiceAgentService.updateSettings({ ...draft, auto_send_enabled: false, mode: "draft_only" }),
    onSuccess: async (payload) => {
      setDraft(payload);
      await queryClient.invalidateQueries({ queryKey: ["ai-service-agent"] });
      toast.success("Cordex Agent atualizado.");
    },
    onError: () => toast.error("Nao foi possivel salvar o Cordex Agent."),
  });

  const prepareMutation = useMutation({
    mutationFn: (draftId: string) => aiServiceAgentService.prepareKommo(draftId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["ai-service-agent", "drafts"] });
      toast.success("Rascunho preparado na Kommo para revisao humana.");
    },
    onError: () => toast.error("Nao foi possivel preparar o rascunho na Kommo."),
  });

  if (settingsQuery.isLoading) {
    return (
      <Card>
        <CardContent className="flex items-center gap-3 p-5 text-sm text-lovable-ink-muted">
          <Loader2 size={18} className="animate-spin text-lovable-primary" />
          Carregando Cordex Agent...
        </CardContent>
      </Card>
    );
  }

  const drafts = draftsQuery.data ?? [];

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bot size={18} className="text-lovable-primary" />
            Cordex Agent Kommo
          </CardTitle>
          <p className="text-sm text-lovable-ink-muted">
            V1 em modo rascunho: le mensagem recebida na Kommo, classifica risco e prepara resposta curta para humano revisar. Autoenvio fica desligado.
          </p>
        </CardHeader>
        <CardContent className="space-y-5">
          <div className="grid gap-3 lg:grid-cols-3">
            <StatusCard title="Modo" value="Draft-only" description="O operador sempre revisa e envia pela Kommo." tone="info" />
            <StatusCard
              title="Autoenvio"
              value="Desligado"
              description="Travado nesta versao para evitar resposta autonoma."
              tone="warning"
            />
            <StatusCard
              title="Guardrails"
              value={draft.sensitive_escalation_enabled ? "Ativos" : "Revisar"}
              description="Cancelamento, dor, contestacao e opt-out escalam."
              tone={draft.sensitive_escalation_enabled ? "success" : "warning"}
            />
          </div>

          <div className="grid gap-3 md:grid-cols-2">
            <label className="flex items-start gap-3 rounded-2xl border border-lovable-border bg-lovable-surface-soft p-4">
              <input
                type="checkbox"
                className="mt-1 h-4 w-4"
                checked={draft.enabled}
                onChange={(event) => setDraft((current) => ({ ...current, enabled: event.target.checked }))}
              />
              <span>
                <span className="block text-sm font-semibold text-lovable-ink">Habilitar agente IA</span>
                <span className="mt-1 block text-xs text-lovable-ink-muted">Processa mensagens Kommo inbound e cria rascunhos auditaveis.</span>
              </span>
            </label>
            <label className="flex items-start gap-3 rounded-2xl border border-lovable-border bg-lovable-surface-soft p-4">
              <input
                type="checkbox"
                className="mt-1 h-4 w-4"
                checked={draft.kommo_required}
                onChange={(event) => setDraft((current) => ({ ...current, kommo_required: event.target.checked }))}
              />
              <span>
                <span className="block text-sm font-semibold text-lovable-ink">Exigir Kommo pronta</span>
                <span className="mt-1 block text-xs text-lovable-ink-muted">Se Kommo nao estiver configurada como principal, o draft fica bloqueado.</span>
              </span>
            </label>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <FormField label="Maximo de rascunhos por dia">
              <Input
                type="number"
                value={draft.max_drafts_per_day}
                onChange={(event) =>
                  setDraft((current) => ({ ...current, max_drafts_per_day: Number(event.target.value) || 0 }))
                }
              />
            </FormField>
            <FormField label="Cooldown apos atendimento humano (h)">
              <Input
                type="number"
                value={draft.human_recent_activity_cooldown_hours}
                onChange={(event) =>
                  setDraft((current) => ({ ...current, human_recent_activity_cooldown_hours: Number(event.target.value) || 0 }))
                }
              />
            </FormField>
          </div>

          <div className="flex justify-end">
            <Button variant="primary" onClick={() => saveMutation.mutate()} disabled={saveMutation.isPending}>
              {saveMutation.isPending ? "Salvando..." : "Salvar Cordex Agent"}
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <MessageSquareText size={18} className="text-lovable-primary" />
            Rascunhos recentes
          </CardTitle>
          <p className="text-sm text-lovable-ink-muted">Amostra dos drafts criados pelo agente para revisao humana.</p>
        </CardHeader>
        <CardContent className="space-y-3">
          {draftsQuery.isLoading ? (
            <div className="flex items-center gap-3 text-sm text-lovable-ink-muted">
              <Loader2 size={18} className="animate-spin text-lovable-primary" />
              Carregando rascunhos...
            </div>
          ) : null}
          {!draftsQuery.isLoading && drafts.length === 0 ? (
            <div className="rounded-2xl border border-lovable-border bg-lovable-surface-soft p-4 text-sm text-lovable-ink-muted">
              Nenhum rascunho gerado ainda. Quando a Kommo enviar mensagens inbound, elas aparecem aqui.
            </div>
          ) : null}
          {drafts.slice(0, 8).map((item) => (
            <div key={item.id} className="rounded-2xl border border-lovable-border bg-lovable-bg-muted/60 p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant={item.status === "draft_ready" ? "success" : item.status === "blocked" ? "warning" : "info"}>
                      {item.status === "draft_ready" ? "Rascunho pronto" : item.status}
                    </Badge>
                    <Badge variant={item.sensitivity === "sensitive" ? "danger" : "neutral"}>{item.intent}</Badge>
                  </div>
                  <p className="mt-3 text-sm font-semibold text-lovable-ink">{item.summary}</p>
                  {item.received_message ? <p className="mt-1 text-xs text-lovable-ink-muted">Recebida: {item.received_message}</p> : null}
                </div>
                {item.status === "draft_ready" ? (
                  <Button
                    variant="secondary"
                    onClick={() => prepareMutation.mutate(item.id)}
                    disabled={prepareMutation.isPending}
                  >
                    Preparar na Kommo
                  </Button>
                ) : null}
              </div>
              {item.draft_reply ? (
                <div className="mt-3 rounded-xl border border-lovable-primary/20 bg-lovable-primary/10 p-3 text-sm text-lovable-ink">
                  {item.draft_reply}
                </div>
              ) : null}
              {item.blocked_reasons.length > 0 ? (
                <div className="mt-3 flex items-start gap-2 text-xs text-lovable-warning">
                  <ShieldAlert size={14} className="mt-0.5 shrink-0" />
                  Bloqueios: {item.blocked_reasons.join(", ")}
                </div>
              ) : null}
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}

function StatusCard({
  title,
  value,
  description,
  tone,
}: {
  title: string;
  value: string;
  description: string;
  tone: "success" | "warning" | "info";
}) {
  const toneClass =
    tone === "success"
      ? "border-emerald-500/20 bg-emerald-500/8"
      : tone === "warning"
        ? "border-amber-500/20 bg-amber-500/8"
        : "border-blue-500/20 bg-blue-500/8";

  return (
    <div className={`rounded-2xl border p-4 ${toneClass}`}>
      <p className="text-[11px] font-semibold uppercase tracking-wide text-lovable-ink-muted">{title}</p>
      <p className="mt-2 text-lg font-semibold text-lovable-ink">{value}</p>
      <p className="mt-1 text-xs text-lovable-ink-muted">{description}</p>
    </div>
  );
}
