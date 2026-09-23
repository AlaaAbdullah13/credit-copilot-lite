from abc import ABC, abstractmethod
from typing import Any


class VectorStoreAdapter(ABC):
    @abstractmethod
    def add_documents(self, docs: list[dict[str, Any]]):
        raise NotImplementedError()

    @abstractmethod
    def query(self, text: str, k: int = 5) -> list[dict[str, Any]]:
        raise NotImplementedError()
