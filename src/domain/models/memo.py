from typing import Any

from pydantic import BaseModel


class CreditMemo(BaseModel):
    application_id: str | None = None
    calculations: dict[str, Any] = {}
    decision: str | None = None
    status: str = "pending_approval"
    recommended_amount: float | None = None
    approval_required_from: str | None = None
    citations: list | None = []
    raw_extraction: dict[str, Any] | None = None
