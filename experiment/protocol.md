# Euclid I–VI authoring experiment

Experiment ID: `euclid-2026-10-11-gpt61-sol-medium`.
Status: running. The end state remains faithful representation of Books I–VI (173 propositions and included source items), with explicit checked/debt counts; an initial pilot does not replace the full target.

## Research question and treatment

Observe the resources and mathematical progress of one Codex agent, using the user's requested `gpt-6.1-sol` with reasoning effort `medium`, redeveloping Euclid I–VI over existing 2D analytic geometry. This is an observational single-run experiment, not a controlled comparison or an estimate of average model performance.

The current thread's `turn_context` at `2026-10-11T02:25:05.398Z` reports model `gpt-6.1-sol` and effort `medium`. Confirm those fields at each metrics checkpoint. No subagents are used. Keep any model/effort changes, user intervention, kernel changes, foundation changes, or resumed pauses visible as deviations rather than silently combining them.

## Starting conditions

- Experimental start: 2026-10-11 10:25:05.398 Asia/Shanghai (02:25:05.398 UTC), the first turn authorizing the experiment.
- Goal created timestamp: 1791685505; goal counters initially report zero tokens and zero seconds.
- Earlier chat contains source inspection, legacy audit, and planning. Record these as preparation, excluded from experimental usage deltas but still present in the model context.
- Initial Git HEAD: `b7fd439a3516530c10e7bf039c04911a1c75e54b`. The working tree already has unrelated changes; save their status and fingerprint the actual selected source files before building. HEAD alone does not identify the tested implementation.
- Source: Fitzpatrick's Euclid PDF; legacy input: `../Book.zip`, 48 proposition files, of which I.3–I.48 are reflexive-conclusion placeholders.
- Reusable foundation: `showcases/math_concepts_in_litex/2_euclidean_geometry/`. Reuse is part of the treatment; this is not from-scratch geometry-library development.
- Foundation semantics: real-coordinate Euclidean plane. Geometric statements and source construction correctness remain required. Do not claim derivability solely from Euclid's five postulates.

## Measurements and provenance

`collect_metrics.py` reads only model metadata and token-count records from this thread's local rollout JSONL. It does not copy conversation text, credentials, or unrelated sessions. Snapshots go to `metrics.jsonl`.

For each snapshot record:

1. Observation timestamp, elapsed wall seconds from start, stage and last available token-event timestamp.
2. Actual model/effort and selected source revision/fingerprints.
3. Cumulative input, cached-input, output, reasoning-output, cache-write-input and total token fields as exposed by the log; subtract the final event preceding experimental start for experiment deltas.
4. Input minus cached input as an explicitly computed uncached-input count. Cached input is a component of input, not an additional term; reasoning output is reported separately and must not be added again to output without an established accounting contract.
5. Goal-tool `tokensUsed` and `timeUsedSeconds` when available, with separate provenance. Do not assume these counters equal rollout totals or average them together.
6. Coverage/verification counts from source-owned records, failed attempts, surviving direct/imported trust, and build/verifier command receipts.

Rollout counters count repeated model inputs, including cached context. They are not unique source tokens, file size, or price. Do not infer money spent from them. Token events can lag current work: each snapshot's token timestamp is its accounting cutoff, not necessarily the observation timestamp. The final checkpoint must be captured in a subsequent tool-visible interval so late usage is included. Treat absent data as null; never estimate hidden thinking time or invent exact tokens. Reject/reset a delta if cumulative counters regress; record the reset instead.

Wall time includes model/tool latency, user waiting and idle periods. Record explicit pauses/interventions and command wall durations separately. `active_reasoning_seconds` is unavailable, not wall time minus command time. Do not report parallel/double-counted command totals as model time. The mainline remains one agent and sequential proof submission.

## Ordered execution

