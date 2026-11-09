# Proof-layout diagnostic correction

Runtime `v25-correct-proof-layout-diagnostics` fixes two proven adapter defects. It does not change the tasks, their D001-to-D010 order, original text, model/service, credentials, seed libraries, nine initial tutorial categories, five-attempt budget, initialization-exclusion accounting, or native acceptance gates.

1. An extra colon on a simple `?` goal was previously described as a comma error when an unrelated outer parameter list contained commas. The selector now uses the located fact and reported token. A `by cases` goal/branch layout error receives the already checked cases/contradiction chapter. Actual extra commas remain distinguishable from other extra tokens.
2. `impossible` used outside its proof scope, or a missing required `impossible` clause, was previously classified as a missing library declaration or unrelated quantifier pattern. These errors now receive the existing checked contradiction-block reference. The advice never authorizes asserting an unproved target or a false premise.

No new task-specific geometric definitions, proofs or answers are supplied. The initial mathematical tutorials remain unchanged. New native regression cases use arithmetic identities and a two-case polynomial identity; they reproduce the malformed blocks and then independently verify the corrected complete files. Original historical source, native diagnostics, attempts and scores remain untouched.

The previous exploratory run did regress: startup-excluded Litex worker time rose from 133.63 to 187.74 seconds, candidate retries rose from 5 to 12, and kernel acceptance fell from 10/10 to 9/10. These fixes remove verified misleading feedback; their existence is not evidence that model performance has recovered. Different agent-generated predecessor libraries and formalization choices also prevent attributing that single-run difference solely to the guides. Source fidelity remains separate from machine acceptance.

After offline validation, a fresh first-ten diagnostic can be prepared/resumed with:

```bash
bash /Users/judy-zhu/AI4Math/auto-build/Stoicheia/litex-Stoicheia/experiment/pi-comparison/run_fast.sh --name local-proofrepair10-01 --split-final-timing
```

This command makes real model requests when run. Correction and offline validation do not call the API. Reusing the completed `local-generic10-01` name does not create an independent new trial.
