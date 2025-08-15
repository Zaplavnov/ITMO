from __future__ import annotations
from typing import List, Dict
import json
from pathlib import Path

from .config import DOCUMENTS_PATH


def load_all_texts() -> List[Dict]:
    return json.loads(Path(DOCUMENTS_PATH).read_text(encoding="utf-8"))


def filter_docs_by_program(docs: List[Dict], program: str) -> List[Dict]:
    # program in our pipeline is part of the id/title slug
    return [d for d in docs if program in d.get("title", "") or program in d.get("id", "") or program in d.get("url", "")]


def recommend_electives(background_tags: List[str], program: str, top_k: int = 6) -> List[str]:
    docs = load_all_texts()
    docs = filter_docs_by_program(docs, program)

    # Simple keyword heuristics: score chunks that mention elective/выбор/треки and match bg tags
    KEYWORDS = ["выбор", "электив", "модуль", "трек", "курс", "дисциплин", "каталог"]

    def score(doc: Dict) -> float:
        text = (doc.get("text") or "").lower()
        s = 0.0
        for kw in KEYWORDS:
            if kw in text:
                s += 1.0
        for tag in background_tags:
            if tag in text:
                s += 0.5
        return s

    ranked = sorted(docs, key=score, reverse=True)
    top_texts = [d["text"][:400] for d in ranked[:top_k]]
    return top_texts
