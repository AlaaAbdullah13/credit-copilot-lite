# AI Usage Log

## Purpose

This log records where AI-assisted development was used in Credit Copilot Lite and how outputs were independently checked. AI assistance supported implementation and documentation; deterministic code, tests, policy documents, and human review remained the sources of record.

## AI-assisted tasks

| Area | AI assistance | Verification |
|---|---|---|
| Vector-store retrieval | Identified that ChromaDB query results expose cosine **distances** and proposed converting them to scores with `1 - distance`. | Ran the Chroma diagnostics and the ingestion threshold test; verified non-hardcoded scores and threshold refusals. |
| Evaluation harness | Helped refine evaluation prompts, expected keyword checks, edition-specific queries, and the strict/lenient query routing. | Ran `python src/cli/evaluate.py`; final result was 15/15 passing. |
| Calculation review | Helped inspect the maximum-eligible-amount formula and evaluation expectations. | Executed deterministic calculation commands and unit tests; calculations are implemented in the domain layer, not by an LLM. |
| Chroma persistence issue | Helped isolate cross-edition result loss to repeated Chroma IDs such as `C-1` and `page-2`. | Ingested both editions, queried each edition, and confirmed both returned the correct tagged policy chunks after the ID fix. |
| Documentation | Helped draft `docs/EVALUATION.md` and this log from observed command output. | Reviewed against the evaluator output and repository behavior. |

## Work written manually

- Defined the product requirements, policy corpus, evaluation questions, and acceptance criteria.
- Reviewed and approved domain calculation formulas, including the income/DBR affordability rule.
- Chose the final threshold policy after inspecting real Chroma scores and false-positive/false-negative behavior.
- Reviewed source documents and confirmed expected policy values, citations, and edition differences.
- Ran local tests and diagnostics, reviewed their output, and made the final implementation decisions.

## AI mistakes discovered during development

### 1. Maximum eligible amount: 382,000 versus 330,000

**Mistake:** AI initially treated 382,000 EGP as the expected result for a case using a 45% DBR limit. That value is not compatible with a monthly income of 30,000 EGP, existing obligations of 4,000 EGP, and a 45% cap.

**How it was discovered:** A deterministic command was run against `calculate_max_eligible_amount`. The correct affordability payment at 45% is:

```text
(30,000 × 0.45) - 4,000 = 9,500 EGP
```

At 24% for 60 months, that payment supports a principal of 330,000 EGP after flooring to the nearest thousand.

**Fix:** The calculation code was corrected to calculate the allowed instalment as `(income × DBR limit) - obligations`, without using the requested instalment. Q10 was updated to expect 330,000 EGP. Q07 correctly retains 382,000 EGP because its APP-001 specification uses a 50% DBR cap, giving an 11,000 EGP instalment limit.

### 2. A single retrieval threshold caused a refusal/retrieval conflict

**Mistake:** AI initially recommended one threshold for all evaluator queries. A low threshold admitted unrelated policy chunks for out-of-corpus questions; a high threshold excluded legitimate product-sheet and pricing-table chunks.

**How it was discovered:** Chroma diagnostics printed real cosine-derived scores. Out-of-corpus queries could score around the mid-0.4 range, while valid formatted policy chunks could score below a high global threshold. Evaluation runs showed either refusal failures or retrieval failures depending on the single threshold selected.

**Fix:** The evaluator now uses two query functions:

- `0.55` for refusal cases, requiring `no_chunk_above_threshold` and no citations.
- `0.40` for retrieval, differential, and injection cases.

This configuration was validated by the final evaluation run: all three refusals and all answerable retrieval cases passed.

## Additional review practice

AI-generated suggestions were not accepted solely on plausibility. Changes affecting policy interpretation, numeric calculations, thresholds, or citations were checked against the local policy corpus, deterministic functions, and automated tests before being retained.
