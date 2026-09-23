from src.infrastructure.ingestion.chunker import chunk_by_clause
from src.infrastructure.ingestion.parser import parse_markdown
from src.infrastructure.ingestion.pipeline import ingest_documents, query_policy
from src.infrastructure.vector_store.chroma_adapter import ChromaAdapter


def test_parse_and_chunk_sample():
    sections = parse_markdown("data/policy/product-sheet-personal-loan.md")
    chunks = chunk_by_clause(sections)
    assert isinstance(chunks, list)
    assert chunks
    assert chunks[0]["metadata"]["source_file"] == "data/policy/product-sheet-personal-loan.md"


def test_ingestion_and_query_return_citations():
    policy_files = [
        "data/policy/product-sheet-personal-loan.md",
        "data/policy/circular-2025-02.md",
        "data/policy/pricing-table.csv",
    ]
    store = ChromaAdapter()

    result = ingest_documents(policy_files, store=store, policy_edition="2025")
    assert result["chunks_ingested"] > 0
    assert not result["failed"]

    answer = query_policy(
        "What is the maximum debt burden ratio for unsecured consumer lending?",
        store=store,
        policy_edition="2025",
        threshold=0.01,
        k=3,
    )

    assert answer["reason"] == "ok"
    assert answer["citations"]
    assert "45%" in answer["answer"] or "45" in answer["answer"]
    assert answer["citations"][0]["policy_edition"] == "2025"


def test_query_returns_no_chunk_above_threshold_when_score_is_low():
    store = ChromaAdapter()
    ingest_documents(
        ["data/policy/circular-2025-02.md"],
        store=store,
        policy_edition="2025",
    )

    answer = query_policy(
        "a completely unrelated policy concept that should not match any corpus text",
        store=store,
        policy_edition="2025",
        threshold=0.95,
        k=3,
    )

    assert answer["reason"] == "no_chunk_above_threshold"
    assert answer["citations"] == []
    assert answer["answer"] == "The documents do not contain enough information."
