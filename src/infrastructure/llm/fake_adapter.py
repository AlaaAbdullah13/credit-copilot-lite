from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any

from src.infrastructure.llm.base import LLMProvider


class FakeLLMAdapter(LLMProvider):
    """Deterministic adapter used for offline pipeline testing."""

    def __init__(self, seed: str = "fake") -> None:
        self.seed = seed

    @staticmethod
    def _normalize_value(value: Any) -> Any:
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        return value

    def complete(self, prompt: str, **kwargs: Any) -> dict[str, Any]:
        lowered = (prompt or "").lower()
        payload = kwargs.get("application") or kwargs.get("input") or kwargs.get("json") or {}
        payload = {key: self._normalize_value(value) for key, value in payload.items()}

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
                "monthly_income": {
                    "value": payload.get("monthly_income", 15000),
                    "source_document": "application-form",
                    "source_section": "income-details",
                    "quoted_text": f"Monthly income: {payload.get('monthly_income', 15000)} EGP",
                },
            }
            return {"content": json.dumps(extraction), "json": extraction}

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
            return {"content": memo_text, "json": {"recommendation": "pending", "summary": memo_text}}

        return {"content": json.dumps({"result": "ok"}), "json": {"result": "ok"}}

    def embed(self, text: str, **kwargs: Any) -> list[float]:
        return [float(ord(char) % 10) / 10 for char in (text or "")[:32]] or [0.0]

    def generate(self, prompt: str, **kwargs: Any) -> dict[str, Any]:
        return self.complete(prompt, **kwargs)
