# Paired language references and retrieval

The default core references are `agent-kit/guides/lean-aligned-core.md` and `agent-kit/guides/litex-aligned-core.md`, curriculum `aligned-core-v2-source-located-retrieval`. Both have the same 17 numbered chapter titles and order, plus an overview. Their IDs are `s00` for the overview and `s01`–`s17` for the corresponding chapters.

The chapters cover source fidelity, the loaded environment, names and blocks, functions, predicates, sets, universal statements, equivalence/negation, assumptions/theorem calls, expansion/algebra, witnesses, cases/contradiction, coordinates, roots/domains, diagnostics, tools/session lifetime and later-book boundaries. Each language has one teaching code block in the same chapters and the same generic mathematical example categories. Syntax, proof style and native error fields remain language specific.

The core references contain 13,838 English characters for Lean and 14,956 for Litex, including whitespace: a 8.1% size difference. These are characters, not provider tokens. The manifest `agent-kit/guides/paired-curriculum.json` records per-section sizes, provenance and legacy advice excluded by the shared experiment policy. This size check catches accidental curriculum imbalance; it is not a claim that character equality establishes mathematical fairness or equal model familiarity.

The user-specified `litex_short_guide.md` remains byte-for-byte intact, as does the earlier `lean-core.md`. Their relevant guidance was reorganized and paired. Repeated warnings and task-specific geometry illustrations were consolidated; the legacy suggestion to use temporary axioms conflicts with the experiment's shared no-placeholder policy and is excluded. The raw legacy references are retained on disk as sources, not mounted as additional agent guide topics. A new job's `core` topic always points to its frozen copy of the aligned reference.

Only the short operation card is included in the compact system prompt. The complete core reference is not automatically injected. Both operation cards use the same four headings. Further paired topics such as `logic`, `roots`, `domains`, `basics` and `feedback` remain available for their stated purposes.

## How the tool retrieves text

`read_docs` takes a JSON object. Both languages use the same implementation and selectors:

```json
{"topic":"core"}
```

In a direct job after an error, this returns the complete latest error-linked section when available. Otherwise it lists IDs, titles and character counts. To explicitly request only the index, use `section:"index"`. Error feedback already contains the relevant complete section, so rereading it is optional. Markdown headings outside code fences define the index.

```json
{"topic":"core","section":"s11"}
```

This returns the complete witness chapter. It does not return the entire guide.

```json
{"topic":"core","sections":["s06","s11"]}
```

This returns several complete chapters in one call, with their IDs and text. At most 20 IDs are accepted.

```json
{"topic":"core","query":"existential witness"}
```

This performs deterministic local lexical ranking over the selected topic, weighted toward title matches, and returns up to three complete matching sections. It calls no model, embedding API or OCR. It does not search another language's guide or an external corpus. It is a convenience lookup, not a semantic search guarantee.

```json
{"topic":"core","section":"all"}
```

This explicitly returns the full aligned guide. Use only one of `section`, `sections` or `query`; combining selectors is an error. Each result includes the full reference's SHA-256, and text results also carry their own hash where applicable. Actual tool responses and native receipts remain recorded.

## Rereading control and experimental interpretation

In the reference protocol, both languages have three information-only assistant turns before each next candidate attempt. In the default direct protocol, the first response must submit a candidate when the full context fits, and after a rejection at most one information-only turn is allowed. One turn may batch several related lookups. Once the allowance is used, the provider request exposes only `submit_candidate` and requests that tool explicitly. If a generated response ignores the required candidate phase, the extension aborts that generation and the controller charges one failed generation attempt. It retains the usage and a durable violation record. Restart recovery charges a recorded violation only once.

The default direct protocol also supplies nine corresponding checked generic procedures in each language: function expansion, existential elimination, negated existence, coordinate equality, predicate declaration, quantifier composition, sets/membership, parameter constraints and logical composition. Error-specific selection uses the first native diagnostic message rather than keywords in arbitrary source identifiers. The complete-candidate replacement rule applies to both languages. These tutorials control the supplied teaching material; they do not establish equal pretrained language familiarity.

The task still has five total attempts shared by candidate submissions, failed generations and network/API failures. Local finalization is excluded. There are no task or kernel time limits. An actual candidate or API-failure attempt starts a fresh lookup allowance; local replay and final checks are not extra attempts. This common orchestration rule changes the policy from the earlier unrestricted-read pilot, so results must use a new batch name and must not be merged as one unchanged protocol.

All guide code blocks are checked together against each pinned native kernel, followed by the independent final-file/declaration gate. Regression checks also cover matching chapter IDs, example categories, source-reference integrity, frozen retrieval, query batching, forced-candidate transitions and exactly-once violation recovery. These checks establish executable teaching examples and protocol behavior, not source-translation correctness.

Semantic contracts remain drafts in `translation/`. This reference revision does not approve them or turn kernel acceptance into faithful-translation accuracy. Historical pilot scores and artifacts remain unchanged.
