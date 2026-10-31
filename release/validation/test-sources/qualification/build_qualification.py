"""Read-only qualification of pinned adapter interfaces and stored fixture data.

Only this qualification directory is written. No adapter or original-delivery
code is executed. The verified foundation loader checks package/runtime metadata.
"""
from __future__ import annotations

import datetime
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parents[4]
FOUNDATION = WORKSPACE / 'outputs/Shared_Foundation_v0.1.0-rc.1/foundation'
NOTE = Path('D:/Deliverables/product-work/_technical-notes/D0002_Technical_Note.md')
PIN = 'e01d3f340239f4abe0daa27cb3e7c64190f95f4f3a0419f493bc14e7b07d571d'
sys.path.insert(0, str(FOUNDATION))
from component_foundation.runtime import Foundation
from component_foundation.safety import digest, read_json, sha256


def write(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def qualify():
    foundation = Foundation(FOUNDATION)
    if foundation.manifest_digest != PIN:
        raise ValueError('Unexpected foundation pin')
    doctor = foundation.doctor()
    if doctor['status'] != 'pass':
        raise ValueError('Pinned runtime profile unavailable')
    sources = [
        'MANIFEST.json', 'CAPABILITIES.json', 'BASELINE-INDEX.json',
        'component_foundation/runtime.py', 'component_foundation/process.py',
        'component_foundation/safety.py', 'schemas/adapter-result.json',
        'registry/components.jsonl', 'adapters/python/entry.py',
        'adapters/python/ADAPTER.json', 'adapters/python/SOURCE-MANIFEST.json',
        'adapters/python/vendor/d0001/frog.py', 'adapters/python/vendor/d0001/pairs_c.py',
        'adapters/python/historical/records.json',
        'adapters/d0007/ADAPTER.json', 'adapters/d0007/SOURCE-MANIFEST.json',
        'adapters/d0007/src/WorkbenchAdapter.cs', 'adapters/d0007/src/P2PDiagnostics.cs',
        'adapters/d0007/src/HarnessCommon.cs', 'adapters/d0007/bin/WorkbenchD7.exe',
        'adapters/d0007/historical/PLAN.md', 'adapters/d0007/historical/raw-inputs.json',
        'adapters/d0007/historical/raw-outcomes.json',
    ]
    sources += [path.relative_to(FOUNDATION).as_posix() for path in sorted((FOUNDATION / 'baselines').glob('*.json'))]
    source_hashes = {path: sha256(FOUNDATION / path) for path in sources}
    catalog = [json.loads(line) for line in (FOUNDATION / 'registry/components.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
    selected = {'D0001/C0081-03', 'D0007/C0322-01', 'D0007/C0322-02'}
    catalog_summary = [{key: item.get(key) for key in (
        'component_id', 'original_status', 'original_g2', 'maturity', 'exclusion_reason',
        'native_check_counts', 'acceptance_check_counts', 'source_refs')}
        for item in catalog if item['component_id'] in selected or item['component_id'].startswith('D0002/P0113-')]

    # Literal values transcribed from the frozen C# oracle, independently of the
    # candidate methods and reported metric totals; read/validate only.
    ids = [f'DEV-T{i:02}' for i in range(1, 9)] + [f'FINAL-T{i:02}' for i in range(1, 7)]
    expected = ['value:0', 'value:3', 'value:5', 'exception:ArgumentException',
                'value:4', 'value:-10', 'value:10', 'value:5',
                'value:2147483648', 'value:5', 'value:1', 'value:0', 'value:1', 'value:2147483647']
    f2p_ids = {'DEV-T03', 'DEV-T07', 'FINAL-T01'}
    source = (FOUNDATION / 'adapters/d0007/src/P2PDiagnostics.cs').read_text(encoding='utf-8')
    oracle_text = source.split('static readonly string[] Values={', 1)[1].split('};', 1)[0]
    source_expected = json.loads('[' + oracle_text + ']')
    if source_expected != expected:
        raise ValueError('Literal C# oracle differs from the independently declared labels')
    d7_baseline = read_json(FOUNDATION / 'baselines/D0007_C0322-01--initial.json')
    input_by_id = {row['case_id']: row for row in d7_baseline['records']['inputs']}
    if set(input_by_id) != set(ids):
        raise ValueError('Frozen input ID inventory differs')
    labels = [{
        'case_id': case_id, 'expected_outcome': value, 'category': 'F2P' if case_id in f2p_ids else 'P2P',
        'task_id': input_by_id[case_id]['task_id'], 'task_version': input_by_id[case_id]['task_version'],
        'split': input_by_id[case_id]['split'], 'arguments': input_by_id[case_id]['arguments'],
    } for case_id, value in zip(ids, expected)]
    oracle = {
        'schema_version': '1.0.0', 'scope': 'frozen authored fixture only; not a blind research holdout',
        'source': 'adapters/d0007/src/P2PDiagnostics.cs', 'source_sha256': source_hashes['adapters/d0007/src/P2PDiagnostics.cs'],
        'source_locator': 'LiteralOracle.Values and Kind, lines 119-123; Pipeline.Cases lines 140-148',
        'expected_values_checked_against_literal_source': True, 'labels': labels,
        'shared_components': ['D0007/C0322-01', 'D0007/C0322-02'],
        'unique_case_count': 14, 'variants_per_case': 3,
    }
    write('D0007-LITERAL-ORACLE.json', oracle)
    d1_oracle = {
        'schema_version': '1.0.0', 'component_id': 'D0001/C0081-03',
        'scope': 'Four bounded domain checks, excluding adapter bookkeeping',
        'source': 'adapters/python/vendor/d0001/pairs_c.py',
        'source_sha256': source_hashes['adapters/python/vendor/d0001/pairs_c.py'],
        'source_locator': '_count_pair lines 268-279; C0081_03 uses fixed NumPy RNG seed 23 at line 310',
        'checks': [
            {'id': 'known_example', 'expected': 14, 'type': 'integer', 'input': '30 fixed role labels; 14 model-generated labels'},
            {'id': 'empty', 'expected': 0, 'type': 'integer', 'input': 'empty role sequence'},
            {'id': 'recomputable', 'expected': 605, 'type': 'integer', 'input': '1,000 role labels from NumPy default_rng(23)',
             'expectation_source': 'Pinned baseline /records/checks/recomputable/expected; source independently recounts role membership'},
            {'id': 'unknown_role', 'expected': "ViolationError: unknown token role(s): ['sys']", 'type': 'string',
             'input': "['reasoning', 'sys']", 'expectation_source': 'Pinned baseline observed exception; original criterion is raises ViolationError'},
        ],
    }
    write('D0001-CHECK-ORACLE.json', d1_oracle)

    extraction_evidence = []
    d7_values = {}
    for component in sorted(selected):
        spec = foundation.capabilities[component]
        for case in spec['cases']:
            relative = 'baselines/' + component.replace('/', '_') + '--' + case + '.json'
            payload = read_json(FOUNDATION / relative)
            if digest(payload) != spec['baseline_sha256'][case]:
                raise ValueError('Capability baseline digest mismatch')
            if component.startswith('D0001'):
                raw = payload['records']['checks']
                checks = []
                absolute_error = 0
                for definition in d1_oracle['checks']:
                    actual = raw[definition['id']]['observed']
                    same_type = type(actual) is (int if definition['type'] == 'integer' else str)
                    success = same_type and actual == definition['expected']
                    checks.append({'id': definition['id'], 'pass': success, 'observed': actual, 'expected': definition['expected']})
                    if definition['type'] == 'integer':
                        absolute_error += abs(actual - definition['expected'])
                counts = {'domain_passed': sum(c['pass'] for c in checks), 'domain_total': 4,
                          'numeric_absolute_error_sum': absolute_error, 'numeric_case_total': 3}
                if counts != ({'domain_passed': 4, 'domain_total': 4, 'numeric_absolute_error_sum': 0, 'numeric_case_total': 3}
                              if case == 'baseline' else {'domain_passed': 1, 'domain_total': 4, 'numeric_absolute_error_sum': 411, 'numeric_case_total': 3}):
                    raise ValueError('Unexpected D0001 independent control result')
                extraction_evidence.append({'component_id': component, 'case': case, 'baseline_file': relative,
                                            'canonical_payload_sha256': digest(payload), 'independent_counts': counts})
            else:
                observations = payload['records']['observations']
                if len(observations) != 42 or len({row['observation_id'] for row in observations}) != 42:
                    raise ValueError('Unexpected observation inventory')
                counts_by_variant = {}
                for variant in ('initial', 'correct', 'regression'):
                    chosen = {row['case_id']: row for row in observations if row['variant'] == variant}
                    if set(chosen) != set(ids):
                        raise ValueError('Missing or duplicate selected observations')
                    counts = {'passed': 0, 'total': 14, 'F2P_passed': 0, 'F2P_total': 3, 'P2P_passed': 0, 'P2P_total': 11}
                    for label in labels:
                        row = chosen[label['case_id']]
                        if row['execution_state'] != 'completed' or any(row[key] != label[key] for key in ('task_id', 'task_version', 'split')):
                            raise ValueError('Observation identity or execution state mismatch')
                        passed = row['outcome'] == label['expected_outcome']
                        counts['passed'] += passed
                        counts[label['category'] + '_passed'] += passed
                    reported = [row for row in payload['records']['totals'] if row['variant'] == variant]
                    if len(reported) != 2 or {row['task_id'] for row in reported} != {'DEV-CLAMP', 'FINAL-MAGNITUDE'}:
                        raise ValueError('Reported totals identity mismatch')
                    if counts != {key: sum(row[key] for row in reported) for key in counts}:
                        raise ValueError('Raw outcome aggregation disagrees with reported totals')
                    counts_by_variant[variant] = counts
                expected_totals = {'initial': (11, 0, 11), 'correct': (14, 3, 11), 'regression': (10, 3, 7)}
                for variant, counts in counts_by_variant.items():
                    if (counts['passed'], counts['F2P_passed'], counts['P2P_passed']) != expected_totals[variant]:
                        raise ValueError('Unexpected D0007 independent control result')
                selected_variants = list(expected_totals) if case == 'all' else [case]
                extraction_evidence.append({'component_id': component, 'case': case, 'baseline_file': relative,
                                            'canonical_payload_sha256': digest(payload),
                                            'independent_counts': {variant: counts_by_variant[variant] for variant in selected_variants}})
                d7_values[component + '/' + case] = payload['records']['observations']
    if d7_values['D0007/C0322-01/initial'] != d7_values['D0007/C0322-02/initial']:
        raise ValueError('Unexpected difference between aliased component datasets')
    write('RAW-EXTRACTION-CHECKS.json', {
        'schema_version': '1.0.0', 'status': 'pass', 'adapter_execution_performed': False,
        'method': 'Independently aggregate frozen raw outcomes against literal expectations; compare reported totals',
        'cases_verified': len(extraction_evidence), 'results': extraction_evidence,
    })

    qualification = {
        'schema_version': '1.0.0', 'status': 'qualified_for_bounded_fixture_comparison_only',
        'qualified_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'scientific_validation': 'unverified', 'adapter_execution_performed_in_this_review': False,
        'original_delivery_code_executed': False, 'original_delivery_files_modified': False,
        'foundation': {'version': foundation.manifest['version'], 'canonical_manifest_sha256': PIN,
                       'manifest_file_sha256': sha256(FOUNDATION / 'MANIFEST.json'),
                       'package_integrity': foundation.verify_package(), 'runtime_doctor': doctor},
        'interfaces': {
            'constructor': 'Foundation(foundation_root, application_root=research_product_root)',
            'run': 'Foundation.run(state_root, component_id, case, timeout=30, parent_run_id=None)',
            'verify': 'Foundation.verify_run(state_root, run_id)',
            'artifact': 'state_root/runs/<run_id>/adapter-result.json',
            'required_before_extraction': ['Foundation package matches exact pin', 'verify_run integrity == pass',
                'result execution == pass', 'result verification == pass',
                'adapter component_id and case match requested arm', 'pinned_baseline_match check passes',
                'artifact hash matches run result', 'scope == authored_fixture', 'scientific_validation stays unverified'],
            'semantic_warning': 'Execution/verification pass means the diagnostic ran as frozen. An intentionally inferior candidate can still have candidate_accepted=false and a passing diagnostic run.',
        },
        'profiles': [
            {
                'id': 'token-role-fidelity', 'components': ['D0001/C0081-03'], 'arm_cases': ['baseline', 'negative-control'],
                'oracle_file': 'D0001-CHECK-ORACLE.json', 'comparison_unit': 'the same four deterministic fixture checks',
                'raw_metric_extraction': {
                    'domain_check_paths': ['/records/checks/known_example/observed', '/records/checks/empty/observed',
                                           '/records/checks/recomputable/observed', '/records/checks/unknown_role/observed'],
                    'domain_pass_fraction': 'Strictly compare the four observed values with oracle expectations; numerator is matching checks; denominator is exactly 4; higher is better.',
                    'numeric_absolute_error_sum': 'Sum abs(observed-expected) for known_example, empty, recomputable only; exactly three integer values; lower is better.',
                    'cross_checks': ['/candidate_checks entries by id, excluding historical_semantic_match', '/candidate_accepted'],
                    'do_not_use_as_method_metric': ['/metrics/check_pass', '/metrics/check_fail', '/checks', '/historical_comparison/semantic_match'],
                },
                'expected_cases': {'baseline': {'passed': 4, 'total': 4, 'absolute_error_sum': 0, 'candidate_accepted': True},
                                   'negative-control': {'passed': 1, 'total': 4, 'absolute_error_sum': 411, 'candidate_accepted': False}},
                'limits': {'unique_domain_checks': 4, 'numeric_checks': 3, 'known_example_role_labels': 30,
                           'recount_role_labels': 1000, 'fixed_seed': 23, 'user_seed_supported': False,
                           'sample_size_override_supported': False, 'arbitrary_input_supported': False},
                'source_claim_scope': 'Exact role-counting and rejection behavior on the frozen fixture. No model-training, coding-agent efficiency or source-paper replication conclusion.',
            },
            {
                'id': 'p2p-fixture-comparison', 'components': ['D0007/C0322-01', 'D0007/C0322-02'],
                'arm_cases': ['initial', 'correct', 'regression'], 'all_case_arm_policy': 'Reject ambiguous all as a comparison arm; available for foundation diagnostics only.',
                'oracle_file': 'D0007-LITERAL-ORACLE.json', 'comparison_unit': 'the same 14 authored inputs; 8 DEV-CLAMP and 6 FINAL-MAGNITUDE',
                'raw_metric_extraction': {
                    'observations_path': '/records/observations',
                    'selection': 'Filter rows by variant == requested case; require exactly one row per expected case_id and all 14 IDs.',
                    'fields': ['case_id', 'variant', 'outcome', 'execution_state', 'task_id', 'task_version', 'split'],
                    'outcome_rule': 'Require execution_state=completed, exact task/version/split, and compare outcome strings to frozen oracle labels.',
                    'overall_pass_fraction': 'matching selected observations / 14; higher is better',
                    'f2p_pass_fraction': 'matching DEV-T03, DEV-T07 and FINAL-T01 observations / 3; higher is better',
                    'p2p_preservation_fraction': 'matching remaining 11 observations / 11; higher is better',
                    'reported_cross_check_paths': ['/metrics/totals', '/records/totals', '/candidate_accepted'],
                    'reported_row_selection': 'Select exactly one row per (variant, task_id); DEV-CLAMP total8, FINAL-MAGNITUDE total6. Sum passed,total,F2P_passed,F2P_total,P2P_passed,P2P_total.',
                    'current_selected_case_metric_pointers': ['/metrics/totals/0/passed', '/metrics/totals/0/total', '/metrics/totals/1/passed', '/metrics/totals/1/total'],
                    'index_warning': 'Use task_id/variant identity rather than trusting row order. records/totals and records/observations always contain all variants.',
                    'do_not_use_as_selected_arm_metric': ['/metrics/correct_p2p_preserved', '/metrics/regression_p2p_preserved', '/metrics/method_calls'],
                },
                'expected_cases': {
                    'initial': {'passed': 11, 'total': 14, 'F2P_passed': 0, 'F2P_total': 3, 'P2P_passed': 11, 'P2P_total': 11, 'candidate_accepted': False},
                    'correct': {'passed': 14, 'total': 14, 'F2P_passed': 3, 'F2P_total': 3, 'P2P_passed': 11, 'P2P_total': 11, 'candidate_accepted': True},
                    'regression': {'passed': 10, 'total': 14, 'F2P_passed': 3, 'F2P_total': 3, 'P2P_passed': 7, 'P2P_total': 11, 'candidate_accepted': False},
                },
                'limits': {'unique_inputs': 14, 'development_inputs': 8, 'inherited_final_evaluation_inputs': 6,
                           'f2p_inputs': 3, 'p2p_inputs': 11, 'fixed_variants': 3, 'method_calls_per_adapter_run': 42,
                           'selected_case_still_executes_all_variants': True, 'custom_dataset_supported': False,
                           'custom_candidate_supported': False, 'random_seed_supported': False},
                'shared_dataset_warning': 'C0322-01 and C0322-02 use the identical source, inputs, labels and outcome table. They are not independent studies, samples or replications.',
                'split_warning': 'final-evaluation is an inherited fixture label. Its labels and expected values are already in the frozen source; this release creates no new blinded research holdout.',
                'source_claim_scope': 'Finite authored repair and preservation diagnostics only. No original repository benchmark, model/RL training, TaskPilot integration, generalization or source-paper replication claim.',
                'source_label': 'PROMPT-VERSION-MISMATCH: original pre-v3 source used',
            },
        ],
        'minimal_control_series': [
            {'id': 'd7-positive', 'profile': 'p2p-fixture-comparison', 'component_id': 'D0007/C0322-01', 'baseline_case': 'initial', 'method_case': 'correct', 'expected': 'improved', 'pass_count_delta': 3, 'p2p_guard': '11/11 retained'},
            {'id': 'd7-inferior', 'profile': 'p2p-fixture-comparison', 'component_id': 'D0007/C0322-02', 'baseline_case': 'correct', 'method_case': 'regression', 'expected': 'inferior', 'pass_count_delta': -4, 'p2p_guard': 'regression7/11; must not accept'},
            {'id': 'd7-equivalent', 'profile': 'p2p-fixture-comparison', 'component_id': 'D0007/C0322-01', 'baseline_case': 'correct', 'method_case': 'correct', 'expected': 'equivalent', 'pass_count_delta': 0},
            {'id': 'd1-positive', 'profile': 'token-role-fidelity', 'component_id': 'D0001/C0081-03', 'baseline_case': 'negative-control', 'method_case': 'baseline', 'expected': 'improved', 'domain_pass_count_delta': 3, 'absolute_error_delta': -411},
            {'id': 'd1-inferior', 'profile': 'token-role-fidelity', 'component_id': 'D0001/C0081-03', 'baseline_case': 'baseline', 'method_case': 'negative-control', 'expected': 'inferior', 'domain_pass_count_delta': -3, 'absolute_error_delta': 411},
            {'id': 'd1-equivalent', 'profile': 'token-role-fidelity', 'component_id': 'D0001/C0081-03', 'baseline_case': 'baseline', 'method_case': 'baseline', 'expected': 'equivalent', 'domain_pass_count_delta': 0, 'absolute_error_delta': 0},
        ],
        'mandatory_negative_interpretation': 'D7 initial versus regression repairs all three F2P cases but breaks four P2P cases and reduces total passes from11 to10. Never turn F2P-only improvement or a passing harness diagnostic into candidate acceptance.',
        'experiment_policy': {
            'comparison_pair': 'Same component, same frozen profile, same input inventory; no cross-metric or cross-dataset comparison.',
            'repeat_default': 1, 'repeat_min': 1, 'repeat_max_recommended': 5,
            'adapter_calls_per_comparison': '2 * repeats, including separate equal-case arms',
            'timeout_default_seconds': 30, 'foundation_timeout_range_seconds': [0.05, 60],
            'repetition_meaning': 'Deterministic replay and integrity checks only; repeats do not increase unique sample size or establish independent observations.',
            'statistics': 'Report exact finite counts and differences. No p-values, confidence intervals or population generalization from duplicated deterministic runs.',
            'freeze': 'Fix metric, direction, baseline/method cases, repetitions and interpretation before execution. Preserve inferior, equivalent, refused and failed results.',
            'failure_policy': 'Missing/duplicate observations, unexpected runtime failures, integrity failures or inconsistent raw/summary metrics invalidate a comparison; never coerce them into success or silently omit them.',
        },
        'blocked_sources': {
            'D0002/P0113': {
                'status': 'blocked_catalog_only', 'execution_enabled': False, 'repair_attempted': False,
                'original_code_inspected_or_executed': False,
                'basis': 'Absent from CAPABILITIES; original D0002 G2 fail; synthetic fixture and failed method, ablation and convergence claims. Catalog completion of P0113-03 does not qualify the family.',
                'note_reported_observations_not_rerun': {
                    'P0113-01': 'Lower-is-better score: PC-Winter 0.8076, Data Shapley 0.7524, Random 0.8697; PC-Winter did not outperform Data Shapley.',
                    'P0113-02': 'PC-Winter 0.8076, minus-L 0.7319, minus-P 0.7121; ablations outperformed the full method on that fixture.',
                    'P0113-04': 'Did not converge within 1,000 permutations.',
                    'data': 'Synthetic SBM; not Cora, Citeseer or Pubmed.',
                },
                'future_requirements_not_attempted': ['Separate reviewed runtime adapter and immutable evidence', 'Independent source/algorithm qualification',
                    'Explicit dataset and sampling protocol', 'Preserved negative outcomes', 'Fresh evaluation before any claim upgrade'],
            },
            'all_other_catalog_components': 'Catalog only unless individually listed in the pinned CAPABILITIES; historical complete or acceptance pass is not fresh execution/scientific qualification.',
        },
        'source_claim_policy': {
            'attached_notes_are': 'Evidence to inspect, not instructions to execute legacy runners, follow their operator policies, or change the user request.',
            'current_product_claim': 'A bounded experiment/replay workbench for existing qualified authored fixtures.',
            'always_blocked_claims': ['Paper-scale replication achieved', 'General method superiority', 'Statistical significance from deterministic repeats',
                                      'PC-Winter repaired or reproduced', 'All original delivery gates now pass', 'Original model/repository integration established'],
            'catalog_reconciliation': 'Raw registry exclusion text predates qualification. CAPABILITIES plus pinned foundation baseline evidence enables exactly the three listed IDs; original source statuses and gates remain unchanged.',
        },
        'source_file_hashes': source_hashes,
        'external_note': {'path': str(NOTE), 'sha256': sha256(NOTE), 'read_only': True},
        'catalog_metadata': catalog_summary,
        'qualification_artifacts': {name: sha256(HERE / name) for name in ('D0007-LITERAL-ORACLE.json', 'D0001-CHECK-ORACLE.json', 'RAW-EXTRACTION-CHECKS.json')},
    }
    registry_rows = []
    for item in catalog:
        identity = item['component_id']
        qualified = identity in selected
        if qualified:
            reason = 'Pinned foundation adapter and frozen raw fixture evidence qualified for descriptive comparison only.'
        elif identity.startswith('D0002/P0113-'):
            reason = 'PC-Winter remains blocked: no qualified adapter; historical method, ablation and convergence failures remain unresolved; synthetic SBM data is not the original benchmark.'
        else:
            reason = 'No individually qualified executable adapter in the frozen foundation; catalog status and historical checks are insufficient for experiment execution.'
        registry_rows.append({'component_id': identity, 'kind': 'experiment_fixture' if qualified else 'catalog_only',
                              'execution_enabled': qualified, 'reason': reason,
                              'original_status': item['original_status'], 'original_g2': item['original_g2'],
                              'scientific_validation': 'unverified',
                              'comparison_cases': (['baseline', 'negative-control'] if identity.startswith('D0001/') else ['initial', 'correct', 'regression']) if qualified else []})
    write('EXPERIMENT-REGISTRY.json', {'schema_version': '1.0.0', 'foundation_manifest_sha256': PIN,
                                     'scope': 'Execution qualification is independent of historical catalog completion',
                                     'qualified_component_count': 3, 'components': registry_rows})
    qualification['execution_registry'] = {'file': 'EXPERIMENT-REGISTRY.json', 'sha256': sha256(HERE / 'EXPERIMENT-REGISTRY.json'),
                                            'component_count': len(registry_rows), 'executable_count': 3,
                                            'catalog_only_count': len(registry_rows) - 3}
    qualification['product_fixed_control_series'] = [
        {'component_id': 'D0001/C0081-03', 'baseline': 'baseline', 'method': 'negative-control', 'expected': 'inferior', 'scores': [1.0, 0.25]},
        {'component_id': 'D0001/C0081-03', 'baseline': 'baseline', 'method': 'baseline', 'expected': 'equivalent', 'scores': [1.0, 1.0]},
        {'component_id': 'D0007/C0322-01', 'baseline': 'initial', 'method': 'correct', 'expected': 'improved', 'pass_counts': [11, 14], 'sample_count': 14},
        {'component_id': 'D0007/C0322-01', 'baseline': 'initial', 'method': 'regression', 'expected': 'inferior', 'pass_counts': [11, 10], 'sample_count': 14},
        {'component_id': 'D0007/C0322-01', 'baseline': 'initial', 'method': 'initial', 'expected': 'equivalent', 'pass_counts': [11, 11], 'sample_count': 14},
    ]
    if (HERE / 'native.py').exists() and (HERE / 'oracles.json').exists():
        qualification['native_measurement'] = {
            'module': 'native.py', 'module_sha256': sha256(HERE / 'native.py'),
            'oracle': 'oracles.json', 'oracle_sha256': sha256(HERE / 'oracles.json'),
            'api': 'measure(payload, component_id, selected_case)',
            'returns': 'score: accuracy [0,1], sample_count, per_case [{id,pass}], candidate_accepted, D7 partitions {F2P:{passed,total},P2P:{passed,total}}, pins {foundation,oracle,method,data}, measurement_version; D1 auxiliary numeric error count',
            'raises': 'QualificationError(ValueError) for unsupported, missing, forged or contradictory native evidence',
            'copy_contract': 'Copy native.py and oracles.json byte-for-byte into the same application module directory. Do not change their contents or source-claim labels.',
            'caller_precondition': 'First verify foundation receipt/artifact hashes and pinned payload digest. The native function then independently recomputes fixture scores and verifies summaries.',
        }
        qualification['qualification_artifacts'].update({name: sha256(HERE / name) for name in ('native.py', 'oracles.json', 'test_native.py', 'EXPERIMENT-REGISTRY.json')})
    write('QUALIFICATION.json', qualification)
    print(json.dumps({'status': qualification['status'], 'components': sorted(selected),
                      'frozen_payloads_independently_checked': len(extraction_evidence),
                      'adapters_executed': 0, 'pcwinter': 'blocked_catalog_only',
                      'qualification_sha256': sha256(HERE / 'QUALIFICATION.json')}))


if __name__ == '__main__':
    qualify()