1. Capture baseline token/model/source metadata, register the experiment and update the existing task ledger.
2. Build the current release once, timed; rerun the selected analytic module and inspect the first failure if any. Record actual binary hash/version and source fingerprints around the build.
3. Establish one canonical `scripts/Euclid_Elements/textbook/` module, registered in `scripts/.textbooks`. Write its one README and mathematical design manual before substantial declarations. Freeze exact dependency ownership after the foundation gate.
4. First pilot: I.1 and its genuine noncollinear equilateral witness, then I.2 including coincident starting points; expand through I.8. The I.1 tracer links the existing coordinate construction with the book's two-circle requirements.
5. Continue the bounded book slices in `../migration_plan.md`, in source order, preserving theorem identity and independently justified definitions.
6. Use one persistent release Session. Journal each top-level statement's source, timestamps, mathematical role, actual output, outcome, and restart reason. Failed ordinary statements stay in that Session.
7. At each accepted file/slice checkpoint, run the registered clean `-f` gate, capture a metrics snapshot, update source-item status and factual documentation, and run the required liveness/debt audit.
8. Complete each book and the six-book integration gate; revisit exact proof debt under the repository two-pass timebox. Stop protected owner changes for the existing concrete authorization boundary.

## Outcomes and interpretation

Primary outcome: faithful source coverage, with count of actual checked proofs under the disclosed foundation and separately count of statements depending on temporary trust. File presence and a green verifier over placeholders are not mathematical completion.

Secondary outcomes: experimental token deltas by category, wall time by slice, failed materially distinct proof attempts, command runtimes, restarts, source mismatches, model/user interventions, and dependency gaps. Report per-item resource ratios only with the denominator's precise status (translated or checked) and note shared foundation overhead. Ratios do not predict remaining books before observing their different dependencies.

For example, legacy I.47 has conclusion `a = a`; checking it does not count as Pythagoras. Completion requires a nondegenerate right-triangle hypothesis and the actual square/area relation, with corresponding proof evidence. I.1 also requires a valid triangle, not only an equal-distance formula labeled as a triangle.

## Files and checkpoints

- `protocol.md`: this method and deviations.
- `collect_metrics.py`, `metrics.jsonl`: reproducible measurement and snapshots.
- `baseline.json`: selected source and archive fingerprints, initial dirty-tree status, and baseline log counters.
- `commands.jsonl`: command, start/end timestamps, duration, status, and receipt path.
- `../proof_journals/`: individual theorem/definition attempts and accepted source.
- `../translation_records/`: source fidelity and checked/debt status.
- `../.draft/`: scratch targets and raw command/session captures.
- `../experience/problem_notes/`: durable acceptance comparisons at verified checkpoints.

## Deviations

