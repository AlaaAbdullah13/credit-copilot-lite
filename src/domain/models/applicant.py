from datetime import date

from pydantic import BaseModel


class Applicant(BaseModel):
    id: str | None = None
    name: str | None = None
    birth_date: date | None = None
    monthly_income: float
    other_monthly_installments: float
    nationality: str | None = None
    gender: str | None = None
    marital_status: str | None = None
