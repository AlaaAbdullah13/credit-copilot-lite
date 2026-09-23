from fastapi import FastAPI, Depends, HTTPException
from typing import Dict
import os

from src.application.auth import require_role, enforce_authority_limit
from src.application.pipeline import run_assessment

app = FastAPI(title="Credit Copilot Lite")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ingest")
def ingest():
    # Placeholder ingestion endpoint
    return {"status": "ingested"}


@app.post("/assess")
def assess(payload: Dict):
    try:
        memo = run_assessment(payload.get("application", {}), payload.get("policy", {}))
        return memo.dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/approve")
def approve(payload: Dict, _=Depends(require_role("credit_officer"))):
    amount = payload.get("amount", 0)
    enforce_authority_limit(amount)
    return {"status": "approved", "amount": amount}
