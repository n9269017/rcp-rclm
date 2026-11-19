import RcpRclmFormalCoreV4
import Mathlib.Tactic

/-
Phase 17G. A concrete, scoped append-only registry kernel.
Programs are immutable data. `eval` is a fixed deterministic interpretation,
not a candidate-supplied executor. Byte measurements and hash-to-data bindings
are discharged by the Python verifier, not by this file. Candidate credits are
the only resource modeled here. This is NOT the complete RCLM/Gate E kernel.
-/
namespace Phase17Registry

variable {Program : Type} [DecidableEq Program]

abbrev Entry (Program : Type) := String × Program

structure State (Program : Type) where
  protectedImage : List Nat
  entries : List (Entry Program)
  root : String
  deriving DecidableEq

structure Update (Program : Type) where
  key : String
  program : Program
  deriving DecidableEq

structure Evidence (Program : Type) where
  root : String
  parentEntries : List (Entry Program)
  used : Nat
  budget : Nat
  deriving DecidableEq

def lookup (key : String) : List (Entry Program) → Option Program
  | [] => none
  | e :: es => if e.1 = key then some e.2 else lookup key es

def erase (key : String) : List (Entry Program) → List (Entry Program)
  | [] => []
  | e :: es => if e.1 = key then erase key es else e :: erase key es

def apply (s : State Program) (u : Update Program) : State Program :=
  { s with entries := s.entries ++ [(u.key, u.program)] }

def recover (u : Update Program) (observed : State Program) : State Program :=
  { observed with entries := erase u.key observed.entries }

/-- Every inherited identifier keeps its program for arbitrary extension data. -/
theorem lookup_retained (xs : List (Entry Program)) (u : Update Program)
    (key : String) (p : Program) (h : lookup key xs = some p) :
    lookup key (xs ++ [(u.key, u.program)]) = some p := by
  induction xs with
  | nil => simp [lookup] at h
  | cons e es ih =>
    by_cases he : e.1 = key
    · simpa [lookup, he] using h
    · simp only [lookup, if_neg he] at h
      simpa [lookup, he] using ih h

/-- A fresh key is callable after extension. -/
theorem lookup_added (xs : List (Entry Program)) (u : Update Program)
    (h : lookup u.key xs = none) :
    lookup u.key (xs ++ [(u.key, u.program)]) = some u.program := by
  induction xs with
  | nil => simp [lookup]
  | cons e es ih =>
    by_cases he : e.1 = u.key
    · simp [lookup, he] at h
    · simp only [lookup, if_neg he] at h
      simpa [lookup, he] using ih h

theorem erase_extension (xs : List (Entry Program)) (u : Update Program)
    (h : lookup u.key xs = none) :
    erase u.key (xs ++ [(u.key, u.program)]) = xs := by
  induction xs with
  | nil => simp [erase]
  | cons e es ih =>
    by_cases he : e.1 = u.key
    · simp [lookup, he] at h
    · simp only [lookup, if_neg he] at h
      simpa [erase, he] using congrArg (List.cons e) (ih h)

theorem exact_recovery (s : State Program) (u : Update Program)
    (fresh : lookup u.key s.entries = none) : recover u (apply s u) = s := by
  cases s with
  | mk image entries root =>
    change State.mk image (erase u.key (entries ++ [(u.key, u.program)])) root = State.mk image entries root
    rw [erase_extension entries u fresh]

def dispatch {Input Output : Type} (eval : Program → Input → Output)
    (s : State Program) (key : String) (input : Input) : Option Output :=
  (lookup key s.entries).map (fun p => eval p input)

/-- Universal behavioral preservation, not a finite input sample. -/
theorem dispatch_retained {Input Output : Type}
    (eval : Program → Input → Output) (s : State Program) (u : Update Program)
    (key : String) (p : Program) (registered : lookup key s.entries = some p)
    (input : Input) :
    dispatch eval (apply s u) key input = dispatch eval s key input := by
  simp only [dispatch, apply]
  rw [lookup_retained s.entries u key p registered, registered]

structure Task (Input Output : Type) where
  key : String
  input : Input
  expected : Output

def Solves {Input Output : Type} (eval : Program → Input → Output)
    (s : State Program) (t : Task Input Output) : Prop :=
  dispatch eval s t.key t.input = some t.expected

