"""Separate collection for customer packs; it is never queried as policy."""

from src.infrastructure.llm.base import LLMProvider
from src.infrastructure.vector_store.chroma_adapter import ChromaAdapter


class UntrustedApplicationStore(ChromaAdapter):
    store_kind = "untrusted_application"

    def __init__(
        self,
        embedding_provider: LLMProvider,
        persist_directory: str = "./data/chroma_db",
    ):
        super().__init__(
            persist_directory, "untrusted_applications", embedding_provider
        )
