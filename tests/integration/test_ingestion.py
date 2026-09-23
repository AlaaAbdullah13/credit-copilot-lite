from src.infrastructure.ingestion.parser import parse_markdown
from src.infrastructure.ingestion.chunker import chunk_by_clause


def test_parse_and_chunk_sample():
    # Use an in-repo policy file if present; otherwise ensure functions run
    sections = parse_markdown("data/policy/product-sheet-personal-loan.md")
    chunks = chunk_by_clause(sections)
    assert isinstance(chunks, list)
