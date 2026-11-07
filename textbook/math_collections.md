# Mathematical collections

## Purpose and scope

Represent the geometry of Euclid Books I–IV and VI faithfully over the real plane; Book V supplies only the required ratio lemmas. Definitions and source propositions retain their mathematical meaning and numbering. The design is analytic; it does not assert that coordinates have been constructed from Euclid's five postulates. Interfaces below are design commitments until their actual use probes pass.

## Modeling conventions

Reuse the existing Geometry2d vocabulary from `scripts/LitexGeo-AutoBuild/shenjiachen/新geo和geo_definitions/geo.lit`. It includes its definitions, so do not load `geo_definitions.lit` a second time in the production prefix. The manifest-only `geometry/` dependency mounts the existing file as `geometry::main`; the book uses `geometry::main::distance_sq`, `geometry::main::det`, and the other actual source interfaces. Each proof file explicitly releases the operations needed in its own environment. Releasing them in an earlier export does not initialize later file environments. The external source remains owned by its existing workspace; no copied library becomes a parallel source of truth. The manifest exists because the source library has no module manifest at that location.

Points use `cart(R,R)`; coordinates are one-based calls. Nondegenerate triangles have nonzero determinant. Circles have radius in `R+`. The current library permits flat parallelograms and coincident points in concyclicity; source-facing figures must assert the stricter conditions required by Euclid explicitly. Segment equality, triangle congruence, area equality, and similarity are distinct relations.

## Mathematical spine

### Points, displacement, dot product and determinant

- Ordinary meaning: real pairs and vector arithmetic; determinant gives orientation and signed doubled area.
- Semantic roles/forms: carrier and ordinary formula-defined functions, using existing `have`/`have fn` declarations.
- Interface: `geometry::vec(a,b)`, `geometry::dot(u,v)`, `geometry::det(u,v)`.
- Nearest rejected form: abstract point axioms with implicit coordinate laws, since the chosen model is concrete.
- Dependencies: builtin real arithmetic and pair projection, by signature/definition.
- Uses: I.1 noncollinearity; line incidence, angle relations and later area.
- Allowable hole: verifier limitations in an exact coordinate proof, recorded without changing the carrier.

### Squared distance, segments and circles

- Ordinary meaning: squared length is the displacement's self-dot-product; a positive-radius circle is its fixed-distance locus.
- Form: reuse `geometry::distance_sq`, `geometry::circle`, and segment-congruence relations. Circle is a set-valued function, not merely a property of unnamed data.
- Uses: I.1's two-circle witness and I.2's transferred segment. Later length inequalities may use the library's `distance` and its proven square law.
- Dependencies: metric definition; nonnegativity/positive-radius WD; existing theorem laws only when their actual source has passed.
- Boundary: distinct endpoints are necessary for a genuine given segment; distance itself permits coincident endpoints. Do not add the archived I.2 restriction `a != b` when the new start point may coincide with an endpoint.

### Equilateral construction and genuine triangles

- Ordinary meaning: on distinct endpoints a,b construct c so abc is a noncollinear triangle with three equal sides.
- Form: a source-facing theorem using existing `geometry::is_equilateral`, with a formula-defined oriented apex when callers actually need that function.
- Nearest rejected form: the weaker showcase predicate that contains only `a != b` and two equal-distance laws without an explicit triangle condition.
- Dependencies: metric symmetry, square-root algebra and a nonzero determinant. Two-circle membership must follow from the same witness; do not assume an apex merely to obtain existence.
- Use probe: base (0,0) to (2,0), apex (1,sqrt(3)), plus a genuinely arbitrary distinct base. Coincident endpoints must be rejected by the source-facing relation.
- Allowable hole: the narrowest unproved equality/inequality, marked as debt; it cannot be called fully checkable.

### Lines, rays, angles and congruence

