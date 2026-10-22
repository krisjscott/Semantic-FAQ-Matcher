"""Audit original-source hashes and label references without modifying the data."""
import csv
from hashlib import sha256
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    manifest = json.loads((ROOT / 'backend/data/provenance.json').read_text())
    for item in manifest:
        path = ROOT / item['path']
        assert sha256(path.read_bytes()).hexdigest() == item['sha256'], f'Source changed: {path}'
    with (ROOT / 'backend/semantic_faq_dataset.csv').open() as stream:
        faqs = list(csv.DictReader(stream))
    ids = {faq['faq_id'] for faq in faqs}
    print(f'{len(faqs)} FAQs, {len(ids)} unique IDs, all source hashes verified.')
    for filename in ['semantic_faq_test_queries.csv', 'semantic_faq_additional_test_queries.csv']:
        with (ROOT / 'backend/data' / filename).open() as stream:
            rows = list(csv.DictReader(stream))
        invalid = [row for row in rows if row['expected_faq_id'].strip().upper() not in ids]
        print(f'{filename}: {len(rows)} rows; {len(invalid)} unknown expected IDs.')
        for row in invalid:
            print('  Excluded from accuracy:', row)


if __name__ == '__main__':
    main()
