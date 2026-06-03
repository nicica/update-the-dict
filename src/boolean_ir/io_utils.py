"""Input/output helpers for loading the small JSONL corpus used in the demo."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, List

from .index import Document


def load_jsonl_documents(path: str | Path) -> List[Document]:
    """Load documents from a JSON Lines file.

    Each line must contain a JSON object with at least:
    - doc_id
    - title
    - text
    - split
    """
    documents: List[Document] = []
    path = Path(path)

    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {line_number} of {path}") from exc
            documents.append(Document.from_dict(data))

    return documents


def split_documents(documents: Iterable[Document], split: str) -> List[Document]:
    """Return documents whose split label equals *split*."""
    return [document for document in documents if document.split == split]
