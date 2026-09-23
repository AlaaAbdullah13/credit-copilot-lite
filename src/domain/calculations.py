from decimal import ROUND_HALF_UP, Decimal, getcontext

getcontext().prec = 28


def _quantize2(d: Decimal) -> Decimal:
    return d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_installment(principal: float, annual_rate_percent: float, months: int) -> Decimal:
    """Calculate monthly installment (EMI) using reducing-balance formula.

    principal: loan amount
    annual_rate_percent: e.g., 12.5 for 12.5%%
    months: number of monthly installments
    Returns: Decimal rounded half-up to 2 decimals
    """
    P = Decimal(str(principal))
    if months <= 0:
        raise ValueError("months must be > 0")
    r = Decimal(str(annual_rate_percent)) / Decimal(100) / Decimal(12)
    n = int(months)
    if r == 0:
        emi = P / Decimal(n)
    else:
        one_plus_r_n = (Decimal(1) + r) ** n
        emi = P * r * one_plus_r_n / (one_plus_r_n - Decimal(1))
    return _quantize2(emi)


def calculate_dbr(monthly_installment: float, monthly_income: float, other_installments: float = 0.0) -> Decimal:
    """Debt Burden Ratio in percent, rounded half-up to 2 decimals."""
    total = Decimal(str(monthly_installment)) + Decimal(str(other_installments))
    income = Decimal(str(monthly_income))
    if income == 0:
        raise ValueError("monthly_income must be > 0")
    ratio = (total / income) * Decimal(100)
    return _quantize2(ratio)


def calculate_max_eligible_amount(monthly_installment: float, annual_rate_percent: float, months: int) -> Decimal:
    """Invert EMI formula to compute principal given EMI, rate and tenure."""
    emi = Decimal(str(monthly_installment))
    r = Decimal(str(annual_rate_percent)) / Decimal(100) / Decimal(12)
    n = int(months)
    if r == 0:
        principal = emi * Decimal(n)
    else:
        one_plus_r_n = (Decimal(1) + r) ** n
        principal = emi * (one_plus_r_n - Decimal(1)) / (r * one_plus_r_n)
    return _quantize2(principal)
