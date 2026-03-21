import { useCallback, useEffect, useRef, useState } from "react";
import {
  CheckCircle2,
  Loader2,
  PhoneOff,
  QrCode,
  RefreshCw,
  Smartphone,
  WifiOff,
} from "lucide-react";
import toast from "react-hot-toast";

import { Button, Card, CardContent, CardHeader, CardTitle } from "../ui2";
import {
  whatsappConnectionService,
  type WhatsAppStatus,
} from "../../services/whatsappConnectionService";

type Phase = "idle" | "loading" | "qr" | "connected" | "error";

const POLL_MS = 3000;
const QR_TIMEOUT_MS = 120_000;

export function WhatsAppConnectionTab() {
  const [status, setStatus] = useState<WhatsAppStatus | null>(null);
  const [phase, setPhase] = useState<Phase>("idle");
  const [qrCode, setQrCode] = useState<string | null>(null);
  const [qrExpired, setQrExpired] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const expiryRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
    if (expiryRef.current) {
      clearTimeout(expiryRef.current);
      expiryRef.current = null;
    }
  }, []);

  const startPolling = useCallback(() => {
    stopPolling();
    setQrExpired(false);

    expiryRef.current = setTimeout(() => {
      setQrExpired(true);
      stopPolling();
    }, QR_TIMEOUT_MS);

    pollRef.current = setInterval(async () => {
      try {
        const data = await whatsappConnectionService.getQR();

        if (data.status === "connected") {
          stopPolling();
          setPhase("connected");
          setQrCode(null);
          const updated = await whatsappConnectionService.getStatus();
          setStatus(updated);
          toast.success("WhatsApp conectado.");
          return;
        }

        if (data.qrcode) {
          setQrCode(data.qrcode);
          setPhase("qr");
        }
      } catch {
        // Ignore intermittent polling failures.
      }
    }, POLL_MS);
  }, [stopPolling]);

  useEffect(() => {
    let cancelled = false;

    async function loadStatus() {
      try {
        const current = await whatsappConnectionService.getStatus();
        if (cancelled) {
          return;
        }
        setStatus(current);
        if (current.status === "connected") {
          setPhase("connected");
          return;
        }
        if (current.status === "connecting") {
          setPhase("loading");
          startPolling();
        }
      } catch {
        if (!cancelled) {
          setPhase("error");
        }
      }
    }

    void loadStatus();
    return () => {
      cancelled = true;
      stopPolling();
    };
  }, [startPolling, stopPolling]);

  const handleConnect = useCallback(async () => {
    setPhase("loading");
    setQrExpired(false);
    try {
      const data = await whatsappConnectionService.connect();
      if (data.qrcode) {
        setQrCode(data.qrcode);
        setPhase("qr");
        startPolling();
        return;
      }

      if (data.status === "connected") {
        setPhase("connected");
        setStatus(await whatsappConnectionService.getStatus());
        return;
      }

      startPolling();
    } catch {
      setPhase("error");
      toast.error("Falha ao iniciar a conexao. Verifique a Evolution API.");
    }
  }, [startPolling]);

  const handleDisconnect = useCallback(async () => {
    if (!window.confirm("Desconectar o WhatsApp desta academia?")) {
      return;
    }

    stopPolling();
    try {
      await whatsappConnectionService.disconnect();
      setPhase("idle");
      setQrCode(null);
      setQrExpired(false);
      setStatus((previous) => ({
        status: "disconnected",
        phone: null,
        connected_at: null,
        instance: previous?.instance ?? null,
      }));
      toast.success("WhatsApp desconectado.");
    } catch {
      toast.error("Erro ao desconectar o WhatsApp.");
    }
  }, [stopPolling]);

  const handleRefreshQR = useCallback(async () => {
    setPhase("loading");
    setQrExpired(false);
    try {
      const data = await whatsappConnectionService.connect();
      if (data.qrcode) {
        setQrCode(data.qrcode);
        setPhase("qr");
        startPolling();
        return;
      }
      startPolling();
    } catch {
      setPhase("error");
      toast.error("Nao foi possivel gerar um novo QR Code.");
    }
  }, [startPolling]);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Smartphone size={18} className="text-lovable-primary" />
          Conexao WhatsApp
        </CardTitle>
        <p className="text-sm text-lovable-ink-muted">
          Cada academia envia automacoes e mensagens pelo proprio numero conectado.
        </p>
      </CardHeader>

      <CardContent className="space-y-6">
        <StatusIndicator status={status?.status ?? "disconnected"} phone={status?.phone} />

        {(phase === "idle" || phase === "error") && (
          <div className="flex flex-col gap-4">
            <p className="max-w-2xl text-sm leading-relaxed text-lovable-ink-muted">
              Conecte o numero da academia para enviar mensagens automaticas de retencao,
              nurturing, briefings e CRM diretamente pelo WhatsApp da unidade.
            </p>
            <InstructionSteps />
            <Button variant="primary" size="md" onClick={handleConnect} className="w-fit">
              <QrCode size={16} />
              Gerar QR Code para conectar
            </Button>
            {phase === "error" && (
              <p className="text-xs text-lovable-danger">
                Falha na conexao. Verifique se a Evolution API esta acessivel.
              </p>
            )}
          </div>
        )}

        {phase === "loading" && (
          <div className="flex items-center gap-3 text-sm text-lovable-ink-muted">
            <Loader2 size={18} className="animate-spin text-lovable-primary" />
            Gerando QR Code...
          </div>
        )}

        {phase === "qr" && (
          <div className="flex flex-col items-center gap-4 rounded-2xl border border-lovable-border bg-lovable-surface-soft p-6 text-center">
            {qrExpired ? (
              <div className="flex flex-col items-center gap-3">
                <WifiOff size={40} className="text-lovable-ink-muted" />
                <p className="text-sm text-lovable-ink-muted">QR Code expirado. Gere um novo.</p>
                <Button variant="secondary" size="sm" onClick={handleRefreshQR}>
                  <RefreshCw size={14} />
                  Novo QR Code
                </Button>
              </div>
            ) : (
              <>
                {qrCode ? (
                  <img
                    src={qrCode}
                    alt="QR Code WhatsApp"
                    className="h-52 w-52 rounded-xl border border-lovable-border bg-white p-2"
                  />
                ) : (
                  <div className="flex h-52 w-52 items-center justify-center rounded-xl border border-lovable-border">
                    <Loader2 size={28} className="animate-spin text-lovable-primary" />
                  </div>
                )}

                <div>
                  <p className="text-sm font-semibold text-lovable-ink">
                    Escaneie com o WhatsApp do celular da academia
                  </p>
                  <p className="mt-1 text-xs text-lovable-ink-muted">
                    Atualiza automaticamente e expira em 2 minutos.
                  </p>
                </div>

                <div className="flex items-center gap-2 text-xs text-lovable-ink-muted">
                  <Loader2 size={12} className="animate-spin text-lovable-primary" />
                  Aguardando leitura...
                </div>
              </>
            )}
          </div>
        )}

        {phase === "connected" && (
          <div className="flex flex-col gap-4">
            <div className="flex items-start gap-3 rounded-2xl border border-emerald-500/20 bg-emerald-500/8 p-4">
              <CheckCircle2 size={20} className="mt-0.5 shrink-0 text-emerald-400" />
              <div>
                <p className="text-sm font-semibold text-lovable-ink">WhatsApp conectado</p>
                {status?.phone && (
                  <p className="mt-0.5 text-xs text-lovable-ink-muted">Numero: +{status.phone}</p>
                )}
                {status?.connected_at && (
                  <p className="text-xs text-lovable-ink-muted">
                    Conectado em: {new Date(status.connected_at).toLocaleString("pt-BR")}
                  </p>
                )}
              </div>
            </div>
            <Button variant="danger" size="sm" onClick={handleDisconnect} className="w-fit">
              <PhoneOff size={14} />
              Desconectar WhatsApp
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function StatusIndicator({ status, phone }: { status: string; phone?: string | null }) {
  const map: Record<string, { dot: string; label: string; text: string }> = {
    connected: {
      dot: "bg-emerald-400 shadow-[0_0_6px_2px_rgba(52,211,153,0.4)]",
      label: phone ? `Conectado · +${phone}` : "Conectado",
      text: "text-emerald-400",
    },
    connecting: {
      dot: "bg-amber-400 animate-pulse",
      label: "Conectando...",
      text: "text-amber-400",
    },
    disconnected: {
      dot: "bg-lovable-ink-muted",
      label: "Desconectado",
      text: "text-lovable-ink-muted",
    },
    error: {
      dot: "bg-lovable-danger",
      label: "Erro de conexao",
      text: "text-lovable-danger",
    },
  };

  const config = map[status] ?? map.disconnected;

  return (
    <div className="flex items-center gap-2">
      <span className={`h-2.5 w-2.5 rounded-full ${config.dot}`} />
      <span className={`text-sm font-medium ${config.text}`}>{config.label}</span>
    </div>
  );
}

function InstructionSteps() {
  const steps = [
    "Abra o WhatsApp no celular da academia.",
    'Toque em "Aparelhos conectados" e depois em "Conectar aparelho".',
    "Escaneie o QR Code gerado abaixo.",
  ];

  return (
    <ol className="space-y-1.5">
      {steps.map((step, index) => (
        <li key={step} className="flex items-start gap-2 text-sm text-lovable-ink-muted">
          <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-lovable-primary/15 text-[10px] font-bold text-lovable-primary">
            {index + 1}
          </span>
          {step}
        </li>
      ))}
    </ol>
  );
}
