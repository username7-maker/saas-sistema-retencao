import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.hoisted(() => {
  vi.stubEnv("VITE_BIOIMPEDANCE_SMART_CAPTURE_V1", "true");
  vi.stubEnv("VITE_BIOIMPEDANCE_SCANNER_V2", "true");
  vi.stubEnv("VITE_BIOIMPEDANCE_SEGMENTED_CAPTURE_V1", "true");
  vi.stubEnv("VITE_BODY_COMPOSITION_MULTI_IMAGE_PARSE_V1", "true");
});
import { GuidedDocumentScanner } from "../components/assessments/GuidedDocumentScanner";
import { bodyCompositionService } from "../services/bodyCompositionService";
import * as analysisLoop from "../components/assessments/scanner/analysisLoop";

const metadata = {
  corners: [{ x: .1, y: .1 }, { x: .9, y: .1 }, { x: .9, y: .9 }, { x: .1, y: .9 }],
  confidence: .9, method: "perspective", quality_codes: [], quality_metrics: {},
  source_width: 1600, source_height: 2400, output_width: 1400, output_height: 2200,
};
const photo = new File(["original"], "receipt.jpg", { type: "image/jpeg" });
const corrected = new Blob(["corrected"], { type: "image/jpeg" });
let drawnSources: string[];
let media: EventTarget & { getUserMedia: ReturnType<typeof vi.fn> };

beforeEach(() => {
  drawnSources = [];
  media = Object.assign(new EventTarget(), {
    getUserMedia: vi.fn().mockRejectedValue(new Error("no camera")),
    enumerateDevices: vi.fn().mockResolvedValue([]),
  });
  Object.defineProperty(navigator, "mediaDevices", { configurable: true, value: media });
  vi.spyOn(bodyCompositionService, "recordCaptureEvent").mockResolvedValue(undefined);
  vi.spyOn(URL, "createObjectURL").mockImplementation((blob) => blob === corrected ? "blob:corrected" : "blob:original");
  vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => undefined);
  Object.defineProperty(HTMLImageElement.prototype, "decode", { configurable: true, value: vi.fn().mockResolvedValue(undefined) });
  vi.spyOn(HTMLImageElement.prototype, "naturalWidth", "get").mockReturnValue(1600);
  vi.spyOn(HTMLImageElement.prototype, "naturalHeight", "get").mockReturnValue(2400);
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue({
    fillRect() {}, save() {}, restore() {}, beginPath() {}, moveTo() {}, lineTo() {}, closePath() {}, clip() {}, translate() {}, rotate() {},
    drawImage(source: CanvasImageSource) { if (source instanceof HTMLImageElement) drawnSources.push(source.src); },
    getImageData(_x: number, _y: number, width: number, height: number) {
      const data = new Uint8ClampedArray(width * height * 4);
      for (let i = 0; i < data.length; i += 4) {
        const value = Math.floor(i / 4 / width) % 4 < 2 ? 50 : 220;
        data.set([value, value, value, 255], i);
      }
      return { data, width, height };
    },
  } as unknown as CanvasRenderingContext2D);
  vi.spyOn(HTMLCanvasElement.prototype, "toBlob").mockImplementation((callback) => callback(new Blob(["output"], { type: "image/jpeg" })));
});
afterEach(() => vi.restoreAllMocks());

function upload(container: HTMLElement) {
  fireEvent.change(container.querySelector('input[type="file"]')!, { target: { files: [photo] } });
}

