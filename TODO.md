# Project TODO Checklist

## Phase 0: Project Setup & Repository Infrastructure
- [x] Initialize Git repository with correct `.gitignore` (from first commit) and `LICENSE`.
- [x] Setup Python environment with Poetry / `uv` and pin dependencies (`poetry.lock` / `uv.lock`).
- [x] Configure Ruff for linting and code formatting.
- [x] Create `.env.example` with all required environment variables documented.
- [x] Setup base project folder structure (`src/domain`, `src/infrastructure`, `src/application`, `tests`, `docs`).
- [x] Setup GitHub Actions workflow (`.github/workflows/ci.yml`) running lint and pytest on every PR; must be green on main at submission.
- [x] Add Pull Request template (`.github/pull_request_template.md`) with: what / why / how tested sections.
- [ ] Plan and maintain ≥15 meaningful commits across ≥4 calendar days using Conventional Commits style (no "fix2" or "final-final").
- [ ] Open ≥3 Pull Requests into main, each with a short description of what, why, and how tested.

## Phase 1: Pure Domain Logic & Calculation Engine (FR-4)
- [x] Implement `installment_calculator` using reducing-balance formula (P × r ÷ (1 − (1 + r)^−n)), rounded to 2 decimals half-up.
- [x] Implement `debt_burden_ratio` (DBR) calculation function, displayed to 2 decimals.
- [x] Implement `maximum_eligible_amount` function (largest P keeping DBR ≤ max, rounded down to nearest 1,000 EGP using floor division).
- [x] Implement `age_at_maturity` rule check (age at application + tenor years ≤ policy maximum).
- [x] Implement bureau score evaluation (below threshold → refer to human, not automatic decline).
- [x] Implement employment duration evaluation function.
- [x] Implement amount & tenor limits check against product sheet values.
- [x] Create all custom domain exceptions: `PolicyEditionNotFound`, `InvalidApplication`, `UnverifiedExtraction`, `InvalidLLMOutput`, `AuthorityLimitExceeded`.
- [x] Write unit tests for the deterministic formula-based APP-001 style scenario using standard product assumptions.
- [x] Write unit tests for edge cases: DBR exactly at the limit, zero existing obligations, age exactly at the limit, loan amount at product minimum and maximum.
- [x] Confirm calculation engine has zero imports from any LLM or vector-store library.
- [x] Phase 1 validation: `pytest tests/unit/test_calculations.py -q` passed.
- [x] Phase 1 validation: Ruff check passed for the calculation module and tests.

## Phase 2: Document Ingestion & RAG Infrastructure (FR-1, FR-2)
- [x] Setup two separate stores: Trusted Vector Store (ChromaDB / Qdrant) for policy docs, and Untrusted Application Store for applicant packs — never mix them.
- [x] Build Document Loader supporting PDF, Markdown, and CSV formats.
- [x] Implement Clause/Section-based text chunker (split by clause/section ID, not fixed character count) with metadata: `source_file`, `page`, `clause_id`, `policy_edition`, `effective_dates`.
- [x] Build ingestion pipeline that is idempotent (running twice must not create duplicate chunks).
- [x] Ingestion pipeline must report which documents succeeded and which failed.
- [x] Implement semantic (vector) search with policy edition metadata filtering.
- [x] Add relevance score threshold: below threshold → return `{"answer": "The documents do not contain enough information.", "citations": [], "reason": "no_chunk_above_threshold"}`.
- [x] Every Q&A answer must include a citations list referencing the source chunks.
- [x] Write integration test for ingestion + retrieval with citation verification.

## Phase 3: Application Pipeline & LLM Integration (FR-3)
- [x] Create abstract `LLMProvider` interface with `complete` and `embed` methods — domain/pipeline code must only call this interface, never a concrete provider directly.
- [x] Store all LLM prompts in external files (e.g. `prompts/extract.txt`, `prompts/memo.txt`), never hardcoded strings.
- [x] Implement `FakeLLMAdapter` returning deterministic responses for offline pipeline testing (no internet or API keys required).
- [x] Implement `GeminiLLMAdapter` / `GroqAdapter` (or equivalent) using a free API tier.
- [x] Document in `DESIGN.md` exactly which file to add and which config to change to switch LLM provider.
- [x] Step 1: Implement application load & schema validation (amount, tenor, date of birth, application date).
- [x] Step 2: Implement code-based protected attribute stripping (`gender`, `marital_status`, `religion`, `nationality`) — code only, not LLM — and log that stripping occurred.
- [x] Step 3: Implement policy edition selector based on application date — code only, not LLM.
- [x] Step 4: Implement LLM Data Extraction returning validated Pydantic JSON with `value` + `source_document` + `source_section` + `quoted_text` for each field.
- [x] Step 4 Verification: Write text verifier that normalises and checks each extracted value appears literally in its cited `quoted_text`; raises `UnverifiedExtraction` on mismatch → result becomes "Refer to human".
- [x] Step 5: Retrieve relevant policy clauses filtered to the selected edition and current circulars only.
- [x] Step 6: Run rule evaluation engine (all rules from Section 2.3); output pass / fail / refer per rule with policy citation.
- [x] Step 7: Draft credit memo using LLM — every numeric value (installment, DBR, max amount) is inserted by code, not typed by the LLM.
- [x] Step 8: Save recommendation as `pending` — no offer is issued until a credit officer acts.
- [x] If any step fails or evidence is missing → result is "Refer to human", never a guess.
- [x] Pipeline test (Fake LLM): approvable application — must pass.
- [x] Pipeline test (Fake LLM): over-age application — must fail with correct rule citation.
- [x] Pipeline test (Fake LLM): invalid LLM JSON output → raises `InvalidLLMOutput` → "Refer to human".
- [x] Pipeline test: LLM JSON not matching Pydantic schema is explicitly rejected (separate test).
- [x] Fairness Test (`test_fairness`): submit same application twice changing only protected attributes; assert identical result, calculations, and memo wording.
- [x] All pipeline tests must run without internet or API keys.

