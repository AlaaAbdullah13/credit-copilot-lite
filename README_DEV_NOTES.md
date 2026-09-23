Developer notes: This folder contains lightweight boilerplate for Credit Copilot Lite.

Structure created:
- src/domain: business models, calculations, rules, exceptions
- src/infrastructure: llm adapters, vector store adapters, ingestion parsers, db
- src/application: pipeline, anonymizer, auth, api
- tests/: unit, integration, pipeline

Run tests locally:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip pytest ruff
pytest -q
```
