from src.infrastructure.ingestion.chunker import chunk_by_clause
from src.infrastructure.ingestion.parser import parse_document, parse_markdown
from src.infrastructure.ingestion.pipeline import ingest_documents, query_policy
from src.infrastructure.llm.fake_adapter import FakeLLMAdapter
from src.infrastructure.vector_store.chroma_adapter import ChromaAdapter


class CountingEmbeddingProvider(FakeLLMAdapter):
    """Offline provider used to ensure unchanged chunks are never re-embedded."""

    def __init__(self):
        super().__init__()
        self.embedding_calls = 0

    def embed(self, text, **kwargs):
        self.embedding_calls += 1
        return super().embed(text, **kwargs)


def test_parse_and_chunk_sample():
    sections = parse_markdown("data/policy/product-sheet-personal-loan.md")
    chunks = chunk_by_clause(sections)
    assert isinstance(chunks, list)
    assert chunks
    assert (
        chunks[0]["metadata"]["source_file"]
        == "data/policy/product-sheet-personal-loan.md"
    )


def test_ingestion_and_query_return_citations(tmp_path):
    policy_files = [
        "data/policy/product-sheet-personal-loan.md",
        "data/policy/circular-2025-02.md",
        "data/policy/pricing-table.csv",
    ]
    store = ChromaAdapter(
        persist_directory=str(tmp_path / "policy-store"),
        embedding_provider=FakeLLMAdapter(),
    )

    result = ingest_documents(policy_files, store=store, policy_edition="2025")
    assert result["chunks_ingested"] > 0
    assert not result["failed"]

    answer = query_policy(
        "What is the maximum debt burden ratio for unsecured consumer lending?",
        store=store,
        policy_edition="2025",
        threshold=0.25,
        k=3,
    )

    assert answer["reason"] == "ok"
    assert answer["citations"]
    assert "45%" in answer["answer"] or "45" in answer["answer"]
    assert answer["citations"][0]["policy_edition"] == "CP-2025"


def test_reingestion_skips_unchanged_policy_and_application_chunks(tmp_path):
    """A second offline ingestion must make no calls to the embedding provider."""
    from src.infrastructure.ingestion.application_packs import seed_application_packs
    from src.infrastructure.vector_store.untrusted_application_store import (
        UntrustedApplicationStore,
    )

    policy_provider = CountingEmbeddingProvider()
    policy_store = ChromaAdapter(
        persist_directory=str(tmp_path / "policy-store"),
        embedding_provider=policy_provider,
    )
    files = ["data/policy/circular-2025-02.md"]
    first_policy = ingest_documents(files, store=policy_store, policy_edition="2025")
    policy_calls_after_first = policy_provider.embedding_calls
    second_policy = ingest_documents(files, store=policy_store, policy_edition="2025")

    assert first_policy["chunks_inserted"] > 0
    assert second_policy["chunks_inserted"] == 0
    assert second_policy["chunks_skipped"] == first_policy["chunks_ingested"]
    assert policy_provider.embedding_calls == policy_calls_after_first

    application_provider = CountingEmbeddingProvider()
    application_store = UntrustedApplicationStore(
        application_provider, persist_directory=str(tmp_path / "application-store")
    )
    first_packs = seed_application_packs(application_store)
    application_calls_after_first = application_provider.embedding_calls
    second_packs = seed_application_packs(application_store)

    assert first_packs["chunks_inserted"] > 0
    assert second_packs["chunks_inserted"] == 0
    assert second_packs["chunks_skipped"] == first_packs["chunks_inserted"]
    assert application_provider.embedding_calls == application_calls_after_first


def test_query_returns_no_chunk_above_threshold_when_score_is_low(tmp_path):
    store = ChromaAdapter(
        persist_directory=str(tmp_path / "policy-store"),
        embedding_provider=FakeLLMAdapter(),
    )
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


def test_policy_pdfs_are_chunked_by_clause_with_required_metadata():
    sections = parse_document("data/policy/credit-policy-2025.pdf")
    clause_ids = {section["id"] for section in sections}

    assert {"CP-3.3", "CP-4.1", "CP-4.3"} <= clause_ids
    dbr = next(section for section in sections if section["id"] == "CP-4.1")
    assert dbr["page"] == 2


def test_real_corpus_answers_are_edition_scoped_and_cited(tmp_path):
    store = ChromaAdapter(
        persist_directory=str(tmp_path / "policy-store"),
        embedding_provider=FakeLLMAdapter(),
    )
    result = ingest_documents(
        [
            "data/policy/credit-policy-2024.pdf",
            "data/policy/credit-policy-2025.pdf",
            "data/policy/credit-procedures-manual.pdf",
        ],
        store=store,
    )
    assert not result["failed"]
    assert result["documents"]["data/policy/credit-policy-2025.pdf"]["inserted"]

    dbr_2025 = query_policy("maximum DBR", store=store, policy_edition="CP-2025")
    dbr_2024 = query_policy("maximum DBR", store=store, policy_edition="CP-2024")
    income_2025 = query_policy(
        "minimum net monthly income", store=store, policy_edition="CP-2025"
    )
    authority = query_policy("Credit Officer approval authority limit", store=store)
    crypto = query_policy("crypto-backed loans", store=store, threshold=0.60)

    assert "45%" in dbr_2025["answer"]
    assert dbr_2025["citations"][0]["clause_id"] == "CP-4.1"
    assert "50%" in dbr_2024["answer"]
    assert "10,000" in income_2025["answer"]
    assert authority["citations"][0]["clause_id"] == "PM-2"
    assert crypto["reason"] == "no_chunk_above_threshold"


def test_conflicting_circulars_cite_both_and_identify_supersession(tmp_path):
    store = ChromaAdapter(
        persist_directory=str(tmp_path / "policy-store"),
        embedding_provider=FakeLLMAdapter(),
    )
    ingest_documents(
        ["data/policy/circular-2024-07.md", "data/policy/circular-2025-02.md"],
        store=store,
    )
    answer = query_policy("maximum tenor", store=store, threshold=0.25, k=5)

    assert len(answer["citations"]) == 2
    assert "supersedes" in answer["answer"].lower()
