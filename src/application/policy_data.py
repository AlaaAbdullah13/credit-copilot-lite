"""Deterministic readers for the provided policy artefacts."""
import re
import subprocess
from csv import DictReader
from decimal import Decimal
from pathlib import Path

from src.domain.exceptions import PolicySourceUnavailable, PricingNotFound

POLICY_DIR = Path(__file__).resolve().parents[2] / "data" / "policy"


def load_annual_rate(tenor_months: int, segment: str) -> Decimal:
    with (POLICY_DIR / "pricing-table.csv").open(encoding="utf-8", newline="") as handle:
        for row in DictReader(handle):
            if row["segment"] == segment and int(row["tenor_from_months"]) <= tenor_months <= int(row["tenor_to_months"]):
                return Decimal(row["annual_rate_percent"])
    raise PricingNotFound(f"No pricing row for tenor {tenor_months} and segment {segment!r}")


def load_product_limits() -> dict[str, int]:
    text = (POLICY_DIR / "product-sheet-personal-loan.md").read_text(encoding="utf-8")
    values = [int(value.replace(",", "")) for value in re.findall(r"\| (?:Minimum|Maximum) (?:loan amount|tenor) \| EGP ([\d,]+)|\| (?:Minimum|Maximum) tenor \| (\d+)", text) for value in value if value]
    return dict(zip(("min_amount", "max_amount", "min_tenor", "max_tenor"), values, strict=True))


def load_credit_policy_limits(edition: str) -> dict[str, int]:
    policy_path = POLICY_DIR / f"credit-policy-{edition}.pdf"
    try:
        result = subprocess.run(
            ["pdftotext", "-layout", str(policy_path), "-"],
            check=True, capture_output=True, text=True,
        )
    except FileNotFoundError as exc:
        raise PolicySourceUnavailable("pdftotext is required to load policy limits") from exc
    text = result.stdout
    patterns = {
        "max_dbr": r"must not exceed (\d+)%",
        "min_employment_months": r"At least (\d+) months with the",
        "max_age_at_maturity": r"Maximum age at maturity\s+(\d+) years",
        "min_bureau_score": r"Score (\d+) and above",
        "min_income": r"Minimum net monthly\s+EGP ([\d,]+)",
    }
    limits = {
        key: Decimal(re.search(pattern, text).group(1).replace(",", ""))
        if key == "min_income" else int(re.search(pattern, text).group(1))
        for key, pattern in patterns.items() if re.search(pattern, text)
    }
    limits["max_dbr"] = Decimal(limits["max_dbr"]) / Decimal(100)
    if len(limits) != len(patterns):
        raise ValueError(f"Could not load all limits for policy edition {edition}")
    return limits
