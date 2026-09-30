"""Authenticated API; Alembic, never application startup, owns schema creation."""

import os
import uuid

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from src.application.anonymizer import PROTECTED
from src.application.auth import (
    enforce_authority_limit,
    hash_password,
    issue_token,
    require_role,
    verify_password,
)
from src.application.pipeline import run_assessment
from src.application.validation import load_application, select_policy_edition
from src.domain.exceptions import (
    AuthorityLimitExceeded,
    InvalidApplication,
    InvalidLLMOutput,
    PolicyEditionNotFound,
    PolicySourceUnavailable,
    PricingNotFound,
    UnverifiedExtraction,
)
from src.infrastructure.db.models import (
    Application,
    ApprovalRecord,
    AssessmentRun,
    User,
)
from src.infrastructure.db.sql import SessionLocal
from src.infrastructure.ingestion.pipeline import ingest_documents, query_policy
from src.infrastructure.llm.provider_factory import create_llm_provider
from src.infrastructure.vector_store.chroma_adapter import ChromaAdapter

app = FastAPI(title="Credit Copilot Lite")
staff = require_role("loan_officer", "credit_officer")
credit = require_role("credit_officer")
# The persistent Chroma client is deliberately lazy: import/reload of the API
# (as done by offline tests) must not open a database or trigger embedding work.
_store: ChromaAdapter | None = None
_seeded = False
_ingest_report: dict = {}


def get_store() -> ChromaAdapter:
    global _seeded, _ingest_report, _store
    if _store is None:
        _store = ChromaAdapter(embedding_provider=create_llm_provider())
    if not _seeded:
        _ingest_report = ingest_documents(
            [
                "data/policy/circular-2024-07.md",
                "data/policy/circular-2025-02.md",
                "data/policy/product-sheet-personal-loan.md",
                "data/policy/pricing-table.csv",
                "data/policy/credit-policy-2024.pdf",
                "data/policy/credit-policy-2025.pdf",
                "data/policy/credit-procedures-manual.pdf",
            ],
            store=_store,
        )
        _seeded = True
    return _store


@app.exception_handler(InvalidApplication)
@app.exception_handler(PolicyEditionNotFound)
@app.exception_handler(UnverifiedExtraction)
@app.exception_handler(InvalidLLMOutput)
@app.exception_handler(AuthorityLimitExceeded)
@app.exception_handler(PricingNotFound)
@app.exception_handler(PolicySourceUnavailable)
async def named_error(_: Request, exc: Exception):
    status_codes = {
        AuthorityLimitExceeded: 403,
        PolicyEditionNotFound: 404,
        PolicySourceUnavailable: 503,
    }
    content = {"error": type(exc).__name__, "detail": str(exc)}
    if isinstance(exc, (PricingNotFound, PolicySourceUnavailable)):
        content["result"] = "Refer to human"
    return JSONResponse(status_code=status_codes.get(type(exc), 422), content=content)


def seed_demo_users() -> None:
    """Create or refresh the documented demo accounts from environment passwords."""
    accounts = (
        ("loan_officer", "loan_officer", "LOAN_OFFICER_PASSWORD", 0.0),
        (
            "credit_officer",
            "credit_officer",
            "CREDIT_OFFICER_PASSWORD",
            float(os.getenv("CREDIT_OFFICER_AUTHORITY_LIMIT", "250000")),
        ),
    )
    passwords = {
        password_variable: os.getenv(password_variable)
        for _, _, password_variable, _ in accounts
    }
    missing = [name for name, password in passwords.items() if not password]
    if missing:
        raise RuntimeError(
            "Required demo-user password environment variable(s) missing: "
            + ", ".join(missing)
        )

    with SessionLocal() as db:
        for username, role, password_variable, authority_limit in accounts:
            password = passwords[password_variable]
            user = db.query(User).filter(User.username == username).one_or_none()
            if user is None:
                db.add(
                    User(
                        username=username,
                        role=role,
                        authority_limit=authority_limit,
                        password_hash=hash_password(password),
                    )
                )
            elif not verify_password(password, user.password_hash):
                user.password_hash = hash_password(password)
        db.commit()


@app.post("/login")
def login(payload: dict):
    username, password = payload.get("username"), payload.get("password")
    if not username or not password:
        raise HTTPException(400, "username and password are required")
    with SessionLocal() as db:
        user = db.query(User).filter(User.username == username).one_or_none()
        if user is None or not verify_password(password, user.password_hash):
            raise HTTPException(401, "Invalid username or password")
        return {
            "token": issue_token(user.username, user.role, user.authority_limit),
            "role": user.role,
            "username": user.username,
        }


