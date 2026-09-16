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
  it("asks for framing when no document exists instead of claiming blur", () => {
    const frame = receiptFrame();
    frame.data.fill(150);
    expect(analyzeDocumentFrame(frame).instruction).toBe("Centralize");
  });

  it("detects a local saturated patch even on a dark background", () => {
    const frame = receiptFrame();
    for (let y = 120; y < 160; y++) for (let x = 96; x < 128; x++) {
      frame.data.set([255, 255, 255, 255], (y * frame.width + x) * 4);
    }
    const result = analyzeDocumentFrame(frame);
    expect(result.qualityCodes).toContain("document_glare");
    expect(result.instruction).toBe("Evite reflexo");
    expect(result.ready).toBe(false);
  });

  it.each([0, 1, 2])("rejects actual blur in region %s with text still present", (region) => {
    const frame = receiptFrame();
    const source = new Uint8ClampedArray(frame.data);
    for (let y = 15 + region * 96; y < 15 + (region + 1) * 96; y++) {
      for (let x = 55; x < 185; x++) {
        let total = 0; let count = 0;
        for (let dy = -6; dy <= 6; dy++) for (let dx = -6; dx <= 6; dx++) {
          total += source[((y + dy) * frame.width + x + dx) * 4]; count++;
        }
        const value = total / count;
        frame.data.set([value, value, value, 255], (y * frame.width + x) * 4);
      }
    }
    const result = analyzeDocumentFrame(frame);
    expect(result.qualityCodes, JSON.stringify(result.metrics)).toContain(["top_blurred", "middle_blurred", "bottom_blurred"][region]);
    expect(result.ready).toBe(false);
  });

  it("tracks slanted paper corners instead of returning its bounding rectangle", () => {
    const frame = receiptFrame();
    const source = new Uint8ClampedArray(frame.data);
    for (let y = 0; y < frame.height; y++) {
      const shift = Math.round((y - 160) * .10);
      for (let x = 0; x < frame.width; x++) {
        const sourceX = x - shift;
        const value = sourceX >= 0 && sourceX < frame.width ? source[(y * frame.width + sourceX) * 4] : 22;
        frame.data.set([value, value, value, 255], (y * frame.width + x) * 4);
      }
    }
    const result = analyzeDocumentFrame(frame);
    expect(result.corners).not.toBeNull();
    expect(result.corners![3].x - result.corners![0].x).toBeGreaterThan(.08);
    expect(result.corners![0].y).toBeCloseTo(15 / 320, 2);
  });
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
