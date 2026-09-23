

from fastapi import Depends, FastAPI, HTTPException

from src.application.auth import enforce_authority_limit, require_role
from src.application.pipeline import run_assessment
from src.domain.exceptions import AuthorityLimitExceeded

# Create module-level dependency call to satisfy lint (avoid calling require_role in defaults)
credit_officer_dep = require_role("credit_officer")

app = FastAPI(title="Credit Copilot Lite")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ingest")
def ingest():
    # Placeholder ingestion endpoint
    return {"status": "ingested"}


@app.post("/assess")
def assess(payload: dict):
    # Only handle known domain errors here; let unexpected errors propagate
    memo = run_assessment(payload.get("application", {}), payload.get("policy", {}))
    return memo.dict()


@app.post("/approve", dependencies=[Depends(credit_officer_dep)])
def approve(payload: dict):
    amount = payload.get("amount", 0)
    try:
        enforce_authority_limit(amount)
    except AuthorityLimitExceeded as e:
        raise HTTPException(status_code=403, detail=str(e))
    return {"status": "approved", "amount": amount}
