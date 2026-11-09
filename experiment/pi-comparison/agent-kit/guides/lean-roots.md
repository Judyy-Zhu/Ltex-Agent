# Real square roots and polynomial reasoning: development topic U09

Only Mathlib.Analysis.Real.Sqrt, Mathlib.Tactic.Ring, Mathlib.Tactic.Linarith, Mathlib.Tactic.NormNum, Mathlib.Tactic.Positivity and Mathlib.Tactic.FieldSimp are approved here. The REPL loads them once; increments must not import them again. The example below is a standalone file. Do not import a historical geometry library or the Mathlib umbrella module. Formal transitive-import auditing remains pending.

Real.sqrt is total on reals and returns zero on negative inputs. Prove nonnegativity when the mathematical model requires it. Useful interfaces are Real.sqrt_nonneg x, Real.sq_sqrt (h : 0 ≤ x), and Real.sqrt_pos.2 (h : 0 < x). Do not assume sqrt(x²)=x for arbitrary real x.

The following standalone teaching examples are not answers to Euclid propositions:

```lean
import Mathlib.Analysis.Real.Sqrt
import Mathlib.Tactic.Linarith

theorem training_root (x : ℝ) (h : 0 ≤ x) :
    Real.sqrt x ^ 2 = x := by
  exact Real.sq_sqrt h

theorem training_square_zero (x : ℝ) (h : x ^ 2 = 0) : x = 0 := by
  nlinarith [sq_nonneg x]
```

For nonlinear equalities, establish checked root-square equalities before using nlinarith. Use ring for polynomial identities. rcases splits existentials/conjunctions; by_cases h : P and by_contra h support cases/contradiction. Prod.ext reduces pair equality to coordinates. These tools prove the original target; they do not authorize stronger premises.
