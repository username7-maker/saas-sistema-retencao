import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Dumbbell, Loader2, ShieldCheck, Sparkles } from "lucide-react";
import toast from "react-hot-toast";

import { personalAiService } from "../../services/personalAiService";
import type { PersonalAiSettings } from "../../types";
import { Badge, Button, Card, CardContent, CardHeader, CardTitle, FormField, Input } from "../ui2";

const safeDefaults: PersonalAiSettings = {
  enabled: false,
  mode: "coach_review",
  auto_send_enabled: false,
  sensitive_escalation_enabled: true,
  kommo_prepare_enabled: true,
  max_drafts_per_day: 50,
  allowed_domains: [
    "training_guidance",
    "routine_support",
    "assessment_explanation",
    "body_composition_explanation",
  ],
};

export function PersonalAiSettingsTab() {
  const queryClient = useQueryClient();
  const settingsQuery = useQuery({
    queryKey: ["personal-ai", "settings"],
    queryFn: () => personalAiService.getSettings(),
  });
  const draftsQuery = useQuery({
    queryKey: ["personal-ai", "drafts"],
    queryFn: () => personalAiService.listDrafts(),
    staleTime: 30_000,
  });
  const [draft, setDraft] = useState<PersonalAiSettings>(safeDefaults);

  useEffect(() => {
    if (settingsQuery.data) setDraft(settingsQuery.data);
  }, [settingsQuery.data]);

  const saveMutation = useMutation({
    mutationFn: () => personalAiService.updateSettings({ ...draft, auto_send_enabled: false, mode: "coach_review" }),
    onSuccess: async (payload) => {
      setDraft(payload);
      await queryClient.invalidateQueries({ queryKey: ["personal-ai"] });
      toast.success("Personal IA atualizado.");
    },
    onError: () => toast.error("Nao foi possivel salvar o Personal IA."),
  });

  const prepareMutation = useMutation({
    mutationFn: (draftId: string) => personalAiService.prepareKommo(draftId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["personal-ai", "drafts"] });
      toast.success("Orientacao preparada na Kommo para revisao do professor.");
    },
    onError: () => toast.error("Nao foi possivel preparar na Kommo."),
  });

  if (settingsQuery.isLoading) {
    return (
      <Card>
        <CardContent className="flex items-center gap-3 p-5 text-sm text-lovable-ink-muted">
          <Loader2 size={18} className="animate-spin text-lovable-primary" />
          Carregando Personal IA...
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
            <Dumbbell size={18} className="text-lovable-primary" />
            Personal IA
          </CardTitle>
          <p className="text-sm text-lovable-ink-muted">
            V1 em modo professor revisa: usa avaliacao, bioimpedancia, treino ativo, metas e restricoes para criar rascunhos tecnicos supervisionados.
          </p>
        </CardHeader>
        <CardContent className="space-y-5">
          <div className="grid gap-3 lg:grid-cols-3">
            <StatusCard title="Modo" value="Coach review" description="Professor sempre revisa antes de usar." tone="info" />
            <StatusCard title="Autoenvio" value="Desligado" description="Sem resposta autonoma ao aluno nesta V1." tone="warning" />
            <StatusCard
              title="Seguranca"
              value={draft.sensitive_escalation_enabled ? "Ativa" : "Revisar"}
              description="Dor, lesao, dieta, suplemento e cancelamento bloqueiam."
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
                <span className="block text-sm font-semibold text-lovable-ink">Habilitar Personal IA</span>
                <span className="mt-1 block text-xs text-lovable-ink-muted">Permite gerar orientacoes tecnicas em rascunho para alunos.</span>
              </span>
            </label>
            <label className="flex items-start gap-3 rounded-2xl border border-lovable-border bg-lovable-surface-soft p-4">
              <input
                type="checkbox"
                className="mt-1 h-4 w-4"
                checked={draft.kommo_prepare_enabled}
                onChange={(event) => setDraft((current) => ({ ...current, kommo_prepare_enabled: event.target.checked }))}
              />
              <span>
                <span className="block text-sm font-semibold text-lovable-ink">Preparar na Kommo</span>
                <span className="mt-1 block text-xs text-lovable-ink-muted">Cria tarefa/contexto na Kommo para o professor revisar.</span>
              </span>
            </label>
          </div>

          <FormField label="Maximo de rascunhos por dia">
            <Input
              type="number"
              value={draft.max_drafts_per_day}
              onChange={(event) => setDraft((current) => ({ ...current, max_drafts_per_day: Number(event.target.value) || 0 }))}
            />
          </FormField>

          <div className="rounded-2xl border border-lovable-border bg-lovable-bg-muted/60 p-4">
            <p className="flex items-center gap-2 text-sm font-semibold text-lovable-ink">
              <ShieldCheck size={16} className="text-emerald-400" />
              Escopo permitido nesta V1
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              {draft.allowed_domains.map((domain) => (
                <Badge key={domain} variant="neutral">
                  {domain}
                </Badge>
              ))}
            </div>
            <p className="mt-3 text-xs text-lovable-ink-muted">
              O Personal IA nao monta treino novo, nao corrige movimento por video, nao da dieta/suplemento e nao responde dor ou lesao sem humano.
            </p>
          </div>

          <div className="flex justify-end">
            <Button variant="primary" onClick={() => saveMutation.mutate()} disabled={saveMutation.isPending}>
              {saveMutation.isPending ? "Salvando..." : "Salvar Personal IA"}
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Sparkles size={18} className="text-lovable-primary" />
            Rascunhos tecnicos recentes
          </CardTitle>
          <p className="text-sm text-lovable-ink-muted">Orientacoes geradas para revisao do professor.</p>
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
              Nenhum rascunho tecnico gerado ainda.
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
                  <p className="mt-1 text-xs text-lovable-ink-muted">Pergunta: {item.question}</p>
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
                <p className="mt-3 text-xs text-lovable-warning">Bloqueios: {item.blocked_reasons.join(", ")}</p>
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
