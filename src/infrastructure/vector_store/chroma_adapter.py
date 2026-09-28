from __future__ import annotations

import hashlib
import logging
import re
from typing import Any

from .base import VectorStoreAdapter

logger = logging.getLogger(__name__)

try:  # pragma: no cover - optional dependency
    import chromadb  # type: ignore
except ImportError:  # pragma: no cover - fallback for local/offline use
    chromadb = None  # type: ignore


class ChromaAdapter(VectorStoreAdapter):
    store_kind = "generic"

    def __init__(
        self,
        persist_directory: str = "./data/chroma_db",
        collection_name: str = "policy_documents",
    ):
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self._memory_docs: list[dict[str, Any]] = []
        self._seen: set[tuple[str, str, str | None, str | None]] = set()
        self._client = None
        self.collection = None

        if chromadb is not None:
            try:
                self._client = chromadb.PersistentClient(path=self.persist_directory)
                self.collection = self._client.get_or_create_collection(
                    name=self.collection_name,
                    metadata={"hnsw:space": "cosine"},
                )
            except (AttributeError, TypeError, ValueError):
                logger.debug(
                    "Chroma unavailable; falling back to in-memory store.",
                    exc_info=True,
                )
                self._client = None
                self.collection = None

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
        return min(score, 1.0)

    def query(
        self,
        text: str,
        k: int = 5,
        *,
        policy_edition: str | None = None,
        threshold: float | None = None,
    ) -> list[dict[str, Any]]:
        if self.collection is not None:
            try:
                result = self.collection.query(
                    query_texts=[text],
                    n_results=min(max(k, 1), 10),
                    where={"policy_edition": policy_edition}
                    if policy_edition
                    else None,
                )
                if result and result.get("documents"):
                    hits = []
                    docs = result.get("documents", [[]])[0]
                    metadatas = result.get("metadatas", [[None]])[0]
                    ids = result.get("ids", [[]])[0]
                    distances = result.get("distances", [[]])[0]
                    for index, document in enumerate(docs):
                        distance = distances[index] if index < len(distances) else 1.0
                        score = round(1.0 - distance, 4)
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
            if policy_edition and metadata.get("policy_edition") not in {
                policy_edition,
                None,
            }:
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

    def __init__(self, persist_directory: str = "./data/chroma_db/trusted"):
        super().__init__(
            persist_directory=persist_directory,
            collection_name="trusted_policy_documents",
        )


class UntrustedApplicationStore(ChromaAdapter):
    store_kind = "untrusted_applications"

    def __init__(self, persist_directory: str = "./data/chroma_db/untrusted"):
        super().__init__(
            persist_directory=persist_directory,
            collection_name="untrusted_applications",
        )
