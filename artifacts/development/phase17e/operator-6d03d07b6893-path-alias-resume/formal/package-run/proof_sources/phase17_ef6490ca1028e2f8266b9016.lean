import Mathlib

macro "q" : tactic => `(tactic| omega)

theorem phase17_ef6490ca1028e2f8266b9016 (n : Nat) : n <= n + 4 := by
  q

#print axioms phase17_ef6490ca1028e2f8266b9016
