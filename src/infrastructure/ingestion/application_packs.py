"""Parsing and loading of untrusted, seeded application packs."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.domain.exceptions import InvalidApplication
from src.infrastructure.ingestion.parser import parse_document
from src.infrastructure.vector_store.untrusted_application_store import (
    UntrustedApplicationStore,
)

PACKS_DIR = Path("data/applications")


def _value(text: str, label: str) -> str:
    match = re.search(rf"{re.escape(label)}\s+(.+)", text)
    if not match:
        raise InvalidApplication(f"Application form is missing {label!r}")
    return match.group(1).strip()


def _date(value: str) -> str:
    try:
        return (
            datetime.strptime(value, "%d %B %Y")
            .replace(tzinfo=timezone.utc)
            .date()
            .isoformat()
        )
    except ValueError as exc:
        raise InvalidApplication(f"Invalid application form date: {value!r}") from exc


def _number(value: str) -> float:
    match = re.search(r"[\d,]+(?:\.\d+)?", value)
    if not match:
        raise InvalidApplication(f"Invalid numeric application form value: {value!r}")
    return float(match.group(0).replace(",", ""))


def load_application_pack(application_id: str) -> dict[str, Any]:
    if not re.fullmatch(r"APP-00[1-5]", application_id):
        raise InvalidApplication(
            "application_id must identify a seeded pack (APP-001 to APP-005)"
        )
    sections = parse_document(str(PACKS_DIR / f"{application_id}.pdf"))
    by_id = {section["id"]: section["text"] for section in sections}
    form = by_id.get("application-form", "")
    if not form:
        raise InvalidApplication(f"Application form missing from {application_id}")
    return {
        "id": application_id,
        "application_id": application_id,
        "requested_amount": _number(_value(form, "Requested amount")),
        "tenure_months": int(_number(_value(form, "Requested tenor"))),
        "date_of_birth": _date(_value(form, "Date of birth")),
        "application_date": _date(_value(form, "Application date")),
        # Evidence values are populated only after quote-verified extraction.
        "monthly_income": 1.0,
        "other_monthly_installments": 0.0,
        "salary_transferred_to_delta": _value(
            form, "Salary transferred to Delta"
        ).lower()
        == "yes",
        "gender": _value(form, "Gender"),
        "marital_status": _value(form, "Marital status"),
        "religion": _value(form, "Religion"),
        "nationality": _value(form, "Nationality"),
        "national_id": _value(form, "National ID (synthetic)"),
        "phone": _value(form, "Mobile"),
        "documents": by_id,
    }


def seed_application_packs(store: UntrustedApplicationStore) -> dict[str, int]:
    """Idempotently seed packs into the dedicated untrusted collection."""
    chunks: list[dict[str, Any]] = []
    for path in sorted(PACKS_DIR.glob("APP-*.pdf")):
        for section in parse_document(str(path)):
            chunks.append(
                {
                    "id": f"{path.stem}:{section['id']}",
                    "text": section["text"],
                    "metadata": {
                        "source_file": str(path),
                        "clause_id": section["id"],
                        "document_type": "untrusted_application",
                    },
                }
            )
    inserted = store.add_documents(chunks)
    return {
        "packs": 5,
        "chunks_inserted": inserted,
        "chunks_skipped": store.last_add_counts["skipped"],
    }
