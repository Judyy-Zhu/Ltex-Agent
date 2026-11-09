# Separate language monitors

Keep the experiment's current terminal running. Open two additional terminals in this directory:

```bash
bash monitor.sh lean
```

```bash
bash monitor.sh litex
```

Both refresh every two seconds. They read existing logs and do not launch a worker, request a model response, verify code, or write experiment state. Ctrl+C closes only that monitor. The selected language's current task, attempt window, cumulative attempts, last tool, last kernel check/diagnostic, network waits and known token subtotal are shown. Failed intermediate checks are normal repair feedback and do not by themselves mark the whole task failed.

The default batch is local-compact-01. Use --name for another batch, --interval 5 for a slower refresh, --once for a single snapshot, and --json for machine-readable output:

```bash
bash monitor.sh lean --name local-compact-01 --once
bash monitor.sh litex --once --json
```

Known tokens are a lower bound when usage has not returned or was lost; an in-flight request is included in pending/missing usage. The pass rate displayed here uses finished tasks only. These operator tools are outside the frozen solver runtime and can observe the currently running experiment without changing its code or guides.

The monitor also shows cumulative verifier wall time separately from task wall time, and whether local automatic finalization is pending, failed or complete. Non-verifier time includes model, network and orchestration; it is not pure model latency. Each completed task manifest also stores a verification_timing breakdown for session startup, incremental code, replay, independent final file and declaration checks.
