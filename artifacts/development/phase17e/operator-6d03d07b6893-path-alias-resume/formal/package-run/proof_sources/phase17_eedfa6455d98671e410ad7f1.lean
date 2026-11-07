import Mathlib

macro "q" : tactic => `(tactic| omega)

theorem phase17_eedfa6455d98671e410ad7f1 (n : Nat) : 0 < n + 1 := by
  q

#print axioms phase17_eedfa6455d98671e410ad7f1
