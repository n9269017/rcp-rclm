import RcpRclmFormalCoreV4
import Mathlib.Tactic
import Mathlib.Data.Finset.Filter

namespace Phase17TaskMeaning

structure Program where
  family : Nat
  variant : Nat
  a : Int
  b : Int
  deriving DecidableEq, Repr

def insertInt (a : Int) : List Int → List Int
  | [] => [a]
  | b :: bs => if a ≤ b then a :: b :: bs else b :: insertInt a bs

def sortInts : List Int → List Int
  | [] => []
  | a :: rest => insertInt a (sortInts rest)

/-- Independent Lean semantics of the unchanged four-integer mutation DSL. -/
def execute (p : Program) (xs : List Int) : List Int :=
  let v := p.variant + 1
  let vi : Int := Int.ofNat v
  let x := fun (i : Nat) => xs.getD i 0
  match p.family with
  | 0 => xs.map (fun z => vi * z + p.a - p.b)
  | 1 => (List.range 4).map (fun i => x ((i + v + 1) % 4) + p.a * Int.ofNat (i + 1) + p.b)
  | 2 => (List.range 4).map (fun i => x ((i + v) % 4) + if i = 0 then p.a else 0)
  | 3 => (List.range 4).map (fun i => xs.sum + p.a + Int.ofNat (v * (i + 1) * (i + 2) / 2) - p.b * Int.ofNat (i + 1))
  | 4 => [x 0 + p.a, x 1 * vi, x 2 - p.b, x 3 + x 0 * vi]
  | 5 => (List.range 4).map (fun i => x ((i * v + p.b.natAbs) % 4))
  | 6 => [x 0 + x 1 + p.a, x 1 - x 2 + p.b, x 2 * vi, x 3 + p.a - p.b]
  | 7 => sortInts (xs.map (fun z => z + p.a * vi - p.b))
  | _ => []

-- State projection is supplied by the external physical evaluator. These proofs
-- do not establish that arbitrary self-reported observations describe a model.
structure ObservationState where
  proofs : List (String × String × String)
  programs : List (String × Program)

structure Meaning where
  check : ObservationState → Bool
  holds : ObservationState → Prop
  sound : ∀ s, check s = true → holds s

def theoremMeaning (task source decode : String) (P : Prop) (proof : P) : Meaning where
  check := fun s => decide ((task, source, decode) ∈ s.proofs)
  holds := fun s => (task, source, decode) ∈ s.proofs ∧ P
  sound := by
    intro s h
    exact ⟨of_decide_eq_true h, proof⟩

structure VectorContract where
  family : Nat
  requiredProgram : Option String
  inputs : List (List Int)
  targets : List (List Int)

def vectorMeaning (t : VectorContract) : Meaning where
  check := fun s => s.programs.any (fun e => decide
    (e.2.family = t.family ∧
     (t.requiredProgram = none ∨ t.requiredProgram = some e.1) ∧
     t.inputs.map (execute e.2) = t.targets))
  holds := fun s => ∃ e ∈ s.programs,
    e.2.family = t.family ∧
    (t.requiredProgram = none ∨ t.requiredProgram = some e.1) ∧
    t.inputs.map (execute e.2) = t.targets
  sound := by
    intro s h
    simpa only [List.any_eq_true, decide_eq_true_eq] using h

def rejectMeaning : Meaning where
  check := fun _ => false
  holds := fun _ => False
  sound := by intro s h; cases h

def checkedFrontier (declared : Finset Nat) (catalog : Nat → Meaning)
    (s : ObservationState) : Finset Nat :=
  declared.filter (fun t => (catalog t).check s = true)

theorem checked_frontier_sound (declared : Finset Nat) (catalog : Nat → Meaning)
    (s : ObservationState) {task : Nat}
    (member : task ∈ checkedFrontier declared catalog s) : (catalog task).holds s := by
  exact (catalog task).sound s (Finset.mem_filter.mp member).2

open RcpRclmFormalCoreV2 RcpRclmFormalCoreV3

