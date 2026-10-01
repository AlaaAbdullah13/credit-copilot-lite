# AI Usage Log and Engineering Ownership

## Human engineering ownership

The following work was designed, implemented, and reviewed as human engineering work:

- the core domain model and deterministic financial calculation engine, including the reducing-balance installment formula, DBR calculation, and floor division used for maximum eligible amount;
- the protected-attribute and PII sanitization boundaries, including removal of gender, marital status, religion, and nationality before LLM interaction;
- the custom domain exception hierarchy, including `PolicyEditionNotFound`, `AuthorityLimitExceeded`, and `UnverifiedExtraction`;
- the layered architecture, FastAPI route design, authorization controls, and approval state transitions.

## AI assistance scope

AI tools were used as development accelerators for repetitive boilerplate, initial test-mock scaffolding, CSS/HTML layout tuning, Dockerfile optimization, and documentation structure. Suggestions were treated as untrusted input: policy interpretation, numeric behavior, retrieval thresholds, and security boundaries were verified against source files, deterministic code, and automated tests before adoption.

## Errors found and corrected

### Flat-rate calculation proposal

An AI suggestion used a simple flat-rate interest approach instead of the required reducing-balance formula: `P × r / (1 - (1 + r)^-n)`. A unit-test mismatch exposed the error. The implementation was manually rewritten in the domain calculation engine and exact outcomes were retained as unit-test assertions.

### LLM-owned financial formatting

An early AI-generated approach allowed an LLM to format financial figures directly in the credit memo. That created a hallucination path between deterministic calculation and the user-visible recommendation. The pipeline was refactored so Python supplies verified numeric values to the memo stage; the LLM drafts prose only around those values.

### Retrieval threshold generalization

An AI suggestion favored one global retrieval threshold. Diagnostics showed that this either admitted irrelevant chunks for out-of-corpus questions or rejected valid formatted policy chunks. The evaluator now explicitly tests strict refusal behavior separately from answerable retrieval behavior, with the final configuration verified by the offline evaluation suite.

## Review practice

No AI output is accepted solely because it is plausible. Changes that affect credit policy, arithmetic, protected attributes, citations, retrieval, or authorization require a code review against the local corpus and test evidence. This preserves engineer accountability for the behavior of the delivered system.