- Ordinary meaning: source geometric relations on supplied points with appropriate nonzero arms and positions.
- Form: existing set-valued lines and geometric `prop` relations; source-owned supplementary conditions where Euclid requires distinct lines, interior rays or ordered vertices.
- Dependencies: incidence/determinant, affine parameters, dot product, sign-sensitive angle equality.
- Uses: I.3 onward, including I.4 SAS and I.5. Equal squared cosines alone do not identify the angle: retain the library's sign condition.
- Boundary: parallel directions may include coincident lines, while Euclid's parallel lines are distinct and disjoint; the book must state that extra condition.

### Principal ray-angle magnitude (I.13 onward)

- Ordinary meaning: angle between two nonzero rays as a principal radian value in [0,pi]. A genuine source rectilinear angle additionally excludes collinearity; zero/straight boundary values are auxiliary, not silently called source angles.
- Semantic role/form: normalized cosine and angle are `have fn` quantities, not predicates. Existing `are_angles_congruent` remains the relational interface and needs an explicit measure-equivalence bridge.
- Designed signature: `ray_angle(p,q,r cart(R,R): p!=q, r!=q) R = arccos(angle_cosine(p,q,r))`. The definition and range are strict Session checked; the cold module file gate is pending.
- Forward dependencies: original metric -> positive norm product -> square-root denominator WD -> normalized-dot bounds [-1,1] by dot/determinant identity -> principal arccos -> numeric angle addition/order/ratios.
- Immediate probes: orthogonal unit rays give pi/2; opposite base rays with a perpendicular third ray give a sum pi; a zero arm rejects.
- Checked so far in the authoring Session: denominator positive, nonnegative and square-root nonzero; normalized-cosine function definition; two bounded opposite cosine values have arccos values summing to pi. Cosine range, principal angle definition/range, cosine reconstruction, and both directions of the right-angle measure bridge are strict Session checked. The concrete orthogonal-unit-ray probe passed; the zero-arm probe was rejected by its exact point-distinctness guard. I.13's angle sum is Session accepted, with a full file checkpoint pending. Proof source and domain boundaries are in `../translation_records/angle_measure_interface.json`.
- Nearest rejected form: an unexplained Boolean wrapper that merely asserts the requested angle sum, or a source theorem whose conclusion is only collinearity.

### Positive segment length (I.20 and magnitude interfaces)

- Ordinary meaning: Euclidean length of a segment with distinct endpoints, not squared distance.
- Form: `have fn segment_length(a,b cart(R,R): a!=b) R+ = sqrt(distance_sq(a,b))`; its domain/codomain and definition are strict Session checked, cold file gate pending.
- Forward dependencies: original squared-distance nonnegativity -> positivity for distinct endpoints -> exact positive-root membership -> positive-valued function.
- Use probes: a nonzero segment's length square equals its squared distance; coincident endpoints must reject this positive-segment interface. Both use probes passed in the retained Session: (0,0) to (3,4) gives length 5, and coincident endpoints reject at the point-distinctness guard.
- Uses: source I.20's three strict side sums, later constructions and positive same-kind magnitudes; zero distance remains available through the original unconditional squared-distance function.

### Strict triangle interior (I.21)

- Ordinary meaning: the open interior of a nondegenerate triangle; vertices and edges are excluded.
- Form: source-local `strictly_inside_triangle(p,a,b,c)` with triangle/point-domain guards and positive barycentric weights `u,v`, `u+v<1`, remaining weight `1-u-v>0`.
- Forward construction: intersect ray BD with AC at E, parameter `v/(1-u)`; D then lies strictly between B and E with parameter `1-u`. Prove these incidence facts before consuming length/angle results.
- Uses: I.21's two comparisons and later polygon/area interfaces. I.20 and I.16 supply the source proof route; no I.32 angle sum is assumed.
- Probes: in the triangle (0,0),(4,0),(0,4), point (1,1) is interior; (2,0) is a boundary point. Both probes passed in Session: (1,1) has positive witnesses 1/4,1/4, and (2,0) is rigorously excluded because its second coordinate would force a positive weight to zero.

