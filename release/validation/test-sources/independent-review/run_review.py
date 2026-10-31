"""Run operational review and bind evidence to the exact source bytes tested."""
import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
PRODUCT = HERE.parent
FILES = ['src/research_toolkit/' + name + '.py' for name in ('toolkit', 'protocols', 'storage', 'execution', 'reporting')]
FILES += ['numerical/' + name + '.py' for name in ('adapter', 'data', 'metrics')]
FILES += ['qualification/native.py', 'qualification/oracles.json', 'independent-review/test_operations.py']


def hashes():
    return {name: hashlib.sha256((PRODUCT / name).read_bytes()).hexdigest() for name in FILES}


before = hashes()
process = subprocess.run([sys.executable, '-I', '-B', str(HERE / 'test_operations.py')],
                         cwd=PRODUCT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
after = hashes()
(HERE / 'operational-test-output.txt').write_text(process.stdout, encoding='utf-8')
matched = re.search(r'Ran (\d+) tests in ([0-9.]+)s', process.stdout)
passed = process.returncode == 0 and before == after
report = {
    'schema_version': '1.0.0', 'status': 'pass' if passed else 'blocked',
    'reviewed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'exit_code': process.returncode, 'test_count': int(matched[1]) if matched else None,
    'elapsed_seconds': float(matched[2]) if matched else None,
    'source_unchanged_during_tests': before == after, 'source_sha256_before': before,
    'source_sha256_after': after,
    'scope': 'Independent operational review using real bounded native/numerical child executions plus explicit fault-injection and concurrency tests.',
    'foundation_manifest_pin': 'e01d3f340239f4abe0daa27cb3e7c64190f95f4f3a0419f493bc14e7b07d571d',
    'original_delivery_execution': False, 'model_calls': 0, 'source_files_edited_by_reviewer': False,
    'limitation': 'The narrow test fixture bypasses Toolkit construction. Exact assembled package, embedded dependency identity, launcher and release evidence still need separate acceptance.',
    'findings': [
        {'id': 'ops-001', 'severity': 'medium', 'status': 'remediated' if passed else 'requires_test_review',
         'finding': 'A cancellation arriving after evaluation but before sealing retained a positive public summary and successful implementation flag.',
         'remediation': 'Late cancellation now sets implementation status unverified and omits the public summary, while private evidence remains preserved.'},
        {'id': 'ops-002', 'severity': 'medium', 'status': 'remediated' if passed else 'requires_test_review',
         'finding': 'Incompatible comparisons omitted each completed run outcome from the response, including a negative result.',
         'remediation': 'The incomparable response retains both complete individual public results without pooling their scores.'},
        {'id': 'ops-003', 'severity': 'medium', 'status': 'remediated' if passed else 'requires_test_review',
         'finding': 'A malformed numerical fit_details list caused uncaught AttributeError and prevented a failed terminal receipt.',
         'remediation': 'Numerical payloads now validate fit metadata and predictions before access; malformed and non-finite outputs produce sealed failed evidence.'},
        {'id': 'ops-004', 'severity': 'medium', 'status': 'remediated' if passed else 'requires_test_review',
         'finding': 'Failed reproducibility retained a positive first-repetition public summary despite the unavailable overall comparison.',
         'remediation': 'The public result omits final summary scores when reproducibility fails; independent verification still recomputes all private comparisons.'},
    ],
    'additional_boundaries_verified': ['Final labels absent from method requests and public exports',
        'Negative results remain exportable with source claims unverified', 'Protocol content, timestamp and version-chain protection',
        'Dataset metadata receipt integrity', 'Concurrent protocol registration and duplicate run ownership',
        'Concurrent cancellation/finalization receipt consistency', 'Recovery never reexecutes unknown child outcomes',
        'Completed output can be independently recomputed after interrupted receipt sealing',
        'Missing outputs, NaN and malformed records fail closed', 'Failed/incomplete runs are not pooled',
        'Deterministic repetitions do not multiply sample counts', 'Protocol text is escaped in script-free public HTML'],
    'stdout': 'operational-test-output.txt',
}
(HERE / 'OPERATIONAL-REVIEW.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(process.stdout)
print(json.dumps({'status': report['status'], 'tests': report['test_count'],
                  'source_unchanged': before == after, 'report': str(HERE / 'OPERATIONAL-REVIEW.json')}))
raise SystemExit(0 if passed else 1)
