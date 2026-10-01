from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

PROTECTED = {"gender", "religion", "marital_status", "nationality"}


def anonymize_application(payload: dict[str, Any]) -> dict[str, Any]:
    """Remove protected attributes from a dict representing an application."""
    out = dict(payload)
    stripped: list[str] = []
    for field in PROTECTED:
        if field in out:
            out.pop(field)
            stripped.append(field)
    if stripped:
        logger.info(
            "Protected attributes stripped before LLM use: %s",
            ", ".join(sorted(stripped)),
        )
    return out


def sanitize_for_llm(payload: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Strip protected data and mask identifiers from every LLM-bound text field."""
    out = anonymize_application(payload)
    removed = sorted(PROTECTED & set(payload))
    documents = dict(out.get("documents") or {})
    patterns = (
        r"(?im)^\s*(Gender|Marital status|Religion|Nationality)\s+.*$",
        r"\b\d{14}\b",
        r"\b01\d[- ]?\d{4}[- ]?\d{4}\b",
    )
    cleaned: dict[str, str] = {}
    for name, text in documents.items():
        value = str(text)
        value = re.sub(patterns[0], "", value)
        value = re.sub(patterns[1], "[NATIONAL_ID_MASKED]", value)
        value = re.sub(patterns[2], "[PHONE_MASKED]", value)
        cleaned[name] = value
    out["documents"] = cleaned
    if removed:
        logger.info("Protected attributes removed from pack: %s", ", ".join(removed))
    return out, removed
