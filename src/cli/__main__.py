"""Unified CLI: python -m src.cli <command>

Commands:
  seed-users   Seed demo users (loan1, credit1, senior1)
  seed-apps    Seed synthetic application packs into the untrusted store
  seed-policy  Ingest trusted policy documents into ChromaDB
  evaluate     Run the 15-question evaluation harness
  calibrate    Calibrate retrieval thresholds offline
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

POLICY_RUNS: list[tuple[list[str], str | None]] = [
    (
        [
            "data/policy/circular-2024-07.md",
            "data/policy/credit-policy-2024.pdf",
        ],
        "2024",
    ),
    (
        [
            "data/policy/circular-2025-02.md",
            "data/policy/credit-policy-2025.pdf",
        ],
        "2025",
    ),
    (
        [
            "data/policy/product-sheet-personal-loan.md",
            "data/policy/pricing-table.csv",
            "data/policy/credit-procedures-manual.pdf",
        ],
        None,
    ),
]


def _cmd_seed_users(_: argparse.Namespace) -> int:
    from src.cli.seed_users import main as seed_users_main

    seed_users_main()
    return 0


def _cmd_seed_apps(_: argparse.Namespace) -> int:
    from src.cli.seed_applications import main as seed_apps_main

    seed_apps_main()
    return 0


def _cmd_seed_policy(_: argparse.Namespace) -> int:
    from src.infrastructure.ingestion.pipeline import ingest_documents

    total_chunks = 0
    for files, edition in POLICY_RUNS:
        result = ingest_documents(files, policy_edition=edition)
        total_chunks += int(result.get("chunks_ingested", 0))
        print(result)
    print(f"Seeding complete. Total chunks ingested: {total_chunks}")
    return 0


def _cmd_evaluate(_: argparse.Namespace) -> int:
    from src.cli.evaluate import evaluate

    summary = evaluate()
    print(json.dumps(summary, indent=2, default=str))
    print("\n" + "=" * 50)
    print("EVALUATION SUMMARY")
    print("=" * 50)
    print(
        f"Total:                {summary['total_passed']}/{summary['total_cases']} passed"
    )
    print(f"Retrieval hit-rate:   {summary['retrieval_hit_rate']:.0%}  (k=3)")
    print(f"Refusal correctness:  {summary['refusal_correctness']:.0%}")
    print(f"Calculation exactness:{summary['calculation_exactness']:.0%}")
    print(f"Differential accuracy:{summary['differential_accuracy']:.0%}")
    print(f"Injection resistance: {summary['injection_resistance']:.0%}")
    print("=" * 50)
    print("\nPer-case results:")
    for row in summary["results"]:
        status = "✅ PASS" if row["passed"] else "❌ FAIL"
        print(f"  {row['id']} [{row['kind']:16s}] {status} — {row['description']}")
    return 0 if summary["total_passed"] == summary["total_cases"] else 1


def _cmd_calibrate(_: argparse.Namespace) -> int:
    from src.cli.calibrate_retrieval import calibrate

    calibrate()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m src.cli",
        description="Credit Copilot Lite CLI",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("seed-users", help="Seed demo users after migrations").set_defaults(
        func=_cmd_seed_users
    )
    sub.add_parser(
        "seed-apps", help="Seed synthetic application packs into untrusted store"
    ).set_defaults(func=_cmd_seed_apps)
    sub.add_parser(
        "seed-policy", help="Ingest trusted policy documents into ChromaDB"
    ).set_defaults(func=_cmd_seed_policy)
    sub.add_parser(
        "evaluate", help="Run the 15-question evaluation harness"
    ).set_defaults(func=_cmd_evaluate)
    sub.add_parser(
        "calibrate", help="Calibrate retrieval thresholds with FakeLLMAdapter"
    ).set_defaults(func=_cmd_calibrate)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
