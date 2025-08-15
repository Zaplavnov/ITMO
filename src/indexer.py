from __future__ import annotations
from typing import List, Tuple
import json
from pathlib import Path

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .config import DOCUMENTS_PATH, INDEX_PATH


class TfidfRetrievalIndex:
    def __init__(self, vectorizer: TfidfVectorizer, document_vectors, document_ids: List[str]):
        self.vectorizer = vectorizer
        self.document_vectors = document_vectors
        self.document_ids = document_ids

    def query(self, text: str, top_k: int = 5) -> List[Tuple[str, float]]:
        query_vec = self.vectorizer.transform([text])
        scores = cosine_similarity(query_vec, self.document_vectors)[0]
        ranked = sorted(zip(self.document_ids, scores), key=lambda x: x[1], reverse=True)
        return ranked[:top_k]


def build_index() -> None:
    docs = json.loads(Path(DOCUMENTS_PATH).read_text(encoding="utf-8"))
    corpus = [d["text"] for d in docs]
    doc_ids = [d["id"] for d in docs]

    vectorizer = TfidfVectorizer(
        lowercase=True,
        ngram_range=(1, 2),
        token_pattern=r"(?u)\b\w{2,}\b",
        max_df=0.9,
        min_df=2,
    )
    document_vectors = vectorizer.fit_transform(corpus)

    joblib.dump(
        {
            "vectorizer": vectorizer,
            "document_vectors": document_vectors,
            "document_ids": doc_ids,
        },
        INDEX_PATH,
    )


if __name__ == "__main__":
    build_index()
