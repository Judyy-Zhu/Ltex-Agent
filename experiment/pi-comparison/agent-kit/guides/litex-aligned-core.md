Litex reference guide. Paired curriculum: aligned-core-v1. Sections s01 through s17 have the same titles, order, teaching objectives and example categories as the Lean reference. Examples teach language mechanisms, not answers to Euclid tasks. The system operation card is the short starting reference; this document is queried when a specific rule is missing.

## 01. Scope and source fidelity

Translate the original source's mathematical meaning, including object domains, quantified variables, conditions, witnesses and conclusions. A checked definition can still describe the wrong object. Naming a predicate after a source concept does not establish correspondence. Do not replace a geometric condition with an unrelated constant or a tautology.

Preserve original proof steps when a source proof is supplied. Separately identify additional arguments needed by the coordinate model. An alternative proof may establish the same theorem without translating the original route. Definitions without an asserted theorem need checked definitions, not an invented characterization or existence project. Kernel acceptance and source fidelity remain separate outcomes.

## 02. Environment and library reuse

The pinned Litex Session loads the technical seed and its native algebraic foundation before your candidate. `GeoPoint` is the real-coordinate carrier `cart(R, R)`. The seed exports `geo_point`, `geo_x`, `geo_y`, `geo_vec`, `geo_dot` and `geo_det`. It does not preload Euclid's distances, angles, circles or source propositions. Read the supplied interface for signatures rather than inferring them from names.

The complete published own-language predecessor library is loaded too. Use its symbol index and `read_library` to find actual signatures and bodies. An earlier source task that failed is not available as a theorem. Write only the new increment: do not repeat imports, seed definitions or accepted predecessors. The controller assembles the standalone final file.

## 03. Names, parameters and block structure

Use fresh declaration names and explicit parameter domains. `N` and `R` are builtin set names, not fresh local variables. Prefer local names such as `p0`, `p1`, `x0`; do not shadow existing declarations or rebind variables already in the theorem's scope. A name conflict is not repaired by adding a second quantifier over the same name.

Indentation delimits blocks. Function application uses parentheses, as in `geo_x(p)`, and tuples use `(x, y)`. Function bodies follow `=` on the same logical line; a colon opens an indented block where documented. Line comments use `#`; a triple-quote block delimiter occupies its own line. Comments carry no mathematical evidence. Resolve an unknown identifier against the actual library before creating a competing definition.

## 04. Objects and explicit functions

Use `have` for a named object, `have fn` for an explicit function and `prop` for a condition or relation. Function binders use `(x R)` without Lean's colon, and the return domain follows the closing parenthesis without an arrow. A separately declared geometric condition does not constrain an exported object unless it is actually bound into its definition.

```lit
have fn guide_shift(x R) R = x + 2
```

This is a total arithmetic teaching function. It is not a supplied geometric construction. A constrained function places its conditions after the parameter domain, as in `(x R: x != 0)`. Discharge those conditions at each use. Choose a convenient representation only when it preserves the source meaning and necessary representation bridges.

## 05. Predicates and conjunctions

Use `prop name(parameters):` followed by its defining conditions. Multiple body conditions form the required conjunction. A predicate describes the supplied parameters; defining it does not prove that every object satisfies it. An unrelated condition elsewhere in the file does not constrain this predicate.

```lit
prop guide_fixed(x R):
    x = 7
prop guide_between(x R):
    x >= 0
    x <= 1
```

Apply a predicate as `$guide_fixed(x)`, including the `$` in theorem premises and conclusions. Ordinary function calls do not use `$`. To establish a conjunction, establish every required fact. Keep the parameter roles consistent when a relation is asymmetric. Do not omit nondegeneracy merely because a formula is syntactically valid.

## 06. Sets and membership

Use `power_set(T)` for a function returning a set of objects in `T`. Set comprehension is `{x T: condition}`, and membership is `x $in S`. Do not use bare `set` as a return domain or omit the `$` from membership. A point, a set of points and a verified membership fact have different roles.

```lit
have fn guide_level(t R) power_set(R) = {x R: x = t}
```

Defining this set does not establish every geometric property suggested by a name. Before applying membership, expose the actual set definition and required conditions. Do not replace equality of sets with one inclusion; both directions must be justified when needed. Never assume an arbitrary set is inhabited without evidence.

