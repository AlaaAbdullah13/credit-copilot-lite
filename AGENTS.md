# AGENTS.md - Developer & AI Agent Guidelines

This document serves as the operational guide and guardrails for human developers and AI coding agents working on Credit Copilot Lite.

---

## 🏛️ ARCHITECTURE & DESIGN PRINCIPLES

### Layered Architecture Structure
The codebase strictly follows Domain-Driven Design (DDD) layered architecture:
- `src/domain`: Pure business logic, credit rules, calculation algorithms, and custom exceptions.
- `src/infrastructure`: Database, vector store, file loaders, LLM adapters, and external services.
- `src/application`: Use-case workflows, pipeline steps, and orchestration logic.
- `src/api` or `src/cli`: HTTP endpoints (FastAPI) and CLI demo scripts.

### Core Architectural Guardrails
1. **Zero LLM Imports in Domain Layer**: The `domain` layer MUST NOT import any LLM, vector store, or external library.
2. **LLM Never Calculates Numbers**: All financial calculations (installment, DBR, max loan amount, age limit) MUST be computed by deterministic Python code in `src/domain/calculations.py`. The LLM's role in drafting memos is strictly to incorporate code-supplied values.
3. **Separate Trusted and Untrusted Stores**:
   - **Trusted Vector Store**: Contains official bank policy documents (ChromaDB / Qdrant).
   - **Untrusted Store**: Holds applicant documents. NEVER query applicant documents to answer general policy questions or mix chunk stores.
4. **Protected Attribute Stripping**: Step 2 of the pipeline MUST strip protected attributes (`gender`, `marital_status`, `religion`, `nationality`) via pure Python code before passing application data to any LLM.
5. **Human-In-The-Loop Enforcement**: Applications default to `Pending`. Final approvals or rejections MUST be executed by a human user with appropriate role permissions (`Credit Officer`).

---

## 🛑 NEVER CUT — NON-NEGOTIABLE
These components MUST exist in the final submission regardless of time constraints:
- Calculation engine and its corresponding unit tests (`APP-001` test cases).
- Fairness test (`test_fairness`).
- Citations and refusals for out-of-corpus queries.
- Approval workflow (`Pending` → `Approved` / `Rejected` → `Issued`).
- Evaluation test set (15 questions) + evaluation runner script + `docs/EVALUATION.md`.
- `README.md` containing the numbered "5-Minute Demo Path".

---

## 🐙 GIT WORKFLOW RULES
- Use **Conventional Commits** format: `feat:`, `fix:`, `test:`, `docs:`, `chore:`.
- Maintain a minimum of **15 meaningful commits** spread across at least **4 calendar days**.
- Create a minimum of **3 Pull Requests** into `main`, each with the PR template fully filled out (`what`, `why`, `how tested`).
- CI pipeline (`.github/workflows/ci.yml` running linting and tests) MUST be green on `main` at submission time.
- Vague commit messages (e.g., "fix2", "final", "wip") are strictly prohibited.

---

## 📝 PROMPT MANAGEMENT
- All LLM prompts MUST be stored in external text files under the `prompts/` directory (e.g., `src/infrastructure/llm/prompts/extract.txt`).
- No prompt strings are allowed to be hardcoded in Python source files.
- Prompt files must be dynamically loaded at runtime using a prompt loader utility.

---

## 🔒 SECURITY & SANITIZATION RULES
- Mask National ID numbers and phone numbers before sending any text payload to external LLM providers.
- Validate all file uploads: check MIME type and enforce strict maximum file size limits.
- All database queries MUST use parameterised queries (SQLAlchemy ORM or parameterised SQL) — string-concatenated SQL is strictly forbidden.
- Never render raw LLM output as raw HTML in any endpoint or template.
- Applicant documents passed to the LLM must be clearly delimited from system instructions using XML-style boundary tags (e.g., `<untrusted_document>...</untrusted_document>`).

---

