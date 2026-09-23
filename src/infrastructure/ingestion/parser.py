from typing import List, Dict


def parse_markdown(path: str) -> List[Dict[str, str]]:
    # Minimal parser that reads markdown and returns sections
    sections = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
    except FileNotFoundError:
        return sections
    sections.append({"id": "root", "text": text})
    return sections


def parse_csv(path: str) -> List[Dict[str, str]]:
    rows = []
    try:
        import csv

        with open(path, newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for r in reader:
                rows.append(dict(r))
    except FileNotFoundError:
        return rows
    return rows