## Phase 4: Database, Authorization & Approval Engine (FR-5, FR-8, FR-9)
- [ ] Setup relational database (SQLite or PostgreSQL) with Alembic migrations — schema must never be created by ad-hoc startup code.
- [ ] Create models: `Application`, `AssessmentRun`, `ApprovalRecord`, `User`.
- [ ] Implement per-request logging: request ID, steps executed, chunk IDs retrieved, policy edition used, fields removed in Step 2, tokens consumed.
- [ ] Implement RBAC: `Loan Officer` (ingest, ask, submit applications) and `Credit Officer` (also approve/reject) — enforced server-side, not by hiding UI buttons.
- [ ] Implement Approval Flow: `Pending → Approved / Rejected → Issued`. Store approver identity, timestamp, and comment.
- [ ] Implement server-side authority limit check: reject Credit Officer approval if recommended amount exceeds their limit (e.g. 250,000 EGP); return clear error `AuthorityLimitExceeded`.

## Phase 5: API, Interfaces & Evaluation Suite (FR-6, FR-7)
- [ ] Build FastAPI REST endpoints: `/ingest`, `/query`, `/assess`, `/approve`, `/reject`.
- [ ] Auto-generate OpenAPI / Swagger UI documentation.
- [ ] Build CLI script for quick terminal demonstration of the full flow.
- [ ] Create evaluation test set of exactly 15 questions with expected answers, covering:
  - [ ] ≥3 out-of-corpus questions (system must refuse).
  - [ ] ≥2 questions where the correct answer differs between policy editions.
  - [ ] ≥3 calculation cases with exact expected numbers.
  - [ ] ≥2 prompt injection attempts (≥1 hidden inside an applicant document).
- [ ] Build evaluation runner script printing: retrieval hit-rate (state the k used), refusal correctness, calculation exactness.
- [ ] Execute evaluation with real results; record findings including failures in `docs/EVALUATION.md`.

## Phase 6: Security
- [ ] Mask national ID numbers and phone numbers before sending any text to the LLM provider.
- [ ] Validate all file uploads: check file type and enforce size limits.
- [ ] Use parameterised database queries everywhere — no string-concatenated SQL.
- [ ] Never render LLM output as raw HTML.
- [ ] Applicant documents are untrusted: pass them to the LLM clearly separated from system instructions; demonstrate prompt injection attempt failing in evaluation (S3).
- [ ] Run secret scanner (e.g. `gitleaks`) before submission; no API keys or passwords in repository including Git history.
- [ ] Note in `README.md` exactly what data is sent to the LLM provider.

## Phase 7: Documentation & Final Deliverables
- [ ] `docs/DESIGN.md` (2–4 pages) must cover:
  - [ ] Simple architecture diagram.
  - [ ] Chunking strategy choice and rationale.
  - [ ] How the policy edition is selected (with code reference).
  - [ ] How the LLM is kept away from arithmetic.
  - [ ] How protected attributes are removed and proven irrelevant (fairness test reference).
  - [ ] Exactly which file to add and which settings to change to switch LLM provider.
  - [ ] What you would add with more time, and what you left out on purpose (honest cuts).
- [ ] `docs/EVALUATION.md`: 15 test cases, real results (including failures), and what failures taught you.
- [ ] `docs/AI-USAGE-LOG.md`: what you asked AI tools to do, what you wrote yourself, and ≥2 cases where the AI was wrong and how you found out.
- [ ] `README.md` must include:
  - [ ] Quick start instructions.
  - [ ] Every environment variable explained.
  - [ ] How to get a free API key for the chosen provider.
  - [ ] Demo accounts for both roles (Loan Officer + Credit Officer).
  - [ ] How to run tests and the evaluation script.
  - [ ] A numbered "5-Minute Demo Path".
  - [ ] Exactly what data is sent to the LLM provider.
- [ ] `docker-compose.yml`: `docker compose up` starts everything; one command loads the demo documents.
- [ ] Clone the repo fresh and verify it runs end-to-end from the README before submission.
- [ ] Demo video (3–5 min, unlisted) must show in order:
  - [ ] Document ingestion.
  - [ ] A cited answer to a policy question.
  - [ ] A correct refusal for an out-of-corpus question.
  - [ ] An answer that changes between policy editions.
  - [ ] An application assessed with the full calculation breakdown.
  - [ ] A prompt injection attempt failing (and logged).
  - [ ] Credit Officer approval flow — including a rejected attempt above the authority limit.

## Never Cut (from Section 9)
- [x] Calculation engine and its unit tests.
- [ ] Fairness test.
- [ ] Citations and refusals.
- [ ] The approval step.
- [ ] The evaluation (15 questions + script + EVALUATION.md).
- [ ] README.

## Stretch Goals (only after core is complete)
- [ ] Hybrid search: BM25 + vector with reciprocal rank fusion — report before/after evaluation numbers.
- [ ] Re-ranking or query rewriting — report before/after evaluation numbers.
- [ ] Extend document pack with your own synthetic documents and new test cases.
- [ ] Replace fixed pipeline with 2–3 LLM agents using tool calling (typed inputs/outputs).
- [ ] Streaming answers (SSE) with visible progress of assessment steps.
- [ ] Local-model fallback via Ollama when API fails or free tier runs out.
- [ ] Second product (e.g. auto loans with a down-payment rule).
- [ ] Generate approved offer letter with repayment schedule as formatted PDF or DOCX.
- [ ] Token and cost tracking per user.
