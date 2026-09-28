from __future__ import annotations

import hashlib
import logging
import re
from typing import Any

from src.infrastructure.llm.base import LLMProvider

from .base import VectorStoreAdapter

logger = logging.getLogger(__name__)

try:  # pragma: no cover - optional dependency
    import chromadb  # type: ignore
    from chromadb.api.types import Documents, EmbeddingFunction, Embeddings
except ImportError:  # pragma: no cover - fallback for local/offline use
    chromadb = None  # type: ignore
    Documents = list[str]  # type: ignore[misc,assignment]
    Embeddings = list[list[float]]  # type: ignore[misc,assignment]
    EmbeddingFunction = object  # type: ignore[misc,assignment]


class _SchemaEmbeddingFunction(EmbeddingFunction[Documents]):
    """Deserialization-only embedding function required by Chroma's schema."""

    def __init__(self) -> None:
        pass

    def __call__(self, input: Documents) -> Embeddings:
        return [[0.0] for _ in input]

    @staticmethod
    def name() -> str:
        return "provider-embedding-function"

    def get_config(self) -> dict[str, str]:
        return {}

    @staticmethod
    def build_from_config(config: dict[str, str]) -> _SchemaEmbeddingFunction:
        return _SchemaEmbeddingFunction()

    def is_legacy(self) -> bool:
        return False


class ProviderEmbeddingFunction(EmbeddingFunction[Documents]):
    """Chroma embedding callback backed by the configured LLMProvider."""

    def __init__(self, provider: LLMProvider):
        self.provider = provider

    def __call__(self, input: Documents) -> Embeddings:
        return [self.provider.embed(text) for text in input]

    @staticmethod
    def name() -> str:
        return "provider-embedding-function"

    def get_config(self) -> dict[str, str]:
        return {"provider": type(self.provider).__name__}

    @staticmethod
    def build_from_config(config: dict[str, str]) -> _SchemaEmbeddingFunction:
        # Collection schema deserialization only requires a callable here.  The
        # live collection keeps the explicitly supplied instance above; this
        # placeholder is never used to embed data.
        return _SchemaEmbeddingFunction()

    def is_legacy(self) -> bool:
        """Provider callbacks are current Chroma embedding functions."""
        return False


