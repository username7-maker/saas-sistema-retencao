from __future__ import annotations

from dataclasses import dataclass, field

import cv2
import numpy as np

MAX_DECODED_PIXELS = 48_000_000
MAX_OUTPUT_BYTES = 8 * 1024 * 1024
MIN_DOCUMENT_AREA_RATIO = 0.12


@dataclass(frozen=True)
class DocumentPreprocessingResult:
    image_bytes: bytes
    media_type: str
    applied: bool
    method: str
    confidence: float
    source_width: int
    source_height: int
    output_width: int
    output_height: int
    quality_codes: list[str] = field(default_factory=list)
    quality_metrics: dict[str, float] = field(default_factory=dict)


def _order_points(points: np.ndarray) -> np.ndarray:
    ordered = np.zeros((4, 2), dtype="float32")
    sums = points.sum(axis=1)
    differences = np.diff(points, axis=1).reshape(-1)
    ordered[0] = points[np.argmin(sums)]
    ordered[2] = points[np.argmax(sums)]
    ordered[1] = points[np.argmin(differences)]
    ordered[3] = points[np.argmax(differences)]
    return ordered


def _find_receipt(gray: np.ndarray) -> tuple[np.ndarray | None, float]:
    height, width = gray.shape[:2]
    frame_area = float(height * width)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 45, 140)
    edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8), iterations=2)
    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    best: np.ndarray | None = None
    best_score = 0.0
    for contour in sorted(contours, key=cv2.contourArea, reverse=True)[:20]:
        area = float(cv2.contourArea(contour))
        area_ratio = area / frame_area
        if area_ratio < MIN_DOCUMENT_AREA_RATIO:
            continue
        perimeter = cv2.arcLength(contour, True)
        polygon = cv2.approxPolyDP(contour, 0.025 * perimeter, True)
        if len(polygon) != 4 or not cv2.isContourConvex(polygon):
            continue
        points = _order_points(polygon.reshape(4, 2).astype("float32"))
        top = np.linalg.norm(points[1] - points[0])
        bottom = np.linalg.norm(points[2] - points[3])
        left = np.linalg.norm(points[3] - points[0])
        right = np.linalg.norm(points[2] - points[1])
        short_side = max(1.0, min((top + bottom) / 2, (left + right) / 2))
        long_side = max((top + bottom) / 2, (left + right) / 2)
        aspect_ratio = long_side / short_side
        if not 1.6 <= aspect_ratio <= 8.5:
            continue
        rectangularity = min(1.0, area / max(1.0, short_side * long_side))
        score = min(1.0, area_ratio / 0.55) * 0.55 + rectangularity * 0.3 + min(1.0, aspect_ratio / 3) * 0.15
        if score > best_score:
            best, best_score = points, score
    if best is not None:
        return best, round(best_score, 3)

    # Thermal paper often has faint or clipped borders, so edge detection alone
    # may not close a quadrilateral. Fall back to the largest bright, narrow
    # connected region and rectify its minimum-area rectangle.
    _, bright = cv2.threshold(
        cv2.GaussianBlur(gray, (9, 9), 0),
        0,
        255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU,
    )
    bright = cv2.morphologyEx(
        bright,
        cv2.MORPH_CLOSE,
        np.ones((25, 11), np.uint8),
        iterations=2,
    )
    bright_contours, _ = cv2.findContours(bright, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for contour in sorted(bright_contours, key=cv2.contourArea, reverse=True)[:10]:
        area = float(cv2.contourArea(contour))
        area_ratio = area / frame_area
        if area_ratio < MIN_DOCUMENT_AREA_RATIO:
            continue
        rectangle = cv2.minAreaRect(contour)
        rect_width, rect_height = rectangle[1]
        short_side = max(1.0, min(rect_width, rect_height))
        long_side = max(rect_width, rect_height)
        aspect_ratio = long_side / short_side
        rectangularity = area / max(1.0, rect_width * rect_height)
        if not 1.6 <= aspect_ratio <= 8.5 or rectangularity < 0.5:
            continue
        score = min(0.82, 0.42 + area_ratio * 0.45 + rectangularity * 0.2)
        return _order_points(cv2.boxPoints(rectangle).astype("float32")), round(score, 3)
    return None, 0.0


def _warp(image: np.ndarray, points: np.ndarray) -> np.ndarray:
    top_left, top_right, bottom_right, bottom_left = points
    width = int(max(np.linalg.norm(bottom_right - bottom_left), np.linalg.norm(top_right - top_left)))
    height = int(max(np.linalg.norm(top_right - bottom_right), np.linalg.norm(top_left - bottom_left)))
    destination = np.array([[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]], dtype="float32")
    matrix = cv2.getPerspectiveTransform(points, destination)
    return cv2.warpPerspective(image, matrix, (max(width, 1), max(height, 1)), borderValue=(255, 255, 255))


def _adaptive_resize(image: np.ndarray) -> np.ndarray:
    height, width = image.shape[:2]
    short_side, long_side = min(width, height), max(width, height)
    scale = 1.0
    if short_side < 1000:
        scale = 1000 / max(1, short_side)
    if long_side * scale > 4000:
        scale = 4000 / max(1, long_side)
    if abs(scale - 1.0) < 0.01:
        return image
    interpolation = cv2.INTER_CUBIC if scale > 1 else cv2.INTER_AREA
    return cv2.resize(image, (max(1, round(width * scale)), max(1, round(height * scale))), interpolation=interpolation)


def _quality(gray: np.ndarray) -> tuple[list[str], dict[str, float]]:
    regions = np.array_split(gray, 3, axis=0)
    sharpness = [float(cv2.Laplacian(region, cv2.CV_64F).var()) for region in regions if region.size]
    mean = float(np.mean(gray))
    contrast = float(np.std(gray))
    highlights = float(np.mean(gray >= 250))
    shadows = float(np.mean(gray <= 18))
    metrics = {
        "luminance_mean": round(mean, 2),
        "contrast_stddev": round(contrast, 2),
        "highlight_ratio": round(highlights, 4),
        "shadow_ratio": round(shadows, 4),
        "sharpness_top": round(sharpness[0], 2),
        "sharpness_middle": round(sharpness[1], 2),
        "sharpness_bottom": round(sharpness[2], 2),
    }
    codes: list[str] = []
    if min(sharpness) < 35:
        codes.append("document_blurred")
    if mean < 55 or shadows > 0.35:
        codes.append("document_dark")
    if highlights > 0.42:
        codes.append("document_glare")
    if contrast < 22:
        codes.append("document_low_contrast")
    return codes, metrics


def preprocess_receipt_image(image_bytes: bytes, *, enabled: bool) -> DocumentPreprocessingResult | None:
    """Prepare a thermal receipt in memory. Returns None when decoding is unavailable."""
    encoded = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
    if image is None:
        return None
    source_height, source_width = image.shape[:2]
    if source_height * source_width > MAX_DECODED_PIXELS:
        return None

    working = image
    method = "original"
    confidence = 0.0
    receipt_short_side_raw = float(min(source_width, source_height))
    document_area_ratio = 0.0
    if enabled:
        points, confidence = _find_receipt(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY))
        if points is not None and confidence >= 0.45:
            document_area_ratio = float(abs(cv2.contourArea(points))) / max(1.0, source_width * source_height)
            working = _warp(image, points)
            method = "receipt_perspective"
            receipt_short_side_raw = float(min(working.shape[1], working.shape[0]))

        working = _adaptive_resize(working)
        luminance = cv2.cvtColor(working, cv2.COLOR_BGR2LAB)
        lightness, channel_a, channel_b = cv2.split(luminance)
        background = cv2.GaussianBlur(lightness, (0, 0), sigmaX=31, sigmaY=31)
        normalized = cv2.divide(lightness, np.maximum(background, 1), scale=235)
        normalized = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(8, 8)).apply(normalized)
        clahe = cv2.createCLAHE(clipLimit=1.6, tileGridSize=(8, 8)).apply(lightness)

        normalized_image = cv2.cvtColor(cv2.merge((normalized, channel_a, channel_b)), cv2.COLOR_LAB2BGR)
        clahe_image = cv2.cvtColor(cv2.merge((clahe, channel_a, channel_b)), cv2.COLOR_LAB2BGR)
        normalized_codes, normalized_metrics = _quality(cv2.cvtColor(normalized_image, cv2.COLOR_BGR2GRAY))
        clahe_codes, clahe_metrics = _quality(cv2.cvtColor(clahe_image, cv2.COLOR_BGR2GRAY))
        normalized_score = (
            min(
                normalized_metrics["sharpness_top"],
                normalized_metrics["sharpness_middle"],
                normalized_metrics["sharpness_bottom"],
            )
            + normalized_metrics["contrast_stddev"] * 1.8
            - len(normalized_codes) * 20
        )
        clahe_score = (
            min(clahe_metrics["sharpness_top"], clahe_metrics["sharpness_middle"], clahe_metrics["sharpness_bottom"])
            + clahe_metrics["contrast_stddev"] * 1.8
            - len(clahe_codes) * 20
        )
        if normalized_score > clahe_score:
            working = normalized_image
            method = f"{method}+background_normalization+clahe"
        else:
            working = clahe_image
            method = f"{method}+clahe"

    output_height, output_width = working.shape[:2]
    quality_codes, quality_metrics = _quality(cv2.cvtColor(working, cv2.COLOR_BGR2GRAY))
    quality_metrics["receipt_short_side_raw"] = round(receipt_short_side_raw, 2)
    quality_metrics["document_area_ratio"] = round(min(1.0, document_area_ratio), 4)
    output = None
    for quality in (88, 82, 76, 70):
        ok, candidate = cv2.imencode(".jpg", working, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
        if not ok:
            return None
        output = candidate
        if candidate.nbytes <= MAX_OUTPUT_BYTES:
            break
    if output is None or output.nbytes > MAX_OUTPUT_BYTES:
        return None
    return DocumentPreprocessingResult(
        image_bytes=output.tobytes(),
        media_type="image/jpeg",
        applied=enabled,
        method=method,
        confidence=confidence,
        source_width=source_width,
        source_height=source_height,
        output_width=output_width,
        output_height=output_height,
        quality_codes=quality_codes,
        quality_metrics=quality_metrics,
    )
