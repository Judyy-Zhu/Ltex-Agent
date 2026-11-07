# Euclid's Elements, Books I–VI: current-Litex redevelopment plan

Prepared: 2026-10-11; updated: 2026-10-12. Status: I.1–I.33 passed the complete canonical strict checkpoint (49 declarations, 2420.565s Python monotonic, stable hashes). Full I.34 candidate1 failed an explicit equal-squares/root bridge; candidate2 is prepared in the recovery Session. Foundations: 1/74 complete across all six books (1/33 in Book I); later books and corollaries remain unfinished.

## Goal and source boundary

Re-author the first six books using the current Litex language and verifier. Preserve the identity and mathematical content of every numbered proposition, including construction problems, definitions, original postulates/common notions, and source corollaries. Keep source proof ideas visible even when a checked proof uses a different established route.

The authoritative source is [Euclid's Elements, translated by Richard Fitzpatrick](https://farside.ph.utexas.edu/Books/Euclid/Elements.pdf), revised 2008. Book openings are printed pages 5, 49, 69, 109, 129, and 155; Book VII starts at 193. These coincide with the PDF's one-based pages. The agreed working boundary is Books I–VI; later solid geometry is outside this six-book slice.

The coverage target is 173 numbered propositions: 48 + 14 + 37 + 16 + 25 + 33. That count does not include definitions or corollaries. Coverage and completed proofs must be reported separately.

## Observed legacy baseline

`Euclid_Elements_Book.lit` is currently a 25-line entry file. Its comments reference 48 separate files under `Book/`. The user subsequently identified their archive: `Book.zip` in this same workspace. The entry's only theorem is a trusted reflexive-equality placeholder:

```litex
thm book_one_placeholder:
    ? forall x R:
        x = x
        =>:
            x = x
    trust x = x
```

The archive has now been inspected directly, without extraction or modification. It contains all 48 `Book/PropXX.lit` files. I.1 and I.2 contain substantive coordinate-based construction code; I.3–I.48 are 46 placeholders whose formal conclusion is `a = a`. For example, `Book/Prop47.lit` mentions Pythagoras in a comment but formally states only reflexive point equality, without a right-angle hypothesis or the square/area conclusion. Their acceptance would not verify the source propositions.

The archive's README claims all 48 propositions are fully verified, while PROGRESS and TRANSLATION_LOG give different completion counts. These historical summaries do not establish coverage; use the actual theorem statements as the baseline. See `legacy_archive_audit.md` for the reproducible inventory. The old binary/version has not been identified, and unchanged archived I.1/I.2 reproduce current-parser rejection of legacy bracket indexing. Preserve the archive and entry file. Treat I.1/I.2 as migration candidates and I.3–I.48 as new statement/proof authoring, reusing source explanations and diagrams where appropriate.

## Decisions before foundational authoring

### Geometry model

Following the user's proposed direction, use the existing 2D analytic-geometry module as the primary foundation candidate: points in `cart(R, R)`, coordinate-defined operations, and derived geometric relations. This replaces the initial synthetic recommendation. Keep the book's geometric statements, proposition order, constructions, and proof ideas visible above that foundation. The results will be proved in a real-coordinate model; they do not establish derivability from Euclid's five postulates alone.

The intended layers are analytic primitives, reusable geometric objects/relations and their laws, then source-numbered book propositions. Audit the maintained analytic module before deciding its exact dependency boundary. The initially inspected showcase has this smaller scope. The selected full Geometry2d dependency supplies 40 definitions and 186 theorems, including lines, circles, collinearity, perpendicularity, congruence, and affine constructions; its 227 top-level statements passed the current strict verifier. Add missing reusable geometry only from independently justified definitions and actual book uses. Construction problems require explicit valid witnesses and construction-step correctness, not merely algebraic equations or labels asserting constructibility.

Two existing maintained candidates merit inspection and current-source verification:

- `showcases/math_concepts_in_litex/14_tarski_geometry_from_axioms/`: synthetic Tarski-style relations and assumption bundles, including code for I.5 and SAS. Its README explicitly lists incomplete later layers; it is not a complete Euclid library.
- `showcases/math_concepts_in_litex/2_euclidean_geometry/`: analytic `cart(R, R)` geometry and code for I.1. An analytic witness is useful evidence for this route, but does not by itself verify Euclid's two-circle construction or all synthetic foundations.

The small analytic showcase and full selected analytic library have now been rerun successfully; the synthetic candidate is not the selected dependency. Avoid silently copying a complete showcase, adopting all its assumptions, or presenting its axiom system as identical to Euclid's five postulates. Decide import versus source-local foundation ownership after the selected interface audit.

The exact existing coordinate statement illustrates the alternative, not the selected new-book interface:

```litex
thm euclid_book1_proposition_1:
    ? forall a, b cart(R, R):
        a != b
        =>:
            exist c cart(R, R) st {$is_equilateral_triangle(a, b, c)}
```

### Foundation and proof debt

Keep three categories separate: Euclid's explicit postulates/common notions, additional mathematical assumptions needed for rigor, and temporary unproved facts. Do not declare later propositions as foundational laws just to make their proofs immediate.

I.1 is the first acceptance tracer. Source page 8 explicitly notes an additional assumption behind circle intersection. The formalization must establish an actual apex on the two intended circles, equal sides, and a genuine noncollinear triangle; `a != b` alone is not a substitute for all required witness properties. A selected apex is not canonical without an orientation/side choice, so do not assert unique existence merely to expose a function.

For synthetic geometry, audit incidence, order/Pasch, congruence, dimension, parallelism, and circle/line continuity separately. For coordinates, document the `R²` interpretation and prove the appropriate construction properties. Neither route may assume I.47 or later similarity results to establish earlier dependencies.

### Magnitudes and equality

Plan the interfaces needed by Books II, V, and VI before finishing Book I's area layer. Separate equal lengths, equal angles, triangle congruence, equal areas, and similarity. Equal figures in area arguments must not be encoded as pointwise equality or congruence.

Book V requires a faithful equimultiple comparison relation for ratios, including incommensurable magnitudes. A positive-real interpretation may be chosen, but must be declared as a model, retain the source definition, and justify its bridge to division. Lengths, areas, angles, and arcs require compatible quantity domains; arbitrary cross-kind addition or comparison is forbidden. Book VI.33 makes angle and arc magnitudes a real downstream consumer, not optional vocabulary.

## Staged delivery and acceptance checkpoints

| Stage | Source scope | Main work | Exit evidence |
|---|---|---|---|
| 0 | Existing Book I and six-book source | Locate legacy files; choose foundations; identify reusable current interfaces; establish source manifest and explicit assumption ledger | Source inventory, agreed model, verified minimal definition/use probe, I.1 acceptance statement |
| 1a | I definitions, postulates, common notions; I.1–I.8 | Points, lines/segments, circles, genuine triangles, constructions, congruence | I.1 witness and downstream I.2 use; all eight source statements; exact assumptions/debt |
| 1b | I.9–I.26 | Bisectors, perpendiculars, angle relations, triangle inequalities and congruence | Source-ordered file gate; endpoint/coincidence and side-position cases audited |
| 1c | I.27–I.32 | Parallelism and triangle angle results | Parallel-postulate dependencies distinguished from neutral results; I.32 reusable |
| 1d | I.33–I.48 | Parallelograms, area equality, square constructions, Pythagoras and converse | Complete 48-proposition Book I gate; I.47/I.48 use tests; area versus congruence audit |
| 2 | II.1–II.14 | Rectangles/squares and geometric algebra, with actual geometric inputs and constructions | Complete 14-proposition gate; geometry-to-magnitude bridge and II.14 witness |
| 3a | III.1–III.18 | Circle center, chords, intersections, tangency | Circle and tangent definitions/use probes; relevant cases and nondegeneracy |
| 3b | III.19–III.37 | Circle angles, arcs, cyclic figures, tangent/secant results | Complete 37-proposition gate; source configurations and area-product dependencies |
| 4 | IV.1–IV.16 | Inscribed/circumscribed constructions and regular polygons | Complete 16-proposition gate; witnesses, vertex order, distinctness, and enclosure verified |
| 5 | V definitions; V.1–V.25 | Same-kind magnitudes, equimultiples, ratio equality/order, proportional reasoning | Complete 25-proposition gate; equimultiple definition and any numerical bridge verified |
| 6a | VI.1–VI.17 | Area ratios, similarity, proportional constructions | Both Book I area and Book V ratio interfaces consumed; similarity/congruence distinguished |
| 6b | VI.18–VI.33 | Similar polygons, area applications, further constructions, angles/arcs | Complete 33-proposition gate; VI.33 included; all six books integration audit |
| 7 | I–VI consolidation | Revisit remaining proof debt, shorten proofs, reconcile source records and documentation | 173/173 source statements; checked counts and remaining debt disclosed independently; clean whole-module gate |

No calendar estimate is committed before Stage 1a exposes real foundation and verifier costs. Execute and report bounded source slices. A run that depends on `trust` is a translated, runnable checkpoint, not completion of proof verification.

## Dependency spine and implementation order

The arrows below describe intended mathematical prerequisites, not verified theorem citations. `signature` means carrier/type dependence, `definition` means vocabulary construction, `existence` means required witnesses, and `proof` means an earlier mathematical result supports later derivations. `assumption` marks the chosen foundation boundary.

```text
Chosen carriers and named foundations --signature/assumption--> incidence, order, congruence
Incidence/order/congruence --definition--> segments, rays, triangles, circles, angles
Circle existence/intersection --existence--> I.1 --proof--> I.2/I.3
Congruence and angle laws --proof--> I.4–I.26
Parallel foundation + preceding angle results --proof--> I.27–I.32
Parallel/triangle results + area interface --proof--> I.33–I.48
Book I area and constructions --proof--> Book II
Book I congruence/order + circle vocabulary --proof--> Book III
Books I–III constructions --proof--> Book IV
Magnitude domain + equimultiple definition --definition/proof--> Book V
Books I/II/III + Book V --proof--> Book VI
Angle and arc magnitude interfaces + Book III/Book V --proof--> VI.33
```

Design Book V's necessary quantity interfaces early; implement its source-facing propositions in Book V's original order. Do not import Book V's future results into Book I. Each proposition record must later replace this coarse plan with actual direct dependencies. Detect circularity before inserting proof debt; return to the first missing independently justified interface.

## Workspace and durable artifacts

Continue using this local-only workspace. After the foundation choice, register `Euclid_Elements` once in `scripts/.textbooks` and create one maintained module under `textbook/`, with one `README.md`, one `math_collections.md`, a `litex.config`, and ordered book files. Split long books into ordered files only when useful for proof checkpoints; retain Book/proposition numbering.

Keep these working records beside the module:

- `migration_plan.md`: this maintained scope and sequence.
- `translation_records/`: source item, mathematical statement/reformulation, proof idea, current code, status and command evidence; required fields are `source`, `problem`, `proof_idea`, `litex_code`, `comments`.
- `proof_journals/`: accepted statements and materially distinct failed attempts, with exact verifier feedback.
- `todo.md` and `unfinished/problem_notes/`: surviving narrowly labeled `trust` or `kernel_problem` items, including downstream dependencies and next acceptance checks.
- `experience/problem_notes/book01_proposition01_acceptance.md`: durable legacy/current tracer comparison once I.1 is actually verified. Do not create a fictitious former failure where old proof files are unavailable.
- `.draft/`: the single area for scratch prefixes, isolated configs, probes, and raw transcripts. Do not register drafts in the production module.

All `scripts/` paths remain ignored and untracked in the parent repository. Preserve any existing nested repository; do not initialize one. Publication is a separate requested step, governed by the user's local-only scripts boundary.

## Verification protocol

1. Build the current source once with `cargo build --release`; record the source revision and release version. An old system binary is not a substitute.
2. Establish a passing registered prefix or an isolated draft context with the exact preceding exports and an empty target. Start `target/release/litex -lang en -f <accepted-prefix.lit> -session`.
3. Submit one top-level statement at a time in source order and consume each result. Keep the same live Session after an ordinary failure. Do not use historical `-before`, `-compact`, `-runner`, or literal `try:` recipes.
4. Journal accepted source before proceeding. At a coherent checkpoint save the accepted contiguous prefix and run `target/release/litex -lang en -f <registered-file.lit>`. Require exit 0 and Normal JSON `kind: run`, `run_result: "success"`, `session_terminated: false`, `termination: null`.
5. Use `-strict` where user trust/global axioms must be excluded. Strict acceptance under a setting still proves a theorem relative to that setting; it does not prove the assumptions themselves or consistency of the geometry model.
6. Timebox unresolved obligations under the repository's two-pass policy: at most three active minutes initially, then at most five active minutes per debt after the intended checkpoint runs. Keep only the narrow missing fact trusted; survivors remain explicit. Migration triage itself must preserve unchanged failures rather than patching them with trust.
7. Check actual downstream use and relevant degenerate cases. Apply backward proof liveness and whole-chain deletion probes; keep genuine source-facing calculations.
8. Run an explicit whole-book/whole-module `-r` gate at the stated integration checkpoints, not per proof attempt. Select any Rust gates by the actual semantic impact; protected owner changes retain their separate authorization requirements.

## Completion and next bounded action

Completion requires all 173 propositions and included source items to be represented faithfully, with construction outputs verified rather than merely named. Report separately: translated statements, checked proofs under accepted foundations, direct and imported proof debt, and kernel blockers. A clean run alone cannot establish full source coverage or absence of hidden assumptions.

The legacy-location question is resolved by `Book.zip`. The dependency is the fuller Geometry2d source at `scripts/LitexGeo-AutoBuild/shenjiachen/新geo和geo_definitions/geo.lit`, mounted by a manifest without copying its source. I.1–I.10 passed the canonical strict file checkpoint with stable source/executable hashes; I.11/I.12 have strict Session acceptance and their first-twelve gate is running. No user trust was added. Source definitions, postulates, common notions and the remaining numbered propositions are unfinished. Principal ray angle, its range, supplementary-angle and right-angle-measure interfaces have strict Session acceptance. I.13's actual sum proof is the current source item; four-plus ordinary representation-bridge attempts are recorded in the proof journal, and the live Session is retained. Continue through I.14–I.15 and the rest of Book I, then Books II–VI in the staged plan. Measurements and exact binary provenance are recorded in `experiment/`.


Source foundation inventory update: the supplied revised-2008 edition has 23/2/11/7/18/3 definitions in Books I–VI, plus the five postulates and five common notions in Book I: 74 source foundation items in total. The former 1/33 counter is explicitly Book I only. The whole six-book foundation count is 1/74, with later 41 definitions inventoried but unformalized. Book VI has only three definitions in this edition before Proposition 1. Corollaries remain a separate mandatory inventory. Book III curved segment angles and Book V equimultiple ratio equivalence are explicit modeling obligations; ordinary ray angles and rational proportions cannot silently replace them.
