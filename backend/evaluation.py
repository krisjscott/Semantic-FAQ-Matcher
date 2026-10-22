"""Evaluate supplied labels; keep invalid references visible and unscored."""
from collections import Counter
from datetime import datetime, timezone
from functools import lru_cache
from hashlib import sha256
from pathlib import Path
from threading import Lock

import pandas as pd

from .matcher import FAQMatcher, MODEL_NAME

TEST_FILES = {
    'original': ('Original queries', 'semantic_faq_test_queries.csv', True),
    'additional': ('Additional queries', 'semantic_faq_additional_test_queries.csv', True),
    'unrelated': ('Unrelated queries', 'semantic_faq_no_match_test_queries.csv', False),
}


def rate(values: list[bool]) -> float | None:
    return sum(values) / len(values) if values else None


class Evaluator:
    def __init__(self, matcher: FAQMatcher, data_dir: Path):
        self.matcher = matcher
        self.data_dir = data_dir
        self._lock = Lock()

    def inventory(self) -> list[dict]:
        inventory = []
        for key, (name, filename, labeled) in TEST_FILES.items():
            path = self.data_dir / filename
            inventory.append(dict(key=key, name=name, filename=filename, labeled=labeled,
                                  available=path.is_file(),
                                  count=len(self._load(path, labeled)) if path.is_file() else 0))
        return inventory

    def _load(self, path: Path, labeled: bool) -> list[dict]:
        frame = pd.read_csv(path, dtype=str, keep_default_na=False)
        required = {'user_query', 'expected_faq_id'} if labeled else {'user_query'}
        if not required.issubset(frame.columns):
            raise ValueError(f'{path.name} requires columns: {sorted(required)}')
        for field in required:
            frame[field] = frame[field].str.strip()
            if (frame[field] == '').any():
                raise ValueError(f'{path.name} has empty {field} values.')
        if labeled:
            frame['expected_faq_id'] = frame['expected_faq_id'].str.upper()
        return frame.to_dict(orient='records')

    @lru_cache(maxsize=1)
    def _ranked(self) -> list[dict]:
        ids = {faq.faq_id for faq in self.matcher.faqs}
        records = []
        for key, (_, filename, labeled) in TEST_FILES.items():
            path = self.data_dir / filename
            if not path.is_file():
                continue
            rows = self._load(path, labeled)
            matches = self.matcher.rank_many([row['user_query'] for row in rows])
            for row, candidates in zip(rows, matches):
                expected = row.get('expected_faq_id')
                records.append(dict(dataset=key, query=row['user_query'], expected_faq_id=expected,
                                    valid_label=expected in ids if labeled else True,
                                    candidates=[c.faq_id for c in candidates], score=candidates[0].score))
        return records

    def run(self, threshold: float) -> dict:
        # Protect first cache fill; scores are immutable for this process's data snapshot.
        with self._lock:
            ranked = self._ranked()
        rows = []
        for row in ranked:
            prediction = row['candidates'][0] if row['score'] >= threshold else None
            expected = row['expected_faq_id']
            valid = row['valid_label']
            rows.append({**row, 'predicted_faq_id': prediction,
                         'top1_correct': row['candidates'][0] == expected if valid and expected else None,
                         'top3_correct': expected in row['candidates'] if valid and expected else None,
                         'correct': prediction == expected if valid else None})
        summaries = []
        for info in self.inventory():
            group = [r for r in rows if r['dataset'] == info['key']]
            valid = [r for r in group if r['valid_label']]
            summaries.append({**info, 'valid_count': len(valid),
                              'invalid_count': len(group) - len(valid),
                              'top1_accuracy': rate([r['top1_correct'] for r in valid]) if info['labeled'] else None,
                              'top3_accuracy': rate([r['top3_correct'] for r in valid]) if info['labeled'] else None,
                              'accepted_accuracy': rate([r['correct'] for r in valid]) if info['labeled'] else None,
                              'rejection_rate': rate([r['predicted_faq_id'] is None for r in valid]) if not info['labeled'] else None,
                              'false_accepts': sum(r['predicted_faq_id'] is not None for r in valid) if not info['labeled'] else None})
        sweep = []
        for t in [round(i / 100, 2) for i in range(20, 81, 5)]:
            labeled = [r for r in ranked if r['expected_faq_id'] and r['valid_label']]
            unrelated = [r for r in ranked if r['dataset'] == 'unrelated']
            sweep.append(dict(threshold=t,
                              correct_match_rate=rate([r['score'] >= t and r['candidates'][0] == r['expected_faq_id'] for r in labeled]),
                              rejection_rate=rate([r['score'] < t for r in unrelated])))
        counts = Counter(r['query'].strip().lower() for r in rows)
        return dict(threshold=threshold, model=MODEL_NAME,
                    measured_at=datetime.now(timezone.utc).isoformat(),
                    datasets=summaries, rows=rows, threshold_sweep=sweep,
                    duplicate_query_rows=sum(n - 1 for n in counts.values()),
                    test_sha256={f: sha256((self.data_dir / f).read_bytes()).hexdigest()
                                 for _, f, _ in TEST_FILES.values() if (self.data_dir / f).is_file()})
