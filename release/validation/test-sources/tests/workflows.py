"""Exercise all declared experiments through real bounded adapters."""
import hashlib
import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--app',default=str(HERE/'src'))
parser.add_argument('--workspace')
parser.add_argument('--exports')
parser.add_argument('--report',default=str(HERE/'tests/WORKFLOW-RESULTS.json'))
args=parser.parse_args()
APP=Path(args.app).resolve()
sys.path[:0]=[str(APP),str(APP/'foundation')]
from research_toolkit.toolkit import Toolkit
from component_foundation.safety import read_json,sha256

app=Toolkit(APP)
root=Path(args.workspace).resolve() if args.workspace else Path(tempfile.mkdtemp(prefix='research-workflows-',dir=HERE.parents[2]))
root.mkdir(parents=True,exist_ok=True)
exports=Path(args.exports).resolve() if args.exports else root
exports.mkdir(parents=True,exist_ok=True)
state=root/'state'
expected={'token-equivalence':('inconclusive',4),'token-negative':('negative',4),
          'repair-positive':('positive',14),'repair-negative':('negative',14),'repair-equivalence':('inconclusive',14),
          'linear-positive':('positive',4),'negative-slope-positive':('positive',4),
          'distribution-shift-negative':('negative',4),'zero-negative':('negative',4),'numeric-equivalence':('inconclusive',4)}
records=[]
for preset,(outcome,n) in expected.items():
    prepared=app.prepare(state,preset,2)
    frozen=app.protocol(state,prepared['protocol_id'])
    result=app.run(state,prepared['protocol_id'],run_id=preset)
    assert result['execution']=='completed' and result['implementation_checks']=='pass',result
    assert result['comparison']==outcome and result['summary']['sample_count']==n,result
    assert result['summary']['repetitions']==2 and result['summary']['reproducible']
    assert result['source_claim']=='unverified' and result['summary']['independence_claim'] is False
    request=read_json(state/'runs'/preset/'request.json')
    assert frozen['frozen_at'] < request['started_at']
    verified=app.verify(state,preset)
    assert verified['metrics_recomputed']
    destination=exports/('export-'+preset)
    app.export(state,preset,destination)
    public=read_json(destination/'report.json')
    assert public['result']['comparison']==outcome and public['private_rows_included'] is False
    assert set(p.name for p in destination.iterdir())=={'report.json','report.html','MANIFEST.json'}
    forbidden={'per_row','per_case','predictions','final_labels','rows','dataset','baseline_observed','candidate_observed'}
    def no_private(value):
        if isinstance(value,dict):
            assert not (set(value)&forbidden),set(value)&forbidden
            for item in value.values(): no_private(item)
        elif isinstance(value,list):
            for item in value: no_private(item)
    no_private(public)
    assert app.resume(state,preset)==result
    records.append({'preset':preset,'run_id':preset,'comparison':outcome,'sample_count':n,
                    'candidate_score':result['summary']['candidate_score'],'baseline_score':result['summary']['baseline_score'],
                    'repetitions':2,'frozen_before_run':True,'raw_recomputed':True,'public_export_private_rows':False})
    print(preset+': '+outcome,flush=True)
assert app.compare(state,'linear-positive','zero-negative')['comparison']=='compatible descriptive comparison'
assert app.compare(state,'zero-negative','token-negative')['comparison']=='incomparable'
assert len(app.runs(state))==10
report={'schema_version':'1.0.0','status':'pass','app_manifest_sha256':app.pin,'state':str(state),
        'real_adapter_processes':40,'protocols_tested':10,'records':records,'network_calls':0,
        'scope':'authored controls and original fixed fixtures; no paper replication'}
report_path=Path(args.report)
report_path.parent.mkdir(parents=True,exist_ok=True)
report_path.write_bytes((json.dumps(report,indent=2)+'\n').encode('utf-8'))
print(json.dumps({'status':'pass','state':str(state),'protocols':10,'processes':40}))
