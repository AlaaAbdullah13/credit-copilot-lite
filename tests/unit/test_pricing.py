from decimal import Decimal


def test_pricing_rate_is_selected_by_tenor_and_segment():
    from src.application.policy_data import load_annual_rate

    assert load_annual_rate(60, "standard") == Decimal("24.00")
    assert load_annual_rate(60, "payroll_transfer") == Decimal("22.00")