### Three-side triangle constructor (I.22)

- Ordinary meaning: construct a genuine triangle from three positive magnitudes satisfying every strict triangle inequality.
- Form: upper-plane apex `((r^2+s^2-t^2)/(2*r), sqrt(s^2-((r^2+s^2-t^2)/(2*r))^2))`, with all three inequalities inside the function domain.
- Forward dependency: three strict inequalities -> positive four-factor discriminant -> positive squared height -> actual apex -> distance/circle certificates -> nondegenerate triangle witness.
- Uses/probes: lengths 3,4,5 must yield a genuine triangle; equality at a side-sum boundary must reject the strict constructor. Constructor, both metric/circle certificates, and the source-segment wrapper are strict Session accepted. The 3-4-5 probe gives apex (0,4), squared distances 16/25 and determinant 12; the 1-1-2 equality boundary rejects. Canonical first-twenty-two cold gate passed with stable hashes.

### Areas, magnitudes, ratios and similarity

- Ordinary meaning: unsigned area of nondegenerate figures and same-kind positive quantities; Book V compares equimultiples and Book VI applies those ratios to geometry.
- Form: real-valued area/length functions and genuine ratio relations. Exact definitions will be audited before introduction; no unimplemented signatures are claimed as API.
- Dependencies: determinants/absolute values, geometry figure constraints, builtin positive reals and integer multiples; mathematical bridges from the source definitions.
- Uses: I.35–I.48, Books II/V/VI, including VI.33's angle/arc ratios.
- Boundary: do not replace source proportion by unexplained cross multiplication, equate different kinds of quantities, confuse area with congruence, or use later source results circularly.
- Verified numerical bridge (draft): `have_equal_equimultiple_comparisons(a,b,c,d)` quantifies all positive-integer pairs and all three comparison equivalences. For arbitrary positive real measures it is equivalent to `a*d=b*c`; the reverse proof uses rational separation, not rational-only magnitudes. Strict clean checkpoint passed 11 declarations, including an irrational use and quotient consumer; wrong-ratio and zero-input controls rejected in the retained Session. See `../translation_records/book05-equimultiple-equivalence.json`. Same-kind quantity interfaces and canonical Book V definitions remain pending.

- Further numerical layer: the exact V.Def7 predicate retains `m*c <= n*d` and is equivalent to strict cross-product order. V.Def4 comparability, V.7–V.11 (both applicable clauses), V.7 inversion corollary, and V.13 now have checked positive-real formulations. Coherent strict27 passed with stable hashes; equality-boundary and irrational uses passed and equal-ratio/zero-input negatives rejected. Source mappings and remaining quantity-kind scope: `../translation_records/book05-ratio-order-real-measures.json`.

## Dependency map and build order

`signature/definition`: real pairs → vector operations → squared distance and determinant → triangles/circles/lines.

`proof/existence`: independent coordinate algebra → I.1 witness and circle membership → source constructions and congruence → parallels and areas → circles/polygons; magnitude definitions → Book V; preceding geometry + Book V → Book VI.

The full analytic library contains later results proved independently by algebra. Reuse must be documented as an analytic proof route, not falsely described as the original source dependency order. The book preserves its source order; any source proof route not yet checked remains visible as such.

## Interface decisions and permissible gaps

Keep the existing geometry vocabulary canonical. Do not create aliases for each imported function or export proof-only helpers with one consumer. Check the actual interfaces before adopting theorem names; a declaration name or a historical README does not prove source fidelity. All temporary trust remains explicit and separately counted in the experiment.


### Actual parallel straight lines (Book I Definition 23, I.27 onward)

