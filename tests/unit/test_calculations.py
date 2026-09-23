from src.domain.calculations import (
    calculate_dbr,
    calculate_installment,
    calculate_max_eligible_amount,
)


def test_worked_example_approx():
    # Using approximate parameters to reproduce the worked example values
    principal = 382000
    annual_rate = 12.5
    months = 60

    emi = calculate_installment(principal, annual_rate, months)
    # EMI should be close to the worked example 8,630.39
    assert abs(float(emi) - 8630.39) < 200

    dbr = calculate_dbr(emi, 20500)
    # DBR should be close to 42.10%
    assert abs(float(dbr) - 42.10) < 5

    # If we invert the EMI, we should get approximately the original principal
    max_amount = calculate_max_eligible_amount(float(emi), annual_rate, months)
    assert abs(float(max_amount) - principal) < 5000
