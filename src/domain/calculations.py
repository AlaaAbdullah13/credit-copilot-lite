from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import ROUND_HALF_UP, Decimal, getcontext

getcontext().prec = 28


def _as_decimal(value: Decimal | float | str) -> Decimal:
    return Decimal(str(value))


def _quantize2(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _floor_to_thousands(value: Decimal) -> Decimal:
    return (value // Decimal(1000)) * Decimal(1000)


def calculate_installment(
    principal: float | Decimal,
    annual_rate_percent: float | Decimal,
    months: int,
) -> Decimal:
    """Calculate the monthly installment with the reducing-balance formula.

    Formula: P × r / (1 - (1 + r)^-n)
    where r is the annual rate divided by 12 and n is the number of months.
    The result is rounded half-up to 2 decimal places.
    """
    P = _as_decimal(principal)
    if months <= 0:
        raise ValueError("months must be > 0")
    if P < 0:
        raise ValueError("principal must be >= 0")

    annual_rate = _as_decimal(annual_rate_percent)
    monthly_rate = annual_rate / Decimal(100) / Decimal(12)

    if monthly_rate == 0:
        emi = P / Decimal(months)
    else:
        emi = (P * monthly_rate) / (
            Decimal(1) - (Decimal(1) + monthly_rate) ** (-months)
        )

    return _quantize2(emi)


def calculate_dbr(
    monthly_installment: float | Decimal,
    monthly_income: float | Decimal,
    other_installments: float | Decimal = 0.0,
) -> Decimal:
    """Return the debt burden ratio as a percentage rounded half-up to 2 decimals."""
    installment = _as_decimal(monthly_installment)
    income = _as_decimal(monthly_income)
    obligations = _as_decimal(other_installments)

    if income <= 0:
        raise ValueError("monthly_income must be > 0")

    dbr = ((installment + obligations) / income) * Decimal(100)
    return _quantize2(dbr)


def calculate_max_eligible_amount(
    monthly_installment: float | Decimal,
    annual_rate_percent: float | Decimal,
    months: int,
    *,
    monthly_income: float | Decimal | None = None,
    max_dbr_percent: float | Decimal = 50.0,
    other_installments: float | Decimal = 0.0,
) -> Decimal:
    """Compute the largest principal compatible with the payment or DBR limit.

    When monthly_income is provided, the maximum affordable EMI is capped by the
    allowed DBR limit. The final principal is floored to the nearest 1,000 EGP.
    """
    if months <= 0:
        raise ValueError("months must be > 0")

    allowable_installment = _as_decimal(monthly_installment)
    if monthly_income is not None:
        income = _as_decimal(monthly_income)
        obligations = _as_decimal(other_installments)
        dbr_limit = _as_decimal(max_dbr_percent) / Decimal(100)
        allowable_installment = (income * dbr_limit) - obligations

    if allowable_installment < 0:
        return Decimal(0)

    annual_rate = _as_decimal(annual_rate_percent)
    monthly_rate = annual_rate / Decimal(100) / Decimal(12)

    if monthly_rate == 0:
        principal = allowable_installment * Decimal(months)
    else:
        factor = (Decimal(1) + monthly_rate) ** months
        principal = (
            allowable_installment * (factor - Decimal(1))
        ) / (monthly_rate * factor)

    return _floor_to_thousands(principal)


def age_at_maturity_check(
    date_of_birth: date | None,
    application_date: date | None,
    tenor_months: int,
    max_age_at_maturity: int,
) -> bool:
    """Return True when applicant age at maturity is within the policy cap."""
    if date_of_birth is None:
        return True
    if tenor_months < 0:
        raise ValueError("tenor_months must be >= 0")

    as_of = application_date or datetime.now(timezone.utc).date()
    age_years = Decimal((as_of - date_of_birth).days) / Decimal("365.25")
    age_at_maturity = age_years + (Decimal(tenor_months) / Decimal(12))
    return age_at_maturity <= Decimal(max_age_at_maturity)


def evaluate_bureau_score(score: int | None, min_score: int | None = 680) -> bool:
    """Score below threshold should not be automatically declined; it should be referred."""
    if score is None or min_score is None:
        return True
    return score >= min_score


def employment_duration_ok(
    months_employed: float | Decimal, minimum_months: int = 6
) -> bool:
    """Check the minimum employment duration requirement."""
    if months_employed is None:
        return True
    return _as_decimal(months_employed) >= Decimal(minimum_months)


def validate_product_limits(
    loan_amount: float | Decimal,
    tenor_months: int,
    *,
    min_amount: float | Decimal = 20000,
    max_amount: float | Decimal = 1000000,
    min_tenor: int = 12,
    max_tenor: int = 60,
) -> bool:
    """Validate loan amount and tenor against product sheet limits."""
    amount = _as_decimal(loan_amount)
    amount_ok = amount >= _as_decimal(min_amount) and amount <= _as_decimal(max_amount)
    tenor_ok = min_tenor <= tenor_months <= max_tenor
    return amount_ok and tenor_ok


__all__ = [
    "age_at_maturity_check",
    "calculate_dbr",
    "calculate_installment",
    "calculate_max_eligible_amount",
    "employment_duration_ok",
    "evaluate_bureau_score",
    "validate_product_limits",
]
