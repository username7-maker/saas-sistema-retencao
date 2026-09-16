import { describe, expect, it } from "vitest";

import { containedImageRect, pointToImageCoordinates, validDocumentCorners } from "../components/assessments/scanner/geometry";

describe("scanner geometry", () => {
  it("accepts ordered convex corners and rejects crossed or invalid corners", () => {
    const corners = [{ x: 0, y: 0 }, { x: 1, y: 0 }, { x: 1, y: 1 }, { x: 0, y: 1 }];
    expect(validDocumentCorners(corners)).toBe(true);
    expect(validDocumentCorners([corners[0], corners[2], corners[1], corners[3]])).toBe(false);
    expect(validDocumentCorners([{ x: NaN, y: 0 }, ...corners.slice(1)])).toBe(false);
    expect(validDocumentCorners(corners.map((p) => ({ x: p.x * .01, y: p.y * .01 })))).toBe(false);
  });
  it.each([90, 180, 270, -90])("maps rotated corners back to original image at %s degrees", (rotation) => {
    const rect = containedImageRect(400, 600, 1600, 2400, rotation);
    const angle = rotation * Math.PI / 180;
    for (const point of [{ x: 0, y: 0 }, { x: 1, y: 0 }, { x: 1, y: 1 }, { x: 0, y: 1 }]) {
      const dx = (point.x - .5) * rect.width;
      const dy = (point.y - .5) * rect.height;
      const x = rect.left + rect.width / 2 + dx * Math.cos(angle) - dy * Math.sin(angle);
      const y = rect.top + rect.height / 2 + dx * Math.sin(angle) + dy * Math.cos(angle);
      const mapped = pointToImageCoordinates(x, y, rect, rotation);
      expect(mapped.x).toBeCloseTo(point.x);
      expect(mapped.y).toBeCloseTo(point.y);
      expect(x).toBeGreaterThanOrEqual(-.001);
      expect(x).toBeLessThanOrEqual(400.001);
      expect(y).toBeGreaterThanOrEqual(-.001);
      expect(y).toBeLessThanOrEqual(600.001);
    }
  });
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