class ChromaAdapter(VectorStoreAdapter):
    store_kind = "generic"

    def __init__(
        self,
        persist_directory: str = "./data/chroma_db",
        collection_name: str = "policy_documents",
        embedding_provider: LLMProvider | None = None,
    ):
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self._memory_docs: list[dict[str, Any]] = []
        self._seen: set[tuple[str, str, str | None, str | None]] = set()
        self._client = None
        self.collection = None
        self.backend_name = "chromadb"
        if embedding_provider is None:
            raise ValueError(
                "ChromaAdapter requires an explicit embedding_provider. "
                "Pass a configured LLM provider in production or FakeLLMAdapter "
                "for offline tests; Chroma's downloading default is disabled."
            )
        self.embedding_provider = embedding_provider

        if chromadb is not None:
            try:
                self._client = chromadb.PersistentClient(path=self.persist_directory)
                self.collection = self._client.get_or_create_collection(
                    name=self.collection_name,
                    metadata={"hnsw:space": "cosine"},
                    embedding_function=ProviderEmbeddingFunction(embedding_provider),
                )
            except (AttributeError, TypeError, ValueError):
                self.backend_name = "in-memory-warning"
                logger.warning(
                    "Chroma initialization failed; using non-persistent in-memory backend.",
                    exc_info=True,
                )
                self._client = None
                self.collection = None
        else:
            self.backend_name = "in-memory-warning"
            logger.warning(
                "chromadb is not installed; using non-persistent in-memory backend."
            )

    def contains(self, doc: dict[str, Any]) -> bool:
        return self._canonical_key(self._coerce_doc(doc)) in self._seen

    def _canonical_key(
        self, doc: dict[str, Any]
    ) -> tuple[str, str, str | None, str | None]:
        metadata = dict(doc.get("metadata") or {})
        text = str(doc.get("text") or "").strip()
        source = str(metadata.get("source_file") or "")
        clause = str(metadata.get("clause_id") or doc.get("id") or "")
        edition = str(metadata.get("policy_edition") or "") or None
        return (text, source, clause, edition)

    def _generate_id(self, doc: dict[str, Any]) -> str:
        metadata = doc.get("metadata") or {}
        source = str(metadata.get("source_file") or "")
        clause = str(metadata.get("clause_id") or doc.get("id") or "")
        text = str(doc.get("text") or "")
        raw = f"{source}:{clause}:{text}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]

    def _coerce_doc(self, doc: dict[str, Any]) -> dict[str, Any]:
        metadata = dict(doc.get("metadata") or {})
        # Chroma collection IDs must be globally unique. Clause IDs and PDF page
        # IDs repeat across policy editions (for example, both PDFs contain
        # ``page-2``), so derive the storage ID from source, clause, and text.
        generated_id = self._generate_id(doc)
        return {
            "id": generated_id,
            "text": str(doc.get("text") or "").strip(),
            "metadata": metadata,
        }

    def add_documents(self, docs: list[dict[str, Any]]) -> int:
        inserted = 0
        for doc in docs:
            normalized = self._coerce_doc(doc)
            if not normalized["text"]:
                continue
            key = self._canonical_key(normalized)
            if key in self._seen:
                continue
            self._seen.add(key)
            self._memory_docs.append(normalized)
            inserted += 1

            if self.collection is not None:
                try:
                    self.collection.upsert(
                        ids=[normalized["id"]],
                        documents=[normalized["text"]],
                        metadatas=[normalized["metadata"]],
                    )
                except (AttributeError, TypeError, ValueError):
                    logger.debug(
                        "Chroma upsert failed; remaining in memory store.",
                        exc_info=True,
                    )

        return inserted

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        return {token.lower() for token in re.findall(r"[a-zA-Z0-9]+", text)}

    @staticmethod
    def _score(query: str, candidate: str) -> float:
        query_tokens = ChromaAdapter._tokenize(query)
        if not query_tokens:
            return 0.0

        candidate_tokens = ChromaAdapter._tokenize(candidate)
        overlap = query_tokens & candidate_tokens
        if not overlap:
            return 0.0

        score = len(overlap) / max(1, len(query_tokens))
        if candidate_tokens:
            score += 0.1 * len(overlap) / max(1, len(candidate_tokens))
        # Keep exact multi-word policy labels above explanatory definitions.
        normalized_query = " ".join(query.lower().split())
        normalized_candidate = " ".join(candidate.lower().split())
        for phrase in (
            "minimum net monthly income",
            "maximum debt burden ratio",
            "approval authority",
        ):
            if phrase in normalized_query and phrase in normalized_candidate:
                score += 0.35
        return min(score, 1.0)

    @staticmethod
    def _distance_to_score(distance: float, space: str) -> float:
        """Map Chroma HNSW distances to a higher-is-better relevance score.

        cosine: Chroma returns ``1 - cosine_similarity``; score is cosine
        similarity.  l2 is squared Euclidean distance and ip is ``1 - dot``;
        their bounded similarity equivalents below are only used if a legacy
        collection explicitly declares either space.
        """
        if space == "cosine":
            return 1.0 - distance
        if space == "l2":
            return 1.0 / (1.0 + distance)
        if space == "ip":
            return 1.0 - distance
        raise ValueError(f"Unsupported Chroma hnsw:space: {space!r}")

    def query(
        self,
        text: str,
        k: int = 5,
        *,
        policy_edition: str | None = None,
        threshold: float | None = None,
    ) -> list[dict[str, Any]]:
        normalized_edition = (
            f"CP-{policy_edition}"
            if policy_edition and policy_edition.isdigit()
            else policy_edition
        )
        edition_values = {normalized_edition, policy_edition, None}
        if self.collection is not None:
            try:
                result = self.collection.query(
                    query_texts=[text],
                    n_results=min(max(k, 1), 10),
                    where={"policy_edition": normalized_edition}
                    if normalized_edition
                    else None,
                )
                if result and result.get("documents"):
                    hits = []
                    docs = result.get("documents", [[]])[0]
                    metadatas = result.get("metadatas", [[None]])[0]
                    ids = result.get("ids", [[]])[0]
                    distances = result.get("distances", [[]])[0]
                    space = str(
                        (self.collection.metadata or {}).get("hnsw:space", "l2")
                    )
                    for index, document in enumerate(docs):
                        distance = distances[index] if index < len(distances) else 1.0
                        score = round(self._distance_to_score(distance, space), 4)
                        logger.debug(
                            "Chroma hit id=%s space=%s raw_distance=%.6f score=%.6f",
                            ids[index] if index < len(ids) else f"hit-{index}",
                            space,
                            distance,
                            score,
                        )
                        if threshold is not None and score < threshold:
                            continue
                        metadata = metadatas[index] if index < len(metadatas) else {}
                        hits.append(
                            {
                                "id": ids[index]
                                if index < len(ids)
                                else f"hit-{index}",
                                "text": document,
                                "metadata": metadata,
                                "score": score,
                                "raw_distance": distance,
                                "distance_space": space,
                            }
                        )
                    return hits[:k]
            except (AttributeError, TypeError, ValueError):
                logger.debug(
                    "Chroma query failed; falling back to in-memory matching.",
                    exc_info=True,
                )

        ranked: list[dict[str, Any]] = []
        for doc in self._memory_docs:
            metadata = doc.get("metadata") or {}
            if (
                normalized_edition
                and metadata.get("policy_edition") not in edition_values
            ):
                continue
            score = self._score(text, doc["text"])
            if threshold is not None and score < threshold:
                continue
            ranked.append(
                {
                    "id": doc["id"],
                    "text": doc["text"],
                    "metadata": metadata,
                    "score": round(score, 4),
                }
            )

        ranked.sort(key=lambda item: item["score"], reverse=True)
        return ranked[:k]


class TrustedPolicyStore(ChromaAdapter):
    store_kind = "trusted_policy"

    def __init__(
        self,
        persist_directory: str = "./data/chroma_db/trusted",
        *,
        embedding_provider: LLMProvider,
    ):
        super().__init__(
            persist_directory=persist_directory,
            collection_name="trusted_policy_documents",
            embedding_provider=embedding_provider,
        )


class UntrustedApplicationStore(ChromaAdapter):
    store_kind = "untrusted_applications"

    def __init__(
        self,
        persist_directory: str = "./data/chroma_db/untrusted",
        *,
        embedding_provider: LLMProvider,
    ):
        super().__init__(
            persist_directory=persist_directory,
            collection_name="untrusted_applications",
            embedding_provider=embedding_provider,
        )