- Foundation audit found a more complete existing analytic library at `scripts/LitexGeo-AutoBuild/shenjiachen/新geo和geo_definitions/geo.lit`, documented historically as 40 definitions and 186 theorems. Its current full gate is running. The smaller I.1 showcase passed the current strict file gate in 46.435 seconds. Evaluate the fuller library before selecting final dependency ownership.
- A definitions-only draft Session may be used for the first pilot while the complete library gate runs. It uses the actual `geo_definitions.lit` as export `geometry`; its namespace matches the planned full-library export. This is a reduced authoring context, not a canonical proof completion gate. Adopting the full prefix requires a deliberate restart/replay and full-context checkpoint.
- The two independent baseline commands overlap in wall time. Command durations must not be summed as experiment elapsed time; record this departure from the initially sequential baseline measurement.
- Planning and telemetry setup count toward experimental time/tokens; pre-start preparation is excluded from deltas.
- The full current geometry gate passed: 227/227 statements, strict, exit 0, success true, no session error, 438.6148 seconds. Source and binary fingerprints are in baseline/command records.
- Full-library Session 95113 accepted I.1 (including nonzero determinant and the two circles) and I.2 (including coincident start/input endpoints), without trust. Their canonical registered file is `../textbook/book01-constructions.lit`; its independent file verification remains pending.
- I.3's first frame used reserved builtin name `e`, which terminated Session 95113. Preserve the actual failure, replace the existential binder by `z`, and replay the accepted registered I.1/I.2 prefix in Session 39247. This is an authoring error and additional setup cost, not a kernel defect or mathematical blocker.
- After that error, introduce the existing `-latex -f` converter as a parse-only preflight in an isolated draft manifest. The corrected I.3 parses in 0.0068 seconds; its former reserved-name source rejects as a negative control. This gate does not verify mathematics or discharge WD. Keep accepted dependencies in the preflight context when names need them. This mid-run authoring change is recorded as an experimental intervention; no permanent skill rule was added.
- The registered I.1/I.2 replay and an independent I.1 deletion probe overlap. The deletion probe omits three product-membership echoes and deliberately excludes the already-proven book theorem. Treat command wall times as concurrent observations, not additive elapsed time or a serial performance comparison. No source target is changed while its verification is running.
- Registered replay 39247 terminated with failed I.1/I.2: operation releases in a preceding export did not populate the book file's environment. The mathematical Session results remain historical evidence, not clean-file certification. Move the four required releases into the actual Book I file and remove the ineffective initialization export. This is an authoring/context repair, not a verifier change. The standalone deletion probe already uses its own local releases and continues under handle 39175.
- The corrected first-three-proposition registered batch gate passed: exit 0, all eight target statements successful, no session error, source hash unchanged, 458.1708 seconds. I.1/I.2 concrete consumers and their mathematical rejection boundaries passed their expectations in the live Session. I.3 was added only from accepted journal source.
- That batch's receipt collected the binary hash after completion, not at process launch. It differs from the original measured executable. The exact loaded executable for this gate is therefore unknown; do not relabel its post-run hash as the launch hash or treat this interval as a fixed-verifier comparison.
- Epoch 2: rebuild the current source with stable before/after tree hashes, copy exact release bytes into `.draft/pinned-release/target/release/litex`, record their hash/version, and use that immutable release snapshot for future frames and gates. This remains the current-source release executable, not a debug or historical system binary. Existing kernel source changes were not authored by this experiment. Save accepted source and deliberately restart/replay when adopting the new executable; this is not an ordinary-failure restart.
- Definitions-only attempts established the need for explicit `release obj def` at a cross-file use boundary. No kernel repair was made. The pilot Session is deliberately replaced when adopting the full library, so its existing positivity/coordinate theorems can be reused rather than reconstructed. The production dependency is a manifest referring to the original library, not a source copy.

- Later full-prefix replay (Session 64406) remained live without new stdout through 04:31:27 UTC. While preserving it, author faithful parser-only I.5–I.12 drafts and inventory the 33 Book I foundation items. These are not canonical proof completion. An independent I.11 diagnostic selects the exact original geometry definition prefix and exact point_difference_norm_pos theorem under `.draft/reduced-check/`; no axioms/trust or canonical dependency change. Its first clean-file check failed at the alias expression dx^2+dy^2>0. Repeat the unchanged source once solely because the first observation truncated JSON; save complete feedback and keep that reproduction separate from a distinct authoring attempt. An explicit coordinate-equality repair draft is pending verification in the mainline Session. The independent diagnostic overlaps the full replay; never sum their command durations as experiment elapsed time.

- Authoring-context intervention: preserve full replay 64406 as the independent complete-context check while establishing one reduced authoring Session. Three dependency selections (12, 16, 25 original unchanged theorem bodies) fail the original isosceles_base_dot proof before reaching a REPL. The first fails at its dot-from-lengths statement; the next two fail at its final base-dot equality. These are prefix-selection diagnostics, not failed I.5 theorem submissions or evidence of a kernel defect. No library proof was rewritten and no signatures/trust assumed. The next prefix preserves all 70 original predecessor theorems through isosceles_base_dot, plus four originally selected later affine/determinant helpers, and is loading under Session 62166. Exact draft snapshots and failed JSON are retained under `.draft/authoring-slice/`. These processes overlap the full replay, so times are not additive. Canonical source still imports the complete original library.

