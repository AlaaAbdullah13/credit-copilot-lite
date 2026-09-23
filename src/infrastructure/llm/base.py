from abc import ABC, abstractmethod
from typing import Any


class LLMAdapter(ABC):
    """Abstract base class for LLM adapters."""

    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> dict[str, Any]:
        raise NotImplementedError()
