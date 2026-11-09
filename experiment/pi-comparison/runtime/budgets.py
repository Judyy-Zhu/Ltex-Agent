"""Nullable limits: no time limit is distinct from a measured zero duration."""
import math
import time


def remaining(deadline):
    return math.inf if deadline is None else max(0, deadline-time.monotonic())


def until(state, job, start=None):
    deadline=state.get('deadline_monotonic')
    timeout=job.get('single_check_timeout_seconds')
    return min(math.inf if deadline is None else deadline,
               math.inf if timeout is None else (time.monotonic() if start is None else start)+timeout)


def timeout_seconds(deadline):
    seconds=remaining(deadline)
    return None if math.isinf(seconds) else seconds


def run_remaining(budget, elapsed):
    return math.inf if budget.get('run_seconds') is None else budget['run_seconds']-elapsed


def task_seconds(budget, elapsed):
    value=min(math.inf if budget.get('task_seconds') is None else budget['task_seconds'],
              run_remaining(budget,elapsed))
    return None if math.isinf(value) else max(1,int(value))