-- Supplies the ACTUAL frontier/solves/frontierSound fields of the immutable root.
-- All other kernel fields and their adequacy remain obligations of the caller.
def attachTaskSemantics
    {State Update BaseCertificate Protected ResidualIndex Generator Proposal PackageHash : Type*}
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    (other : Learned.FrontierKernel (Task := Nat) (Generator := Generator)
      (Proposal := Proposal) (PackageHash := PackageHash) base)
    (observe : State → ObservationState) (declared : State → Finset Nat)
    (catalog : Nat → Meaning) :
    Learned.FrontierKernel (Task := Nat) (Generator := Generator)
      (Proposal := Proposal) (PackageHash := PackageHash) base :=
  { other with
    frontier := fun s => checkedFrontier (declared s) catalog (observe s)
    solves := fun s task => (catalog task).holds (observe s)
    frontierSound := by
      intro s task member
      exact checked_frontier_sound (declared s) catalog (observe s) member }

theorem attached_root_frontier_sound
    {State Update BaseCertificate Protected ResidualIndex Generator Proposal PackageHash : Type*}
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    (other : Learned.FrontierKernel (Task := Nat) (Generator := Generator)
      (Proposal := Proposal) (PackageHash := PackageHash) base)
    (observe : State → ObservationState) (declared : State → Finset Nat)
    (catalog : Nat → Meaning) {s : State} {task : Nat}
    (member : task ∈ (attachTaskSemantics other observe declared catalog).frontier s) :
    (attachTaskSemantics other observe declared catalog).solves s task :=
  (attachTaskSemantics other observe declared catalog).frontierSound member

end Phase17TaskMeaning

namespace Phase17TaskMeaning
set_option maxRecDepth 16384
set_option maxHeartbeats 4000000
-- Independently recomputed catalog SHA256: 0e31d56ea5c44be47e5ad3b3319efdc0e82e5eccf58fe56f98995ca5a1bcaa89
namespace Inherited0
theorem phase17_c4df74a5676f3be58d91172a (a b : Nat) (h : a + 2 <= b) : a < b := by
  omega


def Target : Prop := ∀ (a b : Nat) (_h : a + 2 <= b), a < b
end Inherited0
theorem inherited_0 : Inherited0.Target := Inherited0.phase17_c4df74a5676f3be58d91172a
namespace Inherited1
theorem phase17_90f3310a3ade240161a9ccfe : (7 : Nat) = 7 := by
  rfl


def Target : Prop := (7 : Nat) = 7
end Inherited1
theorem inherited_1 : Inherited1.Target := Inherited1.phase17_90f3310a3ade240161a9ccfe
namespace Inherited2
theorem phase17_aa812b822aba1af8a0a8ee21 (n : Nat) : n + 0 = n := by
  simp


def Target : Prop := ∀ (n : Nat), n + 0 = n
end Inherited2
theorem inherited_2 : Inherited2.Target := Inherited2.phase17_aa812b822aba1af8a0a8ee21
namespace Inherited3
theorem phase17_a6f303464a35370717f5b43b (n : Nat) : n <= n := by
  omega


def Target : Prop := ∀ (n : Nat), n <= n
end Inherited3
theorem inherited_3 : Inherited3.Target := Inherited3.phase17_a6f303464a35370717f5b43b
namespace Inherited4
theorem phase17_ab4b84ad0b06a5f8bb5b3feb (n : Nat) : 0 <= n := by
  omega


def Target : Prop := ∀ (n : Nat), 0 <= n
end Inherited4
theorem inherited_4 : Inherited4.Target := Inherited4.phase17_ab4b84ad0b06a5f8bb5b3feb
namespace Inherited5
theorem phase17_95bcb898619e04c7c7a8dc7c (n : Nat) : n < n + 1 := by
  omega


def Target : Prop := ∀ (n : Nat), n < n + 1
end Inherited5
theorem inherited_5 : Inherited5.Target := Inherited5.phase17_95bcb898619e04c7c7a8dc7c
namespace Inherited6
theorem phase17_4b6c1b29c9bb833d61e2f656 (n : Nat) : n < n + 2 := by
  omega


