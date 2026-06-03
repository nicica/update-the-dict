from __future__ import annotations

import re
from typing import List

TOKEN_RE = re.compile(r"[A-Za-z0-9]+(?:'[A-Za-z0-9]+)?")


def tokenize(text: str) -> List[str]:
    """Return normalized tokens from *text*.

    Normalization choices are deliberately simple:
    - lowercase all terms;
    - remove punctuation by extracting word-like tokens;
    - keep numbers as searchable tokens.

    Parameters
    ----------
    text:
        Raw document or query text.

    Returns
    -------
    list[str]
        Lowercased tokens in their original order.
    """
    return [match.group(0).lower() for match in TOKEN_RE.finditer(text)]
