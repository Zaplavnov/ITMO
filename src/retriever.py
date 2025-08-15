from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path
from typing import List

import joblib

from .config import INDEX_PATH, DOCUMENTS_PATH


@dataclass
class RetrievedChunk:
    id: str
    url: str
    title: str
    text: str
    score: float


class Retriever:
    def __init__(self) -> None:
        payload = joblib.load(INDEX_PATH)
        self.vectorizer = payload["vectorizer"]
        self.document_vectors = payload["document_vectors"]
        self.document_ids = payload["document_ids"]
        docs = json.loads(Path(DOCUMENTS_PATH).read_text(encoding="utf-8"))
        self.id_to_doc = {d["id"]: d for d in docs}

    def search(self, query: str, top_k: int = 5) -> List[RetrievedChunk]:
        query_vec = self.vectorizer.transform([query])
        # Cosine sim from sklearn is expensive to import again; compute manually via dot
        import numpy as np
        from numpy.linalg import norm

        q = query_vec.toarray()[0]
        mat = self.document_vectors
        sims = (mat @ q) / (norm(q) * np.sqrt((mat.multiply(mat)).sum(axis=1)).A1 + 1e-12)
        pairs = list(zip(self.document_ids, sims))
        pairs.sort(key=lambda x: x[1], reverse=True)
        results: List[RetrievedChunk] = []
        for doc_id, score in pairs[:top_k]:
            meta = self.id_to_doc.get(doc_id)
            if not meta:
                continue
            results.append(
                RetrievedChunk(
                    id=doc_id,
                    url=meta["url"],
                    title=meta.get("title", doc_id),
                    text=meta["text"],
                    score=float(score),
                )
            )
        return results