@app.post("/ingest")
def ingest(_: dict = Depends(staff)):
    get_store()
    return {"status": "ingested", **_ingest_report}


@app.post("/query")
def query(payload: dict, _: dict = Depends(staff)):
    if not payload.get("question"):
        raise InvalidApplication("question is required")
    return query_policy(
        payload["question"],
        store=get_store(),
        policy_edition=payload.get("policy_edition"),
        threshold=0.40,
        k=3,
    )


@app.post("/assess")
def assess(payload: dict, user: dict = Depends(staff)):
    raw, normalized = (
        payload.get("application", {}),
        load_application(payload.get("application", {})),
    )
    memo, request_id = (
        run_assessment(raw, payload.get("policy", {}), store=get_store()),
        str(uuid.uuid4()),
    )
    with SessionLocal() as db:
        owner = db.query(User).filter(User.username == user["sub"]).one()
        app_id = str(
            normalized.get("id") or normalized.get("application_id") or uuid.uuid4()
        )
        application = Application(
            id=app_id,
            owner_id=owner.id,
            requested_amount=normalized["requested_amount"],
            tenure_months=normalized["tenure_months"],
            monthly_income=normalized["monthly_income"],
            other_monthly_installments=normalized["other_monthly_installments"],
            date_of_birth=normalized["date_of_birth"],
            application_date=normalized["application_date"],
            policy_edition=select_policy_edition(normalized["application_date"]),
            status="pending_approval",
            decision_reason=memo.decision,
        )
        db.merge(application)
        run = AssessmentRun(
            application_id=app_id,
            request_id=request_id,
            policy_edition=application.policy_edition,
            steps_executed=[
                "validate",
                "anonymize",
                "extract",
                "retrieve",
                "rules",
                "calculate",
                "memo",
                "recommend",
            ],
            chunk_ids=[c.get("chunk_id") for c in memo.citations if c.get("chunk_id")],
            removed_fields=sorted(PROTECTED & set(raw)),
            tokens_consumed=_tokens_consumed(memo),
            token_usage=memo.raw_extraction.get("token_usage", {}),
            status="pending_approval",
        )
        db.add(run)
        db.commit()
        db.refresh(run)
    result = memo.model_dump()
    result.update(
        {"run_id": run.id, "request_id": request_id, "status": "pending_approval"}
    )
    return result


def _tokens_consumed(memo) -> int:
    """Persist usage reported by the LLM adapter, never an API-side estimate."""
    return int(memo.raw_extraction.get("tokens_consumed", 0))


def _transition(payload: dict, user: dict, decision: str):
    if not payload.get("application_id"):
        raise InvalidApplication("application_id is required")
    with SessionLocal() as db:
        application, actor = (
            db.get(Application, payload["application_id"]),
            db.query(User).filter(User.username == user["sub"]).one(),
        )
        if application is None:
            raise HTTPException(404, "Application not found")
        if application.status != "pending_approval":
            raise HTTPException(
                409, "Only pending applications can be approved or rejected"
            )
        amount = float(payload.get("amount", application.requested_amount))
        if decision == "Approved":
            enforce_authority_limit(amount, actor.authority_limit)
        application.status = decision.lower()
        application.decision_reason = payload.get("comment")
        db.add(
            ApprovalRecord(
                application_id=application.id,
                approver_id=actor.id,
                decision=decision,
                comment=payload.get("comment"),
                amount=amount,
            )
        )
        db.commit()
        return {"application_id": application.id, "status": application.status}


@app.post("/approve")
def approve(payload: dict, user: dict = Depends(credit)):
    return _transition(payload, user, "Approved")


@app.post("/reject")
def reject(payload: dict, user: dict = Depends(credit)):
    return _transition(payload, user, "Rejected")


@app.post("/issue")
def issue(payload: dict, _: dict = Depends(credit)):
    with SessionLocal() as db:
        application = db.get(Application, payload.get("application_id"))
        if application is None:
            raise HTTPException(404, "Application not found")
        if application.status != "approved":
            raise HTTPException(409, "Only Approved applications can become Issued")
        application.status = "issued"
        db.commit()
        return {"application_id": application.id, "status": application.status}
