# Minimal plane-algebra seed

Both formal languages implement the mathematical interface real-plane-algebra-v1. Sources are plane.lean and plane.lit; interface.json is the shared specification.

Seven names are provided: GeoPoint is a real ordered pair; geo_point constructs a point; geo_x/geo_y are coordinate projections; geo_vec(a,b) returns b minus a, directed from a to b; geo_dot is the ordinary 2D dot product; geo_det(u,v) is u.x*v.y - u.y*v.x. Argument order fixes the determinant sign.

This seed is a two-dimensional starting point. Solid-geometry tasks need explicitly modeled higher-dimensional carriers; do not reinterpret a 2D pair as a 3D point. Higher-dimensional foundation alignment must be reviewed/frozen at the appropriate stage.

For coordinatewise point equality, Lean can use Prod.ext. Litex can use by thm tuple_equal_from_coordinates(left,right); the native release thm spelling of this same rule is also permitted. The rule still verifies the complete finite domain and each coordinate equality; it does not publish an unchecked equality. State function expansions, coordinates and scalar intermediate equalities explicitly before connecting Litex point equalities.

These are technical interfaces for the analytic model. Each approved foundation provides real arithmetic, order, square roots and allowed tactics. The seed supplies no distance, circle, collinearity, triangle, congruence, similarity, midpoint, circle-intersection result or Euclid proposition proof.

## Loading and final assembly

Preparation copies the assigned-language seed to seed.lean/seed.lit in input and the shared interface to seed-interface.json. foundation.json records exported names, paths and SHA-256 hashes.

Session/REPL startup loads the frozen seed and own-language published predecessors. Restart loads those same files and replays accepted current-task source. Seed declarations do not enter the agent acceptance journal or count as agent-built definitions.

Read the interface and assigned-language seed source; do not redeclare their names. read_library(["accepted_prefix"]) returns frozen seed + predecessors + acceptance journal, including required Lean imports. write_source(base="accepted",content="") saves that prefix directly as a complete final module without repeatedly sending the entire library through the model. Final checking verifies the unchanged prefix; using the seed in-session does not permit replacing it in the saved file.

Seed authoring/manual preparation is setup cost. In-task loading, reloading and replay count toward solve time; seed reads count toward model input usage. The seed does not automatically complete any source task, including Book I definition 1.

## Verification scope

test_seeds.py checks universal coordinate/vector/dot-product/determinant properties in both real verifiers, numeric orientation/sign, reload after restart, tampering rejection and false-equality rejection. This checks the seven technical interfaces, not the complete equivalence of all transitive Lean imports and Litex builtins.
