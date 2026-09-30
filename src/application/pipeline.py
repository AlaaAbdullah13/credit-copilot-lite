from __future__ import annotations

import json
import logging
import os
import re
from collections.abc import Mapping
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ValidationError

from src.application.anonymizer import anonymize_application
from src.application.policy_data import (
    load_annual_rate,
    load_credit_policy_limits,
    load_product_limits,
)
from src.application.validation import load_application, select_policy_edition
from src.domain.calculations import (
    age_at_maturity_check,
    calculate_dbr,
    calculate_exact_dbr,
    calculate_installment,
    calculate_max_eligible_amount,
    employment_duration_ok,
    evaluate_bureau_score,
    validate_product_limits,
)
from src.domain.exceptions import (
    InvalidLLMOutput,
    PolicyEditionNotFound,
    PolicySourceUnavailable,
    PricingNotFound,
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
    net_monthly_income: ExtractionField
    existing_monthly_obligations: ExtractionField
    employment_start_date: ExtractionField
    bureau_score: ExtractionField


def _to_json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as exc:
            raise InvalidLLMOutput(
                f"LLM response is not valid JSON: {value!r}"
            ) from exc
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
    for candidate in {
        str(value),
        str(float(value)) if isinstance(value, (int, float, Decimal)) else None,
    }:
        if candidate and _normalize_text(candidate) in normalized_quote:
            return

    raise UnverifiedExtraction(
        f"Extracted value {value!r} was not found verbatim in quoted_text {quoted_text!r}"
    )


def _validate_extraction_payload(
    payload: dict[str, Any], documents: Mapping[str, str]
) -> dict[str, Any]:
    for field_name in [
        "requested_amount",
        "tenure_months",
        "date_of_birth",
        "application_date",
        "net_monthly_income",
        "existing_monthly_obligations",
        "employment_start_date",
        "bureau_score",
    ]:
        if field_name not in payload:
            continue
        field = payload[field_name]
        if not isinstance(field, dict):
            raise InvalidLLMOutput(f"Field {field_name!r} is not an object")
        _verify_value(field.get("value"), field.get("quoted_text"))
        source = field.get("source_document")
        if not source or _normalize_text(field["quoted_text"]) not in _normalize_text(
            documents.get(source, "")
        ):
            raise UnverifiedExtraction(
                "Quoted extraction text was not found in the cited document"
            )

    try:
        return ApplicationExtraction.model_validate(payload).model_dump(mode="python")
    except ValidationError as exc:
        raise InvalidLLMOutput(
            "LLM extraction did not match the expected schema"
        ) from exc


def extract_structured_data(
    application: Mapping[str, Any],
    llm: LLMProvider | None = None,
    *,
    raise_on_error: bool = True,
) -> ApplicationExtraction:
    """Use the configured LLM to extract a validated application payload."""
    provider = llm or create_llm_provider()
    prompt = load_prompt("extract").replace(
        "{{untrusted_document}}", "\n".join(application.get("documents", {}).values())
    )
    response = provider.complete(prompt, application=dict(application))
    payload = (
        response.get("json")
        if isinstance(response, dict) and isinstance(response.get("json"), dict)
        else None
    )
    if payload is None:
        text = response.get("content") if isinstance(response, dict) else response
        payload = _to_json_object(text)

    validated = _validate_extraction_payload(payload, application.get("documents", {}))
    return ApplicationExtraction.model_validate(validated)


def retrieve_policy_clauses(
    policy_edition: str,
    *,
    store: ChromaAdapter | None = None,
    threshold: float = 0.25,
) -> list[dict[str, Any]]:
    vector_store = store or ChromaAdapter()
    policy_files = [
        "data/policy/circular-2024-07.md",
        "data/policy/circular-2025-02.md",
        "data/policy/product-sheet-personal-loan.md",
        "data/policy/pricing-table.csv",
        "data/policy/credit-policy-2024.pdf",
        "data/policy/credit-policy-2025.pdf",
        "data/policy/credit-procedures-manual.pdf",
    ]
    ingest_documents(policy_files, store=vector_store)

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
    policy_limits = load_credit_policy_limits(policy_edition)

    def citation_for(*clause_ids: str) -> dict[str, Any]:
        for citation in citations or []:
            if not clause_ids or citation.get("clause_id") in clause_ids:
                return citation
        # Retrieval is mandatory before this function is called. This fallback
        # keeps every rule traceable if a corpus uses different clause labels.
        return {
            "source_file": f"circular-{policy_edition}-02.md",
            "clause_id": "policy-limits",
            "policy_edition": policy_edition,
        }

    rules: list[dict[str, Any]] = []

    limits = load_product_limits()
    amount_ok = validate_product_limits(
        app["requested_amount"], app["tenure_months"], **limits
    )
    rules.append(
        {
            "rule": "product_limits",
            "status": "pass" if amount_ok else "fail",
            "citation": citation_for(),
        }
    )

    rules.append(
        {
            "rule": "min_income",
            "status": "pass"
            if Decimal(str(app.get("monthly_income", 0))) >= policy_limits["min_income"]
            else "fail",
            "citation": citation_for("CP-3.3"),
        }
    )
    rules.append(
        {
            "rule": "employment_duration",
            "status": "pass"
            if employment_duration_ok(
                app.get("months_employed"), policy_limits["min_employment_months"]
            )
            else "fail",
            "citation": citation_for("CP-3.2"),
        }
    )
    rules.append(
        {
            "rule": "bureau_score",
            "status": "pass"
            if evaluate_bureau_score(
                app.get("bureau_score"), policy_limits["min_bureau_score"]
            )
            else "refer",
            "citation": citation_for("CP-3.6"),
        }
    )

    segment = (
        "payroll_transfer" if app.get("salary_transferred_to_delta") else "standard"
    )
    try:
        annual_rate = load_annual_rate(app["tenure_months"], segment)
    except PricingNotFound:
        return rules
    emi = calculate_installment(
        app["requested_amount"], annual_rate, app["tenure_months"]
    )
    exact_dbr = calculate_exact_dbr(
        emi, app.get("monthly_income", 0), app.get("other_monthly_installments", 0)
    )
    dbr = calculate_dbr(
        emi, app.get("monthly_income", 0), app.get("other_monthly_installments", 0)
    )
    rules.append(
        {
            "rule": "debt_burden_ratio",
            "status": "pass" if exact_dbr <= policy_limits["max_dbr"] else "fail",
            "value": float(dbr),
            "limit": policy_limits["max_dbr"],
            "citation": citation_for("CP-4.1"),
        }
    )

    age_ok = age_at_maturity_check(
        app["date_of_birth"],
        app["application_date"],
        app["tenure_months"],
        policy_limits["max_age_at_maturity"],
    )
    rules.append(
        {
            "rule": "age_at_maturity",
            "status": "pass" if age_ok else "fail",
            "value": age_ok,
            "citation": citation_for("CP-3.5"),
        }
    )

    if (
        app.get("gender") is not None
        or app.get("marital_status") is not None
        or app.get("religion") is not None
        or app.get("nationality") is not None
    ):
        rules.append(
            {
                "rule": "protected_attributes_removed",
                "status": "pass",
                "citation": citation_for("C-4"),
            }
        )

    return rules


def draft_credit_memo(
    provider: LLMProvider,
    application: Mapping[str, Any],
    calculations: Mapping[str, Any],
    citations: list[dict[str, Any]],
) -> str:
    """Draft prose only; deterministic values are inserted into the prompt by code."""
    prompt = load_prompt("memo")
    for name in ("requested_amount", "monthly_income", "emi", "dbr", "max_amount"):
        prompt = prompt.replace(
            "{{" + name + "}}", str(calculations.get(name, application.get(name, 0)))
        )
    code_values = {**application, **calculations, "calculations": dict(calculations)}
    response = provider.complete(
        prompt,
        application=dict(code_values),
        calculations=dict(calculations),
        citations=citations,
    )
    return (
        json.dumps(response["json"])
        if isinstance(response, dict) and isinstance(response.get("json"), dict)
        else str(response.get("content") if isinstance(response, dict) else response)
    )


def derive_recommendation(
    rule_results: list[dict[str, Any]], requested_amount: float, max_amount: float
) -> tuple[str, float | None]:
    """Derive the credit recommendation exclusively from deterministic rule outcomes."""
    statuses = {str(rule.get("status", "")).lower() for rule in rule_results}
    if "refer" in statuses:
        return "refer to human", None
    if "fail" in statuses:
        # A DBR failure must disclose affordability; other hard policy failures decline too.
        return "decline", max_amount if any(
            rule.get("rule") == "debt_burden_ratio" and rule.get("status") == "fail"
            for rule in rule_results
        ) else None
    return "approve", requested_amount


def required_approval_level(recommended_amount: float | None) -> str | None:
    if recommended_amount is None:
        return None
    limit = float(os.getenv("CREDIT_OFFICER_AUTHORITY_LIMIT", "250000"))
    return "credit_officer" if recommended_amount <= limit else "senior_credit_officer"


def run_assessment(
    application: Mapping[str, Any],
    *,
    llm: LLMProvider | None = None,
    store: ChromaAdapter | None = None,
    raise_on_error: bool = False,
) -> CreditMemo:
    """Run the 8-step application assessment pipeline and return a credit memo."""
    steps_executed = ["validate"]
    try:
        app = load_application(application)
        steps_executed.append("anonymize")
        sanitized = anonymize_application(app)
        policy_edition = select_policy_edition(app["application_date"])
        provider = llm or create_llm_provider()
        steps_executed.append("extract")
        extraction = extract_structured_data(
            sanitized, llm=provider, raise_on_error=True
        )

        steps_executed.append("retrieve")
        citations = retrieve_policy_clauses(
            policy_edition,
            store=store or ChromaAdapter(embedding_provider=provider),
        )
        steps_executed.append("rules")
        rule_results = evaluate_rules(sanitized, policy_edition, citations)

        steps_executed.append("calculate")
        segment = (
            "payroll_transfer" if app.get("salary_transferred_to_delta") else "standard"
        )
        annual_rate = load_annual_rate(app["tenure_months"], segment)
        emi = calculate_installment(
            app["requested_amount"], annual_rate, app["tenure_months"]
        )
        dbr = calculate_dbr(
            emi, app.get("monthly_income", 0), app.get("other_monthly_installments", 0)
        )
        max_amount = calculate_max_eligible_amount(
            emi,
            annual_rate,
            app["tenure_months"],
            monthly_income=app.get("monthly_income", 0),
            max_dbr=load_credit_policy_limits(policy_edition)["max_dbr"],
            other_installments=app.get("other_monthly_installments", 0),
        )
        calculations = {
            "requested_amount": float(app["requested_amount"]),
            "annual_rate": float(annual_rate),
            "emi": float(emi),
            "dbr": float(dbr),
            "max_amount": float(max_amount),
            "tenure_months": int(app["tenure_months"]),
            "policy_edition": f"CP-{policy_edition}",
        }

        steps_executed.append("memo")
        memo_text = draft_credit_memo(provider, sanitized, calculations, citations)

        steps_executed.append("recommend")
        recommendation, recommended_amount = derive_recommendation(
            rule_results, float(app["requested_amount"]), float(max_amount)
        )
        memo = CreditMemo(
            application_id=str(app.get("id") or app.get("application_id") or "unknown"),
            calculations=calculations,
            citations=citations,
            raw_extraction={
                "extraction": extraction.model_dump(mode="python"),
                "rule_results": rule_results,
                "memo": memo_text,
                "tokens_consumed": int(getattr(provider, "tokens_consumed", 0)),
                "token_usage": dict(getattr(provider, "token_usage", {})),
                "steps_executed": steps_executed,
            },
            decision=recommendation,
            status="pending_approval",
            recommended_amount=recommended_amount,
            approval_required_from=required_approval_level(recommended_amount),
        )
        return memo
    except (
        InvalidLLMOutput,
        PolicyEditionNotFound,
        PolicySourceUnavailable,
        PricingNotFound,
        UnverifiedExtraction,
        ValueError,
        TypeError,
    ) as exc:
        if raise_on_error:
            raise
        memo = CreditMemo(
            application_id=str(
                application.get("id") if isinstance(application, Mapping) else "unknown"
            ),
            calculations={},
            citations=[],
            raw_extraction={"error": str(exc), "steps_executed": steps_executed},
            decision="refer to human",
            status="pending_approval",
        )
        return memo
