import Std
import Lean.Elab.Tactic.Omega

/- Phase 17AN: the protected broker's fixed dispatch and conservative accounting
   admission interface. Concrete values are projected from retained native
   commission, broker, client-anchor and accounting records after independent
   byte/source validation. The caller does not provide paths, keys, anchors,
   objective/evaluator implementations, or authentication results through Intent.
   These structural theorems do not prove the Python/OS refinement, legitimate
   independent provisioning, physical storage currentness, global exclusivity,
   complete physical costs or root promotion acceptance. -/
namespace Phase17ProtectedAuthority

structure Commission where
  identity : String
  authorityCommission : String
  root : String
  brokerSource : String
  controllerSource : String
  objective : String
  evaluator : String
  accountingPolicy : String
  maxCredits : Nat
  maxIntents : Nat
  deriving DecidableEq

structure RuntimeBinding where
  brokerSource : String
  controllerSource : String
  objective : String
  evaluator : String
  accountingPolicy : String
  deriving DecidableEq

def FixedBinding (c : Commission) (b : RuntimeBinding) : Prop :=
  c.identity ≠ "" ∧ c.authorityCommission ≠ "" ∧ c.root ≠ "" ∧
  b.brokerSource = c.brokerSource ∧ b.controllerSource = c.controllerSource ∧
  b.objective = c.objective ∧ b.evaluator = c.evaluator ∧
  b.accountingPolicy = c.accountingPolicy ∧
  0 < c.maxCredits ∧ c.maxCredits ≤ 32 ∧ 0 < c.maxIntents ∧ c.maxIntents ≤ 128

instance (c : Commission) (b : RuntimeBinding) : Decidable (FixedBinding c b) := by
  unfold FixedBinding
  infer_instance

structure Cursor where
  epoch : Nat
  serial : Nat
  head : String
  deriving DecidableEq

structure Mutation where
  current : Cursor
  nonce : String
  credits : Nat
  deriving DecidableEq

structure State where
  commission : String
  root : String
  current : Cursor
  pending : Option Mutation
  consumed : List String
  deriving DecidableEq

/-- The public frontend intent has no authority paths, keys or state fields. -/
structure Intent where
  operation : String
  nonce : String
  credits : Nat
  deriving DecidableEq

/-- Broker intent correlation is retained here. For a run this is also the
    AM wire nonce. Read/reconcile wire challenges/nonces are separately observed. -/
structure Issued where
  authorityCommission : String
  root : String
  current : Cursor
  operation : String
  nonce : String
  credits : Nat
  deriving DecidableEq

def Operation (operation : String) : Prop :=
  operation = "read" ∨ operation = "run" ∨ operation = "reconcile"

instance (operation : String) : Decidable (Operation operation) := by
  unfold Operation
  infer_instance

def Guard (c : Commission) (b : RuntimeBinding) (s : State) (q : Intent) : Prop :=
  FixedBinding c b ∧ s.commission = c.identity ∧ s.root = c.root ∧
  s.current.head ≠ "" ∧ Operation q.operation ∧ q.nonce ≠ "" ∧ q.credits ≤ c.maxCredits ∧
  (q.operation ≠ "run" → q.credits = 0) ∧
  (q.operation = "run" → s.pending = none ∧ q.nonce ∉ s.consumed) ∧
  (q.operation = "reconcile" → s.pending ≠ none) ∧
  (q.operation = "read" → s.pending = none) ∧ q.nonce ∉ s.consumed ∧
  s.consumed.length < c.maxIntents ∧ (q.operation = "run" → 0 < q.credits)

instance (c : Commission) (b : RuntimeBinding) (s : State) (q : Intent) :
    Decidable (Guard c b s q) := by
  unfold Guard
  infer_instance

def issued (c : Commission) (s : State) (q : Intent) : Issued :=
  ⟨c.authorityCommission, c.root, s.current,
    if q.operation = "reconcile" then "read" else q.operation, q.nonce, q.credits⟩

def dispatch (c : Commission) (b : RuntimeBinding) (s : State) (q : Intent) : Option Issued :=
  if Guard c b s q then some (issued c s q) else none