- The contiguous 74-theorem original library slice initialized successfully. I.5 base and below-base conclusions and the shared I.4 proof passed strict Session 62166 without trust. A first-five full-original-library isolated checkpoint then passed (13 target statements, 582.060s, exit 0, success true, no session error, hashes captured at launch and completion all stable). Promote byte-identical source plus a production-only helper export; launch the required canonical path/manifest gate. Stop the old full replay 64406 deliberately to adopt the verified replacement prefix, not as a successful old gate or a timeout outcome.
- Sequentially replay eight original AAS-support theorem bodies in the authoring Session, namespace-adapted but not assumed. Sending AAS itself reveals an input transport failure: one 1512-byte line produces 507 BEL characters in canonical TTY mode; no valid math result is claimed. Save the accepted source prefix, stop 62166 to replace the broken transport, and start Session 48605 with `stty -icanon -echo` on its own task PTY. Pipe output through `tee` to `.draft/authoring-pipe/session-raw.log` so future verbose failures can be read in full despite observation clipping. Its prefix replays the 74 source library proofs, the two accepted geometric helpers, and eight accepted late library proofs; restore success before sending AAS again. No Rust, AST, Env or Runtime changes are made. Both source coverage and telemetry distinguish transport failures from mathematical authoring failures.

- Canonical first-five wiring gate passed: 13 target statements, 562.579s, exit 0, success true, no session error, all launch/completion source and pinned binary hashes stable. Noncanonical-TTY replay accepted AAS without BEL loss; I.6 passed, I.7 passed after correcting the cosine-law vertex order and explicit projection/determinant calculations, and I.8 passed after exposing reversed side equalities. Save I.6–I.8 to canonical source with references restored to the original full-library names and launch the first-eight strict gate (handle 32519). Root replay/library diagnostics do not increment numbered proposition counts. Source I.9 and later, all foundations, and Books II–VI remain incomplete.

- Canonical first-eight strict full-original-library checkpoint passed (16 target declarations, 648.040s, stable launch/completion hashes). Continue in the same Session 48605: I.9 passes after explicit witness/affine/vector/sign bridges, I.10 after midpoint parameter expansion, I.11 after explicit rotated-endpoint projections, I.12 after explicit projection displacements. Zero trust and zero kernel changes. Save first-ten canonical source and run gate 35528; stage I.11/I.12 without mutating frozen gate sources. First-twelve staged source is not reported as file-checked. Next I.13 interface audit must preserve the actual angle-sum statement.

- Angle-magnitude modeling for I.13 uses native principal arccos in radians. Prove geometric norm-product domain facts before defining normalized cosine; function definition checked once exact nonnegative and sqrt-nonzero facts are available. Two bounded opposite normalized values have principal arccos values summing to pi. The normalized cosine range proof reaches abs(n) lower-bound transport. A malformed by-cases draft missing its ? goal/case prefixes was incorrectly submitted after a failing preflight; this is an author/control error and fatal parser stop, not a kernel/math failure. Preserve the failure, fix syntax and positively check preflight before launching any further submission. Restore accepted source in Session 55623, keep noncanonical input and tee complete log. This restored prefix and the independent first-ten gate remain live; no outcome is guessed from observation timeout. No numeric-angle function or I.13 proof counted complete.


Clock and transport observation update: gate wall_seconds is obtained from Python time.monotonic. UTC start/end strings and the collector’s UTC experiment span are distinct observations; measured first31 differences are preserved in clock-observation.json, cause not verified. Do not equate, add, or label either duration as CPU time. All author preparation/transport failures remain part of this experiment. prepare_repl_statement.py reads only workspace-owned files, enforces one root statement, strips REPL-terminating interior blanks, checks exact headers and pinned parser artifacts, and emits structured source only after success. Callers must inspect exit_code and JSON preparation kind before sending anything. Optional preflight-only root-function context is never returned in transferred source. Runtime success still requires actual Session/cold-gate feedback.
