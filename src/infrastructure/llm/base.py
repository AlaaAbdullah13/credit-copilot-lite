from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class LLMProvider(ABC):
    """Abstract contract for LLM-based providers used by the pipeline."""

    @abstractmethod
    def complete(self, prompt: str, **kwargs: Any) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def embed(self, text: str, **kwargs: Any) -> list[float]:
        raise NotImplementedError


class LLMAdapter(LLMProvider):
    """Backward-compatible alias for older imports."""

    def complete(self, prompt: str, **kwargs: Any) -> dict[str, Any]:
        raise NotImplementedError

    def embed(self, text: str, **kwargs: Any) -> list[float]:
        raise NotImplementedError

    def generate(self, prompt: str, **kwargs: Any) -> dict[str, Any]:
        return self.complete(prompt, **kwargs)


__all__ = ["LLMAdapter", "LLMProvider"]
