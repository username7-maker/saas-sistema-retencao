import type { FrameCorners, FramePoint } from "./frameAnalysis";

const cross = (a: FramePoint, b: FramePoint, c: FramePoint) =>
  (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x);
export function polygonArea(points: FrameCorners): number {
  return Math.abs(points.reduce((sum, p, i) => {
    const q = points[(i + 1) % 4];
    return sum + p.x * q.y - q.x * p.y;
  }, 0)) / 2;
}
export function sideAspect(points: FrameCorners): number {
  const sides = points.map((p, i) => Math.hypot(p.x - points[(i + 1) % 4].x, p.y - points[(i + 1) % 4].y));
  return (sides[1] + sides[3]) / Math.max(1, sides[0] + sides[2]);
}
export function validQuadrilateral(points: FrameCorners, width: number, height: number): boolean {
  const turns = points.map((p, i) => cross(p, points[(i + 1) % 4], points[(i + 2) % 4]));
  const sides = points.map((p, i) => Math.hypot(p.x - points[(i + 1) % 4].x, p.y - points[(i + 1) % 4].y));
  return turns.every(value => value > 0) && Math.min(...sides) >= 12
    && polygonArea(points) >= width * height * .08
    && sides[0] / sides[2] > .4 && sides[0] / sides[2] < 2.5
    && sides[1] / sides[3] > .4 && sides[1] / sides[3] < 2.5;
}

function approximateHull(points: FramePoint[]): FrameCorners | null {
  points.sort((a, b) => a.x - b.x || a.y - b.y);
  const lower: FramePoint[] = []; const upper: FramePoint[] = [];
  for (const point of points) {
    while (lower.length > 1 && cross(lower[lower.length - 2], lower[lower.length - 1], point) <= 0) lower.pop();
    lower.push(point);
  }
  for (let i = points.length - 1; i >= 0; i--) {
    const point = points[i];
    while (upper.length > 1 && cross(upper[upper.length - 2], upper[upper.length - 1], point) <= 0) upper.pop();
    upper.push(point);
  }
  const hull = lower.slice(0, -1).concat(upper.slice(0, -1));
  while (hull.length > 4) {
    let least = Infinity; let remove = 0;
    for (let i = 0; i < hull.length; i++) {
      const area = Math.abs(cross(hull[(i + hull.length - 1) % hull.length], hull[i], hull[(i + 1) % hull.length]));
      if (area < least) { least = area; remove = i; }
    }
    hull.splice(remove, 1);
  }
  if (hull.length !== 4) return null;
  let first = 0;
  hull.forEach((p, i) => { if (p.x + p.y < hull[first].x + hull[first].y) first = i; });
  return [...hull.slice(first), ...hull.slice(0, first)] as FrameCorners;
}

