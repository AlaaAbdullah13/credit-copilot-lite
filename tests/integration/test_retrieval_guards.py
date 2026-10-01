from src.infrastructure.ingestion.pipeline import ingest_documents, query_policy
from src.infrastructure.llm.fake_adapter import FakeLLMAdapter
from src.infrastructure.vector_store.chroma_adapter import ChromaAdapter


class InventingAnswerProvider(FakeLLMAdapter):
    def complete(self, prompt, **kwargs):
        return {"content": "The maximum DBR is 99%."}


def _store(tmp_path):
    store = ChromaAdapter(
        persist_directory=str(tmp_path / "policy-store"),
        embedding_provider=FakeLLMAdapter(),
    )
    ingest_documents(
        [
            "data/policy/credit-policy-2024.pdf",
            "data/policy/credit-policy-2025.pdf",
            "data/policy/circular-2024-07.md",
            "data/policy/circular-2025-02.md",
        ],
        store=store,
    )
    return store


def test_ungrounded_match_returns_exact_refusal_shape(tmp_path):
    response = query_policy(
        "Who won the World Cup?", store=_store(tmp_path), threshold=0
    )
    assert response == {
        "answer": "The documents do not contain enough information to answer this question.",
        "citations": [],
        "reason": "no_chunk_above_threshold",
    }


def test_edition_filter_and_unfiltered_answer_labels_both_editions(tmp_path):
    store = _store(tmp_path)
    current = query_policy(
        "maximum debt burden ratio", store=store, policy_edition="CP-2025", threshold=0
    )
    comparison = query_policy(
        "maximum debt burden ratio", store=store, threshold=0, k=5
    )
    assert "45%" in current["answer"]
    assert {citation["policy_edition"] for citation in current["citations"]} == {
        "CP-2025"
    }
    assert "CP-2024:" in comparison["answer"]
    assert "CP-2025:" in comparison["answer"]


def test_composer_cannot_introduce_a_number_absent_from_chunks(tmp_path):
    response = query_policy(
        "maximum debt burden ratio",
        store=_store(tmp_path),
        threshold=0,
        llm_provider=InventingAnswerProvider(),
    )
    assert "99%" not in response["answer"]
    assert response["citations"]
