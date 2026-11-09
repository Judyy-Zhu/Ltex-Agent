# Lean operation card

## Declarations and functions
Place `/-- ... -/` before the declaration and its modifiers; use `--` comments between declarations.

Use the seed's `GeoPoint`, `geo_point`, `geo_x`, `geo_y`, `geo_vec`, `geo_dot` and `geo_det` directly. The imports and predecessor declarations are already loaded. Write only new declarations. Use `def`, `abbrev`, `structure` and `theorem` as appropriate; explicit domains help diagnostics. Use fresh names and consult the published symbol index before introducing a name.

```lean
def training_twice (x : ℝ) : ℝ := x + x
def training_positive (x : ℝ) : Prop := 0 < x
theorem training_fold (x : ℝ) (hx : 0 < x) : training_positive x := hx
theorem training_double (x : ℝ) : training_twice x = 2 * x := by
  unfold training_twice
  ring
```

## Domains and well-definedness
Use `{x : T | condition}` for set comprehension and `x ∈ S` for membership, with `S : Set T`. A set, element, function and proof have different types. See the direct-protocol `sets_membership` example. Set equality requires both inclusions.

A restricted function may take a proof `(hx : x ≠ 0)`; supply it at each application. Read the signature and preserve source hypotheses when repairing types. Direct-protocol `parameter_constraints` and `logical_composition` examples show supported forms.

`GeoPoint` is `ℝ × ℝ`; use `p.1`, `p.2` and `Prod.ext` for coordinate equality. Predicates use `Prop`; sets use `Set T`. State nonzero, positivity and membership hypotheses when mathematically needed. `Real.sqrt` is noncomputable: a new real-valued definition depending on it generally needs `noncomputable def`. This marks computational status and is not a proof placeholder.

```lean
noncomputable def training_root (x : ℝ) : ℝ := Real.sqrt x
theorem training_root_nonnegative (x : ℝ) : 0 ≤ training_root x := by
  exact Real.sqrt_nonneg x
```

## Quantifiers and proof structure
For a quantified definition with several scopes, named predicates can expose the inner conditions; see the supplied `quantifier_composition` procedure. Keep all free parameters explicit. Do not move an existential across a universal or change witness dependencies. `def name (parameters) : Prop := body` defines a predicate; a definition alone does not prove that it is inhabited or holds universally.

Use explicit theorem parameters or `∀`, `∃`, `∧`, `∨` and `→`. Standard tools include `intro`, `rcases`, `constructor`, `exact`, `apply`, `rw`, `simp`, `ring`, `linarith`, `norm_num`, `positivity` and `field_simp`. Unfold the intended definition before a tactic that operates on its body. A completed proof should stop: additional tactics can produce “No goals to be solved”. Check function argument explicitness rather than repeatedly applying a set-membership proof as a function.

## Diagnostics and references
Native REPL `messages` contain `severity`, `data`, `pos` and `endPos`; `sorries` and errors prevent acceptance. A returned `env` alone is insufficient; `environment_transition.adopted_returned_env` records commitment. The controller adopts no failed environment. `check` feedback contains unchanged native messages and the full receipt reference. `read_docs({topic:"core",section:"index"})` lists the aligned reference sections. Error feedback already attaches a relevant complete section; a bare core lookup reuses that selection. Explicit queries and section IDs remain available. `read_docs({topic:"logic",section:"all"})` contains checked generic proof structures. Use exact published symbols with `read_library`; do not guess predecessor signatures or redeclare them.
