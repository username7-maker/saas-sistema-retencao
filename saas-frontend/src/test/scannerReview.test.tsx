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
