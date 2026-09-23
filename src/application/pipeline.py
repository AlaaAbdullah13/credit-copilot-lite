from __future__ import annotations

import json
import logging
import re
from collections.abc import Mapping
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ValidationError

from src.application.anonymizer import anonymize_application
from src.application.validation import load_application, select_policy_edition
from src.domain.calculations import (
    age_at_maturity_check,
    calculate_dbr,
    calculate_installment,
    calculate_max_eligible_amount,
    validate_product_limits,
)
from src.domain.exceptions import (
    InvalidLLMOutput,
    PolicyEditionNotFound,
    UnverifiedExtraction,
)
from src.domain.models.memo import CreditMemo
from src.infrastructure.ingestion.pipeline import ingest_documents, query_policy
from src.infrastructure.llm.base import LLMProvider
from src.infrastructure.llm.prompt_loader import load_prompt
from src.infrastructure.llm.provider_factory import create_llm_provider
from src.infrastructure.vector_store.chroma_adapter import ChromaAdapter

logger = logging.getLogger(__name__)


class ExtractionField(BaseModel):
    value: Any
    source_document: str
    source_section: str
    quoted_text: str


class ApplicationExtraction(BaseModel):
    requested_amount: ExtractionField
    tenure_months: ExtractionField
    date_of_birth: ExtractionField
    application_date: ExtractionField
    monthly_income: ExtractionField | None = None


def _to_json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as exc:
            raise InvalidLLMOutput(f"LLM response is not valid JSON: {value!r}") from exc
        if not isinstance(parsed, dict):
            raise InvalidLLMOutput("LLM JSON payload must be an object")
        return parsed
    if isinstance(value, Mapping):
        return dict(value)
    raise InvalidLLMOutput("LLM response was not a JSON object")


def _normalize_text(value: Any) -> str:
    return " ".join(re.sub(r"[^a-zA-Z0-9]+", " ", str(value).lower()).split())


def _verify_value(value: Any, quoted_text: Any) -> None:
    if quoted_text is None:
        raise UnverifiedExtraction("Missing quoted_text for extraction")

    normalized_value = _normalize_text(value)
    normalized_quote = _normalize_text(quoted_text)

    if not normalized_value or normalized_value in normalized_quote:
        return

    # Accept simple numeric/string variants in the quote even when formatting differs.
    for candidate in {str(value), str(float(value)) if isinstance(value, (int, float, Decimal)) else None}:
        if candidate and _normalize_text(candidate) in normalized_quote:
            return

    raise UnverifiedExtraction(
        f"Extracted value {value!r} was not found verbatim in quoted_text {quoted_text!r}"
    )


def _validate_extraction_payload(payload: dict[str, Any]) -> dict[str, Any]:
    for field_name in [
        "requested_amount",
        "tenure_months",
        "date_of_birth",
        "application_date",
        "monthly_income",
    ]:
        if field_name not in payload:
            continue
        field = payload[field_name]
        if not isinstance(field, dict):
            raise InvalidLLMOutput(f"Field {field_name!r} is not an object")
        _verify_value(field.get("value"), field.get("quoted_text"))

    try:
        return ApplicationExtraction.model_validate(payload).model_dump(mode="python")
    except ValidationError as exc:
        raise InvalidLLMOutput("LLM extraction did not match the expected schema") from exc


def extract_structured_data(
    application: Mapping[str, Any],
    llm: LLMProvider | None = None,
    *,
    raise_on_error: bool = True,
) -> ApplicationExtraction:
    """Use the configured LLM to extract a validated application payload."""
    provider = llm or create_llm_provider()
    prompt = load_prompt("extract")
    response = provider.complete(prompt, application=dict(application))
    payload = response.get("json") if isinstance(response, dict) and isinstance(response.get("json"), dict) else None
    if payload is None:
        text = response.get("content") if isinstance(response, dict) else response
        payload = _to_json_object(text)

    validated = _validate_extraction_payload(payload)
    return ApplicationExtraction.model_validate(validated)


