import Mathlib

macro "z" : tactic => `(tactic| simp)

theorem phase17_aa812b822aba1af8a0a8ee21 (n : Nat) : n + 0 = n := by
  z

#print axioms phase17_aa812b822aba1af8a0a8ee21
