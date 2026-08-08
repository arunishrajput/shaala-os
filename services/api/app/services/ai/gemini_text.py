"""Shared Gemini REST call for the AI layer's two text-only features (Weekly
Briefing narrative, Ask Shaala intent parsing) -- PROMPT.md §6.6. Same REST
`generateContent` endpoint and request shape as services/vision/gemini.py,
minus the inline_data image part -- kept as a separate module rather than
merged into the vision provider because these calls send text only and have
no doc-type/bbox contract to share.
"""

from __future__ import annotations

import json

import httpx

from app.config import settings

GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
TIMEOUT_SECONDS = 20.0


class GeminiTextError(Exception):
    """Raised on any failure -- missing key, network, bad JSON, quota. Callers
    are expected to catch this and fall back to a deterministic path, per the
    same demo-safety rule as the vision provider: never an error screen on
    the live URL for a missing/exhausted API key."""


def call_gemini_json(prompt: str, *, temperature: float = 0.2) -> dict:
    if not settings.gemini_api_key or not settings.gemini_model_id:
        raise GeminiTextError("GEMINI_API_KEY or GEMINI_MODEL_ID not configured.")

    url = GEMINI_ENDPOINT.format(model=settings.gemini_model_id)
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "response_mime_type": "application/json",
            "temperature": temperature,
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
        return json.loads(text)
    except (httpx.HTTPError, KeyError, IndexError, json.JSONDecodeError) as e:
        raise GeminiTextError(f"Gemini call failed: {e}") from e
