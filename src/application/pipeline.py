from typing import Any

from src.application.anonymizer import anonymize_application
from src.domain.calculations import (
    calculate_dbr,
    calculate_installment,
    calculate_max_eligible_amount,
)
from src.domain.models.memo import CreditMemo
from src.infrastructure.llm.fake_adapter import FakeLLMAdapter


def run_assessment(application: dict[str, Any], policy: dict[str, Any]) -> CreditMemo:
    """A fixed 8-step simplified pipeline placeholder.

    Steps: Load -> Anonymize -> Select Policy -> Extract JSON -> Retrieve Clauses
    -> Calculate -> Draft Memo -> Pending Approval
    """
    # 1. Load (application given)
    app = application

    # 2. Anonymize (we keep the operation to remove protected attributes)
    anonymize_application(app)

    # 4. Extract JSON (use fake LLM)
    llm = FakeLLMAdapter()
    extraction = llm.generate("extract structured json from application")

    # 5. Retrieve clauses (skipped in placeholder)
    citations = []

    # 6. Calculate
    emi = calculate_installment(
        application.get("requested_amount", 0), application.get("annual_rate", 12.5), application.get("tenure_months", 60)
    )
    dbr = calculate_dbr(emi, application.get("monthly_income", 1), application.get("other_monthly_installments", 0))
    max_amount = calculate_max_eligible_amount(emi, application.get("annual_rate", 12.5), application.get("tenure_months", 60))

    calculations = {"emi": float(emi), "dbr": float(dbr), "max_amount": float(max_amount)}

    # 7. Draft memo
    memo = CreditMemo(
        application_id=application.get("id"), calculations=calculations, citations=citations, raw_extraction=extraction
    )

    # 8. Pending approval
    memo.decision = None
    return memo
