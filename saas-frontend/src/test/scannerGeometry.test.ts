import { describe, expect, it } from "vitest";

import { containedImageRect, pointToImageCoordinates } from "../components/assessments/scanner/geometry";

describe("scanner geometry", () => {
  it("maps pointer coordinates against the actual portrait image, not its landscape container", () => {
    const rect = containedImageRect(1600, 900, 900, 1600);
    expect(rect.width).toBeCloseTo(506.25);
    expect(rect.left).toBeCloseTo(546.875);

    expect(pointToImageCoordinates(rect.left, 0, rect)).toEqual({ x: 0, y: 0 });
    expect(pointToImageCoordinates(rect.left + rect.width / 2, 450, rect)).toEqual({ x: 0.5, y: 0.5 });
    expect(pointToImageCoordinates(0, 1000, rect)).toEqual({ x: 0, y: 1 });
  });

  it("maps a landscape image without phantom letterboxing", () => {
    const rect = containedImageRect(1200, 800, 1800, 1200);
    expect(rect).toEqual({ left: 0, top: 0, width: 1200, height: 800 });
  });
});
