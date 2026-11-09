# Litex-first agent workflow optimization

The current generic tutorial/diagnostic revision is v24; see [GENERIC_LANGUAGE_OPERATIONS.md](GENERIC_LANGUAGE_OPERATIONS.md) for its paired operation coverage, source-location routing and the new diagnostic run command.

New `prepare` commands default to `direct_candidate_with_local_repair_v1`. The frozen task job and batch plan explicitly record this profile. Historical runs retain their files and results; use a new batch name after updating this checkout.

The original source TXT and every mathematical task clause remain intact. The technical seed is unchanged. No Euclid answers, extra geometry axioms or target proofs are preloaded.

## Request path

1. The initial prompt supplies the source, seed, actual predecessor code and checked generic operations. A display copy removes predecessor comments only; native verification still receives the unchanged, hash-bound original library. Needed original context texts are included when they fit.
2. If the full predecessor display and original context fit, the first provider request exposes and requires only `submit_candidate`. There is no ceremonial library read or documentation-index request.
3. A rejected candidate returns the full original native diagnostics plus deterministic local repair hints. Hints point to checked operations; no model is called to summarize the error or choose a repair example.
4. After rejection, at most one information-only assistant turn may batch indispensable lookups. The following request requires a complete candidate. If the predecessor library is too large for the initial display, the initial indispensable lookup remains available too.
5. Success still requires native acceptance, independent final-file checking and the declaration/axiom gate. Local indexing, final checking and submission consume no model request. Five total task attempts continue to include candidate, failed generation and API/network failures. There are no task or kernel time limits.

The operation packs contain nine corresponding categories: explicit function expansion, existential extraction, negated-existential contradiction, coordinate equality, predicate declaration, quantified definitions composed from named predicates, sets/membership, parameter constraints, and logical composition. Each pack is checked against the actual native kernel, not merely copied from prose. The Lean counterparts have the same generic mathematical statements. The multi-line antecedent rule was corrected for the pinned Litex executable: one premise per line, without a trailing comma. The original user-specified guide remains preserved as a provenance source.

The initial operations and later repair references are teaching material, not declarations already loaded in the verifier. Adapt fresh names and preserve all source requirements. A generic repair example is never a proof of the actual target.

## Message-first repair revision

Runtime revision `v22-message-first-repair-and-paired-quantifiers` selects the first non-replay native error. Litex uses `errors`; Lean uses error-severity `messages` and native process errors. The diagnostic message has priority over the submitted statement. A source name containing `witness` or a `GeoPoint` domain does not select a proof procedure. Parse errors receive syntax guidance before any proof-search advice. Long messages have only a bounded preview in the repair metadata; the original native diagnostic is retained intact.

Missing-name advice explicitly distinguishes the published predecessor library from helpers in a rejected candidate. Each submission is a complete replacement, so required new helpers must remain in the candidate and precede their uses. Both languages receive this rule. The named-quantifier examples teach only generic real-number predicates; they do not add Euclid definitions, axioms or target answers to the seed.

Use a new batch name to measure this revision. Do not resume a historical batch in order to claim a clean before/after comparison. Offline routing replay demonstrates which advice is selected, not that a real model will use it successfully or that its language familiarity has become equal.

To investigate language familiarity separately, freeze independent paired exercises before evaluating models. Cover predicate definitions, functions, quantifier scope, witness extraction, implication and simple proof repair, using mathematical material outside the formalization evaluation tasks. Record first-candidate parse success, kernel acceptance, tokens and retries before and after providing the fixed language tutorials. Keep the guide and model revision fixed during each evaluation. These diagnostic exercises must not be added to the Euclid success denominator. Equal tutorial length, equal training budgets or equal exercise scores do not establish identical pretraining exposure.

## Foreground run

After the offline regression and preflight pass, run from any directory:

```bash
bash /Users/judy-zhu/AI4Math/auto-build/Stoicheia/litex-Stoicheia/experiment/pi-comparison/run_fast.sh --name local-repair10-01
```

This prepares or resumes `local-repair10-01`, runs the same first ten original definition tasks for both languages with the existing separate credentials, and keeps the controller in the foreground. Ctrl+C saves the current checkpoint; running the same command resumes it. The source-cache shortcut reuses only verified source text, never prior generated libraries. The script's historical default name remains `local-direct10-01`; explicitly supply the new name above to avoid resuming that completed run.

Progress includes `finished_task_verifier_seconds` and `finished_task_warm_kernel_seconds` separately from total elapsed wall time. These totals cover finished tasks only, and unavailable timing stays null. Detailed time, token and retry accounting remains in the per-task records. Both languages use the same orchestration policy; the language-specific instructions retain their own syntax and native errors.

For two independent read-only views:

```bash
bash monitor.sh lean --name local-repair10-01
bash monitor.sh litex --name local-repair10-01
```

## Separate native measurement

The full agent experiment measures model, network, reference lookup, repair and verification together. The native diagnostic measures nine explicitly matched generic operations without an agent, API key or model call:

```bash
python3 runtime/benchmark_kernel.py --output benchmarks/kernel-direct-01 --repetitions 3 --warmups 1
```

Every sample uses a newly initialized native process, actually submits candidate code without acceptance-cache reuse, and separately checks the complete saved file in another fresh process. Language order is randomized within paired samples. Initialization, warm request-response and fresh-file timing are reported separately. All failures and warmup rows are retained; only warmups are excluded from measured summaries. Source, seed and kernel hashes identify the tested artifacts. This diagnostic measures the stated generic operations, not Euclid translation accuracy.

`--reference-protocol` on a new `prepare` command selects the previous three-information-turn profile for an explicitly labeled comparison. Do not mix its end-to-end measurements with the new profile as though the orchestration were unchanged.

Kernel acceptance remains separate from source fidelity. Pending semantic review never blocks the machine acceptance path. Measured real-model efficiency must come from a new API run; deterministic offline Pi fixtures only establish the request protocol and native execution path.

For directly measured translation-plus-verification time with BOTH initialization stages excluded, use the new opt-in final-session timing profile documented in [STARTUP_EXCLUDED_TIME.md](STARTUP_EXCLUDED_TIME.md). The command is `bash run_fast.sh --name local-timing10-01 --split-final-timing`. The final checker uses an independent fresh native Session/REPL with separately measured loading and actual candidate checking; historical CLI initialization cannot be recovered from its combined timer.
