import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { startAnalysisLoop, type AnalysisWorker } from "../components/assessments/scanner/analysisLoop";
import type { FrameAnalysis } from "../components/assessments/scanner/frameAnalysis";
import type { AnalysisRequest, AnalysisResponse } from "../components/assessments/scanner/analysisProtocol";

class FakeWorker {
  onmessage: ((event: MessageEvent<AnalysisResponse>) => void) | null = null;
  onerror: (() => void) | null = null;
  requests: AnalysisRequest[] = [];
  terminated = false;
  postMessage(request: AnalysisRequest) { this.requests.push(request); }
  terminate() { this.terminated = true; }
  reply(ready = true, request = this.requests[this.requests.length - 1]) {
    this.onmessage?.({ data: { sessionId: request.sessionId, requestId: request.requestId,
      result: { ready, instruction: "Foto pronta" } as FrameAnalysis } } as MessageEvent<AnalysisResponse>);
  }
}

function setup() {
  const workers: FakeWorker[] = [];
  const onResult = vi.fn(); const onReset = vi.fn(); const onUnavailable = vi.fn();
  const onCountdown = vi.fn(); const onCapture = vi.fn();
  let active = true; let auto = true;
  const loop = startAnalysisLoop({
    createWorker: () => { const worker = new FakeWorker(); workers.push(worker); return worker as AnalysisWorker; },
    sample: () => ({ data: new Uint8ClampedArray(4), width: 1, height: 1 }) as ImageData,
    isActive: () => active, autoEnabled: () => auto,
    onResult, onReset, onUnavailable, onCountdown, onCapture,
  });
  return { loop, workers, onResult, onReset, onUnavailable, onCountdown, onCapture,
    setActive: (value: boolean) => { active = value; }, setAuto: (value: boolean) => { auto = value; } };
}

