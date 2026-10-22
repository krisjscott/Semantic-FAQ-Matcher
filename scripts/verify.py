"""Exercise a running API with the real model and save reproducible measurements.

Run from the project root: python3 scripts/verify.py
"""
import argparse
import asyncio
import csv
import json
from pathlib import Path
import sys

import httpx


async def verify(client: httpx.AsyncClient, output_path: str):
    metadata_response = await client.get('/api/metadata'); metadata_response.raise_for_status()
    metadata = metadata_response.json()
    faqs_response = await client.get('/api/faqs'); faqs_response.raise_for_status()
    faqs = faqs_response.json()
    assert len(faqs) == metadata['faq_count']
    for faq in faqs:
        response = await client.post('/api/match', json={'query': faq['question']})
        response.raise_for_status()
        result = response.json()
        assert result['top_matches'][0]['score'] >= 0.99, result
        for candidate in result['top_matches']:
            expected = 0.85 * candidate['semantic_similarity'] + 0.15 * candidate['keyword_overlap']
            assert abs(candidate['score'] - expected) < 1e-7
    assert (await client.post('/api/match', json={'query': '  '})).status_code == 422
    response = await client.post('/api/evaluate', json={'threshold': 0.45})
    response.raise_for_status()
    report = response.json()
    for dataset in report['datasets']:
        valid = [row for row in report['rows'] if row['dataset'] == dataset['key'] and row['valid_label']]
        assert len(valid) == dataset['valid_count']
        metric = 'accepted_accuracy' if dataset['labeled'] else 'rejection_rate'
        expected = sum(row['correct'] for row in valid) / len(valid) if valid else None
        assert dataset[metric] == expected
    output = Path(output_path); output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({'metadata': metadata, **report}, indent=2) + '\n')
    csv_path = output.with_suffix('.csv')
    fields = ['dataset', 'query', 'expected_faq_id', 'valid_label', 'predicted_faq_id', 'score', 'top1_correct', 'top3_correct', 'correct']
    with csv_path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction='ignore')
        writer.writeheader(); writer.writerows(report['rows'])
    print(f"Verified {len(faqs)} FAQ self-queries and {len(report['rows'])} supplied test rows.")
    for dataset in report['datasets']:
        print(dataset['name'], json.dumps({k: dataset[k] for k in ['valid_count', 'invalid_count', 'top1_accuracy', 'top3_accuracy', 'accepted_accuracy', 'rejection_rate']}))
    print(f'Results: {output} and {csv_path}')

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://127.0.0.1:8000')
    parser.add_argument('--output', default='artifacts/evaluation.json')
    parser.add_argument('--in-process', action='store_true', help='Exercise real ASGI routes without TCP sockets')
    args = parser.parse_args()
    if args.in_process:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        from backend.main import create_app
        app = create_app()
        async def pulse():
            while True:
                await asyncio.sleep(0.01)
        heartbeat = asyncio.create_task(pulse())
        try:
            async with app.router.lifespan_context(app):
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
                    await verify(client, args.output)
        finally:
            heartbeat.cancel()
    else:
        async with httpx.AsyncClient(base_url=args.url, timeout=180) as client:
            await verify(client, args.output)


if __name__ == '__main__':
    asyncio.run(main())
