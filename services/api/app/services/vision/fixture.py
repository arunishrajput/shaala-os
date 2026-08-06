"""Replays cached extraction JSON keyed by the uploaded image's content hash —
no network call, works with the network disabled (the Phase 3 gate's literal
requirement). Primarily serves the 4 "Try a sample" images; any other upload
gets an honest "no fixture for this image" result instead of a crash or a
fabricated extraction.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from app.services.vision.base import ExtractionResult, VisionProvider, parse_extraction_json

FIXTURES_DIR = Path(__file__).resolve().parents[3] / "fixtures"
RESPONSES_DIR = FIXTURES_DIR / "responses"


def image_hash(image_bytes: bytes) -> str:
    return hashlib.sha256(image_bytes).hexdigest()[:16]


class FixtureProvider(VisionProvider):
    def extract(self, image_bytes: bytes, mime_type: str) -> ExtractionResult:
        key = image_hash(image_bytes)
        path = RESPONSES_DIR / f"{key}.json"
        if not path.exists():
            return ExtractionResult(
                doc_type="unknown",
                doc_type_confidence=0.0,
                fields=[],
                rows=[],
                warnings=[
                    "No cached fixture for this image. Use one of the 'Try a "
                    "sample' forms, or set VISION_PROVIDER=gemini for real "
                    "extraction."
                ],
            )
        payload = json.loads(path.read_text())
        return parse_extraction_json(payload)