/-- Old solved tasks retain their operational meaning under fixed evaluation. -/
theorem solved_task_retained {Input Output : Type}
    (eval : Program → Input → Output) (s : State Program) (u : Update Program)
    (t : Task Input Output) (solved : Solves eval s t) :
    Solves eval (apply s u) t := by
  cases h : lookup t.key s.entries with
  | none => simp [Solves, dispatch, h] at solved
  | some p =>
    change dispatch eval (apply s u) t.key t.input = some t.expected
    rw [dispatch_retained eval s u t.key p h t.input]
    exact solved

open RcpRclmFormalCoreV2

/-- The concrete observation is equality of the entire protected image. -/
noncomputable def protectedValue (s : State Program) (image : List Nat) : ℝ :=
  if s.protectedImage = image then 1 else 0

noncomputable def distance (x y : State Program) : ℝ := if x = y then 0 else 1

def admissible (s : State Program) : Prop :=
  s.root ≠ "" ∧ ∀ n ∈ s.protectedImage, n < 256

def trustValid (s : State Program) (c : RCP.Candidate (State Program) (Update Program))
    (e : Evidence Program) : Prop :=
  e.root = s.root ∧ c.next.root = s.root ∧ e.parentEntries = s.entries

def realityContained (s : State Program)
    (c : RCP.Candidate (State Program) (Update Program)) (e : Evidence Program) : Prop :=
  c.next = apply s c.update ∧ lookup c.update.key s.entries = none ∧
    c.update.key ≠ "" ∧ e.parentEntries = s.entries

/-- Nonconstant protected observations, credit residuals, and rejectable reality
checks instantiate the actual immutable RCP.Kernel structure. Program validity,
unique identifiers, serialization, and physical binding are additional Python
checks; this formal instance deliberately covers only append-only registry state. -/
noncomputable def kernel [Inhabited Program] : RCP.Kernel (State Program) (Update Program)
    (Evidence Program) (List Nat) Unit where
  apply := apply
  admissible := admissible
  protectedInvariant := admissible
  protectedValue := protectedValue
  protectedValue_nonconstant := by
    refine ⟨⟨[], [], "r"⟩, [], ⟨[1], [], "r"⟩, [], ?_⟩
    norm_num [protectedValue]
  transportProtected := fun _ _ image => image
  lossBudget := fun _ _ => 0
  lossBudget_nonnegative := by intros; exact le_rfl
  stateDistance := distance
  stateDistance_nonnegative := by intros; unfold distance; split <;> norm_num
  recover := fun _ c observed => recover c.update observed
  recoveryBudget := fun _ _ => 0
  recoveryBudget_nonnegative := by intros; exact le_rfl
  progress := fun s => (s.entries.length : ℝ)
  strictWitness := fun s c _ => lookup c.update.key s.entries = none
  residual := fun _ _ e _ => (e.used : ℝ) - (e.budget : ℝ)
  residual_nonconstant := by
    let s : State Program := ⟨[], [], "r"⟩
    let c : RCP.Candidate (State Program) (Update Program) := ⟨⟨"k", default⟩, s⟩
    refine ⟨s, c, ⟨"r", [], 0, 0⟩, s, c, ⟨"r", [], 1, 0⟩, (), ?_⟩
    norm_num
  trustValid := trustValid
  resourceValid := fun _ _ e => e.used ≤ e.budget ∧ e.budget ≤ 32
  realityContained := realityContained
  realityContained_not_universal := by
    let s : State Program := ⟨[], [], "r"⟩
    let c : RCP.Candidate (State Program) (Update Program) := ⟨⟨"", default⟩, s⟩
    refine ⟨s, c, ⟨"r", [], 0, 0⟩, ?_⟩
    simp [realityContained, c]

