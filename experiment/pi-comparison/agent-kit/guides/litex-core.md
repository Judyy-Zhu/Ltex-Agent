# Litex core language guide

This guide targets the observed Litex 1.1.2-beta, pinned together with its binary SHA-256. Its teaching objectives match lean-core.md, using Litex's own fact/proof syntax. Complete introductory examples are in examples/basics.lit, with local checks in smoke-receipt.json. They do not replace the pending foundation and topic audits.

## Types and coordinates

The real carrier is `R`; coordinate pairs use `cart(R,R)`. Inspect any foundation-declared `points` interface before using it. Coordinates are `p(1)`, `p(2)` and pairs `(a,b)`, not Lean's `.1`/`.2` or historical bracket syntax. Carrier membership and geometric nondegeneracy are distinct conditions.

The seed provides `GeoPoint = cart(R,R)`. `geo_point(x,y)` constructs a point; `geo_x(p)` and `geo_y(p)` extract coordinates. `geo_vec(a,b)` means b minus a. `geo_dot(u,v)` and `geo_det(u,v)` are the dot product and ordered determinant. Read seed-interface.json and foundation.seed.input_path; do not redefine these names in increments. Distances, circles and triangles are not preloaded. Preserve the frozen seed prefix in the final file.

## Functions and sets

Explicit functions commonly use `have fn f(x T) U = expression`. Predicates use `prop name(x T):` followed by conditions. Set values use `power_set(T)` and comprehensions such as `{x T: condition}`. Parameter restrictions follow a colon inside the parameter list; satisfy the domain before applying the function.

The example `training_shift` teaches function syntax; it is not a preloaded geometry definition. Do not redeclare existing library symbols.

## Propositions, quantifiers and premises

Use `forall` and `exist ... st {...}`. A named theorem starts `thm name:`; its `?` goal block lists premises, followed by `=>:` conclusions and a proof body. Invoke a custom predicate as `$name(args)`. Defining a predicate and proving an instance are separate tasks.

The checked core examples use premises on separate lines. Follow the tested syntax for multiple premises and compound logic rather than copying contradictory historical examples. Definition changes must preserve source meaning and provide bridges. Do not strengthen task premises just to simplify a proof.

## Expansion and calculation

Proof bodies can state justified equalities, facts and proof commands. Every fact must follow from established definitions, premises, previous results or supported kernel rules. Writing a conclusion is not permission to add an assumption.

Explicitly state function expansions and connect intermediate facts. Use tested interfaces such as `by def` and `by thm` where appropriate. Simple arithmetic and complex theorem applications need not use identical formats or artificially minimize references. Do not invent builtin names or copy Lean tactics. When a large step fails, inspect the first unsolved obligation instead of adding the desired fact to the premises.

## Existential witnesses and paired objects

A checked example uses `witness exist y R st {y = training_shift(x)} from training_shift(x)`. General witnesses still require all constraints; this does not replace the legality/properties of a Euclid construction.

Use actual approved interfaces for point equality, coordinate conditions and membership. Numerical examples do not prove arbitrary-point claims.

## References, modules and tools

Reference only approved foundation and current-run library declarations. Find symbols through the public interface index; identical names need not have identical meanings. Actual litex.config and export boundaries determine module dependencies. Local single-file acceptance cannot replace independent acceptance of the complete submission.

Send one complete top-level block per tracked check(incremental) fragment to the same Session. The underlying adapter can submit multiple blocks sequentially and stops at the first rejection while retaining earlier accepted blocks; the current per-item protocol forbids mixing multiple logical items in one fragment. Ordinary rejection preserves the Session. Use actual session_terminated, termination and process state to diagnose parser failures; phase alone does not determine whether a restart is needed.

Do not overwrite accepted fragments with unrelated probes. Editing invalidates dependent suffixes. The external journal stores accepted source; restarts must replay every entry successfully. read_library(["accepted_prefix"]) exports the journal source; assemble the complete file and call check(final), which uses a fresh process and preserves the writing Session. Each native Session response is retained; a historical exit summary is not a candidate response.

Final checking uses a fresh process, actual module configuration and strict policy, preserving native JSON and exit status. Strict rejection of user trust/axiom does not imply an assumption-free foundation. New abstract declarations, named foundation releases and imports must also obey the approved list. Never turn failed proofs into axioms or use historical try: wrappers.

## Further reading

Case splits, contradiction, induction, ratios, square roots, 3D objects and module dependencies require approved topic pages and checked examples. Do not substitute historical archives for missing topics. Reading documentation and diagnostics consumes measured task time and model tokens.
