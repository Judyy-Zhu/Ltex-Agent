Lean reference guide. Paired curriculum: aligned-core-v1. Sections s01 through s17 have the same titles, order, teaching objectives and example categories as the Litex reference. Examples teach language mechanisms, not answers to Euclid tasks. The system operation card is the short starting reference; this document is queried when a specific rule is missing.

## 01. Scope and source fidelity

Translate the original source's mathematical meaning, including object domains, quantified variables, conditions, witnesses and conclusions. A well-typed definition can still describe the wrong object. Naming a predicate after a source concept does not establish correspondence. Do not replace a geometric condition with an unrelated constant or a tautology.

Preserve original proof steps when a source proof is supplied. Separately identify additional arguments needed by the coordinate model. An alternative proof may establish the same theorem without translating the original route. Definitions without an asserted theorem need checked definitions, not an invented characterization or existence project. Kernel acceptance and source fidelity remain separate outcomes.

## 02. Environment and library reuse

The pinned Lean REPL loads the approved imports and technical seed before your candidate. `GeoPoint` is the real-coordinate carrier `ℝ × ℝ`. The seed exports `geo_point`, `geo_x`, `geo_y`, `geo_vec`, `geo_dot` and `geo_det`. It does not preload Euclid's distances, angles, circles or source propositions. Read the supplied interface for signatures rather than inferring them from names.

The complete published own-language predecessor library is loaded too. Use its symbol index and `read_library` to find actual signatures and bodies. An earlier source task that failed is not available as a theorem. Write only the new increment: do not repeat imports, seed definitions or accepted predecessors. The controller assembles the standalone final file.

## 03. Names, parameters and block structure

Use fresh declaration names and explicit parameter types. Lean identifiers are case sensitive. A name's capitalization does not determine its type; bind it explicitly. A local declaration can shadow another name and change elaboration, so prefer distinct local names. Parameters introduced in a theorem are already available in its proof; do not accidentally introduce a second independent copy.

Indent tactic blocks consistently after `:= by`. Function application is normally space separated, as in `geo_x p`; tuples use `(x, y)`. A function expecting an explicit proof argument must receive one. Comments use `--` or `/- ... -/`; comments carry no mathematical evidence. Resolve an unknown identifier against the actual library before creating a competing definition.

## 04. Objects and explicit functions

Use `def` for a function or specified object, `abbrev` when intentional reducibility is useful, and `structure` for records. Every field and parameter must carry the intended type. A record carrying raw data alone does not enforce a separately declared geometric predicate; add the relevant proof field or bind the predicate in the exported concept when required by the source.

```lean
def guide_shift (x : ℝ) : ℝ := x + 2
```

This is a total arithmetic teaching function. It is not a supplied geometric construction. For a restricted operation, include the actual mathematical domain and justify its use. Choose a convenient representation only when it preserves the source meaning and necessary representation bridges.

## 05. Predicates and conjunctions

A predicate is a definition returning `Prop`. Its parameters specify which objects it describes. A conjunction requires both constituent conditions; an unrelated predicate elsewhere in the file does not constrain this definition. Defining a predicate is different from proving that an object satisfies it.

```lean
def guide_fixed (x : ℝ) : Prop := x = 7
def guide_between (x : ℝ) : Prop := 0 ≤ x ∧ x ≤ 1
```

Use `guide_fixed x` for application. For a conjunction proof, use `constructor` or `⟨h₁, h₂⟩`; extract components with `.1`, `.2` or `rcases`. Keep the parameter roles consistent when a relation is asymmetric. Do not omit nondegeneracy merely because a formula is syntactically total.

## 06. Sets and membership

Use `Set T` for sets of objects of type `T`. Set comprehension is `{x : T | P x}`, and membership is `x ∈ S`. A point, a set of points and a proof of membership are different types. Defining a set does not prove it is inhabited, nor establish every geometric property suggested by its name.

```lean
def guide_level (t : ℝ) : Set ℝ := {x : ℝ | x = t}
```

When using membership, inspect the actual set definition before unfolding or applying it. A membership proof may reduce to a condition, but it is not always a function to call on more arguments. Do not replace equality of sets with one inclusion; both directions must be justified when needed.