theorem dispatch_spec (c : Commission) (b : RuntimeBinding) (s : State) (q : Intent) (r : Issued)
    (accepted : dispatch c b s q = some r) : Guard c b s q ∧ r = issued c s q := by
  unfold dispatch at accepted
  split at accepted
  next valid => exact ⟨valid, (Option.some.inj accepted).symm⟩
  next invalid => cases accepted

theorem dispatch_construct (c : Commission) (b : RuntimeBinding) (s : State) (q : Intent)
    (valid : Guard c b s q) : dispatch c b s q = some (issued c s q) := by
  simp only [dispatch, valid, if_true]

theorem dispatch_fixed_binding (c : Commission) (b : RuntimeBinding) (s : State) (q : Intent) (r : Issued)
    (accepted : dispatch c b s q = some r) : FixedBinding c b :=
  (dispatch_spec c b s q r accepted).1.1

theorem dispatch_pinned_authority (c : Commission) (b : RuntimeBinding) (s : State) (q : Intent) (r : Issued)
    (accepted : dispatch c b s q = some r) :
    r.authorityCommission = c.authorityCommission ∧ r.root = c.root ∧ r.current = s.current := by
  rw [(dispatch_spec c b s q r accepted).2]
  exact ⟨rfl, rfl, rfl⟩

theorem wrong_commission_refused (c : Commission) (b : RuntimeBinding) (s : State) (q : Intent)
    (wrong : s.commission ≠ c.identity) : dispatch c b s q = none := by
  simp only [dispatch]
  split
  · rename_i h
    exact False.elim (wrong h.2.1)
  · rfl

theorem wrong_root_refused (c : Commission) (b : RuntimeBinding) (s : State) (q : Intent)
    (wrong : s.root ≠ c.root) : dispatch c b s q = none := by
  simp only [dispatch]
  split
  · rename_i h
    exact False.elim (wrong h.2.2.1)
  · rfl

theorem wrong_runtime_refused (c : Commission) (b : RuntimeBinding) (s : State) (q : Intent)
    (wrong : ¬ FixedBinding c b) : dispatch c b s q = none := by
  simp only [dispatch]
  split
  · rename_i h
    exact False.elim (wrong h.1)
  · rfl

theorem administrative_operation_refused (c : Commission) (b : RuntimeBinding) (s : State) (q : Intent)
    (wrong : ¬ Operation q.operation) : dispatch c b s q = none := by
  simp only [dispatch]
  split
  · rename_i h
    exact False.elim (wrong h.2.2.2.2.1)
  · rfl

theorem run_requires_idle (c : Commission) (b : RuntimeBinding) (s : State) (q : Intent) (r : Issued)
    (accepted : dispatch c b s q = some r) (run : q.operation = "run") :
    s.pending = none ∧ q.nonce ∉ s.consumed := by
  exact (dispatch_spec c b s q r accepted).1.2.2.2.2.2.2.2.2.1 run

theorem pending_run_refused (c : Commission) (b : RuntimeBinding) (s : State) (q : Intent)
    (run : q.operation = "run") (pending : s.pending ≠ none) : dispatch c b s q = none := by
  simp only [dispatch]
  split
  · rename_i h
    exact False.elim (pending (h.2.2.2.2.2.2.2.2.1 run).1)
  · rfl

theorem replayed_run_refused (c : Commission) (b : RuntimeBinding) (s : State) (q : Intent)
    (run : q.operation = "run") (used : q.nonce ∈ s.consumed) : dispatch c b s q = none := by
  simp only [dispatch]
  split
  · rename_i h
    exact False.elim ((h.2.2.2.2.2.2.2.2.1 run).2 used)
  · rfl

theorem dispatch_credit_limit (c : Commission) (b : RuntimeBinding) (s : State) (q : Intent) (r : Issued)
    (accepted : dispatch c b s q = some r) (run : q.operation = "run") :
    0 < q.credits ∧ q.credits ≤ c.maxCredits := by
  rcases (dispatch_spec c b s q r accepted).1 with
    ⟨_, _, _, _, _, _, bounded, _, _, _, _, _, _, positive⟩
  exact ⟨positive run, bounded⟩

