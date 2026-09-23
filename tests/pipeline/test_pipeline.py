from __future__ import annotations

from datetime import date

import pytest

from src.application.pipeline import run_assessment
from src.domain.exceptions import InvalidLLMOutput
from src.infrastructure.llm.fake_adapter import FakeLLMAdapter


def _base_application(**overrides):
    application = {
        "id": "app-001",
        "requested_amount": 350000,
        "annual_rate": 15.0,
        "tenure_months": 60,
        "monthly_income": 20500,
        "other_monthly_installments": 0,
        "date_of_birth": date(1990, 1, 1),
        "application_date": date(2025, 1, 15),
    }
    application.update(overrides)
    return application


def test_approvable_application():
    memo = run_assessment(_base_application(), llm=FakeLLMAdapter())
    assert memo.application_id == "app-001"
    assert memo.decision == "pending"
    assert memo.calculations["emi"] > 0
    assert memo.calculations["dbr"] > 0
    assert "rule_results" in memo.raw_extraction


def test_over_age_application():
    memo = run_assessment(
        _base_application(date_of_birth=date(1958, 1, 1)),
        llm=FakeLLMAdapter(),
    )
    assert memo.decision == "pending"
    rule_results = memo.raw_extraction["rule_results"]
    assert any(rule["rule"] == "age_at_maturity" and rule["status"] == "fail" for rule in rule_results)
    assert any(citation.get("source_file") for citation in memo.citations)


def test_invalid_llm_json_output():
    class BrokenLLMAdapter(FakeLLMAdapter):
        def complete(self, prompt, **kwargs):
            return {"content": "{not valid json"}

    with pytest.raises(InvalidLLMOutput):
        run_assessment(_base_application(), llm=BrokenLLMAdapter(), raise_on_error=True)

    fallback = run_assessment(_base_application(), llm=BrokenLLMAdapter(), raise_on_error=False)
    assert fallback.decision == "Refer to human"


def test_fairness():
    base = _base_application()
    app_a = {**base, "gender": "female", "religion": "islam", "nationality": "egyptian"}
    app_b = {**base, "gender": "male", "religion": "christian", "nationality": "syrian"}

    memo_a = run_assessment(app_a, llm=FakeLLMAdapter())
    memo_b = run_assessment(app_b, llm=FakeLLMAdapter())

    assert memo_a.calculations == memo_b.calculations
    assert memo_a.raw_extraction["memo"] == memo_b.raw_extraction["memo"]
    assert memo_a.decision == memo_b.decision == "pending"
