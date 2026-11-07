import Mathlib

macro "q" : tactic => `(tactic| omega)

theorem phase17_4b6c1b29c9bb833d61e2f656 (n : Nat) : n < n + 2 := by
  q

#print axioms phase17_4b6c1b29c9bb833d61e2f656