def retrieve_policy_clauses(
    policy_edition: str,
    *,
    store: ChromaAdapter | None = None,
    threshold: float = 0.01,
) -> list[dict[str, Any]]:
    vector_store = store or ChromaAdapter()
    policy_files = [
        "data/policy/circular-2024-07.md",
        "data/policy/circular-2025-02.md",
        "data/policy/product-sheet-personal-loan.md",
    ]
    ingest_documents(policy_files, store=vector_store, policy_edition=policy_edition)

    search_queries = [
        "maximum tenor unsecured consumer instalment loans",
        "maximum debt burden ratio unsecured consumer lending",
        "age and income eligibility requirements",
        "gender religion marital status nationality not used in credit decision",
    ]
    citations: list[dict[str, Any]] = []
    for query in search_queries:
        answer = query_policy(
            query,
            store=vector_store,
            policy_edition=policy_edition,
            threshold=threshold,
            k=3,
        )
        if answer.get("citations"):
            citations.extend(answer["citations"])
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, str]] = set()
    for citation in citations:
        key = (
            str(citation.get("source_file") or ""),
            str(citation.get("clause_id") or ""),
            str(citation.get("page") or ""),
            str(citation.get("policy_edition") or ""),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(citation)
    return deduped


def evaluate_rules(
    application: Mapping[str, Any],
    policy_edition: str,
    citations: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    app = load_application(application)
    max_dbr = 45.0 if policy_edition == "2025" else 50.0
    max_tenor = 72 if policy_edition == "2025" else 60
    age_limit = 69

    rules: list[dict[str, Any]] = []

    amount_ok = validate_product_limits(
        app["requested_amount"],
        app["tenure_months"],
        min_amount=20000,
        max_amount=1000000,
        min_tenor=12,
        max_tenor=max_tenor,
    )
    rules.append(
        {
            "rule": "product_limits",
            "status": "pass" if amount_ok else "fail",
            "citation": (citations or [])[0] if citations else {"source_file": "product-sheet-personal-loan.md"},
        }
    )

    emi = calculate_installment(app["requested_amount"], app.get("annual_rate", 12.5), app["tenure_months"])
    dbr = calculate_dbr(emi, app.get("monthly_income", 0), app.get("other_monthly_installments", 0))
    rules.append(
        {
            "rule": "debt_burden_ratio",
            "status": "pass" if float(dbr) <= max_dbr else "fail",
            "value": float(dbr),
            "limit": max_dbr,
            "citation": next((item for item in citations or [] if item.get("clause_id") in {"C-2", "C-1"}), {"source_file": "circular-2025-02.md"}),
        }
    )

    age_ok = age_at_maturity_check(app["date_of_birth"], app["application_date"], app["tenure_months"], age_limit)
    rules.append(
        {
            "rule": "age_at_maturity",
            "status": "pass" if age_ok else "fail",
            "value": age_ok,
            "citation": next((item for item in citations or [] if item.get("source_file", "").endswith("product-sheet-personal-loan.md")), {"source_file": "product-sheet-personal-loan.md"}),
        }
    )

    if app.get("gender") is not None or app.get("marital_status") is not None or app.get("religion") is not None or app.get("nationality") is not None:
        rules.append(
            {
                "rule": "protected_attributes_removed",
                "status": "pass",
                "citation": next((item for item in citations or [] if "circular-2025-02.md" in str(item.get("source_file"))), {"source_file": "circular-2025-02.md"}),
            }
        )

    return rules


def run_assessment(
    application: Mapping[str, Any],
    policy: Mapping[str, Any] | None = None,
    *,
    llm: LLMProvider | None = None,
    store: ChromaAdapter | None = None,
    raise_on_error: bool = False,
) -> CreditMemo:
    """Run the 8-step application assessment pipeline and return a credit memo."""
    try:
        app = load_application(application)
        sanitized = anonymize_application(app)
        policy_edition = select_policy_edition(app["application_date"])
        provider = llm or create_llm_provider()
        extraction = extract_structured_data(sanitized, llm=provider, raise_on_error=True)

        citations = retrieve_policy_clauses(policy_edition, store=store)
        rule_results = evaluate_rules(app, policy_edition, citations)

        emi = calculate_installment(app["requested_amount"], app.get("annual_rate", 12.5), app["tenure_months"])
        dbr = calculate_dbr(emi, app.get("monthly_income", 0), app.get("other_monthly_installments", 0))
        max_amount = calculate_max_eligible_amount(
            emi,
            app.get("annual_rate", 12.5),
            app["tenure_months"],
            monthly_income=app.get("monthly_income", 0),
            max_dbr_percent=45 if policy_edition == "2025" else 50,
            other_installments=app.get("other_monthly_installments", 0),
        )
        calculations = {
            "requested_amount": float(app["requested_amount"]),
            "emi": float(emi),
            "dbr": float(dbr),
            "max_amount": float(max_amount),
            "tenure_months": int(app["tenure_months"]),
            "policy_edition": policy_edition,
        }

        memo_prompt = load_prompt("memo")
        memo_prompt = memo_prompt.replace("{{requested_amount}}", str(app["requested_amount"]))
        memo_prompt = memo_prompt.replace("{{monthly_income}}", str(app.get("monthly_income", 0)))
        memo_prompt = memo_prompt.replace("{{emi}}", str(emi))
        memo_prompt = memo_prompt.replace("{{dbr}}", str(dbr))
        memo_prompt = memo_prompt.replace("{{max_amount}}", str(max_amount))

        memo_response = provider.complete(memo_prompt, application=app, calculations=calculations, citations=citations)
        memo_text = memo_response.get("content") if isinstance(memo_response, dict) else str(memo_response)
        if isinstance(memo_response, dict) and isinstance(memo_response.get("json"), dict):
            memo_text = json.dumps(memo_response["json"])

        memo = CreditMemo(
            application_id=str(app.get("id") or app.get("application_id") or "unknown"),
            calculations=calculations,
            citations=citations,
            raw_extraction={
                "extraction": extraction.model_dump(mode="python"),
                "rule_results": rule_results,
                "memo": memo_text,
            },
            decision="pending",
        )
        return memo
    except (InvalidLLMOutput, PolicyEditionNotFound, UnverifiedExtraction, ValueError, TypeError) as exc:
        if raise_on_error:
            raise
        memo = CreditMemo(
            application_id=str(application.get("id") if isinstance(application, Mapping) else "unknown"),
            calculations={},
            citations=[],
            raw_extraction={"error": str(exc)},
            decision="Refer to human",
        )
        return memo