## 07. Universal statements and hypotheses

Theorem parameters `(x : T)` introduce arbitrary objects. Proof parameters `(h : P x)` introduce assumptions, and the theorem's final type is its conclusion. `∀ x : T, P x`, `P → Q`, `∃ x, P x`, `P ∧ Q` and `P ∨ Q` have distinct logical roles. Preserve the original quantifier order and witness dependencies.

```lean
theorem guide_guard (x : ℝ) (h : guide_between x) : 0 ≤ x := by
  exact h.1
```

For an implication or universal goal use `intro`; do not introduce extra premises absent from the source. Assumptions apply to the current theorem's scope. A construction proved for one fixed numeral does not establish a universally quantified source claim.

## 08. Equivalence and negation

`P ↔ Q` requires both directions. Use `constructor` and prove each implication, or provide two explicitly named directional theorems. `¬ P` means `P → False`. Keep negation scope visible: negating a universal, an existential, a conjunction and an atomic equation are different claims. Do not use a one-way implication as a characterization.

```lean
theorem guide_forward (x : ℝ) (h : guide_fixed x) : x = 7 := by
  exact h
theorem guide_backward (x : ℝ) (h : x = 7) : guide_fixed x := by
  exact h
```

These two teaching proofs share the same domain and no additional side assumptions. For actual source equivalences, check whether each side's expressions are defined independently; a guard present in only one direction may be insufficient for the other direction.

## 09. Using assumptions and named theorems

Use `exact` when a term proves the goal; use `apply` when a theorem's conclusion matches and its premises remain to be proved. `have h : P := ...` records a proved intermediate fact. A local hypothesis is already evidence; do not attempt to prove the same hypothesis by assuming the desired conclusion. A named function and a theorem about that function have different roles.

```lean
theorem guide_call (x : ℝ) (h : guide_fixed x) : x = 7 := by
  exact guide_forward x h
```

Check the actual signature for explicit and implicit arguments. Do not guess a theorem based on its name. Tactics are proof constructors checked by Lean; unsuccessful elaboration or an unsolved goal does not create a new library fact.

## 10. Definition expansion and equation chains

`rfl` proves definitional equality. `unfold`, `dsimp` and `simp [name]` expose definitions; `rw [h]` rewrites using an equality. These steps differ from polynomial normalization. A proof should first expose the relevant expression and then justify its algebra. Avoid using `rfl` as a general arithmetic solver.

```lean
theorem guide_expand (x : ℝ) : guide_shift x - 2 = x := by
  unfold guide_shift
  ring
```

For a longer chain, use `calc` with a proof for each equality. Do not mix equality with an inequality as if they were the same relation. Splitting a difficult derivation into small established facts makes the first unsolved obligation easier to identify without weakening the final conclusion.

## 11. Existential witnesses and their properties

An existential proof must supply a witness and all its required properties. Use `refine ⟨w, ...⟩` or `exact ⟨w, h⟩`. Eliminate an existing existential with `rcases h with ⟨w, hw⟩`. A witness may depend on earlier universal parameters, but not on variables introduced only later.

```lean
theorem guide_witness (x : ℝ) : ∃ y : ℝ, y = x + 1 ∧ y - x = 1 := by
  refine ⟨x + 1, rfl, ?_⟩
  ring
```

The witness is checked against both conditions. Existence does not imply uniqueness. Choosing an arbitrary value or using classical choice still needs the corresponding existence evidence and every source property; choice does not justify a missing geometric construction.

## 12. Cases and contradiction

Use `rcases` to split a known disjunction or `by_cases h : P` to consider a proposition and its negation. Prove the same target in every branch. `by_contra h` introduces the negated goal and requires a contradiction. Scope and the exact negation matter.

```lean
theorem guide_branch (x : ℝ) (h : x = 0 ∨ x = 1) : x * (x - 1) = 0 := by
  rcases h with h | h <;> simp [h]
theorem guide_square_nonnegative (x : ℝ) : 0 ≤ x ^ 2 := by
  by_contra h
  exact h (sq_nonneg x)
```