/-- All eleven base obligations for this explicitly scoped concrete kernel.
No LearnedAcceptedStep or AutonomousAcceptedStep is asserted here. -/
theorem base_step_sound [Inhabited Program]
    (s : State Program) (u : Update Program) (e : Evidence Program)
    (valid : admissible s)
    (fresh : lookup u.key s.entries = none)
    (keyValid : u.key ≠ "")
    (rootBound : e.root = s.root)
    (parentBound : e.parentEntries = s.entries)
    (credits : e.used ≤ e.budget) (ceiling : e.budget ≤ 32) :
    RCP.StepObligations kernel s ⟨u, apply s u⟩ e := by
  constructor
  · rfl
  · intro _index
    change (e.used : ℝ) - (e.budget : ℝ) ≤ 0
    exact sub_nonpos.mpr (by exact_mod_cast credits)
  · intro image
    change protectedValue s image ≤ protectedValue (apply s u) image + 0
    simp [protectedValue, apply]
  · change distance (recover u (apply s u)) s ≤ 0
    rw [exact_recovery s u fresh]
    simp [distance]
  · change admissible (apply s u)
    exact valid
  · change (s.entries.length : ℝ) ≤ ((s.entries ++ [(u.key, u.program)]).length : ℝ)
    simp
  · intro _witness
    change (s.entries.length : ℝ) < ((s.entries ++ [(u.key, u.program)]).length : ℝ)
    simp
  · exact ⟨rootBound, rfl, parentBound⟩
  · exact ⟨credits, ceiling⟩
  · exact ⟨rfl, fresh, keyValid, parentBound⟩
  · change admissible (apply s u)
    exact valid

end Phase17Registry

namespace Phase17Registry
set_option maxRecDepth 8192
set_option maxHeartbeats 1000000
-- Measured packet SHA256: 57e61a3f656684621e3d70c680d53b92e7d4cfa0fb41162a2e89c52c0ef90c99
def selectedBefore (image : List Nat) : State String := { protectedImage := image, entries := [("1b3e59ea732ae920aa4d272bf89d3cd3acb7930ff3d921459efda0f2888e0fc3", "{\"family\":\"tool_policy\",\"generation\":1,\"operation_id\":\"install_package_bound_tool_chain\",\"parameter_a\":0,\"parameter_b\":-12,\"promotion_index\":1,\"public_nonce_hash\":\"3eadfb23d3d408b49f0cc0554ddcefcd5ab18c6a395add082c1f3b56cd70609d\",\"schema_id\":\"runtime.v4.phase16.mutation_program.v1\",\"variant\":2}"), ("40ddd0f569709b232e4d769b2b288d694705a4561ef039aae2781deca29581d6", "{\"family\":\"optimizer_policy\",\"generation\":1,\"operation_id\":\"install_expanding_resource_schedule\",\"parameter_a\":-11,\"parameter_b\":-13,\"promotion_index\":2,\"public_nonce_hash\":\"2dd5d6a4ba4f7b7f97613ec229ef35567ad68b1b5c101f37a319e0c86c3e3018\",\"schema_id\":\"runtime.v4.phase16.mutation_program.v1\",\"variant\":0}"), ("5dd1421b9968b2619b62416177c38a29898d05514db22440c2229ccd51679649", "{\"family\":\"planner_policy\",\"generation\":1,\"operation_id\":\"install_fair_search_planning_rule\",\"parameter_a\":7,\"parameter_b\":2,\"promotion_index\":7,\"public_nonce_hash\":\"ba06a98486729268c074b860ac3c3a5d0b213a4834b9970fb7ad5bbd38451a32\",\"schema_id\":\"runtime.v4.phase16.mutation_program.v1\",\"variant\":1}"), ("7d98001be0bd64487cb44f7db6f741b3e0436eec4cc0c4b0d74f5e6f774f2c1a", "{\"family\":\"adapter_policy\",\"generation\":1,\"operation_id\":\"install_transfer_adapter_motif\",\"parameter_a\":11,\"parameter_b\":1,\"promotion_index\":3,\"public_nonce_hash\":\"3fcabe4b75c6ac66d6c72c91265ff98374c6a8eaa9984569be8894dd84177a83\",\"schema_id\":\"runtime.v4.phase16.mutation_program.v1\",\"variant\":3}"), ("aedc8351d94932d37506d4d7b44fac9b1b40baf95d35f52bee726af598e7a5c2", "{\"family\":\"architecture_policy\",\"generation\":1,\"operation_id\":\"install_bounded_execution_route\",\"parameter_a\":-5,\"parameter_b\":-5,\"promotion_index\":0,\"public_nonce_hash\":\"90c8521cbefb4912adde553650a13bdd94ab9ca4165a77689541f14abf2e4c54\",\"schema_id\":\"runtime.v4.phase16.mutation_program.v1\",\"variant\":1}"), ("b1e1738eecfb2e51693f8aea51ff14a49d38787a26ea62ef81078b326a9a197f", "{\"family\":\"verification_automation_policy\",\"generation\":1,\"operation_id\":\"install_untrusted_proof_search_policy\",\"parameter_a\":-13,\"parameter_b\":-2,\"promotion_index\":6,\"public_nonce_hash\":\"34b1a9e23cc3061091b07580f47b0f2164c3e72b267bfd661b13453c7b47b483\",\"schema_id\":\"runtime.v4.phase16.mutation_program.v1\",\"variant\":1}"), ("b558b30a69cfed7c0faa2157402ed7910269e29212cbb0d3354f02fe5e0c1aad", "{\"family\":\"retrieval_policy\",\"generation\":1,\"operation_id\":\"install_rejection_conditioned_retrieval_route\",\"parameter_a\":12,\"parameter_b\":-7,\"promotion_index\":4,\"public_nonce_hash\":\"a5e3c88f1a974ccd87b9543fc4d2beacc7830c293abbffac822aa65aaaf16673\",\"schema_id\":\"runtime.v4.phase16.mutation_program.v1\",\"variant\":1}"), ("ebb887e9009fdd02f1fc999cc900c47dee131970826c19bdc55a74b9c7cccd7e", "{\"family\":\"memory_policy\",\"generation\":1,\"operation_id\":\"install_content_addressed_memory_motif\",\"parameter_a\":-15,\"parameter_b\":-3,\"promotion_index\":5,\"public_nonce_hash\":\"013c1d5f062431f990b2abeb3b40be59991046a010369c7d52e1a51a844cd09e\",\"schema_id\":\"runtime.v4.phase16.mutation_program.v1\",\"variant\":3}")], root := "fc4cf15ec370547b14fc67ae360269cea71cbc10d773536d1a77891acbe3bf7e" }
def selectedUpdate : Update String := { key := "a4f37fb8f2f7d3a90829340f2f02b2f19dbc5dfa5caf7a7633e9092837265c0e", program := "{\"family\":\"tool_policy\",\"generation\":2,\"operation_id\":\"install_package_bound_tool_chain\",\"parameter_a\":-4,\"parameter_b\":16,\"promotion_index\":0,\"public_nonce_hash\":\"8888888888888888888888888888888888888888888888888888888888888888\",\"schema_id\":\"runtime.v4.phase16.mutation_program.v1\",\"variant\":1}" }
def selectedEvidence : Evidence String := { root := "fc4cf15ec370547b14fc67ae360269cea71cbc10d773536d1a77891acbe3bf7e", parentEntries := (selectedBefore []).entries, used := 1, budget := 32 }
theorem selected_base_step (image : List Nat) (validBytes : ∀ n ∈ image, n < 256) :
    RcpRclmFormalCoreV2.RCP.StepObligations kernel (selectedBefore image)
      ⟨selectedUpdate, apply (selectedBefore image) selectedUpdate⟩ selectedEvidence := by
  apply base_step_sound
  · exact ⟨by decide, validBytes⟩
  · decide
  · decide
  · rfl
  · rfl
  · decide
  · decide
