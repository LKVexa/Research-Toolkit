"""Frozen payload and tamper tests; no original or adapter code execution."""
import copy
import json
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
FOUNDATION = HERE.parents[4] / 'outputs/Shared_Foundation_v0.1.0-rc.1/foundation'
sys.path.insert(0, str(HERE))
from native import QualificationError, measure


def payload(component='D0007/C0322-01', case='correct'):
    return json.loads((FOUNDATION / 'baselines' / (component.replace('/', '_') + '--' + case + '.json')).read_text(encoding='utf-8'))


class NativeMeasurementTests(unittest.TestCase):
    def test_all_eight_supported_frozen_cases(self):
        for component, cases in [('D0001/C0081-03', {'baseline': (4, 4, True), 'negative-control': (1, 4, False)}),
                                 ('D0007/C0322-01', {'initial': (11, 14, False), 'correct': (14, 14, True), 'regression': (10, 14, False)}),
                                 ('D0007/C0322-02', {'initial': (11, 14, False), 'correct': (14, 14, True), 'regression': (10, 14, False)})]:
            for case, (passed, total, accepted) in cases.items():
                with self.subTest(component=component, case=case):
                    result = measure(payload(component, case), component, case)
                    self.assertEqual(result['score'], passed / total)
                    self.assertEqual(result['sample_count'], total)
                    self.assertEqual(sum(row['pass'] for row in result['per_case']), passed)
                    self.assertIs(result['candidate_accepted'], accepted)
                    self.assertEqual(set(result['pins']), {'foundation', 'oracle', 'method', 'data'})

    def test_negative_candidate_is_valid_negative_measurement(self):
        result = measure(payload(case='regression'), 'D0007/C0322-01', 'regression')
        self.assertEqual(result['partitions'], {'F2P': {'passed': 3, 'total': 3}, 'P2P': {'passed': 7, 'total': 11}})
        self.assertFalse(result['candidate_accepted'])

    def test_data_identity_does_not_inflate_across_component_aliases(self):
        left = measure(payload(), 'D0007/C0322-01', 'correct')
        right = measure(payload('D0007/C0322-02'), 'D0007/C0322-02', 'correct')
        self.assertEqual(left['pins']['data'], right['pins']['data'])
        self.assertEqual(left['per_case'], right['per_case'])

    def test_selection_does_not_depend_on_array_order(self):
        value = payload()
        value['records']['observations'].reverse()
        value['records']['inputs'].reverse()
        value['records']['totals'].reverse()
        value['metrics']['totals'].reverse()
        for variant in ('correct', 'regression'):
            value['records'][variant]['rows'].reverse()
        self.assertEqual(measure(value, 'D0007/C0322-01', 'correct')['score'], 1)

    def test_malformed_or_forged_d7_evidence_rejected(self):
        edits = [
            lambda p: p['records']['observations'].pop(),
            lambda p: p['records']['observations'].append(copy.deepcopy(p['records']['observations'][0])),
            lambda p: p['records']['observations'][1].update(outcome='value:99'),
            lambda p: p['records']['observations'][1].update(execution_state='runtime_error'),
            lambda p: p['records']['observations'][1].update(call_ordinal=True),
            lambda p: p['records']['observations'][1].update(split='different'),
            lambda p: p['records']['observations'][1].update(outcome='value:NaN'),
            lambda p: p['records']['observations'][1].update(outcome='value:9223372036854775808'),
            lambda p: p['records']['inputs'][0]['arguments'].append(9),
            lambda p: p['records']['totals'][0].update(passed=8),
            lambda p: p['metrics']['totals'][0].update(passed=7),
            lambda p: p['metrics'].update(p2p_total=True),
            lambda p: p.update(candidate_accepted=False),
            lambda p: p['provenance'].update(dataset_manifest_sha256='0' * 64),
            lambda p: p['checks'][0].update(status='fail'),
            lambda p: p['records']['correct'].update(accepted=False),
            lambda p: p['records']['correct']['rows'][0].update(after='value:99'),
            lambda p: p['records']['regression'].update(regressions=[]),
        ]
        for index, edit in enumerate(edits):
            with self.subTest(edit=index):
                value = payload()
                edit(value)
                with self.assertRaises(QualificationError):
                    measure(value, 'D0007/C0322-01', 'correct')

    def test_malformed_or_forged_d1_evidence_rejected(self):
        edits = [
            lambda p: p['records']['checks'].pop('empty'),
            lambda p: p['records']['checks']['known_example'].update(observed=True),
            lambda p: p['records']['checks']['known_example'].update(observed=15),
            lambda p: p['records']['checks']['known_example'].update(expected=15),
            lambda p: p['candidate_checks'][0].update(actual=30),
            lambda p: p['metrics'].update(check_pass=1),
            lambda p: p.update(candidate_accepted=False),
        ]
        for index, edit in enumerate(edits):
            with self.subTest(edit=index):
                value = payload('D0001/C0081-03', 'baseline')
                edit(value)
                with self.assertRaises(QualificationError):
                    measure(value, 'D0001/C0081-03', 'baseline')

    def test_coordinated_summary_edits_conflict_with_literal_diagnostics(self):
        value = payload()
        observation = next(row for row in value['records']['observations'] if row['observation_id'] == 'DEV-T01:correct')
        observation['outcome'] = 'value:99'
        for rows in (value['records']['totals'], value['metrics']['totals']):
            row = next(row for row in rows if row['variant'] == 'correct' and row['task_id'] == 'DEV-CLAMP')
            row.update(passed=7, P2P_passed=5)
        value['metrics']['correct_p2p_preserved'] = 10
        trace = value['records']['correct']
        trace.update(accepted=False, p2p_preserved=10, downstream_status='reject', regressions=['DEV-T01'])
        row = next(row for row in trace['rows'] if row['case_id'] == 'DEV-T01')
        row.update(after='value:99', preserved=False)
        value['candidate_accepted'] = False
        with self.assertRaises(QualificationError):
            measure(value, 'D0007/C0322-01', 'correct')

    def test_ambiguous_or_unqualified_requests_rejected(self):
        for component, case in [('D0007/C0322-01', 'all'), ('D0002/P0113-01', 'baseline'),
                                ('D0001/C0081-03', 'correct')]:
            with self.subTest(component=component, case=case), self.assertRaises(QualificationError):
                measure(payload(), component, case)
        with self.assertRaises(QualificationError):
            measure({'component_id': 'D0007/C0322-01'}, 'D0007/C0322-01', 'correct')


if __name__ == '__main__':
    unittest.main(verbosity=2)
