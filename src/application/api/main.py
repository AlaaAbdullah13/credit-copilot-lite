from fastapi import Depends, FastAPI, HTTPException

from src.application.approval import ApprovalEngine
from src.application.auth import enforce_authority_limit, require_role
from src.application.pipeline import run_assessment
from src.domain.exceptions import AuthorityLimitExceeded
from src.infrastructure.db.models import User
from src.infrastructure.db.sql import SessionLocal

credit_officer_dep = require_role("credit_officer")
loan_officer_dep = require_role("loan_officer")

app = FastAPI(title="Credit Copilot Lite")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ingest")
def ingest():
    return {"status": "ingested"}


@app.post("/assess")
def assess(payload: dict):
    memo = run_assessment(payload.get("application", {}), payload.get("policy", {}))
    return memo.dict()


@app.post("/approve", dependencies=[Depends(credit_officer_dep)])
def approve(payload: dict):
    amount = float(payload.get("amount", 0))
    actor_role = str(payload.get("actor_role", "credit_officer"))
    actor_limit = payload.get("authority_limit")
    try:
        enforce_authority_limit(amount, actor_role=actor_role, authority_limit=actor_limit)
    except AuthorityLimitExceeded as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    application_id = payload.get("application_id")
    actor_id = payload.get("actor_id")
    if application_id and actor_id:
        with SessionLocal() as session:
            engine = ApprovalEngine(session)
            actor = session.get(User, actor_id)
            if actor is None:
                raise HTTPException(status_code=404, detail="Unknown actor")
            record = engine.approve(
                application_id,
                actor.id,
                justification=payload.get("comment", "Approved by credit officer."),
                amount=amount,
            )
            return {"status": "approved", "amount": amount, "approval_id": record.id}
    return {"status": "approved", "amount": amount}
