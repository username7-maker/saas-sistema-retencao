import { Camera, Check, RefreshCcw, RotateCcw, RotateCw, SwitchCamera, X } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import toast from "react-hot-toast";

import { Button } from "../ui2/Button";
import { Select } from "../ui2/Select";

type ScannerCapabilities = {
  torch: boolean;
  zoom: { min: number; max: number; step: number } | null;
  continuousFocus: boolean;
  continuousExposure: boolean;
  continuousWhiteBalance: boolean;
};

type QualityResult = {
  blocking: string[];
  warnings: string[];
};

type CapturedSegment = {
  file: File;
  width: number;
  height: number;
  rotation: number;
};

type CropCorner = "topLeft" | "topRight" | "bottomRight" | "bottomLeft";
type CropPoint = { x: number; y: number };
type CropCorners = Record<CropCorner, CropPoint>;
const FULL_CROP: CropCorners = {
  topLeft: { x: 0, y: 0 }, topRight: { x: 1, y: 0 },
  bottomRight: { x: 1, y: 1 }, bottomLeft: { x: 0, y: 1 },
};

export function cameraPreferenceScore(device: MediaDeviceInfo): number {
  const label = device.label.toLocaleLowerCase("pt-BR");
  let score = 0;
  if (/traseira|rear|back|environment/.test(label)) score += 30;
  if (/usb|logitech|webcam|brio/.test(label)) score += 15;
  if (/principal|main|wide camera/.test(label)) score += 20;
  if (/ultra|ultrawide|ultra-wide|0[,.]5/.test(label)) score -= 60;
  if (/virtual|obs|snap camera|manycam/.test(label)) score -= 80;
  return score;
}

export function preferredCamera(devices: MediaDeviceInfo[]): MediaDeviceInfo | undefined {
  return [...devices].sort((left, right) => cameraPreferenceScore(right) - cameraPreferenceScore(left))[0];
}

export interface DocumentCaptureMetadata {
  width: number;
  height: number;
  rotation: number;
  device_kind: "webcam" | "mobile" | "unknown";
  quality_codes: string[];
  document_confidence: number | null;
  capture_mode?: "single" | "segmented";
  segments?: Array<{
    role: "full" | "top" | "middle" | "bottom";
    width: number;
    height: number;
    rotation: number;
    index: number;
  }>;
}

interface GuidedDocumentScannerProps {
  open: boolean;
  onClose: () => void;
  onConfirm: (file: File, metadata?: DocumentCaptureMetadata, supplementalFiles?: File[]) => void;
}

const MAX_SIDE = 4000;
const MAX_BYTES = 8 * 1024 * 1024;
const SCANNER_V2_ENABLED = import.meta.env.VITE_BIOIMPEDANCE_SCANNER_V2 === "true";
const CAPTURE_GUIDE_V3_ENABLED = import.meta.env.VITE_BIOIMPEDANCE_CAPTURE_GUIDE_V3 === "true";
const SEGMENTED_CAPTURE_ENABLED = import.meta.env.VITE_BIOIMPEDANCE_SEGMENTED_CAPTURE_V1 === "true"
  && import.meta.env.VITE_BODY_COMPOSITION_MULTI_IMAGE_PARSE_V1 === "true";
const PREFERRED_CAMERA_STORAGE_KEY = "cordex:bioimpedance:preferred-camera";
const RESOLUTION_LADDER = [
  { width: 3840, height: 2160 },
  { width: 2560, height: 1440 },
  { width: 1920, height: 1080 },
  { width: 1280, height: 720 },
] as const;

function stopStream(stream: MediaStream | null): void {
  stream?.getTracks().forEach((track) => track.stop());
}

const EMPTY_CAPABILITIES: ScannerCapabilities = {
  torch: false,
  zoom: null,
  continuousFocus: false,
  continuousExposure: false,
  continuousWhiteBalance: false,
};

function isMobileCaptureDevice(): boolean {
  return /android|iphone|ipad|mobile/i.test(navigator.userAgent);
}

