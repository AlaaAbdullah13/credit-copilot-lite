from abc import ABC, abstractmethod
from typing import Any, Dict


class LLMAdapter(ABC):
    """Abstract base class for LLM adapters."""

    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        raise NotImplementedError()
