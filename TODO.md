# Project Status

## Core implementation: complete

The required implementation work is complete and covered by automated tests:

- deterministic calculation and underwriting rules;
- trusted policy retrieval, citations, and out-of-corpus refusals;
- protected-attribute removal, PII masking, and fairness coverage;
- application assessment, RBAC, authority limits, and approval workflow;
- offline 15-case evaluation suite and supporting documentation;
- Docker/local setup, API, minimal web interface, and documentation viewer.

The former phase-by-phase checklist was retired because it no longer reflected the repository state and could confuse reviewers.

## Submission actions still required

These are external release tasks, not unfinished product features:

- [ ] Open and merge the `feature/docs-and-web-viewer` pull request into `main` after review.
- [ ] Confirm GitHub Actions is green on the pull request and on `main` after merge.
- [ ] Record the required 3–5 minute unlisted demo video and replace the README placeholder with its link.
- [ ] Perform a final fresh-clone, README-guided end-to-end verification before submission.

## Optional future improvements

The following are intentionally out of scope for this training project: hybrid retrieval, reranking, streaming updates, a second lending product, provider failover, and generated offer documents. They are documented as honest future work in `docs/DESIGN.md` and are not blockers for the core submission.