describe("scanner review", () => {
  it("keeps a connected webcam available when device enumeration and capabilities fail", async () => {
    const track = { stop: vi.fn(), readyState: "live", getCapabilities: () => { throw new Error("unsupported"); }, getSettings: () => ({ deviceId: "webcam" }) };
    media.getUserMedia.mockResolvedValue({ getTracks: () => [track], getVideoTracks: () => [track] });
    vi.spyOn(navigator.mediaDevices, "enumerateDevices").mockRejectedValue(new Error("enumeration failed"));
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => { throw new Error("storage blocked"); });
    vi.spyOn(HTMLVideoElement.prototype, "videoWidth", "get").mockReturnValue(1600);
    vi.spyOn(HTMLVideoElement.prototype, "videoHeight", "get").mockReturnValue(900);
    const { unmount } = render(<GuidedDocumentScanner memberId="synthetic" open onClose={vi.fn()} onConfirm={vi.fn()} />);
    await waitFor(() => expect(screen.getByRole("button", { name: "Fotografar agora" })).toBeEnabled());
    act(() => media.dispatchEvent(new Event("devicechange")));
    expect(media.getUserMedia).toHaveBeenCalledTimes(1);
    expect(track.stop).not.toHaveBeenCalled();
    unmount();
    expect(track.stop).toHaveBeenCalled();
  });

  it("explains permission denial without issuing another permission request", async () => {
    media.getUserMedia.mockRejectedValue(new DOMException("denied", "NotAllowedError"));
    render(<GuidedDocumentScanner memberId="synthetic" open onClose={vi.fn()} onConfirm={vi.fn()} />);
    expect(await screen.findByText(/Permita o acesso a camera/)).toBeInTheDocument();
    expect(media.getUserMedia).toHaveBeenCalledTimes(1);
  });

  it("keeps the camera zoom at its actual value when the webcam ignores the request", async () => {
    const track = {
      stop: vi.fn(),
      getCapabilities: () => ({ zoom: { min: 1, max: 3, step: .1 } }),
      getSettings: () => ({ deviceId: "webcam", zoom: 1 }),
      applyConstraints: vi.fn().mockResolvedValue(undefined),
    };
    media.getUserMedia.mockResolvedValue({ getTracks: () => [track], getVideoTracks: () => [track] });
    vi.spyOn(HTMLVideoElement.prototype, "videoWidth", "get").mockReturnValue(1600);
    vi.spyOn(HTMLVideoElement.prototype, "videoHeight", "get").mockReturnValue(900);
    render(<GuidedDocumentScanner memberId="synthetic" open onClose={vi.fn()} onConfirm={vi.fn()} />);
    const slider = await screen.findByRole("slider", { name: "Zoom da câmera" });
    fireEvent.change(slider, { target: { value: "2" } });
    await waitFor(() => expect(track.applyConstraints).toHaveBeenCalled());
    await waitFor(() => expect(slider).toHaveValue("1"));
    expect(screen.getByText(/não aceitou o zoom/i)).toBeInTheDocument();
  });

  it("shows a zoom change only after the camera reports the new setting", async () => {
    let actualZoom = 1;
    const track = {
      stop: vi.fn(),
      getCapabilities: () => ({ zoom: { min: 1, max: 3, step: .1 } }),
      getSettings: () => ({ deviceId: "webcam", zoom: actualZoom }),
      applyConstraints: vi.fn().mockImplementation(async () => { actualZoom = 2; }),
    };
    media.getUserMedia.mockResolvedValue({ getTracks: () => [track], getVideoTracks: () => [track] });
    vi.spyOn(HTMLVideoElement.prototype, "videoWidth", "get").mockReturnValue(1600);
    vi.spyOn(HTMLVideoElement.prototype, "videoHeight", "get").mockReturnValue(900);
    render(<GuidedDocumentScanner memberId="synthetic" open onClose={vi.fn()} onConfirm={vi.fn()} />);
    const slider = await screen.findByRole("slider", { name: "Zoom da câmera" });
    fireEvent.change(slider, { target: { value: "2" } });
    await waitFor(() => expect(slider).toHaveValue("2"));
    expect(screen.getByText("2.0×")).toBeInTheDocument();
    expect(screen.queryByText(/não aceitou o zoom/i)).not.toBeInTheDocument();
  });

  it("retries a camera zoom as a required constraint when an optional one is ignored", async () => {
    let actualZoom = 1;
    const track = {
      stop: vi.fn(),
      getCapabilities: () => ({ zoom: { min: 1, max: 3, step: .1 } }),
      getSettings: () => ({ deviceId: "webcam", zoom: actualZoom }),
      applyConstraints: vi.fn().mockImplementation(async (constraints: MediaTrackConstraints) => {
        if ("zoom" in constraints) actualZoom = Number(constraints.zoom);
      }),
    };
    media.getUserMedia.mockResolvedValue({ getTracks: () => [track], getVideoTracks: () => [track] });
    vi.spyOn(HTMLVideoElement.prototype, "videoWidth", "get").mockReturnValue(1600);
    vi.spyOn(HTMLVideoElement.prototype, "videoHeight", "get").mockReturnValue(900);
    render(<GuidedDocumentScanner memberId="synthetic" open onClose={vi.fn()} onConfirm={vi.fn()} />);
    const slider = await screen.findByRole("slider", { name: "Zoom da câmera" });
    fireEvent.change(slider, { target: { value: "2" } });
    await waitFor(() => expect(track.applyConstraints).toHaveBeenCalledTimes(2));
    expect(slider).toHaveValue("2");
    expect(screen.queryByText(/não aceitou o zoom/i)).not.toBeInTheDocument();
  });

  it("rotates and uses manually adjusted corners before confirming", async () => {
    const prepare = vi.spyOn(bodyCompositionService, "prepareImage").mockRejectedValueOnce(new Error("not detected"))
      .mockResolvedValueOnce({ blob: corrected, metadata });
    const onConfirm = vi.fn();
    const { container } = render(<GuidedDocumentScanner memberId="synthetic" open onClose={vi.fn()} onConfirm={onConfirm} />);
    await screen.findByText("Tentar novamente");
    upload(container);
    await screen.findByText(/nao encontrou os quatro cantos/i);
    fireEvent.click(screen.getByRole("button", { name: "Girar direita" }));
    fireEvent.click(screen.getByRole("button", { name: "Ajustar quatro cantos" }));
    fireEvent.click(screen.getByRole("button", { name: "Aplicar correcao" }));
    await waitFor(() => expect(prepare).toHaveBeenCalledTimes(2));
    expect(prepare.mock.calls[1][2]).toHaveLength(4);
    fireEvent.click(await screen.findByRole("button", { name: "Confirmar foto corrigida" }));
    await waitFor(() => expect(onConfirm).toHaveBeenCalledOnce());
    expect(onConfirm.mock.calls[0][1].rotation).toBe(90);
    expect(onConfirm.mock.calls[0][1].correction_confirmed).toBe(true);
  });

  it("warns when the actual paper has too few pixels for reliable reading", async () => {
    vi.spyOn(bodyCompositionService, "prepareImage").mockResolvedValue({
      blob: corrected,
      metadata: { ...metadata, quality_metrics: { receipt_short_side_raw: 248 } },
    });
    const { container } = render(<GuidedDocumentScanner memberId="synthetic" open onClose={vi.fn()} onConfirm={vi.fn()} />);
    await screen.findByText("Tentar novamente");
    upload(container);
    expect(await screen.findByText(/papel ficou pequeno na foto/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Confirmar foto corrigida" })).toBeEnabled();
  });

  it("allows a careful read of a small blurred receipt and forwards its quality evidence", async () => {
    vi.spyOn(bodyCompositionService, "prepareImage").mockResolvedValue({
      blob: corrected,
      metadata: { ...metadata, quality_codes: ["document_blurred"], quality_metrics: { receipt_short_side_raw: 248 } },
    });
    const onConfirm = vi.fn();
    const { container } = render(<GuidedDocumentScanner memberId="synthetic" open onClose={vi.fn()} onConfirm={onConfirm} />);
    await screen.findByText("Tentar novamente");
    upload(container);
    expect(await screen.findByText(/resolução original do papel é baixa/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Confirmar foto corrigida" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Girar direita" }));
    expect(screen.getByRole("button", { name: "Confirmar foto corrigida" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Usar esta foto" }));
    fireEvent.click(screen.getByRole("button", { name: "Confirmar foto corrigida" }));
    await waitFor(() => expect(onConfirm).toHaveBeenCalledOnce());
    expect(onConfirm.mock.calls[0][1].quality_codes).toContain("document_blurred");
    expect(onConfirm.mock.calls[0][1].regional_quality.receipt_short_side_raw).toBe(248);
  });

  it("keeps low-resolution evidence when the original image is chosen", async () => {
    vi.spyOn(bodyCompositionService, "prepareImage").mockResolvedValue({
      blob: corrected,
      metadata: { ...metadata, quality_codes: ["document_blurred"], quality_metrics: { receipt_short_side_raw: 248 } },
    });
    const onConfirm = vi.fn();
    const { container } = render(<GuidedDocumentScanner memberId="synthetic" open onClose={vi.fn()} onConfirm={onConfirm} />);
    await screen.findByText("Tentar novamente");
    upload(container);
    await screen.findByText(/resolução original do papel é baixa/i);
    fireEvent.click(screen.getByRole("button", { name: "Original" }));
    fireEvent.click(screen.getByRole("button", { name: "Usar esta foto" }));
    fireEvent.click(screen.getByRole("button", { name: "Confirmar foto original" }));
    await waitFor(() => expect(onConfirm).toHaveBeenCalledOnce());
    expect(onConfirm.mock.calls[0][1].correction_confirmed).toBe(false);
    expect(onConfirm.mock.calls[0][1].quality_codes).toContain("document_blurred");
    expect(onConfirm.mock.calls[0][1].regional_quality.receipt_short_side_raw).toBe(248);
  });

  it("resumes live analysis when the captured image is rejected", async () => {
    const loop = { stop: vi.fn(), resetStability: vi.fn(), setPaused: vi.fn() };
    vi.spyOn(analysisLoop, "startAnalysisLoop").mockReturnValue(loop);
    vi.stubGlobal("Worker", vi.fn());
    const track = { stop: vi.fn(), getSettings: () => ({ deviceId: "rear" }) };
    media.getUserMedia.mockResolvedValue({ getTracks: () => [track], getVideoTracks: () => [track] });
    vi.spyOn(HTMLVideoElement.prototype, "videoWidth", "get").mockReturnValue(1600);
    vi.spyOn(HTMLVideoElement.prototype, "videoHeight", "get").mockReturnValue(2400);
    const oversized = new Blob(["synthetic"], { type: "image/jpeg" });
    Object.defineProperty(oversized, "size", { value: 33 * 1024 * 1024 });
    vi.spyOn(HTMLCanvasElement.prototype, "toBlob").mockImplementation(callback => callback(oversized));
    try {
      render(<GuidedDocumentScanner memberId="synthetic" open onClose={vi.fn()} onConfirm={vi.fn()} />);
      await waitFor(() => expect(screen.getByRole("button", { name: "Fotografar agora" })).toBeEnabled());
      loop.setPaused.mockClear();
      fireEvent.click(screen.getByRole("button", { name: "Fotografar agora" }));
      await waitFor(() => expect(loop.setPaused).toHaveBeenLastCalledWith(false));
      expect(loop.setPaused).toHaveBeenCalledWith(true);
      expect(screen.queryByRole("button", { name: "Original" })).not.toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Fotografar agora" })).toBeEnabled();
    } finally { vi.unstubAllGlobals(); }
  });
  it("shows retry and disables capture when photographing fails", async () => {
    const stop = vi.fn();
    const track = { stop, getSettings: () => ({ deviceId: "rear" }) };
    media.getUserMedia.mockResolvedValue({ getTracks: () => [track], getVideoTracks: () => [track] });
    vi.spyOn(HTMLVideoElement.prototype, "videoWidth", "get").mockReturnValue(1600);
    vi.spyOn(HTMLVideoElement.prototype, "videoHeight", "get").mockReturnValue(2400);
    vi.spyOn(HTMLCanvasElement.prototype, "toBlob").mockImplementation(callback => callback(null));
    render(<GuidedDocumentScanner memberId="synthetic" open onClose={vi.fn()} onConfirm={vi.fn()} />);
    await waitFor(() => expect(screen.getByRole("button", { name: "Fotografar agora" })).toBeEnabled());
    fireEvent.click(screen.getByRole("button", { name: "Fotografar agora" }));
    expect(await screen.findByRole("button", { name: "Tentar novamente" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Camera indisponivel" })).toBeDisabled();
    expect(stop).toHaveBeenCalledOnce();
    fireEvent.click(screen.getByRole("button", { name: "Tentar novamente" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Fotografar agora" })).toBeEnabled());
  });
  it("allows confirming all three segments after restarting the camera", async () => {
    vi.spyOn(bodyCompositionService, "prepareImage").mockResolvedValue({ blob: corrected, metadata });
    const onConfirm = vi.fn();
    const { container } = render(<GuidedDocumentScanner memberId="synthetic" open onClose={vi.fn()} onConfirm={onConfirm} />);
    await screen.findByText("Tentar novamente");
    fireEvent.click(screen.getByRole("button", { name: "Fotografar em partes" }));
    for (let index = 0; index < 3; index++) {
      await screen.findByText("Tentar novamente");
      upload(container);
      const name = index < 2 ? "Confirmar e continuar" : "Confirmar foto corrigida";
      await waitFor(() => expect(screen.getByRole("button", { name })).toBeEnabled());
      fireEvent.click(screen.getByRole("button", { name }));
      await waitFor(() => expect(screen.queryByRole("button", { name: "Original" })).not.toBeInTheDocument());
    }
    fireEvent.click(await screen.findByRole("button", { name: "Usar as tres fotos" }));
    expect(onConfirm).toHaveBeenCalledOnce();
    expect(onConfirm.mock.calls[0][2]).toHaveLength(2);
  }, 10_000);

  it("ignores a delayed camera enumeration after closing", async () => {
    let finish!: (devices: MediaDeviceInfo[]) => void;
    const enumerate = vi.spyOn(navigator.mediaDevices, "enumerateDevices").mockReturnValue(new Promise((resolve) => { finish = resolve; }));
    const stop = vi.fn();
    const track = { stop, getSettings: () => ({ deviceId: "front" }) };
    media.getUserMedia.mockResolvedValue({ getTracks: () => [track], getVideoTracks: () => [track] });
    render(<GuidedDocumentScanner memberId="synthetic" open onClose={vi.fn()} onConfirm={vi.fn()} />);
    await waitFor(() => expect(enumerate).toHaveBeenCalledOnce());
    fireEvent.click(screen.getByLabelText("Fechar camera"));
    await act(async () => finish([
      { kind: "videoinput", deviceId: "front", label: "Front" },
      { kind: "videoinput", deviceId: "rear", label: "Rear main" },
    ] as MediaDeviceInfo[]));
    expect(media.getUserMedia).toHaveBeenCalledOnce();
    expect(stop).toHaveBeenCalledOnce();
  });

  it.each(["Original", "Corrigida"])("confirms exactly the %s version and its provenance", async (version) => {
    vi.spyOn(bodyCompositionService, "prepareImage").mockResolvedValue({ blob: corrected, metadata });
    const onConfirm = vi.fn();
    const { container } = render(<GuidedDocumentScanner memberId="synthetic" open onClose={vi.fn()} onConfirm={onConfirm} />);
    await screen.findByText("Tentar novamente");
    upload(container);
    await waitFor(() => expect(screen.getByRole("button", { name: "Confirmar foto corrigida" })).toBeEnabled());
    fireEvent.click(screen.getByRole("button", { name: version }));
    fireEvent.click(screen.getByRole("button", { name: `Confirmar foto ${version === "Original" ? "original" : "corrigida"}` }));
    await waitFor(() => expect(onConfirm).toHaveBeenCalledOnce());
    expect(drawnSources).toContain(version === "Original" ? "blob:original" : "blob:corrected");
    expect(onConfirm.mock.calls[0][1].correction_confirmed).toBe(version === "Corrigida");
  });

  it("blocks confirmation during preparation and discards results after retake", async () => {
    let finish!: (value: { blob: Blob; metadata: typeof metadata }) => void;
    const prepare = vi.spyOn(bodyCompositionService, "prepareImage").mockReturnValue(new Promise((resolve) => { finish = resolve; }));
    const { container } = render(<GuidedDocumentScanner memberId="synthetic" open onClose={vi.fn()} onConfirm={vi.fn()} />);
    await screen.findByText("Tentar novamente");
    upload(container);
    expect(screen.getByRole("button", { name: "Preparando..." })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Refazer" }));
    expect(prepare.mock.calls[0][3]?.aborted).toBe(true);
    await act(async () => finish({ blob: corrected, metadata }));
    expect(screen.queryByRole("button", { name: "Confirmar foto corrigida" })).not.toBeInTheDocument();
  });

  it("does not reopen the camera on devicechange while reviewing", async () => {
    vi.spyOn(bodyCompositionService, "prepareImage").mockResolvedValue({ blob: corrected, metadata });
    const { container } = render(<GuidedDocumentScanner memberId="synthetic" open onClose={vi.fn()} onConfirm={vi.fn()} />);
    await screen.findByText("Tentar novamente");
    upload(container);
    await screen.findByRole("button", { name: "Confirmar foto corrigida" });
    const count = media.getUserMedia.mock.calls.length;
    act(() => media.dispatchEvent(new Event("devicechange")));
    expect(media.getUserMedia).toHaveBeenCalledTimes(count);
  });
});
