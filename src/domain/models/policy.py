from pydantic import BaseModel
from typing import Optional


class Policy(BaseModel):
    edition: str
    min_age: Optional[int] = None
    max_tenure_months: Optional[int] = None
    min_bureau_score: Optional[int] = None
    notes: Optional[str] = None
