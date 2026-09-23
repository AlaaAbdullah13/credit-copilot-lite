
from pydantic import BaseModel


class Policy(BaseModel):
    edition: str
    min_age: int | None = None
    max_tenure_months: int | None = None
    min_bureau_score: int | None = None
    notes: str | None = None