## 07. Universal statements and hypotheses

A named theorem starts with `thm name:` and a goal block beginning `? forall x R:`. Antecedents precede `=>:`; conclusions follow it. Write one antecedent fact per line without trailing commas; commas separate bound parameter names, not these fact lines. Keep arbitrary variables in the quantified header and use those same variables in the proof. Preserve the original quantifier order and witness dependencies.

```lit
thm guide_guard:
    ? forall x R:
        $guide_between(x)
        =>:
            x >= 0
    x >= 0
```

An unconditional quantified goal needs no `=>:` separator. Do not add an antecedent absent from the source. A construction proved for one fixed numeral does not establish a universally quantified claim. A theorem requires a complete proof body, not only a goal declaration.

## 08. Equivalence and negation

An equivalence requires both directions on the same domain. The pinned named-theorem goal syntax does not accept a root `forall ... <=>:` goal: use two named directional theorems when that presentation is needed. Do not guess the placement of `<=>:` from unrelated definition or standalone-fact syntax. Keep negation scope visible: `not`, `!=`, a negated universal and a negated existential do not express the same claim.

```lit
thm guide_forward:
    ? forall x R:
        $guide_fixed(x)
        =>:
            x = 7
    x = 7
thm guide_backward:
    ? forall x R:
        x = 7
        =>:
            $guide_fixed(x)
    by def $guide_fixed(x)
```

These two teaching proofs share the same domain and no additional side assumptions. For actual source equivalences, ensure each direction's expressions are defined; a guard present in only one direction cannot automatically justify the other direction.

## 09. Using assumptions and named theorems

The proof body records facts that must follow from the current environment. Predicate premises make their defining conditions available. Do not redeclare an already known premise with `know`, introduce it as a new assumption, or prove it by assuming the desired conclusion. A named function and a theorem about that function have different roles.

```lit
thm guide_call:
    ? forall x R:
        $guide_fixed(x)
        =>:
            x = 7
    by thm guide_forward(x)
```

Use the actual theorem signature for argument order and required conditions. Do not guess a theorem from its name. Internal rule labels in a native trace are not automatically callable `by` commands; in particular, do not invent a command from a verifier's explanation of membership or equality reasoning.

## 10. Definition expansion and equation chains

Expose needed function definitions as explicit equations before relying on their expanded forms. Use `by def $predicate(args)` to fold a predicate after its conditions are established. If a fact is unknown, identify its missing expansion or premise instead of merely repeating the same assertion.

```lit
thm guide_expand:
    ? forall x R:
        guide_shift(x) - 2 = x
    guide_shift(x) = x + 2
    guide_shift(x) - 2 = (x + 2) - 2 = x
```

An equation chain justifies successive equalities; algebraic normalization can handle supported polynomial identities. Do not mix equality and inequality in one chain. Split a difficult derivation into small established facts, so the first unsolved obligation identifies a missing step without weakening the final conclusion. Predicate application still needs `$`; function expansion does not.

## 11. Existential witnesses and their properties

Existence is written `exist y R st {conditions}`. A witness proof uses `witness exist ... st {...} from value`, with an indented body when additional properties need proof. Use `exist`, not `exists`, and keep the braces following `st`. A witness may depend on earlier universal parameters, but not on variables introduced only later.

```lit
thm guide_witness:
    ? forall x R:
        exist y R st {y = x + 1 and y - x = 1}
    witness exist y R st {y = x + 1 and y - x = 1} from x + 1:
        (x + 1) - x = 1
```

The witness must satisfy every condition. Existence does not imply uniqueness. A unique-selection function needs both existence and uniqueness evidence; naming or selecting an arbitrary value does not justify a missing geometric construction.

## 12. Cases and contradiction

Use a documented `by cases:` block with its target and a branch for each case. Prove the same conclusion in every branch. `by contra:` supplies a contradiction proof of the stated target; `impossible` must be justified by available facts, not used as a placeholder. Scope and the exact negation matter.

```lit
thm guide_branch:
    ? forall x R:
        x = 0 or x = 1
        =>:
            x * (x - 1) = 0
    by cases:
        ? x * (x - 1) = 0
        case x = 0:
            x * (x - 1) = 0
        case x = 1:
            x * (x - 1) = 0
thm guide_square_nonnegative:
    ? forall x R:
        x^2 >= 0
    by contra:
        ? x^2 >= 0
        impossible not x^2 >= 0
```

