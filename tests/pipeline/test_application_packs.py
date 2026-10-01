from __future__ import annotations

import pytest

from src.application.pipeline import run_assessment
from src.infrastructure.ingestion.application_packs import load_application_pack
from src.infrastructure.llm.fake_adapter import FakeLLMAdapter


@pytest.mark.parametrize(
    ("application_id", "decision", "rules"),
    [
        ("APP-001", "approve", {"debt_burden_ratio": "pass"}),
        ("APP-002", "decline", {"debt_burden_ratio": "fail"}),
        ("APP-003", "decline", {"age_at_maturity": "fail"}),
        ("APP-004", "refer to human", {"prompt_injection_detected": "refer"}),
        ("APP-005", "refer to human", {"bureau_score": "refer"}),
    ],
)
def test_seeded_pack_outcomes(application_id, decision, rules):
    memo = run_assessment(load_application_pack(application_id), llm=FakeLLMAdapter())
    actual = {
        item["rule"]: item["status"] for item in memo.raw_extraction["rule_results"]
    }
    assert memo.calculations["policy_edition"] == "CP-2025"
    assert memo.decision == decision
    assert rules.items() <= actual.items()


def test_app_001_uses_verified_evidence_for_calculation():
    memo = run_assessment(load_application_pack("APP-001"), llm=FakeLLMAdapter())
    assert memo.calculations["emi"] == 8630.39
    assert memo.calculations["dbr"] == 0.421
    assert memo.calculations["max_amount"] == 330000.0
    assert memo.citations and memo.raw_extraction["rule_results"]


def test_llm_input_is_sanitized(monkeypatch):
    received = []
    original = FakeLLMAdapter.complete

    def capture(self, prompt, **kwargs):
        received.append(prompt)
        return original(self, prompt, **kwargs)

    monkeypatch.setattr(FakeLLMAdapter, "complete", capture)
    pack = load_application_pack("APP-001")
    run_assessment(pack, llm=FakeLLMAdapter())
    llm_text = "\n".join(received)
    assert pack["national_id"] not in llm_text
    assert pack["phone"] not in llm_text
    assert pack["gender"] not in llm_text
    assert pack["nationality"] not in llm_text
