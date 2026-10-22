"""Deterministic scoring and API contract tests; no model download required."""
import asyncio
import csv
from pathlib import Path
import tempfile
import unittest

import httpx
import numpy as np

from backend.evaluation import Evaluator
from backend.main import create_app
from backend.matcher import FAQMatcher, tokenize
from backend.repository import CSVFAQRepository


class FixedEncoder:
    """Known normalized vectors isolate scoring and threshold behavior."""
    def encode(self, texts, **kwargs):
        vectors = {'track order': [1., 0.], 'reset password': [0., 1.],
                   'order location': [0.8, 0.6], 'unrelated': [-1., 0.]}
        return np.array([vectors[text] for text in texts])


class MatcherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.faq_file = self.root / 'faqs.csv'
        self.write_csv(self.faq_file, ['faq_id', 'category', 'question', 'answer'], [
            ['ORD001', 'Orders', 'track order', 'Use tracking.'],
            ['ACC002', 'Account', 'reset password', 'Use reset.'],
        ])
        self.matcher = FAQMatcher(CSVFAQRepository(self.faq_file), FixedEncoder())
        self.write_csv(self.root / 'semantic_faq_test_queries.csv', ['user_query', 'expected_faq_id'], [
            ['order location', 'ORD001'], ['reset password', 'MISSING'],
        ])
        self.write_csv(self.root / 'semantic_faq_additional_test_queries.csv', ['user_query', 'expected_faq_id'], [
            ['reset password', 'ACC002'],
        ])
        self.write_csv(self.root / 'semantic_faq_no_match_test_queries.csv', ['user_query'], [['unrelated']])

    @staticmethod
    def write_csv(path, columns, rows):
        with path.open('w', newline='') as stream:
            writer = csv.writer(stream); writer.writerow(columns); writer.writerows(rows)

    def test_notebook_tokenization(self):
        self.assertEqual(tokenize("Order, ORDER! #123 can't"), {'order', '123', 'can', 't'})

    def test_formula_and_query_denominator(self):
        result = self.matcher.find_answer('order location')
        self.assertEqual(result.faq_id, 'ORD001')
        self.assertAlmostEqual(result.similarity, 0.85 * 0.8 + 0.15 * 0.5)
        self.assertAlmostEqual(result.top_matches[0].semantic_similarity, 0.8)
        self.assertAlmostEqual(result.top_matches[0].keyword_overlap, 0.5)

    def test_threshold_uses_unrounded_score_and_accepts_equality(self):
        score = self.matcher.find_answer('order location').similarity
        self.assertEqual(self.matcher.find_answer('order location', score).status, 'Match found')
        rejected = self.matcher.find_answer('order location', score + 0.000001)
        self.assertIsNone(rejected.faq_id)
        self.assertIsNone(rejected.matched_question)
        self.assertEqual(len(rejected.top_matches), 2)

    def test_empty_query_does_not_encode(self):
        result = self.matcher.find_answer('  ')
        self.assertEqual(result.status, 'Invalid query')
        self.assertEqual(result.top_matches, [])

    def test_invalid_threshold(self):
        with self.assertRaises(ValueError):
            self.matcher.find_answer('track order', 1.1)

    def test_unrelated_query_is_rejected(self):
        result = self.matcher.find_answer('unrelated')
        self.assertEqual(result.status, 'No suitable match')
        self.assertIsNone(result.faq_id)

    def test_repository_rejects_duplicate_ids(self):
        with self.faq_file.open('a') as stream:
            stream.write('ORD001,Orders,another question,another answer\n')
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            CSVFAQRepository(self.faq_file).load()

    def test_repository_rejects_missing_fields(self):
        self.faq_file.write_text('faq_id,question\nX,question\n')
        with self.assertRaisesRegex(ValueError, 'missing'):
            CSVFAQRepository(self.faq_file).load()

    def test_repository_rejects_blank_fields(self):
        self.faq_file.write_text('faq_id,category,question,answer\nX,Orders,question,\n')
        with self.assertRaisesRegex(ValueError, 'complete'):
            CSVFAQRepository(self.faq_file).load()

    def test_invalid_labels_excluded_and_rejections_measured(self):
        result = Evaluator(self.matcher, self.root).run(0.45)
        original, additional, unrelated = result['datasets']
        self.assertEqual((original['count'], original['valid_count'], original['invalid_count']), (2, 1, 1))
        self.assertEqual(original['top1_accuracy'], 1)
        self.assertEqual(additional['accepted_accuracy'], 1)
        self.assertEqual(unrelated['rejection_rate'], 1)
        self.assertEqual(unrelated['false_accepts'], 0)
        self.assertIsNone(result['rows'][1]['correct'])
        self.assertEqual(result['duplicate_query_rows'], 1)

    def test_rejected_labeled_query_counts_as_incorrect(self):
        evaluator = Evaluator(self.matcher, self.root)
        result = evaluator.run(0.99)
        self.assertEqual(result['datasets'][0]['top1_accuracy'], 1)
        self.assertEqual(result['datasets'][0]['accepted_accuracy'], 0)

    def test_missing_test_files_have_null_metrics(self):
        for path in self.root.glob('semantic*.csv'):
            path.unlink()
        result = Evaluator(self.matcher, self.root).run(0.45)
        self.assertFalse(result['datasets'][0]['available'])
        self.assertIsNone(result['datasets'][0]['top1_accuracy'])

    def test_real_api_routes_and_request_validation(self):
        async def check():
            # A periodic loop wake also supports sandboxes that block thread wakeup sockets.
            async def pulse():
                while True:
                    await asyncio.sleep(0.01)
            heartbeat = asyncio.create_task(pulse())
            self.addCleanup(heartbeat.cancel)
            app = create_app(self.matcher, self.root)
            async with app.router.lifespan_context(app):
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
                    self.assertEqual((await client.get('/api/health')).json()['faq_count'], 2)
                    self.assertEqual(len((await client.get('/api/faqs?category=Orders')).json()), 1)
                    self.assertEqual((await client.get('/api/faqs?search=missing')).json(), [])
                    answer = await client.post('/api/match', json={'query': 'order location'})
                    self.assertEqual(answer.status_code, 200, answer.text)
                    self.assertEqual(answer.json()['faq_id'], 'ORD001')
                    for body in [{'query': '   '}, {'query': 'x', 'threshold': -1}, {'query': 'x' * 2001}, {'query': 'x', 'threshold': 'NaN'}]:
                        self.assertEqual((await client.post('/api/match', json=body)).status_code, 422)
                    report = await client.post('/api/evaluate', json={'threshold': 0.45})
                    self.assertEqual(report.status_code, 200, report.text)
                    self.assertEqual(report.json()['datasets'][0]['invalid_count'], 1)
                    download = await client.get('/api/dataset/download')
                    self.assertEqual(download.status_code, 200)
                    self.assertIn('text/csv', download.headers['content-type'])
        asyncio.run(check())


if __name__ == '__main__':
    unittest.main()
