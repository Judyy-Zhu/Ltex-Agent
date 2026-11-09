# Independent source-fidelity evaluation

The selected criterion is **faithful translation**: preserve complete mathematical meaning and the source proof route. Identify and justify any additional arguments needed by the chosen modern model. A different correct proof can preserve the goal while failing this stricter source-route criterion.

This directory is an offline evaluation layer. It does not call an API, run an agent, change prompts, modify historical batches, or replace machine acceptance. Its Python code checks artifact identity, review completeness and evidence binding; it does **not** decide mathematical semantics.

## Two separate outcomes

1. **Kernel acceptance** retains the experiment's existing native-check, independent final-file check and submission-gate result. Pending semantic review never blocks this outcome or publication.
2. **Faithful translation** needs an independent assessment of the exact original text, an approved common mathematical interpretation, and the saved formal module. Kernel acceptance, declaration names and controller-generated clause mappings cannot establish this outcome.

Meaning preservation and source proof route are recorded separately. For example, an alternative proof may pass meaning preservation and fail faithful translation. Definitions without a source proof have no invented proof-route requirement.

## Current scope and limitations

`contracts/` contains **11 drafts**, Book I definitions 1–10 and proposition I.1, not the full 644-task collection. Their quotes and hashes bind actual text that both solvers received. Their mathematical interpretations remain open and have not been approved as ground truth. In particular, D8's use of “lines” must be reconciled with D9's separate restriction to straight lines before fixing the common angle representation.

I.1 preserves a hash-bound reference to the existing development target, including H1, C1–C5 and the construction requirements. The new draft also separates original proof steps from the editorial notes about circle intersection and shared line segments. The existing development target is not automatically an approved semantic specification.

An independent reviewer must inspect actual definitions and proof bodies, including prior-library meanings and dependencies. Exact excerpts provide traceability; an excerpt or a reviewer identity alone does not prove correctness or independence. A model judge can make errors and should be calibrated against expert review. Reading unknown syntax must lead to `uncertain`, not a guessed pass.

## Prospective comparison procedure

1. Prepare a language-neutral contract for each task from its original source. Record objects, quantifiers, conditions, conclusions and the required source steps. Resolve model choices once for both languages; do not derive them from one solver's answer.
2. Review the interpretation, resolve each `interpretation_decisions` entry and record the reviewer and rationale in `approval`. Only then set `status` to `approved` and freeze the contract. Contract creation/approval is an offline benchmark-preparation cost, separate from solver performance.
3. In a future experiment revision, give both agents the same original text, common approved target, allowed model assumptions and source-route requirement, with their own language guides/tools. Do not supply either formal answer. **This directory does not yet wire these drafts into the runtime.**
4. Preserve native diagnostics and the existing kernel acceptance path. Save exact final artifacts even when semantic review is pending.
5. Assess each saved module independently against the source and the frozen contract. Do not expose the other language's output, desired speed ranking or generator confidence to the reviewer. Identify dependencies and model refinements; fill every source-clause and proof-step judgment with reasons and actual code evidence.
6. Report kernel acceptance, independently assessed faithful translation, review coverage, solver time/tokens/retries and kernel timings separately. Review time/tokens have their own fields and must not be added to solver measurements without a clearly labeled end-to-end measure.

Use the same review policy and quality checks for Lean and Litex. Once assessments are complete, compare solver time/tokens on the same successfully translated task pairs as well as on all registered tasks, retaining failures, network costs and incomplete token usage. Shortening a language's obligations to obtain a speed advantage changes the task.

## Offline commands

Run from the `pi-comparison` directory:

```bash
python3 translation/review.py validate-contracts
python3 -m unittest discover -s translation -p 'test_review.py' -v
python3 translation/review.py make \
  --batch batches/local-compact10-01 \
  --output translation/reviews/my-new-diagnostic
python3 translation/review.py summarize \
  --reviews translation/reviews/my-new-diagnostic
```

`make` requires a new output directory and a stopped batch. It validates frozen job/input hashes, the final native receipt, the gate and work-file hashes. Each task-language packet includes original text and context, the common contract, the actual solver target/foundation, the complete formal module, current candidate, native declaration metadata and machine evidence. The packet contains no other-language answer. `judge-system.txt` supplies the same review instruction to either language's evaluator.

The accompanying `.review.json` starts **unreviewed**. A human or an explicitly configured independent evaluator may fill it later; no evaluator is launched by these commands. Pass/fail judgments require reasons and exact formal excerpts. Proof-route judgments also require evidence. Model refinements need their introduced fact, source gap/model change, justification and code evidence. Route-only assessments still require an identified reviewer.

Reviews are bound to packet, contract and formal-source hashes. Regenerate packets in a new directory after changing a contract; an old review must not silently apply to a new target. Approval requires resolving model decisions, not merely changing the status string.

`summarize` rejects missing clause judgments, mismatched hashes and invented excerpts. Draft-based pass/fail assessments remain provisional and cannot produce a final faithful-translation rate. Unreviewed and uncertain cases remain unknown. The report gives coverage and possible rate bounds; it does not fabricate a final accuracy. A finished kernel failure cannot count as an end-to-end successful translation; an interrupted task stays unknown. Missing-contract slots are listed, and subset results are not full-book results.

The saved diagnostic under `reviews/local-compact10-01-diagnostic-v1/` is retrospective. These contracts were not the pilot's original acceptance criteria. Historical solver scores and timing/token files remain unchanged.
