# Lean core language guide

This guide targets the experiment's pinned Lean 4.35.0. Its teaching objectives match litex-core.md, using Lean's own proof style. Complete introductory examples are in examples/basics.lean, with local checks recorded in smoke-receipt.json. These examples do not replace the pending foundation and topic audits.

## Types and coordinates

`ℝ` is the real type; `ℝ × ℝ` is its product. If a foundation declares `Point`, inspect its actual definition and interface rather than assuming `def` or `abbrev`. Coordinates are `p.1`, `p.2`; pairs are `(a, b)`. Express carrier types and geometric nondegeneracy separately.

The current seed provides `GeoPoint := ℝ × ℝ`. `geo_point x y` constructs a point; `geo_x p` and `geo_y p` extract coordinates. `geo_vec a b` means b minus a. `geo_dot u v` is the dot product and `geo_det u v` the ordered determinant. Read seed-interface.json and foundation.seed.input_path; do not redefine these names in increments. Distances, circles and triangles are not preloaded. Preserve the frozen seed prefix in the final file.

The REPL loads approved real-number and tactic imports once at startup; increments must not repeat imports. A standalone final file still needs those imports. Importing a tactic alone does not guarantee that real types/instances are available. Do not let unresolved `ℝ` become an arbitrary implicit type. The actual foundation is foundation.json/read_library([]).

## Functions and sets

Functions commonly use `def f (x : T) : U := expression`; predicates are definitions returning `Prop`. Use `Set T` and `{x : T | condition}` for sets. Carry required premises or proof parameters for restricted domains: do not omit nonzero-denominator or nonnegative-radicand obligations.

The example `training_shift` teaches function syntax; it is not a preloaded geometry definition. Do not redeclare symbols already in the library.

## Propositions, quantifiers and premises

Use `∀`, `∃`, `→` and `∧` for universal/existential quantification, implication and conjunction. A theorem can be `theorem name (x : T) (h : P x) : Q x := by ...`. Defining a predicate does not prove that every object satisfies it.

Use `intro` for variables/premises, `exact` or `apply` for matching proofs, `have` for intermediate facts, and `constructor` for conjunctions. Changes to a definition must preserve source meaning and supply required bridges. Do not strengthen task premises just to simplify a proof.

## Expansion and algebra

`rfl` proves definitional equality; it is not a general algebra solver. `unfold`, `dsimp`, `rw` and `simp` expand or rewrite according to the actual approved environment.

Approved `ring`, `field_simp`, `linarith` and `nlinarith` generate checked proofs. Establish their side conditions first. Do not apply a tactic after the previous command has closed the goal. Do not imitate the other language's line-by-line fact format.

## Existential witnesses and paired objects

A simple witness can use `exact ⟨witness, proof⟩`. The introductory example chooses `training_shift x` and uses `rfl`; actual Euclid constructions still require legality and every geometric property.

Use the current type's actual interfaces to relate pair equality and coordinate conditions. Numerical examples do not establish claims about arbitrary points.

## References, modules and tools

Reference only approved foundation and current-run library declarations. Find symbols through the public interface index; identical names need not have identical mathematical meanings. Incremental REPL fragments do not repeat imports, whereas standalone modules must load their dependencies. A historical script rule is not a rule of Lean itself.

Iterate with check and repair the first actual unsolved obligation. After editing an accepted prefix, allow resynchronization/replay; an old REPL environment does not certify the edited file. Independently check the saved module and audit target types and axiom dependencies. `sorry` may yield only a warning: exit code zero alone is insufficient.

Save one complete declaration per tracked .lean fragment and call check(incremental). Failed commands do not adopt returned env; earlier accepted context survives. Do not overwrite accepted files with unrelated probes. Editing them invalidates dependent suffixes. read_library(["accepted_prefix"]) exports the journal source including approved imports; assemble the final file and call check(final), which preserves the writing REPL.

## Further reading

Case splits, contradiction, induction, ratios, square roots, 3D objects and module dependencies require approved topic pages and checked examples. Do not substitute historical archives for missing topics. Reading documentation and diagnostics consumes measured task time and model tokens.
