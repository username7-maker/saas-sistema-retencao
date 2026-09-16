export type ImageContentRect = { left: number; top: number; width: number; height: number };

export function validDocumentCorners(points: Array<{ x: number; y: number }>): boolean {
  if (points.length !== 4 || points.some((p) => !Number.isFinite(p.x) || !Number.isFinite(p.y) || p.x < 0 || p.x > 1 || p.y < 0 || p.y > 1)) return false;
  let area = 0;
  for (let i = 0; i < 4; i++) {
    const a = points[i], b = points[(i + 1) % 4], c = points[(i + 2) % 4];
    if ((b.x - a.x) * (c.y - b.y) - (b.y - a.y) * (c.x - b.x) <= .0001) return false;
    area += a.x * b.y - b.x * a.y;
  }
  return area / 2 > .01;
}

export function containedImageRect(
  containerWidth: number,
  containerHeight: number,
  imageWidth: number,
  imageHeight: number,
  rotation = 0,
): ImageContentRect {
  if (containerWidth <= 0 || containerHeight <= 0 || imageWidth <= 0 || imageHeight <= 0) {
    return { left: 0, top: 0, width: Math.max(0, containerWidth), height: Math.max(0, containerHeight) };
  }
  const sideways = Math.abs(rotation % 180) === 90;
  const scale = Math.min(containerWidth / (sideways ? imageHeight : imageWidth), containerHeight / (sideways ? imageWidth : imageHeight));
  const width = imageWidth * scale;
  const height = imageHeight * scale;
  return {
    left: (containerWidth - width) / 2,
    top: (containerHeight - height) / 2,
    width,
    height,
  };
}

export function pointToImageCoordinates(
  clientX: number,
  clientY: number,
  imageRect: ImageContentRect,
  rotation = 0,
): { x: number; y: number } {
  const radians = -rotation * Math.PI / 180;
  const dx = clientX - imageRect.left - imageRect.width / 2;
  const dy = clientY - imageRect.top - imageRect.height / 2;
  return {
    x: Math.min(1, Math.max(0, 0.5 + (dx * Math.cos(radians) - dy * Math.sin(radians)) / Math.max(1, imageRect.width))),
    y: Math.min(1, Math.max(0, 0.5 + (dx * Math.sin(radians) + dy * Math.cos(radians)) / Math.max(1, imageRect.height))),
  };
}