def selectedAfter : List (Entry String) := [("1b3e59ea732ae920aa4d272bf89d3cd3acb7930ff3d921459efda0f2888e0fc3", "{\"family\":\"tool_policy\",\"generation\":1,\"operation_id\":\"install_package_bound_tool_chain\",\"parameter_a\":0,\"parameter_b\":-12,\"promotion_index\":1,\"public_nonce_hash\":\"3eadfb23d3d408b49f0cc0554ddcefcd5ab18c6a395add082c1f3b56cd70609d\",\"schema_id\":\"runtime.v4.phase16.mutation_program.v1\",\"variant\":2}"), ("40ddd0f569709b232e4d769b2b288d694705a4561ef039aae2781deca29581d6", "{\"family\":\"optimizer_policy\",\"generation\":1,\"operation_id\":\"install_expanding_resource_schedule\",\"parameter_a\":-11,\"parameter_b\":-13,\"promotion_index\":2,\"public_nonce_hash\":\"2dd5d6a4ba4f7b7f97613ec229ef35567ad68b1b5c101f37a319e0c86c3e3018\",\"schema_id\":\"runtime.v4.phase16.mutation_program.v1\",\"variant\":0}"), ("5dd1421b9968b2619b62416177c38a29898d05514db22440c2229ccd51679649", "{\"family\":\"planner_policy\",\"generation\":1,\"operation_id\":\"install_fair_search_planning_rule\",\"parameter_a\":7,\"parameter_b\":2,\"promotion_index\":7,\"public_nonce_hash\":\"ba06a98486729268c074b860ac3c3a5d0b213a4834b9970fb7ad5bbd38451a32\",\"schema_id\":\"runtime.v4.phase16.mutation_program.v1\",\"variant\":1}"), ("7d98001be0bd64487cb44f7db6f741b3e0436eec4cc0c4b0d74f5e6f774f2c1a", "{\"family\":\"adapter_policy\",\"generation\":1,\"operation_id\":\"install_transfer_adapter_motif\",\"parameter_a\":11,\"parameter_b\":1,\"promotion_index\":3,\"public_nonce_hash\":\"3fcabe4b75c6ac66d6c72c91265ff98374c6a8eaa9984569be8894dd84177a83\",\"schema_id\":\"runtime.v4.phase16.mutation_program.v1\",\"variant\":3}"), ("aedc8351d94932d37506d4d7b44fac9b1b40baf95d35f52bee726af598e7a5c2", "{\"family\":\"architecture_policy\",\"generation\":1,\"operation_id\":\"install_bounded_execution_route\",\"parameter_a\":-5,\"parameter_b\":-5,\"promotion_index\":0,\"public_nonce_hash\":\"90c8521cbefb4912adde553650a13bdd94ab9ca4165a77689541f14abf2e4c54\",\"schema_id\":\"runtime.v4.phase16.mutation_program.v1\",\"variant\":1}"), ("b1e1738eecfb2e51693f8aea51ff14a49d38787a26ea62ef81078b326a9a197f", "{\"family\":\"verification_automation_policy\",\"generation\":1,\"operation_id\":\"install_untrusted_proof_search_policy\",\"parameter_a\":-13,\"parameter_b\":-2,\"promotion_index\":6,\"public_nonce_hash\":\"34b1a9e23cc3061091b07580f47b0f2164c3e72b267bfd661b13453c7b47b483\",\"schema_id\":\"runtime.v4.phase16.mutation_program.v1\",\"variant\":1}"), ("b558b30a69cfed7c0faa2157402ed7910269e29212cbb0d3354f02fe5e0c1aad", "{\"family\":\"retrieval_policy\",\"generation\":1,\"operation_id\":\"install_rejection_conditioned_retrieval_route\",\"parameter_a\":12,\"parameter_b\":-7,\"promotion_index\":4,\"public_nonce_hash\":\"a5e3c88f1a974ccd87b9543fc4d2beacc7830c293abbffac822aa65aaaf16673\",\"schema_id\":\"runtime.v4.phase16.mutation_program.v1\",\"variant\":1}"), ("ebb887e9009fdd02f1fc999cc900c47dee131970826c19bdc55a74b9c7cccd7e", "{\"family\":\"memory_policy\",\"generation\":1,\"operation_id\":\"install_content_addressed_memory_motif\",\"parameter_a\":-15,\"parameter_b\":-3,\"promotion_index\":5,\"public_nonce_hash\":\"013c1d5f062431f990b2abeb3b40be59991046a010369c7d52e1a51a844cd09e\",\"schema_id\":\"runtime.v4.phase16.mutation_program.v1\",\"variant\":3}"), ("a4f37fb8f2f7d3a90829340f2f02b2f19dbc5dfa5caf7a7633e9092837265c0e", "{\"family\":\"tool_policy\",\"generation\":2,\"operation_id\":\"install_package_bound_tool_chain\",\"parameter_a\":-4,\"parameter_b\":16,\"promotion_index\":0,\"public_nonce_hash\":\"8888888888888888888888888888888888888888888888888888888888888888\",\"schema_id\":\"runtime.v4.phase16.mutation_program.v1\",\"variant\":1}")]
theorem selected_registry_mapping :
  selectedAfter = ((selectedBefore []).entries ++ [(selectedUpdate.key, selectedUpdate.program)]) := by decide
end Phase17Registry
#print axioms Phase17Registry.base_step_sound
#print axioms Phase17Registry.dispatch_retained
#print axioms Phase17Registry.solved_task_retained
#print axioms Phase17Registry.exact_recovery
#print axioms Phase17Registry.selected_base_step
#print axioms Phase17Registry.selected_registry_mapping
