from __future__ import annotations

import json
from typing import Any
from urllib import error, request

from .base import LLMProvider


class GroqLLMAdapter(LLMProvider):
    """OpenAI-compatible Groq adapter using the Groq API key from the environment."""

    def __init__(self, api_key: str | None = None):
        self.api_key = (api_key or "").strip()
        if not self.api_key:
            raise ValueError("GROQ_API_KEY is required to use the Groq adapter.")

    def _request_json(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        data = json.dumps(payload).encode("utf-8")
        req = request.Request(
            url,
            data=data,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Groq API request failed: {body}") from exc

    def complete(self, prompt: str, **kwargs: Any) -> dict[str, Any]:
        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
        }
        response = self._request_json(
            "https://api.groq.com/openai/v1/chat/completions", payload
        )
        content = ""
        try:
            content = response["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            content = json.dumps(response)

        parsed: Any = None
        if isinstance(content, str):
            try:
                parsed = json.loads(content)
            except json.JSONDecodeError:
                parsed = None

        return {"content": content, "json": parsed}

    def embed(self, text: str, **kwargs: Any) -> list[float]:
        payload = {
            "input": text,
            "model": "text-embedding-3-small",
        }
        response = self._request_json(
            "https://api.groq.com/openai/v1/embeddings", payload
        )
        try:
            return response["data"][0]["embedding"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(
                "Groq embedding response was missing vector data."
            ) from exc


GroqAdapter = GroqLLMAdapter

__all__ = ["GroqAdapter", "GroqLLMAdapter"]
