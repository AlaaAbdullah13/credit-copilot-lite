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
    assert dbr == Decimal("40.62")

    max_amount = calculate_max_eligible_amount(emi, annual_rate, months)
    assert max_amount == Decimal(350000)


def test_dbr_at_limit_and_zero_obligations():
    installment = 10250.0
    assert calculate_dbr(installment, 20500.0) == Decimal("50.00")
    assert calculate_dbr(installment, 20500.0, 0.0) == Decimal("50.00")
    assert calculate_dbr(0.0, 20000.0) == Decimal("0.00")


def test_age_limit_and_product_limits():
    dob = date(1960, 1, 15)
    app_date = date(2024, 1, 15)
    assert age_at_maturity_check(dob, app_date, 60, 69) is True
    assert age_at_maturity_check(dob, app_date, 60, 68) is False

    assert validate_product_limits(20000, 12) is True
    assert validate_product_limits(1000000, 60) is True
    assert validate_product_limits(15000, 12) is False
    assert validate_product_limits(500000, 11) is False
    assert validate_product_limits(500000, 61) is False


def test_bureau_and_employment_checks():
    assert evaluate_bureau_score(680) is True
    assert evaluate_bureau_score(679) is False
    assert employment_duration_ok(6) is True
    assert employment_duration_ok(5) is False


def test_max_eligible_amount_rounds_down_to_nearest_thousand():
    max_amount = calculate_max_eligible_amount(10250.0, 15.0, 60)
    assert max_amount == Decimal(430000)


def test_zero_or_negative_inputs():
    with pytest.raises(ValueError):
        calculate_installment(10000, 12.5, 0)
    with pytest.raises(ValueError):
        calculate_dbr(5000, 0)
    with pytest.raises(ValueError):
        calculate_max_eligible_amount(1000, 12.5, 0)
