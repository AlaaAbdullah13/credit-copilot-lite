from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
PROMPTS_DIR = PROJECT_ROOT / "prompts"


def load_prompt(name: str) -> str:
    """Load a prompt by filename without hardcoded prompt strings in Python code."""
    prompt_file = PROMPTS_DIR / f"{name}.txt"
    return prompt_file.read_text(encoding="utf-8")


__all__ = ["PROJECT_ROOT", "PROMPTS_DIR", "load_prompt"]
