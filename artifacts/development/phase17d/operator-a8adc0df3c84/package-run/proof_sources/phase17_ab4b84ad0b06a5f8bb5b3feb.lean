import Mathlib

macro "q" : tactic => `(tactic| omega)

theorem phase17_ab4b84ad0b06a5f8bb5b3feb (n : Nat) : 0 <= n := by
  q

#print axioms phase17_ab4b84ad0b06a5f8bb5b3feb
