"""Recompute final saved-run science using stdlib arithmetic only; never run adapters.

No production module is imported. Reads the exact final package/state/reports;
writes only a new review record beside this script.
"""
from __future__ import annotations
import datetime as dt
from fractions import Fraction as F
import hashlib
import json
import math
from pathlib import Path
import stat

HERE = Path(__file__).resolve().parent
PRODUCT = HERE.parent
WORKSPACE = PRODUCT.parents[3]
APP = WORKSPACE / 'outputs/Research_Replication_Toolkit_v0.1.0-rc.1/app'
STATE = WORKSPACE / 'work/rt-final/state'
EXPORTS = WORKSPACE / 'outputs/Research_Toolkit_Example_Reports'
MARKER = PRODUCT / 'release-evidence/FINAL-WORKFLOW-RESULTS.json'
APP_PIN = '2e91b7a37eef922cd177d76ab4c8d9efca83fbafce5f12c5050f7a7c81ab0f78'
SPECS = {
    'token-equivalence': ('token', 'baseline', 'baseline', 'inconclusive', 4),
    'token-negative': ('token', 'negative-control', 'baseline', 'negative', 4),
    'repair-positive': ('repair', 'correct', 'initial', 'positive', 14),
    'repair-negative': ('repair', 'regression', 'initial', 'negative', 14),
    'repair-equivalence': ('repair', 'initial', 'initial', 'inconclusive', 14),
    'linear-positive': ('numeric', 'ordinary-least-squares', 'mean-baseline', 'positive', 4),
    'negative-slope-positive': ('numeric', 'ordinary-least-squares', 'mean-baseline', 'positive', 4),
    'distribution-shift-negative': ('numeric', 'ordinary-least-squares', 'mean-baseline', 'negative', 4),
    'zero-negative': ('numeric', 'zero-predictor', 'mean-baseline', 'negative', 4),
    'numeric-equivalence': ('numeric', 'same-baseline', 'mean-baseline', 'inconclusive', 4),
}


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''): value.update(block)
    return value.hexdigest()


def canonical(value):
    return hashlib.sha256((json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False)+'\n').encode('utf-8')).hexdigest()


def inventory(root):
    result = {}
    for path in sorted(root.rglob('*')):
        info = path.lstat()
        assert not stat.S_ISLNK(info.st_mode) and not getattr(info, 'st_file_attributes', 0) & 0x400
        if path.is_file(): result[path.relative_to(root).as_posix()] = sha(path)
    return result


def verify_files(root, declared):
    for relative, expected in declared.items():
        path = (root / relative).resolve()
        assert path.is_relative_to(root.resolve()) and sha(path) == expected, relative


def close(actual, expected):
    assert math.isclose(float(actual), float(expected), rel_tol=1e-11, abs_tol=1e-9), (actual, str(expected))


def oracle_numeric(dataset, method):
    development = [row for row in dataset['rows'] if row['split']=='development']
    final = [row for row in dataset['rows'] if row['split']=='final']
    xs = [F(str(row['x'])) for row in development]; ys = [F(str(row['y'])) for row in development]
    n = len(xs); slope = F(0); intercept = sum(ys)/n
    denominator = n*sum(x*x for x in xs)-sum(xs)**2
    if method == 'ordinary-least-squares' and denominator:
        slope = (n*sum(x*y for x,y in zip(xs,ys))-sum(xs)*sum(ys))/denominator
        intercept = (sum(ys)-slope*sum(xs))/n
    if method == 'zero-predictor': intercept = F(0)
    return {row['id']: slope*F(str(row['x']))+intercept for row in final}


def summarize(candidate, baseline, metric, tolerance, labels=None):
    assert set(candidate)==set(baseline)
    keys = sorted(candidate); n=len(keys)
    if metric in ('mse','mae'):
        power = 2 if metric=='mse' else 1
        c={key:abs(candidate[key]-labels[key])**power for key in keys}
        b={key:abs(baseline[key]-labels[key])**power for key in keys}
        differences=[b[key]-c[key] for key in keys]
    else:
        c={key:F(candidate[key]) for key in keys}; b={key:F(baseline[key]) for key in keys}
        differences=[c[key]-b[key] for key in keys]
    mean=sum(differences)/n; variance=sum((x-mean)**2 for x in differences)/n
    return {'candidate_score':sum(c.values())/n,'baseline_score':sum(b.values())/n,
            'mean_improvement':mean,'count':n,'population_variance':variance,
            'min':min(differences),'max':max(differences),
            'result':'positive' if mean>tolerance else 'negative' if mean < -tolerance else 'inconclusive'}


def check_comparison(actual, expected):
    for field in ('candidate_score','baseline_score','mean_improvement'): close(actual[field],expected[field])
    assert actual['result']==expected['result']
    stats=actual.get('paired_differences',actual.get('dispersion'))
    assert stats['count']==expected['count']
    close(stats['mean'],expected['mean_improvement'])
    close(stats['population_sd'],math.sqrt(float(expected['population_variance'])))
    close(stats['min'],expected['min']); close(stats['max'],expected['max'])
    assert actual['inference']=='descriptive_only' and actual['independence_claim'] is False


