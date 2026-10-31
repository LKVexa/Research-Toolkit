"""Bounded acceptance helper authored for process-limit tests; not repository code."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

mode=sys.argv[1]
time.sleep(.15)  # Allow the parent to attach its Windows Job before the action.
if mode=='sleep':
    time.sleep(3)
    Path(sys.argv[2]).write_text('unexpected surviving child')
elif mode=='output':
    sys.stdout.buffer.write(b'x'*(2*1024*1024));sys.stdout.buffer.flush()
elif mode=='memory':
    try:
        allocation=bytearray(600*1024*1024)
        print(json.dumps({'allocation':'unexpectedly_allowed','bytes':len(allocation)}))
    except MemoryError:
        print(json.dumps({'allocation':'refused'}))
elif mode=='spawn':
    try:
        child=subprocess.run([sys.executable,'-I','-B','-c',
                              'from pathlib import Path;import sys;Path(sys.argv[1]).write_text("unexpected child")',sys.argv[2]],
                             capture_output=True,timeout=2)
        print(json.dumps({'spawn_returncode':child.returncode}))
    except (OSError,subprocess.SubprocessError):
        print(json.dumps({'spawn':'refused'}))
elif mode=='environment':
    print(json.dumps({'environment_names':sorted(os.environ)}))
else:
    raise SystemExit(2)