- Carrier/form: two proper endpoint pairs in the real plane, with existing `line_through_points` as their actual infinite point sets. Source-facing `parallel::are_parallel_lines` retains the established direction predicate and nonzero transverse determinant.
- Source meaning: the infinite lines do not meet. Both implications between this meaning and the direction/separation formula passed the retained strict Session. The converse constructs an actual common point for nonparallel directions and excludes zero separation.
- Uses: Definition 23, alternate-angle parallelism I.27 and subsequent parallel-line propositions. Distinct horizontal lines passed; coincident horizontal lines passed ordinary endpoint/direction conditions and rejected at the strict fold's zero separation.
- Boundary: the existing `geometry::main::is_parallel` remains a direction relation. Its signature and meaning are not changed. The strict canonical module cold gate passed 7 declarations in 900.318 seconds with stable hashes; the equivalence is canonically verified.

The verified canonical source coverage is I.1–I.44 and I.46–I.48, III.1–III.15 and III.17–III.19, plus the III.1 and III.16 corollaries. Book I promotion uses the strict74 canonical-prefix receipt recorded in `../translation_records/book01-area-canonical-promotion.json`; its binary version is explicit. I.45 remains unfinished. Full III.16 remains unfinished. Source inventories cover 64 definitions and ten Book I postulates/common notions, for 74 foundation items. Five are canonically checked: I.Def23, II.Def1, III.Def2, III.Def4 and III.Def5. The remaining foundation items are still unfinished. Source III.Def7's angle of a circular segment needs a faithful curved-angle interface; V.Def5 must retain positive-integer equimultiple comparisons and irrational real magnitudes.

## Books II–III extension

The source-aware concept inventory, interface choices, immediate uses, typed dependency graph and full51-proposition/13-definition completion gates are in [books02-03-plan.md](../books02-03-plan.md). Circle circumference and disk interior are separate objects. Tangency requires a circumference contact and nonentry into the disk interior. Unique contact and radius-perpendicularity are derived separately. Gnomon and circular segment/sector are real regions, not scalar aliases. III16 curvilinear angle requires its own local-region comparison semantics; it is not ordinary ray_angle. The unfinished gnomon, sector and curved-angle interfaces remain designs. Filled circular segments, angles in segments and segment similarity have now passed independent strict checks; canonical integration is pending. The checked rectangle, circle-center and tangent-line interfaces are recorded in the README.

### Reflection in a proper axis (III.7; also used by draft III.8)

- Mathematical object: the reflection of a real point q across the line through o and p. The function `reflection_in_axis(o,p,q)` returns an actual point, so a predicate alone would not meet its use.
- Domain: all three points lie in `cart(R,R)` and the squared norm of p−o is positive. This is exactly a nonzero axis and guards the denominator in the formula o + 2〈p−o,q−o〉(p−o)/|p−o|² − (q−o).
- Uses: construct the equal-distance partner in III.7 and III.8. Reflection preserves distances to o and p and reverses the signed determinant. For a circle centered at o and q off the axis, its reflection is a distinct point on the opposite side, on the same circle and equally distant from p.
- Evidence: the constructor and horizontal use passed an independent strict checkpoint. General preservation, partner existence and the translated diagonal use have passed their independent strict checkpoint. For o=(1,2), p=(2,3), q=(1,4), the reflected point is (3,2).
- The circle-point uniqueness theorem and its diagonal classification use have also passed an independent strict checkpoint. Radial extrema now have an independent strict checkpoint. Actual angular ordering (interior and both external branches) and the external second-intersection parameter classification have Session acceptance. The combined angle/ray checkpoint now passed. All III.7 clauses have now passed the full III.1–III.7 strict gate and are canonical. III.8–III.15 integration has passed; an individual reflection lemma alone is not a source-proposition completion.


### Radial extrema and ray ordering (III.7–III.10 canonical)

