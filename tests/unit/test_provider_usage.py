from src.infrastructure.llm.gemini_adapter import GeminiLLMAdapter
from src.infrastructure.llm.groq_adapter import GroqLLMAdapter


def test_gemini_response_usage_is_returned_and_accumulated(monkeypatch):
    adapter = GeminiLLMAdapter("test-key")
    monkeypatch.setattr(
        adapter,
        "_request_json",
        lambda *_: {
            "candidates": [{"content": {"parts": [{"text": "{}"}]}}],
            "usageMetadata": {
                "promptTokenCount": 11,
                "candidatesTokenCount": 7,
                "totalTokenCount": 18,
            },
        },
    )

    response = adapter.complete("hello")

    assert response["usage"] == {
        "prompt_tokens": 11,
        "completion_tokens": 7,
        "total_tokens": 18,
    }
    assert adapter.tokens_consumed == 18


def test_groq_response_usage_is_returned_and_accumulated(monkeypatch):
    adapter = GroqLLMAdapter("test-key")
    monkeypatch.setattr(
        adapter,
        "_request_json",
        lambda *_: {
            "choices": [{"message": {"content": "{}"}}],
            "usage": {"prompt_tokens": 13, "completion_tokens": 5, "total_tokens": 18},
        },
    )

    response = adapter.complete("hello")

    assert response["usage"]["total_tokens"] == 18
    assert adapter.token_usage["prompt_tokens"] == 13
