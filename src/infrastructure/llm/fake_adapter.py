from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime
from typing import Any

from src.infrastructure.llm.base import LLMProvider


class FakeLLMAdapter(LLMProvider):
    """Deterministic adapter used for offline pipeline testing."""

    def __init__(self, seed: str = "fake") -> None:
        self.seed = seed
        self.tokens_consumed = 0
        self.token_usage: dict[str, int] = {}

    @staticmethod
    def _normalize_value(value: Any) -> Any:
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        return value

    @staticmethod
    def _display(value: Any) -> Any:
        return int(value) if isinstance(value, float) and value.is_integer() else value

    def complete(self, prompt: str, **kwargs: Any) -> dict[str, Any]:
        # FakeLLM has no provider billable usage; this is its explicit,
        # deterministic adapter usage counter rather than an API-layer guess.
        self.tokens_consumed += max(1, len(prompt.split()))
        self.token_usage = {
            "prompt_tokens": max(1, len(prompt.split())),
            "completion_tokens": 0,
            "total_tokens": max(1, len(prompt.split())),
        }
        lowered = (prompt or "").lower()
        payload = (
            kwargs.get("application") or kwargs.get("input") or kwargs.get("json") or {}
        )
        payload = {
            key: self._display(self._normalize_value(value))
            for key, value in payload.items()
        }

        if "extract" in lowered:
            extraction = {
                "requested_amount": {
                    "value": payload.get("requested_amount", 100000),
                    "source_document": "application-form",
                    "source_section": "loan-details",
                    "quoted_text": f"Requested amount: {payload.get('requested_amount', 100000)} EGP",
                },
                "tenure_months": {
                    "value": payload.get("tenure_months", 36),
                    "source_document": "application-form",
                    "source_section": "loan-details",
                    "quoted_text": f"Tenor: {payload.get('tenure_months', 36)} months",
                },
                "date_of_birth": {
                    "value": payload.get("date_of_birth", "1990-01-01"),
                    "source_document": "application-form",
                    "source_section": "personal-details",
                    "quoted_text": f"Date of birth: {payload.get('date_of_birth', '1990-01-01')}",
                },
                "application_date": {
                    "value": payload.get("application_date", "2025-01-15"),
                    "source_document": "application-form",
                    "source_section": "submission-details",
                    "quoted_text": f"Application date: {payload.get('application_date', '2025-01-15')}",
                },
                "net_monthly_income": {
                    "value": payload.get("monthly_income", 15000),
                    "source_document": "application-form",
                    "source_section": "income-details",
                    "quoted_text": f"Monthly income: {payload.get('monthly_income', 15000)} EGP",
                },
                "existing_monthly_obligations": {
                    "value": payload.get("other_monthly_installments", 0),
                    "source_document": "application-form",
                    "source_section": "income-details",
                    "quoted_text": f"Obligations: {payload.get('other_monthly_installments', 0)} EGP",
                },
                "employment_start_date": {
                    "value": payload.get("employment_start_date", "2020-01-01"),
                    "source_document": "application-form",
                    "source_section": "employment",
                    "quoted_text": f"Employment start: {payload.get('employment_start_date', '2020-01-01')}",
                },
                "bureau_score": {
                    "value": payload.get("bureau_score", 700),
                    "source_document": "application-form",
                    "source_section": "bureau",
                    "quoted_text": f"Bureau score: {payload.get('bureau_score', 700)}",
                },
            }
            return {
                "content": json.dumps(extraction),
                "json": extraction,
                "usage": self.token_usage,
            }

        if "memo" in lowered:
            requested_amount = payload.get("requested_amount", 0)
            monthly_income = payload.get("monthly_income", 0)
            emi = payload.get("calculations", {}).get("emi", 0)
            dbr = payload.get("calculations", {}).get("dbr", 0)
            max_amount = payload.get("calculations", {}).get("max_amount", 0)
            memo_text = (
                "Recommendation: pending. Requested amount is "
                f"{requested_amount} EGP, monthly income is {monthly_income} EGP, "
                f"EMI is {emi} EGP, DBR is {dbr}%, and the maximum eligible amount is {max_amount} EGP."
            )
            return {
                "content": memo_text,
                "json": {"recommendation": "pending", "summary": memo_text},
                "usage": self.token_usage,
            }

        return {
            "content": json.dumps({"result": "ok"}),
            "json": {"result": "ok"},
            "usage": self.token_usage,
        }

    def embed(self, text: str, **kwargs: Any) -> list[float]:
        """Return a fixed-size, deterministic local embedding.

        A fixed dimension is required by vector databases; hashing words also
        gives the offline test provider useful lexical similarity semantics.
        """
        vector = [0.0] * 256
        for token in re.findall(r"[a-z0-9]+", (text or "").lower()):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = digest[0] % len(vector)
            vector[index] += 1.0
        return vector

    def generate(self, prompt: str, **kwargs: Any) -> dict[str, Any]:
        return self.complete(prompt, **kwargs)
