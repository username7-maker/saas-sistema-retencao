import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bot, Loader2, MessageCircle, ShieldAlert, Video } from "lucide-react";
import toast from "react-hot-toast";

import { studentPersonalAiService } from "../../services/studentPersonalAiService";
import type { StudentPersonalAiSettings } from "../../types";
import { Badge, Button, Card, CardContent, CardHeader, CardTitle, FormField, Input } from "../ui2";

const safeDefaults: StudentPersonalAiSettings = {
  enabled: false,
  mode: "draft_only",
  auto_send_enabled: false,
  kommo_required: true,
  personal_ai_enabled: true,
  movement_video_enabled: true,
  require_member_match: true,
  require_communication_consent: true,
  require_image_consent_for_video: true,
  sensitive_escalation_enabled: true,
  max_drafts_per_day: 50,
  human_recent_activity_cooldown_hours: 24,
  allowed_domains: [
    "training_guidance",
    "routine_support",
    "assessment_explanation",
    "body_composition_explanation",
    "movement_video",
  ],
};

export function StudentPersonalAiSettingsTab() {
  const queryClient = useQueryClient();
  const settingsQuery = useQuery({
    queryKey: ["student-personal-ai", "settings"],
    queryFn: () => studentPersonalAiService.getSettings(),
  });
  const draftsQuery = useQuery({
    queryKey: ["student-personal-ai", "drafts"],
    queryFn: () => studentPersonalAiService.listDrafts(),
    staleTime: 30_000,
  });
  const [draft, setDraft] = useState<StudentPersonalAiSettings>(safeDefaults);

  useEffect(() => {
    if (settingsQuery.data) setDraft(settingsQuery.data);
  }, [settingsQuery.data]);

  const saveMutation = useMutation({
    mutationFn: () =>
      studentPersonalAiService.updateSettings({
        ...draft,
        auto_send_enabled: false,
        mode: "draft_only",
        require_member_match: true,
      }),
    onSuccess: async (payload) => {
      setDraft(payload);
      await queryClient.invalidateQueries({ queryKey: ["student-personal-ai"] });
      toast.success("Personal IA do aluno atualizado.");
    },
    onError: () => toast.error("Nao foi possivel salvar o Personal IA do aluno."),
  });

  const prepareMutation = useMutation({
    mutationFn: (draftId: string) => studentPersonalAiService.prepareKommo(draftId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["student-personal-ai", "drafts"] });
      toast.success("Rascunho preparado na Kommo.");
    },
    onError: () => toast.error("Nao foi possivel preparar na Kommo."),
  });

  if (settingsQuery.isLoading) {
    return (
      <Card>
        <CardContent className="flex items-center gap-3 p-5 text-sm text-lovable-ink-muted">
          <Loader2 size={18} className="animate-spin text-lovable-primary" />
          Carregando Personal IA do aluno...
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
            Personal IA do aluno via Kommo
          </CardTitle>
          <p className="text-sm text-lovable-ink-muted">
            O aluno escreve ou envia video na Kommo. O sistema identifica o aluno, prepara rascunho/review e entrega para a equipe revisar. Autoenvio fica desligado.
          </p>
        </CardHeader>
        <CardContent className="space-y-5">
          <div className="grid gap-3 lg:grid-cols-3">
            <StatusCard title="Canal" value="Kommo" description="Entrada e preparo operacional ficam na conversa Kommo." tone="info" />
            <StatusCard title="Modo" value="Draft-only" description="Professor ou equipe revisa antes de responder." tone="success" />
            <StatusCard title="Autoenvio" value="Desligado" description="Travado nesta V1 para evitar resposta autonoma." tone="warning" />
          </div>

          <div className="grid gap-3 md:grid-cols-2">
            <ToggleCard
              checked={draft.enabled}
              title="Habilitar entrada do aluno"
              description="Processa mensagens tecnicas e videos recebidos pela Kommo."
              onChange={(checked) => setDraft((current) => ({ ...current, enabled: checked }))}
            />
            <ToggleCard
              checked={draft.kommo_required}
              title="Exigir Kommo como canal principal"
              description="Se Kommo nao estiver pronta, o draft fica bloqueado em vez de prometer execucao."
              onChange={(checked) => setDraft((current) => ({ ...current, kommo_required: checked }))}
            />
            <ToggleCard
              checked={draft.personal_ai_enabled}
              title="Perguntas tecnicas por texto"
              description="Cria rascunhos sobre treino, rotina, avaliacao e bioimpedancia."
              onChange={(checked) => setDraft((current) => ({ ...current, personal_ai_enabled: checked }))}
            />
            <ToggleCard
              checked={draft.movement_video_enabled}
              title="Video do aluno"
              description="Cria review supervisionado quando o aluno envia video pela Kommo."
              onChange={(checked) => setDraft((current) => ({ ...current, movement_video_enabled: checked }))}
            />
            <ToggleCard
              checked={draft.require_communication_consent}
              title="Exigir consentimento de comunicacao"
              description="Sem consentimento, o sistema bloqueia e explica o motivo."
              onChange={(checked) => setDraft((current) => ({ ...current, require_communication_consent: checked }))}
            />
            <ToggleCard
              checked={draft.require_image_consent_for_video}
              title="Exigir consentimento de imagem"
              description="Videos ficam bloqueados se nao houver consentimento de imagem."
              onChange={(checked) => setDraft((current) => ({ ...current, require_image_consent_for_video: checked }))}
            />
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
              {saveMutation.isPending ? "Salvando..." : "Salvar Personal IA do aluno"}
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <MessageCircle size={18} className="text-lovable-primary" />
            Entradas recentes do aluno
          </CardTitle>
          <p className="text-sm text-lovable-ink-muted">Rascunhos e videos capturados via Kommo para revisao humana.</p>
        </CardHeader>
        <CardContent className="space-y-3">
          {draftsQuery.isLoading ? (
            <div className="flex items-center gap-3 text-sm text-lovable-ink-muted">
              <Loader2 size={18} className="animate-spin text-lovable-primary" />
              Carregando entradas...
            </div>
          ) : null}
          {!draftsQuery.isLoading && drafts.length === 0 ? (
            <div className="rounded-2xl border border-lovable-border bg-lovable-surface-soft p-4 text-sm text-lovable-ink-muted">
              Nenhuma entrada do aluno ainda. Quando a Kommo receber perguntas tecnicas ou videos, elas aparecem aqui e na fila do professor.
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
                    <Badge variant={item.intent === "movement_video" ? "info" : "neutral"}>
                      {item.intent === "movement_video" ? "Video do aluno" : item.intent}
                    </Badge>
                    {item.movement_video_review_id ? (
                      <Badge variant="info">
                        <Video size={12} />
                        Review criado
                      </Badge>
                    ) : null}
                  </div>
                  <p className="mt-3 text-sm font-semibold text-lovable-ink">{item.summary}</p>
                  {item.received_message ? <p className="mt-1 text-xs text-lovable-ink-muted">Aluno: {item.received_message}</p> : null}
                </div>
                {item.status === "draft_ready" ? (
                  <Button variant="secondary" onClick={() => prepareMutation.mutate(item.id)} disabled={prepareMutation.isPending}>
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

function ToggleCard({
  checked,
  title,
  description,
  onChange,
}: {
  checked: boolean;
  title: string;
  description: string;
  onChange: (checked: boolean) => void;
}) {
  return (
    <label className="flex items-start gap-3 rounded-2xl border border-lovable-border bg-lovable-surface-soft p-4">
      <input type="checkbox" className="mt-1 h-4 w-4" checked={checked} onChange={(event) => onChange(event.target.checked)} />
      <span>
        <span className="block text-sm font-semibold text-lovable-ink">{title}</span>
        <span className="mt-1 block text-xs text-lovable-ink-muted">{description}</span>
      </span>
    </label>
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
