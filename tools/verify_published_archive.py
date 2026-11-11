"""Verify published evidence using only local files and the Python standard library."""
from collections import Counter
from decimal import Decimal
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / 'artifacts/experiments/elice-dev30-20261111'
FINAL = ARCHIVE / 'runs/elice-dev30-10usd-20261111-recovery-4/final-analysis'

def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def check(condition, message):
    if not condition:
        raise ValueError(message)

def archived_path(original):
    normalized = original.replace('\\', '/')
    marker = '/model-lab/runs/'
    check(marker in normalized, 'unexpected historical evidence path')
    target = (ARCHIVE / 'runs' / normalized.split(marker, 1)[1]).resolve()
    check(target.is_relative_to((ARCHIVE / 'runs').resolve()), 'path outside archive')
    return target

def verify():
    manifest = read(ROOT / 'FILE_MANIFEST.json')
    for entry in manifest['files']:
        path = (ROOT / entry['path']).resolve()
        check(path.is_relative_to(ROOT), 'manifest path outside repository')
        data = path.read_bytes()
        check(len(data) == entry['bytes'], 'size mismatch: ' + entry['path'])
        check(hashlib.sha256(data).hexdigest() == entry['sha256'], 'hash mismatch: ' + entry['path'])
    provenance = read(ARCHIVE / 'publication-provenance.json')
    for entry in provenance['files']:
        check(hashlib.sha256((ROOT / entry['path']).read_bytes()).hexdigest() == entry['sha256'],
              'original copied-file hash mismatch: ' + entry['path'])
    accounting = read(FINAL / 'case-accounting.json')
    analysis = read(FINAL / 'analysis.json')
    cases = accounting['cases']
    check(len(cases) == 96, 'case slot count')
    check(len({row['model_case_key'] for row in cases}) == 96, 'duplicate case slots')
    check(Counter(row['status'] for row in cases) == Counter(
        succeeded=56, failed=23, interrupted=2, not_executed=15), 'status mismatch')
    check(all(row['review_status'] == 'unreviewed' for row in cases), 'review status changed')
    attempts = [attempt for row in cases for attempt in row['attempts']]
    check(len(attempts) == len({a['physical_attempt_id'] for a in attempts}) == 125, 'attempt reconciliation')
    check({a['physical_attempt_id'] for a in attempts} ==
          {a['physical_attempt_id'] for a in accounting['transport_attempt_index']}, 'transport coverage')
    known = [a for a in attempts if a['input_tokens'] is not None and a['output_tokens'] is not None]
    unknown = [a for a in attempts if a not in known]
    check(len(known) == 120 and len(unknown) == 5, 'missing usage count')
    check(sum(a['input_tokens'] for a in known) == 1015304, 'known input subtotal')
    check(sum(a['output_tokens'] for a in known) == 91313, 'known output subtotal')
    for side, expected in [('lower', '1.209497700'), ('upper', '1.267645900')]:
        check(sum((Decimal(a['cost_' + side + '_usd']) for a in known), Decimal(0)) == Decimal(expected),
              'known tariff ' + side)
    held = sum((Decimal(a['transport_reserved_usd']) for a in unknown), Decimal(0))
    check(held == Decimal('0.40724675'), 'unknown usage reservations')
    exposure = Decimal('1.267645900') + held
    check(exposure == Decimal('1.674892650'), 'conservative exposure')
    traces = [a['raw_trace'] for a in attempts if a.get('raw_trace')]
    check(len(traces) == 123, 'raw trace count')
    for trace in traces:
        data = archived_path(trace['path']).read_bytes()
        check(hashlib.sha256(data).hexdigest() == trace['sha256'], 'raw trace fingerprint mismatch')
    check(analysis['semantic_judge_calls'] == 0 and analysis['approved_accuracy_denominator'] == 0,
          'unreviewed diagnostic status')
    check(analysis['cost']['cost_usd'] is None, 'actual total must remain unknown')
    for case_id in {row['case_id'] for row in cases}:
        check((ROOT / 'docs/experiment/cases' / (case_id + '.md')).is_file(), 'case page missing')
    return {'status': 'verified', 'manifest_files': len(manifest['files']), 'case_slots': 96,
        'physical_attempts': 125, 'raw_responses': 123, 'usage_unknown_attempts': 5,
        'known_tariff_lower_usd': '1.209497700', 'known_tariff_upper_usd': '1.267645900',
        'conservative_exposure_usd': str(exposure), 'actual_invoice_total_usd': None,
        'review_status': 'unreviewed', 'api_calls': 0}

if __name__ == '__main__':
    print(json.dumps(verify(), ensure_ascii=False, indent=2))