## 🚨 CUSTOM DOMAIN EXCEPTIONS
The domain layer MUST define and raise the following 5 custom exceptions:
1. `PolicyEditionNotFound`: Raised when a requested policy edition does not exist.
2. `InvalidApplication`: Raised when required application payload fields are missing or malformed.
3. `UnverifiedExtraction`: Raised when extracted data fails exact quote verification against source documents.
4. `InvalidLLMOutput`: Raised when LLM output cannot be parsed into the target Pydantic schema or JSON structure.
5. `AuthorityLimitExceeded`: Raised when a Credit Officer attempts to approve an application exceeding their assigned authority threshold.

---

## 🧪 REQUIRED PIPELINE TESTS
All pipeline tests MUST run offline using `FakeLLMAdapter` (zero API keys or internet required):
- `test_approvable_application`: Complete pass scenario where all credit rules succeed.
- `test_over_age_application`: Applicant maturity age exceeds policy limit; asserts automatic decline with exact rule citation.
- `test_invalid_llm_output`: `FakeLLMAdapter` returns malformed JSON; verifies system raises `InvalidLLMOutput` and defaults result to `"Refer to human"`.
- `test_schema_rejection`: Explicit test asserting LLM JSON not matching the target Pydantic schema is rejected.
- `test_fairness`: Submits identical applications differing only in protected attributes and asserts identical output calculations and memo decisions.

---

## 📊 EVALUATION REQUIREMENTS (FR-6)
The 15-question evaluation suite in `docs/EVALUATION.md` MUST follow this exact distribution:
- **≥3 out-of-corpus questions**: System must refuse to answer and return `no_chunk_above_threshold`.
- **≥2 policy edition differential questions**: Questions where answers differ between the 2024 and 2025 policy editions.
- **≥3 calculation cases**: Queries requiring exact numerical answers verified against deterministic formulas.
- **≥2 prompt injection attempts**: System security test, with at least 1 injection hidden inside an applicant document payload.

---

## ⚙️ DEVELOPMENT PHASES

### Phase 0: Setup & CI Infrastructure
- Setup repository, dependencies, linting (Ruff), and GitHub Actions CI.
- Add PR template (`.github/pull_request_template.md`).

### Phase 1: Pure Domain Logic & Calculation Engine (FR-4)
- Implement financial formulas: Installment (reducing balance), DBR, Max Eligible Amount, and Age at Maturity.
- Implement product limit checks and bureau score logic.
- Write unit tests covering exact APP-001 numbers and edge cases.

### Phase 2: Document Ingestion & RAG Infrastructure (FR-1, FR-2)
- Build ingestion pipeline for PDF, Markdown, and CSV files.
- Implement clause/section-based chunking with complete metadata tracking.
- Build ChromaDB adapter with relevance thresholding, idempotency, and ingestion failure reports.

### Phase 3: Application Pipeline & LLM Integration (FR-3)
- Implement `LLMProvider` interface, `FakeLLMAdapter`, and `GeminiLLMAdapter` / `GroqAdapter`.
- Implement Step 1 through Step 8 of the assessment pipeline.
- Enforce quote verification and external prompt loading.

### Phase 4: Database, Authorization & Approval Engine (FR-5, FR-8, FR-9)
- Setup database models (Application, AssessmentRun, ApprovalRecord, User) with Alembic migrations.
- Implement RBAC (`Loan Officer` vs `Credit Officer`) and authority limit enforcement.
- Configure detailed per-request logging and token tracking.

### Phase 5: API, CLI & Evaluation Suite (FR-6, FR-7)
- Build FastAPI endpoints (`/ingest`, `/query`, `/assess`, `/approve`, `/reject`) and CLI demo script.
- Execute the 15-question evaluation suite and generate `docs/EVALUATION.md`.

### Phase 6: Security & Hardening
- Implement National ID masking, file upload validation, and secret scanning.

### Phase 7: Documentation & Video
- Complete `docs/DESIGN.md`, `docs/AI-USAGE-LOG.md`, `README.md` (5-Minute Demo Path), and record the 3-5 minute unlisted demo video.