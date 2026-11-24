"""Semantic cache: embed the question, return the stored answer of the closest cached question
in the same scope (tenant, model, system, max_tokens) if cosine similarity >= threshold.
Optional ID guard: every token that holds a digit (AB12, 2025) must match exactly, case included, or there is no hit."""
import re
import time

import numpy as np
from sentence_transformers import SentenceTransformer

ID_TOKEN = re.compile(r"\b\w*\d\w*\b")


def ids(text: str) -> set[str]:
    return set(ID_TOKEN.findall(text))


class SemanticCache:
    def __init__(self, model="sentence-transformers/all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model, device="cpu")
        self.entries = []  # (scope, question, vector, answer)

    def embed(self, text: str) -> np.ndarray:
        return self.model.encode(text, normalize_embeddings=True)  # unit length: dot = cosine

    def put(self, scope, question, answer):
        self.entries.append((scope, question, self.embed(question), answer))

    def nearest(self, scope, question):
        """Closest same-scope entry: (similarity, question, answer, embed_ms)."""
        t0 = time.perf_counter()
        v = self.embed(question)
        ms = (time.perf_counter() - t0) * 1000
        best = max(((float(v @ e[2]), e) for e in self.entries if e[0] == scope),
                   key=lambda x: x[0], default=(0.0, None))
        sim, e = best
        return sim, (e[1] if e else None), (e[3] if e else None), ms

    def get(self, scope, question, threshold, id_guard=True):
        sim, q, answer, _ = self.nearest(scope, question)
        if sim < threshold or (id_guard and ids(q) != ids(question)):
            return None
        return answer
