from typing import List, Dict


def chunk_by_clause(sections: List[Dict[str, str]]) -> List[Dict[str, str]]:
    # Very small example chunker: emits same sections with synthetic clause ids
    chunks = []
    for i, s in enumerate(sections):
        chunks.append({"clause_id": f"CP-{i+1}", "text": s.get("text", "")})
    return chunks
