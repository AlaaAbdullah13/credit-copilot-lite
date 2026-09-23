from datetime import datetime, timezone


def age_at_maturity_ok(birth_date: datetime.date | None, tenure_months: int, max_age_at_maturity: int | None) -> bool:
    if birth_date is None or max_age_at_maturity is None:
        return True
    # compute age at maturity
    years_to_maturity = tenure_months / 12
    today = datetime.now(tz=timezone.utc).date()
    age_now = (today - birth_date).days / 365.25
    age_at_maturity = age_now + years_to_maturity
    return age_at_maturity <= max_age_at_maturity


def tenure_ok(tenure_months: int, max_tenure_months: int | None) -> bool:
    if max_tenure_months is None:
        return True
    return tenure_months <= max_tenure_months


def bureau_score_ok(score: int | None, min_score: int | None) -> bool:
    if min_score is None or score is None:
        return True
    return score >= min_score


def dbr_ok(dbr_percent: float, max_dbr_percent: float = 50.0) -> bool:
    return dbr_percent <= max_dbr_percent
