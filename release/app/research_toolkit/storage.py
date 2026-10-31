"""Research-owned storage. Shared foundation supplies paths, JSON, hashes and locks."""
import datetime as dt
import os
import time
from contextlib import contextmanager
from pathlib import Path

from component_foundation.safety import FoundationError, RunLock, atomic_json, digest, inside, no_links, read_json, sha256, valid_run_id

PIN = 'e01d3f340239f4abe0daa27cb3e7c64190f95f4f3a0419f493bc14e7b07d571d'
LOCKS = ('run.lock', 'control.lock')


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def overlap(a, b):
    a, b = Path(a).resolve(), Path(b).resolve()
    return a == b or a in b.parents or b in a.parents


def new_destination(path, protected):
    path = Path(path).absolute()
    no_links(path)
    if path.exists() or not path.parent.is_dir():
        raise FoundationError('Use a new destination with an existing parent folder')
    if any(overlap(path, p) for p in protected):
        raise FoundationError('Destination overlaps a protected product, source or state folder')
    return path


def inventory(root, excluded=()):
    result = {}
    for path in sorted(Path(root).rglob('*')):
        no_links(path)
        if path.is_file():
            rel = path.relative_to(root).as_posix()
            if rel not in excluded:
                result[rel] = sha256(path)
    return result


def verify_files(root, files, excluded=(), exact=True):
    if not isinstance(files, dict) or not files:
        raise FoundationError('Empty artifact inventory')
    for relative, expected in files.items():
        path = inside(root, relative)
        if not path.is_file() or sha256(path) != expected:
            raise FoundationError('Artifact integrity mismatch: ' + relative)
    if exact and set(inventory(root, excluded)) != set(files):
        raise FoundationError('Unexpected or missing artifact')


def state_root(path, protected):
    path = Path(path).absolute()
    no_links(path)
    if any(overlap(path, p) for p in protected):
        raise FoundationError('State overlaps a protected product or original delivery')
    marker = path / 'STATE.json'
    if path.exists() and not marker.exists() and any(path.iterdir()):
        raise FoundationError('State folder contains unrelated files')
    path.mkdir(parents=True, exist_ok=True)
    expected = {'product':'research-replication-toolkit','schema_version':'1.0.0'}
    if not marker.exists():
        atomic_json(marker, expected)
    if read_json(marker) != expected:
        raise FoundationError('Incompatible state folder')
    for part in ('datasets', 'protocols', 'runs', 'annotations'):
        no_links(path / part)
        (path / part).mkdir(exist_ok=True)
    return path.resolve()


def write_text(path, content):
    no_links(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(content.encode('utf-8')); stream.flush(); os.fsync(stream.fileno())


@contextmanager
def control_lock(run):
    end = time.monotonic() + 10
    while True:
        lock = RunLock(run / 'control.lock')
        try:
            lock.__enter__(); break
        except FoundationError as exc:
            if 'Run is still active' not in str(exc) or time.monotonic() >= end:
                raise
            time.sleep(.02)
    try:
        yield
    finally:
        lock.__exit__(None, None, None)


def seal(run, result):
    with control_lock(run):
        if (run / 'CANCEL.json').exists() and result['execution'] == 'completed':
            result.update(execution='cancelled', implementation_checks='unverified', comparison='unavailable',
                          release_eligible=False, reason='Cancellation requested before evidence was sealed')
            result.pop('summary', None)
        if (run / 'result.json').exists():
            previous = read_json(run / 'result.json')
            result['finished_at'] = previous.get('finished_at')
            if previous != result:
                raise FoundationError('Interrupted result differs from independent recovery')
        else:
            atomic_json(run / 'result.json', result)
        files = inventory(run, (*LOCKS, 'RECEIPT.json'))
        atomic_json(run / 'RECEIPT.json', {'schema_version':'1.0.0','files':files,'files_sha256':digest(files)})
    return result


def run_path(state, run_id):
    path = inside(state, 'runs/' + valid_run_id(run_id))
    if not path.is_dir():
        raise FoundationError('Unknown run')
    return path


def verify_receipt(run):
    receipt = read_json(run / 'RECEIPT.json')
    if receipt.get('schema_version') != '1.0.0' or digest(receipt.get('files')) != receipt.get('files_sha256'):
        raise FoundationError('Invalid run receipt')
    verify_files(run, receipt['files'], (*LOCKS, 'RECEIPT.json'))
    return read_json(run / 'result.json')
