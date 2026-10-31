import Mathlib

macro "q" : tactic => `(tactic| omega)

theorem phase17_95bcb898619e04c7c7a8dc7c (n : Nat) : n < n + 1 := by
  q

#print axioms phase17_95bcb898619e04c7c7a8dc7c
