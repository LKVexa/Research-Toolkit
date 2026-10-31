"""Focused revalidation after the public-report wording correction."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

sys.dont_write_bytecode=True
REVIEW=Path(__file__).resolve().parent
WORKSPACE=REVIEW.parents[4]
parser=argparse.ArgumentParser()
parser.add_argument('--app',type=Path,required=True)
parser.add_argument('--expected-manifest',required=True)
args=parser.parse_args()
APP=args.app.resolve()
QA=WORKSPACE/'work/rt-package-qa'/('label-'+uuid.uuid4().hex[:8]);QA.mkdir(parents=True)
STATE=QA/'state';LOGS=QA/'logs';LOGS.mkdir()
tests=[];commands=[]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def check(name,passed,**detail):tests.append({'name':name,'passed':bool(passed),**detail})
def invoke(name,argv,contains=None):
    started=time.monotonic()
    proc=subprocess.run([str(x) for x in argv],cwd=QA,capture_output=True,text=True,encoding='utf-8',errors='replace',
                        timeout=60,shell=False,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    (LOGS/(name+'.stdout.txt')).write_text(proc.stdout,encoding='utf-8')
    (LOGS/(name+'.stderr.txt')).write_text(proc.stderr,encoding='utf-8')
    check(name,proc.returncode==0 and (contains is None or contains in proc.stdout),exit_code=proc.returncode)
    commands.append({'name':name,'argv':[str(x) for x in argv],'exit_code':proc.returncode,
                     'seconds':round(time.monotonic()-started,3)})
    try:return json.loads(proc.stdout)
    except ValueError:return {}
def cli(name,*tail,contains=None):return invoke(name,[sys.executable,'-I','-B',APP/'research.py',*tail],contains)
manifest=json.loads((APP/'PRODUCT-MANIFEST.json').read_text())
pin=sha(APP/'PRODUCT-MANIFEST.json')
check('corrected_exact_pin',pin==args.expected_manifest,actual=pin,expected=args.expected_manifest)
if pin!=args.expected_manifest:raise SystemExit('Refusing to test an unexpected package.')
old=json.loads((REVIEW/'PRE-LABEL-FIX-MANIFEST.json').read_text())
changed=[name for name in sorted(set(old['files'])|set(manifest['files'])) if old['files'].get(name)!=manifest['files'].get(name)]
check('only_report_renderer_changed',changed==['research_toolkit/reporting.py'],changed=changed)
actual={p.relative_to(APP).as_posix():sha(p) for p in APP.rglob('*') if p.is_file()}
check('exact_inventory',actual==dict(manifest['files'],**{'PRODUCT-MANIFEST.json':pin}))
check('no_bytecode',not any('__pycache__' in p or p.endswith('.pyc') for p in actual))
cli('final_doctor','doctor',contains='"status": "pass"')
ps=Path(os.environ['SystemRoot'])/'System32/WindowsPowerShell/v1.0/powershell.exe'
invoke('final_powershell_default',[ps,'-NoProfile','-ExecutionPolicy','Bypass','-File',APP/'Start-Research.ps1'],contains='"status": "pass"')
cmd=Path(os.environ['SystemRoot'])/'System32/cmd.exe'
invoke('final_cmd_catalog',[cmd,'/d','/s','/c',subprocess.list2cmdline([str(APP/'Research-Toolkit.cmd'),'catalog','--query','repair'])],contains='repair-equivalence')
cli('final_native_prepare','prepare','--preset','repair-equivalence','--state',STATE)
result=cli('final_native_run','run','--protocol','repair-equivalence--1.0.0','--state',STATE,'--run-id','native-label-01')
check('native_scope_remains_diagnostic',result.get('execution')=='completed' and result.get('implementation_checks')=='pass'
      and result.get('comparison')=='inconclusive' and result.get('source_claim')=='unverified')
cli('final_native_verify','verify','--run-id','native-label-01','--state',STATE,contains='"metrics_recomputed": true')
export=QA/'public report'
cli('final_native_export','export','--run-id','native-label-01','--state',STATE,'--destination',export)
html=(export/'report.html').read_text(encoding='utf-8')
check('corrected_scored_observations_label','Scored observations' in html and 'Final observations' not in html)
check('native_count_not_mislabeled_holdout',result.get('summary',{}).get('sample_count')==14
      and 'Scored observations</span><strong>14</strong>' in html)
check('public_scope_disclosed','unverified' in html and 'not a statistical significance claim or a completed paper replication' in html)
public=json.loads((export/'report.json').read_text())
def keys(value):
    if isinstance(value,dict):return set(value)|set().union(*(keys(v) for v in value.values()),set())
    if isinstance(value,list):return set().union(*(keys(v) for v in value),set())
    return set()
check('final_export_remains_aggregate',public.get('private_rows_included') is False
      and not (keys(public)&{'predictions','per_case','per_row','final_labels','dataset','rows','baseline_observed','candidate_observed'}))
check('package_unchanged',actual=={p.relative_to(APP).as_posix():sha(p) for p in APP.rglob('*') if p.is_file()})
report={'schema_version':'1.0.0','package_manifest_sha256':pin,'previous_manifest_sha256':sha(REVIEW/'PRE-LABEL-FIX-MANIFEST.json'),
        'scope':'Focused final manifest, launchers and native report-label/privacy revalidation; core modules unchanged',
        'qa_root':str(QA),'real_model_calls':0,'tests':tests,'test_count':len(tests),'passed_count':sum(t['passed'] for t in tests),
        'passed':all(t['passed'] for t in tests)}
(REVIEW/'FINAL-LABEL-ACCEPTANCE.json').write_text(json.dumps(report,indent=2)+'\n')
(REVIEW/'FINAL-LABEL-COMMANDS.json').write_text(json.dumps(commands,indent=2)+'\n')
print(json.dumps({'passed':report['passed'],'passed_count':report['passed_count'],'test_count':report['test_count'],
                  'failed':[t for t in tests if not t['passed']]},indent=2))
