from __future__ import annotations

import json
import logging
import os
import time
from typing import Any
from urllib import error, request

from src.domain.exceptions import LLMProviderError

from .base import LLMProvider

logger = logging.getLogger(__name__)


class GeminiLLMAdapter(LLMProvider):
    """Gemini adapter with fixed-size retrieval embeddings and safe failures."""

    _BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
    _MAX_ATTEMPTS = 3

    def __init__(self, api_key: str | None = None):
        self.api_key = (api_key or "").strip()
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is required to use the Gemini adapter.")
        self.model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip()
        self.embedding_model = os.getenv(
            "GEMINI_EMBEDDING_MODEL", "gemini-embedding-001"
        ).strip()
        try:
            self.embedding_dimension = int(os.getenv("GEMINI_EMBEDDING_DIM", "768"))
        except ValueError as exc:
            raise ValueError(
                "GEMINI_EMBEDDING_DIM must be a positive integer."
            ) from exc
        if not self.model or not self.embedding_model or self.embedding_dimension <= 0:
            raise ValueError("Gemini model names and embedding dimension must be set.")
        self.tokens_consumed = 0
        self.token_usage: dict[str, int] = {}

    @staticmethod
    def _model_path(model: str) -> str:
        return model.removeprefix("models/")

    def _url(self, model: str, method: str) -> str:
        return f"{self._BASE_URL}/{self._model_path(model)}:{method}?key={self.api_key}"

    def _safe_message(self, status: int | None, body: str) -> str:
        safe_body = body.replace(self.api_key, "[REDACTED]")
        detail = " ".join(safe_body.split())[:500]
        prefix = (
            f"Gemini API request failed ({status})"
            if status
            else "Gemini API request failed"
        )
        return f"{prefix}: {detail}" if detail else prefix

    def _request_json(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        data = json.dumps(payload).encode("utf-8")
        for attempt in range(self._MAX_ATTEMPTS):
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
                if (exc.code == 429 or 500 <= exc.code < 600) and attempt < 2:
                    time.sleep(2**attempt)
                    continue
                message = self._safe_message(exc.code, body)
                if exc.code == 404 and "model" in body.lower():
                    message += (
                        ". Check GEMINI_MODEL and choose a model available to "
                        "this API key."
                    )
                    logger.warning("Gemini model configuration warning: %s", message)
                raise LLMProviderError(message) from exc
            except (error.URLError, TimeoutError, OSError) as exc:
                if attempt < 2:
                    time.sleep(2**attempt)
                    continue
                raise LLMProviderError(
                    "Gemini API request failed: network error."
                ) from exc
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                raise LLMProviderError(
                    "Gemini API returned an invalid response."
                ) from exc
        raise LLMProviderError("Gemini API request failed after retries.")

    def complete(self, prompt: str, **kwargs: Any) -> dict[str, Any]:
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.0},
        }
        response = self._request_json(self._url(self.model, "generateContent"), payload)

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
        return self.embed_many([text], **kwargs)[0]

    def embed_many(self, texts: list[str], **kwargs: Any) -> list[list[float]]:
        if not texts:
            return []
        task_type = kwargs.get("task_type", "RETRIEVAL_DOCUMENT")
        requests = [
            {
                "model": f"models/{self._model_path(self.embedding_model)}",
                "content": {"parts": [{"text": text}]},
                "taskType": task_type,
                "outputDimensionality": self.embedding_dimension,
            }
            for text in texts
        ]
        response = self._request_json(
            self._url(self.embedding_model, "batchEmbedContents"),
            {"requests": requests},
        )
        try:
            vectors = [item["values"] for item in response["embeddings"]]
        except (KeyError, TypeError, IndexError) as exc:
            raise LLMProviderError(
                "Gemini embedding response was missing vector data."
            ) from exc
        if len(vectors) != len(texts) or any(
            len(vector) != self.embedding_dimension for vector in vectors
        ):
            raise LLMProviderError(
                "Gemini returned embeddings with an unexpected dimension; "
                "check GEMINI_EMBEDDING_DIM."
            )
        return vectors


GeminiAdapter = GeminiLLMAdapter


def _gemini_usage(response: dict[str, Any]) -> dict[str, int]:
    metadata = response.get("usageMetadata") or {}
    return {
        "prompt_tokens": int(metadata.get("promptTokenCount", 0)),
        "completion_tokens": int(metadata.get("candidatesTokenCount", 0)),
        "total_tokens": int(metadata.get("totalTokenCount", 0)),
    }


__all__ = ["GeminiAdapter", "GeminiLLMAdapter"]
