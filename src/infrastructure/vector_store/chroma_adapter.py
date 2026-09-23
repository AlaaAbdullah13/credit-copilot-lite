from typing import Any

from .base import VectorStoreAdapter


class ChromaAdapter(VectorStoreAdapter):
    def __init__(self, persist_directory: str = "./data/chroma_db"):
        self.persist_directory = persist_directory

    def add_documents(self, docs: list[dict[str, Any]]):
        # Placeholder for Chroma ingestion
        return len(docs)

    def query(self, text: str, k: int = 5) -> list[dict[str, Any]]:
        # Placeholder: return empty list
        return []