// Connected gradient contours are bounded by the already-downsampled worker frame.
// Requiring continuous support on every side avoids mistaking separate text rows for paper.
export function edgeDocument(values: Float32Array, width: number, height: number): FrameCorners | null {
  const edges = new Uint8Array(values.length);
  for (let y = 1; y < height - 1; y++) for (let x = 1; x < width - 1; x++) {
    const i = y * width + x;
    if (Math.hypot(values[i + 1] - values[i - 1], values[i + width] - values[i - width]) >= 7) edges[i] = 1;
  }
  const visited = new Uint8Array(values.length); const queue = new Int32Array(values.length);
  let best: FrameCorners | null = null; let bestScore = 0;
  for (let start = 0; start < values.length; start++) {
    if (!edges[start] || visited[start]) continue;
    let head = 0; let tail = 1; queue[0] = start; visited[start] = 1;
    const points: FramePoint[] = [];
    while (head < tail) {
      const i = queue[head++]; const x = i % width; const y = Math.floor(i / width);
      points.push({ x, y });
      for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) {
        const xx = x + dx; const yy = y + dy; const j = yy * width + xx;
        if (xx < 1 || xx >= width - 1 || yy < 1 || yy >= height - 1 || visited[j] || !edges[j]) continue;
        visited[j] = 1; queue[tail++] = j;
      }
    }
    if (points.length < (width + height) * .35) continue;
    const corners = approximateHull(points);
    if (!corners || !validQuadrilateral(corners, width, height) || sideAspect(corners) < 1.35 || sideAspect(corners) > 8.5) continue;
    const support = corners.map((p, side) => {
      const q = corners[(side + 1) % 4]; let hits = 0;
      for (let step = 1; step < 40; step++) {
        const x = Math.round(p.x + (q.x - p.x) * step / 40);
        const y = Math.round(p.y + (q.y - p.y) * step / 40);
        let hit = false;
        for (let dy = -2; dy <= 2; dy++) for (let dx = -2; dx <= 2; dx++) {
          if (x + dx >= 0 && x + dx < width && y + dy >= 0 && y + dy < height && edges[(y + dy) * width + x + dx]) hit = true;
        }
        if (hit) hits++;
      }
      return hits / 39;
    });
    if (Math.min(...support) < .8) continue;
    const score = polygonArea(corners) * Math.min(...support);
    if (score > bestScore) { best = corners; bestScore = score; }
  }
  return best;
}

export type RegionEvidence = { sharpness: number; edgeRatio: number; content: boolean };
export function documentRegions(values: Float32Array, width: number, height: number, corners: FrameCorners): RegionEvidence[] {
  const documentWidth = Math.min(Math.hypot(corners[1].x - corners[0].x, corners[1].y - corners[0].y), Math.hypot(corners[2].x - corners[3].x, corners[2].y - corners[3].y));
  const documentHeight = documentWidth * sideAspect(corners);
  const columns = Math.max(1, Math.floor(documentWidth * .8 / 12));
  const rows = Math.max(1, Math.floor(documentHeight * .25 / 12));
  return [0, 1, 2].map(region => {
    let total = 0; let coarseTotal = 0; let count = 0;
    for (let row = 0; row < rows; row++) for (let column = 0; column < columns; column++) {
      let min = 255; let max = 0; let laplacian = 0; let coarse = 0; let pixels = 0;
      for (let yy = 0; yy < 12; yy++) for (let xx = 0; xx < 12; xx++) {
        const u = .1 + (column + (xx + .5) / 12) / columns * .8;
        const v = region / 3 + .04 + (row + (yy + .5) / 12) / rows * .25;
        const x = Math.round((1 - v) * ((1 - u) * corners[0].x + u * corners[1].x) + v * ((1 - u) * corners[3].x + u * corners[2].x));
        const y = Math.round((1 - v) * ((1 - u) * corners[0].y + u * corners[1].y) + v * ((1 - u) * corners[3].y + u * corners[2].y));
        if (x < 3 || x >= width - 3 || y < 3 || y >= height - 3) continue;
        // Keep the entire derivative stencil inside the polygon, including on
        // narrow or perspective-distorted receipts.
        if (corners.some((p, side) => {
          const q = corners[(side + 1) % 4];
          return cross(p, q, { x, y }) / Math.hypot(q.x - p.x, q.y - p.y) < 3;
        })) continue;
        const i = y * width + x; const value = values[i];
        min = Math.min(min, value); max = Math.max(max, value);
        laplacian += Math.abs(values[i - 1] + values[i + 1] + values[i - width] + values[i + width] - 4 * value);
        coarse += Math.abs(values[i + 3] - values[i - 3]) + Math.abs(values[i + 3 * width] - values[i - 3 * width]);
        pixels++;
      }
      // Local contrast preserves weak, blurred printed content as evidence while
      // uniform margins and blank receipt tails do not vote against focus.
      if (max - min >= 8 && coarse > 0) { total += laplacian; coarseTotal += coarse; count += pixels; }
    }
    return { sharpness: total / Math.max(1, count), edgeRatio: total / Math.max(1, coarseTotal), content: count > 0 };
  });
}
