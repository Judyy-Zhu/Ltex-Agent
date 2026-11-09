Current version 15 adds SAME-task checkpoint recovery with a durable Pi session and tool-result cache. Five total attempts share code/generation/network failures. Five all-API failures pause without grading the task as a mathematical failure; explicit restart continues this task with a fresh window and full historical costs. Partial windows retain their remaining allowance. See PARALLEL.md and agent-kit/guides/task-rounds.md.

Current version 14 uses five whole-task candidate rounds and no task/batch/verifier time or checker-count cap. The complete user-specified Litex guide is embedded in the system prompt and available through read_docs(core). See agent-kit/guides/task-rounds.md for the current protocol. Earlier fragment descriptions below apply to historical tracked_fragments jobs.

# Pi runner for English text-only Euclid formalization

Version 13 uses English task instructions, tool descriptions, system/user prompts, guides, comments and submission metadata. Every task is text-only. Source TXT retains original statements, proofs and notes; original mathematical notation is preserved. The current mode measures formalization-translation, not statement-only proof discovery.

The full catalog contains 644 source items, including 465 propositions. Each language builds an independent library from a minimal technical plane seed. Published machine-passed tasks are immediately usable. Semantic review is optional and never gates success, publication or primary scoring; complete foundation equivalence is not certified. Run instructions are in ../PARALLEL.md and ../RUN_FULL.md.

## Tools and boundaries

Both languages use read_input, read_docs, read_library, write_source, check, remaining_budget and submit with the same schemas. Pi builtin shell/read/edit/write, MCP, skills and automatic project-context discovery are disabled. The explicit tools.ts extension serializes tool calls.

Resolved-path boundaries reject absolute paths, traversal and escaping symlinks. Agents cannot read credentials, controller logs or the other language's output. Compiler processes do not inherit model API keys. The source guard rejects placeholders, unapproved trust/import features and Lean metaprogramming. This is not a claim to sandbox a hostile compiler.

No image is generated or mounted by current source preparation. New caches contain verified TXT and pack.json only; converting an old cache copies verified text without images. read_input permits text formats and rejects image/binary reads. Per-task model configuration declares input=[text]; the transport rejects image payloads before sending. Historical diagram inventory/crop scripts are retained as development material and are not part of this run.

## Native sessions

incremental uses native persistent verifiers: Litex -strict -lang en -session and the pinned Lean REPL. A persistent Python broker serves Pi tool calls. Ordinary failures preserve prior accepted context; Lean does not adopt failed returned environments. Hard process failure triggers startup and journal replay, with no silent whole-file fallback. Failed replay blocks continuation.

Each tracked fragment contains one complete top-level definition/proof with stable item_id/item_kind. Editing accepted source invalidates dependent suffixes, which must be rechecked in order. Accepted-source exports assemble the frozen seed, published predecessors and current journal. Final checking runs the complete saved module in a fresh process and preserves the writing session.

The common receipt includes passed, receipt_id, source_hashes, scope, process_status and session. Native inner feedback is preserved: complete Litex Session JSON, or Lean REPL messages/sorries/env plus environment transition. Final diagnostics retain each language's actual format. Litex final display follows the historical three-field formatter while termination/exit controls remain in the full receipt. No JSON is truncated into invalid syntax.

## Seed and publication

The shared mathematical interface real-plane-algebra-v1 provides GeoPoint, geo_point, geo_x, geo_y, geo_vec, geo_dot and geo_det. Sources are seeds/plane.lean and seeds/plane.lit; seed-interface.json specifies the same mathematics. Vector direction is b-a and determinant is u.x*v.y-u.y*v.x. Euclid-specific geometry remains agent-built.

Preparation freezes seed/interface hashes. Native startup/restart loads those files and the own-language published predecessor library. Final source must preserve the unchanged prefix. Seed declarations are not agent-completed source tasks. Three-dimensional books require explicit additional representations; a pair is not a 3D point.

Only complete submissions with a current successful final receipt, clause mappings, interface metadata and in-budget declaration/axiom gate can publish. The gate checks actual declarations and Lean #print axioms or Litex strict acceptance. Failed task increments are rolled back at the task boundary, even if some local fragments were accepted. New tasks inherit the library, not prior chat.

## English prompts and inputs

prompts.py constructs actual English system/user prompts. run.py saves their snapshots and hashes before launching Pi. prepare.py copies frozen own-language guides. agent_language.py creates English task metadata from the historical catalog without modifying it, and rejects CJK text in mounted inputs/guides, source/interface writes and submission metadata. Native Litex is explicitly configured for English; Lean diagnostics are preserved in English.

Every task receives task.json, source-manifest.json and current/needed predecessor foundation TXT. Source order is navigation, not an audited logical dependency graph. Missing results must be proved, not assumed. Missing or ambiguous textual initial conditions are reported as source-material problems; no image fallback is available. Generic clauses cover full source content and encoding; the I.1 development contract has C1-C5.

## Timing, usage and retries

The controller uses a monotonic clock from before Pi startup through process-group cleanup. Task time includes model waiting, reading, tools, native initialization/replay, failures and final verification. Source/software preparation is separate setup. Deadlines terminate owned process groups. agent_settled, not the first agent_end, determines the end of the loop.

The native transport logger records real requests and provider usage, including compaction calls bypassing ordinary message hooks. Only authoritative deduplicated usage is summed. Cache/reasoning fields are not counted twice; unknowns remain unknown. Automatic SDK retries and cache warming are disabled. The shared development limits are context 32768, output 8192, compaction reserve 14000 and recent context 6000; these are local caps, not provider capability claims.

Task-level time/tokens include helper work. Stable per-definition/proof IDs record attempts and retries=max(0,attempts-1). Cache hits, automatic replay, final verification and submission gates are separate. Interrupted uncertain counts stay null with known lower bounds. Results include report.json, results.csv and items.csv.

Parallel plans use two independently progressing language workers and separate credential aliases. Parent wall time is measured directly; overlapping intervals must not be added. Shared-host resource contention is disclosed. Original credentials remain in ignored private/api_config.json and the secondary configuration, outside agent input.

## Running and checking

On this Mac, use bash run_local.sh to select the validated Python 3.12 instead of an arbitrary Conda python3. Preflight is offline; run/resume make model API calls. A new frozen batch is required after changes. No secret is passed on the command line.

python3 verify_sessions.py from runtime runs the local offline native/session/Pi suite and writes a receipt binding source, guide and seed hashes. Tests cover true/false seed properties, tampering, native failure/replay/rollback, final isolation, raw diagnostics, item retries, text-only gates, English inputs and actual Pi tool transport. Offline providers forbid model calls. Passing these engineering checks is not a formal Euclid benchmark result.

The main accuracy denominator is the 465 registered propositions. Definitions, postulates, common notions, lemmas and corollaries retain their own costs and statuses. Primary accuracy is the machine-verification pass rate, independent of pending semantic annotations. Optional semantic_accuracy and review certificates remain separate. Definitions and other kinds also report task pass rates. New score policies never reinterpret historical frozen plans. Historical development runs and obsolete input modes must not be merged into the current comparison.