def Target : Prop := ∀ (n : Nat), n < n + 2
end Inherited6
theorem inherited_6 : Inherited6.Target := Inherited6.phase17_4b6c1b29c9bb833d61e2f656
namespace Inherited7
theorem phase17_eedfa6455d98671e410ad7f1 (n : Nat) : 0 < n + 1 := by
  omega


def Target : Prop := ∀ (n : Nat), 0 < n + 1
end Inherited7
theorem inherited_7 : Inherited7.Target := Inherited7.phase17_eedfa6455d98671e410ad7f1
namespace Inherited8
theorem phase17_8b38bcb47eda0b70b2b7db53 (n : Nat) : n < n + 5 := by
  omega


def Target : Prop := ∀ (n : Nat), n < n + 5
end Inherited8
theorem inherited_8 : Inherited8.Target := Inherited8.phase17_8b38bcb47eda0b70b2b7db53
namespace Inherited9
theorem phase17_d69e7a698f7d392c9d7249ed (n : Nat) : n + 1 <= n + 2 := by
  omega


def Target : Prop := ∀ (n : Nat), n + 1 <= n + 2
end Inherited9
theorem inherited_9 : Inherited9.Target := Inherited9.phase17_d69e7a698f7d392c9d7249ed
namespace Inherited10
theorem phase17_ef6490ca1028e2f8266b9016 (n : Nat) : n <= n + 4 := by
  omega


def Target : Prop := ∀ (n : Nat), n <= n + 4
end Inherited10
theorem inherited_10 : Inherited10.Target := Inherited10.phase17_ef6490ca1028e2f8266b9016
namespace Inherited11
theorem phase17_40d58c7bcb7e075de355931f (x : Nat) : x + 2 < x + 3 := by
  have h : 2 < 3 := by omega
  exact Nat.add_lt_add_left h x


def Target : Prop := ∀ (x : Nat), x + 2 < x + 3
end Inherited11
theorem inherited_11 : Inherited11.Target := Inherited11.phase17_40d58c7bcb7e075de355931f
namespace Inherited12
def phase17Affine (x : Int) : Int := (-2) * x + (-7)
theorem phase17_ea08af8580910d01fc67b2a9 (x : Int) : phase17Affine x = (-2) * x + (-7) := by
  rfl


