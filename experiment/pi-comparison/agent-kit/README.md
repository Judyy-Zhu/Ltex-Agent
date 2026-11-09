Current agent protocol v21: new CLI preparations default to direct candidates with local repair hints. The first request exposes submit_candidate only when the complete predecessor display and original source context fit the prompt. Generic checked operations are supplied upfront; Litex includes obtain, negated-existential contradiction and explicit tuple reconstruction. After a rejection the original native feedback is preserved and deterministic local repair hints are appended without a model call. At most one information-only turn is allowed before the next candidate. The verifier still receives the untouched seed and predecessor sources, five total attempts include API failures, and no task/verifier time limit is imposed. The previous bounded-lookup protocol is available only for a separately named new plan with --reference-protocol. Frozen historical plans must not be resumed after changing this checkout.

Current reference revision: aligned-core-v1. Both core guides now use the same 17 chapters, section IDs and teaching-example categories. Runtime reads lean-aligned-core.md or litex-aligned-core.md through the same indexed read_docs API. The original user-specified litex_short_guide.md and earlier lean-core.md are preserved as source references, not extra agent tool topics. See guides/paired-curriculum.json for coverage, source provenance and character counts. Compact jobs expose five tools and use submit_candidate for the complete task increment. Lookup-only assistant turns are bounded equally for both languages; keyword retrieval and multi-section retrieval reduce serial reads. The version notes below describe historical protocols.

Current version 15 adds SAME-task checkpoint recovery with a durable Pi session and tool-result cache. Five total attempts share code/generation/network failures. Five all-API failures pause without grading the task as a mathematical failure; explicit restart continues this task with a fresh window and full historical costs. Partial windows retain their remaining allowance. See PARALLEL.md and agent-kit/guides/task-rounds.md.

Current version 14: each source task gets five whole-task candidate rounds, including the first. Full task candidates may include helpers in one file; see guides/task-rounds.md. Task, batch and verifier time limits are absent. Time and tokens remain measured. The Litex core is the verbatim copied guides/litex_short_guide.md, embedded in the system prompt. The earlier per-fragment workflow below describes historical jobs.

# Inputs for Lean and Litex formalization agents

Each independent Pi conversation receives the same mathematical source task. The assigned formal language, its guides, foundation syntax and verifier adapter differ; source text, mathematical requirements, approved foundation intent, budgets and submission rules are shared. Merely replacing the word Lean with Litex would not establish an equivalent experiment.

The current experiment is English and text-only. All task instructions, tool descriptions, system/user prompts, guides, comments and submission metadata use English. Mathematical notation is preserved. Original source TXT includes definitions, proposition statements, original proof text and source notes. No image, initial figure, auxiliary diagram or completed-construction screenshot is provided.

## Six input groups

1. Shared role and workflow: common-system.txt, runtime-instructions.txt and feedback-common.txt. Both sides receive the same shared text.
2. Mathematical task: task.json, source-manifest.json, current source TXT and needed preceding foundation texts. Translate all source content, not just the title. Each required conclusion has a clause ID; most tasks use shared coverage/encoding clauses, while the I.1 development contract has C1-C5.
3. Approved foundation: the minimal plane seed in seeds/README.md, with GeoPoint, geo_point, geo_x, geo_y, geo_vec, geo_dot and geo_det. Frozen own-language source and a shared interface are copied per task. Distances, circles, equilateral triangles and source propositions remain agent-built. Complete transitive foundation equivalence remains pending.
4. Language guides: own-language role card and the frozen read_docs topics core, basics, roots, workflow, domains, feedback, items and seed. Paired teaching objectives cover definitions, quantifiers, witnesses, algebra, modules, diagnostics and references, without target formal proofs. Equal byte/token lengths are not claimed.
5. Accumulated own-language library: complete machine-accepted predecessors and interface metadata. Each independent run starts at its seed. Autonomous libraries can diverge; that is part of sequential library building. A fixed-predecessor comparison would be a separately labeled experiment.
6. Tools, budget and submission: the same seven tool schemas and submission.schema.json. The controller measures time/tokens/checks and records receipts; the agent cannot alter these measurements.

## Task workspace

input/ contains task.json, source-manifest.json, source TXT, foundation.json, seed-interface.json, the assigned-language seed and submission-schema.json. Published predecessors are copied to read-only input files. docs/ contains frozen guides. work/ holds current source fragments and interfaces.json. job.json binds the task, formal language, versions and input hashes. The agent uses the seven tools rather than unrestricted filesystem access.

The actual system/user prompt builder is runtime/prompts.py. Every execution saves system-prompt.txt and user-prompt.txt. Examples can be prepared offline without model calls; actual preceding-library contents depend on the run's published checkpoints.

Each task starts a fresh agent conversation. It inherits its own library, not previous chat or the other language's outputs. Historical formal answers, secrets and evaluator decisions are not mounted. Source proof text is provided intentionally: this is formalization-translation, not statement-only proof discovery.

## Proof obligations and tools

Read task/source/foundation/interface metadata and the current library. Build definitions, formal statements, representation bridges and proofs in the assigned language. Use check(incremental) on one complete definition/proof per stable item ID. Inspect the native diagnostics rather than just passed. Save interfaces.json, assemble final from accepted source, call check(final) and submit. Final declaration/axiom gates consume the same remaining budget.

The native inner schemas differ. Litex preserves Session statement_results/errors and termination controls; Lean preserves messages/sorries/env and records environment adoption. Full receipts remain available. Read the language-specific feedback guide and the shared per-item retry protocol.

## Acceptance and metrics

Automatic success is determined by the machine gates: a complete submission must pass fresh final verification, unchanged-prefix/file-hash checks, required clause mappings, declaration existence and the approved axiom/trust rules. Passing tasks publish immediately and count toward the primary score. Primary accuracy means machine-verified propositions divided by the registered proposition denominator.

Semantic review is optional metadata. Pending, absent or later negative annotations never block automatic task success, publication or the primary score. A separate semantic_accuracy metric may be reported when reviews exist; it is not the primary experiment metric. The machine score does not independently certify source fidelity.

Time and provider-reported tokens are recorded per original task, including helpers, failures, tool use, compaction and final checking. Unknown usage stays unknown. Per-item attempts/retries are separate from raw checker calls; automatic replay, cache hits, final checks and submission gates are not proof retries. Parent wall time in parallel execution is measured directly, not obtained by adding overlapping worker intervals.

Frozen plans are immutable. New guides, prompts or input policies require a new batch. Do not add staging material to an ongoing run. The introductory source examples cover language mechanisms and do not supply formal Euclid answers.
