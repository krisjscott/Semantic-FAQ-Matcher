from typing import Literal

from pydantic import BaseModel, Field, field_validator

from .repository import FAQ


class MatchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    threshold: float = Field(default=0.45, ge=0, le=1)

    @field_validator('query')
    @classmethod
    def trim_query(cls, value: str) -> str:
        if not value.strip():
            raise ValueError('Please enter a question.')
        return value.strip()


class Candidate(FAQ):
    score: float
    semantic_similarity: float
    keyword_overlap: float


class MatchResponse(BaseModel):
    status: Literal['Match found', 'No suitable match', 'Invalid query']
    faq_id: str | None
    matched_question: str | None
    answer: str
    category: str | None
    similarity: float
    threshold: float
    top_matches: list[Candidate]
    elapsed_ms: float


class EvaluationRequest(BaseModel):
    threshold: float = Field(default=0.45, ge=0, le=1)
