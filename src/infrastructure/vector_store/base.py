from abc import ABC, abstractmethod
from typing import List, Dict, Any


class VectorStoreAdapter(ABC):
    @abstractmethod
    def add_documents(self, docs: List[Dict[str, Any]]):
        raise NotImplementedError()

    @abstractmethod
    def query(self, text: str, k: int = 5) -> List[Dict[str, Any]]:
        raise NotImplementedError()