- Real-plane foundation: for a positive-radius circle and noncentral observer, the center-axis endpoints have squared distances `(sqrt(distance_sq(o,p))-radius)^2` and `(sqrt(distance_sq(o,p))+radius)^2`. Their global bounds and strict uniqueness have passed the independent strict radial checkpoint. The observer-on-circle case has minimum0 and remains included.
- Actual angle interface: `angle_measure::ray_angle(o,p,q)` uses nonzero arms; `segment_length(p,q)` is positive. The cosine law and angle-order proofs use those interfaces directly. For an interior observer, proximity in angle to the center direction gives a greater distance. For an external observer the far branch has that order and the near branch has the reverse order.
- External branch meaning: with positive power `distance_sq(o,p)-radius^2`, the other circle point on the same ray has affine parameter `power/distance_sq(p,q)`. The near/far inequalities put that parameter above/below1, and equality fixes q. A proved second-parameter classification rules out any third parameter. The geometric construction, actual angular order and complete second-ray-point classification have now passed the combined strict checkpoint, including interior4<8 and tangent-inclusive2<4<8 concrete uses. Later all-ray weak order characterizations and radial placement lemmas have Session acceptance and await the source integration gates.
- Source boundary: squared-distance comparisons alone are not counted as complete III.7/III.8. Keep the source clauses for diameter placement, extrema, angular order and the unique opposite-side equal partner together at integration. The source wording “nearer” is interpreted in the angular sense noted by the translation's footnote.

- III.7 completion evidence: `.draft/book03-first-seven-checkpoint/receipt.json` checks44 target declarations. `proposition_07_diameter` includes the closed-disk boundary; `proposition_07_greatest_passes_center` proves actual finite-segment incidence. The minimum, maximum, angular-order and two equal-partner clauses are checked together.


### Equal chord lengths and perpendicular distances (III.14 canonical)

The existing `geometry::main::is_foot` permits a foot equal to the circle center, so diameters are included. Chord midpoint and perpendicular foot are equivalent; the common identity is `distance_sq(o,m)+distance_sq(a,b)/4=radius^2`. Both source implications use actual Euclidean distances and the `are_chords_equidistant_from_center` definition. Ordinary chords, diameters, and a converse use passed independent and joint strict checkpoints. III.14 and III.Def4 are canonical; III.15 and III.Def5 are checked in the same 94-declaration joint gate. See `translation_records/book03-proposition14-plan.json`.


### Selected arcs and filled circular segments (III.20–23, verified drafts)

`chosen_arc_angle` distinguishes minor, semicircular and major intercepted arcs; its reflex branch is retained. III.20–22 passed the 140-declaration joint circle/tangent gate. `circular_segment_region` is the intersection of a closed disk with a selected chord half-plane, so it includes both its interior and boundary. `is_angle_in_circular_segment` requires a circumference vertex strictly on the selected side and nonzero arms. `are_similar_circular_segments` supplies actual equal-angle witnesses; III.21 proves independence of the chosen vertices. III.23 identifies the entire filled regions for a common chord and side. The independent III.23 gate passed46 declarations; joint integration of III.Def6/8/11 and III.20–23 passed154 declarations. Proof-liveness audit and canonical promotion remain pending. These drafts do not yet change the canonical counts above.

### Rigid motions for superposition (III.24 in progress)

`plane_rigid_motion(p,t,co,si,orientation)` applies reflection, rotation and translation. Its domain requires unit rotation coefficients and orientation±1. The explicit inverse, preservation of squared distances, signed determinant, inner product and circle incidence, and the equal-chord endpoint constructor have passed a 19-declaration strict file gate with concrete rotation/reflection, half-plane and translated-chord consumers. Angle preservation has Session acceptance in the full circle context.

`is_plane_rigid_motion_between_regions` means membership equivalence for every point under this motion. The inverse gives onto correspondence, and distance preservation plus injectivity supplies actual region congruence. III.24's dependency order is equal-chord endpoint construction → side/angle preservation → circular-segment transport → III.23 region equality. The transport lemma, source III.24 and an actual opposite-semicircle congruence consumer have Session acceptance; the independent source file gate passed65 declarations with stable hashes. This interface does not replace congruence by scalar area equality.

### A strict selected-arc point (III.25 prerequisite)

