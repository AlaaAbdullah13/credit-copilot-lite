from __future__ import annotations

import logging
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
