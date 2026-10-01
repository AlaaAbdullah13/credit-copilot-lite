import io
import json
from urllib.error import HTTPError

import pytest

from src.domain.exceptions import LLMProviderError
from src.infrastructure.llm.gemini_adapter import GeminiLLMAdapter
from src.infrastructure.vector_store.chroma_adapter import ChromaAdapter


class _Response:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self.payload).encode()


def test_gemini_embedding_uses_environment_model_dimension_and_batch(monkeypatch):
    monkeypatch.setenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-2")
    monkeypatch.setenv("GEMINI_EMBEDDING_DIM", "768")
    captured = {}

    def fake_urlopen(req, timeout):
        captured["url"] = req.full_url
        captured["payload"] = json.loads(req.data)
        return _Response({"embeddings": [{"values": [0.0] * 768}]})

    monkeypatch.setattr(
        "src.infrastructure.llm.gemini_adapter.request.urlopen", fake_urlopen
    )
    adapter = GeminiLLMAdapter("test-key")

    assert len(adapter.embed("policy chunk", task_type="RETRIEVAL_DOCUMENT")) == 768
    assert "/gemini-embedding-2:batchEmbedContents?" in captured["url"]
    request_payload = captured["payload"]["requests"][0]
    assert request_payload["outputDimensionality"] == 768
    assert request_payload["taskType"] == "RETRIEVAL_DOCUMENT"


def test_gemini_http_error_is_named_and_redacts_key(monkeypatch):
    key = "top-secret-key"

    def fake_urlopen(req, timeout):
        raise HTTPError(
            req.full_url,
            404,
            "Not Found",
            {},
            io.BytesIO(f"request url {req.full_url}".encode()),
        )

    monkeypatch.setattr(
        "src.infrastructure.llm.gemini_adapter.request.urlopen", fake_urlopen
    )
    with pytest.raises(LLMProviderError) as exc_info:
        GeminiLLMAdapter(key).embed("test")

    assert "404" in str(exc_info.value)
    assert key not in str(exc_info.value)


def test_collection_embedding_configuration_mismatch_has_reingest_guidance():
    class Collection:
        def __init__(self):
            self.metadata = {
                "embedding_model": "old-model",
                "embedding_dimension": 384,
            }

        @staticmethod
        def count():
            return 1

    adapter = object.__new__(ChromaAdapter)
    adapter.collection = Collection()
    adapter.embedding_model = "gemini-embedding-001"
    adapter.embedding_dimension = 768

    with pytest.raises(LLMProviderError, match="Delete data/chroma_db and re-ingest"):
        adapter._validate_collection_embedding_config()
