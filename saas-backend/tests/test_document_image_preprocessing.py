import cv2
import numpy as np

from app.services.document_image_preprocessing import (
    MAX_OUTPUT_BYTES,
    build_thermal_recovery_image,
    preprocess_receipt_image,
)


def _encode(image: np.ndarray) -> bytes:
    ok, encoded = cv2.imencode(".jpg", image, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
    assert ok
    return encoded.tobytes()


def test_preprocess_receipt_rectifies_bright_thermal_paper_without_persisting_it():
    image = np.full((1600, 1000, 3), 28, dtype=np.uint8)
    receipt = np.array([[250, 30], [780, 75], [700, 1570], [190, 1530]], dtype=np.int32)
    cv2.fillConvexPoly(image, receipt, (225, 225, 225))
    for y in range(150, 1450, 65):
        cv2.line(image, (310, y), (650, y + 10), (55, 55, 55), 3)

    result = preprocess_receipt_image(_encode(image), enabled=True)

    assert result is not None
    assert result.applied is True
    assert result.method.startswith("receipt_perspective")
    assert result.confidence >= 0.45
    assert min(result.output_width, result.output_height) >= 1000
    assert max(result.output_width, result.output_height) <= 4000
    assert len(result.image_bytes) <= MAX_OUTPUT_BYTES
    assert result.recovery_image_bytes is None


def test_preprocess_receipt_builds_high_contrast_recovery_for_weak_print():
    image = np.full((1200, 600, 3), 218, dtype=np.uint8)
    for y in range(90, 1110, 55):
        cv2.putText(image, f"Weight {65 + y % 7}.1", (70, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (174, 174, 174), 1)

    result = preprocess_receipt_image(_encode(image), enabled=True)

    assert result is not None
    recovery_bytes = build_thermal_recovery_image(result.image_bytes)
    assert recovery_bytes is not None
    recovered = cv2.imdecode(np.frombuffer(recovery_bytes, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
    assert recovered is not None
    assert recovered.shape[:2] == (result.output_height, result.output_width)
    assert float(np.std(recovered)) > 10


def test_preprocess_receipt_falls_back_safely_for_undecodable_content():
    assert preprocess_receipt_image(b"not-an-image", enabled=True) is None


def test_white_thermal_paper_is_not_mislabeled_as_glare_when_text_has_contrast():
    image = np.full((1200, 600, 3), 252, dtype=np.uint8)
    for y in range(80, 1140, 50):
        cv2.putText(image, "Weight 65.1", (55, y), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (45, 45, 45), 2)

    result = preprocess_receipt_image(_encode(image), enabled=True)

    assert result is not None
    assert "document_glare" not in result.quality_codes
