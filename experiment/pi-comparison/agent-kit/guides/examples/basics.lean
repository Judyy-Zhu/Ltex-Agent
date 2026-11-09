import Mathlib.Basic.Real.Basic

def training_shift (x : ℝ) : ℝ := x + 2
def training_fixed (x : ℝ) : Prop := x = 7

theorem training_unfold (x : ℝ) : training_shift x = x + 2 := by
  rfl

theorem training_condition (x : ℝ) (h : training_fixed x) : x = 7 := by
  exact h

theorem training_witness (x : ℝ) : ∃ y : ℝ, y = training_shift x := by
  exact ⟨training_shift x, rfl⟩

theorem training_pair (p : ℝ × ℝ) : (p.1, p.2) = p := by
  rfl