def Target : Prop := ∀ (x : Int), phase17Affine x = (-2) * x + (-7)
end Inherited12
theorem inherited_12 : Inherited12.Target := Inherited12.phase17_ea08af8580910d01fc67b2a9
def catalog : Nat → Meaning
  | 0 => theoremMeaning "lean.phase10.heldout.linear_gap" "8410efe3df3b56346023950e05536e31d3ed1436ba189e5d081eca7ecae3c2a3" "06b1bfcdd4b4d556af71bc4b9ad25705bdccc8769043bd28693b0494b1938da2" Inherited0.Target inherited_0
  | 1 => theoremMeaning "lean.phase10.protected.reflexive_seven" "2923a5127ebb2dce77b93f25bfacd4ff8d23778e9c045de8ddabed164da927fb" "5392f810f0edaae2646222e27e4ba85dd09365294490637453dd5afc4086fd0a" Inherited1.Target inherited_1
  | 2 => theoremMeaning "lean.phase11.heldout.add_zero_macro" "f17a5ce95e825ce7b1f160ea01b9af617754a0599dc79e598631d760d2737662" "047c1526c8be605c14dbb1ea9e7fdf798d960958c44b0c54e2c3b20b72e5e8f1" Inherited2.Target inherited_2
  | 3 => theoremMeaning "lean.phase12.generation1.le_refl_macro" "29a44f8162d395296df0b6a3695ef84d4c53754badd4fc40ac572339afe81343" "64b40cfc1967d7c61ff59e88447dda1c08214b7d4f6854ab21dfce92a58ef432" Inherited3.Target inherited_3
  | 4 => theoremMeaning "lean.phase12.generation2.zero_le_macro" "2ccfa1a6941344d7717e88514799bc03b443551733ef5f6611568e3b709d11ad" "810b78e6006b0587963765efe4a87f9e1cf374126d4cdbee47d22b3483200d2c" Inherited4.Target inherited_4
  | 5 => theoremMeaning "lean.phase12.generation3.lt_succ_planner_macro" "ef24333062d901e017672cd228a08665df7fe26cd039bd30af051edfe0bf1f15" "0a157eea313f12a5c66a407b2ab782cb22f9e6c4a49d5c231ccb29d5854b2caf" Inherited5.Target inherited_5
  | 6 => theoremMeaning "lean.phase12.generation4.lt_add_two_adapter_macro" "60e6bbca487b6807d97338b84253481f2884d25644d8f9274b716799a504d269" "32fae1c4dd17a247879289f9b8f1b4e9988f76195a101abaab29f579438c1a6e" Inherited6.Target inherited_6
  | 7 => theoremMeaning "lean.phase14.generation5_zero_lt_succ" "00a2b7cac3e41ec4f7f10326f38e7876550a166956b3133ab43b60a71d167d77" "c548cc466699b3891f55e2ea9b89cb03ffa95345e797b85abd1b5ccef11fab8c" Inherited7.Target inherited_7
  | 8 => theoremMeaning "lean.phase14.generation6_lt_add_five" "5f3d24df1725dd940f10edd1a1fc857d3e0a0a74aee4af2970c17e87e88e1387" "d81b0c93645b5d1fe8038d6bdc5bf36bc7ce66f65c98e5e0e437351553f5a771" Inherited8.Target inherited_8
  | 9 => theoremMeaning "lean.phase14.generation7_succ_le_add_two" "e674398024eb21a38ba89194a88e47bdb9e76adc711744020733036883991f1e" "fcfda49e8ce97e014155ca5d8a1f66e5b74eadad09c53517ac8829cc3dffb910" Inherited9.Target inherited_9
  | 10 => theoremMeaning "lean.phase14.generation8_le_add_four" "e213d8c64ed0c514b3be2f8e1dabde63c3b432d738e0a603140a3c948ba6ddfa" "f08827e9b291f026e450572beb47983bb520419f39f515a22f1338dfa0bece31" Inherited10.Target inherited_10
  | 11 => theoremMeaning "lean.phase15.dynamic.multistep.4a7a415bcd169bb8" "a269501136730bdcde4b1ab63efdb521ebb95bf9007b4dce32025cd893b3f830" "f34f041f82c60bc693c28bcee6677254696d0988d8ab656af003131fdf93d5b8" Inherited11.Target inherited_11
  | 12 => vectorMeaning { family := 0, requiredProgram := (some "7d98001be0bd64487cb44f7db6f741b3e0436eec4cc0c4b0d74f5e6f774f2c1a"), inputs := [[(-4), 14, (-5), (-11)]], targets := [[(-6), 66, (-10), (-34)]] }
  | 13 => vectorMeaning { family := 1, requiredProgram := (some "aedc8351d94932d37506d4d7b44fac9b1b40baf95d35f52bee726af598e7a5c2"), inputs := [[(-13), (-15), 11, 15]], targets := [[5, (-28), (-35), (-14)]] }
  | 14 => vectorMeaning { family := 2, requiredProgram := (some "ebb887e9009fdd02f1fc999cc900c47dee131970826c19bdc55a74b9c7cccd7e"), inputs := [[1, (-13), 15, 16]], targets := [[(-14), (-13), 15, 16]] }
  | 15 => vectorMeaning { family := 3, requiredProgram := (some "40ddd0f569709b232e4d769b2b288d694705a4561ef039aae2781deca29581d6"), inputs := [[(-10), 3, (-1), (-2)]], targets := [[(-7), 8, 24, 41]] }
  | 16 => vectorMeaning { family := 4, requiredProgram := (some "5dd1421b9968b2619b62416177c38a29898d05514db22440c2229ccd51679649"), inputs := [[16, (-13), (-5), (-14)]], targets := [[23, (-26), (-7), 18]] }
  | 17 => vectorMeaning { family := 5, requiredProgram := (some "b558b30a69cfed7c0faa2157402ed7910269e29212cbb0d3354f02fe5e0c1aad"), inputs := [[8, 8, (-2), 2]], targets := [[2, 8, 2, 8]] }
  | 18 => vectorMeaning { family := 6, requiredProgram := (some "1b3e59ea732ae920aa4d272bf89d3cd3acb7930ff3d921459efda0f2888e0fc3"), inputs := [[(-6), 11, (-15), 8]], targets := [[5, 14, (-45), 20]] }
  | 19 => vectorMeaning { family := 7, requiredProgram := (some "b1e1738eecfb2e51693f8aea51ff14a49d38787a26ea62ef81078b326a9a197f"), inputs := [[(-1), (-7), (-6), (-10)]], targets := [[(-34), (-31), (-30), (-25)]] }
  | 20 => theoremMeaning "program.phase15.dynamic.affine.beb80dc125251a70" "74b00915a34bd9b2abc617337883e545052e5193f01de883549f4b61c1e9bb9e" "3020c0904123f2b84315c42fe0e13b211f9a554d81b0e2f8e730805d737f505e" Inherited12.Target inherited_12
  | 21 => vectorMeaning { family := 6, requiredProgram := none, inputs := [[24, (-13), (-1), (-6)], [23, (-29), (-4), 10], [(-9), 28, 12, 11], [23, (-32), (-6), 13], [(-21), 4, (-21), (-3)], [3, (-17), (-21), 19], [3, 4, (-21), (-5)], [26, (-18), (-29), 29]], targets := [[7, 4, (-2), (-26)], [(-10), (-9), (-8), (-10)], [15, 32, 24, (-9)], [(-13), (-10), (-12), (-7)], [(-21), 41, (-42), (-23)], [(-18), 20, (-42), (-1)], [3, 41, (-42), (-25)], [4, 27, (-58), 9]] }
  | _ => rejectMeaning
