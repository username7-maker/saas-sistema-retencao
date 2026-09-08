import cv2
import numpy as np

from app.services.document_image_preprocessing import MAX_OUTPUT_BYTES, preprocess_receipt_image


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


def test_preprocess_receipt_falls_back_safely_for_undecodable_content():
    assert preprocess_receipt_image(b"not-an-image", enabled=True) is None
