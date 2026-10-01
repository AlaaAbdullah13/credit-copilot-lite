"""Measure trusted-policy retrieval separation with the offline fake provider.

Usage: python3 src/cli/calibrate_retrieval.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.infrastructure.ingestion.pipeline import (
    _has_meaningful_term,
    ingest_documents,
)
from src.infrastructure.llm.fake_adapter import FakeLLMAdapter
from src.infrastructure.vector_store.chroma_adapter import ChromaAdapter

POLICY_FILES = [
    "data/policy/circular-2024-07.md",
    "data/policy/circular-2025-02.md",
    "data/policy/product-sheet-personal-loan.md",
    "data/policy/pricing-table.csv",
    "data/policy/credit-policy-2024.pdf",
    "data/policy/credit-policy-2025.pdf",
    "data/policy/credit-procedures-manual.pdf",
]


def calibrate() -> dict[str, object]:
    questions = json.loads(
        (PROJECT_ROOT / "data/eval/retrieval_questions.json").read_text(
            encoding="utf-8"
        )
    )
    store = ChromaAdapter(
        persist_directory=str(PROJECT_ROOT / ".tmp-calibration-chroma"),
        embedding_provider=FakeLLMAdapter(),
    )
    ingest_documents(POLICY_FILES, store=store)
    rows = []
    for item in questions:
        hits = store.query(
            item["question"], k=1, policy_edition=item.get("policy_edition")
        )
        hit = hits[0] if hits else None
        score = float(hit["score"]) if hit else 0.0
        grounded = bool(hit and _has_meaningful_term(item["question"], hit))
        rows.append({**item, "score": score, "grounded": grounded})
    in_scores = [row["score"] for row in rows if row["expected"] == "in"]
    out_scores = [row["score"] for row in rows if row["expected"] == "out"]
    min_in, max_out = min(in_scores), max(out_scores)
    midpoint = round((min_in + max_out) / 2, 4)
    overlap = max_out >= min_in
    suggested = round(min_in, 4) if overlap else midpoint
    print("question | expected | top score | result at chosen threshold")
    for row in rows:
        accepted = row["score"] >= suggested and row["grounded"]
        result = "accepted" if accepted else "refused"
        print(f"{row['question']} | {row['expected']} | {row['score']:.4f} | {result}")
    refused_in = [
        row["question"]
        for row in rows
        if row["expected"] == "in"
        and not (row["score"] >= suggested and row["grounded"])
    ]
    print(f"min in-corpus score: {min_in:.4f}")
    print(f"max out-of-corpus score: {max_out:.4f}")
    print(f"score midpoint: {midpoint:.4f}")
    print(f"suggested threshold: {suggested:.4f}")
    print(f"second guard used: {'yes (ranges overlap)' if overlap else 'no'}")
    print("in-corpus questions refused: " + (", ".join(refused_in) or "none"))
    return {
        "rows": rows,
        "threshold": suggested,
        "overlap": overlap,
        "refused_in": refused_in,
    }


if __name__ == "__main__":
    calibrate()
