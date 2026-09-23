from .base import LLMAdapter
from typing import Dict, Any


class FakeLLMAdapter(LLMAdapter):
    def __init__(self, seed: str = "fake"):
        self.seed = seed

    def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        # Deterministic fake response for local testing
        return {
            "prompt": prompt,
            "text": "{\"applicant\": {\"income\": 20000}, \"decision\": \"proceed\"}",
            "structured": {"applicant": {"income": 20000}, "decision": "proceed"},
        }
