from datetime import date
from typing import Optional

from .models.ruleset import RuleSet


def age_at_maturity_ok(birth_date: Optional[date], tenure_months: int, max_age_at_maturity: Optional[int]) -> bool:
    if birth_date is None or max_age_at_maturity is None:
        return True
    # compute age at maturity
    years_to_maturity = tenure_months / 12
    age_now = (date.today() - birth_date).days / 365.25
    age_at_maturity = age_now + years_to_maturity
    return age_at_maturity <= max_age_at_maturity


def tenure_ok(tenure_months: int, max_tenure_months: Optional[int]) -> bool:
    if max_tenure_months is None:
        return True
    return tenure_months <= max_tenure_months


def bureau_score_ok(score: Optional[int], min_score: Optional[int]) -> bool:
    if min_score is None or score is None:
        return True
    return score >= min_score


def dbr_ok(dbr_percent: float, max_dbr_percent: float = 50.0) -> bool:
    return dbr_percent <= max_dbr_percent