def taskIds : List String := ["lean.phase10.heldout.linear_gap", "lean.phase10.protected.reflexive_seven", "lean.phase11.heldout.add_zero_macro", "lean.phase12.generation1.le_refl_macro", "lean.phase12.generation2.zero_le_macro", "lean.phase12.generation3.lt_succ_planner_macro", "lean.phase12.generation4.lt_add_two_adapter_macro", "lean.phase14.generation5_zero_lt_succ", "lean.phase14.generation6_lt_add_five", "lean.phase14.generation7_succ_le_add_two", "lean.phase14.generation8_le_add_four", "lean.phase15.dynamic.multistep.4a7a415bcd169bb8", "phase16.dynamic.adapter_policy.2624594ed996371dbea9", "phase16.dynamic.architecture_policy.c3cd1f252d113cb41ebc", "phase16.dynamic.memory_policy.f9734b7e402fa0a0e992", "phase16.dynamic.optimizer_policy.10a54f6a7c3503fa7430", "phase16.dynamic.planner_policy.e8a5ef052b4885132a71", "phase16.dynamic.retrieval_policy.376f6d7a4130a978e1e6", "phase16.dynamic.tool_policy.231b912e39ff91bade12", "phase16.dynamic.verification_automation_policy.4290be408ad83beccf87", "program.phase15.dynamic.affine.beb80dc125251a70", "phase17.dynamic.478d7884588779bca1483fb65d06d2a4b4d430960c47a6fdfd8036fb8a39c2ab"]
def before : ObservationState := { proofs := [("lean.phase10.heldout.linear_gap", "8410efe3df3b56346023950e05536e31d3ed1436ba189e5d081eca7ecae3c2a3", "06b1bfcdd4b4d556af71bc4b9ad25705bdccc8769043bd28693b0494b1938da2"), ("lean.phase10.protected.reflexive_seven", "2923a5127ebb2dce77b93f25bfacd4ff8d23778e9c045de8ddabed164da927fb", "5392f810f0edaae2646222e27e4ba85dd09365294490637453dd5afc4086fd0a"), ("lean.phase11.heldout.add_zero_macro", "f17a5ce95e825ce7b1f160ea01b9af617754a0599dc79e598631d760d2737662", "047c1526c8be605c14dbb1ea9e7fdf798d960958c44b0c54e2c3b20b72e5e8f1"), ("lean.phase12.generation1.le_refl_macro", "29a44f8162d395296df0b6a3695ef84d4c53754badd4fc40ac572339afe81343", "64b40cfc1967d7c61ff59e88447dda1c08214b7d4f6854ab21dfce92a58ef432"), ("lean.phase12.generation2.zero_le_macro", "2ccfa1a6941344d7717e88514799bc03b443551733ef5f6611568e3b709d11ad", "810b78e6006b0587963765efe4a87f9e1cf374126d4cdbee47d22b3483200d2c"), ("lean.phase12.generation3.lt_succ_planner_macro", "ef24333062d901e017672cd228a08665df7fe26cd039bd30af051edfe0bf1f15", "0a157eea313f12a5c66a407b2ab782cb22f9e6c4a49d5c231ccb29d5854b2caf"), ("lean.phase12.generation4.lt_add_two_adapter_macro", "60e6bbca487b6807d97338b84253481f2884d25644d8f9274b716799a504d269", "32fae1c4dd17a247879289f9b8f1b4e9988f76195a101abaab29f579438c1a6e"), ("lean.phase14.generation5_zero_lt_succ", "00a2b7cac3e41ec4f7f10326f38e7876550a166956b3133ab43b60a71d167d77", "c548cc466699b3891f55e2ea9b89cb03ffa95345e797b85abd1b5ccef11fab8c"), ("lean.phase14.generation6_lt_add_five", "5f3d24df1725dd940f10edd1a1fc857d3e0a0a74aee4af2970c17e87e88e1387", "d81b0c93645b5d1fe8038d6bdc5bf36bc7ce66f65c98e5e0e437351553f5a771"), ("lean.phase14.generation7_succ_le_add_two", "e674398024eb21a38ba89194a88e47bdb9e76adc711744020733036883991f1e", "fcfda49e8ce97e014155ca5d8a1f66e5b74eadad09c53517ac8829cc3dffb910"), ("lean.phase14.generation8_le_add_four", "e213d8c64ed0c514b3be2f8e1dabde63c3b432d738e0a603140a3c948ba6ddfa", "f08827e9b291f026e450572beb47983bb520419f39f515a22f1338dfa0bece31"), ("lean.phase15.dynamic.multistep.4a7a415bcd169bb8", "a269501136730bdcde4b1ab63efdb521ebb95bf9007b4dce32025cd893b3f830", "f34f041f82c60bc693c28bcee6677254696d0988d8ab656af003131fdf93d5b8"), ("program.phase15.dynamic.affine.beb80dc125251a70", "74b00915a34bd9b2abc617337883e545052e5193f01de883549f4b61c1e9bb9e", "3020c0904123f2b84315c42fe0e13b211f9a554d81b0e2f8e730805d737f505e")],
 programs := [("1b3e59ea732ae920aa4d272bf89d3cd3acb7930ff3d921459efda0f2888e0fc3", { family := 6, variant := 2, a := 0, b := (-12) }), ("40ddd0f569709b232e4d769b2b288d694705a4561ef039aae2781deca29581d6", { family := 3, variant := 0, a := (-11), b := (-13) }), ("5dd1421b9968b2619b62416177c38a29898d05514db22440c2229ccd51679649", { family := 4, variant := 1, a := 7, b := 2 }), ("7d98001be0bd64487cb44f7db6f741b3e0436eec4cc0c4b0d74f5e6f774f2c1a", { family := 0, variant := 3, a := 11, b := 1 }), ("aedc8351d94932d37506d4d7b44fac9b1b40baf95d35f52bee726af598e7a5c2", { family := 1, variant := 1, a := (-5), b := (-5) }), ("b1e1738eecfb2e51693f8aea51ff14a49d38787a26ea62ef81078b326a9a197f", { family := 7, variant := 1, a := (-13), b := (-2) }), ("b558b30a69cfed7c0faa2157402ed7910269e29212cbb0d3354f02fe5e0c1aad", { family := 5, variant := 1, a := 12, b := (-7) }), ("ebb887e9009fdd02f1fc999cc900c47dee131970826c19bdc55a74b9c7cccd7e", { family := 2, variant := 3, a := (-15), b := (-3) })] }
