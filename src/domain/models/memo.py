from pydantic import BaseModel
from typing import Any, Dict, Optional


class CreditMemo(BaseModel):
    application_id: Optional[str] = None
    calculations: Dict[str, Any] = {}
    decision: Optional[str] = None
    citations: Optional[list] = []
    raw_extraction: Optional[Dict[str, Any]] = None
