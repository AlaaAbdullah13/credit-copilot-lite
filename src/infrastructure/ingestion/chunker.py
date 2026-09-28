from __future__ import annotations

import re
from pathlib import Path
from typing import Any


def _infer_policy_edition(source_file: str | None) -> str | None:
    if not source_file:
        return None
    match = re.search(r"(20\d{2})", Path(source_file).name)
    if match:
        return (
            f"CP-{match.group(1)}"
            if "credit-policy" in Path(source_file).name
            else None
        )
    return None


def chunk_by_clause(
    sections: list[dict[str, Any]] | None,
    source_file: str | None = None,
    policy_edition: str | None = None,
    effective_dates: str | None = None,
) -> list[dict[str, Any]]:
    if not sections:
        return []

    chunks: list[dict[str, Any]] = []
    file_name = source_file or sections[0].get("source_file")

    for index, section in enumerate(sections, start=1):
        text = str(section.get("text") or "").strip()
        if not text:
            continue

        section_id = str(
            section.get("id") or section.get("clause_id") or f"section-{index}"
        )
        heading = str(section.get("heading") or "").strip()
        if heading:
            text = f"{heading}\n{text}"

        metadata = {
            "source_file": section.get("source_file") or file_name,
            "page": section.get("page"),
            "clause_id": section_id,
            "policy_edition": section.get("policy_edition")
            or policy_edition
            or _infer_policy_edition(str(file_name)),
            "effective_dates": section.get("effective_dates") or effective_dates,
            "document_type": section.get("document_type"),
            "superseded": bool(section.get("superseded", False)),
        }

        chunks.append(
            {
                "id": section_id,
                "text": text,
                "metadata": metadata,
            }
        )

    return chunks