def after : ObservationState := { proofs := [("lean.phase10.heldout.linear_gap", "8410efe3df3b56346023950e05536e31d3ed1436ba189e5d081eca7ecae3c2a3", "06b1bfcdd4b4d556af71bc4b9ad25705bdccc8769043bd28693b0494b1938da2"), ("lean.phase10.protected.reflexive_seven", "2923a5127ebb2dce77b93f25bfacd4ff8d23778e9c045de8ddabed164da927fb", "5392f810f0edaae2646222e27e4ba85dd09365294490637453dd5afc4086fd0a"), ("lean.phase11.heldout.add_zero_macro", "f17a5ce95e825ce7b1f160ea01b9af617754a0599dc79e598631d760d2737662", "047c1526c8be605c14dbb1ea9e7fdf798d960958c44b0c54e2c3b20b72e5e8f1"), ("lean.phase12.generation1.le_refl_macro", "29a44f8162d395296df0b6a3695ef84d4c53754badd4fc40ac572339afe81343", "64b40cfc1967d7c61ff59e88447dda1c08214b7d4f6854ab21dfce92a58ef432"), ("lean.phase12.generation2.zero_le_macro", "2ccfa1a6941344d7717e88514799bc03b443551733ef5f6611568e3b709d11ad", "810b78e6006b0587963765efe4a87f9e1cf374126d4cdbee47d22b3483200d2c"), ("lean.phase12.generation3.lt_succ_planner_macro", "ef24333062d901e017672cd228a08665df7fe26cd039bd30af051edfe0bf1f15", "0a157eea313f12a5c66a407b2ab782cb22f9e6c4a49d5c231ccb29d5854b2caf"), ("lean.phase12.generation4.lt_add_two_adapter_macro", "60e6bbca487b6807d97338b84253481f2884d25644d8f9274b716799a504d269", "32fae1c4dd17a247879289f9b8f1b4e9988f76195a101abaab29f579438c1a6e"), ("lean.phase14.generation5_zero_lt_succ", "00a2b7cac3e41ec4f7f10326f38e7876550a166956b3133ab43b60a71d167d77", "c548cc466699b3891f55e2ea9b89cb03ffa95345e797b85abd1b5ccef11fab8c"), ("lean.phase14.generation6_lt_add_five", "5f3d24df1725dd940f10edd1a1fc857d3e0a0a74aee4af2970c17e87e88e1387", "d81b0c93645b5d1fe8038d6bdc5bf36bc7ce66f65c98e5e0e437351553f5a771"), ("lean.phase14.generation7_succ_le_add_two", "e674398024eb21a38ba89194a88e47bdb9e76adc711744020733036883991f1e", "fcfda49e8ce97e014155ca5d8a1f66e5b74eadad09c53517ac8829cc3dffb910"), ("lean.phase14.generation8_le_add_four", "e213d8c64ed0c514b3be2f8e1dabde63c3b432d738e0a603140a3c948ba6ddfa", "f08827e9b291f026e450572beb47983bb520419f39f515a22f1338dfa0bece31"), ("lean.phase15.dynamic.multistep.4a7a415bcd169bb8", "a269501136730bdcde4b1ab63efdb521ebb95bf9007b4dce32025cd893b3f830", "f34f041f82c60bc693c28bcee6677254696d0988d8ab656af003131fdf93d5b8"), ("program.phase15.dynamic.affine.beb80dc125251a70", "74b00915a34bd9b2abc617337883e545052e5193f01de883549f4b61c1e9bb9e", "3020c0904123f2b84315c42fe0e13b211f9a554d81b0e2f8e730805d737f505e")],
 programs := [("1b3e59ea732ae920aa4d272bf89d3cd3acb7930ff3d921459efda0f2888e0fc3", { family := 6, variant := 2, a := 0, b := (-12) }), ("40ddd0f569709b232e4d769b2b288d694705a4561ef039aae2781deca29581d6", { family := 3, variant := 0, a := (-11), b := (-13) }), ("5dd1421b9968b2619b62416177c38a29898d05514db22440c2229ccd51679649", { family := 4, variant := 1, a := 7, b := 2 }), ("7d98001be0bd64487cb44f7db6f741b3e0436eec4cc0c4b0d74f5e6f774f2c1a", { family := 0, variant := 3, a := 11, b := 1 }), ("aedc8351d94932d37506d4d7b44fac9b1b40baf95d35f52bee726af598e7a5c2", { family := 1, variant := 1, a := (-5), b := (-5) }), ("b1e1738eecfb2e51693f8aea51ff14a49d38787a26ea62ef81078b326a9a197f", { family := 7, variant := 1, a := (-13), b := (-2) }), ("b558b30a69cfed7c0faa2157402ed7910269e29212cbb0d3354f02fe5e0c1aad", { family := 5, variant := 1, a := 12, b := (-7) }), ("ebb887e9009fdd02f1fc999cc900c47dee131970826c19bdc55a74b9c7cccd7e", { family := 2, variant := 3, a := (-15), b := (-3) }), ("a4f37fb8f2f7d3a90829340f2f02b2f19dbc5dfa5caf7a7633e9092837265c0e", { family := 6, variant := 1, a := (-4), b := 16 })] }

