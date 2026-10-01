from datetime import date
from decimal import Decimal

import pytest

from src.domain.calculations import (
    age_at_maturity_check,
    calculate_dbr,
    calculate_installment,
    calculate_max_eligible_amount,
    employment_duration_ok,
    evaluate_bureau_score,
    validate_product_limits,
)


def test_app_001_standard_formula_numbers():
    principal = 350000
    annual_rate = 15.0
    months = 60

    emi = calculate_installment(principal, annual_rate, months)
    assert emi == Decimal("8326.48")

    dbr = calculate_dbr(emi, 20500.0)
    assert dbr == Decimal("0.4062")

    max_amount = calculate_max_eligible_amount(
        emi, annual_rate, months, max_dbr=Decimal("0.50")
    )
    assert max_amount == Decimal(350000)


def test_dbr_at_limit_and_zero_obligations():
    installment = 10250.0
    assert calculate_dbr(installment, 20500.0) == Decimal("0.5000")
    assert calculate_dbr(installment, 20500.0, 0.0) == Decimal("0.5000")
    assert calculate_dbr(0.0, 20000.0) == Decimal("0.0000")


def test_exact_dbr_preserves_precision_for_rule_comparisons():
    from src.domain.calculations import calculate_exact_dbr

    assert calculate_exact_dbr(4500.004, 10000, 0) > Decimal("0.45")


def test_age_limit_and_product_limits():
    dob = date(1960, 1, 15)
    app_date = date(2024, 1, 15)
    assert age_at_maturity_check(dob, app_date, 60, 69) is True
    assert age_at_maturity_check(dob, app_date, 60, 68) is False

    limits = {
        "min_amount": 20000,
        "max_amount": 1000000,
        "min_tenor": 12,
        "max_tenor": 60,
    }
    assert validate_product_limits(20000, 12, **limits) is True
    assert validate_product_limits(1000000, 60, **limits) is True
    assert validate_product_limits(15000, 12, **limits) is False
    assert validate_product_limits(500000, 11, **limits) is False
    assert validate_product_limits(500000, 61, **limits) is False


def test_bureau_and_employment_checks():
    assert evaluate_bureau_score(680, 680) is True
    assert evaluate_bureau_score(679, 680) is False
    assert employment_duration_ok(6, 6) is True
    assert employment_duration_ok(5, 6) is False


def test_max_eligible_amount_rounds_down_to_nearest_thousand():
    max_amount = calculate_max_eligible_amount(
        10250.0, 15.0, 60, max_dbr=Decimal("0.50")
    )
    assert max_amount == Decimal(430000)


def test_zero_or_negative_inputs():
    with pytest.raises(ValueError):
        calculate_installment(10000, 12.5, 0)
    with pytest.raises(ValueError):
        calculate_dbr(5000, 0)
    with pytest.raises(ValueError):
        calculate_max_eligible_amount(1000, 12.5, 0, max_dbr=Decimal("0.50"))
