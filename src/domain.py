from __future__ import annotations
from typing import List, Optional
import re

from .retriever import Retriever


_RECOMMEND_PATTERNS = [
    r"рекоменд",
    r"выборн",
    r"электив",
    r"что\s+выбрат",
    r"какие\s+дисциплины",
    r"лучше\s+послушать",
    r"по\s+бэкграунду",
]

_BG_TAGS = {
    "python": ["python", "питон"],
    "ml": ["ml", "machine learning", "машин", "обучени"],
    "data_science": ["data science", "аналитик", "анализ данных", "ds"],
    "cv": ["computer vision", "cv", "компьютерн", "зрение"],
    "nlp": ["nlp", "обработк", "текст", "язык"],
    "product": ["product", "продакт", "менеджмент", "управлен"],
    "backend": ["backend", "бэкенд", "сервер", "python dev", "java", "go", "node"],
    "frontend": ["frontend", "фронтенд", "web", "react", "vue", "ui"],
    "math": ["матем", "матстат", "вероятност", "алгебр"],
    "devops": ["devops", "mlo", "mlops", "docker", "kubernetes", "k8s"],
}


def is_recommendation_intent(text: str) -> bool:
    lowered = text.lower()
    return any(re.search(pat, lowered) for pat in _RECOMMEND_PATTERNS)


def extract_background_tags(text: str) -> List[str]:
    lowered = text.lower()
    tags: List[str] = []
    for tag, patterns in _BG_TAGS.items():
        if any(p in lowered for p in patterns):
            tags.append(tag)
    return tags


def detect_program_from_text(text: str) -> Optional[str]:
    t = text.lower()
    if "ai product" in t or "ai_product" in t or "продакт" in t or "product" in t:
        return "ai_product"
    if re.search(r"\bai\b", t) or "искусствен" in t:
        return "ai"
    return None


def is_relevant_question(text: str, retriever: Retriever, threshold: float = 0.08) -> bool:
    # Use retriever scores to decide relevance
    results = retriever.search(text, top_k=1)
    if not results:
        return False
    return results[0].score >= threshold
