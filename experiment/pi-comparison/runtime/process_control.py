"""Identify owned process groups across controller restarts without PID guessing."""
import os
import signal
import subprocess
import time


def birth(pid):
    result=subprocess.run(['ps','-p',str(pid),'-o','stat=','-o','lstart='],capture_output=True,text=True)
    parts=result.stdout.strip().split(None,1)
    return parts[1] if len(parts)==2 and not parts[0].startswith('Z') else None


def identity(pid):return {'pid':pid,'birth':birth(pid)}


def stop_owned(record):
    pid=record.get('pid');expected=record.get('birth')
    if not pid or not expected or birth(pid)!=expected:return
    try:
        if os.getpgid(pid)!=pid:raise ValueError('Recorded controller is no longer its own process group')
        os.killpg(pid,signal.SIGTERM)
    except ProcessLookupError:return
    until=time.monotonic()+8
    while birth(pid)==expected and time.monotonic()<until:time.sleep(.05)
    if birth(pid)==expected:
        try:os.killpg(pid,signal.SIGKILL)
        except ProcessLookupError:pass
