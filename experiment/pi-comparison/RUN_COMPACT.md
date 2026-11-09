# Compact agent protocol and verifier-only replay

The current paired protocol uses the same five tools in both languages:

- `submit_candidate({code})`: durably save one complete increment, run the native incremental verifier, return full diagnostics, and automatically finish independent final verification/publication gates after acceptance.
- `read_input({path})`: original TXT and frozen task/foundation files.
- `read_docs({topic, section?})`: list sections, retrieve an exact section, or use `section="all"` for the intact full reference.
- `read_library({symbols})`: actual own-language declarations, source, interfaces and full receipts.
- `remaining_budget({})`: optional; native feedback also contains the shared attempt counter.

The common system instructions and short language operation cards are always present. The original Litex short guide is retained verbatim as the on-demand core reference. Both cards cover declarations, domains, proof structure and diagnostics, and their code examples are checked against the installed kernels. Original primary text, including proof text, is preserved in full. All mathematical conditions of special task contracts, including I.1's five conclusions and construction requirements, remain in the prompt.

A candidate submission replaces separate write/check tool calls. The agent still decides when to submit. One complete candidate/check/feedback sequence consumes one attempt. Five total attempts per task window include network/API failures. Five all-API failures stop at the same task for explicit restart with full history retained. No task/checker time limit is added. Native diagnostics and independent final/dependency checks remain enforced. Duplicate tool IDs and interrupted local submissions recover their original receipts without spending another round.

## Agent pilot and full experiment

From this directory, the prepared 10-task pilot can be started explicitly:

```bash
caffeinate -i bash run_local.sh resume --name local-compact10-01
```

This is Book I definitions 1–10, ten original tasks per language, twenty language jobs. The full prepared batch is separate:

```bash
caffeinate -i bash run_local.sh resume --name local-compact-01
```

Both use Lean=primary and Litex=secondary credentials in parallel. Preparation/preflight do not launch a model. These new batches must be explicitly started; historical frozen batches should not be resumed with changed runtime files.

Read-only monitors:

```bash
bash monitor.sh lean --name local-compact10-01
bash monitor.sh litex --name local-compact10-01
```

To prepare another exact task-count pilot without confusing definitions with proposition counts:

```bash
bash run_local.sh prepare --name another-compact10 --books 1 --limit-tasks 10 --execution parallel --source-cache batches/local-pilot10-02/source-cache
```

## Verifier-only speed measurement: zero model calls

Replay already machine-accepted, hash-bound artifacts from the completed pilot:

```bash
/Library/Frameworks/Python.framework/Versions/3.12/bin/python3 runtime/replay_benchmark.py \
  --batch batches/local-pilot10-02 \
  --output kernel-replays/pilot10-02-r3 \
  --warmups 1 --repetitions 3
```

Use a new output directory for each run. The runner does not start Pi, read credentials, call an API, rewrite accepted source, or use controller acceptance caches. Both languages replay the same original task IDs, selected from tasks accepted in both languages. The original pilot contains eight such task pairs; the two non-jointly-accepted tasks are explicitly listed as excluded, and their original pass/fail scores remain untouched.

Each sample creates a NEW Session/REPL, loads the immutable seed and own predecessor library, then actually submits every candidate block. It separately runs the complete saved file in a fresh verifier process. Paired language order is randomized with a recorded seed; the experiment runs sequentially to avoid language-worker contention. Warmups are retained in raw data and excluded only from measured summaries. Verification failures are retained and make the replay fail; they are never silently dropped. A fresh process is not a flushed OS cache.

The replay writes `results.json`, `results.csv` and raw fresh-file receipts. It records artifact/job/verifier/runner hashes and zero model calls. The reported phases are:

- `session_initialization_seconds`: process/seed/predecessor loading.
- `warm_candidate_seconds`: candidate-native request/response time after baseline loading.
- `fresh_file_seconds`: a new process checking the full saved file, including imports/startup.

These are wall-clock verifier phases, not CPU-only kernel timings. Paired task IDs do not independently certify semantic equivalence of the two agent-generated formalizations. Source review remains a separate optional annotation.

## Agent metrics: keep all costs visible

Per-task manifests and results CSV also separate session initialization, warm candidate requests, recovery replay, independent final-file checking, other verifier work and non-verifier wall time. End-to-end time, token usage, pass rates and retries remain separately available. API failures remain in the task's cumulative accounting; missing provider usage stays unknown. Native work recovered outside a completed receipt is explicitly retained rather than being mislabeled as model time.

The compact profile reduces supplied guide text and tool round trips structurally. Actual model-request/token savings require a new real-API comparison and must not be inferred solely from prompt character counts or offline fixture messages.
