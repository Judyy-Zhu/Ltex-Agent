import Mathlib.Analysis.Real.Sqrt
import Mathlib.Tactic.Ring

namespace TrainingStructure

def positive (x : ℝ) : Prop := 0 < x

theorem fold (x : ℝ) (h : 0 < x) : positive x := by
  exact h

theorem branch (x : ℝ) (h : x = 0 ∨ x = 1) : x * (x - 1) = 0 := by
  rcases h with h | h <;> simp [h]

theorem square_nonnegative (x : ℝ) : 0 ≤ x ^ 2 := by
  by_contra h
  exact h (sq_nonneg x)

theorem compound_witness (x : ℝ) : ∃ y : ℝ, y = x + 1 ∧ y - x = 1 := by
  refine ⟨x + 1, rfl, ?_⟩
  ring

theorem root_bridge (u v : ℝ) (_hu : 0 ≤ u) (_hv : 0 ≤ v) (h : u = v) :
    Real.sqrt u = Real.sqrt v := by
  exact congrArg Real.sqrt h

theorem add_zero_fact (x : ℝ) : x + 0 = x := by
  exact add_zero x

example : (6 : ℝ) + 0 = 6 := add_zero_fact 6

end TrainingStructure
