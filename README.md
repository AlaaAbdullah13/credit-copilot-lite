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

Seed the policy documents (first run only):

```bash
docker compose run --rm seed
```

### Option B — Local (no Docker)

```bash
git clone https://github.com/AlaaAbdullah13/credit-copilot-lite.git
cd credit-copilot-lite
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # add your API key (or set LLM_PROVIDER=fake)
uvicorn src.application.api.main:app --reload --port 8000
```

Seed policy documents:

```bash
python -c "
import sys; sys.path.insert(0, '.')
from src.infrastructure.ingestion.pipeline import ingest_documents
ingest_documents(['data/policy/circular-2024-07.md', 'data/policy/credit-policy-2024.pdf'], policy_edition='2024')
ingest_documents(['data/policy/circular-2025-02.md', 'data/policy/credit-policy-2025.pdf'], policy_edition='2025')
ingest_documents(['data/policy/product-sheet-personal-loan.md', 'data/policy/pricing-table.csv', 'data/policy/credit-procedures-manual.pdf'], policy_edition=None)
print('Seeding complete.')
"
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

Authentication uses the `X-Role` request header (demo only — not for production).

| Account | Role | X-Role header value | Authority limit |
|---|---|---|---|
| ahmed | Loan Officer | `loan_officer` | Can submit, cannot approve |
| sara | Credit Officer | `credit_officer` | Up to EGP 250,000 |
| omar | Senior Credit Officer | `credit_officer` | Raise limit via `CREDIT_OFFICER_AUTHORITY_LIMIT` |

**Login example:**

```bash
curl -s -X POST http://localhost:8000/login \
  -H "Content-Type: application/json" \
  -d '{"username": "ahmed", "role": "loan_officer"}'
```

Use the returned role value as the `X-Role` header in subsequent requests.

---

## Running Tests

```bash
# All tests (unit + pipeline + integration)
pytest tests/ -v

# Linting
ruff check .

# Evaluation harness (15 test cases)
python src/cli/evaluate.py
```

Expected results:
- `pytest`: 14/14 passed
- `ruff`: no errors
- `evaluate.py`: 15/15 passed, 100% across all categories

---

## 5-Minute Demo Path

### Rebuild policy retrieval data

Policy PDF table chunking changed. Rebuild the persisted collection before
testing retrieval:

```bash
rm -rf data/chroma_db
python3 src/cli/calibrate_retrieval.py
```

Then start the API or call `POST /ingest`; it recreates `data/chroma_db` from
the policy sources. The calibration command prints the chosen threshold and
the reusable evaluation rows from `data/eval/retrieval_questions.json`.

Run these steps in order against a running server (`http://localhost:8000/docs` for Swagger UI).

**Step 1 — Ingest policy documents**
```bash
docker compose run --rm seed
# Expected: 35 chunks ingested, 0 failed
```

**Step 2 — Ask a policy question (cited answer)**
```bash
curl -s -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -H "X-Role: loan_officer" \
  -d '{"question": "What is the maximum debt burden ratio under the 2025 policy?"}'
# Expected: answer "45%" with citation to CP-2025 clause CP-4.1
```

**Step 3 — Ask an out-of-corpus question (correct refusal)**
```bash
curl -s -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -H "X-Role: loan_officer" \
  -d '{"question": "What is the bank policy on cryptocurrency-backed loans?"}'
# Expected: {"answer": "The documents do not contain enough information.", "reason": "no_chunk_above_threshold"}
```

**Step 4 — Same question, different policy editions**
```bash
curl -s -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -H "X-Role: loan_officer" \
  -d '{"question": "What is the maximum DBR?", "policy_edition": "2024"}'
# Expected: 50%

curl -s -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -H "X-Role: loan_officer" \
  -d '{"question": "What is the maximum DBR?", "policy_edition": "2025"}'
# Expected: 45%
```

**Step 5 — Assess application APP-001**
```bash
curl -s -X POST http://localhost:8000/assess \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"application_id": "APP-001"}'
# Expected: instalment 8630.39, DBR 42.10%, max eligible 330000, status pending_approval
```

**Step 6 — Prompt injection attempt (APP-004)**
```bash
curl -s -X POST http://localhost:8000/assess \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"application_id": "APP-004"}'
# Expected: extracted income = real figure (18,000), injection detected and referred
```

**Step 7 — Credit Officer approval (within limit)**
```bash
curl -s -X POST http://localhost:8000/approve \
  -H "Content-Type: application/json" \
  -H "X-Role: credit_officer" \
  -d '{"amount": 200000, "comment": "Documents verified."}'
# Expected: {"status": "approved", "amount": 200000}
```

**Step 8 — Approval above authority limit (server rejects)**
```bash
curl -s -X POST http://localhost:8000/approve \
  -H "Content-Type: application/json" \
  -H "X-Role: credit_officer" \
  -d '{"amount": 300000, "comment": "Approved."}'
# Expected: 403 "Amount EGP 300,000 exceeds authority limit EGP 250,000."
```

**Step 9 — Loan Officer cannot approve (wrong role)**
```bash
curl -s -X POST http://localhost:8000/approve \
  -H "Content-Type: application/json" \
  -H "X-Role: loan_officer" \
  -d '{"amount": 100000}'
# Expected: 403 "Insufficient role"
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
