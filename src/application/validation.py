from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime, timezone
from typing import Any

from src.domain.exceptions import InvalidApplication, PolicyEditionNotFound

REQUIRED_APPLICATION_FIELDS = {
    "requested_amount",
    "tenure_months",
    "date_of_birth",
    "application_date",
}


def _parse_date(value: Any) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        cleaned = value.strip()
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
            try:
                return datetime.strptime(cleaned, fmt).replace(tzinfo=timezone.utc).date()
            except ValueError:
                continue
    raise InvalidApplication(f"Invalid date value: {value!r}")


def load_application(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    """Validate a minimal application payload and return a normalized dict."""
    if not isinstance(payload, Mapping):
        raise InvalidApplication("Application payload must be a mapping.")

    normalized: dict[str, Any] = dict(payload)
    missing = sorted(REQUIRED_APPLICATION_FIELDS - set(normalized))
    if missing:
        raise InvalidApplication(f"Missing required application fields: {', '.join(missing)}")

    normalized["requested_amount"] = float(normalized["requested_amount"])
    if normalized["requested_amount"] <= 0:
        raise InvalidApplication("requested_amount must be > 0")

    tenure = normalized["tenure_months"]
    if isinstance(tenure, str):
        tenure = int(float(tenure))
    if not isinstance(tenure, int) or tenure <= 0:
        raise InvalidApplication("tenure_months must be a positive integer")
    normalized["tenure_months"] = tenure

    normalized["date_of_birth"] = _parse_date(normalized["date_of_birth"])
    normalized["application_date"] = _parse_date(normalized["application_date"])

    if normalized["application_date"] < normalized["date_of_birth"]:
        raise InvalidApplication("application_date cannot be earlier than date_of_birth")

    normalized.setdefault("annual_rate", 12.5)
    normalized.setdefault("monthly_income", 0.0)
    normalized.setdefault("other_monthly_installments", 0.0)
    normalized.setdefault("bureau_score", 700)
    normalized.setdefault("months_employed", 12)

    return normalized


def select_policy_edition(application_date: Any) -> str:
    """Return the policy edition active for the supplied application date."""
    app_date = _parse_date(application_date)
    if app_date >= date(2025, 3, 1):
        return "2025"
    if app_date >= date(2024, 8, 1):
        return "2024"
    raise PolicyEditionNotFound("No policy edition exists for the supplied application date")


def select_policy_edition_for_date(application_date: Any) -> str:
    return select_policy_edition(application_date)
