"""Fixed adapter registry and versioned experimental protocol contracts."""
from component_foundation.contracts import validate
from component_foundation.safety import FoundationError, digest

EXPERIMENTS = {
    'token-equivalence': {'kind':'native','component_id':'D0001/C0081-03','method':'baseline','baseline':'baseline',
                          'metric':'accuracy','direction':'maximize','scope':'four authored token-counter diagnostic cases'},
    'token-negative': {'kind':'native','component_id':'D0001/C0081-03','method':'negative-control','baseline':'baseline',
                      'metric':'accuracy','direction':'maximize','scope':'deliberately faulty token counter, four authored cases'},
    'repair-positive': {'kind':'native','component_id':'D0007/C0322-01','method':'correct','baseline':'initial',
                       'metric':'accuracy','direction':'maximize','scope':'14 authored C# regression cases; not repository benchmark performance'},
    'repair-negative': {'kind':'native','component_id':'D0007/C0322-01','method':'regression','baseline':'initial',
                       'metric':'accuracy','direction':'maximize','scope':'14 authored C# cases with a deliberate P2P regression'},
    'repair-equivalence': {'kind':'native','component_id':'D0007/C0322-01','method':'initial','baseline':'initial',
                          'metric':'accuracy','direction':'maximize','scope':'14 authored C# cases, identical baseline comparison'},
    'numeric-ols': {'kind':'numeric','method':'ordinary-least-squares','baseline':'mean-baseline','direction':'minimize',
                    'scope':'authored fixed univariate regression; user-supplied or synthetic data, no paper claim'},
    'numeric-zero': {'kind':'numeric','method':'zero-predictor','baseline':'mean-baseline','direction':'minimize',
                     'scope':'authored zero-prediction control versus development-mean baseline'},
    'numeric-equivalence': {'kind':'numeric','method':'same-baseline','baseline':'mean-baseline','direction':'minimize',
                            'scope':'authored identical-baseline comparison control'},
}
PRESETS = {key: {'experiment_id':key, 'dataset':None} for key in EXPERIMENTS if EXPERIMENTS[key]['kind']=='native'}
PRESETS.update({
    'linear-positive': {'experiment_id':'numeric-ols','dataset':'positive-linear'},
    'negative-slope-positive': {'experiment_id':'numeric-ols','dataset':'negative-linear'},
    'distribution-shift-negative': {'experiment_id':'numeric-ols','dataset':'negative-shift'},
    'zero-negative': {'experiment_id':'numeric-zero','dataset':'positive-linear'},
    'numeric-equivalence': {'experiment_id':'numeric-equivalence','dataset':'positive-linear'},
})

ID = {'type':'string','pattern':'^[a-z][a-z0-9-]{0,39}$'}
VERSION = {'type':'string','pattern':'^[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}$'}
PROTOCOL_SCHEMA = {'type':'object','required':['schema_version','protocol_id','version','experiment_id','hypothesis',
    'dataset_sha256','metric','direction','absolute_tolerance','repetitions','seeds','stopping_rule','timeout_seconds',
    'claim_scope','supersedes','change_reason'], 'additionalProperties':False, 'properties': {
        'schema_version':{'const':'1.0.0'}, 'protocol_id':ID, 'version':VERSION,
        'experiment_id':{'enum':list(EXPERIMENTS)}, 'hypothesis':{'type':'string','minLength':1,'maxLength':2000},
        'dataset_sha256':{'type':'string','pattern':'^(embedded|[0-9a-f]{64})$'},
        'metric':{'enum':['accuracy','mse','mae']}, 'direction':{'enum':['maximize','minimize']},
        'absolute_tolerance':{'type':'number','minimum':0,'maximum':1e6},
        'repetitions':{'type':'integer','minimum':1,'maximum':3}, 'seeds':{'type':'array','maxItems':0},
        'stopping_rule':{'const':'fixed-repetitions-stop-on-execution-error'},
        'timeout_seconds':{'type':'number','minimum':0.05,'maximum':30},
        'claim_scope':{'const':'fixture-or-authored-diagnostic; no-paper-replication'},
        'supersedes':{'type':['string','null'],'maxLength':64},
        'change_reason':{'type':['string','null'],'minLength':1,'maxLength':1000}}}


def validate_protocol(value):
    validate(value, PROTOCOL_SCHEMA)
    spec = EXPERIMENTS[value['experiment_id']]
    if value['direction'] != spec['direction']:
        raise FoundationError('Metric direction does not match the qualified experiment')
    if spec['kind']=='native':
        if value['dataset_sha256']!='embedded' or value['metric']!='accuracy' or value['absolute_tolerance']>1:
            raise FoundationError('Native fixture protocol requires embedded data and accuracy')
    elif value['dataset_sha256']=='embedded' or value['metric'] not in ('mse','mae'):
        raise FoundationError('Numeric protocol requires registered data and MSE or MAE')
    if (value['supersedes'] is None) != (value['change_reason'] is None):
        raise FoundationError('A protocol correction needs both supersedes and a reason')
    return spec


def key(protocol):
    validate_protocol(protocol)
    return protocol['protocol_id'] + '--' + protocol['version']


def preset_protocol(name, dataset_sha256, repetitions=1):
    if name not in PRESETS:
        raise FoundationError('Unknown preset')
    experiment_id = PRESETS[name]['experiment_id']
    spec = EXPERIMENTS[experiment_id]
    result = {'schema_version':'1.0.0','protocol_id':name,'version':'1.0.0','experiment_id':experiment_id,
              'hypothesis':'Compare the fixed method with its declared baseline on this frozen diagnostic dataset.',
              'dataset_sha256':dataset_sha256,'metric':spec.get('metric','mse'),'direction':spec['direction'],
              'absolute_tolerance':1e-9,'repetitions':repetitions,'seeds':[],
              'stopping_rule':'fixed-repetitions-stop-on-execution-error','timeout_seconds':10,
              'claim_scope':'fixture-or-authored-diagnostic; no-paper-replication', 'supersedes':None,'change_reason':None}
    validate_protocol(result)
    return result