theorem dispatch_intent_capacity (c : Commission) (b : RuntimeBinding) (s : State) (q : Intent) (r : Issued)
    (accepted : dispatch c b s q = some r) : s.consumed.length < c.maxIntents := by
  rcases (dispatch_spec c b s q r accepted).1 with
    ⟨_, _, _, _, _, _, _, _, _, _, _, _, capacity, _⟩
  exact capacity

theorem over_credit_refused (c : Commission) (b : RuntimeBinding) (s : State) (q : Intent)
    (over : c.maxCredits < q.credits) : dispatch c b s q = none := by
  simp only [dispatch]
  split
  · rename_i h
    rcases h with ⟨_, _, _, _, _, _, bounded, _, _, _, _, _, _, _⟩
    omega
  · rfl

theorem zero_credit_refused (c : Commission) (b : RuntimeBinding) (s : State) (q : Intent)
    (run : q.operation = "run") (zero : q.credits = 0) : dispatch c b s q = none := by
  simp only [dispatch]
  split
  · rename_i h
    rcases h with ⟨_, _, _, _, _, _, _, _, _, _, _, _, _, positive⟩
    have nonzero := positive run
    omega
  · rfl

theorem intent_capacity_refused (c : Commission) (b : RuntimeBinding) (s : State) (q : Intent)
    (exhausted : c.maxIntents ≤ s.consumed.length) : dispatch c b s q = none := by
  simp only [dispatch]
  split
  · rename_i h
    rcases h with ⟨_, _, _, _, _, _, _, _, _, _, _, _, capacity, _⟩
    omega
  · rfl

theorem replayed_intent_refused (c : Commission) (b : RuntimeBinding) (s : State) (q : Intent)
    (used : q.nonce ∈ s.consumed) : dispatch c b s q = none := by
  simp only [dispatch]
  split
  · rename_i h
    rcases h with ⟨_, _, _, _, _, _, _, _, _, _, _, fresh, _, _⟩
    exact False.elim (fresh used)
  · rfl

def beginMutation (c : Commission) (b : RuntimeBinding) (s : State) (q : Intent) : Option State :=
  if Guard c b s q ∧ q.operation = "run" then
    some { s with pending := some ⟨s.current, q.nonce, q.credits⟩, consumed := s.consumed ++ [q.nonce] }
  else none

theorem begin_retains_exact_pending (c : Commission) (b : RuntimeBinding) (s next : State) (q : Intent)
    (accepted : beginMutation c b s q = some next) :
    next = { s with pending := some ⟨s.current, q.nonce, q.credits⟩, consumed := s.consumed ++ [q.nonce] } := by
  unfold beginMutation at accepted
  split at accepted
  · exact (Option.some.inj accepted).symm
  · cases accepted

theorem begin_blocks_repeat (c : Commission) (b : RuntimeBinding) (s next : State) (q : Intent)
    (accepted : beginMutation c b s q = some next) : dispatch c b next q = none := by
  unfold beginMutation at accepted
  split at accepted
  next h =>
    have state := (Option.some.inj accepted).symm
    rw [state]
    exact pending_run_refused c b _ q h.2 (by simp)
  next h => cases accepted

def reconcilePending (s : State) (terminal : Bool) : Option Mutation :=
  if terminal then none else s.pending

theorem uncertain_outcome_retained (s : State) : reconcilePending s false = s.pending := rfl

theorem terminal_outcome_cleared (s : State) : reconcilePending s true = none := rfl

theorem reconcile_issues_read (c : Commission) (b : RuntimeBinding) (s : State) (q : Intent) (r : Issued)
    (accepted : dispatch c b s q = some r) (reconcile : q.operation = "reconcile") :
    r.operation = "read" := by
  rw [(dispatch_spec c b s q r accepted).2]
  simp only [issued, reconcile, if_true]

def launchCount (r : Issued) : Nat := if r.operation = "run" then 1 else 0

theorem reconcile_never_launches (c : Commission) (b : RuntimeBinding) (s : State) (q : Intent) (r : Issued)
    (accepted : dispatch c b s q = some r) (reconcile : q.operation = "reconcile") :
    launchCount r = 0 := by
  simp [launchCount, reconcile_issues_read c b s q r accepted reconcile]

structure Coverage where
  category : String
  observed : Option Nat
  upperBound : Option Nat
  meter : String
  deriving DecidableEq

