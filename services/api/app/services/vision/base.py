"""VisionProvider interface (PROMPT.md §6.1). Two implementations —
`gemini.GeminiProvider` and `fixture.FixtureProvider` — behind the same
contract, selected by `VISION_PROVIDER`. `get_extraction()` is the single entry
point the upload pipeline calls: it always falls back to the fixture provider
on any Gemini error or quota exhaustion, per the demo-safety requirement in
PROMPT.md §6.1 ("never an error screen on the live URL").
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

DOC_TYPES = ("admission_form", "attendance_sheet", "marks_sheet", "leave_application")


@dataclass
class ExtractedFieldData:
    name: str
    value: str
    confidence: float
    bbox: list[float] | None = None


@dataclass
class ExtractionResult:
    doc_type: str
    doc_type_confidence: float
    fields: list[ExtractedFieldData] = field(default_factory=list)
    rows: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class VisionProviderError(Exception):
    """Raised by a provider on any failure — network, API error, bad JSON, quota."""


class VisionProvider(ABC):
    @abstractmethod
    def extract(self, image_bytes: bytes, mime_type: str) -> ExtractionResult:
        """Raises VisionProviderError on failure. Never returns a half-parsed result."""


def parse_extraction_json(payload: dict) -> ExtractionResult:
    """Shared parsing for both providers — Gemini's response text and a fixture
    JSON file have the same shape (the prompt's contract), so they parse the
    same way."""
    fields = [
        ExtractedFieldData(
            name=f["name"],
            value=f.get("value", ""),
            confidence=float(f.get("confidence", 0.0)),
            bbox=f.get("bbox"),
        )
        for f in payload.get("fields", [])
    ]
    return ExtractionResult(
        doc_type=payload.get("doc_type", "unknown"),
        doc_type_confidence=float(payload.get("doc_type_confidence", 0.0)),
        fields=fields,
        rows=payload.get("rows", []) or [],
        warnings=payload.get("warnings", []) or [],
    )


def get_provider(name: str) -> VisionProvider:
    if name == "gemini":
        from app.services.vision.gemini import GeminiProvider

        return GeminiProvider()
    from app.services.vision.fixture import FixtureProvider

    return FixtureProvider()


def get_extraction(
    image_bytes: bytes, mime_type: str, configured_provider: str
) -> ExtractionResult:
    provider = get_provider(configured_provider)
    try:
        return provider.extract(image_bytes, mime_type)
    except VisionProviderError as e:
        if configured_provider == "fixture":
            raise  # fixture failing means there's nothing left to fall back to
        logger.warning("Gemini extraction failed (%s) — falling back to fixture.", e)
        from app.services.vision.fixture import FixtureProvider

        return FixtureProvider().extract(image_bytes, mime_type)
