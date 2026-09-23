from pydantic import BaseModel
from typing import Optional
from datetime import date


class Applicant(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    birth_date: Optional[date] = None
    monthly_income: float
    other_monthly_installments: float = 0.0
    nationality: Optional[str] = None
    gender: Optional[str] = None
    marital_status: Optional[str] = None
