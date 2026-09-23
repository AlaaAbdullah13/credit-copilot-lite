# Credit Copilot Lite — A Grounded RAG Assistant for Personal Loan Underwriting

A small, auditable retrieval-augmented generation (RAG) assistant to support personal loan underwriting decisions. It combines a document ingestion and vector search pipeline with guarded LLM adapters to produce grounded answers, calculation-backed assessments, and role-based approval flows.

## Quick Start

Prerequisites
- Python 3.11 or newer
- Git
- (Optional) Docker for running local vector stores or Ollama

Clone the repo

```
git clone https://github.com/your-org/credit-copilot-lite.git
cd credit-copilot-lite
```

Create and activate a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
# Install project dependencies if a requirements file exists
pip install -r requirements.txt || true
```

Environment

```
cp .env.example .env
# Edit .env to add provider keys and any local paths
```

Run the application (example)

If the project exposes a FastAPI app, you can run it with Uvicorn:

```
uvicorn app.main:app --reload --port ${PORT:-8000}
```

Or run the project's entrypoint as documented by the project.

## Environment Variables

Create `.env` from `.env.example` and populate provider keys and paths. Keys included in `.env.example`:

- `ENV` — runtime environment (development|production)
- `PORT` — HTTP port (default 8000)
- `LOG_LEVEL` — logging level (INFO, DEBUG, etc.)
- `LLM_PROVIDER` — one of: `gemini`, `groq`, `ollama`, `fake`
- `GEMINI_API_KEY` — API key for Gemini (set if `LLM_PROVIDER=gemini`)
- `GROQ_API_KEY` — API key for Groq (set if `LLM_PROVIDER=groq`)
- `OLLAMA_BASE_URL` — base URL for a local Ollama server (e.g. `http://localhost:11434`)
- `EMBEDDING_MODEL_NAME` — embedding model id (e.g. `all-MiniLM-L6-v2`)
- `DATABASE_URL` — SQL database URL (e.g. `sqlite:///./credit_copilot.db`)
- `VECTOR_DB_TYPE` — vector DB backend (e.g. `chroma` or `qdrant`)
- `CHROMA_DB_DIR` — filesystem path for Chroma DB (if used)
- `CREDIT_OFFICER_AUTHORITY_LIMIT` — numeric authority cap (e.g. `250000`)

Populate only the keys relevant to your chosen adapters. Keep secrets out of source control.

## How to get a free API key / Local setup

- Gemini: Sign up for Google Cloud/Vertex AI and follow the Gemini API onboarding; a free tier or trial credits are often available. Save the key to `GEMINI_API_KEY`.
- Groq: Register for Groq Cloud and obtain an API key; set it in `GROQ_API_KEY`.
- Ollama (local): Install Ollama on your machine (or via Docker) and run a local model server. Set `OLLAMA_BASE_URL` to the server address (default `http://localhost:11434`). Ollama allows local model usage without a cloud API key.

If you do not have API access during development, use `LLM_PROVIDER=fake` to exercise the pipeline without external requests.

## Demo Accounts & Roles

The repository includes role-aware checks for approvals. Example demo roles and limits:

- Loan Officer: Can submit assessments and view application details. Example demo identity: `loan_officer@example.com`.
- Credit Officer: Can approve or reject applications up to an authority cap.
  - Default authority limit: `CREDIT_OFFICER_AUTHORITY_LIMIT=250000` (EGP)

Adjust authority limits using the `CREDIT_OFFICER_AUTHORITY_LIMIT` environment variable.

## Running Tests & CI

Run unit tests with `pytest`:

```bash
pytest -q
```

Run linting with `ruff` (if installed):

```bash
ruff check .
```

The GitHub Actions pipeline runs `pytest` and `ruff check .` — ensure both succeed before pushing.

## 5-Minute Demo Path

1. Prepare environment: `cp .env.example .env` and populate a provider key or set `LLM_PROVIDER=fake`.
2. Ingest documents: run the ingestion script (example) to index policy docs into the vector store.
3. Q&A with citations: query the assistant and confirm answers include citations to the policy documents.
4. Generate assessment: submit an example application and let the system compute affordability/EMI and DBR.
5. Officer approval: as `Credit Officer`, open the generated assessment and approve or reject according to the authority limit.

## Evaluation & Next Steps

- Phase 1 implements core calculations (EMI, DBR, eligibility). Phase 2 adds ingestion and vector search.
- To extend: add more unit tests for the calculation engine, wire a persistent vector DB (Chroma/Qdrant), and integrate a real LLM adapter.

## Contributing

Please open issues or PRs for bugs, features, or improvements. Follow repository coding guidelines and run tests before submitting.

---
Credits: Project scaffolded for the Credit Copilot Lite proof-of-concept.