`selected_arc_point(o,a,b,radius,side)` uses the normalized chord normal. Positive radius, positive squared chord length and side±1 are guarded in its domain. The circle-incidence and strict selected-side certificate and translated minor/major consumer have Session acceptance. The center(3,4), radius5, chord(0,8)–(6,8) example yields(3,9) and(3,-1). The nine-declaration independent certificate gate passed. The earlier constructor-only checkpoint failed because it omitted the distance_sq definition release; the full gate supplies that context. Arc-only center/radius reconstruction and recovery of the original supporting circle have Session acceptance, with a21-declaration independent gate running. Source center-location consequences remain.

`is_circular_arc_with_chord(arc,a,b)` keeps center/radius/side witnesses inside its definition. `proposition_25_circle_completion` computes a center from a noncollinear boundary triple and a positive radius, and proves the entire arc lies on the result. `proposition_25_recovers_original_circle` checks that this construction recovers any given supporting-circle representation. `selected_arc_point_equidistant` supplies the perpendicular-bisector ingredient for the remaining source cases; it currently has Session acceptance only.

### Actual cut-line areas and acute triangles (II.2–13 current drafts)

The current 1.1.1-beta drafts use actual positive-area rectangles and I.46 squares, with square areas related to squared side lengths. Strict segment cuts and external extensions retain endpoint inequalities, orientation independence and midpoint restrictions. II.2–11 passed the combined78-declaration independent gate with stable hashes; II.12 source-angle construction and consumers passed the retained Session, with an independent95-declaration gate running. These remain drafts until full original-context integration and source audit.

`orthogonal_projection_to_line` constructs the foot and affine parameter; negative parameters yield the outside-foot case of II.12. For II.13, positivity of the endpoint projections proves the parameter lies strictly between0 and1. The source-facing `is_acute_triangle` definition includes a genuine triangle, explicit distinct vertices for angle-function domains, and all three ray angles strictly below pi/2. The selected-angle criterion alone is not substituted for a fully acute triangle. Positive/negative dot products are linked to the angle measures by proved bridge theorems. The current II.13 actual construction and source wrapper have Session acceptance; independent validation and concrete consumers are being completed.

II.1 now has a retained-Session arbitrary finite-cut construction: `is_strict_finite_segment_partition` requires fixed endpoints, ordered affine cut points and strictly increasing consecutive parameters; `is_finite_piece_rectangle_family` certifies actual rectangles with positive heights matching each subsegment and a named indexed area function. Ordinary induction proves the arbitrary-length area sum. Coordinate rectangle representatives may share an origin: no claim of a non-overlapping physical dissection of those representatives is made. Nonuniform/reversed consumers and zero-width rejection pass; full original integration is pending. Fixed two- or three-piece instances alone would not complete the source scope. II.14 and I.45 still require an actual finite simple polygon region/decomposition and its area interface. A bare positive scalar or a triangle-only construction does not complete those source propositions.

Polygon-area prerequisites (current draft): closed triangle and strict interior are actual barycentric point regions; standalone11 gate passes. Retained polygon Session also checks convexity, nonempty interior, a single-triangle decomposition, overlap exclusion, and a strict edge cut into two proper triangles with disjoint interiors and determinant ratios. Coverage and unsigned area additivity are separate obligations; finite simple polygon triangulation and full I.45/II.14 remain pending. No source proposition completion is inferred from these primitives.

### Polygon inscribed in a circle / circle circumscribed about a polygon (IV.Def3, IV.Def6)

- One geometric incidence relation describes both source directions: a finite simple polygonal boundary has every indexed vertex on the positive-radius circle. Use a `prop`; the circle itself remains the existing set-valued `geometry::main::circle`.
- Reuse the verified draft simple-cycle interface, with at least three nonrepeated vertices, proper edges and no intersections except common endpoints. Reuse `circle_contact::is_chord` for IV.Def7 rather than inventing a second chord definition.
- `polygon_inscribed_in_circle(n, vertices, center, radius)` is a draft API pending positive/negative consumers and integration. IV.Def6 maps to the same relation with its circle described first; it does not require a duplicate predicate.
- Probe: a proper three-vertex unit-circle triangle; nearest boundary: the same vertices on a wrong-radius circle. Tangency and polygon containment for IV.Def1,2,4,5 remain separate obligations.
- Source: Fitzpatrick2008, PDF page110 (zero-based109), lines4529–4540. This boundary-incidence definition does not claim polygon triangulation or area independence.