def private_keys(value):
    forbidden={'predictions','per_row','per_case','labels','observations','rows','candidate_observed',
               'baseline_observed','checks','y','expected_outcome','arguments'}
    if isinstance(value,dict):
        assert not set(value)&forbidden, set(value)&forbidden
        for item in value.values(): private_keys(item)
    elif isinstance(value,list):
        for item in value: private_keys(item)


def main():
    if not MARKER.is_file():
        raise SystemExit('Final workflow marker not yet present; no review verdict written')
    workflow=read(MARKER)
    assert workflow['status']=='pass' and workflow['app_manifest_sha256']==APP_PIN
    assert workflow['protocols_tested']==10 and workflow['real_adapter_processes']==40
    assert sha(APP/'PRODUCT-MANIFEST.json')==APP_PIN
    manifest=read(APP/'PRODUCT-MANIFEST.json'); verify_files(APP,manifest['files'])
    app_before=inventory(APP); state_before=inventory(STATE); exports_before=inventory(EXPORTS)
    assert set(app_before)==set(manifest['files'])|{'PRODUCT-MANIFEST.json'}
    repair_oracle_path=PRODUCT/'qualification/D0007-LITERAL-ORACLE.json'
    token_oracle_path=PRODUCT/'qualification/D0001-CHECK-ORACLE.json'
    repair_rows=read(repair_oracle_path)['labels']
    repair_oracle={}
    categories={}
    for row in repair_rows:
        args=row['arguments']
        if row['task_id']=='DEV-CLAMP':
            x,lo,hi=args
            expected='exception:ArgumentException' if lo>hi else 'value:'+str(max(lo,min(x,hi)))
        else:
            assert row['task_id']=='FINAL-MAGNITUDE'
            expected='value:'+str(abs(args[0]))
        assert expected==row['expected_outcome']
        repair_oracle[row['case_id']]=expected; categories[row['case_id']]=row['category']
    token_oracle={row['id']:row['expected'] for row in read(token_oracle_path)['checks']}
    assert token_oracle['known_example']==7+3+4 and token_oracle['empty']==0
    results=[]
    for run_id,(kind,method,baseline_method,expected_category,count) in SPECS.items():
        run=STATE/'runs'/run_id
        request=read(run/'request.json'); frozen=read(run/'protocol.json'); protocol=frozen['protocol']
        result=read(run/'result.json'); evaluation=read(run/'private/evaluation.json')
        receipt=read(run/'RECEIPT.json'); verify_files(run,receipt['files'])
        assert canonical(receipt['files'])==receipt['files_sha256']
        assert protocol['repetitions']==2 and protocol['seeds']==[]
        assert dt.datetime.fromisoformat(frozen['frozen_at'])<dt.datetime.fromisoformat(request['started_at'])
        assert frozen['protocol_sha256']==canonical(protocol)==request['protocol_sha256']==result['protocol_sha256']
        assert request['package_manifest_sha256']==frozen['package_manifest_sha256']==result['package_manifest_sha256']==APP_PIN
        assert result['execution']=='completed' and result['implementation_checks']=='pass'
        assert result['source_claim']=='unverified' and result['comparison']==expected_category
        assert len(evaluation['comparisons'])==2
        dataset=read(run/'private/dataset.json') if kind=='numeric' else None
        if dataset is not None: assert canonical(dataset)==protocol['dataset_sha256']
        per_rep=[]; payload_hashes=[]
        for repetition in (1,2):
            observed={}; partitions={}; hashes={}
            for role,variant in (('baseline',baseline_method),('candidate',method)):
                stage=run/f'rep-{repetition}'/role
                payload=read(stage/'output.json'); process=read(stage/'process.json')
                assert read(stage/'stdout.log')==payload
                assert process['exit_code']==0 and process['outcome']=='completed'
                hashes[role]=canonical(payload)
                if kind=='numeric':
                    assert payload['method']==variant
                    expected=oracle_numeric(dataset,variant)
                    found={row['id']:row['value'] for row in payload['predictions']}
                    assert set(found)==set(expected)
                    for key in expected: close(found[key],expected[key])
                    observed[role]=expected
                    inputs=read(stage/'input.json')
                    assert inputs['method']==variant
                    final=[{'id':row['id'],'x':row['x']} for row in dataset['rows'] if row['split']=='final']
                    development=[{'id':row['id'],'x':row['x'],'y':row['y']} for row in dataset['rows'] if row['split']=='development']
                    assert inputs['final']==final and inputs['dev']==development
                    assert all(set(row)=={'id','x'} for row in inputs['final'])
                    assert payload['fit_details']['training_rows']==8
                    assert payload['fit_details']['final_labels_received'] is False
                elif kind=='token':
                    assert payload['case']==variant
                    raw=payload['records']['checks']
                    assert set(raw)==set(token_oracle)
                    observed[role]={key:raw[key]['observed']==expected for key,expected in token_oracle.items()}
                else:
                    assert payload['case']==variant
                    raw=[row for row in payload['records']['observations'] if row['variant']==variant]
                    assert len(raw)==len({row['case_id'] for row in raw})==14
                    assert all(row['execution_state']=='completed' for row in raw)
                    actual={row['case_id']:row['outcome'] for row in raw}
                    assert set(actual)==set(repair_oracle)
                    observed[role]={key:actual[key]==expected for key,expected in repair_oracle.items()}
                    partitions[role]={category:{'total':sum(value==category for value in categories.values()),
                                                'passed':sum(observed[role][key] for key in categories if categories[key]==category)}
                                      for category in ('P2P','F2P')}
            metric=protocol['metric']; tolerance=F(str(protocol['absolute_tolerance']))
            labels={row['id']:F(str(row['y'])) for row in dataset['rows'] if row['split']=='final'} if dataset else None
            assert protocol['direction']==('minimize' if kind=='numeric' else 'maximize')
            expected=summarize(observed['candidate'],observed['baseline'],metric,tolerance,labels)
            assert expected['result']==expected_category and expected['count']==count
            check_comparison(evaluation['comparisons'][repetition-1],expected)
            check_comparison(result['summary'],expected)
            if kind=='repair':
                for role in ('baseline','candidate'): assert result['summary'][role+'_partitions']==partitions[role]
            assert evaluation['canonical_output_hashes'][repetition-1]==hashes
            payload_hashes.append(hashes)
            per_rep.append({key:str(value) if isinstance(value,F) else value for key,value in expected.items()})
        assert payload_hashes[0]==payload_hashes[1]
        assert result['summary']==evaluation['summary']==read(run/'summary.json')
        assert result['summary']['sample_count']==count and result['summary']['repetitions']==2
        assert result['summary']['reproducible'] is True
        export=EXPORTS/('export-'+run_id)
        public=read(export/'report.json'); html=(export/'report.html').read_text(encoding='utf-8')
        export_manifest=read(export/'MANIFEST.json'); verify_files(export,export_manifest['files'])
        assert public['private_rows_included'] is False and public['result']==result and public['protocol']==frozen
        assert public['receipt_sha256']==sha(run/'RECEIPT.json')
        private_keys(public)
        assert 'Scored observations' in html and 'Final observations' not in html
        assert 'not a statistical significance claim' in html and 'completed paper replication' in html
        assert 'Repeated runs do not increase the independent sample count' in html
        raw_ids=list(repair_oracle)+['row-09','row-10','row-11','row-12','known_example','unknown_role','recomputable']
        assert all(identifier not in html for identifier in raw_ids)
        assert set(path.name for path in export.iterdir())=={'MANIFEST.json','report.html','report.json'}
        results.append({'run_id':run_id,'kind':kind,'comparison':expected_category,'repetitions':2,
                        'unique_scored_observations':count,'frozen_before_started':True,
                        'exact_recomputed_repetitions':per_rep,'paired_dispersion_verified':True,
                        'private_fields_absent_public_export':True,'receipt_sha256':sha(run/'RECEIPT.json')})
    assert {row['comparison'] for row in results}=={'positive','negative','inconclusive'}
    assert app_before==inventory(APP) and state_before==inventory(STATE) and exports_before==inventory(EXPORTS)
    report={'schema_version':'1.0.0','review':'independent-final-saved-run-science','status':'pass',
            'created_at_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'app_manifest_sha256':APP_PIN,
            'workflow_marker_sha256':sha(MARKER),'runs_reviewed':10,'repetitions_per_run':2,
            'adapter_calls_reexecuted_by_review':0,'production_modules_imported':False,
            'scientific_oracle':'Exact rational normal equations and loss arithmetic; native raw observations scored against independent literal/math expectations',
            'native_oracles':{'d7_file_sha256':sha(repair_oracle_path),'d1_file_sha256':sha(token_oracle_path),
                              'd7_expectations_rederived_from_arguments':True,
                              'd1_random_recount': 'Expected 605 is the qualified frozen fixture oracle, not newly regenerated random data'},
            'all_outcome_categories_verified':['positive','negative','inconclusive'],
            'case_count_note':'D0007 14 scored cases include 8 development and 6 final-evaluation cases; they are not 14 independent holdout observations',
            'deterministic_repetitions_do_not_multiply_sample_counts':True,
            'confidence_interval_claim':False,'paper_replication_claim':False,
            'unchanged_before_after':{'app':True,'final_saved_state':True,'public_exports':True},
            'reviewed_file_counts':{'app':len(app_before),'state':len(state_before),'exports':len(exports_before)},
            'input_inventory_digests':{'app':canonical(app_before),'state':canonical(state_before),'exports':canonical(exports_before)},
            'results':results,
            'limitations':['Inspectably authored controls and existing qualified fixture observations; no scientific paper replication',
                           'Timestamps establish recorded local freeze/run ordering, not a cryptographically trusted time service',
                           'No new model calls, method executions or inferential statistical tests performed']}
    target=HERE/'FINAL-RUNNER-SCIENTIFIC-REVIEW.json'
    with target.open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(report,stream,sort_keys=True,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps({'status':'pass','runs':10,'repetitions':20,'outcomes':report['all_outcome_categories_verified'],
                      'app_manifest_sha256':APP_PIN,'output':str(target)}))


if __name__=='__main__':main()
