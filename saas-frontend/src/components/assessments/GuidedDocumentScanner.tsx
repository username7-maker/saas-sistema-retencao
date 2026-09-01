import { Camera, Check, RefreshCcw, RotateCcw, RotateCw, SwitchCamera, X } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import toast from "react-hot-toast";

import { Button } from "../ui2/Button";
import { Select } from "../ui2/Select";

type ScannerCapabilities = {
  torch: boolean;
  zoom: { min: number; max: number; step: number } | null;
};

type QualityResult = {
  blocking: string[];
  warnings: string[];
};

interface GuidedDocumentScannerProps {
  open: boolean;
  onClose: () => void;
  onConfirm: (file: File) => void;
}

const MAX_SIDE = 2400;
const MAX_BYTES = 8 * 1024 * 1024;

function stopStream(stream: MediaStream | null): void {
  stream?.getTracks().forEach((track) => track.stop());
}

function canvasBlob(canvas: HTMLCanvasElement, quality: number): Promise<Blob> {
  return new Promise((resolve, reject) => {
    canvas.toBlob((blob) => blob ? resolve(blob) : reject(new Error("capture_blob_failed")), "image/jpeg", quality);
  });
}

async function imageFromBlob(blob: Blob): Promise<HTMLImageElement> {
  const url = URL.createObjectURL(blob);
  try {
    const image = new Image();
    image.decoding = "async";
    image.src = url;
    await image.decode();
    return image;
  } finally {
    URL.revokeObjectURL(url);
  }
}

function analyzeCanvas(canvas: HTMLCanvasElement): QualityResult {
  const sample = document.createElement("canvas");
  const scale = Math.min(1, 256 / Math.max(canvas.width, canvas.height));
  sample.width = Math.max(1, Math.round(canvas.width * scale));
  sample.height = Math.max(1, Math.round(canvas.height * scale));
  const context = sample.getContext("2d", { willReadFrequently: true });
  if (!context) return { blocking: [], warnings: ["Nao foi possivel verificar automaticamente a qualidade."] };
  context.drawImage(canvas, 0, 0, sample.width, sample.height);
  const pixels = context.getImageData(0, 0, sample.width, sample.height).data;
  let luminanceSum = 0;
  let luminanceSquared = 0;
  let highlights = 0;
  for (let index = 0; index < pixels.length; index += 4) {
    const luminance = 0.2126 * pixels[index] + 0.7152 * pixels[index + 1] + 0.0722 * pixels[index + 2];
    luminanceSum += luminance;
    luminanceSquared += luminance * luminance;
    if (luminance > 248) highlights += 1;
  }
  const count = pixels.length / 4;
  const mean = luminanceSum / count;
  const variance = Math.max(0, luminanceSquared / count - mean * mean);
  const blocking: string[] = [];
  const warnings: string[] = [];
  if (mean < 8 || variance < 1.5) blocking.push("A imagem esta vazia ou sem informacao utilizavel.");
  if (canvas.width < 640 || canvas.height < 640) blocking.push("A resolucao e insuficiente para leitura.");
  else if (Math.max(canvas.width, canvas.height) < 1200) warnings.push("Resolucao baixa; aproxime a folha e refaca se o texto estiver pequeno.");
  if (mean < 55) warnings.push("Imagem escura; aumente a iluminacao sem usar reflexo direto.");
  if (variance < 180) warnings.push("Possivel desfoque ou pouco contraste; mantenha o aparelho firme.");
  if (highlights / count > 0.34) warnings.push("Possivel reflexo forte; incline levemente a camera ou a folha.");
  return { blocking, warnings };
}

