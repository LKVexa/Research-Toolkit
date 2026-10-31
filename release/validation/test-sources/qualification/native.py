"""Independent raw-observation measurement for three frozen foundation fixtures.

This module does not execute adapters, import original deliveries, or accept new
candidate algorithms. The caller must first verify the foundation run receipt,
artifact hashes and pinned baseline. Negative candidate outcomes are measurements;
inconsistent or forged evidence raises QualificationError.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

VERSION = '1.0.0'
ORACLE_SHA256 = 'b17abaea1aac9ff75d583bc6b2057da73521fe2f4087340defadfec1b40ce8f2'
COMPONENTS = ('D0001/C0081-03', 'D0007/C0322-01', 'D0007/C0322-02')


class QualificationError(ValueError):
    """The payload cannot support a qualified fixture measurement."""


def _need(condition, message):
    if not condition:
        raise QualificationError(message)


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     ensure_ascii=False, allow_nan=False).encode('utf-8')).hexdigest()


def _same(actual, expected, description):
    _need(_digest(actual) == _digest(expected), description)


def _load_oracles():
    raw = Path(__file__).with_name('oracles.json').read_bytes()
    _need(hashlib.sha256(raw).hexdigest() == ORACLE_SHA256, 'Frozen oracle integrity mismatch')
    value = json.loads(raw)
    _need(value['schema_version'] == VERSION, 'Unsupported frozen oracle schema')
    return value


def _unique(rows, key, expected, description):
    _need(type(rows) is list, description + ': list required')
    result = {}
    for row in rows:
        _need(type(row) is dict and key in row and type(row[key]) is str, description + ': malformed row')
        _need(row[key] not in result, description + ': duplicate identity')
        result[row[key]] = row
    _need(set(result) == set(expected), description + ': missing or unexpected identity')
    return result


def _count(value, expected, description):
    _need(type(value) is int and value == expected, description)


def _boolean(value, expected, description):
    _need(type(value) is bool and value is expected, description)


def _token_measure(payload, case, oracle):
    _need(case in ('baseline', 'negative-control'), 'Unsupported token fixture case')
    definitions = oracle['D0001']['checks']
    records = payload['records']
    _need(records['id'] == 'C0081-03' and records['work_type'] == 'Measurement', 'Wrong token record identity')
    raw = records['checks']
    _need(type(raw) is dict and set(raw) == {d['id'] for d in definitions}, 'Token check inventory mismatch')
    per_case = []
    expected_candidate_ids = [d['id'] for d in definitions] + (['historical_semantic_match'] if case == 'baseline' else [])
    candidates = _unique(payload['candidate_checks'], 'id', expected_candidate_ids, 'Candidate check inventory')
    absolute_error = 0
    for definition in definitions:
        identity = definition['id']
        row = raw[identity]
        _need(type(row) is dict and row['id'] == identity, 'Token raw check identity mismatch')
        expected_type = int if definition['type'] == 'integer' else str
        observed = row['observed']
        _need(type(observed) is expected_type, 'Token raw observation type mismatch')
        passed = observed == definition['expected']
        expected_description = 'raises ViolationError' if identity == 'unknown_role' else definition['expected']
        _same(row['expected'], expected_description, 'Token declared expectation was changed')
        _need(row['result'] == ('pass' if passed else 'fail'), 'Token raw status contradicts observation')
        check = candidates[identity]
        _same(check['actual'], observed, 'Candidate check contradicts raw observation')
        _same(check['expected'], expected_description, 'Candidate check expectation differs')
        _need(check['status'] == ('pass' if passed else 'fail'), 'Candidate check status contradicts raw observation')
        per_case.append({'id': identity, 'pass': passed})
        if expected_type is int:
            absolute_error += abs(observed - definition['expected'])
    _need(_digest(payload['checks']) == oracle['D0001']['payload_checks_sha256'][case], 'Token harness diagnostics differ from frozen checks')
    _same(payload['metrics'], {'check_fail': 0, 'check_pass': 5 if case == 'baseline' else 1}, 'Token harness metrics mismatch')
    if case == 'baseline':
        historical = candidates['historical_semantic_match']
        _boolean(historical['actual'], True, 'Historical compatibility diagnostic failed')
        _boolean(historical['expected'], True, 'Historical compatibility expectation changed')
        _need(historical['status'] == 'pass', 'Historical compatibility status changed')
    accepted = all(item['pass'] for item in per_case)
    _boolean(payload['candidate_accepted'], accepted, 'Token acceptance contradicts independent checks')
    return {'score': sum(item['pass'] for item in per_case) / 4, 'sample_count': 4,
            'per_case': per_case, 'candidate_accepted': accepted,
            'auxiliary': {'numeric_absolute_error_sum': absolute_error, 'numeric_case_count': 3}}


def _d7_measure(payload, case, oracle):
    data = oracle['D0007']
    _need(case in data['variants'], 'A D0007 comparison arm must select initial, correct or regression')
    labels = {row['case_id']: row for row in data['labels']}
    records = payload['records']
    inputs = _unique(records['inputs'], 'case_id', labels, 'Raw input inventory')
    expected_inputs = {row['case_id']: row for row in data['inputs']}
    _same(inputs, expected_inputs, 'Frozen raw input data was changed')
    expected_ids = [identity + ':' + variant for identity in labels for variant in data['variants']]
    observations = _unique(records['observations'], 'observation_id', expected_ids, 'Raw observation inventory')
    variants = {}
    totals = {}
    for variant in data['variants']:
        values = []
        for index, (identity, label) in enumerate(labels.items()):
            row = observations[identity + ':' + variant]
            _need(row['case_id'] == identity and row['variant'] == variant, 'Observation identity mismatch')
            for field in ('task_id', 'task_version', 'split'):
                _need(row[field] == label[field], 'Observation ' + field + ' mismatch')
            _need(row['execution_state'] == 'completed', 'Unexpected adapter runtime failure')
            _count(row['call_ordinal'], index * 3 + data['variants'].index(variant) + 1, 'Observation call order mismatch')
            outcome = row['outcome']
            _need(type(outcome) is str, 'Raw outcome must be a string')
            if outcome != 'exception:ArgumentException':
                _need(bool(re.fullmatch(r'value:(0|-?[1-9][0-9]{0,18})', outcome)), 'Unsupported raw numeric outcome')
                _need(-(2**63) <= int(outcome[6:]) <= 2**63 - 1, 'Raw numeric outcome outside Int64 range')
            values.append({'id': identity, 'pass': outcome == label['expected_outcome']})
        variants[variant] = values
        for task in ('DEV-CLAMP', 'FINAL-MAGNITUDE'):
            members = [item for item in values if labels[item['id']]['task_id'] == task]
            f2p = [item for item in members if labels[item['id']]['category'] == 'F2P']
            p2p = [item for item in members if labels[item['id']]['category'] == 'P2P']
            totals[(variant, task)] = {
                'variant': variant, 'task_id': task, 'total': len(members), 'passed': sum(v['pass'] for v in members),
                'F2P_total': len(f2p), 'F2P_passed': sum(v['pass'] for v in f2p),
                'P2P_total': len(p2p), 'P2P_passed': sum(v['pass'] for v in p2p),
            }
    for value in variants['initial']:
        _need(value['pass'] == (labels[value['id']]['category'] == 'P2P'), 'Original F2P/P2P category was changed')

    def check_totals(rows, expected, description):
        _need(type(rows) is list and len(rows) == len(expected), description + ': row count mismatch')
        seen = {}
        for row in rows:
            _need(type(row) is dict, description + ': invalid row')
            identity = (row['variant'], row['task_id'])
            _need(identity in expected and identity not in seen, description + ': duplicate or unexpected row')
            _same(row, expected[identity], description + ': contradicts raw observations')
            seen[identity] = row

    check_totals(records['totals'], totals, 'All native totals')
    check_totals(payload['metrics']['totals'], {key: value for key, value in totals.items() if key[0] == case}, 'Selected native totals')
    _need(payload['provenance']['dataset_manifest_sha256'] == data['data_pin'], 'Dataset manifest mismatch')
    _need(payload['provenance']['source_label'] == data['source_label'], 'Source qualification label changed')
    _need(_digest(payload['checks']) == data['payload_checks_sha256'], 'D0007 diagnostic checks changed')
    _need(_digest(records['diagnostics']) == data['diagnostics_sha256'], 'D0007 diagnostic evidence changed')
    diagnostic_checks = {row['id']: row for row in payload['checks']}
    ordered_totals = [totals[(variant, task)] for task in ('DEV-CLAMP', 'FINAL-MAGNITUDE') for variant in data['variants']]
    for check_id, field in (('literal_pass_totals', 'passed'), ('literal_P2P_totals', 'P2P_passed'), ('literal_F2P_totals', 'F2P_passed')):
        _same(diagnostic_checks[check_id]['actual'], [row[field] for row in ordered_totals],
              'Literal diagnostic totals contradict independently aggregated outcomes')
    _count(payload['metrics']['method_calls'], 42, 'Method-call total mismatch')
    _count(payload['metrics']['input_count'], 14, 'Input total mismatch')
    _count(payload['metrics']['p2p_total'], 11, 'P2P total mismatch')
    p2p_ids = [identity for identity, label in labels.items() if label['category'] == 'P2P']
    for variant in ('correct', 'regression'):
        preserved = sum(value['pass'] for value in variants[variant] if value['id'] in p2p_ids)
        _count(payload['metrics'][variant + '_p2p_preserved'], preserved, 'Preservation metric contradicts outcomes')
        trace = records[variant]
        _need(trace['variant'] == variant, 'Preservation trace variant mismatch')
        _need(trace['producer_manifest_sha256'] == data['data_pin'], 'Preservation trace dataset mismatch')
        _count(trace['p2p_total'], 11, 'Preservation trace total mismatch')
        _count(trace['p2p_preserved'], preserved, 'Preservation trace count mismatch')
        _count(trace['consumer_calls_to_candidates'], 0, 'Unexpected consumer calls')
        _boolean(trace['accepted'], preserved == 11, 'Preservation acceptance mismatch')
        _need(trace['downstream_status'] == ('accept' if preserved == 11 else 'reject'), 'Downstream status mismatch')
        trace_rows = _unique(trace['rows'], 'case_id', p2p_ids, 'Preservation row inventory')
        failed = []
        for identity in p2p_ids:
            row = trace_rows[identity]
            before, after = observations[identity + ':initial']['outcome'], observations[identity + ':' + variant]['outcome']
            _need(row['before'] == before and row['after'] == after, 'Preservation row contradicts raw outcomes')
            _boolean(row['preserved'], before == after, 'Preservation row flag mismatch')
            for field in ('task_id', 'task_version', 'split'):
                _need(row[field] == labels[identity][field], 'Preservation row metadata mismatch')
            if before != after:
                failed.append(identity)
        _same(trace['regressions'], failed, 'Regression case IDs mismatch')
        if variant == 'regression':
            _same(diagnostic_checks['regression_ids_literal']['actual'], failed, 'Literal regression IDs contradict outcomes')
    _boolean(payload['metrics']['regression_candidate_accepted'], records['regression']['accepted'], 'Regression acceptance metric mismatch')
    per_case = variants[case]
    accepted = all(value['pass'] for value in per_case)
    _boolean(payload['candidate_accepted'], accepted, 'Candidate acceptance contradicts raw observations')
    partitions = {}
    for category in ('F2P', 'P2P'):
        members = [value for value in per_case if labels[value['id']]['category'] == category]
        partitions[category] = {'passed': sum(value['pass'] for value in members), 'total': len(members)}
    return {'score': sum(value['pass'] for value in per_case) / 14, 'sample_count': 14,
            'per_case': per_case, 'partitions': partitions, 'candidate_accepted': accepted}


def measure(payload, component_id, selected_case):
    """Return independent finite-fixture accuracy; higher score is better.

    Inputs are a parsed, receipt-verified adapter-result.json and its exact
    requested component/case. Scores are descriptive, never statistical claims.
    """
    try:
        _need(type(payload) is dict, 'Adapter payload must be an object')
        _need(component_id in COMPONENTS, 'Component is not qualified for research execution')
        _need(payload['component_id'] == component_id and payload['case'] == selected_case, 'Adapter identity or selected case mismatch')
        _need(payload['schema_version'] == '1.0.0' and payload['adapter_version'] == '0.1.0', 'Adapter schema or version mismatch')
        _need(payload['scope'] == 'authored_fixture' and payload['scientific_validation'] == 'unverified', 'Unsupported source-claim scope')
        _need(payload['execution'] == 'pass', 'Adapter execution did not pass')
        oracle = _load_oracles()
        if component_id == 'D0001/C0081-03':
            result = _token_measure(payload, selected_case, oracle)
            files = ['adapters/python/entry.py', 'adapters/python/vendor/d0001/frog.py', 'adapters/python/vendor/d0001/pairs_c.py']
            data_pin = oracle['D0001']['data_pin']
        else:
            result = _d7_measure(payload, selected_case, oracle)
            files = ['adapters/d0007/bin/WorkbenchD7.exe', 'adapters/d0007/src/WorkbenchAdapter.cs', 'adapters/d0007/src/P2PDiagnostics.cs']
            data_pin = oracle['D0007']['data_pin']
        result['pins'] = {'foundation': oracle['foundation_manifest_sha256'], 'oracle': ORACLE_SHA256,
                          'method': _digest({'component_id': component_id, 'case': selected_case,
                                             'files': {name: oracle['source_pins'][name] for name in files}}),
                          'data': data_pin}
        result['measurement_version'] = VERSION
        return result
    except QualificationError:
        raise
    except (KeyError, TypeError, ValueError, IndexError, OverflowError) as exc:
        raise QualificationError('Malformed or inconsistent native evidence: ' + type(exc).__name__) from exc
