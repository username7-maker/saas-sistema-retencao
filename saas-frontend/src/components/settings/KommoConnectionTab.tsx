import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Loader2, MessageSquareShare, TriangleAlert } from "lucide-react";
import toast from "react-hot-toast";

import { PRODUCT_NAME } from "../../config/brand";
import { kommoSettingsService } from "../../services/kommoSettingsService";
import type { KommoDomainRoute } from "../../types";
import { Button, Card, CardContent, CardHeader, CardTitle, Input } from "../ui2";

const KOMMO_DOMAINS = [
  ["retention", "Retencao"],
  ["onboarding", "Onboarding"],
  ["assessment", "Avaliacao"],
  ["body_composition", "Bioimpedancia"],
  ["finance", "Financeiro"],
  ["sales", "Comercial"],
  ["student_ai", "Aluno IA"],
  ["support", "Suporte"],
] as const;

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
  const [primaryMessageChannel, setPrimaryMessageChannel] = useState("whatsapp");
  const [operatorConfirmedSend, setOperatorConfirmedSend] = useState(true);
  const [autoCloseEnabled, setAutoCloseEnabled] = useState(true);
  const [fallbackChannel, setFallbackChannel] = useState("whatsapp");
  const [domainRoutes, setDomainRoutes] = useState<KommoDomainRoute[]>([]);
  const [nativeTestLeadId, setNativeTestLeadId] = useState("");

  useEffect(() => {
    if (!settingsQuery.data) return;
    setEnabled(settingsQuery.data.kommo_enabled);
    setBaseUrl(settingsQuery.data.kommo_base_url ?? "");
    setAccessToken("");
    setClearAccessToken(false);
    setPipelineId(settingsQuery.data.kommo_default_pipeline_id ?? "");
    setStageId(settingsQuery.data.kommo_default_stage_id ?? "");
    setResponsibleUserId(settingsQuery.data.kommo_default_responsible_user_id ?? "");
    setPrimaryMessageChannel(settingsQuery.data.primary_message_channel ?? "whatsapp");
    setOperatorConfirmedSend(settingsQuery.data.kommo_operator_confirmed_send_enabled);
    setAutoCloseEnabled(settingsQuery.data.kommo_auto_close_enabled);
    setFallbackChannel(settingsQuery.data.kommo_fallback_channel ?? "whatsapp");
    setDomainRoutes(ensureDomainRoutes(settingsQuery.data.domain_routes ?? []));
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
        primary_message_channel: primaryMessageChannel,
        kommo_operator_confirmed_send_enabled: operatorConfirmedSend,
        kommo_auto_close_enabled: autoCloseEnabled,
        kommo_fallback_channel: fallbackChannel,
        domain_routes: domainRoutes,
      }),
    onSuccess: async (payload) => {
      await queryClient.invalidateQueries({ queryKey: ["kommo-settings"] });
      setAccessToken("");
      setClearAccessToken(false);
      toast.success(
        payload.automatic_handoff_ready
          ? `Kommo pronta para receber handoffs do ${PRODUCT_NAME}.`
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

  const nativeFileTestMutation = useMutation({
    mutationFn: () => kommoSettingsService.testNativeFileUpload(nativeTestLeadId),
    onSuccess: (result) => {
      if (result.success) {
        toast.success(result.message);
      } else {
        toast.error(result.detail || result.message);
      }
    },
    onError: () => toast.error("Falha ao testar upload nativo da Kommo."),
  });

  const settings = settingsQuery.data;
  const canTest = useMemo(() => {
    return Boolean(enabled && baseUrl.trim() && (accessToken.trim() || settings?.kommo_has_access_token) && !clearAccessToken);
  }, [accessToken, baseUrl, clearAccessToken, enabled, settings?.kommo_has_access_token]);

  function updateRoute(domain: string, patch: Partial<KommoDomainRoute>) {
    setDomainRoutes((current) => current.map((route) => (route.domain === domain ? { ...route, ...patch } : route)));
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <MessageSquareShare size={18} className="text-lovable-primary" />
          Kommo como motor de envio
        </CardTitle>
        <p className="text-sm text-lovable-ink-muted">
          O {PRODUCT_NAME} decide a acao e aciona o Salesbot da Kommo no dominio certo. Assim a academia preserva o numero oficial no canal que ja usa hoje.
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
            <div className="grid gap-4 lg:grid-cols-4">
              <StatusCard
                title="Canal Kommo"
                value={settings.kommo_enabled ? "Ativo" : "Desligado"}
                description={`Liga ou desliga o handoff do ${PRODUCT_NAME} para a Kommo nesta academia.`}
                tone={settings.kommo_enabled ? "success" : "warning"}
              />
              <StatusCard
                title="Canal principal"
                value={settings.primary_message_channel === "kommo" ? "Kommo" : settings.primary_message_channel === "manual" ? "Manual" : "WhatsApp"}
                description={`Fallback: ${settings.kommo_fallback_channel === "manual" ? "manual" : "WhatsApp"}.`}
                tone={settings.primary_message_channel === "kommo" ? "success" : "neutral"}
              />
              <StatusCard
                title="Handoff automatico"
                value={settings.automatic_handoff_ready ? "Pronto" : "Pendente"}
                description={
                  settings.automatic_handoff_ready
                    ? "As automacoes e os envios manuais ja podem entregar contexto operacional para a Kommo."
                    : `Ainda faltam URL e token validos para o ${PRODUCT_NAME} conversar com a Kommo.`
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
                  Quando ligada, as automacoes podem acionar Salesbot ou preparar fallback na Kommo em vez de tentar mandar WhatsApp direto pelo {PRODUCT_NAME}.
                </p>
              </div>
            </label>

            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-lovable-ink-muted">
                  Canal principal da operacao
                </label>
                <select
                  value={primaryMessageChannel}
                  onChange={(event) => setPrimaryMessageChannel(event.target.value)}
                  className="h-11 w-full rounded-xl border border-lovable-border bg-lovable-bg-muted px-3 text-sm text-lovable-ink outline-none focus:border-lovable-primary"
                >
                  <option value="kommo">Kommo</option>
                  <option value="whatsapp">WhatsApp</option>
                  <option value="manual">Manual</option>
                </select>
                <p className="mt-1 text-xs text-lovable-ink-muted">
                  Quando estiver em Kommo, a Work Queue usa a rota do dominio para enviar ou preparar contexto na Kommo.
                </p>
              </div>
              <div>
                <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-lovable-ink-muted">
                  Fallback quando Kommo falhar
                </label>
                <select
                  value={fallbackChannel}
                  onChange={(event) => setFallbackChannel(event.target.value)}
                  className="h-11 w-full rounded-xl border border-lovable-border bg-lovable-bg-muted px-3 text-sm text-lovable-ink outline-none focus:border-lovable-primary"
                >
                  <option value="whatsapp">WhatsApp</option>
                  <option value="manual">Manual</option>
                </select>
              </div>
            </div>

            <div className="grid gap-3 md:grid-cols-2">
              <label className="flex items-start gap-3 rounded-2xl border border-lovable-border bg-lovable-surface-soft p-4">
                <input
                  type="checkbox"
                  className="mt-1 h-4 w-4"
                  checked={operatorConfirmedSend}
                  onChange={(event) => setOperatorConfirmedSend(event.target.checked)}
                />
                <div>
                  <p className="text-sm font-semibold text-lovable-ink">Envio confirmado pelo operador na Kommo</p>
                  <p className="mt-1 text-xs text-lovable-ink-muted">
                    V1 exige clique humano no Cordex; depois disso o Salesbot pode enviar pelo canal oficial da Kommo.
                  </p>
                </div>
              </label>
              <label className="flex items-start gap-3 rounded-2xl border border-lovable-border bg-lovable-surface-soft p-4">
                <input
                  type="checkbox"
                  className="mt-1 h-4 w-4"
                  checked={autoCloseEnabled}
                  onChange={(event) => setAutoCloseEnabled(event.target.checked)}
                />
                <div>
                  <p className="text-sm font-semibold text-lovable-ink">Auto-fechar por resposta Kommo</p>
                  <p className="mt-1 text-xs text-lovable-ink-muted">
                    Respostas simples podem fechar tasks; cancelamento, reclamacao e opt-out escalam para humano.
                  </p>
                </div>
              </label>
            </div>

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

            <div className="rounded-2xl border border-lovable-border bg-lovable-surface-soft p-4">
              <div className="flex flex-col gap-1 md:flex-row md:items-end md:justify-between">
                <div>
                  <p className="text-sm font-semibold text-lovable-ink">Roteamento por dominio</p>
                  <p className="mt-1 text-xs text-lovable-ink-muted">
                    Configure onde cada mensagem cai na Kommo. O Salesbot usa os campos de mensagem/PDF para enviar ao numero do aluno.
                  </p>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <Input
                    value={nativeTestLeadId}
                    onChange={(event) => setNativeTestLeadId(event.target.value)}
                    placeholder="Lead ID opcional para testar anexo"
                    className="h-9 w-64"
                  />
                  <Button
                    variant="secondary"
                    onClick={() => nativeFileTestMutation.mutate()}
                    disabled={!canTest || nativeFileTestMutation.isPending}
                  >
                    {nativeFileTestMutation.isPending ? "Testando..." : "Testar PDF nativo"}
                  </Button>
                </div>
              </div>

              <div className="mt-4 space-y-3">
                {domainRoutes.map((route) => (
                  <div key={route.domain} className="rounded-xl border border-lovable-border bg-lovable-bg-muted p-3">
                    <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
                      <label className="flex items-center gap-2 text-sm font-semibold text-lovable-ink">
                        <input
                          type="checkbox"
                          className="h-4 w-4"
                          checked={route.is_enabled}
                          onChange={(event) => updateRoute(route.domain, { is_enabled: event.target.checked })}
                        />
                        {domainLabel(route.domain)}
                      </label>
                      <span className="text-[11px] uppercase tracking-wide text-lovable-ink-muted">
                        {route.salesbot_id ? "Salesbot configurado" : "Falta Salesbot"}
                      </span>
                    </div>
                    <div className="mb-3 grid gap-3 md:grid-cols-3">
                      <div>
                        <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wide text-lovable-ink-muted">Modo PDF</label>
                        <select
                          value={route.pdf_delivery_mode || "native_file_required"}
                          onChange={(event) => updateRoute(route.domain, { pdf_delivery_mode: event.target.value })}
                          className="h-10 w-full rounded-xl border border-lovable-border bg-lovable-surface px-3 text-xs text-lovable-ink outline-none focus:border-lovable-primary"
                        >
                          <option value="native_file_required">Nativo obrigatorio</option>
                          <option value="native_file_preferred">Nativo preferencial</option>
                          <option value="link_only">Somente link</option>
                        </select>
                      </div>
                      <RouteInput label="Campo file_uuid" value={route.file_uuid_field_id} onChange={(value) => updateRoute(route.domain, { file_uuid_field_id: value })} />
                      <RouteInput label="Campo nome arquivo" value={route.file_name_field_id} onChange={(value) => updateRoute(route.domain, { file_name_field_id: value })} />
                    </div>
                    <div className="grid gap-3 md:grid-cols-4">
                      <RouteInput label="Pipeline" value={route.pipeline_id} onChange={(value) => updateRoute(route.domain, { pipeline_id: value })} />
                      <RouteInput label="Etapa" value={route.stage_id} onChange={(value) => updateRoute(route.domain, { stage_id: value })} />
                      <RouteInput label="Salesbot" value={route.salesbot_id} onChange={(value) => updateRoute(route.domain, { salesbot_id: value })} />
                      <RouteInput label="Responsavel" value={route.responsible_user_id} onChange={(value) => updateRoute(route.domain, { responsible_user_id: value })} />
                      <RouteInput label="Campo mensagem" value={route.message_field_id} onChange={(value) => updateRoute(route.domain, { message_field_id: value })} />
                      <RouteInput label="Campo PDF" value={route.pdf_url_field_id} onChange={(value) => updateRoute(route.domain, { pdf_url_field_id: value })} />
                      <RouteInput label="Campo origem" value={route.source_type_field_id} onChange={(value) => updateRoute(route.domain, { source_type_field_id: value })} />
                      <RouteInput label="Campo ID origem" value={route.source_id_field_id} onChange={(value) => updateRoute(route.domain, { source_id_field_id: value })} />
                      <RouteInput label="Campo nota/anexo" value={route.file_attachment_note_field_id} onChange={(value) => updateRoute(route.domain, { file_attachment_note_field_id: value })} />
                    </div>
                    <div className="mt-3">
                      <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-lovable-ink-muted">Tags</label>
                      <Input
                        value={(route.tags ?? []).join(", ")}
                        onChange={(event) => updateRoute(route.domain, { tags: event.target.value.split(",").map((item) => item.trim()).filter(Boolean) })}
                        placeholder="retencao, cordex, bioimpedancia"
                      />
                    </div>
                    <p className="mt-2 text-[11px] text-lovable-ink-muted">
                      `Nativo obrigatorio` so marca sucesso se o PDF for anexado na Kommo. `Somente link` mantem o comportamento antigo via campo PDF.
                    </p>
                  </div>
                ))}
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

            {nativeFileTestMutation.data ? (
              <div
                className={`rounded-2xl border p-4 text-sm ${
                  nativeFileTestMutation.data.success
                    ? "border-emerald-500/20 bg-emerald-500/8 text-lovable-ink"
                    : "border-amber-500/20 bg-amber-500/8 text-lovable-ink"
                }`}
              >
                <div className="flex items-start gap-3">
                  {nativeFileTestMutation.data.success ? (
                    <CheckCircle2 size={18} className="mt-0.5 shrink-0 text-emerald-400" />
                  ) : (
                    <TriangleAlert size={18} className="mt-0.5 shrink-0 text-amber-400" />
                  )}
                  <div>
                    <p className="font-semibold">{nativeFileTestMutation.data.message}</p>
                    <p className="mt-1 text-xs text-lovable-ink-muted">
                      Upload: {nativeFileTestMutation.data.upload_status || "-"} · Anexo: {nativeFileTestMutation.data.attach_status || "-"} · UUID:{" "}
                      {nativeFileTestMutation.data.file_uuid || "-"}
                    </p>
                    {nativeFileTestMutation.data.detail ? <p className="mt-1 text-xs text-lovable-ink-muted">{nativeFileTestMutation.data.detail}</p> : null}
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

function ensureDomainRoutes(routes: KommoDomainRoute[]): KommoDomainRoute[] {
  const existing = new Map(routes.map((route) => [route.domain, route]));
  return KOMMO_DOMAINS.map(([domain]) => existing.get(domain) ?? emptyRoute(domain));
}

function emptyRoute(domain: string): KommoDomainRoute {
  return {
    domain,
    is_enabled: true,
    pipeline_id: null,
    stage_id: null,
    salesbot_id: null,
    channel_source_id: null,
    responsible_user_id: null,
    message_field_id: null,
    pdf_url_field_id: null,
    pdf_delivery_mode: "native_file_required",
    file_uuid_field_id: null,
    file_name_field_id: null,
    file_attachment_note_field_id: null,
    source_type_field_id: null,
    source_id_field_id: null,
    tags: [],
  };
}

function domainLabel(domain: string): string {
  return KOMMO_DOMAINS.find(([key]) => key === domain)?.[1] ?? domain;
}

function RouteInput({ label, value, onChange }: { label: string; value: string | null; onChange: (value: string | null) => void }) {
  return (
    <div>
      <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wide text-lovable-ink-muted">{label}</label>
      <Input value={value ?? ""} onChange={(event) => onChange(event.target.value.trim() || null)} placeholder="Opcional" />
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
