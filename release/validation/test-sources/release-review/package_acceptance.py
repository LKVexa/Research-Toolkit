"""Exact-package CLI and real bounded-process acceptance; no model/network calls."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import time
import uuid

sys.dont_write_bytecode=True
REVIEW=Path(__file__).resolve().parent
WORKSPACE=REVIEW.parents[4]
parser=argparse.ArgumentParser()
parser.add_argument('--app',type=Path,required=True)
parser.add_argument('--expected-manifest',required=True)
parser.add_argument('--work-root',type=Path,default=WORKSPACE/'work/rt-package-qa')
args=parser.parse_args()
APP=args.app.resolve()
WORK_ROOT=args.work_root.resolve()
allowed=(WORKSPACE/'work/rt-package-qa').resolve()
if WORK_ROOT!=allowed:raise SystemExit('Use the explicitly authorized short QA root.')
WORK_ROOT.mkdir(parents=True,exist_ok=True)
QA=WORK_ROOT/('qa-'+uuid.uuid4().hex[:8]);QA.mkdir()
LOGS=QA/'logs';LOGS.mkdir()
STATE=QA/'state'
PY=Path(sys.executable)
tests=[];commands=[];children=[]

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def inventory(root):return {p.relative_to(root).as_posix():sha(p) for p in sorted(root.rglob('*')) if p.is_file()}
def check(name,passed,**detail):tests.append({'name':name,'passed':bool(passed),**detail})
def owned(path):
    absolute=Path(path).absolute()
    resolved=absolute.resolve()
    if not resolved.is_relative_to(QA.resolve()) or resolved==QA.resolve():raise RuntimeError('Target outside disposable QA root')
    return absolute
def invoke(name,argv,expected=0,contains=None,input_text=None):
    start=time.monotonic()
    try:
        proc=subprocess.run([str(x) for x in argv],cwd=QA,capture_output=True,text=True,
                            encoding='utf-8',errors='replace',input=input_text,timeout=60,shell=False,
                            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        code,out,err=proc.returncode,proc.stdout,proc.stderr
    except subprocess.TimeoutExpired:
        code,out,err=-999,'','Acceptance command exceeded its deadline.'
    (LOGS/(name+'.stdout.txt')).write_text(out,encoding='utf-8')
    (LOGS/(name+'.stderr.txt')).write_text(err,encoding='utf-8')
    check(name,code==expected and (contains is None or contains in out+err),exit_code=code,expected_exit_code=expected)
    commands.append({'name':name,'argv':[str(x) for x in argv],'exit_code':code,
                     'seconds':round(time.monotonic()-start,4),'stdout':str(LOGS/(name+'.stdout.txt')),
                     'stderr':str(LOGS/(name+'.stderr.txt'))})
    try:return json.loads(out)
    except ValueError:return None
def cli(name,*tail,app=APP,expected=0,contains=None):
    return invoke(name,[PY,'-I','-B',app/'research.py',*tail],expected,contains)
def write_json(path,value):path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')

baseline=inventory(APP)
manifest_path=APP/'PRODUCT-MANIFEST.json'
actual_pin=sha(manifest_path)
check('exact_manifest_pin',actual_pin==args.expected_manifest,actual=actual_pin,expected=args.expected_manifest)
if actual_pin!=args.expected_manifest:raise SystemExit('Package pin differs; no acceptance commands executed.')
manifest=json.loads(manifest_path.read_text())
check('exact_inventory',baseline==dict(manifest['files'],**{'PRODUCT-MANIFEST.json':actual_pin}))
check('no_bytecode',not any('__pycache__' in p or p.endswith(('.pyc','.pyo')) for p in baseline))
check('no_credential_filenames',not any(Path(p).name.lower() in ('auth.json','.env','credentials.json') for p in baseline))
cli('doctor','doctor',contains='"status": "pass"')
catalog=cli('catalog_query','catalog','--query','token')
check('catalog_query_filters_experiments',isinstance(catalog,dict) and bool(catalog.get('experiments'))
      and all('token' in x['experiment_id'] for x in catalog['experiments']))
check('pc_winter_disclosed',isinstance(catalog,dict) and 'unavailable' in catalog.get('pc_winter',''))
ps=Path(os.environ['SystemRoot'])/'System32/WindowsPowerShell/v1.0/powershell.exe'
cmd=Path(os.environ['SystemRoot'])/'System32/cmd.exe'
invoke('powershell_default_doctor',[ps,'-NoProfile','-ExecutionPolicy','Bypass','-File',APP/'Start-Research.ps1'],contains='"status": "pass"')
invoke('powershell_query_arguments',[ps,'-NoProfile','-ExecutionPolicy','Bypass','-File',APP/'Start-Research.ps1','catalog','--query','token'],contains='token-equivalence')
cmdline=subprocess.list2cmdline([str(APP/'Research-Toolkit.cmd'),'catalog','--query','token'])
invoke('cmd_launcher_query',[cmd,'/d','/s','/c',cmdline],contains='token-equivalence')

for preset,run_id,outcome in [('linear-positive','positive-01','positive'),('zero-negative','negative-01','negative'),
                              ('numeric-equivalence','equivalent-01','inconclusive')]:
    prepared=cli('prepare_'+run_id,'prepare','--preset',preset,'--state',STATE)
    key=preset+'--1.0.0'
    check('prepared_key_'+run_id,isinstance(prepared,dict) and prepared.get('protocol_id')==key)
    cli('protocol_'+run_id,'protocol','--id',key,'--state',STATE,contains='"protocol_sha256"')
    result=cli('run_'+run_id,'run','--protocol',key,'--state',STATE,'--run-id',run_id)
    check('outcome_'+run_id,isinstance(result,dict) and result.get('execution')=='completed'
          and result.get('implementation_checks')=='pass' and result.get('comparison')==outcome
          and result.get('source_claim')=='unverified')
    cli('verify_'+run_id,'verify','--run-id',run_id,'--state',STATE,contains='"metrics_recomputed": true')
cli('runs_listing','runs','--state',STATE,contains='positive-01')
cli('inspect_positive','inspect','--run-id','positive-01','--state',STATE,contains='"integrity": "pass"')
cli('duplicate_run_id','run','--protocol','linear-positive--1.0.0','--state',STATE,'--run-id','positive-01',expected=2)
cli('case_alias_run_id','run','--protocol','linear-positive--1.0.0','--state',STATE,'--run-id','POSITIVE-01',expected=2)
positive_before=inventory(STATE/'runs/positive-01')
cli('resume_completed','resume','--run-id','positive-01','--state',STATE,contains='"execution": "completed"')
check('completed_resume_no_reexecution',inventory(STATE/'runs/positive-01')==positive_before)
cli('cancel_terminal_rejected','cancel','--run-id','positive-01','--state',STATE,expected=2,contains='already terminal')
cli('explicit_superseding_run','run','--protocol','linear-positive--1.0.0','--state',STATE,'--run-id','positive-02',
    '--supersedes','positive-01','--reason','Explicit unchanged-protocol acceptance reproducibility check.',contains='"execution": "completed"')
cli('compare_compatible','compare','--left','positive-01','--right','positive-02','--state',STATE,contains='compatible descriptive comparison')

# Independent custom MAE relation fixed before execution: y=3x-4 on all rows.
dataset={'schema_version':'1.0.0','dataset_id':'custom-mae-control','license':'CC0-1.0; authored acceptance data',
         'rows':[{'id':f'private-row-{i:02}','group':f'group-{i:02}',
                  'split':'development' if i<8 else 'final','x':x,'y':3*x-4}
                 for i,x in enumerate(range(-4,8))]}
datafile=QA/'custom data with spaces.json';write_json(datafile,dataset)
registered=cli('register_custom_data','dataset','--file',datafile,'--state',STATE)
if isinstance(registered,dict) and registered.get('dataset_sha256'):
    protocol={'schema_version':'1.0.0','protocol_id':'custom-mae','version':'1.0.0','experiment_id':'numeric-ols',
              'hypothesis':'Fixed exact relation y=3x-4; analytical OLS MAE zero versus mean MAE eighteen.',
              'dataset_sha256':registered['dataset_sha256'],'metric':'mae','direction':'minimize',
              'absolute_tolerance':1e-9,'repetitions':1,'seeds':[],
              'stopping_rule':'fixed-repetitions-stop-on-execution-error','timeout_seconds':10,
              'claim_scope':'fixture-or-authored-diagnostic; no-paper-replication','supersedes':None,'change_reason':None}
    protocolfile=QA/'custom protocol.json';write_json(protocolfile,protocol)
    cli('freeze_custom_mae','freeze','--file',protocolfile,'--state',STATE,contains='custom-mae--1.0.0')
    result=cli('run_custom_mae','run','--protocol','custom-mae--1.0.0','--state',STATE,'--run-id','custom-mae-01')
    summary=(result or {}).get('summary',{})
    check('custom_mae_analytical_values',summary.get('metric')=='mae' and summary.get('candidate_score')==0
          and summary.get('baseline_score')==18 and summary.get('result')=='positive')
    cli('verify_custom_mae','verify','--run-id','custom-mae-01','--state',STATE,contains='"metrics_recomputed": true')
    cli('incomparable_metrics','compare','--left','positive-01','--right','custom-mae-01','--state',STATE,contains='incomparable')
    protocol['absolute_tolerance']=1
    write_json(protocolfile,protocol)
    cli('frozen_protocol_change_rejected','freeze','--file',protocolfile,'--state',STATE,expected=2,contains='cannot be changed')

export=QA/'public report with spaces'
invoke('powershell_export_spaces',[ps,'-NoProfile','-ExecutionPolicy','Bypass','-File',APP/'Start-Research.ps1',
                                  'export','--run-id','positive-01','--state',str(STATE),'--destination',str(export)],contains='"status": "exported"')
cli('duplicate_export_rejected','export','--run-id','positive-01','--state',STATE,'--destination',export,expected=2)
cli('missing_export_parent_rejected','export','--run-id','positive-01','--state',STATE,'--destination',QA/'missing parent/report',expected=2)
cli('export_into_state_rejected','export','--run-id','positive-01','--state',STATE,'--destination',STATE/'forbidden report',expected=2)
public=json.loads((export/'report.json').read_text()) if (export/'report.json').exists() else {}
forbidden={'predictions','per_row','final_labels','dataset','baseline_observed','candidate_observed','comparisons','rows'}
def keys(value):
    if isinstance(value,dict):return set(value)|set().union(*(keys(v) for v in value.values()),set())
    if isinstance(value,list):return set().union(*(keys(v) for v in value),set())
    return set()
check('public_export_aggregate_only',bool(public) and not (keys(public)&forbidden)
      and public.get('private_rows_included') is False)
check('public_html_exists', (export/'report.html').is_file() and (export/'report.html').stat().st_size>100)

invoke('runtime_requires_isolated',[PY,'-B',APP/'research.py','catalog'],expected=2,contains='isolated mode')
invoke('runtime_rejects_wrong_version',[PY,'-I','-B','-c','import sys,runpy;sys.version_info=(3,12,13);runpy.run_path(sys.argv[1],run_name="__main__")',APP/'research.py'],expected=2,contains='Python 3.12.14')
cli('invalid_run_path','inspect','--run-id','../escape','--state',STATE,expected=2)
cli('invalid_protocol_path','protocol','--id','../escape','--state',STATE,expected=2)
cli('unknown_preset','prepare','--preset','pc-winter','--state',STATE,expected=2,contains='Unknown preset')
cli('invalid_repetitions','prepare','--preset','linear-positive','--state',STATE,'--repetitions','4',expected=2)
cli('state_inside_application','runs','--state',APP/'forbidden state',expected=2,contains='protected')
protected=json.loads((APP/'PROTECTED-ROOTS.json').read_text())['paths']
for i,path in enumerate(p for p in protected if any(s in str(p) for s in ('Local_Component_Workbench','Coding_Agent_Platform'))):
    cli('sibling_state_rejected_'+str(i),'runs','--state',Path(path)/'forbidden-research-state',expected=2,contains='protected')
unrelated=QA/'unrelated-state';unrelated.mkdir();(unrelated/'keep.txt').write_text('unchanged')
cli('unrelated_state_rejected','runs','--state',unrelated,expected=2,contains='unrelated')
jtarget=owned(QA/'junction target');jtarget.mkdir();(jtarget/'sentinel.txt').write_text('keep')
jlink=owned(QA/'junction state')
mklink=subprocess.run([str(cmd),'/d','/c','mklink','/J',str(jlink),str(jtarget)],capture_output=True,text=True,timeout=10)
check('junction_created_for_test',mklink.returncode==0)
if mklink.returncode==0:
    cli('junction_state_rejected','runs','--state',jlink,expected=2)
    check('junction_target_preserved',inventory(jtarget)=={'sentinel.txt':hashlib.sha256(b'keep').hexdigest()})

# Mutate only disposable copies or this acceptance run's own state.
copy=owned(QA/'app space');shutil.copytree(APP,copy)
cli('relocated_doctor','doctor',app=copy,contains='"status": "pass"')
for name,relative,mode in [
    ('changed_app','START_HERE.md','append'),('missing_app','RELEASE-NOTES.md','missing'),
    ('changed_protocol_code','research_toolkit/protocols.py','append'),
    ('changed_native_oracle','native/oracles.json','append'),
    ('changed_foundation','foundation/registry/components.jsonl','append'),
    ('missing_foundation','foundation/registry/checks.jsonl','missing')]:
    path=owned(copy/relative);original=path.read_bytes()
    if mode=='append':path.write_bytes(original+b'\n')
    else:path.unlink()
    cli(name,'catalog','--query','token',app=copy,expected=2,contains='integrity mismatch')
    path.write_bytes(original)
extra=owned(copy/'unexpected.txt');extra.write_text('controlled extra')
cli('unexpected_app_file','doctor',app=copy,expected=2,contains='Unexpected or missing')
extra.unlink()
for name,relative,command in [
    ('frozen_record_tamper','protocols/linear-positive--1.0.0.json',['protocol','--id','linear-positive--1.0.0']),
    ('raw_output_tamper','runs/positive-01/rep-1/candidate/stdout.log',['verify','--run-id','positive-01'])]:
    path=owned(STATE/relative);original=path.read_bytes();path.write_bytes(original+b'\n')
    cli(name,*command,'--state',STATE,expected=2)
    path.write_bytes(original)
extra=owned(STATE/'runs/positive-01/unexpected.txt');extra.write_text('extra')
cli('unexpected_run_file','verify','--run-id','positive-01','--state',STATE,expected=2)
extra.unlink()
cli('restored_run_verifies','verify','--run-id','positive-01','--state',STATE,contains='"integrity": "pass"')

# Real safe helper processes, under the exact final fixed execution wrapper.
sys.path[:0]=[str(APP),str(APP/'foundation')]
from research_toolkit.execution import execute
helper=REVIEW/'safe_child.py'
def child_test(name,mode,timeout=3,cancel=None,marker=None):
    argv=[str(PY),'-I','-B',str(helper),mode]
    if marker is not None:argv.append(str(marker))
    value=execute(argv,QA,timeout,cancel)
    stored={k:v for k,v in value.items() if k not in ('stdout','stderr')}
    stored.update(name=name,stdout_bytes=len(value['stdout']),stderr_bytes=len(value['stderr']),
                  stdout_sha256=hashlib.sha256(value['stdout']).hexdigest(),stderr_sha256=hashlib.sha256(value['stderr']).hexdigest())
    children.append(stored)
    return value
timeout_marker=owned(QA/'timeout-survived.txt')
value=child_test('real_timeout','sleep',timeout=.35,marker=timeout_marker)
check('real_child_timeout',value['outcome']=='timeout' and value['elapsed_seconds']<2 and value['exit_code']!=0)
cancel=owned(QA/'cancel-marker.json');cancel_survived=owned(QA/'cancel-survived.txt')
timer=threading.Timer(.3,lambda:cancel.write_text('{}'));timer.start()
value=child_test('real_cancel','sleep',cancel=cancel,marker=cancel_survived);timer.join()
check('real_child_cancellation',value['outcome']=='cancelled' and value['elapsed_seconds']<2 and value['exit_code']!=0)
value=child_test('real_output_cap','output')
check('real_output_cap',value['outcome']=='output_limit' and len(value['stdout'])<=1048576)
value=child_test('real_memory_cap','memory')
check('real_memory_cap',b'"allocation": "refused"' in value['stdout'] and value['limits']['memory_mb']==512)
spawn_marker=owned(QA/'spawn-survived.txt')
value=child_test('real_process_count_cap','spawn',marker=spawn_marker)
check('real_process_count_cap',not spawn_marker.exists() and value['limits']['active_processes']==1)
value=child_test('real_environment_allowlist','environment')
names=set(json.loads(value['stdout'])['environment_names'])
check('real_environment_allowlist',not any('KEY' in name or 'TOKEN' in name or name.startswith('CODEX_') for name in names))
try:
    execute([str(QA/'missing-runtime.exe')],QA,.2)
    check('missing_runtime_refused',False)
except OSError:check('missing_runtime_refused',True)
check('terminated_children_no_late_writes',not timeout_marker.exists() and not cancel_survived.exists())

state_before=inventory(STATE)
retired=owned(QA/'retired app')
owned(copy);copy.rename(retired)
check('clean_removal_by_rename',not copy.exists() and retired.is_dir() and inventory(STATE)==state_before)
cli('rollback_relocated_catalog','catalog','--query','token',app=retired,contains='token-equivalence')
check('original_package_preserved',inventory(APP)==baseline)
report={'schema_version':'1.0.0','package_manifest_sha256':actual_pin,'package_files':len(manifest['files']),
        'app':str(APP),'qa_root':str(QA),'real_model_calls':0,'application_network_calls':0,
        'scope':'CLI/product acceptance and actual fixed safe process probes; no OS filesystem/network isolation claim',
        'tests':tests,'test_count':len(tests),'passed_count':sum(t['passed'] for t in tests),
        'passed':all(t['passed'] for t in tests)}
report['known_release_findings'] = ([{'code':'misleading_observation_label',
    'detail':'HTML says Final observations for a shared renderer also used by native all-case totals.',
    'status':'Requires Scored observations wording and focused revalidation.'}]
    if (export/'report.html').exists() and 'Final observations' in (export/'report.html').read_text(encoding='utf-8') else [])
report['release_ready_within_review_scope'] = report['passed'] and not report['known_release_findings']
write_json(REVIEW/'PACKAGE-ACCEPTANCE.json',report)
write_json(REVIEW/'PACKAGE-COMMANDS.json',commands)
write_json(REVIEW/'PROCESS-ACCEPTANCE.json',children)
print(json.dumps({'passed':report['passed'],'passed_count':report['passed_count'],'test_count':len(tests),
                  'failed':[t for t in tests if not t['passed']],'report':str(REVIEW/'PACKAGE-ACCEPTANCE.json')},indent=2))
