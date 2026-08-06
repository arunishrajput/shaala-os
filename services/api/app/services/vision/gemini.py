"""Real Gemini calls. REST `generateContent`, not the SDK — httpx is already a
pinned dependency (PROMPT.md §3) and this is a single endpoint; no need for an
extra SDK dependency. Endpoint, request shape, and the `x-goog-api-key` header
verified against https://ai.google.dev/gemini-api/docs at Phase 3 kickoff —
see .env.example for the model ID and when it was last checked.
"""

from __future__ import annotations

import base64
import json

import httpx

from app.config import settings
from app.services.vision.base import (
    ExtractionResult,
    VisionProvider,
    VisionProviderError,
    parse_extraction_json,
)
from app.services.vision.prompts import EXTRACTION_PROMPT

GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
TIMEOUT_SECONDS = 30.0


class GeminiProvider(VisionProvider):
    def extract(self, image_bytes: bytes, mime_type: str) -> ExtractionResult:
        if not settings.gemini_api_key or not settings.gemini_model_id:
            raise VisionProviderError("GEMINI_API_KEY or GEMINI_MODEL_ID not configured.")

        url = GEMINI_ENDPOINT.format(model=settings.gemini_model_id)
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"text": EXTRACTION_PROMPT},
                        {
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": base64.b64encode(image_bytes).decode(),
                            }
                        },
                    ],
                }
            ],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.1,
            },
        }
        headers = {
            "x-goog-api-key": settings.gemini_api_key,
            "Content-Type": "application/json",
        }

        try:
            resp = httpx.post(url, json=payload, headers=headers, timeout=TIMEOUT_SECONDS)
            resp.raise_for_status()
            data = resp.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            parsed = json.loads(text)
        except (httpx.HTTPError, KeyError, IndexError, json.JSONDecodeError) as e:
            raise VisionProviderError(f"Gemini extraction failed: {e}") from e

        return parse_extraction_json(parsed)
