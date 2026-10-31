"""Product runner for fixed trusted adapters, using the foundation Windows Job limits."""
import os
import subprocess
import threading
import time
from component_foundation.process import Job


def execute(argv, cwd, timeout, cancel_path=None):
    cap = 1024 * 1024
    env = {k: os.environ[k] for k in ('SystemRoot', 'WINDIR', 'TEMP', 'TMP', 'NUMBER_OF_PROCESSORS') if k in os.environ}
    env.update(PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1', OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1')
    start = time.monotonic()
    process = subprocess.Popen(argv, cwd=cwd, env=env, shell=False, stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
    job, buffers, exceeded = None, [bytearray(), bytearray()], threading.Event()
    def drain(pipe, output):
        try:
            while True:
                chunk = pipe.read(4096)
                if not chunk: break
                available = cap - len(output)
                output.extend(chunk[:max(0, available)])
                if len(chunk) > available: exceeded.set()
        finally:
            pipe.close()
    try:
        job = Job(process, 512)
        readers = [threading.Thread(target=drain, args=(pipe, output), daemon=True)
                   for pipe, output in zip((process.stdout, process.stderr), buffers)]
        for thread in readers: thread.start()
        outcome = 'completed'
        while process.poll() is None:
            if cancel_path is not None and cancel_path.exists(): outcome = 'cancelled'
            elif exceeded.is_set(): outcome = 'output_limit'
            elif time.monotonic() - start > timeout: outcome = 'timeout'
            if outcome != 'completed':
                job.terminate(); break
            time.sleep(.02)
        process.wait(timeout=5)
        for thread in readers: thread.join(timeout=5)
        if exceeded.is_set(): outcome = 'output_limit'
        return {'outcome':outcome,'exit_code':process.returncode,'elapsed_seconds':round(time.monotonic()-start,6),
                'argv':argv,'cwd':str(cwd),'stdout':bytes(buffers[0]),'stderr':bytes(buffers[1]),
                'environment_names':sorted(env),'limits':{'timeout_seconds':timeout,'output_bytes_per_stream':cap,
                                                         'memory_mb':512,'active_processes':1}}
    finally:
        if process.poll() is None:
            if job: job.terminate()
            else: process.kill()
        process.wait(timeout=5)
        if job: job.close()
