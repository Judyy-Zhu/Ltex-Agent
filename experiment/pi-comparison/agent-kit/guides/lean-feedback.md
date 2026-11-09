# Lean diagnostics and repair

The first response block is common controller metadata; the second is native diagnostics. REPL JSON and CLI text are not converted into Litex errors. Fields can be absent. Read passed/controller_error and then all native messages.

## Common controller envelope

receipt_id identifies this check; mode is incremental/final; entry names the file; source_hashes bind every work file at checking time. Any file edit invalidates the old final receipt. scope distinguishes the persistent session from a fresh complete-file process. passed combines verifier, trust-policy and budget checks; it is not source-fidelity acceptance. seconds measures this check.

controller_error reports budget, source-protocol, foundation, timeout, process/transport or invalidated-prefix problems; resolve it first. process_status.exit_code can be null for REPL commands; timed_out records timeout and process_alive/session_id describe the session. session.accepted_blocks, starts, restarts, session_alive and session_id/session_pid describe the accepted prefix and recovery; lean_environment is the adopted environment. replayed_blocks counts automatic replay; invalidated_blocks identifies suffixes invalidated by edits. feedback_truncated=false means the adapter did not trim the output. Retrieve full_receipt with read_library. Read read_docs(items) for item_tracking.

## Incremental: complete Lean REPL JSON

The second block contains frames, session and note. Frames contain received responses to new fragments; replay is logged separately. Empty frames can mean caching, preparation failure, or a candidate whose response timed out. Consult passed, controller_error and item_tracking; do not infer zero attempts from an empty list.

Each frame has path/block_index (one complete REPL cmd per Lean fragment, normally block_index=0), source_block_start_line (normally 1), passed, and the complete native object. environment_transition.before/after/adopted_returned_env records environment selection. Only adopted_returned_env=true means the returned environment was adopted.

Common native fields:

- messages[] contains all diagnostics. REPL severity values include error, warning, info and trace. data is the message body, possibly including local context and an unsolved goal after ⊢. pos/endPos locate the range within the fragment: lines start at 1, columns at 0; endPos may be absent. Start with the earliest error; later errors may cascade from it.
- env is the native environment index. The REPL can return env even on errors. Its presence alone is not success. The controller checks error messages, unsolved obligations, placeholders and trust policy; failed environments are not adopted.
- sorries describes unresolved goals/placeholders, potentially including goal, positions and proofState. A nonempty list is rejected. Do not fill a gap with sorry merely to silence diagnostics.
- error is a native request/protocol error, potentially without messages. Read it and check the request context; report persistent environment failures.
- Other fields such as tactics/proofStates appear only for applicable requests. Read their native values and do not assume they are always present.

For unsolved goals, local declarations such as x : T and ⊢ G describe the actual remaining goal G; they are not lost protocol fields. Supply a proof preserving every source condition/quantifier. For unknown identifier/constant, inspect the seed, own library index, namespaces and whether predecessors actually passed. For type mismatch, compare expected type/has type and repair argument order, coercions or representation bridges. For tactic failed, inspect the actual target and use approved tactics or smaller lemmas; do not introduce unchecked axioms.

Ordinary failure preserves the before environment. Repair the complete fragment under its original item_id. Read warnings even after success; warnings about declarations using unproved placeholders are rejected. Editing accepted source invalidates the dependent suffix: recheck the changed predecessor first. A replay failure is a recovery/foundation issue to resolve before continuing.

## Final checking and submission

Final checking runs lake env lean <complete-file> in a fresh process. lean-cli-text retains stdout/stderr unchanged. Typical file:line:column: error: locations follow CLI display conventions (one-based lines and columns). The final file includes the seed and predecessor library, so incremental line numbers cannot be applied directly; inspect the saved complete file. Check exit_code, controller_error and placeholder rejection, not the absence of a messages array. Final checking does not close or replace the writing REPL.

The submission gate separately checks declaration existence and axiom dependencies. After failure, read read_library(["submission_gate"]) for declarations, dependencies and stdout/stderr/error. Repair interfaces/source and run final again. Tool isError=true means a parameter, budget or protocol failure; details.error explains it. It is not a successful Lean proof, nor evidence that the mathematical statement is false.

Whole-task jobs expose task_rounds: limit=5, used, remaining, exhausted and a round journal. All helper declarations share this counter. A whole candidate check uses one round, final checks and publication do not. remaining_budget time/check limits are null when unlimited. After the fifth failed round no further model request or sixth candidate is permitted. Native fields and complete diagnostics above remain unchanged.

Checkpoint jobs use five TOTAL attempts shared by code candidates and network/API failures. task_rounds.kind distinguishes candidate/generation/transport. Five all-transport failures pause the SAME task; a later explicit restart opens a new window and retains history. Earlier network failures do not prevent a later kernel-checked submission from passing. used/remaining refer to the current window, while total_used/history are cumulative. Finalization after an unchanged whole candidate passes is outside the candidate allowance.


Automatic finalization jobs: check metadata includes auto_finalization and task_completed. passed reports the native check described by scope; task_completed=true additionally requires the controller's independent final file check and declaration/axiom gate. auto_finalization.completed=false contains final_check and gate diagnostics; read both and repair real code failures. The controller generates interfaces and unreviewed task-level source associations; do not supply encoding labels or repeat model calls after task_completed=true. The controller counts this entire candidate/check/feedback sequence once, including its local final validation. Interrupted local finalization is recovered without consuming a new model/candidate attempt.


Compact protocol: submit_candidate({code}) saves and checks one complete increment in one operation. Its native feedback fields and full receipt remain intact. The controller owns final checking and publication. Diagnostic suggestions can mention macros or imports that are outside the approved experiment source policy. Repair with the loaded foundation and permitted proof tactics; a warning is not permission to introduce metaprogramming or a new import.


## Local source-location repair references

`repair` is controller-added metadata; the original native response remains intact. `matched_rule` names a general syntax/domain rule, not a semantic judgment. `diagnostic.source_context` identifies the actual error line when a native position can be mapped: `path` and `source_line` refer to the saved candidate, `line` is native/frame-local, and `column` retains the native convention. Litex columns are native one-based positions; Lean columns retain the native zero-based convention. `confidence=unlocated` means no exact line was inferred. Preview text may be bounded; the complete native diagnostic and receipt remain available.

`reference_patterns` contains checked generic teaching examples, not definitions already loaded or target-task solutions. `reference_sections` contains a complete relevant section from this job's frozen guide and its reference hash. Use these before another lookup. In direct jobs, `read_docs(topic)` returns the latest error-linked section when available; `section="index"` explicitly requests the section index. Queries, selected section IDs and `section="all"` keep their existing meanings. The hint selector calls no model, modifies no candidate and never replaces native acceptance.
