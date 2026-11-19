import Mathlib

macro "q" : tactic => `(tactic| omega)

theorem phase17_a6f303464a35370717f5b43b (n : Nat) : n <= n := by
  q

#print axioms phase17_a6f303464a35370717f5b43b
