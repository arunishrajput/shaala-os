"""Deskew + contrast normalization (PROMPT.md §6.1), opencv-headless only —
never the GUI build (PROMPT.md §3). Runs before every extraction call,
fixture or Gemini, since a crooked or washed-out photo hurts both equally.
"""

from __future__ import annotations

import cv2
import numpy as np


class PreprocessError(Exception):
    pass


def _deskew(img: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.bitwise_not(gray)
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]

    coords = np.column_stack(np.where(thresh > 0))
    if coords.shape[0] == 0:
        return img

    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle

    # Skip near-zero (nothing to fix) and implausibly large (noise, not skew).
    if abs(angle) < 0.1 or abs(angle) > 45:
        return img

    h, w = img.shape[:2]
    center = (w // 2, h // 2)
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    return cv2.warpAffine(
        img, matrix, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
    )


def _enhance_contrast(img: np.ndarray) -> np.ndarray:
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l_channel = clahe.apply(l_channel)
    merged = cv2.merge((l_channel, a_channel, b_channel))
    return cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)


def preprocess_image(image_bytes: bytes) -> bytes:
    """Returns re-encoded JPEG bytes: deskewed, contrast-enhanced."""
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise PreprocessError("Could not decode image — unsupported or corrupt file.")

    img = _deskew(img)
    img = _enhance_contrast(img)

    ok, encoded = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 90])
    if not ok:
        raise PreprocessError("Could not re-encode preprocessed image.")
    return encoded.tobytes()
