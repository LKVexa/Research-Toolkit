"""Independent rational oracle and scientific boundary review of authored controls.

Expected predictions use rational normal equations, not the production adapter.
Expected metrics use a separate exact arithmetic reduction, not production metrics.
Imports of production code supply observed results only. Writes stay in this folder.
"""
from __future__ import annotations

import ast
import copy
import datetime as dt
from fractions import Fraction as F
import hashlib
import json
import math
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
PRODUCT = HERE.parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(PRODUCT))
from numerical import adapter as observed_adapter
from numerical import data as observed_data
from numerical import metrics as observed_metrics

CHECKS = []


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def rational(value):
    return F(str(value))


def oracle_predictions(dataset, method):
    train = [row for row in dataset['rows'] if row['split'] == 'development']
    n = len(train)
    sx = sum(rational(row['x']) for row in train)
    sy = sum(rational(row['y']) for row in train)
    sxx = sum(rational(row['x']) ** 2 for row in train)
    sxy = sum(rational(row['x']) * rational(row['y']) for row in train)
    slope = F(0)
    intercept = sy / n
    denominator = n * sxx - sx * sx
    if method == 'ordinary-least-squares' and denominator:
        slope = (n * sxy - sx * sy) / denominator
        intercept = (sy - slope * sx) / n
    elif method == 'zero-predictor':
        intercept = F(0)
    return {row['id']: slope * rational(row['x']) + intercept
            for row in dataset['rows'] if row['split'] == 'final'}, slope, intercept


def oracle_comparison(dataset, candidate, baseline, metric, tolerance=F(1, 10**9)):
    labels = {row['id']: rational(row['y']) for row in dataset['rows'] if row['split'] == 'final'}
    exponent = 2 if metric == 'mse' else 1
    candidate_loss = {key: abs(candidate[key] - y) ** exponent for key, y in labels.items()}
    baseline_loss = {key: abs(baseline[key] - y) ** exponent for key, y in labels.items()}
    n = len(labels)
    differences = {key: baseline_loss[key] - candidate_loss[key] for key in labels}
    mean = sum(differences.values()) / n
    variance = sum((value - mean) ** 2 for value in differences.values()) / n
    return {'candidate': sum(candidate_loss.values()) / n, 'baseline': sum(baseline_loss.values()) / n,
            'mean': mean, 'variance': variance, 'count': n,
            'result': 'positive' if mean > tolerance else 'negative' if mean < -tolerance else 'inconclusive'}


def close(left, right):
    assert math.isclose(float(left), float(right), rel_tol=1e-11, abs_tol=1e-9), (left, right)


def check(name, action):
    try:
        details = action()
        CHECKS.append({'id': name, 'result': 'pass', 'details': details})
    except Exception as exc:
        CHECKS.append({'id': name, 'result': 'fail', 'exception': type(exc).__name__, 'detail': str(exc)[:2000]})


def reject(action):
    try:
        action()
    except observed_data.NumericalError as exc:
        return {'rejection': str(exc)}
    raise AssertionError('Invalid scientific input was accepted')


def actual_predictions(dataset, method):
    result = observed_adapter.predict(observed_data.make_request(dataset, method))
    return {row['id']: row['value'] for row in result['predictions']}


def actual_comparison(dataset, candidate, baseline, metric, **kwargs):
    return observed_metrics.compare(
        {'candidate': [{'id': key, 'value': value} for key, value in candidate.items()],
         'baseline': [{'id': key, 'value': value} for key, value in baseline.items()]},
        [{'id': row['id'], 'y': row['y']} for row in dataset['rows'] if row['split'] == 'final'],
        metric, **kwargs)