async function waitForStableCamera(video: HTMLVideoElement): Promise<boolean> {
  const deadline = performance.now() + 2_000;
  const sample = document.createElement("canvas");
  sample.width = 96;
  sample.height = 54;
  const context = sample.getContext("2d", { willReadFrequently: true });
  if (!context) return true;
  let previous: Uint8ClampedArray | null = null;
  let stableFrames = 0;
  while (performance.now() < deadline) {
    await Promise.race([
      new Promise<void>((resolve) => {
        const frameVideo = video as HTMLVideoElement & { requestVideoFrameCallback?: (callback: () => void) => number };
        if (frameVideo.requestVideoFrameCallback) frameVideo.requestVideoFrameCallback(() => resolve());
        else window.setTimeout(resolve, 120);
      }),
      new Promise<void>((resolve) => window.setTimeout(resolve, 180)),
    ]);
    if (video.videoWidth <= 0 || video.videoHeight <= 0) continue;
    context.drawImage(video, 0, 0, sample.width, sample.height);
    const current = context.getImageData(0, 0, sample.width, sample.height).data;
    let luminance = 0;
    let movement = 0;
    for (let index = 0; index < current.length; index += 16) {
      luminance += current[index] + current[index + 1] + current[index + 2];
      if (previous) movement += Math.abs(current[index] - previous[index]);
    }
    const samples = Math.max(1, current.length / 16);
    const mean = luminance / (samples * 3);
    const delta = previous ? movement / samples : Number.POSITIVE_INFINITY;
    stableFrames = mean > 8 && mean < 250 && delta < 7 ? stableFrames + 1 : 0;
    previous = new Uint8ClampedArray(current);
    if (stableFrames >= 3) return true;
  }
  return false;
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
  const scale = Math.min(1, (SCANNER_V2_ENABLED ? 1024 : 256) / Math.max(canvas.width, canvas.height));
  sample.width = Math.max(1, Math.round(canvas.width * scale));
  sample.height = Math.max(1, Math.round(canvas.height * scale));
  const context = sample.getContext("2d", { willReadFrequently: true });
  if (!context) return { blocking: [], warnings: ["Nao foi possivel verificar automaticamente a qualidade."] };
  context.drawImage(canvas, 0, 0, sample.width, sample.height);
  const pixels = context.getImageData(0, 0, sample.width, sample.height).data;
  let luminanceSum = 0;
  const luminance = new Float32Array(sample.width * sample.height);
  let highlights = 0;
  for (let index = 0; index < pixels.length; index += 4) {
    const value = 0.2126 * pixels[index] + 0.7152 * pixels[index + 1] + 0.0722 * pixels[index + 2];
    luminance[index / 4] = value;
    luminanceSum += value;
    if (value > 248) highlights += 1;
  }
  const count = pixels.length / 4;
  const mean = luminanceSum / count;
  const regionSharpness = [0, 0, 0];
  const regionSamples = [0, 0, 0];
  for (let y = 1; y < sample.height - 1; y += 1) {
    const region = Math.min(2, Math.floor((y / sample.height) * 3));
    for (let x = 1; x < sample.width - 1; x += 1) {
      const offset = y * sample.width + x;
      const laplacian = Math.abs(
        luminance[offset - 1] + luminance[offset + 1]
        + luminance[offset - sample.width] + luminance[offset + sample.width]
        - 4 * luminance[offset],
      );
      regionSharpness[region] += laplacian;
      regionSamples[region] += 1;
    }
  }
  const sharpness = regionSharpness.map((value, index) => value / Math.max(1, regionSamples[index]));
  const blocking: string[] = [];
  const warnings: string[] = [];
  if (mean < 8 || Math.max(...sharpness) < 0.8) blocking.push("A foto não tem informação legível.");
  if (canvas.width < 640 || canvas.height < 640) warnings.push("Aproxime o papel ou fotografe em partes.");
  else if (Math.max(canvas.width, canvas.height) < 1200) warnings.push("Resolucao baixa; aproxime a folha e refaca se o texto estiver pequeno.");
  if (mean < 55) warnings.push("Aumente um pouco a iluminação.");
  if (Math.min(...sharpness) < 2.2) warnings.push("Mantenha a câmera firme e aproxime a folha.");
  if (highlights / count > 0.34) warnings.push("Evite reflexo direto sobre o papel.");
  return { blocking, warnings };
}

