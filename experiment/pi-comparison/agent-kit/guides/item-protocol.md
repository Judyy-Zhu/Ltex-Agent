# Per-definition and per-proof tracking (shared by both languages)

Task-level time and tokens belong to the whole source task, including auxiliary definitions/proofs, failures, guide reads and context compaction. Per-item counts do not allocate model tokens or solve time to individual helpers.

The task prompt supplies primary_item_id and primary_item_kind. Use this ID for the source task's main definition/proposition, for example EUCLID.I.D001:main or EUCLID.I.P001:main. Definitions use kind definition; propositions, postulates, common notions, corollaries and lemmas use proof. Missing helper definitions/lemmas use other stable IDs such as TASK_ID:aux:distance.

First write of an incremental fragment:

```json
{"path":"main.lean","content":"complete declaration and proof body","item_id":"EUCLID.I.P001:main","item_kind":"proof"}
```

Litex uses the same schema and a .lit suffix. item_kind is definition or proof. Lean namespace/end/section/open/universe/variable context commands may use scope, excluded from definition/proof totals. A fragment must contain exactly one complete top-level logical definition/theorem/goal and its entire body; keep its proof steps together. Record fields and automatically generated declarations belong to the same logical definition. Lean scope wrappers may surround the single declaration. The controller applies a conservative structure check; the native verifier decides syntax and proof validity.

Call check({path,mode:"incremental"}). Keep the same ID when repairing the same logical item. Later writes to the same path may omit already registered metadata. Syntax repairs, justified premise corrections, route changes and declaration renames do not reset the ID. A failed fragment moved to another path retains its ID and history; do not recheck its old path. Accepted items cannot be duplicated at another path. A path cannot switch IDs. Distinct mathematical helpers need distinct IDs. Record source/declaration correspondence in interfaces.json; stable IDs do not themselves establish semantic correctness.

Counting rules:

- attempt_count counts submitted new candidate incremental checks, including failures, candidates sent before timeout, and source candidates rejected by controller structure/trust rules. Writing a file is not an attempt.
- Tool rejection of parameters, paths, deadlines or checker budgets before checking starts is not a candidate attempt. A started candidate rejected for source structure/trust violations is a failed candidate.
- retry_count = max(0, attempt_count - 1). The first candidate is not a retry. Editing and rechecking a previously accepted item is a subsequent attempt. Resending an unchanged failing candidate also counts.
- An unchanged accepted-source cache hit sends no new candidate; cached_checks is separate and does not add attempts/retries.
- Session initialization, foundation loading and automatic replay are separate. An environment failure before candidate dispatch is preparation_failures. Agent-requested rechecks of invalidated suffix items count when they submit new candidates; automatic replay does not.
- Final module checks and submission declaration/axiom gates count as checker calls, not item retries. Do not use check_calls - 1 as a retry count.
- A hard interruption leaving a start event without a finish event makes exact counts null. Preserve known_attempt_count/known_retry_count lower bounds and pending_checks; never replace unknowns with zero.

check.item_tracking reports item counts, source versions, failures, cached checks, preparation failures and acceptance status. read_library(["retry_stats"]) returns main/helper and definition/proof totals. check_seconds is checker-call time, possibly including startup/replay, not item-level model reasoning or solve time.

Write interfaces.json, then assemble a separate final.lean/final.lit with empty content and base="accepted". Call final, then submit. A complete task's final file must exactly assemble unchanged accepted fragments and include the accepted main item. Final cannot add unchecked definitions/proofs. base="library" only concatenates source; it does not waive tracking. Reserve budget for final and the submission gate.

An item attempt/retry is an auditable tool-level event, not the model's internal reasoning or an unsent draft.
