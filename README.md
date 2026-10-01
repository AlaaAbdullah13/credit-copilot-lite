---

# Credit Copilot Lite

A grounded RAG assistant for personal loan underwriting at Delta Commercial Bank (fictional).
Ingests policy documents, answers policy questions with citations, and prepares credit
recommendations that a human credit officer approves or rejects.

---

## Quick Start

### Option A — Docker (recommended)

```bash
git clone https://github.com/AlaaAbdullah13/credit-copilot-lite.git
cd credit-copilot-lite
cp .env.example .env          # add your API key (or set LLM_PROVIDER=fake)
docker compose up             # starts the API on http://localhost:8000
```

`docker compose up` runs Alembic migrations and seeds the three demo users.
Seed policy documents on the first run:

```bash
docker compose run --rm seed
```

### Option B — Local (no Docker)

```bash
git clone https://github.com/AlaaAbdullah13/credit-copilot-lite.git
cd credit-copilot-lite
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # add your API key (or set LLM_PROVIDER=fake)
alembic upgrade head
python3 -m src.cli seed-users
uvicorn src.application.api.main:app --reload --port 8000
```

Seed policy documents:

```bash
python3 -m src.cli seed-policy
```

---

## Environment Variables

Copy `.env.example` to `.env` and fill in the values you need.

.env is loaded automatically; after changing demo passwords, recreate the DB or re-run seeding.

| Variable | Description | Default |
|---|---|---|
| `LLM_PROVIDER` | `gemini` / `groq` / `ollama` / `fake` | `gemini` |
| `GEMINI_API_KEY` | Gemini API key (if `LLM_PROVIDER=gemini`) | — |
| `GROQ_API_KEY` | Groq API key (if `LLM_PROVIDER=groq`) | — |
| `OLLAMA_BASE_URL` | Local Ollama server URL | `http://localhost:11434` |
| `EMBEDDING_MODEL_NAME` | Sentence-transformer model name | `all-MiniLM-L6-v2` |
| `DATABASE_URL` | SQLAlchemy database URL | `sqlite:///./credit_copilot.db` |
| `CHROMA_DB_DIR` | ChromaDB persistence directory | `./data/chroma_db` |
| `CREDIT_OFFICER_AUTHORITY_LIMIT` | Max EGP a credit officer may approve alone | `250000` |
| `LOAN_OFFICER_PASSWORD` | Password for `loan1` | — |
| `CREDIT_OFFICER_PASSWORD` | Password for `credit1` | — |
| `SENIOR_CREDIT_OFFICER_PASSWORD` | Password for `senior1` | — |
| `LOG_LEVEL` | Logging level | `INFO` |

> **Never commit `.env` to the repository.** It is listed in `.gitignore`.

---

## How to Get a Free API Key

| Provider | Steps |
|---|---|
| **Gemini** | Go to https://aistudio.google.com → Get API key → copy to `GEMINI_API_KEY` |
| **Groq** | Go to https://console.groq.com → API Keys → copy to `GROQ_API_KEY` |
| **Ollama (local)** | Install from https://ollama.com → `ollama pull llama3` → set `OLLAMA_BASE_URL=http://localhost:11434` |
| **No key (offline)** | Set `LLM_PROVIDER=fake` — pipeline runs without any external calls |

---

## Demo Accounts

Authenticate using `POST /login`; protected endpoints require its Bearer token.

| Account | Role | Authority limit |
|---|---|---:|
| `loan1` | Loan Officer | EGP 0; cannot approve |
| `credit1` | Credit Officer | EGP 250,000 |
| `senior1` | Credit Officer | EGP 1,000,000 |

**Login example:**

```bash
curl -s -X POST http://localhost:8000/login \
  -H "Content-Type: application/json" \
  -d '{"username": "loan1", "password": "YOUR_LOAN_OFFICER_PASSWORD"}'
```

Use the returned `token` as `Authorization: Bearer <token>` in subsequent requests.

---

## Running Tests

```bash
# All tests (unit + pipeline + integration)
pytest tests/ -v

# Linting
ruff check .

# Evaluation harness (15 test cases)
LLM_PROVIDER=fake python3 -m src.cli evaluate
```

Expected results:
- `pytest`: all collected tests passed
- `ruff`: no errors
- `python -m src.cli evaluate`: 15/15 passed, 100% across all categories

---

## 5-Minute Demo Path

### Rebuild policy retrieval data

Policy PDF table chunking changed. Rebuild the persisted collection before
testing retrieval:

```bash
rm -rf data/chroma_db
python3 -m src.cli calibrate
```

Then start the API or call `POST /ingest`; it recreates `data/chroma_db` from
the policy sources. The calibration command prints the chosen threshold and
the reusable evaluation rows from `data/eval/retrieval_questions.json`.

Run these steps in order against a running server (`http://localhost:8000/docs` for Swagger UI).

**Step 1 — Ingest policy documents**
```bash
docker compose run --rm seed
# or locally: python3 -m src.cli seed-policy
# Expected: chunks ingested, 0 failed
```