def beforeDeclared : Finset Nat := Finset.range 21
def afterDeclared : Finset Nat := Finset.range 22

theorem before_coverage : checkedFrontier beforeDeclared catalog before = beforeDeclared := by decide
theorem after_coverage : checkedFrontier afterDeclared catalog after = afterDeclared := by decide

theorem selected_before_sound {task : Nat} (member : task ∈ beforeDeclared) :
    (catalog task).holds before := by
  apply checked_frontier_sound beforeDeclared catalog before
  rw [before_coverage]
  exact member

theorem selected_after_sound {task : Nat} (member : task ∈ afterDeclared) :
    (catalog task).holds after := by
  apply checked_frontier_sound afterDeclared catalog after
  rw [after_coverage]
  exact member

theorem selected_frontier_retention :
    checkedFrontier beforeDeclared catalog before ⊆ checkedFrontier afterDeclared catalog after := by
  rw [before_coverage, after_coverage]
  decide

theorem selected_frontier_expansion :
    (checkedFrontier beforeDeclared catalog before).card <
      (checkedFrontier afterDeclared catalog after).card := by
  rw [before_coverage, after_coverage]
  decide

theorem selected_predecessor_rejects_new : (catalog 21).check before = false := by decide

theorem selected_catalog_bijection : taskIds.length = 22 ∧ taskIds.Nodup := by decide

