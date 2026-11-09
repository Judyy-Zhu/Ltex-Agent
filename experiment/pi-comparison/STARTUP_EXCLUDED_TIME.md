# Translation and verification time with initialization excluded

Use a new batch and explicitly enable the measured profile:

```bash
bash /Users/judy-zhu/AI4Math/auto-build/Stoicheia/litex-Stoicheia/experiment/pi-comparison/run_fast.sh --name local-generic10-01 --split-final-timing
```

This runs the original first ten tasks in both languages with the existing DeepSeek model, separate credentials, unchanged language tutorials, five total attempts and checkpoint recovery. It does not reuse previous generated libraries or results. The script prepares and checks the batch locally before making model requests.

## What the main time means

For each language:

`startup_excluded_seconds = language worker wall time - candidate-session initialization - independent-final-session initialization`

All candidate-session initializations and restarts are included in the subtraction, not just the first. Model generation, API waiting and failures, reference reads, retries, candidate verification, independent final verification, metadata inspection after initialization, cleanup and orchestration remain included. The measured initialization boundary includes the frozen technical seed and published predecessor library loading. These are wall times, not CPU-only times or isolated kernel benchmarks.

The sum of per-task corrected times omits gaps between task intervals. The final language figure instead starts with the language worker wall time, so those gaps remain included. The concurrent parent wall time is separate and must not be added to the language times.

## Independent final verification

The previous profile used a fresh CLI file-check process with one combined timer. It could not distinguish initialization from verification. This measured profile instead uses a NEW native Session/REPL for the independent final check in both languages. It reads the exact saved final file, verifies its hash-bound frozen prefix in the new environment, then actually submits and checks every remaining candidate block. It does not inherit the candidate session, previously accepted declarations, or its acceptance cache. The technical seed, predecessor code, mathematical candidate, no-placeholder guard and declaration/axiom gate remain checked.

Receipts use scope `independent_final_session`. They retain the verified file hash, independent PID/session ID, original foundation responses and original per-block native responses. They do not fabricate one native CLI run result from multiple responses. Initialization and candidate verification have separate monotonic timers; the final-process total also includes cleanup and instrumentation overhead. Only initialization is subtracted, so final verification is retained in the main time.

This changes the final-check execution mode relative to historical CLI batches; compare results with that limitation stated. It does not retroactively recover missing historical phase times. Neither the Pi agent nor either kernel is modified.

## Where to read results

`batches/local-generic10-01/report.json`:

- `summary.language_startup_excluded_seconds.litex` and `.lean`: the requested final language totals.
- `summary.workers.<language>.elapsed_execution_seconds`: unadjusted language worker wall time.
- `summary.workers.<language>.initialization_seconds`: measured subtraction.
- `rows[].startup_excluded_seconds`: per-task corrected time.
- `rows[].verification_timing.independent_final_initialization_seconds`: final initialization.
- `rows[].verification_timing.independent_final_verification_seconds`: actual final candidate checking, retained in the main time.

`independent_final_file_seconds` remains the legacy name of the complete independent final-process phase. Its detailed initialization/verification fields are subsets, not additional phases; do not sum both the parent and its details. Missing historical final-startup data and interrupted final attempts without a completed timing receipt produce null adjusted totals. No second-init estimate is substituted from the first init, and the entire final verification is never subtracted as though it were initialization.

Provider-reported tokens and kernel-acceptance rates retain their existing definitions. Kernel acceptance does not independently certify faithful source translation.
