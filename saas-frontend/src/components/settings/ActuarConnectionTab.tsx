import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Loader2, ShieldCheck, TriangleAlert } from "lucide-react";
import toast from "react-hot-toast";

import { actuarSettingsService } from "../../services/actuarSettingsService";
import type { ActuarSyncMode } from "../../types";
import { Button, Card, CardContent, CardHeader, CardTitle, Input } from "../ui2";

function modeLabel(mode: ActuarSyncMode | "disabled" | string | null | undefined): string {
  if (mode === "assisted_rpa") return "Automacao assistida";
  if (mode === "http_api") return "HTTP API";
  if (mode === "csv_export") return "Exportacao CSV";
  return "Desabilitado";
}

export function ActuarConnectionTab() {
  const queryClient = useQueryClient();
  const settingsQuery = useQuery({
    queryKey: ["actuar-settings"],
    queryFn: () => actuarSettingsService.getSettings(),
  });

  const [enabled, setEnabled] = useState(false);
  const [autoSync, setAutoSync] = useState(false);
  const [baseUrl, setBaseUrl] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [clearPassword, setClearPassword] = useState(false);

  useEffect(() => {
    if (!settingsQuery.data) return;
    setEnabled(settingsQuery.data.actuar_enabled);
    setAutoSync(settingsQuery.data.actuar_auto_sync_body_composition);
    setBaseUrl(settingsQuery.data.actuar_base_url ?? "");
    setUsername(settingsQuery.data.actuar_username ?? "");
    setPassword("");
    setClearPassword(false);
  }, [settingsQuery.data]);

  const saveMutation = useMutation({
    mutationFn: () =>
      actuarSettingsService.updateSettings({
        actuar_enabled: enabled,
        actuar_auto_sync_body_composition: autoSync,
        actuar_base_url: baseUrl.trim() || null,
        actuar_username: username.trim() || null,
        actuar_password: password.trim() || undefined,
        clear_password: clearPassword,
      }),
    onSuccess: async (payload) => {
      await queryClient.invalidateQueries({ queryKey: ["actuar-settings"] });
      setPassword("");
      setClearPassword(false);
      toast.success(
        payload.effective_sync_mode === "assisted_rpa"
          ? "Actuar pronto para tentar automacao assistida."
          : "Configuracao do Actuar salva.",
      );
    },
    onError: () => toast.error("Nao foi possivel salvar a configuracao do Actuar."),
  });

  const testMutation = useMutation({
    mutationFn: () => actuarSettingsService.testConnection(),
    onSuccess: (result) => {
      if (result.success) {
        toast.success(result.message);
      } else {
        toast.error(result.message);
      }
      void queryClient.invalidateQueries({ queryKey: ["actuar-settings"] });
    },
    onError: () => toast.error("Falha ao testar a conexao com o Actuar."),
  });

  const settings = settingsQuery.data;
  const canTest = useMemo(() => {
    return Boolean(enabled && baseUrl.trim() && username.trim() && (password.trim() || settings?.actuar_has_password) && !clearPassword);
  }, [baseUrl, clearPassword, enabled, password, settings?.actuar_has_password, username]);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <ShieldCheck size={18} className="text-lovable-primary" />
          Actuar e treino externo
        </CardTitle>
        <p className="text-sm text-lovable-ink-muted">
          Configure a conexao externa para deixar a bioimpedancia menos manual e promover o sync automatico quando o ambiente estiver pronto.
        </p>
      </CardHeader>

      <CardContent className="space-y-6">
        {settingsQuery.isLoading ? (
          <div className="flex items-center gap-3 text-sm text-lovable-ink-muted">
            <Loader2 size={18} className="animate-spin text-lovable-primary" />
            Carregando configuracao do Actuar...
          </div>
        ) : null}

        {settings ? (
          <>
            <div className="grid gap-4 lg:grid-cols-3">
              <StatusCard
                title="Ambiente"
                value={settings.environment_enabled ? "Ativo" : "Desligado"}
                description={`Modo base do ambiente: ${modeLabel(settings.environment_sync_mode)}`}
                tone={settings.environment_enabled ? "success" : "warning"}
              />
              <StatusCard
                title="Modo efetivo"
                value={modeLabel(settings.effective_sync_mode)}
                description={
                  settings.automatic_sync_ready
                    ? "Com credenciais validas, o piloto tenta sync automatico."
                    : "Sem credenciais validas, o piloto continua no fallback manual/CSV."
                }
                tone={settings.automatic_sync_ready ? "success" : "warning"}
              />
              <StatusCard
                title="Senha salva"
                value={settings.actuar_has_password ? "Sim" : "Nao"}
                description="A senha nunca volta para a tela. Voce so envia uma nova quando quiser trocar."
                tone={settings.actuar_has_password ? "success" : "neutral"}
              />
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <label className="flex items-start gap-3 rounded-2xl border border-lovable-border bg-lovable-surface-soft p-4">
                <input
                  type="checkbox"
                  className="mt-1 h-4 w-4"
                  checked={enabled}
                  onChange={(event) => setEnabled(event.target.checked)}
                />
                <div>
                  <p className="text-sm font-semibold text-lovable-ink">Habilitar integracao Actuar</p>
                  <p className="mt-1 text-xs text-lovable-ink-muted">
                    Permite preparar e executar o fluxo externo da bioimpedancia.
                  </p>
                </div>
              </label>

              <label className="flex items-start gap-3 rounded-2xl border border-lovable-border bg-lovable-surface-soft p-4">
                <input
                  type="checkbox"
                  className="mt-1 h-4 w-4"
                  checked={autoSync}
                  onChange={(event) => setAutoSync(event.target.checked)}
                />
                <div>
                  <p className="text-sm font-semibold text-lovable-ink">Tentar sync automatico da bioimpedancia</p>
                  <p className="mt-1 text-xs text-lovable-ink-muted">
                    Quando a conexao estiver valida, o piloto tenta sair do `csv_export/manual`.
                  </p>
                </div>
              </label>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-lovable-ink-muted">
                  URL base do Actuar
                </label>
                <Input
                  value={baseUrl}
                  onChange={(event) => setBaseUrl(event.target.value)}
                  placeholder="https://app.actuar..."
                />
              </div>

              <div>
                <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-lovable-ink-muted">
                  Usuario do Actuar
                </label>
                <Input
                  value={username}
                  onChange={(event) => setUsername(event.target.value)}
                  placeholder="usuario@empresa.com"
                />
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-[minmax(0,1fr)_220px]">
              <div>
                <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-lovable-ink-muted">
                  Senha do Actuar
                </label>
                <Input
                  type="password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder={settings.actuar_has_password ? "Senha salva. Digite so se quiser trocar." : "Digite a senha do Actuar"}
                />
              </div>

              <label className="flex items-center gap-3 rounded-2xl border border-lovable-border bg-lovable-surface-soft px-4 py-3 text-sm text-lovable-ink">
                <input
                  type="checkbox"
                  className="h-4 w-4"
                  checked={clearPassword}
                  onChange={(event) => setClearPassword(event.target.checked)}
                />
                Remover senha salva
              </label>
            </div>

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
