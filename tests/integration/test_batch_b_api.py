"""Batch B API regressions: every database starts at the Alembic head."""

from __future__ import annotations

import asyncio
import importlib
from pathlib import Path

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect

from alembic import command
from src.application.pipeline import run_assessment
from src.domain.exceptions import (
    AuthorityLimitExceeded,
    InvalidApplication,
    InvalidLLMOutput,
    PolicyEditionNotFound,
    PolicySourceUnavailable,
    PricingNotFound,
    UnverifiedExtraction,
)
from src.infrastructure.llm.fake_adapter import FakeLLMAdapter
from src.infrastructure.vector_store.chroma_adapter import ChromaAdapter

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def api_client(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'api.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("AUTH_TOKEN_SECRET", "test-token-secret")
    monkeypatch.setenv("LOAN_OFFICER_PASSWORD", "loan-password")
    monkeypatch.setenv("CREDIT_OFFICER_PASSWORD", "credit-password")
    monkeypatch.setenv("LLM_PROVIDER", "fake")

    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")

    from src.application import auth
    from src.infrastructure.db import sql

    importlib.reload(sql)
    importlib.reload(auth)
    from src.application.api import main

    importlib.reload(main)
    main.seed_demo_users()
    with TestClient(main.app) as client:
        yield client, main


def test_upgrade_head_creates_all_four_workflow_tables(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'empty.db'}"
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")
    assert {"users", "applications", "assessment_runs", "approval_records"} <= set(
        inspect(create_engine(database_url)).get_table_names()
    )


def _login(client, username, password, **extra):
    return client.post(
        "/login", json={"username": username, "password": password, **extra}
    )


@pytest.fixture
def tokens(api_client):
    client, _ = api_client
    loan = _login(client, "loan_officer", "loan-password").json()["token"]
    credit = _login(client, "credit_officer", "credit-password").json()["token"]
    return {
        "loan": {"Authorization": f"Bearer {loan}"},
        "credit": {"Authorization": f"Bearer {credit}"},
    }


def test_protected_endpoints_enforce_authentication_and_roles(api_client, tokens):
    client, _ = api_client
    payloads = {
        "/ingest": {},
        "/query": {"question": "What is the minimum income?"},
        "/assess": {"application": application("API-roles")},
        "/approve": {"application_id": "missing"},
        "/reject": {"application_id": "missing"},
        "/issue": {"application_id": "missing"},
    }
    for endpoint, payload in payloads.items():
        assert client.post(endpoint, json=payload).status_code == 401
    for endpoint in ("/ingest", "/query", "/assess"):
        assert (
            client.post(
                endpoint, json=payloads[endpoint], headers=tokens["loan"]
            ).status_code
            < 400
        )
    for endpoint in ("/approve", "/reject", "/issue"):
        assert (
            client.post(
                endpoint, json=payloads[endpoint], headers=tokens["loan"]
            ).status_code
            == 403
        )
        assert (
            client.post(
                endpoint, json=payloads[endpoint], headers=tokens["credit"]
            ).status_code
            == 404
        )


def test_login_uses_stored_role_not_role_claim(api_client):
    client, _ = api_client
    response = _login(client, "loan_officer", "loan-password", role="credit_officer")
    assert response.status_code == 200
    assert response.json()["role"] == "loan_officer"
    assert (
        client.post(
            "/approve",
            json={"application_id": "missing"},
            headers={"Authorization": f"Bearer {response.json()['token']}"},
        ).status_code
        == 403
    )


def test_wrong_password_is_unauthorized(api_client):
    client, _ = api_client
    assert _login(client, "loan_officer", "wrong").status_code == 401


def application(application_id, **overrides):
    data = {
        "id": application_id,
        "requested_amount": 200000,
        "tenure_months": 60,
        "monthly_income": 30000,
        "other_monthly_installments": 0,
        "date_of_birth": "1990-01-01",
        "application_date": "2025-04-15",
        "months_employed": 24,
        "bureau_score": 700,
        "documents": {
            "application-form": "Requested amount: 200000 EGP\nTenor: 60 months\nDate of birth: 1990-01-01\nApplication date: 2025-04-15\nMonthly income: 30000 EGP\nObligations: 0 EGP\nEmployment start: 2020-01-01\nBureau score: 700"
        },
    }
    data.update(overrides)
    data["documents"] = {
        "application-form": (
            f"Requested amount: {data['requested_amount']} EGP\n"
            f"Tenor: {data['tenure_months']} months\n"
            f"Date of birth: {data['date_of_birth']}\n"
            f"Application date: {data['application_date']}\n"
            f"Monthly income: {data['monthly_income']} EGP\n"
            f"Obligations: {data['other_monthly_installments']} EGP\n"
            "Employment start: 2020-01-01\n"
            f"Bureau score: {data['bureau_score']}"
        )
    }
    return data


def assess(client, headers, application_id="API-001", **overrides):
    response = client.post(
        "/assess",
        json={"application": application(application_id, **overrides)},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_authority_limit_rejects_and_does_not_persist_approval(api_client, tokens):
    client, main = api_client
    assess(client, tokens["loan"], "API-limit", requested_amount=300000)
    response = client.post(
        "/approve",
        json={"application_id": "API-limit", "amount": 300000},
        headers=tokens["credit"],
    )
    assert response.status_code == 403
    assert response.json()["error"] == "AuthorityLimitExceeded"
    with main.SessionLocal() as db:
        assert db.get(main.Application, "API-limit").status == "pending_approval"
        assert db.query(main.ApprovalRecord).count() == 0


def test_lifecycle_pending_to_approved_to_issued_stores_audit_fields(
    api_client, tokens
):
    client, main = api_client
    assess(client, tokens["loan"], "API-life")
    assert (
        client.post(
            "/issue", json={"application_id": "API-life"}, headers=tokens["credit"]
        ).status_code
        == 409
    )
    approved = client.post(
        "/approve",
        json={"application_id": "API-life", "comment": "verified"},
        headers=tokens["credit"],
    )
    assert approved.json()["status"] == "approved"
    assert (
        client.post(
            "/issue", json={"application_id": "API-life"}, headers=tokens["credit"]
        ).json()["status"]
        == "issued"
    )
    with main.SessionLocal() as db:
        record = db.query(main.ApprovalRecord).one()
        assert record.approver_id and record.created_at and record.comment == "verified"
    assess(client, tokens["loan"], "API-rejected")
    assert (
        client.post(
            "/reject", json={"application_id": "API-rejected"}, headers=tokens["credit"]
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/issue", json={"application_id": "API-rejected"}, headers=tokens["credit"]
        ).status_code
        == 409
    )


@pytest.mark.parametrize(
    ("application_id", "overrides", "decision"),
    [
        ("APP-001", {}, "approve"),
        ("APP-002", {"monthly_income": 10000}, "decline"),
        ("APP-003", {"date_of_birth": "1958-01-01"}, "decline"),
        ("APP-005", {"bureau_score": 500}, "refer to human"),
    ],
)
def test_real_application_pack_decisions_are_persisted(
    api_client, tokens, application_id, overrides, decision
):
    client, _ = api_client
    result = assess(client, tokens["loan"], application_id, **overrides)
    assert result["decision"] == decision
    assert result["status"] == "pending_approval"
    assert result["run_id"]
    assert "approval_required_from" in result


def test_assessment_run_persists_pipeline_audit_data(api_client, tokens):
    client, main = api_client
    result = assess(client, tokens["loan"], "API-audit", gender="female")
    with main.SessionLocal() as db:
        run = db.get(main.AssessmentRun, result["run_id"])
        assert run.request_id == result["request_id"]
        assert run.steps_executed and run.chunk_ids
        assert run.policy_edition == "2025"
        assert run.removed_fields == ["gender"]
        assert run.tokens_consumed > 0


def test_populated_policy_store_yields_chunk_ids_and_rule_citations(tmp_path):
    """Step 5 must preserve store IDs and cite every deterministic rule."""
    store = ChromaAdapter(persist_directory=str(tmp_path / "policy-store"))
    memo = run_assessment(
        application("APP-001"), llm=FakeLLMAdapter(), store=store, raise_on_error=True
    )
    rules = memo.raw_extraction["rule_results"]
    assert memo.citations
    assert all(citation.get("chunk_id") for citation in memo.citations)
    assert all(
        rule.get("citation", {}).get("source_file")
        and rule["citation"].get("clause_id")
        and rule["citation"].get("policy_edition")
        for rule in rules
    )


@pytest.mark.parametrize(
    ("error", "expected_status"),
    [
        (InvalidApplication("bad payload"), 422),
        (InvalidLLMOutput("bad output"), 422),
        (UnverifiedExtraction("bad quote"), 422),
        (PolicyEditionNotFound("missing edition"), 404),
        (AuthorityLimitExceeded("too large"), 403),
        (PricingNotFound("no rate"), 422),
        (PolicySourceUnavailable("missing source"), 503),
    ],
)
def test_named_errors_map_to_expected_status_codes(error, expected_status):
    from src.application.api.main import named_error

    response = asyncio.run(named_error(None, error))
    assert response.status_code == expected_status
    if isinstance(error, (PricingNotFound, PolicySourceUnavailable)):
        assert b"Refer to human" in response.body