### Given-segment chord construction (IV.1)

Use the existing proper-chord relation and segment congruence. The positive-radius circle and distinct given segment endpoints are explicit; the squared length bound `distance_sq(u,v) <= 4*radius^2` includes equality. The analytic witness uses half the length and the nonnegative square-root height. Current draft theorem and translated-center/diameter consumers pass the retained Session; an overlong segment rejects the exact diameter premise. Canonical module integration and grouped validation remain pending; see `translation_records/book04-proposition01-draft.json`.

### Book IV triangle incircle interface (draft, 2026-10-18)

`circle_inscribed_in_triangle(a,b,c,center,radius)` reuses the proper-triangle interior, finite segment membership and the existing BookIII `is_tangent_line_at` relation. The positive radius is typed; the center is interior; three witnesses belong to the actual three side segments and certify tangency to their supporting lines. This is the triangle specialization needed by IV.4/IV.3, not completion of the general polygon definitions. The definition and an exclusion of the 3–4–5 triangle excircle with center (3,-3), radius3 have Session acceptance. The general triangle incircle construction IV.4 and its actual consumer have passed the retained Session and a 53-declaration strict checkpoint; canonical integration remains pending. Evidence: proof_journals/resume-2026-10-17.json, `book04_incircle_current`.


### Book IV square circles and golden triangle (draft)

IV.8 and IV.9 accept the existing square predicate without extra shape premises. The diagonal midpoint is the center; IV.8 uses four finite side-midpoint contacts and perpendicular radii, while IV.9 puts all four vertices on the circle. Both constructions and rotated-square consumers have strict Session acceptance, with collapsed-square controls rejected. Their combined clean checkpoint is `../.draft/resume-2026-10-17/book04-square-circles-checkpoint/` (re-gated 16/16 on pinned `b74d9f0c7e11` after releasing `geometry::main::circle` before `is_tangent_line_at`). The parallel repaired package `book04-IV8-IV10-repaired-checkpoint` remains 29/29.

`is_golden_triangle(a,b,d)` includes a proper triangle, distinct angle arms, equal squared waist lengths, the cosine domains, and two actual principal-arccosine equalities saying that each base angle is twice the apex angle. IV.10 constructs such a triangle using the II.11 golden parameter. The complete theorem and consumer have strict Session acceptance; the full-geometry clean checkpoint is `../.draft/resume-2026-10-17/book04-golden-triangle-checkpoint/` (metric certificate re-gated 20/20 with explicit `d-a` coordinate differences). Neither draft changes canonical completion counts.

### Book IV regular pentagon (in progress)

IV.11 must return a simple five-vertex cycle inscribed in the given positive-radius circle, with equal sides and equal interior angles. Five equal chords alone are insufficient: a star order must be excluded. The planned normalized coordinates are `(0,1)`, `(-(1+t)*h,t/2)`, `(-h,-(1+t)/2)`, `(h,-(1+t)/2)`, `((1+t)*h,t/2)`, where `0<t<1`, `t^2=1-t`, and `h>0`, `h^2=(2-t)/4`. Use the existing golden parameter and positive-height construction, prove circle/side/diagonal distances and strict same-side determinants, then connect them to the existing simple-cycle interface and angle congruence. Finally transport by positive scaling and translation. No new primitive polygon or angle assumption is authorized by this plan.

### Perpendicular height and equal-height ratios (VI.Def3 / VI.1)

