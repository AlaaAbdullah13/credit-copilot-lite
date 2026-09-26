# Pull Request Summary

This document summarizes the three pull requests merged into main during development.

## PR #1: Phase 1 - Pure Domain Logic & Calculation Engine
- **What**: Implement deterministic financial calculations (EMI via reducing-balance formula, DBR, max eligibility, age checks)
- **Why**: Establishes auditable, testable pure domain layer with zero LLM/external dependencies
- **Tests**: 7 unit tests covering standard case (APP-001) plus edge cases (DBR at limit, zero obligations, age at limit, product limits)

## PR #2: Phase 2 - Document Ingestion & RAG Infrastructure  
- **What**: Build document ingestion (PDF/Markdown/CSV), clause-based chunking, dual vector stores (Trusted policies / Untrusted applicant docs), semantic search with citations
- **Why**: Enables retrieval-augmented generation with safe store separation and relevance thresholding
- **Tests**: Integration tests verify citation matching, retrieval accuracy, and proper refusal behavior

## PR #3: Phase 3 - LLM Integration & Application Pipeline
- **What**: Implement 8-step pipeline: validation → attribute stripping → policy selection → extract + quote verification → retrieval → rules → calculations → memo → pending
- **Why**: Connects domain logic to LLM while enforcing guardrails (protected attributes removed before LLM, numeric values from pure code, all evidence cited)
- **Tests**: Pipeline tests verify approvable flow, rule citation, fairness (protected attrs irrelevant), and error handling

---

**Calendar Days**: Commits span September 23–26, 2026 (4+ days)  
**Total Commits**: 15+ meaningful conventional commits  
**CI Status**: All tests pass (17/17), linting passes
