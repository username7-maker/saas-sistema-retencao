import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Loader2, MessageSquareShare, TriangleAlert } from "lucide-react";
import toast from "react-hot-toast";

import { kommoSettingsService } from "../../services/kommoSettingsService";
import { Button, Card, CardContent, CardHeader, CardTitle, Input } from "../ui2";

export function KommoConnectionTab() {
  const queryClient = useQueryClient();
  const settingsQuery = useQuery({
    queryKey: ["kommo-settings"],
    queryFn: () => kommoSettingsService.getSettings(),
  });

  const [enabled, setEnabled] = useState(false);
  const [baseUrl, setBaseUrl] = useState("");
  const [accessToken, setAccessToken] = useState("");
  const [clearAccessToken, setClearAccessToken] = useState(false);
  const [pipelineId, setPipelineId] = useState("");
  const [stageId, setStageId] = useState("");
  const [responsibleUserId, setResponsibleUserId] = useState("");

  useEffect(() => {
    if (!settingsQuery.data) return;
    setEnabled(settingsQuery.data.kommo_enabled);
    setBaseUrl(settingsQuery.data.kommo_base_url ?? "");
    setAccessToken("");
    setClearAccessToken(false);
    setPipelineId(settingsQuery.data.kommo_default_pipeline_id ?? "");
    setStageId(settingsQuery.data.kommo_default_stage_id ?? "");
    setResponsibleUserId(settingsQuery.data.kommo_default_responsible_user_id ?? "");
  }, [settingsQuery.data]);

  const saveMutation = useMutation({
    mutationFn: () =>
      kommoSettingsService.updateSettings({
        kommo_enabled: enabled,
        kommo_base_url: baseUrl.trim() || null,
        kommo_access_token: accessToken.trim() || undefined,
        kommo_default_pipeline_id: pipelineId.trim() || null,
        kommo_default_stage_id: stageId.trim() || null,
        kommo_default_responsible_user_id: responsibleUserId.trim() || null,
        clear_access_token: clearAccessToken,
      }),
    onSuccess: async (payload) => {
      await queryClient.invalidateQueries({ queryKey: ["kommo-settings"] });
      setAccessToken("");
      setClearAccessToken(false);
      toast.success(
        payload.automatic_handoff_ready
          ? "Kommo pronta para receber handoffs do AI GYM OS."
          : "Configuracao da Kommo salva.",
      );
    },
    onError: () => toast.error("Nao foi possivel salvar a configuracao da Kommo."),
  });

  const testMutation = useMutation({
    mutationFn: () => kommoSettingsService.testConnection(),
    onSuccess: async (result) => {
      if (result.success) {
        toast.success(result.message);
      } else {
        toast.error(result.message);
      }
      await queryClient.invalidateQueries({ queryKey: ["kommo-settings"] });
    },
    onError: () => toast.error("Falha ao testar a conexao com a Kommo."),
  });

  const settings = settingsQuery.data;
  const canTest = useMemo(() => {
    return Boolean(enabled && baseUrl.trim() && (accessToken.trim() || settings?.kommo_has_access_token) && !clearAccessToken);
  }, [accessToken, baseUrl, clearAccessToken, enabled, settings?.kommo_has_access_token]);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <MessageSquareShare size={18} className="text-lovable-primary" />
          Kommo como motor de envio
        </CardTitle>
        <p className="text-sm text-lovable-ink-muted">
          O AI GYM OS decide a acao e entrega o handoff operacional para a Kommo. Assim a academia preserva o numero oficial no canal que ja usa hoje.
        </p>
      </CardHeader>

      <CardContent className="space-y-6">
        {settingsQuery.isLoading ? (
          <div className="flex items-center gap-3 text-sm text-lovable-ink-muted">
            <Loader2 size={18} className="animate-spin text-lovable-primary" />
            Carregando configuracao da Kommo...
          </div>
        ) : null}

        {settings ? (
          <>
            <div className="grid gap-4 lg:grid-cols-3">
              <StatusCard
                title="Canal Kommo"
                value={settings.kommo_enabled ? "Ativo" : "Desligado"}
                description="Liga ou desliga o handoff do AI GYM OS para a Kommo nesta academia."
                tone={settings.kommo_enabled ? "success" : "warning"}
              />
              <StatusCard
                title="Handoff automatico"
                value={settings.automatic_handoff_ready ? "Pronto" : "Pendente"}
                description={
                  settings.automatic_handoff_ready
                    ? "As automacoes e os envios manuais ja podem entregar contexto operacional para a Kommo."
                    : "Ainda faltam URL e token validos para o AI GYM OS conversar com a Kommo."
                }
                tone={settings.automatic_handoff_ready ? "success" : "warning"}
              />
              <StatusCard
                title="Token salvo"
                value={settings.kommo_has_access_token ? "Sim" : "Nao"}
                description="O token nunca volta para a tela. Digite outro apenas se quiser trocar."
                tone={settings.kommo_has_access_token ? "success" : "neutral"}
              />
            </div>

            <label className="flex items-start gap-3 rounded-2xl border border-lovable-border bg-lovable-surface-soft p-4">
              <input
                type="checkbox"
                className="mt-1 h-4 w-4"
                checked={enabled}
                onChange={(event) => setEnabled(event.target.checked)}
              />
              <div>
                <p className="text-sm font-semibold text-lovable-ink">Habilitar Kommo nesta academia</p>
                <p className="mt-1 text-xs text-lovable-ink-muted">
                  Quando ligada, as automacoes podem criar handoffs na Kommo em vez de tentar mandar WhatsApp direto pelo AI GYM OS.
                </p>
              </div>
            </label>

            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-lovable-ink-muted">
                  URL base da Kommo
                </label>
                <Input
                  value={baseUrl}
                  onChange={(event) => setBaseUrl(event.target.value)}
                  placeholder="https://sua-conta.kommo.com"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-lovable-ink-muted">
                  Access token da integracao
                </label>
                <Input
                  type="password"
                  value={accessToken}
                  onChange={(event) => setAccessToken(event.target.value)}
                  placeholder={settings.kommo_has_access_token ? "Token salvo. Digite so se quiser trocar." : "Cole o access token da Kommo"}
                />
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-3">
              <div>
                <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-lovable-ink-muted">
                  Pipeline padrao
                </label>
                <Input value={pipelineId} onChange={(event) => setPipelineId(event.target.value)} placeholder="Opcional" />
              </div>
              <div>
                <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-lovable-ink-muted">
                  Stage padrao
                </label>
                <Input value={stageId} onChange={(event) => setStageId(event.target.value)} placeholder="Opcional" />
              </div>
              <div>
                <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-lovable-ink-muted">
                  Responsavel padrao
                </label>
                <Input value={responsibleUserId} onChange={(event) => setResponsibleUserId(event.target.value)} placeholder="Opcional" />
              </div>
            </div>

            <label className="flex items-center gap-3 rounded-2xl border border-lovable-border bg-lovable-surface-soft px-4 py-3 text-sm text-lovable-ink">
              <input
                type="checkbox"
                className="h-4 w-4"
                checked={clearAccessToken}
                onChange={(event) => setClearAccessToken(event.target.checked)}
              />
              Remover token salvo
            </label>

            <div className="flex flex-wrap gap-3">
              <Button variant="primary" onClick={() => saveMutation.mutate()} disabled={saveMutation.isPending}>
                {saveMutation.isPending ? "Salvando..." : "Salvar configuracao"}
              </Button>
              <Button variant="secondary" onClick={() => testMutation.mutate()} disabled={!canTest || testMutation.isPending}>
                {testMutation.isPending ? "Testando..." : "Testar conexao"}
              </Button>
            </div>

            {testMutation.data ? (
              <div
                className={`rounded-2xl border p-4 text-sm ${
                  testMutation.data.success
                    ? "border-emerald-500/20 bg-emerald-500/8 text-lovable-ink"
                    : "border-amber-500/20 bg-amber-500/8 text-lovable-ink"
                }`}
              >
                <div className="flex items-start gap-3">
                  {testMutation.data.success ? (
                    <CheckCircle2 size={18} className="mt-0.5 shrink-0 text-emerald-400" />
                  ) : (
                    <TriangleAlert size={18} className="mt-0.5 shrink-0 text-amber-400" />
                  )}
                  <div>
                    <p className="font-semibold">{testMutation.data.message}</p>
                    {testMutation.data.detail ? <p className="mt-1 text-xs text-lovable-ink-muted">{testMutation.data.detail}</p> : null}
                  </div>
                </div>
              </div>
            ) : null}
          </>
        ) : null}
      </CardContent>
    </Card>
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
  tone: "success" | "warning" | "neutral";
}) {
  const toneClass =
    tone === "success"
      ? "border-emerald-500/20 bg-emerald-500/8"
      : tone === "warning"
        ? "border-amber-500/20 bg-amber-500/8"
        : "border-lovable-border bg-lovable-surface-soft";

  return (
    <div className={`rounded-2xl border p-4 ${toneClass}`}>
      <p className="text-[11px] font-semibold uppercase tracking-wide text-lovable-ink-muted">{title}</p>
      <p className="mt-2 text-lg font-semibold text-lovable-ink">{value}</p>
      <p className="mt-1 text-xs text-lovable-ink-muted">{description}</p>
    </div>
  );
}