end Phase17TaskMeaning
#print axioms Phase17TaskMeaning.checked_frontier_sound
#print axioms Phase17TaskMeaning.attached_root_frontier_sound
#print axioms Phase17TaskMeaning.selected_before_sound
#print axioms Phase17TaskMeaning.selected_after_sound
#print axioms Phase17TaskMeaning.selected_frontier_retention
#print axioms Phase17TaskMeaning.selected_frontier_expansion
#print axioms Phase17TaskMeaning.selected_predecessor_rejects_new
#print axioms Phase17TaskMeaning.selected_catalog_bijection
#print axioms Phase17TaskMeaning.inherited_0
#print axioms Phase17TaskMeaning.inherited_1
#print axioms Phase17TaskMeaning.inherited_2
#print axioms Phase17TaskMeaning.inherited_3
#print axioms Phase17TaskMeaning.inherited_4
#print axioms Phase17TaskMeaning.inherited_5
#print axioms Phase17TaskMeaning.inherited_6
#print axioms Phase17TaskMeaning.inherited_7
#print axioms Phase17TaskMeaning.inherited_8
#print axioms Phase17TaskMeaning.inherited_9
#print axioms Phase17TaskMeaning.inherited_10
#print axioms Phase17TaskMeaning.inherited_11
#print axioms Phase17TaskMeaning.inherited_12
