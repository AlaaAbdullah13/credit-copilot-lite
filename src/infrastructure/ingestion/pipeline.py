from __future__ import annotations

from pathlib import Path
from typing import Any

from src.infrastructure.ingestion.chunker import chunk_by_clause
from src.infrastructure.ingestion.parser import parse_document
from src.infrastructure.vector_store.chroma_adapter import ChromaAdapter


def ingest_documents(
    file_paths: list[str | Path],
    *,
    store: ChromaAdapter | None = None,
    policy_edition: str | None = None,
) -> dict[str, Any]:
    vector_store = store or ChromaAdapter()
    successful: list[str] = []
    failed: list[dict[str, str]] = []
    all_chunks: list[dict[str, Any]] = []

    for file_path in file_paths:
        path_text = str(file_path)
        try:
            sections = parse_document(path_text)
            chunks = chunk_by_clause(
                sections,
                source_file=path_text,
                policy_edition=policy_edition,
            )
            if chunks:
                all_chunks.extend(chunks)
            successful.append(path_text)
        except (FileNotFoundError, OSError, TypeError, ValueError) as exc:
            failed.append({"file": path_text, "error": str(exc)})

    vector_store.add_documents(all_chunks)
    return {
        "successful": successful,
        "failed": failed,
        "chunks_ingested": len(all_chunks),
    }


def query_policy(
    question: str,
    *,
    store: ChromaAdapter | None = None,
    policy_edition: str | None = None,
    threshold: float = 0.0,
    k: int = 5,
) -> dict[str, Any]:
    vector_store = store or ChromaAdapter()
    matches = vector_store.query(
        question,
        k=k,
        policy_edition=policy_edition,
        threshold=threshold,
    )

    if not matches:
        return {
            "answer": "The documents do not contain enough information.",
            "citations": [],
            "reason": "no_chunk_above_threshold",
        }

    best = matches[0]
    return {
        "answer": best["text"],
        "citations": [
            {
                "chunk_id": best["id"],
                "source_file": best["metadata"].get("source_file"),
                "clause_id": best["metadata"].get("clause_id"),
                "page": best["metadata"].get("page"),
                "policy_edition": best["metadata"].get("policy_edition"),
            }
        ],
        "reason": "ok",
    }
