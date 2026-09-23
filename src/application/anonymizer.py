from typing import Dict


PROTECTED = {"gender", "religion", "marital_status", "nationality"}


def anonymize_application(payload: Dict) -> Dict:
    """Remove protected attributes from a dict representing an application."""
    out = dict(payload)
    for p in PROTECTED:
        if p in out:
            out[p] = None
    return out
