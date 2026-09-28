from __future__ import annotations

import json
from typing import Any
from urllib import error, request

from .base import LLMProvider


class GeminiLLMAdapter(LLMProvider):
    def __init__(self, api_key: str | None = None):
        self.api_key = (api_key or "").strip()
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is required to use the Gemini adapter.")
        self.tokens_consumed = 0
        self.token_usage: dict[str, int] = {}

    def _request_json(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        data = json.dumps(payload).encode("utf-8")
        req = request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Gemini API request failed: {body}") from exc

    def complete(self, prompt: str, **kwargs: Any) -> dict[str, Any]:
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.0},
        }
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={self.api_key}"
        response = self._request_json(url, payload)

        try:
            content = response["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError):
            content = json.dumps(response)

        parsed: Any = None
        if isinstance(content, str):
            try:
                parsed = json.loads(content)
            except json.JSONDecodeError:
                parsed = None

        usage = _gemini_usage(response)
        self.token_usage = usage
        self.tokens_consumed += usage["total_tokens"]
        return {"content": content, "json": parsed, "usage": usage}

    def embed(self, text: str, **kwargs: Any) -> list[float]:
        payload = {
            "model": "models/text-embedding-004",
            "content": {"parts": [{"text": text}]},
        }
        url = f"https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent?key={self.api_key}"
        response = self._request_json(url, payload)
        try:
            return response["embedding"]["values"]
        except (KeyError, TypeError, IndexError):
            raise RuntimeError("Gemini embedding response was missing vector data.")


GeminiAdapter = GeminiLLMAdapter


def _gemini_usage(response: dict[str, Any]) -> dict[str, int]:
    metadata = response.get("usageMetadata") or {}
    return {
        "prompt_tokens": int(metadata.get("promptTokenCount", 0)),
        "completion_tokens": int(metadata.get("candidatesTokenCount", 0)),
        "total_tokens": int(metadata.get("totalTokenCount", 0)),
    }


__all__ = ["GeminiAdapter", "GeminiLLMAdapter"]
