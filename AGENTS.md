# Agent Execution Guide & Project Roadmap: Credit Copilot Lite

This document guides the AI Agent through the phased development of Credit Copilot Lite.

## Project Phases Overview

### Phase 1: Domain Core & Calculation Engine
- Implement reducing-balance interest & EMI formula.
- Implement DBR, Max Eligible Amount, Age at Maturity, Bureau score, and Loan Limit rules.
- Write unit tests targeting acceptance criteria (APP-001 worked example: Installment 8,630.39, DBR 42.10%, Max Amount 382,000).

### Phase 2: Document Ingestion & Vector Search (RAG Setup)
- Build ingestion pipeline: Extract -> Chunk (by clause/section ID) -> Embed -> Index.
- Set up Trusted Store (ChromaDB/Qdrant) for 12 Policy docs and Untrusted Store for Application packs.
- Implement Metadata filtering by `policy_edition` and citation tracking.
- Implement relevance threshold logic with refusal response ("The documents do not contain enough information.").

### Phase 3: Application Pipeline & LLM Integration
- Create LLM Abstraction Interface (`LLMAdapter`) with primary implementation (e.g., Gemini/Groq API) and Fake LLM implementation for offline testing.
- Implement Step 2: Code-level protected attribute removal + logging.
- Implement Step 4: LLM Structured JSON Extraction + Fact-checking verification against `quoted_text`.
- Implement Step 7: Draft Credit Memo with code-injected calculation numbers.

### Phase 4: Persistence, Governance & Security
- Setup Relational Database (SQLite/Postgres) with migrations (Alembic).
- Implement Role-Based Access Control (RBAC): Loan Officer vs. Credit Officer.
- Enforce Server-Side Approval Authority Limits (e.g., Max 250,000 EGP for Credit Officers).
- Implement Masking for National IDs and Phone Numbers before sending text to LLM.

### Phase 5: API, CLI & Evaluation
- Create FastAPI endpoints for Ingest, Search, Assess Application, Approve/Reject.
- Create CLI script for fast demonstration.
- Build evaluation harness for 15 test cases (`EVALUATION.md`) measuring retrieval hit-rate, refusal correctness, and exactness.
- Build Fairness Test (`test_fairness`).

### Phase 6: CI/CD, Documentation & Packaging
- Setup GitHub Actions workflow for Ruff (Linting) and Pytest.
- Write `docs/DESIGN.md`, `docs/EVALUATION.md`, `docs/AI-USAGE-LOG.md`, and `README.md`.
- Configure `docker-compose.yml` for single-command startup.
