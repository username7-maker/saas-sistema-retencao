import { advanceAutoCaptureGate, type FrameAnalysis } from "./frameAnalysis";
import type { AnalysisRequest, AnalysisResponse } from "./analysisProtocol";

export type AnalysisWorker = {
  onmessage: ((event: MessageEvent<AnalysisResponse>) => void) | null;
  onerror: ((event: ErrorEvent) => void) | null;
  postMessage: (message: AnalysisRequest, transfer: Transferable[]) => void;
  terminate: () => void;
};
type Options = {
  createWorker: () => AnalysisWorker;
  sample: () => ImageData | null;
  isActive: () => boolean;
  autoEnabled: () => boolean;
  onResult: (result: FrameAnalysis) => void;
  onReset: () => void;
  onUnavailable: () => void;
  onCountdown: (value: number | null) => void;
  onCapture: () => void;
};

let nextSession = 0;
const RESPONSE_TIMEOUT_MS = 2_000;
const MAX_RESULT_AGE_MS = 500;

/** Owns just the live-analysis lifecycle; camera capture and review stay in the component. */
export function startAnalysisLoop(options: Options) {
  let worker: AnalysisWorker | null = null;
  let sessionId = ++nextSession;
  let requestId = 0;
  let pending: { requestId: number; sentAt: number } | null = null;
  let timer: ReturnType<typeof setTimeout> | undefined;
  let watchdog: ReturnType<typeof setTimeout> | undefined;
  let stopped = false;
  let paused = false;
  let unavailable = false;
  let recovered = false;
  let captured = false;
  let validSince: number | null = null;
  let averageLatency: number | null = null;

  function reset() {
    validSince = null;
    options.onCountdown(null);
    options.onReset();
  }
  function terminate() {
    clearTimeout(timer);
    clearTimeout(watchdog);
    pending = null;
    worker?.terminate();
    worker = null;
    sessionId = ++nextSession;
  }
  function schedule(delay = 170) {
    if (!stopped && !paused && !unavailable && !captured) timer = setTimeout(sample, delay);
  }
  function fail() {
    if (stopped || paused || unavailable) return;
    terminate();
    reset();
    if (recovered) {
      unavailable = true;
      options.onUnavailable();
      return;
    }
    recovered = true;
    create();
  }
  function create() {
    try {
      const currentWorker = options.createWorker();
      worker = currentWorker;
      currentWorker.onerror = () => { if (worker === currentWorker) fail(); };
      currentWorker.onmessage = ({ data }) => {
        if (stopped || paused || unavailable || worker !== currentWorker || !pending
          || data.sessionId !== sessionId || data.requestId !== pending.requestId) return;
        clearTimeout(watchdog);
        const sentAt = pending.sentAt;
        pending = null;
        if (data.error || !data.result) { fail(); return; }
        const now = performance.now();
        const latency = now - sentAt;
        averageLatency = averageLatency == null ? latency : averageLatency * .75 + latency * .25;
        if (!options.isActive() || latency > MAX_RESULT_AGE_MS) {
          reset();
        } else {
          options.onResult(data.result);
          const gate = advanceAutoCaptureGate(options.autoEnabled() && data.result.ready, now, validSince);
          validSince = gate.validSince;
          options.onCountdown(gate.countdown);
          if (gate.shouldCapture) {
            captured = true;
            options.onCapture();
          }
        }
        const interval = Math.min(500, Math.max(170, averageLatency * 1.25));
        schedule(Math.max(0, interval - (performance.now() - sentAt)));
      };
      schedule();
    } catch { fail(); }
  }
  function sample() {
    if (stopped || paused || unavailable || captured || pending) return;
    if (!options.isActive()) { reset(); schedule(); return; }
    try {
      const image = options.sample();
      if (!image) { reset(); schedule(); return; }
      const id = ++requestId;
      pending = { requestId: id, sentAt: performance.now() };
      watchdog = setTimeout(fail, RESPONSE_TIMEOUT_MS);
      worker?.postMessage({ sessionId, requestId: id, image }, [image.data.buffer]);
    } catch { fail(); }
  }

  create();
  return {
    stop() { stopped = true; terminate(); },
    resetStability() { reset(); },
    setPaused(value: boolean) {
      if (stopped || unavailable || paused === value) return;
      paused = value;
      terminate();
      reset();
      if (!paused) { captured = false; create(); }
    },
  };
}
