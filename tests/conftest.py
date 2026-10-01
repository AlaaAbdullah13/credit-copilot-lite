"""Shared test isolation for filesystem-backed vector stores."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def isolate_chroma_storage(tmp_path, monkeypatch):
    """Never let tests reuse a developer's persisted Chroma collection."""
    monkeypatch.setenv("CHROMA_DB_DIR", str(tmp_path / "chroma"))