A case split is a proof strategy, not an extra source assumption. Ensure all cases are covered. After a tactic closes the last goal, stop; another tactic can produce a “No goals to be solved” diagnostic.

## 13. Coordinates and equality of paired objects

For a point `p : GeoPoint`, `p.1` and `p.2` are its coordinates. The seed also provides `geo_x p` and `geo_y p`. Use `Prod.ext` to prove pair equality from its two coordinate equalities. A scalar equation does not by itself prove equality of ordered pairs.

```lean
theorem guide_reconstruct (p : GeoPoint) : geo_point (geo_x p) (geo_y p) = p := by
  rfl
```

Use the real seed definitions for vector direction, dot product and determinant. Swapping the order of determinant arguments changes its sign. Do not silently identify an unoriented line, a ray and a directed vector; their coordinate representations can require different equivalence relations and domains.

## 14. Algebra, division and real roots

Use the approved `ring`, `linarith`, `nlinarith`, `norm_num`, `positivity` and `field_simp` where available. Supply nonzero denominator facts before cancellation. Establish root-square relations before nonlinear algebra. A solver tactic does not authorize dropping a side condition or introducing an extra assumption.

```lean
theorem guide_root (x : ℝ) (h : 0 ≤ x) : Real.sqrt x ^ 2 = x := by
  exact Real.sq_sqrt h
```

`Real.sqrt` is total on reals and returns zero on negative arguments; the mathematical square-root interpretation still needs a nonnegative radicand. Definitions depending on it usually need `noncomputable def`. `Real.sqrt_nonneg` gives nonnegativity, while a nonzero root needs stronger information. Do not assume `sqrt(x²)=x` for arbitrary real `x`; preserve sign conditions. See `roots` for further details.

## 15. Diagnostics and repair

Read the controller envelope and native REPL diagnostics. Native `messages` include `severity`, `data`, `pos` and `endPos`. Errors, unsolved obligations and `sorries` prevent acceptance. An `env` value alone does not imply success: `environment_transition.adopted_returned_env` records whether the controller committed the returned environment. Failed environments are not adopted.

Repair the actual category: a parser error needs syntax repair; a type mismatch needs the right domain/signature; an unknown identifier needs library lookup; an unsolved goal needs evidence. `controller_error` can instead indicate a source-policy or process problem. `receipt_id` locates complete immutable feedback. A warning-only `sorry` is forbidden despite exit code zero. Read `feedback` for exact field meanings.

## 16. Submission, retrieval and session lifetime

In the compact protocol, call `submit_candidate({code})` with the complete new increment. The controller saves it and checks it in the persistent REPL. On full success it independently checks the saved final module and dependency gate. Stop when `task_completed=true`. `passed` alone refers to the candidate check; local finalization can still fail. Do not manually create interfaces, final files or clause metadata.

`read_docs({topic:"core",section:"index"})` lists section IDs without their bodies. In direct jobs, error feedback attaches a relevant guide section; a bare core lookup returns that latest error-linked section when available. Read one section, batch several with `sections`, or use a focused `query`; `section:"all"` returns this full aligned guide. Lookups are local text retrieval, not model inference. Use actual declaration names with `read_library`. After a restart, accepted context is replayed separately. Five total attempts are shared with API failures; the common information-turn allowance prevents unlimited rereading. No task or verifier time cap is imposed.

## 17. Coverage boundaries and later books

This guide teaches language mechanisms, not a complete geometric foundation. Source-specific meanings and representations must still be built and justified. A two-dimensional technical seed is not a three-dimensional geometry library. In later books preserve magnitude kinds, the meaning of ratios, restrictions on source numbers and distinctions among commensurability classes; see `domains`.

Use the paired `basics`, `logic`, `roots`, `domains`, `seed` and `feedback` topics for their stated questions. Their examples are references, not additional task obligations or preloaded declarations. No user axioms, placeholders, unsafe code, extra imports or trust fallback are authorized. Missing support must be handled with checked definitions/proofs or reported as incomplete. Review time and solver time remain separate.
