# Local English text-only parallel experiment

The current batch is local-resumable-01 (version 15). All agent-visible task instructions, tools, prompts, guides, comments and submission metadata use English. All 644 tasks are text-only. Historical local-parallel-* and local-text-only-01 plans are preserved and are not the current English batch.

Lean uses the primary credential alias; Litex uses secondary. Private configurations remain in ignored private/api_config.json and private/api_config.secondary.json with mode 600. Plans, inputs and reports contain aliases, not keys or key hashes. Credentials are not passed on command lines or mounted for agents.

Two independent worker processes start together. Each builds its own language library in source order without waiting for the other language. Tasks within a worker remain sequential. Workers have separate conversations, checkpoints, libraries and metrics, with a shared read-only source-text snapshot. They cannot read each other's artifacts.

The workers share the Mac CPU, memory and network; results are labeled shared_host_concurrent. Separate keys do not prove separate provider accounts/quotas. Actual waiting, rate limits and failures remain measured. Do not mix these timings with historical serial runs.

## Start

Use run_local.sh on this Mac to select the validated Python 3.12 with pdfplumber. An arbitrary Conda base python3 may lack dependencies; no installation into base is needed. Workers, task runners and tool brokers inherit the same interpreter through sys.executable.

```bash
cd /Users/judy-zhu/AI4Math/auto-build/Stoicheia/litex-Stoicheia/experiment/pi-comparison
bash run_local.sh preflight --name local-resumable-01
caffeinate -i bash run_local.sh run --name local-resumable-01
```

Preflight is offline. The run command actually calls the model API and starts both workers; do not start a second parent controller.

Check progress:

```bash
bash run_local.sh status --name local-resumable-01
```

Ctrl+C stops both workers and cleans their task/verifier processes. Resume with:

```bash
caffeinate -i bash run_local.sh resume --name local-resumable-01
```

Finished tasks are not regenerated. Interrupted tasks resume the SAME attempt directory and Pi conversation with their remaining allowance. Five total attempts consisting only of network/API errors checkpoint the current task and stop the workers; explicit restart opens a new window for that task, retaining earlier usage/history. Earlier network errors do not prevent a later kernel-checked task from passing. Owned processes are identified by PID plus birth before cleanup, and one controller lock prevents duplicate launches.

## Scope and budget

Each language has 644 source tasks, including 465 propositions: 1288 agent tasks in one paired repetition. Per language/task: five whole-task candidate rounds including the first attempt. There is no task, batch or verifier time limit and no separate checker-count cap. Helpers share the task counter; final verification and publication are excluded. Model, budget, English source text and seed mathematical interface are shared; formal-language guides/adapters and credential aliases differ.

Parent wall time is measured directly, excluding paused intervals. Worker/task intervals overlap and cannot be added to obtain wall time. Coverage curves use each language worker's execution clock.

## Inputs and outputs

Every task receives task.json, original source TXT including original proof text/notes, own-language guides, seed and accumulated library. No PNG, initial figure, auxiliary proof diagram, completed figure or screenshot is provided. Image reads and image API payloads are forbidden. Missing textual conditions are source-material problems, not permission to invent premises or seek images. Mathematical notation is retained.

run.py saves actual system-prompt.txt/user-prompt.txt and their hashes in each attempt. English task metadata is generated without rewriting the historical shared catalog. New experiments start with empty accumulated libraries, so no historical Chinese library metadata is inherited.

Outputs under batches/local-resumable-01 include report.json/results.csv for task-level status, time, tokens and retry totals; items.csv for per-definition/proof attempts/retries; and workers/lean and workers/litex for their libraries, checkpoints, native receipts and provider usage. Passing the automatic final/submission gates determines task success and primary accuracy. Semantic review is optional metadata and never blocks success or publication.

## Other ranges

```bash
bash run_local.sh prepare --name english-pilot-01 --execution parallel --books 1 --limit-propositions 8 --max-rounds 5 --source-cache batches/local-resumable-01/source-cache
```

prepare is offline and defaults to serial unless --execution parallel is specified. Frozen plans cannot change execution/input policy in place. The current full batch is already prepared; do not prepare it again under the same name.

The secondary key and current English runner have not been synchronized to the earlier server bundle. A later server migration requires separate code transfer and a newly frozen server plan.

The success policy is automatic machine verification. Primary accuracy = machine-passed propositions / registered propositions. pending semantic status does not prevent passing, library publication, paired-success comparisons or primary scoring. Optional semantic_accuracy is reported separately. Historical frozen score policies are not reinterpreted.

Version 14 embeds the verbatim copied litex_auto_build_system/prompts/litex_short_guide.md as the Litex core reference and exposes it through read_docs(core). Lean receives its own core reference. Complete candidates include helpers in one file. Original definitions do not require invented semantic-bridge theorem projects. The stopped local-auto-english-01 remains diagnostic history and must not be resumed with revised code. Time and tokens remain measured per task despite the absence of a deadline.

## Current-task checkpoint recovery (version 15)

Each task has five TOTAL attempts per execution window; network/API failures share the same allowance with code candidate failures. Five all-API failures stop at this task without marking a mathematical failure. Earlier successful tasks and their libraries remain published. A later explicit resume continues the same source item, opens a new window only for an all-API exhausted window, and retains all attempt/time/token history. A partially used interrupted window keeps its remaining attempts. Mixed/exhausted proof windows follow the ordinary failure policy.

The complete Pi conversation is stored in pi-session.jsonl inside the attempt directory. The task's source, receipts, candidate journal, tool-result cache, attempt history and provider request logs persist there. Native verifier state is restored by replay; an interrupted native check reuses its already reserved attempt. Request IDs continue across process restarts. Missing usage remains unknown. Active task time accumulates across execution segments; stopped intervals are excluded and automatic network waiting is also reported separately. A lost in-flight API request may require resending.

First start and subsequent recovery can both use this command (it never recreates the plan):

```bash
caffeinate -i bash run_local.sh resume --name local-resumable-01
```

Ctrl+C saves checkpoints and stops both workers. If the foreground process remains running during a brief disconnect, it automatically retries while attempts remain. If it exits after five all-API failures, reconnect/fix the API and run resume. Do not start a second parent while the first is alive. Version 14 local-five-rounds-01 is an unused, superseded plan; use local-resumable-01. No API run is started by preparation/preflight.
