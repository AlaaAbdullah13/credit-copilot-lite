from __future__ import annotations

import csv
import re
import subprocess
from pathlib import Path
from typing import Any


def _read_text_file(path: str) -> str:
    file_path = Path(path)
    try:
        return file_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def infer_policy_edition(path: str | Path | None) -> str | None:
    if path is None:
        return None
    file_name = str(path)
    match = re.search(r"(20\d{2})", file_name)
    if match:
        return match.group(1)
    return None


def parse_markdown(path: str) -> list[dict[str, Any]]:
    text = _read_text_file(path)
    if not text.strip():
        return []

    sections: list[dict[str, Any]] = []
    blocks = re.split(r"(?m)^(?=#+\s)", text)

    if len(blocks) == 1:
        sections.append(
            {
                "id": "root",
                "heading": "document",
                "text": text.strip(),
                "source_file": path,
            }
        )
        return sections

    for index, block in enumerate(blocks, start=1):
        block = block.strip()
        if not block:
            continue

        heading_match = re.match(r"^(#+)\s+(.*)$", block, re.MULTILINE)
        heading = (
            heading_match.group(2).strip() if heading_match else f"section-{index}"
        )
        body = re.sub(r"^#+\s+.*\n?", "", block, count=1).strip()
        if not body:
            body = heading

        sections.append(
            {
                "id": heading_match.group(2).strip()
                if heading_match
                else f"section-{index}",
                "heading": heading,
                "text": body,
                "source_file": path,
                "policy_edition": infer_policy_edition(path),
            }
        )

    return sections


def parse_csv(path: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    csv_path = Path(path)
    if not csv_path.exists():
        return rows

    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for index, row in enumerate(reader, start=1):
            row_text = " ".join(
                f"{key}: {value}"
                for key, value in row.items()
                if value is not None and str(value).strip()
            )
            rows.append(
                {
                    "id": row.get("document_id") or row.get("id") or f"row-{index}",
                    "text": row_text,
                    "source_file": path,
                    "policy_edition": infer_policy_edition(path),
                    "row": row,
                }
            )

    return rows


def _extract_pdf_pages_with_library(path: str) -> list[str] | None:
    try:
        from pypdf import PdfReader
        from pypdf.errors import PdfReadError
    except ImportError:
        return None

    try:
        reader = PdfReader(path)
        pages: list[str] = []
        for page in reader.pages:
            page_text = page.extract_text() or ""
            if page_text.strip():
                pages.append(page_text.strip())
        return pages
    except (OSError, TypeError, ValueError, PdfReadError):
        return None


def parse_pdf(path: str) -> list[dict[str, Any]]:
    pdf_path = Path(path)
    if not pdf_path.exists():
        return []

    try:
        result = subprocess.run(
            ["pdftotext", "-layout", str(pdf_path), "-"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        result = None

    raw_text = ""
    if result is not None and result.returncode == 0:
        raw_text = result.stdout

    if not raw_text.strip():
        library_pages = _extract_pdf_pages_with_library(path)
        if library_pages is None:
            return []
        raw_text = "\f".join(library_pages)

    pages = raw_text.split("\f") if "\f" in raw_text else [raw_text]
    sections: list[dict[str, Any]] = []

    clause_pattern = re.compile(r"(?m)^\s*(?P<id>(?:CP|PM)-\d+(?:\.\d+)?)\.?(?:\s|$)")
    for page_index, page_text in enumerate(pages, start=1):
        cleaned = page_text.strip()
        if not cleaned:
            continue
        matches = list(clause_pattern.finditer(cleaned))
        if not matches:
            sections.append(
                {
                    "id": f"page-{page_index}",
                    "text": cleaned,
                    "source_file": path,
                    "page": page_index,
                    "policy_edition": infer_policy_edition(path),
                }
            )
            continue
        # Preserve a cover-page preamble but split every numbered policy/manual
        # clause.  This deliberately avoids arbitrary fixed-size chunks.
        if matches[0].start() > 0:
            sections.append(
                {
                    "id": f"page-{page_index}-preamble",
                    "text": cleaned[: matches[0].start()].strip(),
                    "source_file": path,
                    "page": page_index,
                    "policy_edition": infer_policy_edition(path),
                }
            )
        for index, match in enumerate(matches):
            end = (
                matches[index + 1].start() if index + 1 < len(matches) else len(cleaned)
            )
            text = cleaned[match.start() : end].strip()
            sections.append(
                {
                    "id": match.group("id"),
                    "text": text,
                    "source_file": path,
                    "page": page_index,
                    "policy_edition": infer_policy_edition(path),
                }
            )

    return sections


def parse_document(path: str) -> list[dict[str, Any]]:
    suffix = Path(path).suffix.lower()

    if suffix == ".md":
        return parse_markdown(path)
    if suffix == ".csv":
        return parse_csv(path)
    if suffix == ".pdf":
        return parse_pdf(path)
    return parse_markdown(path) if suffix in {".txt", ".rst"} else []
