export type FramePoint = { x: number; y: number };
export type FrameCorners = [FramePoint, FramePoint, FramePoint, FramePoint];
export type FrameSignature = { values: Uint8Array; centerX: number; centerY: number };

export type FrameAnalysis = {
  corners: FrameCorners | null;
  confidence: number;
  ready: boolean;
  instruction: "Aproxime" | "Afaste" | "Centralize" | "Melhore a iluminação" | "Evite reflexo" | "Mantenha firme" | "Foto pronta";
  qualityCodes: string[];
  metrics: {
    luminance: number;
    contrast: number;
    coverage: number;
    motion: number;
    sharpnessTop: number;
    sharpnessMiddle: number;
    sharpnessBottom: number;
  };
  signature: FrameSignature;
};

export function advanceAutoCaptureGate(
  ready: boolean,
  now: number,
  validSince: number | null,
): { validSince: number | null; countdown: number | null; shouldCapture: boolean } {
  if (!ready) return { validSince: null, countdown: null, shouldCapture: false };
  const startedAt = validSince ?? now;
  const stableFor = now - startedAt;
  if (stableFor < 1_500) return { validSince: startedAt, countdown: null, shouldCapture: false };
  const remaining = Math.max(0, 4_500 - stableFor);
  return {
    validSince: startedAt,
    countdown: remaining > 0 ? Math.max(1, Math.ceil(remaining / 1_000)) : null,
    shouldCapture: stableFor >= 4_500,
  };
}

function luminance(data: Uint8ClampedArray, pixel: number): number {
  const offset = pixel * 4;
  return data[offset] * 0.2126 + data[offset + 1] * 0.7152 + data[offset + 2] * 0.0722;
}

function sharpnessRegion(values: Float32Array, width: number, startY: number, endY: number, minX: number, maxX: number): number {
  let total = 0;
  let count = 0;
  for (let y = Math.max(1, startY + 3); y < Math.min(endY - 3, values.length / width - 1); y += 1) {
    for (let x = Math.max(1, minX + 3); x < Math.min(maxX - 3, width - 1); x += 1) {
      const index = y * width + x;
      total += Math.abs(values[index - 1] + values[index + 1] + values[index - width] + values[index + width] - 4 * values[index]);
      count += 1;
    }
  }
  return total / Math.max(1, count);
}

function buildSignature(values: Float32Array, width: number, height: number, centerX: number, centerY: number): FrameSignature {
  const samples = new Uint8Array(48);
  let index = 0;
  for (let row = 0; row < 6; row += 1) {
    for (let column = 0; column < 8; column += 1) {
      const x = Math.min(width - 1, Math.floor((column + 0.5) * width / 8));
      const y = Math.min(height - 1, Math.floor((row + 0.5) * height / 6));
      samples[index] = Math.round(values[y * width + x]);
      index += 1;
    }
  }
  return { values: samples, centerX, centerY };
}

function largestBrightComponent(values: Float32Array, width: number, height: number, threshold: number) {
  const visited = new Uint8Array(values.length);
  const stack = new Int32Array(values.length);
  let best = { count: 0, minX: width, maxX: -1, minY: height, maxY: -1 };
  for (let start = 0; start < values.length; start += 1) {
    if (visited[start] || values[start] < threshold) continue;
    let size = 0;
    let cursor = 0;
    stack[cursor] = start;
    cursor += 1;
    visited[start] = 1;
    let minX = width; let maxX = -1; let minY = height; let maxY = -1;
    while (cursor > 0) {
      cursor -= 1;
      const pixel = stack[cursor];
      const x = pixel % width;
      const y = Math.floor(pixel / width);
      size += 1;
      minX = Math.min(minX, x); maxX = Math.max(maxX, x);
      minY = Math.min(minY, y); maxY = Math.max(maxY, y);
      let neighbor = pixel - 1;
      if (x > 0 && !visited[neighbor] && values[neighbor] >= threshold) {
        visited[neighbor] = 1; stack[cursor] = neighbor; cursor += 1;
      }
      neighbor = pixel + 1;
      if (x < width - 1 && !visited[neighbor] && values[neighbor] >= threshold) {
        visited[neighbor] = 1; stack[cursor] = neighbor; cursor += 1;
      }
      neighbor = pixel - width;
      if (y > 0 && !visited[neighbor] && values[neighbor] >= threshold) {
        visited[neighbor] = 1; stack[cursor] = neighbor; cursor += 1;
      }
      neighbor = pixel + width;
      if (y < height - 1 && !visited[neighbor] && values[neighbor] >= threshold) {
        visited[neighbor] = 1; stack[cursor] = neighbor; cursor += 1;
      }
    }
    if (size > best.count) best = { count: size, minX, maxX, minY, maxY };
  }
  return best;
}