**Step 2 — Login as `loan1`**
```bash
LOAN_TOKEN=$(curl -s -X POST http://localhost:8000/login \
  -H "Content-Type: application/json" \
  -d '{"username":"loan1","password":"YOUR_LOAN_OFFICER_PASSWORD"}' | python3 -c 'import json,sys; print(json.load(sys.stdin)["token"])')
```

**Step 3 — Ask a cited question, then an out-of-corpus question**
```bash
curl -s -X POST http://localhost:8000/query -H "Authorization: Bearer $LOAN_TOKEN" -H "Content-Type: application/json" -d '{"question":"What percentage of net monthly income is the maximum debt burden ratio?","policy_edition":"CP-2025"}'
curl -s -X POST http://localhost:8000/query -H "Authorization: Bearer $LOAN_TOKEN" -H "Content-Type: application/json" -d '{"question":"What is the bank policy on cryptocurrency-backed loans?"}'
```

**Step 4 — Show the edition difference**
```bash
curl -s -X POST http://localhost:8000/query -H "Authorization: Bearer $LOAN_TOKEN" -H "Content-Type: application/json" -d '{"question":"What is the maximum loan tenor permitted by the regulator?","policy_edition":"CP-2024"}'
curl -s -X POST http://localhost:8000/query -H "Authorization: Bearer $LOAN_TOKEN" -H "Content-Type: application/json" -d '{"question":"What is the maximum loan tenor permitted by the regulator?","policy_edition":"CP-2025"}'
```

**Step 5 — Assess APP-001**
```bash
curl -s -X POST http://localhost:8000/assess \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $LOAN_TOKEN" \
  -d '{"application_id": "APP-001"}'
# Expected: instalment 8630.39, DBR 42.10%, max eligible 382000, status pending_approval
```

**Step 6 — Prompt injection attempt (APP-004)**
```bash
curl -s -X POST http://localhost:8000/assess \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $LOAN_TOKEN" \
  -d '{"application_id": "APP-004"}'
# Expected: extracted income = real figure (18,000), injection detected and referred
```

**Step 7 — `loan1` cannot approve (403)**
```bash
curl -s -X POST http://localhost:8000/approve \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $LOAN_TOKEN" \
  -d '{"application_id":"APP-001","comment":"Attempted by loan officer."}'
# Expected: 403
```

**Step 8 — `credit1` exceeds authority (403)**
```bash
TOKEN=$(curl -s -X POST http://localhost:8000/login -H "Content-Type: application/json" -d '{"username":"credit1","password":"YOUR_CREDIT_OFFICER_PASSWORD"}' | python3 -c 'import json,sys; print(json.load(sys.stdin)["token"])')
curl -s -X POST http://localhost:8000/approve \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"application_id":"APP-001","comment":"Authority check."}'
# Expected: 403 "Amount EGP 300,000 exceeds authority limit EGP 250,000."
```

**Step 9 — `senior1` approves and issues**
```bash
SENIOR_TOKEN=$(curl -s -X POST http://localhost:8000/login -H "Content-Type: application/json" -d '{"username":"senior1","password":"YOUR_SENIOR_CREDIT_OFFICER_PASSWORD"}' | python3 -c 'import json,sys; print(json.load(sys.stdin)["token"])')
curl -s -X POST http://localhost:8000/approve -H "Authorization: Bearer $SENIOR_TOKEN" -H "Content-Type: application/json" -d '{"application_id":"APP-001","comment":"Documents verified; approved."}'
curl -s -X POST http://localhost:8000/issue -H "Authorization: Bearer $SENIOR_TOKEN" -H "Content-Type: application/json" -d '{"application_id":"APP-001"}'
```

---

## Data Sent to the LLM Provider

The following data is sent to the external LLM provider (Gemini / Groq):

- **Policy Q&A:** retrieved policy document chunks (text only, no applicant data)
- **Step 4 extraction:** applicant salary certificate and bureau report text, with national ID numbers and phone numbers masked before sending
- **Step 7 memo drafting:** rule results and calculation outputs (no raw applicant text)

Applicant documents are always wrapped in `<untrusted_document>` tags and clearly separated from system instructions to prevent prompt injection.

No API keys, passwords, or raw applicant PDFs are sent to the LLM provider.

---

## Architecture

```
src/
├── domain/          # Pure Python — zero external dependencies
│   ├── calculations.py   # EMI, DBR, max eligible amount
│   ├── rules.py          # Eligibility rule checks
│   ├── exceptions.py     # Named domain exceptions
│   └── pipeline.py       # 8-step assessment orchestrator
├── infrastructure/  # All I/O
│   ├── llm/              # LLMAdapter interface + Gemini/Groq/Fake adapters
│   ├── vector_store/     # ChromaDB adapter (trusted + untrusted stores)
│   ├── ingestion/        # PDF/Markdown/CSV loaders + chunker
│   └── db/               # SQLAlchemy models + Alembic migrations
└── application/     # FastAPI routers, auth, pipeline wiring
    └── api/main.py
```

See `docs/DESIGN.md` for full architecture details, chunking rationale, and LLM provider switching instructions.

---

## Submission

- **Evaluation results:** `docs/EVALUATION.md` — 15/15 passed
- **Design decisions:** `docs/DESIGN.md`
- **AI usage log:** `docs/AI-USAGE-LOG.md`
