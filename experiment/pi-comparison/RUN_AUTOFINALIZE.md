> Historical protocol: the current compact/atomic instructions are in [RUN_COMPACT.md](RUN_COMPACT.md). The frozen local-context-safe-01 batch belongs to the earlier six-tool runtime and should not be resumed with changed runtime files.

# Run the repaired paired experiment

Run from this directory after offline preparation and preflight succeed:

```bash
caffeinate -i bash run_local.sh resume --name local-context-safe-01
```

Lean uses the primary credential and Litex uses the secondary credential. Both workers run concurrently, each with its own persistent Pi conversation, sources, native session, library, receipts and counters. The experiment has no task or verifier time limit. There are five total attempts per source task, including network/API failures. Five failures consisting only of API/network errors checkpoint the same task; explicitly running the same command reopens its attempt window and retains all historical measurements. Other interrupted tasks retain their remaining attempts.

Open two extra terminals for read-only monitoring:

```bash
bash monitor.sh lean --name local-context-safe-01
bash monitor.sh litex --name local-context-safe-01
```

Both workers use the same deterministic local compaction policy: Pi makes no background summary API calls. A mechanical checkpoint preserves the original primary TXT verbatim, current candidate or its exact file reference, native receipt references and attempt counters; the original conversation and full diagnostics remain on disk. The context/output budgets are identical for both languages.

This batch uses the controller automatic-finalization protocol. The agent receives the complete primary source TXT, task, technical seed, foundation, field guide and own-language library index up front. It writes one complete candidate and calls the incremental checker. Failed native checks return the full original language-specific diagnostics. Litex uses its native persistent Session; Lean uses a persistent REPL environment. Earlier published own-language source is loaded in both.

After a complete candidate passes, local code generates the public declaration index, assembles the final file, independently checks the saved file and validates declaration/axiom dependencies. Litex reuses its native accepted-statement JSON; Lean uses trusted native environment inspection. No second Litex process is launched solely for indexing or manual clause labels. Successful finalization durably saves submission.json and blocks further model requests. Interrupted local finalization resumes without another model request or candidate attempt. Independent final verification failures still prevent completion.

Controller-generated clause associations are explicitly unreviewed task-level associations. Semantic review remains optional metadata and does not block the machine pass score. Machine pass rate is not an independent measurement of source fidelity.

The older local-resumable-01 batch is preserved and stopped. Its runtime was frozen under the previous protocol, so do not resume it using the changed runtime or combine its results with this repaired batch. The new batch starts both languages from the same task list and technical starting seeds. No full experiment is launched by preparation or preflight.

Each task's files appear under:

```text
batches/local-context-safe-01/workers/lean/attempts/NNNN-lean/
batches/local-context-safe-01/workers/litex/attempts/NNNN-litex/
```

The active attempt directory is printed by the monitor. work/candidate.lean or work/candidate.lit contains the current translation; work/final.lean or work/final.lit is the independently checked assembly. work/interfaces.json stores the native public index. receipts/ contains full checks; session-events.jsonl records native requests and responses. auto-finalization.json, submission-gate.json and submission.json record local completion. manifest.json contains cumulative per-task wall time, checker_seconds, non_checker_seconds, verification_timing, usage and retry_statistics. Provider token usage remains unknown when the provider does not return it.

checker_seconds measures verifier phases, including session initialization and local declaration inspection. verification_timing separates startup, incremental candidates, replay, independent final file and declaration gate. non_checker_seconds includes model, network and local orchestration; it is not pure model inference latency. The monitor prints completed verifier time while the task is still running. All task measurements accumulate across resumption and exclude known manual downtime.

The current automatic mode exposes six tools: read_input, read_docs, read_library, write_source, check and remaining_budget. No manual submit/item metadata/final-file modes are exposed. Symbol queries return real published source and native signatures; compaction retains the technical seed, interface, published symbol index and already-retrieved materials. Total definitions need only native domain/type formation checks; extra existence or characterization proofs are requested only when the current source or an actual constructor requires them.

The completed real-API diagnostic pilot is local-pilot10-02: Book I definitions 1–10 in both languages. Its results.csv, report.json and pilot-summary.json retain per-task time, usage lower bounds and attempts, including the observed API outage and resumption. Both languages completed 10 tasks with 9 machine passes. The pilot used the current frozen runtime; local-pilot10-01 and older batches remain diagnostic history and should not be resumed with this changed runtime. The full local-context-safe-01 batch is prepared only; it has not been launched.