def entryComplete (entry : Coverage) : Bool :=
  match entry.observed, entry.upperBound with
  | some actual, some bound => decide (entry.meter ≠ "" ∧ actual ≤ bound)
  | _, _ => false

def coverageReady (required : List String) (entries : List Coverage) : Bool :=
  decide (required ≠ [] ∧ required.Nodup ∧ entries.map Coverage.category = required) &&
    entries.all entryComplete

def upperCost (entries : List Coverage) : Nat :=
  (entries.map (fun entry => entry.upperBound.getD 0)).sum

def promotionAdmission (required : List String) (entries : List Coverage) (budget : Nat)
    (rootAccepted : Bool) : Bool :=
  coverageReady required entries && decide (upperCost entries ≤ budget) && rootAccepted

theorem ready_exact_inventory (required : List String) (entries : List Coverage)
    (ready : coverageReady required entries = true) :
    required ≠ [] ∧ required.Nodup ∧ entries.map Coverage.category = required := by
  have h := (Bool.and_eq_true_iff.mp ready).1
  exact of_decide_eq_true h

theorem ready_entries_complete (required : List String) (entries : List Coverage)
    (ready : coverageReady required entries = true) :
    ∀ entry ∈ entries, entryComplete entry = true := by
  exact List.all_eq_true.mp (Bool.and_eq_true_iff.mp ready).2

theorem unknown_observation_incomplete (entry : Coverage) (unknown : entry.observed = none) :
    entryComplete entry = false := by simp [entryComplete, unknown]

theorem unknown_upper_bound_incomplete (entry : Coverage) (unknown : entry.upperBound = none) :
    entryComplete entry = false := by cases h : entry.observed <;> simp [entryComplete, h, unknown]

theorem incomplete_entry_blocks_coverage (required : List String) (entries : List Coverage)
    (entry : Coverage) (member : entry ∈ entries) (incomplete : entryComplete entry = false) :
    coverageReady required entries = false := by
  cases h : coverageReady required entries
  · rfl
  · have complete := ready_entries_complete required entries h entry member
    rw [incomplete] at complete
    cases complete

theorem accepted_requires_coverage (required : List String) (entries : List Coverage) (budget : Nat)
    (rootAccepted : Bool) (accepted : promotionAdmission required entries budget rootAccepted = true) :
    coverageReady required entries = true := by
  exact (Bool.and_eq_true_iff.mp (Bool.and_eq_true_iff.mp accepted).1).1

theorem accepted_requires_budget (required : List String) (entries : List Coverage) (budget : Nat)
    (rootAccepted : Bool) (accepted : promotionAdmission required entries budget rootAccepted = true) :
    upperCost entries ≤ budget := by
  exact of_decide_eq_true (Bool.and_eq_true_iff.mp (Bool.and_eq_true_iff.mp accepted).1).2

theorem accepted_requires_root (required : List String) (entries : List Coverage) (budget : Nat)
    (rootAccepted : Bool) (accepted : promotionAdmission required entries budget rootAccepted = true) :
    rootAccepted = true := (Bool.and_eq_true_iff.mp accepted).2

theorem incomplete_coverage_blocks_promotion (required : List String) (entries : List Coverage) (budget : Nat)
    (rootAccepted : Bool) (incomplete : coverageReady required entries = false) :
    promotionAdmission required entries budget rootAccepted = false := by
  simp [promotionAdmission, incomplete]

theorem transport_alone_cannot_promote (required : List String) (entries : List Coverage) (budget : Nat) :
    promotionAdmission required entries budget false = false := by simp [promotionAdmission]

/-- Identical cloned trusted state can satisfy the same structural guard.
    An independently current, exclusive physical allocator is a separate premise. -/
theorem identical_brokers_dispatch_identically (c : Commission) (b : RuntimeBinding) (s : State) (q : Intent)
    (accepted : dispatch c b s q = some (issued c s q)) :
    ∃ first second : State, first = s ∧ second = s ∧
      dispatch c b first q = some (issued c s q) ∧
      dispatch c b second q = some (issued c s q) := by
  exact ⟨s, s, rfl, rfl, accepted, accepted⟩

end Phase17ProtectedAuthority
