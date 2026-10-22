"""CSV storage boundary. A future SQL repository can implement the same contract."""
from pathlib import Path
from typing import Protocol

import pandas as pd
from pydantic import BaseModel, ConfigDict


class FAQ(BaseModel):
    model_config = ConfigDict(frozen=True)
    faq_id: str
    category: str
    question: str
    answer: str


class FAQRepository(Protocol):
    def load(self) -> list[FAQ]: ...


class CSVFAQRepository:
    def __init__(self, path: Path):
        self.path = path

    def load(self) -> list[FAQ]:
        frame = pd.read_csv(self.path, dtype=str, keep_default_na=False)
        frame.columns = frame.columns.str.strip().str.lower()
        fields = list(FAQ.model_fields)
        missing = set(fields) - set(frame.columns)
        if missing:
            raise ValueError(f"FAQ CSV is missing columns: {', '.join(sorted(missing))}")
        frame = frame[fields].apply(lambda col: col.str.strip())
        frame['faq_id'] = frame['faq_id'].str.upper()
        if frame.empty or (frame == '').any().any():
            raise ValueError('FAQ CSV must contain complete, nonempty records.')
        if frame['faq_id'].duplicated().any():
            raise ValueError('FAQ CSV contains duplicate FAQ IDs.')
        return [FAQ(**row) for row in frame.to_dict(orient='records')]
