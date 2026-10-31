import Mathlib

theorem phase17_40d58c7bcb7e075de355931f (x : Nat) : x + 2 < x + 3 := by
  have h : 2 < 3 := by omega
  exact Nat.add_lt_add_left h x

#print axioms phase17_40d58c7bcb7e075de355931f
