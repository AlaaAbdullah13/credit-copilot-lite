from pydantic import BaseModel
from typing import Optional


class RuleSet(BaseModel):
    edition: str
    max_age_at_maturity: Optional[int] = None
    max_tenure_months: Optional[int] = None
    min_bureau_score: Optional[int] = None
