"""Notebook-compatible ranking, with FAQ embeddings computed once per process."""
import os
import re
from threading import Lock
from time import perf_counter

import numpy as np
from sentence_transformers import SentenceTransformer

from .repository import FAQRepository
from .schemas import Candidate, MatchResponse

MODEL_NAME = 'all-MiniLM-L6-v2'
SIMILARITY_THRESHOLD = 0.45


def tokenize(text: str) -> set[str]:
    return set(re.findall(r'\b[a-z0-9]+\b', text.lower()))


class FAQMatcher:
    def __init__(self, repository: FAQRepository, model=None):
        self.faqs = repository.load()
        self.model = model if model is not None else SentenceTransformer(
            MODEL_NAME, device=os.getenv('FAQ_DEVICE', 'cpu'),
            local_files_only=os.getenv('FAQ_LOCAL_FILES_ONLY', '0') == '1',
        )
        self._lock = Lock()
        self.embeddings = self.model.encode(
            [faq.question for faq in self.faqs],
            normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False,
        )
        self.word_sets = [tokenize(faq.question) for faq in self.faqs]

    def rank_many(self, queries: list[str]) -> list[list[Candidate]]:
        if not queries:
            return []
        # Serialize model inference across FastAPI worker threads.
        with self._lock:
            embeddings = self.model.encode(
                queries, normalize_embeddings=True, convert_to_numpy=True,
                show_progress_bar=False,
            )
        # Dot product of normalized embeddings equals cosine similarity.
        semantic = np.clip(embeddings @ self.embeddings.T, -1, 1)
        results = []
        for query, semantic_scores in zip(queries, semantic):
            words = tokenize(query)
            overlap = np.array([
                len(words & faq_words) / len(words) if words else 0.0
                for faq_words in self.word_sets
            ])
            scores = 0.85 * semantic_scores + 0.15 * overlap
            indices = np.argsort(scores)[::-1][:3]
            results.append([
                Candidate(**self.faqs[int(i)].model_dump(), score=float(scores[i]),
                          semantic_similarity=float(semantic_scores[i]),
                          keyword_overlap=float(overlap[i])) for i in indices
            ])
        return results

    def find_answer(self, user_question: str, threshold: float | None = None) -> MatchResponse:
        started = perf_counter()
        threshold = SIMILARITY_THRESHOLD if threshold is None else threshold
        if not 0 <= threshold <= 1:
            raise ValueError('Threshold must be between 0 and 1.')
        query = user_question.strip()
        matches = self.rank_many([query])[0] if query else []
        accepted = bool(matches and matches[0].score >= threshold)
        best = matches[0] if accepted else None
        return MatchResponse(
            status='Match found' if accepted else 'No suitable match' if query else 'Invalid query',
            faq_id=best.faq_id if best else None,
            matched_question=best.question if best else None,
            answer=best.answer if best else (
                "I couldn't find a suitable FAQ. Please rephrase your question or contact support."
                if query else 'Please enter a question.'
            ),
            category=best.category if best else None,
            similarity=matches[0].score if matches else 0.0,
            threshold=threshold, top_matches=matches,
            elapsed_ms=round((perf_counter() - started) * 1000, 2),
        )