`has_triangle_perpendicular_height` and `has_parallelogram_perpendicular_height` require actual nondegenerate figures, positive height, and a perpendicular foot on the base line with squared distance equal to height squared. The foot may lie outside the finite base. The determinant identity derives triangle area = base×height/2 and parallelogram area = base×height. VI.1 uses these to obtain quotient equality and the existing all-equimultiples comparison predicate. Both clauses and an outside-foot consumer pass strict29 with stable hashes (`book06-proposition01-checkpoint-v2`). The separately accepted triangle-height existence/uniqueness and `have fn ... by exist!` declarations still await their grouped checkpoint. These are local drafts, not a completed canonical BookVI module.

### VI.1–VI.7 checked draft boundary

Independent strict checkpoints for VI.1–VI.7 passed 29, 30, 31, 24, 28, 28 and 35 statements, respectively, with stable source and pinned executable hashes. VI.1 uses actual heights and areas; VI.2 strict interior parallel cuts; VI.3 internal angle bisectors; VI.4 AAA implies actual side ratios; VI.5 corresponding side ratios imply AAA; VI.6 adjacent side ratios and the included angle imply AAA; VI.7 a nonincluded equal angle and side ratio imply AAA under the source same-acute/nonacute branch. Every ratio theorem has a quotient and necessary numerical equimultiple form. Actual geometric construction consumers accompany them. Checkpoint receipts are under `../.draft/resume-2026-10-17/book06-propositionNN-checkpoint/` (VI.1 uses the `-v2` directory).

Boundary evidence includes corrected VI.2 endpoint9154, VI.3 nonbisector9156 and endpoint9157, VI.4 zero scale9170, VI.5 collapsed base9186, and VI.6 wrong included angle9187. Earlier failed controls that stopped before their intended premise are retained as failed attempts, not boundary evidence. These remain drafts: canonical VI integration and final chapter proof-liveness review are pending. No abstract Book V magnitude model is added. VI.7 keeps the original same-acute/nonacute branch condition in principal-angle measures; its complete independent checkpoint passed. Mixed-branch negative9201 reaches the exact branch premise; positive counterexample9202 proves the corresponding SSA triangles are not similar.

VI.8 independent checkpoint with 3-4-5 consumer passed 27 statements on pinned `b74d9f0c7e11` (altitude foot interior, three AAA similarities ABD~CBA / ACD~BCA / ABD~CAD, and mean-proportional lengths). VI.9–VI.13 construction package (cut prescribed part, similar cut, third/fourth/mean proportional) each passed independent strict gates with positive consumers on the same pinned binary. VI.14 forward/converse (equal equiangular parallelograms ↔ reciprocal adjacent-side squared-length products) passed an independent gate; consumers and non-squared length packaging remain. VI.1 height/area checkpoint was re-gated 29/29 after releasing `area::triangle_area`.

### VI.15–VI.31 triangle/parallelogram ratio package (draft, 2026-10-21)

On pinned `b74d9f0c7e11`, independent strict gates closed the triangle/parallelogram ratio core: VI.15 (equal triangles + one congruent angle ↔ reciprocal adjacent squared sides), VI.16 (four proportional segments ↔ equal extreme/mean rectangles), VI.17 (three proportional ↔ rectangle extremes = square mean), VI.19 (similar-triangle area = square of corresponding side, plus scale/equal-area/any-side packages), VI.21 (similarity transitive/symmetric/reflexive and congruent⇒similar), VI.23 (equiangular parallelograms area–side cross-product, quotients, scale, equal-sides⇒equal-area), and VI.31 (similar triangles on the sides of a right triangle: areas on legs add to the hypotenuse). Checkpoints under `../.draft/resume-2026-10-17/book06-proposition{15,16,17,19,21,23,31}-checkpoint/`. Deferred as interface-heavy: VI.18/20/22 similar polygons; VI.24–30 parallelograms about a diameter / constructions; VI.32 SSA-like; VI.33 circle arcs. Canonical Book VI promotion remains open. No new trust.
