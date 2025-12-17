from __future__ import annotations
import re
from typing import Set

_STOP = {
    "the","and","or","to","of","in","for","a","an","is","are","be","with","by",
    "shall","will","may","must","this","that","as","on","at","from","it","its"
}

def tokenize(text: str) -> Set[str]:
    text = (text or "").lower()
    text = re.sub(r"[^a-z0-9\s]+", " ", text)
    toks = {t for t in text.split() if len(t) > 2 and t not in _STOP}
    return toks

def jaccard(a: str, b: str) -> float:
    A = tokenize(a)
    B = tokenize(b)
    if not A or not B:
        return 0.0
    inter = len(A & B)
    union = len(A | B)
    return inter / union if union else 0.0