async function normalizeCapture(blob: Blob, cropPercent: number, rotation: number): Promise<{ blob: Blob; quality: QualityResult }> {
  const image = await imageFromBlob(blob);
  const cropX = Math.round(image.naturalWidth * cropPercent / 100);
  const cropY = Math.round(image.naturalHeight * cropPercent / 100);
  const sourceWidth = Math.max(1, image.naturalWidth - cropX * 2);
  const sourceHeight = Math.max(1, image.naturalHeight - cropY * 2);
  const rotated = Math.abs(rotation % 180) === 90;
  const outputWidth = rotated ? sourceHeight : sourceWidth;
  const outputHeight = rotated ? sourceWidth : sourceHeight;
  const scale = Math.min(1, MAX_SIDE / Math.max(outputWidth, outputHeight));
  const canvas = document.createElement("canvas");
  canvas.width = Math.max(1, Math.round(outputWidth * scale));
  canvas.height = Math.max(1, Math.round(outputHeight * scale));
  const context = canvas.getContext("2d");
  if (!context) throw new Error("capture_canvas_failed");
  context.fillStyle = "#fff";
  context.fillRect(0, 0, canvas.width, canvas.height);
  context.translate(canvas.width / 2, canvas.height / 2);
  context.rotate(rotation * Math.PI / 180);
  const drawWidth = sourceWidth * scale;
  const drawHeight = sourceHeight * scale;
  context.drawImage(image, cropX, cropY, sourceWidth, sourceHeight, -drawWidth / 2, -drawHeight / 2, drawWidth, drawHeight);
  const quality = analyzeCanvas(canvas);
  let jpeg = await canvasBlob(canvas, 0.9);
  if (jpeg.size > MAX_BYTES) jpeg = await canvasBlob(canvas, 0.78);
  return { blob: jpeg, quality };
}

