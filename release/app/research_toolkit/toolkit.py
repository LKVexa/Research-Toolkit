"""Freeze protocols, execute fixed methods, independently compare, retain evidence."""
from __future__ import annotations
import json
import math
import sys
import uuid
from pathlib import Path

from component_foundation.runtime import Foundation
from component_foundation.contracts import validate
from component_foundation.safety import FoundationError, RunLock, atomic_json, canonical, digest, inside, no_links, parse_json, read_json, sha256, valid_run_id
from numerical.data import validate_dataset, make_request, final_labels
from numerical.metrics import compare as numeric_compare
from native.native import measure
from . import VERSION
from .execution import execute
from .protocols import EXPERIMENTS, PRESETS, validate_protocol, key, preset_protocol
from .storage import PIN, LOCKS, now, inventory, verify_files, state_root, run_path, seal, verify_receipt, control_lock, new_destination, write_text


class Toolkit:
    def __init__(self, root):
        self.root = Path(root).absolute()
        no_links(self.root)
        self.manifest = read_json(self.root/'PRODUCT-MANIFEST.json')
        if self.manifest.get('product')!='research-replication-toolkit' or self.manifest.get('version')!=VERSION:
            raise FoundationError('Unsupported research package')
        verify_files(self.root, self.manifest['files'], ('PRODUCT-MANIFEST.json',))
        self.pin = digest(self.manifest)
        self.foundation = Foundation(self.root/'foundation', application_root=self.root)
        if self.foundation.manifest_digest != PIN:
            raise FoundationError('Wrong shared-foundation dependency')
        self.protected = [self.root, *self.foundation.config['protected_roots'], *read_json(self.root/'PROTECTED-ROOTS.json')['paths']]

    def state(self, path):
        return state_root(path, self.protected)

    def doctor(self):
        report = self.foundation.doctor()
        return {'product':'research-replication-toolkit','version':VERSION,'status':report['status'],
                'package_manifest_sha256':self.pin,'foundation':report,
                'supported_experiments':len(EXPERIMENTS),'sample_protocols':len(PRESETS),
                'network':'unused','source_claims':'unverified; fixture/authored scope only'}

    def catalog(self, query=None):
        experiments = [dict(spec, experiment_id=name) for name,spec in EXPERIMENTS.items()
                       if not query or query.lower() in (name+' '+spec['scope']).lower()]
        components = self.foundation.catalog(query=query)
        for item in components:
            component = item['component_id']
            item['toolkit_available'] = component in ('D0001/C0081-03','D0007/C0322-01')
            if component=='D0007/C0322-02':
                item['toolkit_reason']='Same 14 observations as C0322-01; not another independent experiment'
            elif not item['toolkit_available']:
                item['toolkit_reason']=item.get('exclusion_reason') or 'No qualified toolkit adapter; historical metadata only'
            else:
                item['toolkit_reason']='Qualified fixed authored fixture; no paper-scale claim'
        return {'experiments':experiments,'presets':PRESETS,'source_components':components,
                'pc_winter':'unavailable; not qualified in this foundation; historical negative findings preserved'}

    def register_dataset(self, state, path):
        state = self.state(state)
        raw = read_json(Path(path), 131072)
        dataset = validate_dataset(raw)
        identity = digest(dataset)
        destination = state/'datasets'/identity
        no_links(destination)
        if destination.exists():
            self._dataset(state, identity)
            return {'dataset_sha256':identity,'reused':True}
        destination.mkdir(exist_ok=False)
        atomic_json(destination/'data.json', dataset)
        info = {'schema_version':'1.0.0','dataset_sha256':identity,'source_file_sha256':sha256(Path(path)),
                'dataset_id':dataset['dataset_id'],'license':dataset['license'],'registered_at':now(),
                'development_rows':sum(r['split']=='development' for r in dataset['rows']),
                'final_rows':sum(r['split']=='final' for r in dataset['rows']),
                'data_file_sha256':sha256(destination/'data.json'),'group_policy':'one unique group per row; no overlap'}
        atomic_json(destination/'MANIFEST.json', info)
        atomic_json(destination/'RECEIPT.json', {'files':inventory(destination)})
        return dict(info, reused=False)

    def _dataset(self, state, identity):
        import re
        if not isinstance(identity,str) or not re.fullmatch('[0-9a-f]{64}',identity):
            raise FoundationError('Invalid dataset identity')
        folder = inside(state, 'datasets/'+identity)
        verify_files(folder,read_json(folder/'RECEIPT.json')['files'],('RECEIPT.json',))
        info = read_json(folder/'MANIFEST.json')
        data = validate_dataset(read_json(folder/'data.json', 131072))
        if digest(data)!=identity or info.get('dataset_sha256')!=identity or sha256(folder/'data.json')!=info.get('data_file_sha256'):
            raise FoundationError('Registered data changed')
        if set(inventory(folder)) != {'data.json','MANIFEST.json','RECEIPT.json'}:
            raise FoundationError('Unexpected dataset artifacts')
        return data, info

    def freeze(self, state, value):
        state = self.state(state)
        with RunLock(state/'registry.lock'):
            return self._freeze_locked(state,value)

    def _freeze_locked(self, state, value):
        state = self.state(state)
        spec = validate_protocol(value)
        identifier = key(value)
        destination = inside(state, 'protocols/'+identifier+'.json')
        if destination.exists():
            previous = self.protocol(state, identifier)
            if previous['protocol']!=value:
                raise FoundationError('A frozen protocol cannot be changed; create a new version with a reason')
            return {'protocol_id':identifier,'protocol_sha256':previous['protocol_sha256'],'reused':True}
        if spec['kind']=='numeric': self._dataset(state, value['dataset_sha256'])
        siblings = list((state/'protocols').glob(value['protocol_id']+'--*.json'))
        if value['supersedes']:
            old = self.protocol(state, value['supersedes'])['protocol']
            if old['protocol_id']!=value['protocol_id'] or tuple(map(int,value['version'].split('.'))) <= tuple(map(int,old['version'].split('.'))):
                raise FoundationError('Protocol correction must increase the same protocol version')
        elif siblings:
            raise FoundationError('A later protocol version needs supersedes and a change reason')
        record = {'schema_version':'1.0.0','protocol':value,'protocol_sha256':digest(value),'frozen_at':now(),
                  'package_manifest_sha256':self.pin,'foundation_manifest_sha256':PIN}
        atomic_json(destination, record)
        atomic_json(destination.with_suffix('.sha256.json'), {'sha256':sha256(destination)})
        return {'protocol_id':identifier,'protocol_sha256':record['protocol_sha256'],'reused':False}

    def protocol(self, state, identifier):
        state = self.state(state)
        import re
        if not isinstance(identifier,str) or not re.fullmatch('[a-z][a-z0-9-]{0,39}--[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}',identifier):
            raise FoundationError('Invalid protocol identifier')
        path = inside(state,'protocols/'+identifier+'.json')
        record = read_json(path)
        if sha256(path)!=read_json(path.with_suffix('.sha256.json')).get('sha256'):
            raise FoundationError('Frozen protocol record or timestamp changed')
        if key(record['protocol'])!=identifier or digest(record['protocol'])!=record.get('protocol_sha256'):
            raise FoundationError('Frozen protocol integrity mismatch')
        if record.get('package_manifest_sha256')!=self.pin or record.get('foundation_manifest_sha256')!=PIN:
            raise FoundationError('Protocol belongs to another exact package; preserve that package or register a new version')
        if EXPERIMENTS[record['protocol']['experiment_id']]['kind']=='numeric':
            self._dataset(state,record['protocol']['dataset_sha256'])
        return record

    def prepare(self, state, preset, repetitions=1):
        if preset not in PRESETS: raise FoundationError('Unknown preset')
        item = PRESETS[preset]
        data_id = 'embedded'
        if item['dataset']:
            data_id = self.register_dataset(state, self.root/'numerical/datasets'/ (item['dataset']+'.json'))['dataset_sha256']
        return self.freeze(state, preset_protocol(preset,data_id,repetitions))

    def run(self, state, protocol_id, run_id=None, supersedes=None, reason=None):
        state = self.state(state)
        frozen = self.protocol(state,protocol_id)
        protocol = frozen['protocol']; spec = EXPERIMENTS[protocol['experiment_id']]
        if (supersedes is None)!=(reason is None) or (reason is not None and (not isinstance(reason,str) or not 1<=len(reason)<=1000)):
            raise FoundationError('A superseding run needs both an existing run and a reason')
        if supersedes: verify_receipt(run_path(state,supersedes))
        if self.foundation.doctor()['status']!='pass':
            raise FoundationError('Required runtime unavailable; run doctor')
        identifier = valid_run_id(run_id or ('r'+uuid.uuid4().hex[:20]))
        folder = state/'runs'/identifier
        no_links(folder); folder.mkdir(exist_ok=False)
        with RunLock(folder/'run.lock'):
            request = {'schema_version':'1.0.0','run_id':identifier,'started_at':now(),'protocol_id':protocol_id,
                       'protocol_sha256':frozen['protocol_sha256'],'package_manifest_sha256':self.pin,
                       'foundation_manifest_sha256':PIN,'supersedes':supersedes,'reason':reason,
                       'runtime_python_sha256':sha256(Path(sys.executable))}
            atomic_json(folder/'request.json',request)
            atomic_json(folder/'protocol.json',frozen)
            dataset = None
            if spec['kind']=='numeric':
                dataset, info = self._dataset(state,protocol['dataset_sha256'])
                atomic_json(folder/'private/dataset.json',dataset)
                atomic_json(folder/'private/data-manifest.json',info)
            atomic_json(folder/'INPUTS.json',{'files':inventory(folder,(*LOCKS,'CANCEL.json','INPUTS.json'))})
            try:
                for repetition in range(protocol['repetitions']):
                    for role in ('baseline','candidate'):
                        if (folder/'CANCEL.json').exists():
                            return self._terminal(folder,'cancelled','Cancellation requested')
                        stage = folder/f'rep-{repetition+1}'/role
                        stage.mkdir(parents=True,exist_ok=False)
                        method = spec['baseline'] if role=='baseline' else spec['method']
                        if spec['kind']=='numeric':
                            public = make_request(dataset,method)
                            atomic_json(stage/'input.json',public)
                            argv = [sys.executable,'-I','-B',str(self.root/'numerical/adapter.py'),'--request',str(stage/'input.json')]
                        else:
                            capability = self.foundation.capabilities[spec['component_id']]
                            executable = str(inside(self.foundation.root,capability['entrypoint']))
                            if capability['runtime']=='python':
                                argv = [sys.executable,'-I','-B',executable,'--case',method]
                            else:
                                argv = [executable,'--component',spec['component_id'],'--case',method]
                        atomic_json(stage/'INTENT.json',{'created_at':now(),'method':method,'argv':argv})
                        proc = execute(argv,stage,protocol['timeout_seconds'],folder/'CANCEL.json')
                        for name in ('stdout','stderr'):
                            (stage/(name+'.log')).write_bytes(proc.pop(name))
                        atomic_json(stage/'process.json',proc)
                        if proc['outcome']!='completed' or proc['exit_code']!=0:
                            return self._terminal(folder,'cancelled' if proc['outcome']=='cancelled' else 'failed',
                                                  'Adapter '+proc['outcome']+'; exit '+str(proc['exit_code']))
                        raw = parse_json((stage/'stdout.log').read_bytes(),1024*1024)
                        self._validate_payload(raw,spec,method)
                        atomic_json(stage/'output.json',raw)
                atomic_json(folder/'READY.json',{'files':inventory(folder,(*LOCKS,'CANCEL.json','READY.json'))})
                return self._finish(folder)
            except KeyboardInterrupt:
                return self._terminal(folder,'cancelled','Operator interrupted execution')
            except (FoundationError, ValueError, KeyError, TypeError, OSError) as exc:
                return self._terminal(folder,'failed','Implementation or input validation error: '+type(exc).__name__)

    def _validate_payload(self, payload, spec, method):
        if spec['kind']=='native':
            validate(payload,self.foundation.schemas['adapter-result'])
            if payload['component_id']!=spec['component_id'] or payload['scope']!='authored_fixture':
                raise FoundationError('Native adapter identity mismatch')
            expected = self.foundation.capabilities[spec['component_id']]['baseline_sha256'][method]
            if digest(payload)!=expected or payload['execution']!='pass' or any(c['status']!='pass' for c in payload['checks']):
                raise FoundationError('Native implementation differs from its qualified baseline')
            return measure(payload,spec['component_id'],method)
        if not isinstance(payload,dict) or set(payload)!={'schema_version','method','predictions','fit_details'} or payload['schema_version']!='1.0.0' or payload['method']!=method:
            raise FoundationError('Numerical adapter output identity mismatch')
        details = payload['fit_details']
        number={'type':'number','minimum':-1e12,'maximum':1e12}
        properties={'training_rows':{'type':'integer','minimum':8,'maximum':252},
                    'slope':number,'intercept':number,'development_x_mean':number,'development_y_mean':number,
                    'degenerate_development_x':{'type':'boolean'},'fitted_on':{'const':'development_only'},
                    'final_labels_received':{'const':False,'type':'boolean'},'stochastic':{'const':False,'type':'boolean'},'tuned_parameters':{'const':0,'type':'integer'}}
        validate(details,{'type':'object','required':list(properties),'properties':properties,'additionalProperties':False})
        validate(payload['predictions'],{'type':'array','minItems':4,'maxItems':248,'items':{
            'type':'object','required':['id','value'],'additionalProperties':False,'properties':{
                'id':{'type':'string','pattern':'^[A-Za-z][A-Za-z0-9_-]{0,63}$'},'value':number}}})
        return payload

    def _inputs(self, run):
        request = read_json(run/'request.json')
        if request['package_manifest_sha256']!=self.pin or request['runtime_python_sha256']!=sha256(Path(sys.executable)):
            raise FoundationError('Run requires its exact package and runtime')
        verify_files(run,read_json(run/'INPUTS.json')['files'],exact=False)
        frozen = read_json(run/'protocol.json'); protocol = frozen['protocol']
        validate_protocol(protocol)
        if digest(protocol)!=request['protocol_sha256'] or request['protocol_sha256']!=frozen['protocol_sha256']:
            raise FoundationError('Frozen run protocol changed')
        return request, protocol, EXPERIMENTS[protocol['experiment_id']]

    def _evaluate(self, run):
        request, protocol, spec = self._inputs(run)
        verify_files(run,read_json(run/'READY.json')['files'],exact=False)
        dataset = None
        if spec['kind']=='numeric':
            dataset = validate_dataset(read_json(run/'private/dataset.json',131072))
            if digest(dataset)!=protocol['dataset_sha256']:
                raise FoundationError('Run dataset no longer matches its frozen identity')
        comparisons, hashes = [], []
        for repetition in range(protocol['repetitions']):
            raw, observed = {}, {}
            for role in ('baseline','candidate'):
                stage = run/f'rep-{repetition+1}'/role
                payload = read_json(stage/'output.json',1024*1024)
                method = spec['baseline'] if role=='baseline' else spec['method']
                observed[role] = self._validate_payload(payload,spec,method)
                raw[role] = payload
                proc = read_json(stage/'process.json')
                if proc['outcome']!='completed' or proc['exit_code']!=0 or parse_json((stage/'stdout.log').read_bytes())!=payload:
                    raise FoundationError('Recorded process or raw output differs')
                if spec['kind']=='numeric':
                    expected_request=make_request(dataset,method)
                    if read_json(stage/'input.json')!=expected_request or payload['fit_details']['training_rows']!=len(expected_request['dev']):
                        raise FoundationError('Method input or training count differs from frozen public/development data')
            hashes.append({role:digest(payload) for role,payload in raw.items()})
            if spec['kind']=='numeric':
                comparison = numeric_compare({role:payload['predictions'] for role,payload in raw.items()},
                                             final_labels(dataset), protocol['metric'],protocol['direction'],protocol['absolute_tolerance'])
            else:
                b,c = observed['baseline'],observed['candidate']
                if b['sample_count']!=c['sample_count']:
                    raise FoundationError('Native baseline/method sample mismatch')
                baseline_cases={row['id']:row['pass'] for row in b['per_case']}
                candidate_cases={row['id']:row['pass'] for row in c['per_case']}
                if set(baseline_cases)!=set(candidate_cases): raise FoundationError('Native paired case identities differ')
                differences=[float(candidate_cases[i])-float(baseline_cases[i]) for i in sorted(baseline_cases)]
                improvement = math.fsum(differences)/len(differences); tol=protocol['absolute_tolerance']
                comparison = {'metric':'accuracy','direction':'maximize','candidate_score':c['score'],'baseline_score':b['score'],
                              'mean_improvement':improvement,'result':'positive' if improvement>tol else 'negative' if improvement < -tol else 'inconclusive',
                              'tolerance':tol,'sample_count':c['sample_count'],'baseline_observed':b,'candidate_observed':c,
                              'paired_differences':{'count':len(differences),'mean':improvement,
                                  'population_sd':math.sqrt(math.fsum((d-improvement)**2 for d in differences)/len(differences)),
                                  'min':min(differences),'max':max(differences)},
                              'inference':'descriptive_only','independence_claim':False}
            comparisons.append(comparison)
        reproducible = all(item==hashes[0] for item in hashes)
        first = comparisons[0]
        summary = {field:first[field] for field in ('metric','direction','candidate_score','baseline_score','mean_improvement','result','tolerance','inference','independence_claim')}
        summary['sample_count'] = first.get('sample_count',first.get('paired_differences',{}).get('count'))
        if 'paired_differences' in first: summary['dispersion'] = first['paired_differences']
        for role in ('baseline','candidate'):
            if role+'_observed' in first:
                item = first[role+'_observed']
                summary[role+'_partitions'] = item.get('partitions')
                summary[role+'_accepted_by_fixture'] = item.get('candidate_accepted')
        summary.update(repetitions=protocol['repetitions'], reproducible=reproducible,
                       repetition_policy='deterministic replay; sample count is not multiplied',
                       scientific_validation='unverified; no paper-scale replication claim')
        return {'comparisons':comparisons,'canonical_output_hashes':hashes,'summary':summary}

    def _finish(self, run):
        evaluated = self._evaluate(run)
        request,protocol,spec = self._inputs(run)
        for path,value in [(run/'private/evaluation.json',evaluated),(run/'summary.json',evaluated['summary'])]:
            if path.exists():
                if read_json(path)!=value: raise FoundationError('Interrupted evaluation differs from recomputation')
            else: atomic_json(path,value)
        good = evaluated['summary']['reproducible']
        result = {'schema_version':'1.0.0','run_id':request['run_id'],'finished_at':now(),
                  'execution':'completed','implementation_checks':'pass' if good else 'fail',
                  'comparison':evaluated['summary']['result'] if good else 'unavailable',
                  'source_claim':'unverified','release_eligible':good,'scope':spec['scope'],
                  'protocol_id':request['protocol_id'],'protocol_sha256':request['protocol_sha256'],
                  'dataset_sha256':protocol['dataset_sha256'],'package_manifest_sha256':self.pin,
                  'summary':evaluated['summary'],'supersedes':request['supersedes'],'reason':request['reason']}
        if not good:
            result.pop('summary')
            result['reason']='Deterministic replays disagreed; no final comparison is available. Raw observations are retained privately.'
        return seal(run,result)

    def _terminal(self,run,execution,reason):
        request=read_json(run/'request.json')
        return seal(run,{'schema_version':'1.0.0','run_id':request['run_id'],'finished_at':now(),'execution':execution,
                         'implementation_checks':'fail' if execution=='failed' else 'unverified',
                         'comparison':'unavailable','source_claim':'unverified','release_eligible':False,
                         'protocol_id':request['protocol_id'],'protocol_sha256':request['protocol_sha256'],
                         'package_manifest_sha256':self.pin,'reason':reason,'supersedes':request['supersedes']})

    def inspect(self,state,run_id):
        run=run_path(self.state(state),run_id)
        return {'integrity':'pass','result':verify_receipt(run)}

    def verify(self,state,run_id):
        run=run_path(self.state(state),run_id)
        result=verify_receipt(run); self._inputs(run)
        if result['execution']=='completed':
            evaluated=self._evaluate(run)
            expected_summary=evaluated['summary'] if evaluated['summary']['reproducible'] else None
            if read_json(run/'private/evaluation.json')!=evaluated or result.get('summary')!=expected_summary:
                raise FoundationError('Metrics do not reproduce from recorded raw outcomes')
        return {'run_id':run_id,'integrity':'pass','metrics_recomputed':result['execution']=='completed',
                'execution':result['execution'],'implementation_checks':result['implementation_checks'],'comparison':result['comparison']}

    def resume(self,state,run_id):
        run=run_path(self.state(state),run_id)
        with RunLock(run/'run.lock'):
            if (run/'RECEIPT.json').exists():
                self.verify(state,run_id); return verify_receipt(run)
            self._inputs(run)
            if (run/'READY.json').exists(): return self._finish(run)
            if (run/'result.json').exists():
                raise FoundationError('Terminal receipt interrupted; retain this evidence and start an explicit superseding run')
            return self._terminal(run,'interrupted','Missing complete adapter evidence; resume never reexecutes a process')

    def cancel(self,state,run_id):
        run=run_path(self.state(state),run_id)
        with control_lock(run):
            if (run/'result.json').exists(): raise FoundationError('Run is already terminal')
            if not (run/'CANCEL.json').exists(): atomic_json(run/'CANCEL.json',{'requested_at':now()})
        return {'run_id':run_id,'status':'cancellation_requested'}

    def runs(self,state):
        state=self.state(state); result=[]
        for run in sorted((state/'runs').iterdir()):
            no_links(run); valid_run_id(run.name)
            if (run/'RECEIPT.json').exists():
                item=verify_receipt(run)
                result.append({k:item.get(k) for k in ('run_id','protocol_id','execution','comparison','source_claim')})
            else: result.append({'run_id':run.name,'execution':'incomplete; resume after worker stops'})
        return result

    def compare(self,state,left,right):
        state=self.state(state)
        self.verify(state,left); self.verify(state,right)
        a,b=[verify_receipt(run_path(state,i)) for i in (left,right)]
        if any(r['execution']!='completed' or r['implementation_checks']!='pass' for r in (a,b)):
            return {'comparison':'unavailable','reason':'Both runs need verified complete execution','left':a,'right':b}
        protocols=[read_json(run_path(state,i)/'protocol.json')['protocol'] for i in (left,right)]
        fields=('dataset_sha256','metric','direction','absolute_tolerance')
        specs=[EXPERIMENTS[p['experiment_id']] for p in protocols]
        if any(protocols[0][f]!=protocols[1][f] for f in fields) or any(specs[0].get(f)!=specs[1].get(f) for f in ('kind','component_id','baseline')):
            return {'comparison':'incomparable','reason':'Data, metric, direction, tolerance or baseline differ','left':a,'right':b}
        return {'comparison':'compatible descriptive comparison','left':a['summary'],'right':b['summary'],
                'candidate_score_difference_right_minus_left':b['summary']['candidate_score']-a['summary']['candidate_score'],
                'independence_claim':False,'sample_count_not_pooled':True}

    def export(self,state,run_id,destination):
        state=self.state(state); run=run_path(state,run_id)
        self.verify(state,run_id)
        result=verify_receipt(run)
        protocol=read_json(run/'protocol.json')
        target=new_destination(destination,[*self.protected,state]); target.mkdir()
        public={'schema_version':'1.0.0','result':result,'protocol':protocol,
                'receipt_sha256':sha256(run/'RECEIPT.json'),'private_rows_included':False,
                'evaluation_reproduction':'Requires original local state; public export intentionally omits labels and raw row outcomes'}
        atomic_json(target/'report.json',public)
        from .reporting import render
        write_text(target/'report.html',render(public))
        atomic_json(target/'MANIFEST.json',{'schema_version':'1.0.0','files':inventory(target)})
        return {'status':'exported','directory':str(target),'run_id':run_id,'comparison':result['comparison'],'private_rows_included':False}
