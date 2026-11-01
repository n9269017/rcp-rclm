import Mathlib

macro "q" : tactic => `(tactic| omega)

theorem phase17_d69e7a698f7d392c9d7249ed (n : Nat) : n + 1 <= n + 2 := by
  q

#print axioms phase17_d69e7a698f7d392c9d7249ed
