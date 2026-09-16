import { describe, expect, it, vi } from "vitest";

import {
  CameraAttemptController,
  requestMediaStreamWithTimeout,
} from "../components/assessments/scanner/streamLifecycle";

function stream() {
  const stop = vi.fn();
  return {
    value: { getTracks: () => [{ stop }] } as unknown as MediaStream,
    stop,
  };
}

describe("CameraAttemptController", () => {
  it("stops a stream that resolves after its attempt was invalidated", () => {
    const controller = new CameraAttemptController();
    const attempt = controller.begin();
    const late = stream();

    controller.invalidate();

    expect(controller.accept(attempt, late.value)).toBe(false);
    expect(late.stop).toHaveBeenCalledOnce();
    expect(controller.active).toBeNull();
  });

  it("keeps only one active stream and stops it on invalidate", () => {
    const controller = new CameraAttemptController();
    const first = stream();
    const second = stream();
    expect(controller.accept(controller.begin(), first.value)).toBe(true);
    expect(controller.accept(controller.begin(), second.value)).toBe(true);
    expect(first.stop).toHaveBeenCalledOnce();

    controller.invalidate();

    expect(second.stop).toHaveBeenCalledOnce();
    expect(controller.active).toBeNull();
  });
});

describe("requestMediaStreamWithTimeout", () => {
  it("rejects a stalled permission request and stops a stream that resolves later", async () => {
    vi.useFakeTimers();
    const stop = vi.fn();
    let resolveStream!: (stream: MediaStream) => void;
    const pending = new Promise<MediaStream>((resolve) => { resolveStream = resolve; });

    const result = requestMediaStreamWithTimeout(() => pending, 8_000);
    const rejection = expect(result).rejects.toThrow("camera_request_timeout");
    await vi.advanceTimersByTimeAsync(8_000);
    await rejection;

    resolveStream({ getTracks: () => [{ stop }] } as unknown as MediaStream);
    await Promise.resolve();
    expect(stop).toHaveBeenCalledOnce();
    vi.useRealTimers();
  });
});
