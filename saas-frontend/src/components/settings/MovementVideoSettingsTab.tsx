import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CameraOff, Loader2, ShieldCheck, Video } from "lucide-react";
import toast from "react-hot-toast";

import { movementVideoService } from "../../services/movementVideoService";
import type { MovementVideoAiSettings } from "../../types";
import { Badge, Button, Card, CardContent, CardHeader, CardTitle, FormField, Input } from "../ui2";

const safeDefaults: MovementVideoAiSettings = {
  enabled: false,
  mode: "coach_review",
  auto_send_enabled: false,
  require_image_consent: true,
  store_original_video: false,
  retention_days: 30,
  max_video_mb: 100,
  max_duration_seconds: 120,
  allowed_media_types: ["video/mp4", "video/quicktime", "video/webm"],
};

export function MovementVideoSettingsTab() {
  const queryClient = useQueryClient();
  const settingsQuery = useQuery({
    queryKey: ["movement-video-ai", "settings"],
    queryFn: () => movementVideoService.getSettings(),
  });
  const [draft, setDraft] = useState<MovementVideoAiSettings>(safeDefaults);

  useEffect(() => {
    if (settingsQuery.data) setDraft(settingsQuery.data);
  }, [settingsQuery.data]);

  const saveMutation = useMutation({
    mutationFn: () =>
      movementVideoService.updateSettings({
        ...draft,
        mode: "coach_review",
        auto_send_enabled: false,
        store_original_video: false,
      }),
    onSuccess: async (payload) => {
      setDraft(payload);
      await queryClient.invalidateQueries({ queryKey: ["movement-video-ai"] });
      toast.success("Cordex Motion atualizado.");
    },
    onError: () => toast.error("Nao foi possivel salvar o Cordex Motion."),
  });

  if (settingsQuery.isLoading) {
    return (
      <Card>
        <CardContent className="flex items-center gap-3 p-5 text-sm text-lovable-ink-muted">
          <Loader2 size={18} className="animate-spin text-lovable-primary" />
          Carregando Cordex Motion...
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Video size={18} className="text-lovable-primary" />
            Cordex Motion
          </CardTitle>
          <p className="text-sm text-lovable-ink-muted">
            V1 supervisionada: o video vira evidencia para o professor revisar. O sistema nao da diagnostico autonomo e nao envia feedback sozinho.
          </p>
        </CardHeader>
        <CardContent className="space-y-5">
          <div className="grid gap-3 lg:grid-cols-3">
            <StatusCard title="Modo" value="Coach review" description="Professor revisa tudo antes do aluno." tone="info" />
            <StatusCard title="Autoenvio" value="Desligado" description="Feedback nunca sai automatico nesta V1." tone="warning" />
            <StatusCard title="Video original" value="Nao armazenar" description="Usar referencia segura por padrao." tone="success" />
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
                <span className="block text-sm font-semibold text-lovable-ink">Habilitar Cordex Motion</span>
                <span className="mt-1 block text-xs text-lovable-ink-muted">Permite criar reviews de video para professor revisar.</span>
              </span>
            </label>
            <label className="flex items-start gap-3 rounded-2xl border border-lovable-border bg-lovable-surface-soft p-4">
              <input
                type="checkbox"
                className="mt-1 h-4 w-4"
                checked={draft.require_image_consent}
                onChange={(event) => setDraft((current) => ({ ...current, require_image_consent: event.target.checked }))}
              />
              <span>
                <span className="block text-sm font-semibold text-lovable-ink">Exigir consentimento de imagem</span>
                <span className="mt-1 block text-xs text-lovable-ink-muted">Bloqueia review quando o aluno nao autorizou uso de imagem/video.</span>
              </span>
            </label>
          </div>

          <div className="grid gap-3 md:grid-cols-3">
            <FormField label="Retencao de evidencia (dias)">
              <Input
                type="number"
                value={draft.retention_days}
                onChange={(event) => setDraft((current) => ({ ...current, retention_days: Number(event.target.value) || 30 }))}
              />
            </FormField>
            <FormField label="Tamanho maximo (MB)">
              <Input
                type="number"
                value={draft.max_video_mb}
                onChange={(event) => setDraft((current) => ({ ...current, max_video_mb: Number(event.target.value) || 100 }))}
              />
            </FormField>
            <FormField label="Duracao maxima (segundos)">
              <Input
                type="number"
                value={draft.max_duration_seconds}
                onChange={(event) => setDraft((current) => ({ ...current, max_duration_seconds: Number(event.target.value) || 120 }))}
              />
            </FormField>
          </div>

          <div className="rounded-2xl border border-lovable-border bg-lovable-bg-muted/60 p-4">
            <p className="flex items-center gap-2 text-sm font-semibold text-lovable-ink">
              <ShieldCheck size={16} className="text-emerald-400" />
              Guardrails ativos
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              <Badge variant="neutral">sem diagnostico autonomo</Badge>
              <Badge variant="neutral">sem autoenvio</Badge>
              <Badge variant="neutral">consentimento de imagem</Badge>
              <Badge variant="neutral">limite de tamanho/duracao</Badge>
              {draft.allowed_media_types.map((type) => (
                <Badge key={type} variant="info">
                  {type}
                </Badge>
              ))}
            </div>
          </div>

          <div className="rounded-2xl border border-amber-500/20 bg-amber-500/8 p-4">
            <p className="flex items-center gap-2 text-sm font-semibold text-lovable-ink">
              <CameraOff size={16} className="text-amber-300" />
              Limite honesto da V1
            </p>
            <p className="mt-2 text-xs text-lovable-ink-muted">
              Ainda nao ha correcao biomecanica automatica quadro a quadro. O sistema organiza evidencia, bloqueia risco e prepara feedback para o professor.
            </p>
          </div>

          <div className="flex justify-end">
            <Button variant="primary" onClick={() => saveMutation.mutate()} disabled={saveMutation.isPending}>
              {saveMutation.isPending ? "Salvando..." : "Salvar Cordex Motion"}
            </Button>
          </div>
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
