export type ImageContentRect = { left: number; top: number; width: number; height: number };

export function containedImageRect(
  containerWidth: number,
  containerHeight: number,
  imageWidth: number,
  imageHeight: number,
): ImageContentRect {
  if (containerWidth <= 0 || containerHeight <= 0 || imageWidth <= 0 || imageHeight <= 0) {
    return { left: 0, top: 0, width: Math.max(0, containerWidth), height: Math.max(0, containerHeight) };
  }
  const scale = Math.min(containerWidth / imageWidth, containerHeight / imageHeight);
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
): { x: number; y: number } {
  return {
    x: Math.min(1, Math.max(0, (clientX - imageRect.left) / Math.max(1, imageRect.width))),
    y: Math.min(1, Math.max(0, (clientY - imageRect.top) / Math.max(1, imageRect.height))),
  };
}
