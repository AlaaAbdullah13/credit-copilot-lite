# Design Notes

## Overview

Credit Copilot Lite follows a narrow, rule-driven pipeline so that the LLM is used for drafting and extraction only, while the financial decisions are computed by deterministic Python functions in the domain layer.

```mermaid
flowchart LR
    A[Seeded application_id] --> B[Parse pack + validate form]
    B --> C[Strip protected attributes]
    C --> D[Select policy edition]
    D --> E[LLM extraction + quote verification]
    E --> F[Policy retrieval + citations]
    F --> G[Rule engine (Section 2.3)]
    G --> H[Deterministic calculations]
    H --> I[Memo draft from LLM]
    I --> J[Pending recommendation]
    J --> K[Human approval and issuance]
```

## Chunking and retrieval strategy

The document store uses clause/section chunks, not arbitrary fixed-length chunks. Each chunk keeps metadata such as `source_file`, `page`, `clause_id`, `policy_edition`, and `effective_dates`.

This is implemented in:
- `src/infrastructure/ingestion/chunker.py`
- `src/infrastructure/ingestion/pipeline.py`
- `src/infrastructure/vector_store/chroma_adapter.py`

Rationale:
- policy text changes by circular and clause, so chunking by section preserves legal meaning;
- retrieval can filter by policy edition and cite the exact source clause;
- the system can explain why a rule passed or failed.

## Policy edition selection

The policy edition is chosen in code, not by the LLM. The selection logic is in:
- `src/application/validation.py`

The exact function is:
- `select_policy_edition(application_date)`

It returns:
- `2025` for applications on or after `2025-03-01`
- `2024` for applications on or after `2024-08-01`
- otherwise raises `PolicyEditionNotFound`

This keeps the rule source deterministic and prevents an LLM from inventing or guessing the active circular.

## How arithmetic stays separate from the LLM

All financial calculations live in the domain layer:
- `src/domain/calculations.py`

Examples include:
- `calculate_installment(...)`
- `calculate_dbr(...)`
- `calculate_max_eligible_amount(...)`
- `age_at_maturity_check(...)`

The pipeline writes the computed values into the memo prompt and inserts them by code. The LLM does not do numerical reasoning; it only drafts a memo text around numbers already computed by the application code.

This rule is enforced by two patterns:
1. `src/domain/calculations.py` contains the only numeric logic.
2. `src/application/pipeline.py` supplies precomputed values (`emi`, `dbr`, `max_amount`) to the memo prompt before calling the provider.

## Protected-attribute handling

Protected attributes are stripped before any LLM call:
- `gender`
- `marital_status`
- `religion`
- `nationality`

The implementation is in:
- `src/application/anonymizer.py`

The pipeline logs the stripping event before extraction so the fairness and policy constraints are demonstrable in code and test coverage. This is aligned with the 2025 circular requirement that these attributes not enter the credit decision.

## Seeded application-pack assessment

`/assess` accepts only `{ "application_id": "APP-00X" }`. The server loads the
corresponding seeded PDF from `data/applications`, parses its application form, salary
certificate, and bureau summary, and validates the form fields in code. Client-supplied
income, obligations, score, employment, or request figures are not accepted.

Application packs are held separately in the `untrusted_applications` collection. They are
never ingested into, or searched through, the trusted policy collection. Before an LLM call,
protected form fields and matching free-text lines are removed, while national IDs and phone
numbers are masked. Only the salary certificate and bureau summary are passed inside the
`<untrusted_document>` boundary. Values used by rules and calculations must be quote-verified
against those real sections; failure produces a human referral.

## Provider switching

The provider is configured through environment variables in `.env`:

- `LLM_PROVIDER`
- `GEMINI_API_KEY`
- `GROQ_API_KEY`

The switch points are:
- `.env` for runtime selection
- `src/infrastructure/llm/provider_factory.py` for provider selection logic
- `src/infrastructure/llm/gemini_adapter.py` for the Gemini adapter
- `src/infrastructure/llm/groq_adapter.py` for the Groq adapter
- `src/infrastructure/llm/fake_adapter.py` for offline deterministic testing

To switch providers:
1. Edit `.env` and set `LLM_PROVIDER=gemini` or `LLM_PROVIDER=groq`.
2. Ensure the matching API key is present.
3. Leave the code paths unchanged, because the pipeline resolves the provider through `create_llm_provider()`.

The prompts are not embedded in Python source. They are loaded from the filesystem by:
- `src/infrastructure/llm/prompt_loader.py`
- `prompts/extract.txt`
- `prompts/memo.txt`

## Approval and authority controls

The workflow records applications in `pending_approval`; only a user with the
`credit_officer` role can approve or reject them. The server loads the stored
recommended amount and enforces the approver's per-user authority limit, so a
client cannot bypass the limit by changing a request body.

The idempotent seed command (`python3 -m src.cli.seed_users`) creates three
demo accounts from environment-provided passwords:

- `loan1`: Loan Officer, EGP 0 authority; may query and assess but receives
  HTTP 403 on approval actions.
- `credit1`: Credit Officer, EGP 250,000 authority; receives a named
  `AuthorityLimitExceeded` HTTP 403 above that amount.
- `senior1`: Credit Officer, EGP 1,000,000 authority. “Senior” is an
  authority attribute, not a third role.

Approval records persist the approver, timestamp, decision, comment, and
amount. The server permits `Pending → Approved → Issued` and
`Pending → Rejected`; issuance cannot occur before approval.

## Honest cuts and future work

What is intentionally kept intentionally small for this phase:
- no production-grade prompt routing or tool-calling orchestration;
- the UI is intentionally minimal; the REST API is the primary demo surface;
- no multi-provider retries or cost-tracking.

What would be added next with more time:
- per-provider retry/backoff and token accounting;
- richer evaluation harness for policy question sets and refusal-quality checks;
- a more advanced memo generator with explicit long-form explanation and citations.
