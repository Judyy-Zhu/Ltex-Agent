# Litex operation card

## Declarations and functions
Use separate `#` comment lines; a comment does not continue a declaration or function body.

Use the seed's `GeoPoint`, `geo_point`, `geo_x`, `geo_y`, `geo_vec`, `geo_dot` and `geo_det` directly. The seed and predecessor declarations are already loaded. Write only new declarations. Function bodies belong on the same logical line as `=`. Indentation delimits blocks. Use fresh local names such as `p0`, `p1`, `x0`; do not shadow existing declarations. `N` and `R` are reserved builtin set names, not fresh parameter names.

```lit
have fn training_twice(x R) R = x + x
prop training_positive(x R):
    x > 0
thm training_fold:
    ? forall x R:
        x > 0
        =>:
            $training_positive(x)
    by def $training_positive(x)
thm training_double:
    ? forall x R:
        training_twice(x) = 2 * x
    training_twice(x) = x + x
    x + x = 2 * x
```

## Domains and well-definedness
Use `{x T: condition}` for set comprehension, `x $in S` for membership, and `power_set(T)` for sets of T-elements. A set, element, function and fact have different roles. See the direct-protocol `sets_membership` example. Set equality requires both inclusions.

Restricted function parameters use `(x R: x != 0)`; establish the condition before applying the function. This colon form is not a `prop` parameter list. Preserve source hypotheses when repairing domains. Direct-protocol `parameter_constraints` and `logical_composition` examples show supported forms.

`GeoPoint` is `cart(R, R)`; tuple coordinates are `p(1)` and `p(2)`. Predicate application uses `$name(args)`. Function calls use `name(args)` without `$`. Give explicit parameter domains and constraints needed for membership, division, roots and other operations. Use the approved coordinate-equality interface with its actual premises; do not invent a builtin proof command. State intermediate equalities and domain facts where definition expansion is not automatic.

## Quantifiers and proof structure
For a quantified definition with several scopes, define named predicates for the inner conditions and compose `$predicate(...)` facts; see the supplied `quantifier_composition` procedure. Keep all free parameters explicit. Do not move an existential across a universal or change dependencies to avoid a parser error. `prop name(parameters):` defines a predicate; `have fn ... Prop` is not its syntax.

Place quantified parameters in the documented `? forall ...:` theorem header. Antecedents precede `=>:` and conclusions follow it. Put each antecedent on its own line without a trailing comma. Use `exist x R st {...}` as a complete fact; introduce its witness with `obtain`. Do not insert nested `forall` into positions the parser rejects, or guess the placement of `<=>:`. For new quantifier/equivalence patterns retrieve the relevant original guide section. Supported `by` forms include `cases`, `contra`, `def`, `thm`, `extension` and induction forms documented by the pinned kernel. Native proof-search/internal rule labels are evidence, not automatically callable `by` commands. In particular, do not invent `by contain_exact_1(...)`. Consult checked generic examples for branching and witnesses instead of guessing syntax.

## Diagnostics and references
Read native `run_result`, `statement_results`, `errors`, `session_terminated` and `termination`. Success requires the controller's `passed`, not only `run_result`. Error `phase`, `category`, `message`, `obligation`, `failed_statement`, nested details and source locations identify what to repair. `statement_index` is a turn-local statement index, not a file line; the adapter supplies source/frame line maps. Earlier accepted blocks remain committed, but a partial prefix is not a complete candidate. `read_docs({topic:"core",section:"index"})` lists the aligned reference sections. Error feedback already attaches a relevant complete section; a bare core lookup reuses that selection. Explicit queries and section IDs remain available. `read_docs({topic:"logic",section:"all"})` contains checked generic proof structures. Look up actual predecessor signatures with `read_library`.
