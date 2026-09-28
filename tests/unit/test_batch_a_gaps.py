from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest

from src.application.pipeline import (
    _validate_extraction_payload,
    draft_credit_memo,
    evaluate_rules,
    run_assessment,
)
from src.application.policy_data import load_credit_policy_limits
from src.domain.calculations import (
    calculate_dbr,
    calculate_installment,
    calculate_max_eligible_amount,
)
from src.domain.exceptions import PolicySourceUnavailable, UnverifiedExtraction
from src.infrastructure.llm.fake_adapter import FakeLLMAdapter


def application(**overrides):
    result = {
        "requested_amount": 300000,
        "tenure_months": 60,
        "monthly_income": 30000,
        "other_monthly_installments": 4000,
        "date_of_birth": date(1990, 1, 1),
        "application_date": date(2025, 3, 1),
        "months_employed": 12,
        "bureau_score": 700,
    }
    result.update(overrides)
    return result


def test_section_23_worked_example_uses_ratio_dbr_and_policy_maximums():
    emi = calculate_installment(300000, 24, 60)
    assert emi == Decimal("8630.39")
    assert calculate_dbr(emi, 30000, 4000) == Decimal("0.4210")
    assert calculate_max_eligible_amount(emi, 24, 60, monthly_income=30000, other_installments=4000, max_dbr=Decimal("0.50")) == Decimal(382000)
    assert calculate_max_eligible_amount(emi, 24, 60, monthly_income=30000, other_installments=4000, max_dbr=Decimal("0.45")) == Decimal(330000)


def test_credit_policy_limits_include_minimum_income_by_edition():
    assert load_credit_policy_limits("2024")["min_income"] == Decimal(8000)
    assert load_credit_policy_limits("2025")["min_income"] == Decimal(10000)


def test_income_can_pass_2024_and_fail_2025():
    app = application(monthly_income=9000)
    assert next(rule for rule in evaluate_rules(app, "2024") if rule["rule"] == "min_income")["status"] == "pass"
    assert next(rule for rule in evaluate_rules(app, "2025") if rule["rule"] == "min_income")["status"] == "fail"


def test_missing_bureau_score_refers():
    assert next(rule for rule in evaluate_rules(application(bureau_score=None), "2025") if rule["rule"] == "bureau_score")["status"] == "refer"


@pytest.mark.parametrize(("months", "score", "expected"), [(12, 700, ("pass", "pass")), (5, 700, ("fail", "pass")), (12, 599, ("pass", "refer"))])
def test_employment_and_bureau_rules(months, score, expected):
    rules = {rule["rule"]: rule["status"] for rule in evaluate_rules(application(months_employed=months, bureau_score=score), "2025")}
    assert (rules["employment_duration"], rules["bureau_score"]) == expected


@pytest.mark.parametrize(("amount", "tenor", "expected"), [(20000, 12, "pass"), (1000000, 60, "pass"), (19999, 12, "fail"), (1000001, 60, "fail"), (20000, 11, "fail"), (20000, 61, "fail")])
def test_product_limits(amount, tenor, expected):
    assert next(rule for rule in evaluate_rules(application(requested_amount=amount, tenure_months=tenor), "2025") if rule["rule"] == "product_limits")["status"] == expected


def test_missing_pricing_is_referred_to_human():
    memo = run_assessment(application(tenure_months=73), llm=FakeLLMAdapter())
    assert memo.decision == "Refer to human"


def test_pdftotext_missing_is_named_error():
    with patch(
        "src.application.policy_data.subprocess.run", side_effect=FileNotFoundError
    ), pytest.raises(PolicySourceUnavailable, match="pdftotext"):
        load_credit_policy_limits("2025")


def test_draft_memo_receives_only_code_supplied_numbers():
    memo = draft_credit_memo(FakeLLMAdapter(), {}, {"requested_amount": 300000, "monthly_income": 30000, "emi": 8630.39, "dbr": 0.421, "max_amount": 382000}, [])
    assert "8630.39" in memo and "382000" in memo


def test_extraction_verification_rejects_all_evidence_failures():
    payload = {field: {"value": 1, "source_document": "doc", "source_section": "s", "quoted_text": "1"} for field in ("requested_amount", "tenure_months", "date_of_birth", "application_date", "net_monthly_income", "existing_monthly_obligations", "employment_start_date", "bureau_score")}
    for mutation, documents in (({"quoted_text": "2"}, {"doc": "2"}), ({"value": 2}, {"doc": "1"}), ({}, {"doc": "other"})):
        candidate = {key: dict(value) for key, value in payload.items()}
        candidate["net_monthly_income"].update(mutation)
        with pytest.raises(UnverifiedExtraction):
            _validate_extraction_payload(candidate, documents)