def file_hashes():
    paths = [path for path in (PRODUCT / 'numerical').rglob('*') if path.is_file()]
    paths += [PRODUCT / 'src/research_toolkit/protocols.py', PRODUCT / 'R01-PLAN.json']
    return {path.relative_to(PRODUCT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(paths)}


def main():
    before = file_hashes()
    controls = read(PRODUCT / 'numerical/CONTROLS.json')
    datasets = {path.stem: read(path) for path in sorted((PRODUCT / 'numerical/datasets').glob('*.json'))}
    derived = []
    for control in controls['comparisons']:
        dataset = datasets[control['dataset']]
        expected_c, slope, intercept = oracle_predictions(dataset, control['candidate'])
        expected_b, _, mean = oracle_predictions(dataset, control['baseline'])
        observed_c = actual_predictions(dataset, control['candidate'])
        observed_b = actual_predictions(dataset, control['baseline'])
        def predictions_check():
            assert set(expected_c) == set(observed_c) == set(expected_b) == set(observed_b)
            for key in expected_c:
                close(observed_c[key], expected_c[key]); close(observed_b[key], expected_b[key])
            return {'independent_slope': str(slope), 'independent_intercept': str(intercept),
                    'independent_development_mean': str(mean)}
        prefix = control['dataset'] + '/' + control['candidate']
        check(prefix + '/predictions', predictions_check)
        for metric in ('mse', 'mae'):
            expected = oracle_comparison(dataset, expected_c, expected_b, metric)
            actual = actual_comparison(dataset, observed_c, observed_b, metric)
            def scores_check():
                close(actual['candidate_score'], expected['candidate'])
                close(actual['baseline_score'], expected['baseline'])
                close(actual['mean_improvement'], expected['mean'])
                close(actual['paired_differences']['population_sd'], math.sqrt(float(expected['variance'])))
                close(control[metric]['candidate'], expected['candidate'])
                close(control[metric]['baseline'], expected['baseline'])
                assert actual['result'] == expected['result'] == control['expected_result']
                assert actual['paired_differences']['count'] == expected['count'] == 4
                assert actual['inference'] == 'descriptive_only' and actual['independence_claim'] is False
                assert actual['stochastic_repeats'] == 0
                assert not any('confidence' in key.lower() or 'p_value' in key.lower() for key in actual)
                return {'candidate_score_exact': str(expected['candidate']), 'baseline_score_exact': str(expected['baseline']),
                        'mean_improvement_exact': str(expected['mean']), 'population_variance_exact': str(expected['variance']),
                        'result': expected['result'], 'unique_final_samples': 4}
            check(prefix + '/' + metric, scores_check)
            derived.append({'dataset': control['dataset'], 'candidate': control['candidate'], 'baseline': control['baseline'],
                            'metric': metric, 'oracle': {k: str(v) if isinstance(v, F) else v for k, v in expected.items()},
                            'observed': actual})
    base = datasets['positive-linear']

    def affine_invariants():
        evidence = []
        for method in ('ordinary-least-squares', 'mean-baseline', 'same-baseline', 'zero-predictor'):
            reference = actual_predictions(base, method)
            for name, xs, xo, ys, yo in [('x-translation', 1, 125, 1, 0), ('x-negative-scaling', -4, 0, 1, 0),
                                       ('y-negative-scaling', 1, 0, -3, 0), ('y-translation', 1, 0, 1, 17)]:
                if name == 'y-translation' and method == 'zero-predictor':
                    continue  # Fixed zero is deliberately not equivariant under response translation.
                changed = copy.deepcopy(base)
                for row in changed['rows']:
                    row['x'] = xs * row['x'] + xo; row['y'] = ys * row['y'] + yo
                observed = actual_predictions(changed, method)
                oracle, _, _ = oracle_predictions(changed, method)
                for key in observed:
                    close(observed[key], ys * reference[key] + yo)
                    close(observed[key], oracle[key])
                evidence.append({'method': method, 'transformation': name})
        return {'checks': evidence, 'zero_response_translation_excluded': 'A fixed zero predictor is not translation equivariant'}
    check('affine_prediction_invariants', affine_invariants)

    def score_scaling():
        changed = copy.deepcopy(base)
        for row in changed['rows']: row['y'] *= -3
        evidence = []
        for method in ('ordinary-least-squares', 'zero-predictor', 'same-baseline'):
            for metric, factor in (('mse', 9), ('mae', 3)):
                original = actual_comparison(base, actual_predictions(base, method), actual_predictions(base, 'mean-baseline'), metric)
                scaled = actual_comparison(changed, actual_predictions(changed, method), actual_predictions(changed, 'mean-baseline'), metric)
                for field in ('candidate_score', 'baseline_score', 'mean_improvement'):
                    close(scaled[field], factor * original[field])
                assert scaled['result'] == original['result']
                evidence.append({'method': method, 'metric': metric, 'scale_factor': factor})
        return evidence
    check('loss_scaling_and_direction_invariants', score_scaling)

    def permutation():
        changed = copy.deepcopy(base); changed['rows'].reverse()
        for method in observed_data.METHODS:
            a, b = actual_predictions(base, method), actual_predictions(changed, method)
            for key in a: close(a[key], b[key])
        left = actual_comparison(base, actual_predictions(base, 'ordinary-least-squares'), actual_predictions(base, 'mean-baseline'), 'mse')
        right = actual_comparison(changed, actual_predictions(changed, 'ordinary-least-squares'), actual_predictions(changed, 'mean-baseline'), 'mse')
        assert left == right
        return 'Row permutation preserves predictions by identity and exact comparison record'
    check('permutation_invariance', permutation)

    def final_label_exclusion():
        changed = copy.deepcopy(base)
        for row in changed['rows']:
            if row['split'] == 'final': row['y'] = 999991 - row['x']
        for method in observed_data.METHODS:
            first = observed_data.make_request(base, method)
            second = observed_data.make_request(changed, method)
            assert first == second
            assert all(set(row) == {'id', 'x'} for row in first['final'])
            assert actual_predictions(base, method) == actual_predictions(changed, method)
        return 'Changing every final label leaves all method requests and predictions unchanged'
    check('final_labels_excluded_from_method_inputs_and_fit', final_label_exclusion)

    def altered_dataset(mutator):
        value = copy.deepcopy(base); mutator(value)
        return reject(lambda: observed_data.validate_dataset(value))
    check('cross_split_group_overlap_rejected', lambda: altered_dataset(lambda d: d['rows'][8].update(group=d['rows'][0]['group'])))
    check('within_development_group_duplicate_rejected', lambda: altered_dataset(lambda d: d['rows'][1].update(group=d['rows'][0]['group'])))
    check('duplicate_row_identity_rejected', lambda: altered_dataset(lambda d: d['rows'][8].update(id=d['rows'][0]['id'])))
    check('invalid_split_rejected', lambda: altered_dataset(lambda d: d['rows'][8].update(split='test')))
    check('insufficient_development_split_rejected', lambda: altered_dataset(lambda d: d['rows'][0].update(split='final')))
    check('insufficient_final_split_rejected', lambda: altered_dataset(lambda d: d['rows'][8].update(split='development')))
    check('nonfinite_label_rejected', lambda: altered_dataset(lambda d: d['rows'][8].update(y=float('nan'))))

    def leaked_request():
        request = observed_data.make_request(base, 'ordinary-least-squares'); request['final'][0]['y'] = 11
        return reject(lambda: observed_adapter.predict(request))
    check('explicit_final_label_in_request_rejected', leaked_request)

    def infeasible():
        request = observed_data.make_request(base, 'ordinary-least-squares')
        for index, row in enumerate(request['dev']): row.update(x=index * 1e-13, y=index)
        return reject(lambda: observed_adapter.predict(request))
    check('infeasible_derived_slope_rejected_without_score', infeasible)

    def degenerate():
        dataset = copy.deepcopy(base)
        for row in dataset['rows']:
            if row['split'] == 'development': row['x'] = 1
        result = observed_adapter.predict(observed_data.make_request(dataset, 'ordinary-least-squares'))
        expected, _, _ = oracle_predictions(dataset, 'ordinary-least-squares')
        for row in result['predictions']: close(row['value'], expected[row['id']])
        assert result['fit_details']['degenerate_development_x'] is True
        assert result['fit_details']['slope'] == 0
        return 'Unidentifiable slope uses the declared slope-zero/development-mean tie-break'
    check('degenerate_fit_tie_break_matches_independent_oracle', degenerate)

    def invalid_predictions():
        candidate = actual_predictions(base, 'ordinary-least-squares')
        baseline = actual_predictions(base, 'mean-baseline')
        candidate.pop(next(iter(candidate)))
        return reject(lambda: actual_comparison(base, candidate, baseline, 'mse'))
    check('missing_prediction_rejected_not_positive', invalid_predictions)

    def tolerance_and_direction():
        c, b = actual_predictions(base, 'ordinary-least-squares'), actual_predictions(base, 'mean-baseline')
        exact_boundary = actual_comparison(base, c, b, 'mse', tolerance=149)
        inside = actual_comparison(base, c, b, 'mse', tolerance=150)
        outside = actual_comparison(base, c, b, 'mse', tolerance=148)
        reverse = actual_comparison(base, c, b, 'mse', direction='maximize')
        assert exact_boundary['result'] == inside['result'] == 'inconclusive'
        assert outside['result'] == 'positive' and reverse['result'] == 'negative'
        return {'boundary': 'Strict greater/less; equality is inconclusive',
                'low_level_direction': 'Generic compare can reverse direction; qualified numeric protocol must enforce minimize'}
    check('comparison_boundary_and_direction_are_not_false_positive', tolerance_and_direction)

    def repeat_count():
        results = [actual_comparison(base, actual_predictions(base, 'ordinary-least-squares'),
                                     actual_predictions(base, 'mean-baseline'), 'mse') for _ in range(3)]
        assert results[0] == results[1] == results[2]
        assert all(item['paired_differences']['count'] == 4 and item['stochastic_repeats'] == 0 for item in results)
        return {'executions': 3, 'unique_final_samples_each': 4, 'independent_samples': 4,
                'limitation': 'Actual runner aggregation remains to be reviewed after assembly'}
    check('deterministic_repeats_do_not_add_module_samples', repeat_count)

    protocol_path = PRODUCT / 'src/research_toolkit/protocols.py'
    protocol_source = protocol_path.read_text(encoding='utf-8')
    protocol_tree = ast.parse(protocol_source)
    experiments = next(ast.literal_eval(node.value) for node in protocol_tree.body
                       if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'EXPERIMENTS' for t in node.targets))
    def protocol_source_review():
        assert all(item['direction'] == ('minimize' if item['kind'] == 'numeric' else 'maximize') for item in experiments.values())
        assert "if value['direction'] != spec['direction']:" in protocol_source
        assert "'repetitions':{'type':'integer','minimum':1,'maximum':3}" in protocol_source
        assert "'seeds':{'type':'array','maxItems':0}" in protocol_source
        return {'method': 'Source inspection, not a runtime protocol-validation claim',
                'numeric_losses': 'minimize', 'native_accuracy': 'maximize', 'repetitions': '1-3 deterministic runs', 'seed_list': 'empty'}
    check('protocol_direction_and_repeat_source_contract', protocol_source_review)

    after = file_hashes()
    check('reviewed_inputs_unchanged', lambda: {'unchanged': before == after} if before == after else (_ for _ in ()).throw(AssertionError('Inputs changed during review')))
    report = {'schema_version': '1.0.0', 'review': 'independent-authored-numerical-diagnostics',
              'created_at_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
              'status': 'pass' if all(item['result'] == 'pass' for item in CHECKS) else 'fail',
              'reviewer_role': 'Separate agent from the numerical implementation and root runner',
              'oracle': 'Exact Fraction normal equations and per-row loss arithmetic; production imports supply observations only',
              'source_scope': 'Product-owned authored controls, not original delivery execution or paper replication',
              'input_hashes': before, 'checks': CHECKS, 'derived_controls': derived,
              'counts': {'pass': sum(row['result'] == 'pass' for row in CHECKS), 'fail': sum(row['result'] == 'fail' for row in CHECKS)},
              'confidence_interval_claim': False, 'paper_replication_claim': False,
              'limitations': ['Local inspectable synthetic controls; no population inference or benchmark-superiority claim',
                             'Direct module review only; actual runner reports, aggregation, export separation and runtime protocol checks are pending'],
              'product_gate_acceptance_inferred': False}
    output = HERE / 'SCIENTIFIC-REVIEW.json'
    with output.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(report, stream, indent=2, sort_keys=True, allow_nan=False); stream.write('\n')
    print(json.dumps({'status': report['status'], 'checks': report['counts'], 'output': str(output)}))
    return 0 if report['status'] == 'pass' else 1


if __name__ == '__main__':
    raise SystemExit(main())