beforeEach(() => vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout", "performance"] }));
afterEach(() => { vi.clearAllTimers(); vi.useRealTimers(); });

describe("scanner analysis scheduling", () => {
  it("starts fresh after a rejected automatic photo is explicitly resumed", () => {
    const run = setup();
    for (let i = 0; i < 40 && !run.onCapture.mock.calls.length; i++) {
      vi.advanceTimersToNextTimer(); vi.advanceTimersByTime(200); run.workers[0].reply();
    }
    expect(run.onCapture).toHaveBeenCalledOnce();
    run.loop.setPaused(true);
    run.loop.setPaused(false);
    vi.advanceTimersByTime(170);
    run.workers[1].reply();
    expect(run.onCountdown).toHaveBeenLastCalledWith(null);
    for (let i = 0; i < 40 && run.onCapture.mock.calls.length < 2; i++) {
      vi.advanceTimersToNextTimer(); vi.advanceTimersByTime(200); run.workers[1].reply();
    }
    expect(run.onCapture).toHaveBeenCalledTimes(2);
    run.loop.stop();
  });
  it.each([200, 450])("preserves stability across %s ms processing and captures only once", (latency) => {
    const run = setup();
    for (let i = 0; i < 40 && !run.onCapture.mock.calls.length; i++) {
      vi.advanceTimersToNextTimer();
      const worker = run.workers[0];
      const count = worker.requests.length;
      vi.advanceTimersByTime(latency);
      expect(worker.requests).toHaveLength(count);
      worker.reply();
    }
    expect(run.onCountdown).toHaveBeenCalledWith(3);
    expect(run.onCapture).toHaveBeenCalledOnce();
    vi.advanceTimersByTime(5_000);
    expect(run.onCapture).toHaveBeenCalledOnce();
    run.loop.stop();
  });

  it("rejects stale results and requires a new stable interval", () => {
    const run = setup();
    vi.advanceTimersByTime(170);
    vi.advanceTimersByTime(501);
    run.workers[0].reply();
    expect(run.onResult).not.toHaveBeenCalled();
    expect(run.onCapture).not.toHaveBeenCalled();
    expect(run.onCountdown).toHaveBeenLastCalledWith(null);
    run.loop.stop();
  });

  it("restarts a stalled worker once, clears output and falls back after the second timeout", () => {
    const run = setup();
    vi.advanceTimersByTime(170 + 2_000);
    expect(run.workers[0].terminated).toBe(true);
    expect(run.onReset).toHaveBeenCalled();
    expect(run.workers).toHaveLength(2);
    const oldResult = run.workers[0].requests[0];
    run.workers[0].reply(true, oldResult);
    expect(run.onResult).not.toHaveBeenCalled();
    vi.advanceTimersByTime(170 + 2_000);
    expect(run.onUnavailable).toHaveBeenCalledOnce();
    vi.advanceTimersByTime(10_000);
    expect(run.workers).toHaveLength(2);
    expect(run.workers[1].terminated).toBe(true);
    run.loop.stop();
  });

  it("recovers from errors and accepts only matching request and session IDs", () => {
    const run = setup();
    vi.advanceTimersByTime(170);
    run.workers[0].onerror?.();
    vi.advanceTimersByTime(170);
    const worker = run.workers[1]; const request = worker.requests[0];
    worker.reply(true, { ...request, sessionId: request.sessionId - 1 });
    worker.reply(true, { ...request, requestId: request.requestId + 1 });
    expect(run.onResult).not.toHaveBeenCalled();
    worker.reply();
    expect(run.onResult).toHaveBeenCalledOnce();
    run.loop.stop();
  });

  it("pauses immediately, discards in-flight output and resumes with new stability", () => {
    const run = setup();
    vi.advanceTimersByTime(170);
    run.loop.setPaused(true);
    run.workers[0].reply();
    vi.advanceTimersByTime(8_000);
    expect(run.onResult).not.toHaveBeenCalled();
    expect(run.onUnavailable).not.toHaveBeenCalled();
    run.loop.setPaused(false);
    vi.advanceTimersByTime(170);
    run.workers[1].reply();
    expect(run.onCapture).not.toHaveBeenCalled();
    expect(run.onCountdown).toHaveBeenLastCalledWith(null);
    run.loop.stop();
    vi.advanceTimersByTime(5_000);
    expect(run.workers[1].terminated).toBe(true);
    expect(vi.getTimerCount()).toBe(0);
  });

  it("does not deliver a result or capture after entering review or capture", () => {
    const run = setup(); vi.advanceTimersByTime(170);
    run.setActive(false); run.workers[0].reply();
    expect(run.onResult).not.toHaveBeenCalled();
    expect(run.onCapture).not.toHaveBeenCalled();
    run.loop.stop();
  });

  it("adapts the start interval without concurrent requests", () => {
    const run = setup(); vi.advanceTimersByTime(170);
    vi.advanceTimersByTime(400); run.workers[0].reply();
    vi.advanceTimersByTime(99); expect(run.workers[0].requests).toHaveLength(1);
    vi.advanceTimersByTime(1); expect(run.workers[0].requests).toHaveLength(2);
    run.loop.stop();
  });

  it("restarts the whole stability interval after movement", () => {
    const run = setup();
    const respond = (ready = true) => {
      vi.advanceTimersToNextTimer(); vi.advanceTimersByTime(200); run.workers[0].reply(ready);
    };
    for (let i = 0; i < 15; i++) respond();
    expect(run.onCountdown).toHaveBeenCalledWith(3);
    respond(false);
    expect(run.onCountdown).toHaveBeenLastCalledWith(null);
    for (let i = 0; i < 10; i++) respond();
    expect(run.onCapture).not.toHaveBeenCalled();
    for (let i = 0; i < 10 && !run.onCapture.mock.calls.length; i++) respond();
    expect(run.onCapture).toHaveBeenCalledOnce();
    run.loop.stop();
  });

  it("keeps automatic capture disabled without stopping live guidance", () => {
    const run = setup(); run.setAuto(false);
    for (let i = 0; i < 35; i++) {
      vi.advanceTimersToNextTimer(); vi.advanceTimersByTime(200); run.workers[0].reply();
    }
    expect(run.onResult).toHaveBeenCalledTimes(35);
    expect(run.onCapture).not.toHaveBeenCalled();
    run.loop.stop();
  });

  it("handles an explicit worker failure and keeps the retry budget across pauses", () => {
    const run = setup(); vi.advanceTimersByTime(170);
    const request = run.workers[0].requests[0];
    run.workers[0].onmessage?.(new MessageEvent<AnalysisResponse>("message", {
      data: { sessionId: request.sessionId, requestId: request.requestId, error: "analysis_failed" },
    }));
    run.loop.setPaused(true); run.loop.setPaused(false);
    vi.advanceTimersByTime(170 + 2_000);
    expect(run.onUnavailable).toHaveBeenCalledOnce();
    expect(run.workers).toHaveLength(3);
    run.loop.stop();
  });
});
