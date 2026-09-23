from .base import LLMAdapter
from typing import Dict, Any


class GeminiAdapter(LLMAdapter):
    def __init__(self, api_key: str):
        self.api_key = api_key

    def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        # Placeholder implementation. Real implementation calls Gemini API.
        raise NotImplementedError("GeminiAdapter.generate not implemented in boilerplate")
