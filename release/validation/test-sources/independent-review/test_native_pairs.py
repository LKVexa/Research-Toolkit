"""Focused follow-up for the added native paired descriptive statistics."""
import math
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from test_operations import Operations, Foundation, FOUNDATION, protocols, read_json


class NativePairs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.foundation = Foundation(FOUNDATION)

    setUp = Operations.setUp
    tearDown = Operations.tearDown
    prepare = Operations.prepare
    run_case = Operations.run_case

    def run_tolerance(self, name, tolerance, repetitions=1):
        value = protocols.preset_protocol('repair-positive', 'embedded', repetitions)
        value.update(protocol_id=name, absolute_tolerance=tolerance)
        identifier = self.toolkit.freeze(self.state, value)['protocol_id']
        return self.toolkit.run(self.state, identifier, run_id=name)

    def test_exact_three_fourteenths_boundary_is_inconclusive(self):
        result = self.run_tolerance('exact-boundary', 3 / 14, repetitions=2)
        summary = result['summary']
        self.assertEqual(result['comparison'], 'inconclusive')
        self.assertEqual(summary['mean_improvement'], 3 / 14)
        self.assertEqual(summary['dispersion']['mean'], 3 / 14)
        self.assertEqual(summary['dispersion']['count'], 14)
        self.assertEqual(summary['sample_count'], 14)
        self.assertEqual(summary['repetitions'], 2)
        self.assertEqual(summary['dispersion']['min'], 0)
        self.assertEqual(summary['dispersion']['max'], 1)
        self.assertAlmostEqual(summary['dispersion']['population_sd'], math.sqrt(33) / 14, places=14)
        self.assertFalse(summary['independence_claim'])
        self.assertEqual(summary['inference'], 'descriptive_only')
        self.assertTrue(self.toolkit.verify(self.state, 'exact-boundary')['metrics_recomputed'])
        self.toolkit.export(self.state, 'exact-boundary', self.base / 'boundary-export')
        public = read_json(self.base / 'boundary-export/report.json')
        self.assertEqual(public['result']['summary']['dispersion'], summary['dispersion'])
        self.assertNotIn('per_case', str(public))
        self.assertNotIn('per_row', str(public))
        self.assertEqual(public['result']['source_claim'], 'unverified')

    def test_adjacent_float_tolerances_have_correct_direction(self):
        below = self.run_tolerance('below-boundary', math.nextafter(3 / 14, 0))
        above = self.run_tolerance('above-boundary', math.nextafter(3 / 14, math.inf))
        self.assertEqual(below['comparison'], 'positive')
        self.assertEqual(above['comparison'], 'inconclusive')
        self.assertEqual(below['summary']['mean_improvement'], above['summary']['mean_improvement'])

    def test_negative_token_paired_score_and_population_sd(self):
        result = self.run_case('token-negative', 'token-negative')
        summary = result['summary']
        self.assertEqual(result['comparison'], 'negative')
        self.assertEqual(summary['candidate_score'], 0.25)
        self.assertEqual(summary['baseline_score'], 1)
        self.assertEqual(summary['mean_improvement'], -0.75)
        self.assertEqual(summary['sample_count'], 4)
        self.assertEqual(summary['dispersion']['count'], 4)
        self.assertEqual(summary['dispersion']['min'], -1)
        self.assertEqual(summary['dispersion']['max'], 0)
        self.assertAlmostEqual(summary['dispersion']['population_sd'], math.sqrt(3) / 4, places=14)
        self.assertTrue(self.toolkit.verify(self.state, 'token-negative')['metrics_recomputed'])
        self.toolkit.export(self.state, 'token-negative', self.base / 'negative-export')
        public = read_json(self.base / 'negative-export/report.json')
        self.assertEqual(public['result']['summary']['mean_improvement'], -0.75)
        self.assertEqual(public['result']['summary']['dispersion'], summary['dispersion'])
        self.assertEqual(public['result']['comparison'], 'negative')

    def test_equivalent_native_zero_dispersion_is_not_significance(self):
        result = self.run_case('token-equivalence')
        summary = result['summary']
        self.assertEqual(result['comparison'], 'inconclusive')
        self.assertEqual(summary['dispersion'], {'count': 4, 'mean': 0, 'population_sd': 0, 'min': 0, 'max': 0})
        self.assertEqual(summary['sample_count'], 4)
        self.assertFalse(summary['independence_claim'])
        self.assertEqual(summary['inference'], 'descriptive_only')


if __name__ == '__main__':
    unittest.main(verbosity=2)
