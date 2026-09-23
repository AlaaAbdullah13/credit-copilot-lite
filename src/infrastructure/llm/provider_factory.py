from __future__ import annotations

import os

from src.infrastructure.llm.base import LLMProvider
from src.infrastructure.llm.fake_adapter import FakeLLMAdapter
from src.infrastructure.llm.gemini_adapter import GeminiLLMAdapter
from src.infrastructure.llm.groq_adapter import GroqLLMAdapter


def create_llm_provider() -> LLMProvider:
    """Create the configured LLM provider from environment values in .env."""
    provider_name = (os.getenv("LLM_PROVIDER") or "fake").strip().lower()

    if provider_name in {"fake", "offline", "mock"}:
        return FakeLLMAdapter()
    if provider_name == "gemini":
        return GeminiLLMAdapter(os.getenv("GEMINI_API_KEY"))
    if provider_name == "groq":
        return GroqLLMAdapter(os.getenv("GROQ_API_KEY"))

    raise ValueError(f"Unsupported LLM provider configured: {provider_name!r}")


__all__ = ["create_llm_provider"]
