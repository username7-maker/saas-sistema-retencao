import { describe, expect, it } from "vitest";

import { advanceAutoCaptureGate, analyzeDocumentFrame } from "../components/assessments/scanner/frameAnalysis";

function receiptFrame({ blankBottom = false, offsetX = 0 }: { blankBottom?: boolean; offsetX?: number } = {}) {
  const width = 240;
  const height = 320;
  const data = new Uint8ClampedArray(width * height * 4);
  for (let index = 0; index < data.length; index += 4) {
    data[index] = 22; data[index + 1] = 22; data[index + 2] = 22; data[index + 3] = 255;
  }
  for (let y = 15; y < 305; y += 1) {
    for (let x = 52 + offsetX; x < 188 + offsetX; x += 1) {
      const line = !blankBottom || y < 215 ? y % 12 < 3 : false;
      const value = line && x > 65 + offsetX && x < 175 + offsetX ? 35 : 238;
      const index = (y * width + x) * 4;
      data[index] = value; data[index + 1] = value; data[index + 2] = value;
    }
  }
  return { data, width, height, colorSpace: "srgb" } as ImageData;
}

describe("live scanner frame analysis", () => {
  it("finds a centered vertical receipt and measures all three sharpness regions", () => {
    const result = analyzeDocumentFrame(receiptFrame());
    expect(result.corners).not.toBeNull();
    expect(result.confidence).toBeGreaterThan(0.7);
    expect(result.metrics.sharpnessTop).toBeGreaterThan(5);
    expect(result.metrics.sharpnessMiddle).toBeGreaterThan(5);
    expect(result.metrics.sharpnessBottom).toBeGreaterThan(5);
    expect(result.ready).toBe(true);
  });

  it("does not become ready when the bottom region is blurred", () => {
    const result = analyzeDocumentFrame(receiptFrame({ blankBottom: true }));
    expect(result.qualityCodes).toContain("bottom_blurred");
    expect(result.ready).toBe(false);
    expect(result.instruction).toBe("Mantenha firme");
  });

  it("detects motion between frames and asks the operator to hold still", () => {
    const first = analyzeDocumentFrame(receiptFrame({ offsetX: -20 }));
    const moved = analyzeDocumentFrame(receiptFrame({ offsetX: 20 }), first.signature);
    expect(moved.qualityCodes).toContain("camera_moving");
    expect(moved.ready).toBe(false);
    expect(moved.instruction).toBe("Mantenha firme");
  });
});

describe("automatic capture stability gate", () => {
  it("waits 1.5 seconds, shows a three second countdown and only then captures", () => {
    expect(advanceAutoCaptureGate(true, 0, null)).toEqual({ validSince: 0, countdown: null, shouldCapture: false });
    expect(advanceAutoCaptureGate(true, 1_500, 0).countdown).toBe(3);
    expect(advanceAutoCaptureGate(true, 3_500, 0).countdown).toBe(1);
    expect(advanceAutoCaptureGate(true, 4_500, 0).shouldCapture).toBe(true);
  });

  it("cancels immediately when any condition degrades", () => {
    expect(advanceAutoCaptureGate(false, 3_000, 0)).toEqual({ validSince: null, countdown: null, shouldCapture: false });
  });
});
