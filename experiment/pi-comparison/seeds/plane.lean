import Mathlib.Analysis.Real.Sqrt
import Mathlib.Tactic.Ring
import Mathlib.Tactic.Linarith
import Mathlib.Tactic.NormNum
import Mathlib.Tactic.Positivity
import Mathlib.Tactic.FieldSimp

-- Fixed technical interfaces for the real coordinate plane.
abbrev GeoPoint := ℝ × ℝ

def geo_point (x y : ℝ) : GeoPoint := (x, y)

def geo_x (p : GeoPoint) : ℝ := p.1

def geo_y (p : GeoPoint) : ℝ := p.2

-- The vector directed from a to b is b - a.
def geo_vec (a b : GeoPoint) : GeoPoint :=
  (b.1 - a.1, b.2 - a.2)

def geo_dot (u v : GeoPoint) : ℝ :=
  u.1 * v.1 + u.2 * v.2

def geo_det (u v : GeoPoint) : ℝ :=
  u.1 * v.2 - u.2 * v.1