async function normalizeCapture(blob: Blob, crop: CropCorners, rotation: number): Promise<{ blob: Blob; quality: QualityResult; width: number; height: number }> {
  const image = await imageFromBlob(blob);
  const points = Object.values(crop).map((point) => ({ x: point.x * image.naturalWidth, y: point.y * image.naturalHeight }));
  const cropX = Math.floor(Math.min(...points.map((point) => point.x)));
  const cropY = Math.floor(Math.min(...points.map((point) => point.y)));
  const cropRight = Math.ceil(Math.max(...points.map((point) => point.x)));
  const cropBottom = Math.ceil(Math.max(...points.map((point) => point.y)));
  const sourceWidth = Math.max(1, cropRight - cropX);
  const sourceHeight = Math.max(1, cropBottom - cropY);
  const clipped = document.createElement("canvas");
  clipped.width = sourceWidth;
  clipped.height = sourceHeight;
  const clippedContext = clipped.getContext("2d");
  if (!clippedContext) throw new Error("capture_canvas_failed");
  clippedContext.fillStyle = "#fff";
  clippedContext.fillRect(0, 0, sourceWidth, sourceHeight);
  clippedContext.save();
  clippedContext.beginPath();
  const polygon = [crop.topLeft, crop.topRight, crop.bottomRight, crop.bottomLeft];
  polygon.forEach((point, index) => {
    const x = point.x * image.naturalWidth - cropX;
    const y = point.y * image.naturalHeight - cropY;
    if (index === 0) clippedContext.moveTo(x, y); else clippedContext.lineTo(x, y);
  });
  clippedContext.closePath();
  clippedContext.clip();
  clippedContext.drawImage(image, -cropX, -cropY);
  clippedContext.restore();
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
  context.drawImage(clipped, -drawWidth / 2, -drawHeight / 2, drawWidth, drawHeight);
  const quality = analyzeCanvas(canvas);
  let jpeg = await canvasBlob(canvas, 0.9);
  if (jpeg.size > MAX_BYTES) jpeg = await canvasBlob(canvas, 0.78);
  return { blob: jpeg, quality, width: canvas.width, height: canvas.height };
}