A case split is a proof strategy, not an extra source assumption. Ensure all cases are covered. Consult `logic` for further checked generic patterns rather than guessing a new proof-block command.

## 13. Coordinates and equality of paired objects

For `p GeoPoint`, tuple coordinates are `p(1)` and `p(2)`; indexing is one based. The seed also provides `geo_x(p)` and `geo_y(p)`. Tuple equality requires both coordinate equalities; use the approved `tuple_equal_from_coordinates` interface with its actual premises when direct reconstruction is insufficient. Do not invent a new builtin command.

```lit
thm guide_reconstruct:
    ? forall p GeoPoint:
        geo_point(geo_x(p),geo_y(p)) = p
    geo_point(geo_x(p),geo_y(p)) = p
```

Use the real seed definitions for vector direction, dot product and determinant. Swapping determinant arguments changes its sign. Do not silently identify an unoriented line, a ray and a directed vector; their coordinate representations can require different equivalence relations and domains.

## 14. Algebra, division and real roots

Write supported polynomial, order and cancellation facts in forms the native verifier recognizes. Establish denominator nonzero facts before division or cancellation. For positivity, expose squares and known signs rather than jumping between unrelated forms. A native algebra rule does not authorize dropping a side condition or introducing an extra assumption.

```lit
thm guide_root:
    ? forall x R:
        x >= 0
        =>:
            sqrt(x)^2 = x
    sqrt(x)^2 = x
```

`sqrt(x)` requires a nonnegative real radicand in this environment. Prove that domain fact before use. A nonzero root generally requires positivity, not merely nonnegativity. Do not assume `sqrt(x^2)=x` for arbitrary real `x`; preserve sign conditions. Builtin matching is not a guessed `by builtin` command. See `roots` for further details.

## 15. Diagnostics and repair

Read the controller envelope and full native Session feedback. `run_result` describes the turn; `statement_results` records individual statements; `errors` holds diagnostics. `session_terminated` and `termination` identify session stopping conditions. An earlier accepted statement is not proof that the complete candidate passed. Native error `phase`, `category`, `message`, `obligation`, `failed_statement`, nested details and locations help identify the repair.

`statement_index` is a turn-local statement index, not a file line; use the supplied source/frame line map. Repair syntax, domain/membership, missing facts or name conflicts according to the actual error. `controller_error` can instead indicate a source-policy or process problem. `receipt_id` locates complete immutable feedback. Native `run_result` alone is insufficient; inspect controller `passed`. Read `feedback` for exact field meanings.

## 16. Submission, retrieval and session lifetime

In the compact protocol, call `submit_candidate({code})` with the complete new increment. The controller saves it and checks it in the persistent Session. On full success it independently checks the saved final module and dependency gate. Stop when `task_completed=true`. `passed` alone refers to the candidate check; local finalization can still fail. Do not manually create interfaces, final files or clause metadata.

`read_docs({topic:"core",section:"index"})` lists section IDs without their bodies. In direct jobs, error feedback attaches a relevant guide section; a bare core lookup returns that latest error-linked section when available. Read one section, batch several with `sections`, or use a focused `query`; `section:"all"` returns this full aligned guide. Lookups are local text retrieval, not model inference. Use actual declaration names with `read_library`. After a restart, accepted context is replayed separately. Five total attempts are shared with API failures; the common information-turn allowance prevents unlimited rereading. No task or verifier time cap is imposed.

## 17. Coverage boundaries and later books

This guide teaches language mechanisms, not a complete geometric foundation. Source-specific meanings and representations must still be built and justified. A two-dimensional technical seed is not a three-dimensional geometry library. In later books preserve magnitude kinds, the meaning of ratios, restrictions on source numbers and distinctions among commensurability classes; see `domains`.

Use the paired `basics`, `logic`, `roots`, `domains`, `seed` and `feedback` topics for their stated questions. Their examples are references, not additional task obligations or preloaded declarations. No user axioms, placeholders, unsafe code, extra imports or trust fallback are authorized. Missing support must be handled with checked definitions/proofs or reported as incomplete. Review time and solver time remain separate.
