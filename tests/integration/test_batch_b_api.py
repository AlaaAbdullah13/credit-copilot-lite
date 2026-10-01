"""Batch B API regressions: every database starts at the Alembic head."""

from __future__ import annotations

import asyncio
import importlib
from datetime import date
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
    # Starlette 1.x's lifespan TestClient context currently blocks under the
    # Python 3.13/httpx 0.28 test stack.  These synchronous endpoints have no
    # startup/shutdown hooks, so avoid the unrelated lifespan protocol here.
    client = TestClient(main.app)
    try:
        yield client, main
    finally:
        client.close()


def test_upgrade_head_creates_all_four_workflow_tables(tmp_path, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
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


@pytest.fixture
def pending_application(api_client):
    _, main = api_client

    def create(application_id, amount=200000, recommendation="approve"):
        with main.SessionLocal() as db:
            owner = db.query(main.User).filter_by(username="loan_officer").one()
            db.add(
                main.Application(
                    id=application_id,
                    owner_id=owner.id,
                    requested_amount=amount,
                    tenure_months=60,
                    monthly_income=30000,
                    other_monthly_installments=0,
                    date_of_birth=date(1990, 1, 1),
                    application_date=date(2025, 4, 3),
                    policy_edition="2025",
                    recommended_amount=amount,
                    recommendation=recommendation,
                    status="pending_approval",
                )
            )
            db.commit()
        return application_id

    return create


def test_protected_endpoints_enforce_authentication_and_roles(api_client, tokens):
    client, _ = api_client
    payloads = {
        "/ingest": {},
        "/query": {"question": "What is the minimum income?"},
        "/assess": {"application_id": "APP-001"},
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


def test_openapi_documents_bearer_auth_and_typed_login(api_client):
    client, _ = api_client
    schema = client.get("/openapi.json").json()

    assert schema["components"]["securitySchemes"]["BearerAuth"] == {
        "type": "http",
        "description": "Paste the token returned by /login.",
        "scheme": "bearer",
        "bearerFormat": "JWT",
    }
    assert schema["paths"]["/approve"]["post"]["security"] == [{"BearerAuth": []}]
    assert schema["paths"]["/login"]["post"]["requestBody"]["content"][
        "application/json"
    ]["schema"]["$ref"].endswith("/LoginRequest")
    assess_schema = schema["components"]["schemas"]["AssessRequest"]
    assert "policy" not in assess_schema["properties"]


def test_assess_rejects_removed_client_policy_field(api_client, tokens):
    client, _ = api_client
    response = client.post(
        "/assess",
        json={"application": application("API-no-policy"), "policy": {"max_dbr": 1}},
        headers=tokens["loan"],
    )
    assert response.status_code == 422


@pytest.mark.parametrize(
    "payload",
    [
        {"application_id": "APP-001", "monthly_income": 999999},
        {"application_id": "APP-001", "requested_amount": 1},
        {"application_id": "APP-001", "application": {}},
    ],
)
def test_assess_rejects_client_supplied_numbers(api_client, tokens, payload):
    client, _ = api_client
    assert (
        client.post("/assess", json=payload, headers=tokens["loan"]).status_code == 422
    )


@pytest.mark.parametrize(
    "payload", [{"application_id": "APP-999"}, {}, {"application_id": ""}]
)
def test_assess_rejects_unknown_missing_or_empty_pack_id(api_client, tokens, payload):
    client, _ = api_client
    response = client.post("/assess", json=payload, headers=tokens["loan"])
    assert 400 <= response.status_code < 500


def test_query_uses_retrieval_environment_configuration(
    api_client, tokens, monkeypatch
):
    client, main = api_client
    observed = {}
    monkeypatch.setenv("RETRIEVAL_MIN_SCORE", "0.61")
    monkeypatch.setenv("RETRIEVAL_TOP_K", "7")

    def query_stub(question, **kwargs):
        observed.update(kwargs)
        return {"answer": "ok", "citations": [], "reason": "ok"}

    monkeypatch.setattr(main, "query_policy", query_stub)
    response = client.post(
        "/query", json={"question": "minimum income"}, headers=tokens["loan"]
    )
    assert response.status_code == 200
    assert observed["threshold"] == 0.61
    assert observed["k"] == 7


@pytest.mark.parametrize("edition", ["2025", "cp-2025", "CP-2025"])
def test_query_normalizes_policy_edition(api_client, tokens, monkeypatch, edition):
    client, main = api_client
    observed = {}

    def query_stub(question, **kwargs):
        observed.update(kwargs)
        return {"answer": "ok", "citations": [], "reason": "ok"}

    monkeypatch.setattr(main, "query_policy", query_stub)
    response = client.post(
        "/query",
        json={"question": "minimum income", "policy_edition": edition},
        headers=tokens["loan"],
    )
    assert response.status_code == 200
    assert observed["policy_edition"] == "CP-2025"


def test_query_unknown_policy_edition_has_named_4xx_error(api_client, tokens):
    client, _ = api_client
    response = client.post(
        "/query",
        json={"question": "minimum income", "policy_edition": "CP-2099"},
        headers=tokens["loan"],
    )
    assert response.status_code == 404
    assert response.json()["error"] == "PolicyEditionNotFound"


def test_demo_seed_refreshes_passwords_and_login_rejects_old_password(
    api_client, monkeypatch
):
    client, main = api_client
    monkeypatch.setenv("LOAN_OFFICER_PASSWORD", "refreshed-loan-password")
    main.seed_demo_users()

    assert _login(client, "loan_officer", "refreshed-loan-password").status_code == 200
    assert _login(client, "loan_officer", "loan-password").status_code == 401


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


def assess(client, headers, application_id="APP-001"):
    response = client.post(
        "/assess",
        json={"application_id": application_id},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_authority_limit_rejects_and_does_not_persist_approval(
    api_client, tokens, pending_application
):
    client, main = api_client
    pending_application("API-limit", 300000)
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


@pytest.mark.parametrize(
    ("application_id", "requested_amount", "expected_status"),
    [
        ("API-limit-bypass", 300000, 403),
        ("API-limit-exact", 250000, 200),
        ("API-limit-over", 250001, 403),
    ],
)
def test_approval_uses_stored_recommendation_not_client_amount(
    api_client,
    tokens,
    pending_application,
    application_id,
    requested_amount,
    expected_status,
):
    client, _ = api_client
    pending_application(application_id, requested_amount)
    response = client.post(
        "/approve",
        json={"application_id": application_id, "amount": 100000},
        headers=tokens["credit"],
    )
    assert response.status_code == expected_status
    if expected_status == 403:
        assert response.json()["error"] == "AuthorityLimitExceeded"


def test_lifecycle_pending_to_approved_to_issued_stores_audit_fields(
    api_client, tokens, pending_application
):
    client, main = api_client
    pending_application("API-life")
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
            "/approve", json={"application_id": "API-life"}, headers=tokens["credit"]
        ).status_code
        == 409
    )
    assert (
        client.post(
            "/issue", json={"application_id": "API-life"}, headers=tokens["credit"]
        ).json()["status"]
        == "issued"
    )
    with main.SessionLocal() as db:
        record = db.query(main.ApprovalRecord).one()
        assert record.approver_id and record.created_at and record.comment == "verified"
    pending_application("API-rejected")
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


@pytest.mark.parametrize("recommendation", ["decline", "refer to human"])
def test_non_approvable_recommendation_cannot_be_approved(
    api_client, tokens, pending_application, recommendation
):
    client, _ = api_client
    application_id = f"API-{recommendation.replace(' ', '-')}"
    pending_application(application_id, recommendation=recommendation)
    response = client.post(
        "/approve", json={"application_id": application_id}, headers=tokens["credit"]
    )
    assert response.status_code == 409


def test_reassessing_decided_application_conflicts_without_resetting_status(
    api_client, tokens
):
    client, main = api_client
    assess(client, tokens["loan"], "APP-001")
    with main.SessionLocal() as db:
        db.get(main.Application, "APP-001").status = "approved"
        db.commit()
    response = client.post(
        "/assess",
        json={"application_id": "APP-001"},
        headers=tokens["loan"],
    )
    assert response.status_code == 409
    with main.SessionLocal() as db:
        assert db.get(main.Application, "APP-001").status == "approved"


def test_real_assessment_above_authority_limit_cannot_be_approved(api_client, tokens):
    client, _ = api_client
    assess(client, tokens["loan"], "APP-001")
    response = client.post(
        "/approve", json={"application_id": "APP-001"}, headers=tokens["credit"]
    )
    assert response.status_code == 403
    assert response.json()["error"] == "AuthorityLimitExceeded"


@pytest.mark.parametrize(
    ("application_id", "decision"),
    [
        ("APP-001", "approve"),
        ("APP-002", "decline"),
        ("APP-003", "decline"),
        ("APP-004", "refer to human"),
        ("APP-005", "refer to human"),
    ],
)
def test_real_application_pack_decisions_are_persisted(
    api_client, tokens, application_id, decision
):
    client, main = api_client
    result = assess(client, tokens["loan"], application_id)
    assert result["decision"] == decision
    assert result["status"] == "pending_approval"
    assert result["run_id"]
    assert "approval_required_from" in result
    with main.SessionLocal() as db:
        assert db.get(main.Application, application_id).recommendation == decision
        assert (
            db.get(main.AssessmentRun, result["run_id"]).application_id
            == application_id
        )


def test_assessment_run_persists_pipeline_audit_data(api_client, tokens):
    client, main = api_client
    result = assess(client, tokens["loan"], "APP-001")
    with main.SessionLocal() as db:
        run = db.get(main.AssessmentRun, result["run_id"])
        assert run.request_id == result["request_id"]
        assert run.steps_executed and run.chunk_ids
        assert run.policy_edition == "2025"
        assert run.removed_fields == [
            "gender",
            "marital_status",
            "nationality",
            "religion",
        ]
        assert run.tokens_consumed > 0


def test_invalid_extraction_persists_stopped_pipeline_steps(
    api_client, tokens, monkeypatch
):
    client, main = api_client

    class BrokenLLMAdapter(FakeLLMAdapter):
        def complete(self, prompt, **kwargs):
            return {"content": "{not valid json"}

    monkeypatch.setattr(
        main,
        "run_assessment",
        lambda application, **kwargs: run_assessment(
            application, llm=BrokenLLMAdapter(), **kwargs
        ),
    )
    result = assess(client, tokens["loan"], "APP-001")
    assert result["decision"] == "refer to human"
    with main.SessionLocal() as db:
        run = db.get(main.AssessmentRun, result["run_id"])
        assert run.steps_executed == ["validate", "anonymize", "extract"]


def test_populated_policy_store_yields_chunk_ids_and_rule_citations(tmp_path):
    """Step 5 must preserve store IDs and cite every deterministic rule."""
    store = ChromaAdapter(
        persist_directory=str(tmp_path / "policy-store"),
        embedding_provider=FakeLLMAdapter(),
    )
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