export function GuidedDocumentScanner({ open, onClose, onConfirm }: GuidedDocumentScannerProps) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [devices, setDevices] = useState<MediaDeviceInfo[]>([]);
  const [deviceId, setDeviceId] = useState("");
  const [rawCapture, setRawCapture] = useState<Blob | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [cropCorners, setCropCorners] = useState<CropCorners>(FULL_CROP);
  const [adjustingCrop, setAdjustingCrop] = useState(false);
  const [rotation, setRotation] = useState(0);
  const [quality, setQuality] = useState<QualityResult>({ blocking: [], warnings: [] });
  const [processing, setProcessing] = useState(false);
  const [cameraReady, setCameraReady] = useState(false);
  const [actualSettings, setActualSettings] = useState<MediaTrackSettings | null>(null);
  const [capabilities, setCapabilities] = useState<ScannerCapabilities>({
    torch: false,
    zoom: null,
    continuousFocus: false,
    continuousExposure: false,
    continuousWhiteBalance: false,
  });
  const [torch, setTorch] = useState(false);
  const [zoom, setZoom] = useState<number | null>(null);
  const [cameraHint, setCameraHint] = useState("Preparando camera...");
  const [previewDimensions, setPreviewDimensions] = useState<{ width: number; height: number } | null>(null);
  const [captureMode, setCaptureMode] = useState<"single" | "segmented">("single");
  const [segmentFiles, setSegmentFiles] = useState<CapturedSegment[]>([]);
  const [segmentIndex, setSegmentIndex] = useState(0);
  const [segmentsReady, setSegmentsReady] = useState(false);
  const [acceptWarnings, setAcceptWarnings] = useState(false);

  const close = useCallback(() => {
    stopStream(streamRef.current);
    streamRef.current = null;
    setRawCapture(null);
    setError(null);
    setTorch(false);
    setCapabilities(EMPTY_CAPABILITIES);
    setPreviewDimensions(null);
    setSegmentFiles([]);
    setSegmentIndex(0);
    setSegmentsReady(false);
    setCaptureMode("single");
    onClose();
  }, [onClose]);

  const startCamera = useCallback(async (requestedDeviceId?: string, rememberManualChoice = false) => {
    stopStream(streamRef.current);
    streamRef.current = null;
    setError(null);
    setCameraReady(false);
    setCameraHint("Preparando camera...");
    setTorch(false);
    setCapabilities(EMPTY_CAPABILITIES);
    setPreviewDimensions(null);
    if (!navigator.mediaDevices?.getUserMedia) {
      setError("A camera nao esta disponivel neste navegador. Use o envio de arquivo.");
      return;
    }
    try {
      let stream: MediaStream | null = null;
      const storedDevice = SCANNER_V2_ENABLED ? window.localStorage.getItem(PREFERRED_CAMERA_STORAGE_KEY) : "";
      const storedWasManual = window.localStorage.getItem(`${PREFERRED_CAMERA_STORAGE_KEY}:manual`) === "true";
      const preferredDevice = requestedDeviceId || storedDevice || "";
      const requestedResolution = RESOLUTION_LADDER[0];
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          audio: false,
          video: {
            ...(preferredDevice ? { deviceId: { exact: preferredDevice } } : { facingMode: { ideal: "environment" } }),
            width: { ideal: requestedResolution.width },
            height: { ideal: requestedResolution.height },
            frameRate: { ideal: 30, min: 15 },
          },
        });
      } catch {
        stream = null;
      }
      if (!stream) stream = await navigator.mediaDevices.getUserMedia({ audio: false, video: true });
      streamRef.current = stream;
      if (videoRef.current) videoRef.current.srcObject = stream;
      const track = stream.getVideoTracks()[0];
      const rawCapabilities = typeof track?.getCapabilities === "function" ? track.getCapabilities() as MediaTrackCapabilities & Record<string, unknown> : {};
      const zoomCapability = rawCapabilities.zoom as { min?: number; max?: number; step?: number } | undefined;
      const focusModes = Array.isArray(rawCapabilities.focusMode) ? rawCapabilities.focusMode as string[] : [];
      const exposureModes = Array.isArray(rawCapabilities.exposureMode) ? rawCapabilities.exposureMode as string[] : [];
      const whiteBalanceModes = Array.isArray(rawCapabilities.whiteBalanceMode) ? rawCapabilities.whiteBalanceMode as string[] : [];
      setCapabilities({
        torch: Boolean(rawCapabilities.torch),
        zoom: zoomCapability?.min != null && zoomCapability.max != null
          ? { min: zoomCapability.min, max: zoomCapability.max, step: zoomCapability.step ?? 0.1 }
          : null,
        continuousFocus: focusModes.includes("continuous"),
        continuousExposure: exposureModes.includes("continuous"),
        continuousWhiteBalance: whiteBalanceModes.includes("continuous"),
      });
      const advanced: Record<string, unknown> = {};
      if (SCANNER_V2_ENABLED && focusModes.includes("continuous")) advanced.focusMode = "continuous";
      if (SCANNER_V2_ENABLED && exposureModes.includes("continuous")) advanced.exposureMode = "continuous";
      if (SCANNER_V2_ENABLED && whiteBalanceModes.includes("continuous")) advanced.whiteBalanceMode = "continuous";
      if (Object.keys(advanced).length) {
        try { await track.applyConstraints({ advanced: [advanced] as MediaTrackConstraintSet[] }); } catch { /* optional */ }
      }
      const widthCapability = rawCapabilities.width as { max?: number } | undefined;
      const heightCapability = rawCapabilities.height as { max?: number } | undefined;
      if (CAPTURE_GUIDE_V3_ENABLED && widthCapability?.max && heightCapability?.max) {
        try {
          await track.applyConstraints({
            width: { ideal: widthCapability.max },
            height: { ideal: heightCapability.max },
          });
        } catch { /* the active mode is still usable */ }
      }
      const available = (await navigator.mediaDevices.enumerateDevices()).filter((item) => item.kind === "videoinput");
      setDevices(available);
      const settings = track?.getSettings() ?? null;
      const zoomSetting = settings?.zoom as number | undefined;
      setZoom(zoomSetting ?? zoomCapability?.min ?? null);
      const activeDeviceId = settings?.deviceId ?? requestedDeviceId ?? "";
      const automaticChoice = preferredCamera(available);
      const activeDevice = available.find((item) => item.deviceId === activeDeviceId);
      if (!requestedDeviceId && !storedWasManual && automaticChoice?.deviceId && activeDevice?.deviceId !== automaticChoice.deviceId
        && cameraPreferenceScore(automaticChoice) > cameraPreferenceScore(activeDevice ?? automaticChoice)) {
        stopStream(stream);
        streamRef.current = null;
        await startCamera(automaticChoice.deviceId);
        return;
      }
      setActualSettings(settings);
      setDeviceId(activeDeviceId);
      if (SCANNER_V2_ENABLED && activeDeviceId) window.localStorage.setItem(PREFERRED_CAMERA_STORAGE_KEY, activeDeviceId);
      if (rememberManualChoice) window.localStorage.setItem(`${PREFERRED_CAMERA_STORAGE_KEY}:manual`, "true");
      const video = videoRef.current;
      if (video) {
        const stable = CAPTURE_GUIDE_V3_ENABLED ? await waitForStableCamera(video) : true;
        if (video.videoWidth > 0 && video.videoHeight > 0) {
          setPreviewDimensions({ width: video.videoWidth, height: video.videoHeight });
        } else if (settings?.width && settings.height) {
          setPreviewDimensions({ width: settings.width, height: settings.height });
        }
        setCameraHint(stable ? "Foto pronta" : "Segure a camera e confira o foco");
        setCameraReady(true);
      }
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
    const mediaDevices = navigator.mediaDevices;
    if (!SCANNER_V2_ENABLED || !open || !mediaDevices) return;
    const deviceEvents = mediaDevices as unknown as EventTarget;
    const handleDeviceChange = () => void startCamera(deviceId || undefined);
    deviceEvents.addEventListener("devicechange", handleDeviceChange);
    return () => deviceEvents.removeEventListener("devicechange", handleDeviceChange);
  }, [deviceId, open, startCamera]);

  useEffect(() => {
    if (!rawCapture) {
      setPreviewUrl(null);
      return;
    }
    const url = URL.createObjectURL(rawCapture);
    setPreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [rawCapture]);

  const reviewTransform = useMemo(() => ({ transform: `rotate(${rotation}deg)` }), [rotation]);
  const cropPolygon = useMemo(() => [cropCorners.topLeft, cropCorners.topRight, cropCorners.bottomRight, cropCorners.bottomLeft]
    .map((point) => `${point.x * 100}% ${point.y * 100}%`).join(","), [cropCorners]);
  function moveCorner(corner: CropCorner, event: React.PointerEvent<HTMLButtonElement>) {
    const frame = event.currentTarget.parentElement?.getBoundingClientRect();
    if (!frame) return;
    const limits: Record<CropCorner, { minX: number; maxX: number; minY: number; maxY: number }> = {
      topLeft: { minX: 0, maxX: .49, minY: 0, maxY: .49 }, topRight: { minX: .51, maxX: 1, minY: 0, maxY: .49 },
      bottomRight: { minX: .51, maxX: 1, minY: .51, maxY: 1 }, bottomLeft: { minX: 0, maxX: .49, minY: .51, maxY: 1 },
    };
    const limit = limits[corner];
    const x = Math.min(limit.maxX, Math.max(limit.minX, (event.clientX - frame.left) / frame.width));
    const y = Math.min(limit.maxY, Math.max(limit.minY, (event.clientY - frame.top) / frame.height));
    setCropCorners((current) => ({ ...current, [corner]: { x, y } }));
    setQuality({ blocking: [], warnings: [] });
  }
  const previewWidth = previewDimensions?.width ?? Number(actualSettings?.width || 0);
  const previewHeight = previewDimensions?.height ?? Number(actualSettings?.height || 0);
  const streamIsPortrait = previewHeight > previewWidth;

  async function capture() {
    const video = videoRef.current;
    const track = streamRef.current?.getVideoTracks()[0];
    if (!video || !track || video.videoWidth <= 0) {
      toast.error("Aguarde a imagem da camera carregar.");
      return;
    }
    try {
      let blob: Blob | null = null;
      type ImageCaptureLike = {
        takePhoto: (settings?: { imageWidth?: number; imageHeight?: number }) => Promise<Blob>;
        getPhotoCapabilities?: () => Promise<{ imageWidth?: { max?: number }; imageHeight?: { max?: number } }>;
      };
      const ImageCaptureCtor = (window as typeof window & { ImageCapture?: new (track: MediaStreamTrack) => ImageCaptureLike }).ImageCapture;
      if (ImageCaptureCtor) {
        try {
          const imageCapture = new ImageCaptureCtor(track);
          const photoCapabilities = SCANNER_V2_ENABLED ? await imageCapture.getPhotoCapabilities?.() : undefined;
          const photoSettings = photoCapabilities?.imageWidth?.max && photoCapabilities?.imageHeight?.max
            ? { imageWidth: photoCapabilities.imageWidth.max, imageHeight: photoCapabilities.imageHeight.max }
            : undefined;
          blob = await imageCapture.takePhoto(photoSettings);
        } catch { blob = null; }
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
      const normalized = await normalizeCapture(rawCapture, cropCorners, rotation);
      setQuality(normalized.quality);
      if (normalized.quality.blocking.length) return;
      if (normalized.quality.warnings.length && !acceptWarnings) return;
      if (normalized.blob.size > MAX_BYTES) {
        setQuality({ blocking: ["A imagem continua acima de 8 MB."], warnings: normalized.quality.warnings });
        return;
      }
      const segmentRole = captureMode === "single" ? "full" : (["top", "middle", "bottom"] as const)[segmentIndex];
      const capturedFile = new File([normalized.blob], `bioimpedancia-${segmentRole}-${Date.now()}.jpg`, { type: "image/jpeg" });
      const capturedSegment: CapturedSegment = {
        file: capturedFile,
        width: normalized.width,
        height: normalized.height,
        rotation,
      };
      if (captureMode === "segmented") {
        const updated = [...segmentFiles];
        updated[segmentIndex] = capturedSegment;
        setSegmentFiles(updated);
        setRawCapture(null);
        setQuality({ blocking: [], warnings: [] });
        setAcceptWarnings(false);
        setRotation(0);
        setCropCorners(FULL_CROP);
        if (updated.length === 3 && updated.every(Boolean)) {
          setSegmentsReady(true);
        } else {
          setSegmentIndex(updated.length);
          await startCamera(deviceId || undefined);
        }
        return;
      }
      deliver([capturedSegment]);
    } catch {
      toast.error("Nao foi possivel preparar a imagem.");
    } finally {
      setProcessing(false);
    }
  }

  function deliver(allSegments: CapturedSegment[]) {
      if (captureMode === "segmented" && allSegments.length !== 3) return;
      onConfirm(
        allSegments[0].file,
        {
          width: allSegments[0].width,
          height: allSegments[0].height,
          rotation: allSegments[0].rotation,
          device_kind: isMobileCaptureDevice() ? "mobile" : "webcam",
          quality_codes: [
            ...(quality.warnings.length ? ["quality_warning"] : []),
          ],
          document_confidence: null,
          capture_mode: captureMode,
          segments: allSegments.map((segment, index) => ({
            role: captureMode === "single" ? "full" : (["top", "middle", "bottom"] as const)[index],
            width: segment.width,
            height: segment.height,
            rotation: segment.rotation,
            index,
          })),
        },
        allSegments.slice(1).map((segment) => segment.file),
      );
      toast.success("Foto pronta para leitura.");
      close();
  }

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 p-0 sm:p-3" role="dialog" aria-modal="true" aria-labelledby="guided-scanner-title">
      <section className="h-[100dvh] w-full overflow-y-auto border border-lovable-border bg-lovable-surface p-4 pb-[max(1rem,env(safe-area-inset-bottom))] pt-[max(1rem,env(safe-area-inset-top))] shadow-2xl sm:h-auto sm:max-h-[96dvh] sm:max-w-3xl sm:rounded-2xl">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 id="guided-scanner-title" className="font-semibold text-lovable-ink">Scanner guiado da bioimpedancia</h2>
            <p className="text-xs text-lovable-ink-muted">
              {captureMode === "segmented"
                ? segmentsReady ? "As tres partes estao prontas. Confira antes de continuar." : `Fotografe ${(["o topo", "o centro", "o rodape"] as const)[segmentIndex]} do papel (${segmentIndex + 1} de 3).`
                : isMobileCaptureDevice() ? "Mostre o papel inteiro dentro da moldura." : "Coloque o papel deitado dentro da moldura."}
            </p>
          </div>
          <Button type="button" size="sm" variant="ghost" onClick={close} aria-label="Fechar camera"><X size={16} /></Button>
        </div>

        {segmentsReady ? (
          <div className="mt-4 space-y-3">
            {segmentFiles.map((_, index) => (
              <div key={index} className="flex items-center justify-between gap-2">
                <span>{["Topo", "Centro", "Rodape"][index]} confirmado</span>
                <Button type="button" variant="secondary" onClick={() => {
                  setSegmentIndex(index); setSegmentsReady(false); setRawCapture(null);
                  setRotation(0); setCropCorners(FULL_CROP); setAcceptWarnings(false);
                  setQuality({ blocking: [], warnings: [] }); void startCamera(deviceId || undefined);
                }}>Refazer {["topo", "centro", "rodape"][index]}</Button>
              </div>
            ))}
            <Button type="button" variant="primary" onClick={() => deliver(segmentFiles)}>Usar as tres fotos</Button>
          </div>
        ) : !rawCapture ? (
          <>
            <div className="relative mx-auto mt-4 max-h-[65dvh] max-w-full overflow-hidden rounded-xl border border-lovable-border bg-black"
              style={{ aspectRatio: previewWidth > 0 && previewHeight > 0 ? `${previewWidth}/${previewHeight}` : "16/9" }}>
              <video
                ref={videoRef}
                autoPlay
                muted
                playsInline
                className="h-full w-full object-contain"
                onLoadedMetadata={(event) => {
                  const video = event.currentTarget;
                  if (video.videoWidth > 0 && video.videoHeight > 0) {
                    setPreviewDimensions({ width: video.videoWidth, height: video.videoHeight });
                  }
                }}
              />
              <div
                className={`pointer-events-none absolute rounded-lg border-2 border-dashed border-white/90 shadow-[0_0_0_999px_rgba(0,0,0,0.28)] ${
                  streamIsPortrait ? "inset-y-[5%] left-[28%] right-[28%]" : "inset-x-[5%] bottom-[34%] top-[34%]"
                }`}
                aria-hidden="true"
              />
            </div>
            {error ? <p className="mt-3 text-sm text-lovable-danger">{error}</p> : null}
            <div className="mt-3 grid gap-2 md:grid-cols-2">
              {devices.length > 1 ? (
                <Select aria-label="Selecionar camera" value={deviceId} onChange={(event) => void startCamera(event.target.value, true)}>
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
              {SEGMENTED_CAPTURE_ENABLED && captureMode === "single" ? (
                <Button type="button" variant="ghost" onClick={() => { setCaptureMode("segmented"); setSegmentFiles([]); }}>
                  Fotografar em partes
                </Button>
              ) : null}
              {devices.length > 1 ? <Button type="button" variant="secondary" onClick={() => { const index = devices.findIndex((item) => item.deviceId === deviceId); const next = devices[(index + 1) % devices.length]; if (next) void startCamera(next.deviceId, true); }}><SwitchCamera size={14} />Trocar camera</Button> : null}
              {capabilities.torch ? <Button type="button" variant="secondary" onClick={() => { const next = !torch; setTorch(next); void applyConstraint({ torch: next }); }}>{torch ? "Desligar lanterna" : "Ligar lanterna"}</Button> : null}
              <Button type="button" variant="primary" onClick={() => void capture()} disabled={Boolean(error) || !cameraReady}><Camera size={14} />{cameraReady ? "Fotografar" : "Preparando câmera..."}</Button>
            </div>
            <p className="mt-2 text-center text-xs text-lovable-ink-muted">{cameraHint}</p>
            {actualSettings?.width && actualSettings.height ? (
              <details className="mt-3 text-xs text-lovable-ink-muted">
                <summary>Detalhes da câmera</summary>
                <p className="mt-1">Imagem ativa: {actualSettings.width} × {actualSettings.height}px{capabilities.continuousFocus ? " · foco contínuo" : ""}</p>
              </details>
            ) : null}
          </>
        ) : (
          <>
            <div className="relative mt-4 flex aspect-video items-center justify-center overflow-hidden rounded-xl border border-lovable-border bg-black">
              {previewUrl ? <img src={previewUrl} alt="Previa da folha fotografada" className="max-h-full max-w-full object-contain transition-transform" style={reviewTransform} /> : null}
              {adjustingCrop ? <div className="absolute inset-0" style={{ clipPath: `polygon(${cropPolygon})`, boxShadow: "0 0 0 999px rgba(0,0,0,.55)" }}>
                {(Object.entries(cropCorners) as [CropCorner, CropPoint][]).map(([corner, point]) => <button
                  key={corner} type="button" aria-label={`Ajustar canto ${corner}`} className="absolute h-11 w-11 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-white bg-blue-500/80 touch-none"
                  style={{ left: `${point.x * 100}%`, top: `${point.y * 100}%` }}
                  onPointerDown={(event) => event.currentTarget.setPointerCapture(event.pointerId)}
                  onPointerMove={(event) => { if (event.currentTarget.hasPointerCapture(event.pointerId)) moveCorner(corner, event); }}
                />)}
              </div> : null}
            </div>
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <Button type="button" variant="secondary" onClick={() => { setRotation((value) => value - 90); setQuality({ blocking: [], warnings: [] }); }}><RotateCcw size={14} />Girar esquerda</Button>
              <Button type="button" variant="secondary" onClick={() => { setRotation((value) => value + 90); setQuality({ blocking: [], warnings: [] }); }}><RotateCw size={14} />Girar direita</Button>
              <Button type="button" variant="secondary" onClick={() => setAdjustingCrop((value) => !value)}>{adjustingCrop ? "Concluir recorte" : "Ajustar recorte"}</Button>
              {adjustingCrop ? <Button type="button" variant="ghost" onClick={() => setCropCorners(FULL_CROP)}>Usar imagem inteira</Button> : null}
            </div>
            {quality.blocking.map((message) => <p key={message} className="mt-2 text-sm font-semibold text-lovable-danger">{message}</p>)}
            {quality.warnings.length ? (
              <div className="mt-3 rounded-xl border border-amber-400/40 bg-amber-400/10 p-3 text-sm text-amber-100">
                <p>A foto pode ser lida, mas {quality.warnings[0].toLocaleLowerCase("pt-BR")}</p>
                <div className="mt-2 flex gap-2">
                  <Button type="button" size="sm" variant="secondary" onClick={() => setAcceptWarnings(true)}>Usar esta foto</Button>
                  <Button type="button" size="sm" variant="ghost" onClick={() => { setRawCapture(null); setQuality({ blocking: [], warnings: [] }); setAcceptWarnings(false); void startCamera(deviceId || undefined); }}>Refazer</Button>
                </div>
              </div>
            ) : null}
            <div className="mt-4 flex flex-wrap justify-end gap-2">
              <Button type="button" variant="secondary" onClick={() => { setRawCapture(null); setQuality({ blocking: [], warnings: [] }); void startCamera(deviceId || undefined); }}><RefreshCcw size={14} />Refazer</Button>
              <Button type="button" variant="primary" onClick={() => void confirm()} disabled={processing || (quality.warnings.length > 0 && !acceptWarnings)}><Check size={14} />{processing ? "Preparando..." : captureMode === "segmented" && segmentFiles.length < 2 ? "Confirmar e continuar" : "Confirmar foto"}</Button>
            </div>
          </>
        )}
      </section>
    </div>
  );
}
