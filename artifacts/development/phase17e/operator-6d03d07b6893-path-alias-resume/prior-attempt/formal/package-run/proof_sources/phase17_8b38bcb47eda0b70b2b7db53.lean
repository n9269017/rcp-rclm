import Mathlib

macro "q" : tactic => `(tactic| omega)

theorem phase17_8b38bcb47eda0b70b2b7db53 (n : Nat) : n < n + 5 := by
  q

#print axioms phase17_8b38bcb47eda0b70b2b7db53
