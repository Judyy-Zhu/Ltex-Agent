# Run the full English Lean/Litex formalization comparison

The current local plan is local-resumable-01. See PARALLEL.md for the two-key parallel execution contract. All tasks, tools, prompts, guides and submission instructions are English and text-only. Original source statements and original proof text are included intentionally: the task is formalization-translation.

## Offline preflight and explicit start

```bash
cd /Users/judy-zhu/AI4Math/auto-build/Stoicheia/litex-Stoicheia/experiment/pi-comparison
bash run_local.sh preflight --name local-resumable-01
caffeinate -i bash run_local.sh run --name local-resumable-01
```

The launcher uses the validated local Python 3.12 rather than an arbitrary Conda environment. Preflight checks frozen code, guides, source, kernels, worker bindings and credential configuration without model calls. run starts the real model API experiment. One command starts both independent workers: Lean with primary and Litex with secondary.

## Inventory and budgets

The 13 books contain 644 registered tasks: 130 definitions, 5 postulates, 5 common notions, 465 propositions, 24 corollaries and 15 lemmas. One paired repetition schedules 1288 language-specific agent tasks. Each worker follows source order, retaining its own accepted library. Source order is not an audited dependency DAG; missing predecessors must be proved within the current task budget.

The full local batch permits five complete candidate rounds per source task, first attempt included. Task, batch, verifier-time and checker-count limits are null (unlimited). Final verification and publication do not consume candidate rounds. The shared model is Paratera DeepSeek-V4.1-Flash with thinking disabled, local context cap 32768 and output cap 8192. Retry/cache-warming policies and compaction settings are frozen in the plan. These are experiment caps, not claims about provider limits.

Each task starts a new Pi conversation with its current source TXT, shared task specification, preceding foundation texts, own-language frozen guides, minimal seed and actual published predecessor library. No images or historical formal answers are mounted. English explanations, comments, interfaces and submissions are required. Source mathematical notation is preserved.

## Progress, stop and resume

```bash
bash run_local.sh status --name local-resumable-01
bash run_local.sh report --name local-resumable-01
caffeinate -i bash run_local.sh resume --name local-resumable-01
```

Ctrl+C stops both workers and owned task/verifier processes. Resume retains previous costs and does not automatically retry finished or failed agent attempts. It recovers already durable complete valid submissions when possible, otherwise records interruptions and advances. Do not start concurrent parent controllers for the same plan.

## Results

report.json/results.csv record per-original-task elapsed time, provider tokens, verifier calls, machine-candidate and semantic-review status, and main/helper retry totals. items.csv lists each logical definition/proof, including attempts, retries, failures, cached checks and pending/unknown counts. Stable main IDs align the two languages. Automatic replay, final checking and submission gates are not proof retries.

Time includes model waiting, reading, tools, session initialization/replay, failures and final checking. Preparation is separate setup. Provider raw usage includes compaction and keeps missing counts unknown. Parent wall time is measured directly, not by adding overlapping workers. Shared-host contention is disclosed.

Machine success requires a current final receipt bound to saved work, complete clause mappings, interfaces and an in-budget declaration/axiom gate. It does not certify source fidelity. Optional semantic certificates can annotate source coverage, encoding, permitted assumptions and dependencies; they never gate task success or the primary score. The main accuracy denominator is 465 propositions; definitions and auxiliary items have separate statuses/costs. Unattempted tasks remain in the registered denominator. The current mode is exploratory and formal_result remains false until the mathematical reviews are complete.

## Engineering checks and new plans

Run the offline regression from runtime using the validated interpreter:

```bash
/Library/Frameworks/Python.framework/Versions/3.12/bin/python3 runtime/verify_sessions.py
```

The receipt binds source, guides and seed hashes and verifies native kernels plus actual Pi tool transport with providers that forbid model calls. Guide/prompt/code/input-policy changes require a new plan. Historical plans and results must not be rewritten or mixed with the current English run.

To prepare another range, use bash run_local.sh prepare with a new --name, explicit --execution parallel, --books and optional --limit-propositions. Preparation and preflight do not call the model API. Credentials remain outside agent inputs in ignored private files.

The success policy is automatic machine verification. Primary accuracy = machine-passed propositions / registered propositions. pending semantic status does not prevent passing, library publication, paired-success comparisons or primary scoring. Optional semantic_accuracy is reported separately. Historical frozen score policies are not reinterpreted.

formal_result is an informational mathematical-audit marker. It is not the per-task passed flag and does not block automatic execution or machine scoring.

Version 14 embeds the verbatim copied litex_auto_build_system/prompts/litex_short_guide.md as the Litex core reference and exposes it through read_docs(core). Lean receives its own core reference. Complete candidates include helpers in one file. Original definitions do not require invented semantic-bridge theorem projects. The stopped local-auto-english-01 remains diagnostic history and must not be resumed with revised code. Time and tokens remain measured per task despite the absence of a deadline.

## Current-task checkpoint recovery (version 15)

Each task has five TOTAL attempts per execution window; network/API failures share the same allowance with code candidate failures. Five all-API failures stop at this task without marking a mathematical failure. Earlier successful tasks and their libraries remain published. A later explicit resume continues the same source item, opens a new window only for an all-API exhausted window, and retains all attempt/time/token history. A partially used interrupted window keeps its remaining attempts. Mixed/exhausted proof windows follow the ordinary failure policy.

The complete Pi conversation is stored in pi-session.jsonl inside the attempt directory. The task's source, receipts, candidate journal, tool-result cache, attempt history and provider request logs persist there. Native verifier state is restored by replay; an interrupted native check reuses its already reserved attempt. Request IDs continue across process restarts. Missing usage remains unknown. Active task time accumulates across execution segments; stopped intervals are excluded and automatic network waiting is also reported separately. A lost in-flight API request may require resending.

First start and subsequent recovery can both use this command (it never recreates the plan):

```bash
caffeinate -i bash run_local.sh resume --name local-resumable-01
```

Ctrl+C saves checkpoints and stops both workers. If the foreground process remains running during a brief disconnect, it automatically retries while attempts remain. If it exits after five all-API failures, reconnect/fix the API and run resume. Do not start a second parent while the first is alive. Version 14 local-five-rounds-01 is an unused, superseded plan; use local-resumable-01. No API run is started by preparation/preflight.