export function analyzeDocumentFrame(image: ImageData, previous?: FrameSignature | null): FrameAnalysis {
  const { width, height, data } = image;
  const values = new Float32Array(width * height);
  let sum = 0;
  let squareSum = 0;
  for (let pixel = 0; pixel < width * height; pixel += 1) {
    const value = luminance(data, pixel);
    values[pixel] = value;
    sum += value;
    squareSum += value * value;
  }
  const mean = sum / Math.max(1, values.length);
  const contrast = Math.sqrt(Math.max(0, squareSum / Math.max(1, values.length) - mean * mean));
  const threshold = Math.max(105, mean + Math.min(55, contrast * 0.45));
  const component = largestBrightComponent(values, width, height, threshold);
  const { minX, maxX, minY, maxY } = component;

  const found = component.count > width * height * 0.08 && maxX > minX && maxY > minY;
  const boxWidth = found ? maxX - minX + 1 : 0;
  const boxHeight = found ? maxY - minY + 1 : 0;
  const coverage = boxWidth * boxHeight / Math.max(1, width * height);
  const centerX = found ? (minX + maxX) / (2 * width) : 0.5;
  const centerY = found ? (minY + maxY) / (2 * height) : 0.5;
  const aspect = boxWidth > 0 ? boxHeight / boxWidth : 0;
  const regionHeight = Math.max(1, Math.floor(boxHeight / 3));
  const sharpnessTop = found ? sharpnessRegion(values, width, minY, minY + regionHeight, minX, maxX + 1) : 0;
  const sharpnessMiddle = found ? sharpnessRegion(values, width, minY + regionHeight, minY + regionHeight * 2, minX, maxX + 1) : 0;
  const sharpnessBottom = found ? sharpnessRegion(values, width, minY + regionHeight * 2, maxY + 1, minX, maxX + 1) : 0;
  const signature = buildSignature(values, width, height, centerX, centerY);
  let motion = 0;
  if (previous) {
    for (let index = 0; index < signature.values.length; index += 1) {
      motion += Math.abs(signature.values[index] - previous.values[index]);
    }
    motion = motion / signature.values.length
      + Math.hypot(centerX - previous.centerX, centerY - previous.centerY) * 180;
  }

  const codes: string[] = [];
  if (!found) codes.push("document_not_found");
  if (found && coverage < 0.24) codes.push("document_too_far");
  if (found && coverage > 0.92) codes.push("document_too_close");
  if (found && (minX < 3 || minY < 3 || maxX > width - 4 || maxY > height - 4)) codes.push("document_clipped");
  if (found && (Math.abs(centerX - 0.5) > 0.13 || Math.abs(centerY - 0.5) > 0.13)) codes.push("document_off_center");
  if (found && (aspect < 1.35 || aspect > 8.5)) codes.push("document_bad_aspect");
  if (mean < 45) codes.push("document_dark");
  if (mean > 235 && contrast < 20) codes.push("document_glare");
  if (sharpnessTop < 5) codes.push("top_blurred");
  if (sharpnessMiddle < 5) codes.push("middle_blurred");
  if (sharpnessBottom < 5) codes.push("bottom_blurred");
  if (previous && motion > 18) codes.push("camera_moving");

  let instruction: FrameAnalysis["instruction"] = "Foto pronta";
  if (codes.includes("camera_moving") || codes.some((code) => code.endsWith("_blurred"))) instruction = "Mantenha firme";
  else if (codes.includes("document_dark")) instruction = "Melhore a iluminação";
  else if (codes.includes("document_glare")) instruction = "Evite reflexo";
  else if (codes.includes("document_clipped") || codes.includes("document_too_close")) instruction = "Afaste";
  else if (codes.includes("document_off_center") || codes.includes("document_not_found") || codes.includes("document_bad_aspect")) instruction = "Centralize";
  else if (codes.includes("document_too_far")) instruction = "Aproxime";

  const corners: FrameCorners | null = found ? [
    { x: minX / width, y: minY / height },
    { x: (maxX + 1) / width, y: minY / height },
    { x: (maxX + 1) / width, y: (maxY + 1) / height },
    { x: minX / width, y: (maxY + 1) / height },
  ] : null;
  const confidence = found
    ? Math.max(0, Math.min(1, 0.42 + Math.min(0.3, coverage * 0.7) + Math.min(0.2, contrast / 250) - Math.abs(centerX - 0.5) * 0.2))
    : 0;
  return {
    corners,
    confidence,
    ready: codes.length === 0,
    instruction,
    qualityCodes: codes,
    metrics: {
      luminance: mean,
      contrast,
      coverage,
      motion,
      sharpnessTop,
      sharpnessMiddle,
      sharpnessBottom,
    },
    signature,
  };
}