export function GuidedDocumentScanner({ open, onClose, onConfirm }: GuidedDocumentScannerProps) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [devices, setDevices] = useState<MediaDeviceInfo[]>([]);
  const [deviceId, setDeviceId] = useState("");
  const [rawCapture, setRawCapture] = useState<Blob | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [cropPercent, setCropPercent] = useState(4);
  const [rotation, setRotation] = useState(0);
  const [quality, setQuality] = useState<QualityResult>({ blocking: [], warnings: [] });
  const [processing, setProcessing] = useState(false);
  const [capabilities, setCapabilities] = useState<ScannerCapabilities>({ torch: false, zoom: null });
  const [torch, setTorch] = useState(false);
  const [zoom, setZoom] = useState<number | null>(null);

  const close = useCallback(() => {
    stopStream(streamRef.current);
    streamRef.current = null;
    setRawCapture(null);
    setError(null);
    onClose();
  }, [onClose]);

  const startCamera = useCallback(async (requestedDeviceId?: string) => {
    stopStream(streamRef.current);
    streamRef.current = null;
    setError(null);
    if (!navigator.mediaDevices?.getUserMedia) {
      setError("A camera nao esta disponivel neste navegador. Use o envio de arquivo.");
      return;
    }
    const highResolution: MediaTrackConstraints = requestedDeviceId
      ? { deviceId: { exact: requestedDeviceId }, width: { ideal: 2560 }, height: { ideal: 1440 } }
      : { facingMode: { ideal: "environment" }, width: { ideal: 2560 }, height: { ideal: 1440 } };
    try {
      let stream: MediaStream;
      try {
        stream = await navigator.mediaDevices.getUserMedia({ audio: false, video: highResolution });
      } catch {
        stream = await navigator.mediaDevices.getUserMedia({ audio: false, video: requestedDeviceId ? { deviceId: requestedDeviceId } : true });
      }
      streamRef.current = stream;
      if (videoRef.current) videoRef.current.srcObject = stream;
      const track = stream.getVideoTracks()[0];
      const rawCapabilities = typeof track?.getCapabilities === "function" ? track.getCapabilities() as MediaTrackCapabilities & Record<string, unknown> : {};
      const zoomCapability = rawCapabilities.zoom as { min?: number; max?: number; step?: number } | undefined;
      setCapabilities({
        torch: Boolean(rawCapabilities.torch),
        zoom: zoomCapability?.min != null && zoomCapability.max != null
          ? { min: zoomCapability.min, max: zoomCapability.max, step: zoomCapability.step ?? 0.1 }
          : null,
      });
      setZoom(zoomCapability?.min ?? null);
      const available = (await navigator.mediaDevices.enumerateDevices()).filter((item) => item.kind === "videoinput");
      setDevices(available);
      setDeviceId(track?.getSettings().deviceId ?? requestedDeviceId ?? "");
    } catch {
      setError("Nao foi possivel acessar a camera. Verifique a permissao ou use o envio de arquivo.");
    }
  }, []);

  useEffect(() => {
    if (!open) return;
    void startCamera();
    return () => {
      stopStream(streamRef.current);
      streamRef.current = null;
    };
  }, [open, startCamera]);

  useEffect(() => {
    if (!rawCapture) {
      setPreviewUrl(null);
      return;
    }
    const url = URL.createObjectURL(rawCapture);
    setPreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [rawCapture]);

  const reviewTransform = useMemo(() => ({ transform: `rotate(${rotation}deg) scale(${1 + cropPercent / 100})` }), [cropPercent, rotation]);

  async function capture() {
    const video = videoRef.current;
    const track = streamRef.current?.getVideoTracks()[0];
    if (!video || !track || video.videoWidth <= 0) {
      toast.error("Aguarde a imagem da camera carregar.");
      return;
    }
    try {
      let blob: Blob | null = null;
      const ImageCaptureCtor = (window as typeof window & { ImageCapture?: new (track: MediaStreamTrack) => { takePhoto: () => Promise<Blob> } }).ImageCapture;
      if (ImageCaptureCtor) {
        try { blob = await new ImageCaptureCtor(track).takePhoto(); } catch { blob = null; }
      }
      if (!blob) {
        const canvas = document.createElement("canvas");
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        const context = canvas.getContext("2d");
        if (!context) throw new Error("capture_canvas_failed");
        context.drawImage(video, 0, 0);
        blob = await canvasBlob(canvas, 0.95);
      }
      setRawCapture(blob);
      stopStream(streamRef.current);
      streamRef.current = null;
    } catch {
      toast.error("Nao foi possivel capturar a foto.");
    }
  }

  async function applyConstraint(values: Record<string, unknown>) {
    const track = streamRef.current?.getVideoTracks()[0];
    if (!track) return;
    try { await track.applyConstraints({ advanced: [values] as MediaTrackConstraintSet[] }); } catch { toast.error("Este controle nao e suportado pela camera ativa."); }
  }

  async function confirm() {
    if (!rawCapture) return;
    setProcessing(true);
    try {
      const normalized = await normalizeCapture(rawCapture, cropPercent, rotation);
      setQuality(normalized.quality);
      if (normalized.quality.blocking.length) return;
      if (normalized.quality.warnings.length && quality.warnings.length === 0) return;
      if (normalized.blob.size > MAX_BYTES) {
        setQuality({ blocking: ["A imagem continua acima de 8 MB."], warnings: normalized.quality.warnings });
        return;
      }
      onConfirm(new File([normalized.blob], `bioimpedancia-camera-${Date.now()}.jpg`, { type: "image/jpeg" }));
      toast.success(normalized.quality.warnings.length ? "Foto aceita com avisos. Revise o OCR antes de salvar." : "Foto pronta para leitura.");
      close();
    } catch {
      toast.error("Nao foi possivel preparar a imagem.");
    } finally {
      setProcessing(false);
    }
  }

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 p-3" role="dialog" aria-modal="true" aria-labelledby="guided-scanner-title">
      <section className="max-h-[96vh] w-full max-w-3xl overflow-y-auto rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-2xl">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 id="guided-scanner-title" className="font-semibold text-lovable-ink">Scanner guiado da bioimpedancia</h2>
            <p className="text-xs text-lovable-ink-muted">Enquadre as quatro bordas, evite reflexos e mantenha o texto legivel.</p>
          </div>
          <Button type="button" size="sm" variant="ghost" onClick={close} aria-label="Fechar camera"><X size={16} /></Button>
        </div>

        {!rawCapture ? (
          <>
            <div className="relative mt-4 overflow-hidden rounded-xl border border-lovable-border bg-black">
              <video ref={videoRef} autoPlay muted playsInline className="aspect-video w-full object-contain" />
              <div className="pointer-events-none absolute inset-[7%] rounded-lg border-2 border-dashed border-white/90 shadow-[0_0_0_999px_rgba(0,0,0,0.28)]" aria-hidden="true" />
            </div>
            {error ? <p className="mt-3 text-sm text-lovable-danger">{error}</p> : null}
            <div className="mt-3 grid gap-2 md:grid-cols-2">
              {devices.length > 1 ? (
                <Select aria-label="Selecionar camera" value={deviceId} onChange={(event) => void startCamera(event.target.value)}>
                  {devices.map((device, index) => <option key={device.deviceId} value={device.deviceId}>{device.label || `Camera ${index + 1}`}</option>)}
                </Select>
              ) : null}
              {capabilities.zoom && zoom != null ? (
                <label className="text-xs text-lovable-ink-muted">Zoom
                  <input className="ml-2 align-middle" type="range" min={capabilities.zoom.min} max={capabilities.zoom.max} step={capabilities.zoom.step} value={zoom} onChange={(event) => { const value = Number(event.target.value); setZoom(value); void applyConstraint({ zoom: value }); }} />
                </label>
              ) : null}
            </div>
            <div className="mt-4 flex flex-wrap justify-end gap-2">
              {devices.length > 1 ? <Button type="button" variant="secondary" onClick={() => { const index = devices.findIndex((item) => item.deviceId === deviceId); const next = devices[(index + 1) % devices.length]; if (next) void startCamera(next.deviceId); }}><SwitchCamera size={14} />Trocar camera</Button> : null}
              {capabilities.torch ? <Button type="button" variant="secondary" onClick={() => { const next = !torch; setTorch(next); void applyConstraint({ torch: next }); }}>{torch ? "Desligar lanterna" : "Ligar lanterna"}</Button> : null}
              <Button type="button" variant="primary" onClick={() => void capture()} disabled={Boolean(error)}><Camera size={14} />Fotografar</Button>
            </div>
          </>
        ) : (
          <>
            <div className="mt-4 flex aspect-video items-center justify-center overflow-hidden rounded-xl border border-lovable-border bg-black">
              {previewUrl ? <img src={previewUrl} alt="Previa da folha fotografada" className="max-h-full max-w-full object-contain transition-transform" style={reviewTransform} /> : null}
            </div>
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <Button type="button" variant="secondary" onClick={() => { setRotation((value) => value - 90); setQuality({ blocking: [], warnings: [] }); }}><RotateCcw size={14} />Girar esquerda</Button>
              <Button type="button" variant="secondary" onClick={() => { setRotation((value) => value + 90); setQuality({ blocking: [], warnings: [] }); }}><RotateCw size={14} />Girar direita</Button>
              <label className="text-xs text-lovable-ink-muted">Recorte
                <input className="ml-2 align-middle" type="range" min="0" max="18" step="1" value={cropPercent} onChange={(event) => { setCropPercent(Number(event.target.value)); setQuality({ blocking: [], warnings: [] }); }} />
              </label>
            </div>
            {quality.blocking.map((message) => <p key={message} className="mt-2 text-sm font-semibold text-lovable-danger">{message}</p>)}
            {quality.warnings.map((message) => <p key={message} className="mt-2 text-sm text-amber-300">{message}</p>)}
            <div className="mt-4 flex flex-wrap justify-end gap-2">
              <Button type="button" variant="secondary" onClick={() => { setRawCapture(null); setQuality({ blocking: [], warnings: [] }); void startCamera(deviceId || undefined); }}><RefreshCcw size={14} />Refazer</Button>
              <Button type="button" variant="primary" onClick={() => void confirm()} disabled={processing}><Check size={14} />{processing ? "Preparando..." : quality.warnings.length ? "Continuar com avisos" : "Confirmar foto"}</Button>
            </div>
          </>
        )}
      </section>
    </div>
  );
}
