# Generic language operation and diagnostic revision

Generic tutorial revision: `v24-generic-language-operations-and-located-repair`. The later `v25-correct-proof-layout-diagnostics` correction keeps those tutorials fixed; see [PROOF_LAYOUT_FIX.md](PROOF_LAYOUT_FIX.md).

The paired tutorials now cover nine generic categories: function expansion, existential extraction, negated existence, coordinate equality, predicate declaration, quantifier composition, sets/membership, parameter constraints, and logical composition. Corresponding examples have the same mathematical meaning. They are references in the initial prompt, not declarations preloaded into the technical seed. The new examples use real-number singleton sets, reciprocal on nonzero inputs and a simple logical conjunction/disjunction; they do not provide Euclid translations or proof answers.

The short operation cards teach each language's actual comprehension/membership syntax and the distinction between sets, elements, functions and proofs. They explain restricted function arguments without copying unsupported function-signature syntax into Litex predicate declarations. Comment placement follows each language's grammar. Original source material, approved technical seeds, published-library loading, five total attempts, no time limits and the optional semantic-review policy are unchanged.

## Diagnostics

The selector still starts with the first non-replay native error. It now prioritizes the actual mapped source line over unrelated keywords elsewhere in a declaration. Litex frame line maps are used to recover saved-file line numbers. Lean failure frames retain the actual source line identified by the native message position. Missing positions are explicitly marked unlocated. Strings and comments are masked for lexical classification while all original source and native responses remain unchanged.

Generic categories distinguish malformed comprehensions, bare membership syntax, unsupported logical/quantifier nesting, restricted-operation well-definedness, argument-type problems and declaration-comment layout. They do not rewrite candidate code, weaken mathematical targets or claim that a hint proves the target. Ambiguous errors retain general advice and their full native evidence.

Each applicable repair attaches a checked generic procedure and one complete relevant section from that job's frozen guide, identified by its hash. This local selection makes zero model calls. For direct jobs, a bare `read_docs(topic)` returns that latest error-linked section when available, avoiding an index-only round trip. `section="index"` explicitly returns the index. Explicit queries, individual/batched sections and intact full-reference reads retain their meanings. The same retrieval policy applies to both languages.

## Next diagnostic run

```bash
bash /Users/judy-zhu/AI4Math/auto-build/Stoicheia/litex-Stoicheia/experiment/pi-comparison/run_fast.sh --name local-generic10-01 --split-final-timing
```

This prepares or resumes a NEW batch using the existing DeepSeek service/model and separate credentials, the same first ten original tasks, and measured initialization exclusion for both independent verification stages. No former generated libraries or candidate answers are reused. Startup-excluded wall time still includes model/API time, retries and actual candidate/final verification. It does not attempt to subtract unmeasured network/queue time.

The earlier first-ten runs informed interface debugging and remain development diagnostics. Freeze this revision before an untouched evaluation; re-running those development tasks cannot by itself establish held-out language generalization or a causal speed advantage. Native acceptance and faithful-translation accuracy remain separate metrics. Offline tests and replayed diagnostics do not replace a new real-model measurement.
