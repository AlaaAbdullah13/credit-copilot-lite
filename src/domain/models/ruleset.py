from pydantic import BaseModel


class RuleSet(BaseModel):
    edition: str
    max_age_at_maturity: int | None = None
    max_tenure_months: int | None = None
    min_bureau_score: int | None = None
