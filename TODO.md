# Project TODO Checklist

## Phase 0: Project Setup & Repository Infrastructure
- [ ] Initialize Git repository with correct `.gitignore` and `LICENSE`.
- [ ] Setup Python environment with Poetry / `uv` and pin dependencies (`poetry.lock` / `uv.lock`).
- [ ] Configure Ruff for linting and code formatting.
- [ ] Create `.env.example` file.
- [ ] Setup base project folder structure (`src/domain`, `src/infrastructure`, `src/application`, `tests`, `docs`).
- [ ] Setup GitHub Actions workflow (`.github/workflows/ci.yml`) running lint and pytest on PRs.

## Phase 1: Pure Domain Logic & Calculation Engine (FR-4)
- [ ] Implement `installment_calculator` using reducing-balance formula.
- [ ] Implement `debt_burden_ratio` (DBR) calculation function.
- [ ] Implement `maximum_eligible_amount` function (rounded down to 1000 EGP).
- [ ] Implement `age_at_maturity` rule check.
- [ ] Implement bureau score and employment duration evaluation functions.
- [ ] Create custom domain exceptions (`PolicyEditionNotFound`, `InvalidApplication`, `UnverifiedExtraction`, `AuthorityLimitExceeded`).
- [ ] Write Unit Tests for APP-001 scenario (Verify: EMI = 8,630.39, DBR = 42.10%, Max Amount = 382,000 EGP).
- [ ] Write Unit Tests for edge cases (DBR at limit, 0 obligations, max age limit, min/max loan amounts).

## Phase 2: Document Ingestion & RAG Infrastructure (FR-1, FR-2)
- [ ] Setup Trusted Vector Store (ChromaDB / Qdrant) and Untrusted Application Store.
- [ ] Build Document Loader for PDF, Markdown, CSV documents.
- [ ] Implement Clause/Section-based text chunker with Metadata (source_file, page, clause_id, policy_edition, effective_dates).
- [ ] Build ingestion pipeline ensuring idempotent loading (no duplicate chunks on re-run).
- [ ] Implement semantic vector search with policy edition metadata filtering.
- [ ] Add relevance score threshold for refusal ("The documents do not contain enough information.").
- [ ] Write integration tests for ingestion and retrieval with citations.

## Phase 3: Application Pipeline & LLM Integration (FR-3)
- [ ] Create abstract `LLMProvider` interface (with `complete` and `embed` methods).
- [ ] Implement `FakeLLMAdapter` for offline pipeline testing without internet or API keys.
- [ ] Implement `GeminiLLMAdapter` / `GroqAdapter` using free API tier.
- [ ] Step 1: Implement application load & schema validation.
- [ ] Step 2: Implement code-based protected attribute stripping (`gender`, `marital_status`, `religion`, `nationality`) and log event.
- [ ] Step 3: Implement policy edition selector based on application date.
- [ ] Step 4: Implement LLM Data Extraction with Pydantic JSON schema output.
- [ ] Step 4 Verification: Write text verifier to ensure extracted values appear in cited text (raises `UnverifiedExtraction` on mismatch).
- [ ] Step 5 & 6: Connect retrieval and rule evaluation engine.
- [ ] Step 7: Draft Credit Memo using LLM with strictly code-injected calculation figures.
- [ ] Write pipeline integration test with Fake LLM.
- [ ] Write Fairness Test (`test_fairness`) proving protected attribute changes do not alter assessment outcome.

## Phase 4: Database, Authorization & Approval Engine (FR-5, FR-8, FR-9)
- [ ] Setup Relational Database schema (SQLite/PostgreSQL) and configure Alembic migrations.
- [ ] Create Models: `Application`, `AssessmentRun`, `ApprovalRecord`, `User`.
- [ ] Implement Request Logging (Request ID, steps executed, chunks used, policy edition, removed attributes, token usage).
- [ ] Implement RBAC middleware/dependencies (`Loan Officer` vs `Credit Officer`).
- [ ] Implement Approval Flow (Pending -> Approved/Rejected -> Issued).
- [ ] Implement server-side authority limit check (e.g. reject approval if amount > 250,000 EGP for credit officer).

## Phase 5: API, Interfaces & Evaluation Suite (FR-6, FR-7)
- [ ] Build FastAPI REST endpoints (`/ingest`, `/query`, `/assess`, `/approve`).
- [ ] Auto-generate OpenAPI / Swagger UI documentation.
- [ ] Build CLI script (`main.py`) for quick terminal demonstration.
- [ ] Create 15-question evaluation test set in code/JSON.
- [ ] Build evaluation runner script calculating retrieval hit-rate, refusal correctness, and exactness.
- [ ] Execute evaluation and record real findings in `docs/EVALUATION.md`.

## Phase 6: Documentation, Security & Final Deliverables
- [ ] Perform security review: Mask Phone & National ID numbers in LLM prompts.
- [ ] Run secret scanner (e.g. `gitleaks`) to ensure no API keys or secrets are committed.
- [ ] Write `docs/DESIGN.md` (Architecture, Chunking rationale, Policy selection, LLM abstraction, Fairness proof).
- [ ] Write `docs/EVALUATION.md` (15 test cases, metrics, failure analysis).
- [ ] Write `docs/AI-USAGE-LOG.md` (AI prompts, corrections, incorrect AI answers).
- [ ] Write comprehensive `README.md` (Quickstart, Env vars, Demo credentials, 5-Minute Demo Path).
- [ ] Create `docker-compose.yml` and test `docker compose up` fresh setup.
- [ ] Record 3-5 minute unlisted Demo Video.
