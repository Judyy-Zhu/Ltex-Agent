# Litex diagnostics and repair

Native Litex fields are preserved rather than converted into Lean diagnostics. Optional fields can be absent. The first block is common controller metadata; the next is native JSON. full_receipt points to the complete original record.

## Common controller envelope

receipt_id identifies the check; mode is incremental/final; entry names the checked file; source_hashes bind all work files at checking time. Any edit invalidates an old final receipt. scope distinguishes the persistent incremental session from a fresh complete-file process. passed combines verifier, trust-policy and budget results. seconds measures this check.

controller_error reports budget, source-protocol, foundation, timeout, process/transport or invalidated-prefix problems; resolve it first. process_status.exit_code may be null in Session mode; timed_out records timeout and process_alive/session_id describe the session. session_terminated/termination are native Litex controls. session.accepted_blocks, starts, restarts, session_alive and session_id/session_pid describe the accepted prefix/recovery; replayed_blocks counts automatic replay and invalidated_blocks lists suffixes invalidated by edits. feedback_truncated=false only means the adapter did not trim output. Retrieve full_receipt with read_library; read read_docs(items) for item_tracking.

## Incremental: complete Session JSON

The second block contains frames, session and note. Each frame corresponds to a newly submitted top-level block for which a response arrived. Automatic replay remains in the raw journal; unchanged accepted blocks do not appear as new responses. Empty frames may also mean timeout before a response, not necessarily zero dispatched candidates.

A frame contains path, zero-based file block_index, passed and the complete native object. source_block_start_line is a one-based file line. submitted_source is the exact transmitted frame after removing blank/comment lines. frame_line_to_block_line maps frame lines back to original block lines: array index 0 corresponds to frame line 1. File line = block start line + block-relative line - 1. Native statement_index is not this line number.

Native turn boundaries matter: a first physical line not ending in a colon is evaluated immediately. If an explicit function is incorrectly split after `=`, the adapter sends only that first turn, returns its native parse error, and does not enqueue the remaining body lines. Thus submitted_source may be only the rejected header; the complete candidate remains saved in work. Repair the function body onto the same physical line. If a first turn succeeds but additional unchecked turns remain inside the same source block, controller_error reports the framing problem and the partial context is discarded. The controller never treats that partial success as acceptance of the complete source block.

Principal native fields:

- kind is the message type; normal evaluation expects run. target is the evaluation target, normally repl in a Session. path, detail and language describe native request context.
- run_result reports success/failure or another native result. Success alone is insufficient: errors and termination must be absent, statement_results must be accepted, and the controller must confirm passed.
- statement_results[] contains statement and statement_result. Successful records can include proof_method (rule/method), stores (stored facts), infers (inferred facts) and other complete evidence. Inspect what the kernel actually accepted; these traces do not replace source-fidelity review.
- errors[] contains zero-based statement_index within this native turn, statement, phase, category, message and obligation. obligation is the actual unsatisfied proof obligation. Other native location/detail fields may appear; do not trim them or translate them into another verifier's schema.
- session_terminated says whether the kernel terminated the session; termination contains its reason/details, normally null. If true/non-null, do not assume the old process context survives. The tool recovers from the acceptance journal; failed replay blocks continuation.

Additional error fields:

source_location.path/line/optional column locates native source. In Session mode compare submitted_source and use its line map; do not invent missing locations. failed_statement is an actual nested failure and can differ from the top-level statement. goal is an inner goal; expression is the problematic expression; cause explains the reason. index/step_index/branch_index/then_index are local step/branch indexes, not file lines. expected/actual compare required and obtained values. returned_conclusions lists actual returned conclusions to check whether a call/proof covers its obligations. These fields summarize the actual failure path; absence of a field does not establish absence of an obligation.

For phase=parse, repair syntax first. Domain/well-definedness failures require checked membership, nonzero denominators, valid arguments or other prerequisites. For proof_body and nested failures, repair the failed_statement/obligation at the reported step.

An actual failure shape:

```json
{"kind":"run","run_result":"failure","target":"repl","path":null,"detail":"normal","language":"en","statement_results":[{"statement_result":"rejected","statement":"(2 + 2) = 5"}],"errors":[{"statement_index":0,"statement":"(2 + 2) = 5","phase":"search_proof","message":"Could not prove the goal.","category":"proof_search","obligation":"(2 + 2) = 5"}],"session_terminated":false,"termination":null}
```

search_proof/proof_search means the kernel could not prove the obligation, not that the source statement is false. Check the encoding, then supply verified intermediate steps, domain facts, proved premises, witnesses and their properties. Never delete source conditions/conclusions just to obtain acceptance. For syntax/name/type problems, repair keywords, indentation, parameter domains, names and signatures. Ordinary rejection keeps earlier accepted blocks; the current rejected block is not committed. Repair its original item ID and recheck. Rebuild invalidated_blocks after editing predecessors.

## Final checking and submission

Final checking uses a fresh -strict -lang en -f <file> process. Its display retains complete run_result, statement_results and errors, matching the historical formatter. Other native controls remain in receipt.stdout/process_status; also inspect exit_code, timed_out and controller_error. Invalid JSON is labeled litex-invalid-json: inspect stdout/stderr/process status instead of treating it as an ordinary proof failure. Final statement_index is not a source line number.

After a submission-gate error, read read_library(["submission_gate"]) for declaration existence, extra trust/assumptions, symbol checks and native diagnostics. The verifier does not prove a missing declaration for you. Repair source/interfaces and run final again. Tool isError=true is a tool/protocol failure with explanation in details.error; repair parameters/environment instead of treating it as kernel acceptance.

Whole-task jobs expose task_rounds: limit=5, used, remaining, exhausted and a round journal. All helper declarations share this counter. A whole candidate check uses one round, final checks and publication do not. remaining_budget time/check limits are null when unlimited. After the fifth failed round no further model request or sixth candidate is permitted. Native fields and complete diagnostics above remain unchanged.

Checkpoint jobs use five TOTAL attempts shared by code candidates and network/API failures. task_rounds.kind distinguishes candidate/generation/transport. Five all-transport failures pause the SAME task; a later explicit restart opens a new window and retains history. Earlier network failures do not prevent a later kernel-checked submission from passing. used/remaining refer to the current window, while total_used/history are cumulative. Finalization after an unchanged whole candidate passes is outside the candidate allowance.


Automatic finalization jobs: check metadata includes auto_finalization and task_completed. passed reports the native check described by scope; task_completed=true additionally requires the controller's independent final file check and declaration/axiom gate. auto_finalization.completed=false contains final_check and gate diagnostics; read both and repair real code failures. The controller generates interfaces and unreviewed task-level source associations; do not supply encoding labels or repeat model calls after task_completed=true. The controller counts this entire candidate/check/feedback sequence once, including its local final validation. Interrupted local finalization is recovered without consuming a new model/candidate attempt.


Compact protocol: submit_candidate({code}) saves and checks one complete increment in one operation. Its native feedback fields and full receipt remain intact. The controller owns final checking and publication. Internal proof_method/rule_name provenance is not a list of callable source-language tactics. Use only documented by forms and actual published theorem names; do not turn an internal rule label such as contain_exact_1 into a by command.


## Local source-location repair references

`repair` is controller-added metadata; the original native response remains intact. `matched_rule` names a general syntax/domain rule, not a semantic judgment. `diagnostic.source_context` identifies the actual error line when a native position can be mapped: `path` and `source_line` refer to the saved candidate, `line` is native/frame-local, and `column` retains the native convention. Litex columns are native one-based positions; Lean columns retain the native zero-based convention. `confidence=unlocated` means no exact line was inferred. Preview text may be bounded; the complete native diagnostic and receipt remain available.

`reference_patterns` contains checked generic teaching examples, not definitions already loaded or target-task solutions. `reference_sections` contains a complete relevant section from this job's frozen guide and its reference hash. Use these before another lookup. In direct jobs, `read_docs(topic)` returns the latest error-linked section when available; `section="index"` explicitly requests the section index. Queries, selected section IDs and `section="all"` keep their existing meanings. The hint selector calls no model, modifies no candidate and never replaces native acceptance.
