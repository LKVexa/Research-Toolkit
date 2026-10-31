import argparse
import json
import os
import sys
from pathlib import Path
from component_foundation.safety import FoundationError, read_json
from .toolkit import Toolkit


def main(root):
    parser=argparse.ArgumentParser(description='Research Toolkit — freeze, run, compare and report bounded local experiments.')
    sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('doctor')
    catalog=sub.add_parser('catalog'); catalog.add_argument('--query')
    default=Path(os.environ.get('LOCALAPPDATA',str(Path.home())))/'ResearchReplicationToolkit/state'
    for name in ('prepare','dataset','freeze','protocol','run','runs','inspect','verify','export','compare','cancel','resume'):
        p=sub.add_parser(name); p.add_argument('--state',default=str(default))
        if name=='prepare':
            p.add_argument('--preset',required=True); p.add_argument('--repetitions',type=int,default=1)
        if name in ('dataset','freeze'): p.add_argument('--file',required=True)
        if name=='protocol': p.add_argument('--id',required=True)
        if name=='run':
            p.add_argument('--protocol',required=True); p.add_argument('--run-id')
            p.add_argument('--supersedes'); p.add_argument('--reason')
        if name in ('inspect','verify','export','cancel','resume'): p.add_argument('--run-id',required=True)
        if name=='export': p.add_argument('--destination',required=True)
        if name=='compare': p.add_argument('--left',required=True); p.add_argument('--right',required=True)
    args=parser.parse_args()
    try:
        app=Toolkit(root)
        command=args.command
        if command=='doctor': result=app.doctor()
        elif command=='catalog': result=app.catalog(args.query)
        elif command=='prepare': result=app.prepare(args.state,args.preset,args.repetitions)
        elif command=='dataset': result=app.register_dataset(args.state,Path(args.file))
        elif command=='freeze': result=app.freeze(args.state,read_json(Path(args.file),32768))
        elif command=='protocol': result=app.protocol(args.state,args.id)
        elif command=='run': result=app.run(args.state,args.protocol,args.run_id,args.supersedes,args.reason)
        elif command=='runs': result={'runs':app.runs(args.state)}
        elif command=='export': result=app.export(args.state,args.run_id,Path(args.destination))
        elif command=='compare': result=app.compare(args.state,args.left,args.right)
        else: result=getattr(app,command)(args.state,args.run_id)
        print(json.dumps(result,ensure_ascii=True,allow_nan=False,indent=2))
        if result.get('execution') in ('failed','cancelled','interrupted') or result.get('status')=='fail' or result.get('implementation_checks')=='fail': return 3
        # A negative scientific/diagnostic comparison is a successful toolkit execution.
        return 0
    except (FoundationError,ValueError,KeyError,TypeError,OSError) as exc:
        message=str(exc) if isinstance(exc,(FoundationError,ValueError,FileExistsError)) else type(exc).__name__+': invalid or unavailable input'
        print(json.dumps({'status':'error','message':message},ensure_ascii=True),file=sys.stderr)
        return 2
