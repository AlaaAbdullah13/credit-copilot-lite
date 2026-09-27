import os

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.application.auth import enforce_authority_limit, require_role
from src.application.pipeline import run_assessment
from src.domain.exceptions import AuthorityLimitExceeded
from src.infrastructure.ingestion.pipeline import ingest_documents, query_policy
from src.infrastructure.vector_store.chroma_adapter import ChromaAdapter

credit_officer_dep = require_role("credit_officer")

app = FastAPI(title="Credit Copilot Lite")

# Shared vector store (ingested once at startup)
_store = ChromaAdapter()
_seeded = False


def get_store() -> ChromaAdapter:
    global _seeded
    if not _seeded:
        policy_files = [
            (["data/policy/circular-2024-07.md", "data/policy/credit-policy-2024.pdf"], "2024"),
            (["data/policy/circular-2025-02.md", "data/policy/credit-policy-2025.pdf"], "2025"),
            (["data/policy/product-sheet-personal-loan.md",
              "data/policy/pricing-table.csv",
              "data/policy/credit-procedures-manual.pdf"], None),
        ]
        for files, edition in policy_files:
            ingest_documents(files, store=_store, policy_edition=edition)
        _seeded = True
    return _store


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/login")
def login(payload: dict):
    role = payload.get("role", "")
    username = payload.get("username", "")
    if not role or not username:
        raise HTTPException(status_code=400, detail="username and role required")
    valid_roles = {"loan_officer", "credit_officer"}
    if role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"role must be one of {valid_roles}")
    return {
        "username": username,
        "role": role,
        "token": role,
        "instructions": f"Pass 'X-Role: {role}' header in subsequent requests.",
    }


@app.post("/ingest")
def ingest():
    store = get_store()
    return {"status": "ingested", "chunks": len(store._memory_docs)}


@app.post("/query")
def query(payload: dict):
    question = payload.get("question", "")
    edition = payload.get("policy_edition", None)
    if not question:
        raise HTTPException(status_code=400, detail="question is required")
    store = get_store()
    result = query_policy(question, store=store, policy_edition=edition, threshold=0.40, k=3)
    return result


@app.post("/assess")
def assess(payload: dict):
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


# Serve frontend
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/")
    def frontend():
        return FileResponse(os.path.join(static_dir, "index.html"))
