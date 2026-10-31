"""Independent operational review. Package constructor is bypassed in this suite.

Only exact qualified foundation fixtures and this product's bounded numerical
adapter are executed. No original-delivery runner or model provider is invoked.
"""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import threading
import types
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
PRODUCT = HERE.parent
WORKSPACE = PRODUCT.parents[3]
FOUNDATION = WORKSPACE / 'outputs/Shared_Foundation_v0.1.0-rc.1/foundation'
sys.path[:0] = [str(PRODUCT / 'src'), str(PRODUCT), str(FOUNDATION)]
# The assembler copies this exact qualified package later. Avoid any source edit
# merely to make the current root imports available for narrow behavior tests.
native_package = types.ModuleType('native')
native_package.__path__ = [str(PRODUCT / 'qualification')]
sys.modules['native'] = native_package
from component_foundation.runtime import Foundation
from component_foundation.safety import FoundationError, read_json, atomic_json, digest
from research_toolkit.toolkit import Toolkit
from research_toolkit import toolkit as toolkit_module, storage, protocols


class Operations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.foundation = Foundation(FOUNDATION)

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix='review-', dir=HERE)
        self.base = Path(self.directory.name)
        self.state = self.base / 'state'
        self.toolkit = Toolkit.__new__(Toolkit)
        self.toolkit.root = PRODUCT
        self.toolkit.pin = 'independent-test-package'
        self.toolkit.foundation = self.foundation
        self.toolkit.protected = [FOUNDATION]

    def tearDown(self):
        self.directory.cleanup()

    def prepare(self, name='repair-positive', repetitions=1):
        return self.toolkit.prepare(self.state, name, repetitions)['protocol_id']

    def run_case(self, name='repair-positive', run_id='review', repetitions=1):
        return self.toolkit.run(self.state, self.prepare(name, repetitions), run_id=run_id)

    def fake_process(self, payload, outcome='completed', exit_code=0):
        return {'outcome': outcome, 'exit_code': exit_code, 'stdout': json.dumps(payload).encode(),
                'stderr': b'', 'elapsed_seconds': 0.001, 'argv': ['test-only'], 'cwd': '<test>',
                'environment_names': [], 'limits': {}}

    def test_real_native_negative_preserved_and_exported(self):
        result = self.run_case('repair-negative')
        self.assertEqual(result['execution'], 'completed')
        self.assertEqual(result['comparison'], 'negative')
        self.assertEqual(result['implementation_checks'], 'pass')
        self.assertEqual(result['source_claim'], 'unverified')
        self.assertEqual(result['summary']['candidate_partitions']['P2P'], {'passed': 7, 'total': 11})
        destination = self.base / 'negative-export'
        self.toolkit.export(self.state, 'review', destination)
        exported = read_json(destination / 'report.json')
        self.assertEqual(exported['result']['comparison'], 'negative')
        self.assertFalse(exported['private_rows_included'])
        self.assertEqual(set(storage.inventory(destination)), {'report.json', 'report.html', 'MANIFEST.json'})

    def test_final_labels_absent_from_method_request_and_export(self):
        rows = [{'id': f'dev{i}', 'group': f'groupd{i}', 'split': 'development', 'x': i, 'y': 2*i+1} for i in range(8)]
        rows += [{'id': f'final{i}', 'group': f'groupf{i}', 'split': 'final', 'x': i+8, 'y': 987654.125+i} for i in range(4)]
        source = self.base / 'data.json'
        source.write_text(json.dumps({'schema_version': '1.0.0', 'dataset_id': 'review', 'license': 'Authored fixture', 'rows': rows}))
        data_id = self.toolkit.register_dataset(self.state, source)['dataset_sha256']
        value = protocols.preset_protocol('linear-positive', data_id)
        protocol_id = self.toolkit.freeze(self.state, value)['protocol_id']
        result = self.toolkit.run(self.state, protocol_id, run_id='labels')
        self.assertEqual(result['execution'], 'completed')
        run = self.state / 'runs/labels'
        for role in ('baseline', 'candidate'):
            request = read_json(run / 'rep-1' / role / 'input.json')
            self.assertTrue(all(set(row) == {'id', 'x'} for row in request['final']))
            self.assertNotIn('987654.125', (run / 'rep-1' / role / 'input.json').read_text())
        destination = self.base / 'public'
        self.toolkit.export(self.state, 'labels', destination)
        public = read_json(destination / 'report.json')
        def keys(value):
            if isinstance(value, dict):
                return set(value) | set().union(*(keys(v) for v in value.values()))
            if isinstance(value, list):
                return set().union(*(keys(v) for v in value))
            return set()
        self.assertFalse(keys(public) & {'rows', 'per_row', 'per_case', 'predictions', 'final_labels', 'y'})
        self.assertNotIn('987654.125', json.dumps(public))

    def test_frozen_protocol_cannot_mutate_and_requires_version_reason(self):
        protocol_id = self.prepare('repair-positive')
        record = self.toolkit.protocol(self.state, protocol_id)
        altered = copy.deepcopy(record['protocol'])
        altered['hypothesis'] = 'changed'
        with self.assertRaises(FoundationError): self.toolkit.freeze(self.state, altered)
        altered['version'] = '1.0.1'
        with self.assertRaises(FoundationError): self.toolkit.freeze(self.state, altered)
        altered.update(supersedes=protocol_id, change_reason='New declared question')
        self.assertEqual(self.toolkit.freeze(self.state, altered)['protocol_id'], 'repair-positive--1.0.1')

    def test_missing_raw_output_and_receipt_corruption_refused(self):
        self.run_case('token-equivalence')
        run = self.state / 'runs/review'
        (run / 'rep-1/candidate/output.json').unlink()
        with self.assertRaises((FoundationError, FileNotFoundError)): self.toolkit.verify(self.state, 'review')
        with self.assertRaises((FoundationError, FileNotFoundError)): self.toolkit.export(self.state, 'review', self.base / 'broken')

    def test_resume_after_unknown_outcome_never_reexecutes(self):
        protocol_id = self.prepare('repair-positive')
        with patch('research_toolkit.toolkit.execute', side_effect=SystemExit('simulated crash')):
            with self.assertRaises(SystemExit): self.toolkit.run(self.state, protocol_id, run_id='crash')
        with patch('research_toolkit.toolkit.execute', side_effect=AssertionError('must not execute on resume')):
            resumed = self.toolkit.resume(self.state, 'crash')
        self.assertEqual(resumed['execution'], 'interrupted')
        self.assertEqual(resumed['comparison'], 'unavailable')
        self.assertFalse(resumed['release_eligible'])

    def test_ready_recovery_recomputes_without_execution(self):
        self.run_case('repair-positive')
        run = self.state / 'runs/review'
        (run / 'RECEIPT.json').unlink()
        with patch('research_toolkit.toolkit.execute', side_effect=AssertionError('must not execute on resume')):
            result = self.toolkit.resume(self.state, 'review')
        self.assertEqual(result['comparison'], 'positive')
        self.assertTrue(self.toolkit.verify(self.state, 'review')['metrics_recomputed'])

    def test_late_cancel_has_no_final_success_summary(self):
        original = toolkit_module.seal
        def cancel_before_seal(run, result):
            self.toolkit.cancel(self.state, run.name)
            return original(run, result)
        with patch('research_toolkit.toolkit.seal', cancel_before_seal):
            result = self.run_case('repair-positive')
        self.assertEqual(result['execution'], 'cancelled')
        self.assertEqual(result['comparison'], 'unavailable')
        self.assertFalse(result['release_eligible'])
        self.assertNotIn(result.get('summary', {}).get('result'), ('positive', 'negative', 'inconclusive'))
        destination = self.base / 'cancelled-export'
        self.toolkit.export(self.state, 'review', destination)
        public = read_json(destination / 'report.json')
        self.assertNotIn(public['result'].get('summary', {}).get('result'), ('positive', 'negative', 'inconclusive'))

    def test_failed_and_incomplete_runs_are_not_pooled(self):
        self.run_case('repair-positive', 'good')
        protocol_id = self.prepare('repair-positive')
        with patch('research_toolkit.toolkit.execute', return_value=self.fake_process({}, 'timeout', -1)):
            result = self.toolkit.run(self.state, protocol_id, run_id='bad')
        self.assertEqual(result['execution'], 'failed')
        comparison = self.toolkit.compare(self.state, 'good', 'bad')
        self.assertEqual(comparison['comparison'], 'unavailable')
        self.assertEqual(comparison['right']['execution'], 'failed')
        with patch('research_toolkit.toolkit.execute', side_effect=SystemExit('crash')):
            with self.assertRaises(SystemExit): self.toolkit.run(self.state, protocol_id, run_id='incomplete')
        with self.assertRaises((FoundationError, FileNotFoundError)):
            self.toolkit.compare(self.state, 'good', 'incomplete')

    def test_incompatible_comparison_retains_individual_negative_result(self):
        self.run_case('repair-positive', 'repair')
        self.run_case('token-negative', 'negative')
        result = self.toolkit.compare(self.state, 'repair', 'negative')
        self.assertEqual(result['comparison'], 'incomparable')
        self.assertEqual(result['right']['comparison'], 'negative')

    def test_duplicate_run_identity_does_not_change_completed_evidence(self):
        result = self.run_case('repair-positive')
        run = self.state / 'runs/review'
        before = storage.inventory(run)
        with self.assertRaises((FoundationError, FileExistsError)):
            self.toolkit.run(self.state, result['protocol_id'], run_id='review')
        self.assertEqual(storage.inventory(run), before)

    def test_nan_and_malformed_numeric_results_become_failed_evidence(self):
        protocol_id = self.prepare('linear-positive')
        malformed = {'schema_version': '1.0.0', 'method': 'mean-baseline', 'predictions': [], 'fit_details': []}
        with patch('research_toolkit.toolkit.execute', return_value=self.fake_process(malformed)):
            result = self.toolkit.run(self.state, protocol_id, run_id='malformed')
        self.assertEqual(result['execution'], 'failed')
        self.assertEqual(result['comparison'], 'unavailable')
        malformed['fit_details'] = {'fitted_on': 'development_only', 'final_labels_received': False}
        malformed['predictions'] = [{'id': 'final0', 'value': float('nan')}]
        with patch('research_toolkit.toolkit.execute', return_value=self.fake_process(malformed)):
            result = self.toolkit.run(self.state, protocol_id, run_id='nan')
        self.assertEqual(result['execution'], 'failed')

    def test_invalid_protocols_cannot_inject_commands_or_paths(self):
        base = protocols.preset_protocol('repair-positive', 'embedded')
        for field, value in [('experiment_id', 'cmd /c anything'), ('protocol_id', '../outside'),
                             ('version', '../../x'), ('repetitions', True), ('timeout_seconds', float('nan'))]:
            with self.subTest(field=field):
                modified = dict(base, **{field: value})
                with self.assertRaises(FoundationError): self.toolkit.freeze(self.state, modified)
        with self.assertRaises(FoundationError): self.toolkit.protocol(self.state, '../outside')
        with self.assertRaises(FoundationError): self.toolkit.run(self.state, self.prepare(), run_id='../outside')

    def test_report_escapes_protocol_text(self):
        value = protocols.preset_protocol('repair-positive', 'embedded')
        value['hypothesis'] = '<script>alert("data")</script><img src="https://outside.test">'
        identifier = self.toolkit.freeze(self.state, value)['protocol_id']
        self.toolkit.run(self.state, identifier, run_id='html')
        self.toolkit.export(self.state, 'html', self.base / 'html-export')
        report = (self.base / 'html-export/report.html').read_text()
        self.assertNotIn('<script>', report)
        self.assertNotIn('<img ', report)
        self.assertIn('&lt;script&gt;', report)
        self.assertIn("default-src 'none'", report)

    def test_dataset_metadata_and_protocol_timestamp_tampering_refused(self):
        identifier = self.prepare('linear-positive')
        record = self.toolkit.protocol(self.state, identifier)
        identity = record['protocol']['dataset_sha256']
        metadata = self.state / 'datasets' / identity / 'MANIFEST.json'
        info = read_json(metadata)
        info['license'] = 'tampered metadata'
        metadata.write_text(json.dumps(info))
        with self.assertRaises(FoundationError): self.toolkit._dataset(self.state, identity)
        identifier = self.prepare('repair-positive')
        protocol_path = self.state / 'protocols' / (identifier + '.json')
        frozen = read_json(protocol_path)
        frozen['frozen_at'] = '1900-01-01T00:00:00Z'
        protocol_path.write_text(json.dumps(frozen))
        with self.assertRaises(FoundationError): self.toolkit.protocol(self.state, identifier)

    def test_concurrent_protocol_registration_cannot_bypass_version_chain(self):
        self.toolkit.state(self.state)
        entered, permit = threading.Event(), threading.Event()
        result = []
        original = toolkit_module.atomic_json
        value = protocols.preset_protocol('repair-positive', 'embedded')
        def held_write(path, content, *args, **kwargs):
            if Path(path).name == 'repair-positive--1.0.0.json':
                entered.set()
                if not permit.wait(10): raise RuntimeError('review timeout')
            return original(path, content, *args, **kwargs)
        def first():
            try: result.append(self.toolkit.freeze(self.state, value))
            except Exception as exc: result.append(exc)
        thread = threading.Thread(target=first)
        try:
            with patch('research_toolkit.toolkit.atomic_json', held_write):
                thread.start()
                self.assertTrue(entered.wait(10))
                other = dict(value, version='1.0.1')
                with self.assertRaises(FoundationError): self.toolkit.freeze(self.state, other)
                permit.set()
                thread.join(10)
        finally:
            permit.set()
            thread.join(10)
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], dict)
        self.assertFalse((self.state / 'protocols/repair-positive--1.0.1.json').exists())
        self.toolkit.protocol(self.state, 'repair-positive--1.0.0')

    def test_concurrent_duplicate_run_has_single_evidence_owner(self):
        identifier = self.prepare('repair-positive')
        entered, permit = threading.Event(), threading.Event()
        results = []
        call_count = 0
        def held_execute(argv, cwd, timeout, cancel_path):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                entered.set()
                if not permit.wait(20): raise RuntimeError('review timeout')
            selected = argv[argv.index('--case') + 1]
            raw = read_json(FOUNDATION / 'baselines' / ('D0007_C0322-01--' + selected + '.json'))
            return self.fake_process(raw)
        def first():
            try: results.append(self.toolkit.run(self.state, identifier, run_id='shared'))
            except Exception as exc: results.append(exc)
        thread = threading.Thread(target=first)
        try:
            with patch('research_toolkit.toolkit.execute', held_execute):
                thread.start()
                self.assertTrue(entered.wait(20))
                with self.assertRaises((FoundationError, FileExistsError)):
                    self.toolkit.run(self.state, identifier, run_id='shared')
                permit.set()
                thread.join(20)
        finally:
            permit.set()
            thread.join(20)
        self.assertEqual(len(results), 1)
        self.assertIsInstance(results[0], dict)
        self.assertEqual(results[0]['execution'], 'completed')
        self.assertEqual(call_count, 2)
        self.toolkit.verify(self.state, 'shared')

    def test_concurrent_cancel_during_sealing_preserves_receipt(self):
        entered, permit = threading.Event(), threading.Event()
        cancellation = []
        original_atomic, original_seal = toolkit_module.atomic_json, toolkit_module.seal
        def held_write(path, value, *args, **kwargs):
            if Path(path).name == 'CANCEL.json':
                entered.set()
                if not permit.wait(10): raise RuntimeError('review timeout')
            return original_atomic(path, value, *args, **kwargs)
        def cancel():
            try: cancellation.append(self.toolkit.cancel(self.state, 'review'))
            except Exception as exc: cancellation.append(exc)
        def seal_with_cancel(run, result):
            thread = threading.Thread(target=cancel)
            thread.start()
            try:
                self.assertTrue(entered.wait(10))
                threading.Timer(.25, permit.set).start()
                return original_seal(run, result)
            finally:
                permit.set()
                thread.join(10)
        with patch('research_toolkit.toolkit.atomic_json', held_write), patch('research_toolkit.toolkit.seal', seal_with_cancel):
            result = self.run_case('repair-positive')
        self.assertEqual(result['execution'], 'cancelled')
        self.assertEqual(len(cancellation), 1)
        self.assertIsInstance(cancellation[0], dict)
        self.assertEqual(self.toolkit.inspect(self.state, 'review')['integrity'], 'pass')

    def test_deterministic_repetitions_do_not_multiply_samples(self):
        result = self.run_case('repair-positive', repetitions=2)
        self.assertEqual(result['execution'], 'completed')
        self.assertTrue(result['summary']['reproducible'])
        self.assertEqual(result['summary']['sample_count'], 14)
        self.assertEqual(result['summary']['repetitions'], 2)
        self.assertFalse(result['summary']['independence_claim'])

    def test_nonreproducible_execution_has_no_final_positive_summary(self):
        original = toolkit_module.execute
        def drift_second_candidate(argv, cwd, timeout, cancel_path):
            result = original(argv, cwd, timeout, cancel_path)
            if Path(cwd).name == 'candidate' and Path(cwd).parent.name == 'rep-2':
                payload = json.loads(result['stdout'])
                for row in payload['predictions']:
                    row['value'] += 1
                result['stdout'] = json.dumps(payload).encode('utf-8')
            return result
        with patch('research_toolkit.toolkit.execute', drift_second_candidate):
            result = self.run_case('linear-positive', repetitions=2)
        self.assertEqual(result['implementation_checks'], 'fail')
        self.assertEqual(result['comparison'], 'unavailable')
        self.assertFalse(result['release_eligible'])
        self.assertNotIn(result.get('summary', {}).get('result'), ('positive', 'negative', 'inconclusive'))
        self.toolkit.export(self.state, 'review', self.base / 'nonreproducible')
        public = read_json(self.base / 'nonreproducible/report.json')
        self.assertNotIn(public['result'].get('summary', {}).get('result'), ('positive', 'negative', 'inconclusive'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
