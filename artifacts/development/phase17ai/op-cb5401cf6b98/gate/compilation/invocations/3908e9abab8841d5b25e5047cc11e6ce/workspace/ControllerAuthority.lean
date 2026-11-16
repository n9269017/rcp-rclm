import ProducerDomain

/- Phase 17AI: a local, externally anchored authority for the selected reference
   producer sessions. The trusted policy and current journal head are supplied
   independently of candidate requests. Equal strings bind retained records;
   they do not establish signatures, external issuance, or rollback resistance.
   The issuer reserves a whole declared session envelope before a result can be
   consumed, and every completed result projects to the AH truthful controller.
   Accounting is exact for those envelopes, not for physical host work. -/
namespace Phase17ControllerAuthority

open Phase17ProducerDomain

structure Permit where
  name : String
  binding : Binding
  model : String
  prefixHash : String
  initial : Phase17Controller.Prefix
  checkpoint : String
  frozen : String
  objective : String
  evaluatorCode : String
  deriving DecidableEq

structure AuthorityPolicy where
  authority : String
  policy : String
  catalog : String
  objective : String
  evaluator : String
  evaluatorCode : String
  candidateCredits : Nat
  sessionAttempts : Nat
  poolAttempts : Nat
  sources : List Permit
  deriving DecidableEq

def PermitBound (policy : AuthorityPolicy) (source : Permit) : Prop :=
  source ∈ policy.sources ∧ source.binding.catalog = policy.catalog ∧
  source.binding.evaluator = policy.evaluator ∧ source.objective = policy.objective ∧
  source.evaluatorCode = policy.evaluatorCode ∧
  source.initial = Phase17Controller.initial policy.candidateCredits ∧
  source.checkpoint ≠ "" ∧ source.frozen ≠ "" ∧ source.model ≠ "" ∧ source.prefixHash ≠ ""

instance permitBoundDecidable (policy : AuthorityPolicy) (source : Permit) :
    Decidable (PermitBound policy source) := by unfold PermitBound; infer_instance

def PolicyValid (policy : AuthorityPolicy) : Prop :=
  policy.authority ≠ "" ∧ policy.policy ≠ "" ∧ policy.candidateCredits ≤ 32 ∧
  0 < policy.candidateCredits ∧ 0 < policy.sessionAttempts ∧
  policy.sessionAttempts ≤ 32 ∧ (policy.sources.map Permit.name).Nodup ∧
  ∀ source ∈ policy.sources, PermitBound policy source

instance policyValidDecidable (policy : AuthorityPolicy) : Decidable (PolicyValid policy) := by
  unfold PolicyValid
  infer_instance

/-- This is the issuer's constructor. A request cannot choose another tariff,
    evaluator, catalog, context, source, or candidate credit allowance. -/
def issuedGrant (policy : AuthorityPolicy) (source : Permit) : Grant :=
  { binding := source.binding, candidateLimit := policy.candidateCredits,
    referenceCandidateLimit := policy.sessionAttempts,
    vectorLimit := 2 * policy.sessionAttempts,
    inputLimit := 8 * policy.sessionAttempts, outputLimit := 8 * policy.sessionAttempts,
    costLimit := 112 * policy.sessionAttempts }

structure Lease where
  serial : Nat
  authority : String
  policy : String
  source : Permit
  grant : Grant
  deriving DecidableEq

def issuedLease (policy : AuthorityPolicy) (source : Permit) (serial : Nat) : Lease :=
  ⟨serial, policy.authority, policy.policy, source, issuedGrant policy source⟩

structure Completion where
  lease : Lease
  observations : List Phase17Controller.Observation
  execution : ExecutionState
  checkpoint : String
  deriving DecidableEq

structure AuthorityState where
  nextSerial : Nat
  reservedAttempts : Nat
  pending : Option Lease
  liveLease : Option Lease
  consumed : List String
  completed : List Completion
  halted : Bool
  deriving DecidableEq

def initial : AuthorityState := ⟨0, 0, none, none, [], [], false⟩

def reservedCost (state : AuthorityState) : Nat := 112 * state.reservedAttempts

def reservedVector (state : AuthorityState) : List Nat :=
  [state.reservedAttempts, 2 * state.reservedAttempts,
    8 * state.reservedAttempts, 8 * state.reservedAttempts]

def IssueGuard (trusted supplied : AuthorityPolicy) (expectedHead currentHead : String)
    (state : AuthorityState) (source : Permit) : Prop :=
  supplied = trusted ∧ expectedHead = currentHead ∧ PolicyValid trusted ∧
  state.pending = none ∧ state.halted = false ∧ PermitBound trusted source ∧
  source.name ∉ state.consumed ∧
  state.reservedAttempts + trusted.sessionAttempts ≤ trusted.poolAttempts

instance issueGuardDecidable (trusted supplied : AuthorityPolicy) (expectedHead currentHead : String)
    (state : AuthorityState) (source : Permit) :
    Decidable (IssueGuard trusted supplied expectedHead currentHead state source) := by
  unfold IssueGuard
  infer_instance

def issue (trusted supplied : AuthorityPolicy) (expectedHead currentHead : String)
    (state : AuthorityState) (source : Permit) : Option AuthorityState :=
  if IssueGuard trusted supplied expectedHead currentHead state source then
    some { state with
      nextSerial := state.nextSerial + 1
      reservedAttempts := state.reservedAttempts + trusted.sessionAttempts
      pending := some (issuedLease trusted source state.nextSerial)
      liveLease := some (issuedLease trusted source state.nextSerial) }
  else none

theorem issued_spec (trusted supplied : AuthorityPolicy) (expectedHead currentHead : String)
    (state next : AuthorityState) (source : Permit)
    (issued : issue trusted supplied expectedHead currentHead state source = some next) :
    IssueGuard trusted supplied expectedHead currentHead state source ∧
    next = { state with
      nextSerial := state.nextSerial + 1
      reservedAttempts := state.reservedAttempts + trusted.sessionAttempts
      pending := some (issuedLease trusted source state.nextSerial)
      liveLease := some (issuedLease trusted source state.nextSerial) } := by
  unfold issue at issued
  split at issued
  next valid => exact ⟨valid, (Option.some.inj issued).symm⟩
  next invalid => cases issued

theorem issued_construct (trusted supplied : AuthorityPolicy) (expectedHead currentHead : String)
    (state : AuthorityState) (source : Permit)
    (valid : IssueGuard trusted supplied expectedHead currentHead state source) :
    issue trusted supplied expectedHead currentHead state source =
      some { state with
        nextSerial := state.nextSerial + 1
        reservedAttempts := state.reservedAttempts + trusted.sessionAttempts
        pending := some (issuedLease trusted source state.nextSerial)
        liveLease := some (issuedLease trusted source state.nextSerial) } := by
  simp only [issue, valid, if_true]

theorem self_policy_refused (trusted supplied : AuthorityPolicy) (expectedHead currentHead : String)
    (state : AuthorityState) (source : Permit) (different : supplied ≠ trusted) :
    issue trusted supplied expectedHead currentHead state source = none := by
  have invalid : ¬ IssueGuard trusted supplied expectedHead currentHead state source :=
    fun valid => different valid.1
  simp only [issue, invalid, if_false]

theorem stale_head_refused (trusted supplied : AuthorityPolicy) (expectedHead currentHead : String)
    (state : AuthorityState) (source : Permit) (different : expectedHead ≠ currentHead) :
    issue trusted supplied expectedHead currentHead state source = none := by
  have invalid : ¬ IssueGuard trusted supplied expectedHead currentHead state source :=
    fun valid => different valid.2.1
  simp only [issue, invalid, if_false]

theorem unpermitted_source_refused (trusted supplied : AuthorityPolicy) (expectedHead currentHead : String)
    (state : AuthorityState) (source : Permit) (outside : source ∉ trusted.sources) :
    issue trusted supplied expectedHead currentHead state source = none := by
  have invalid : ¬ IssueGuard trusted supplied expectedHead currentHead state source :=
    fun valid => outside valid.2.2.2.2.2.1.1
  simp only [issue, invalid, if_false]

theorem outstanding_lease_refused (trusted supplied : AuthorityPolicy) (expectedHead currentHead : String)
    (state : AuthorityState) (source : Permit) (pending : state.pending ≠ none) :
    issue trusted supplied expectedHead currentHead state source = none := by
  have invalid : ¬ IssueGuard trusted supplied expectedHead currentHead state source :=
    fun valid => pending valid.2.2.2.1
  simp only [issue, invalid, if_false]

theorem consumed_source_refused (trusted supplied : AuthorityPolicy) (expectedHead currentHead : String)
    (state : AuthorityState) (source : Permit) (consumed : source.name ∈ state.consumed) :
    issue trusted supplied expectedHead currentHead state source = none := by
  have invalid : ¬ IssueGuard trusted supplied expectedHead currentHead state source :=
    fun valid => valid.2.2.2.2.2.2.1 consumed
  simp only [issue, invalid, if_false]

theorem insufficient_pool_refused (trusted supplied : AuthorityPolicy) (expectedHead currentHead : String)
    (state : AuthorityState) (source : Permit)
    (insufficient : trusted.poolAttempts < state.reservedAttempts + trusted.sessionAttempts) :
    issue trusted supplied expectedHead currentHead state source = none := by
  have invalid : ¬ IssueGuard trusted supplied expectedHead currentHead state source := by
    intro valid
    exact Nat.not_le_of_lt insufficient valid.2.2.2.2.2.2.2
  simp only [issue, invalid, if_false]

theorem issued_grant_scope (policy : AuthorityPolicy) (source : Permit) :
    (issuedGrant policy source).binding = source.binding ∧
    (issuedGrant policy source).candidateLimit = policy.candidateCredits ∧
    (issuedGrant policy source).costLimit = 112 * policy.sessionAttempts := ⟨rfl, rfl, rfl⟩

theorem issued_semantics_fixed (trusted supplied : AuthorityPolicy) (expectedHead currentHead : String)
    (state next : AuthorityState) (source : Permit)
    (issued : issue trusted supplied expectedHead currentHead state source = some next) :
    source.binding.catalog = trusted.catalog ∧ source.binding.evaluator = trusted.evaluator ∧
    source.objective = trusted.objective ∧ source.evaluatorCode = trusted.evaluatorCode := by
  have bound := (issued_spec trusted supplied expectedHead currentHead state next source issued).1.2.2.2.2.2.1
  exact ⟨bound.2.1, bound.2.2.1, bound.2.2.2.1, bound.2.2.2.2.1⟩

theorem issued_initial_checkpoint (trusted supplied : AuthorityPolicy) (expectedHead currentHead : String)
    (state next : AuthorityState) (source : Permit)
    (issued : issue trusted supplied expectedHead currentHead state source = some next) :
    source.initial = Phase17Controller.initial trusted.candidateCredits ∧ source.checkpoint ≠ "" := by
  have bound := (issued_spec trusted supplied expectedHead currentHead state next source issued).1.2.2.2.2.2.1
  exact ⟨bound.2.2.2.2.2.1, bound.2.2.2.2.2.2.1⟩

theorem issued_exact_reservation (trusted supplied : AuthorityPolicy) (expectedHead currentHead : String)
    (state next : AuthorityState) (source : Permit)
    (issued : issue trusted supplied expectedHead currentHead state source = some next) :
    next.reservedAttempts = state.reservedAttempts + trusted.sessionAttempts ∧
    next.pending = some (issuedLease trusted source state.nextSerial) ∧
    next.nextSerial = state.nextSerial + 1 := by
  rw [(issued_spec trusted supplied expectedHead currentHead state next source issued).2]
  exact ⟨rfl, rfl, rfl⟩

theorem issued_within_pool (trusted supplied : AuthorityPolicy) (expectedHead currentHead : String)
    (state next : AuthorityState) (source : Permit)
    (issued : issue trusted supplied expectedHead currentHead state source = some next) :
    next.reservedAttempts ≤ trusted.poolAttempts := by
  rw [(issued_exact_reservation trusted supplied expectedHead currentHead state next source issued).1]
  exact (issued_spec trusted supplied expectedHead currentHead state next source issued).1.2.2.2.2.2.2.2

theorem issued_cost_not_refunded (trusted supplied : AuthorityPolicy) (expectedHead currentHead : String)
    (state next : AuthorityState) (source : Permit)
    (issued : issue trusted supplied expectedHead currentHead state source = some next) :
    reservedCost next = reservedCost state + 112 * trusted.sessionAttempts := by
  simp only [reservedCost,
    (issued_exact_reservation trusted supplied expectedHead currentHead state next source issued).1,
    Nat.mul_add]

theorem issued_vector_exact (trusted supplied : AuthorityPolicy) (expectedHead currentHead : String)
    (state next : AuthorityState) (source : Permit)
    (issued : issue trusted supplied expectedHead currentHead state source = some next) :
    reservedVector next = List.zipWith Nat.add (reservedVector state)
      [trusted.sessionAttempts, 2 * trusted.sessionAttempts,
        8 * trusted.sessionAttempts, 8 * trusted.sessionAttempts] := by
  simp only [reservedVector,
    (issued_exact_reservation trusted supplied expectedHead currentHead state next source issued).1,
    Nat.mul_add, List.zipWith_cons_cons, List.zipWith_nil_left]
  rfl

abbrev Contexts := Permit → Phase17Provenance.Context
abbrev Evaluators := Permit → List Nat → Nat → Bool

/-- A session may complete after an accepted result, a controller terminal, or
    a denied next declared reference attempt. A mere inspected prefix does not
    become complete by submitting a fresh checkpoint hash. -/
def SessionStopped (lease : Lease) (context : Phase17Provenance.Context)
    (final : ExecutionState) : Prop :=
  match Phase17Controller.decision context final.controller with
  | some .awaitRoot | some .searchExhausted | some .resourceExhausted => True
  | some (.evaluate _) => reserveTrial lease.grant final.spent 2 = none
  | _ => False

instance sessionStoppedDecidable (lease : Lease) (context : Phase17Provenance.Context)
    (final : ExecutionState) : Decidable (SessionStopped lease context final) := by
  unfold SessionStopped
  split <;> infer_instance

/-- Completion uses the evaluator selected outside the request. It cannot accept
    a caller-supplied Boolean table or an unverified replacement checkpoint. -/
def CompletionValid (policy : AuthorityPolicy) (contexts : Contexts) (evaluators : Evaluators)
    (state : AuthorityState) (result : Completion) : Prop :=
  state.pending = some result.lease ∧ state.halted = false ∧
  result.lease.authority = policy.authority ∧ result.lease.policy = policy.policy ∧
  PermitBound policy result.lease.source ∧
  result.lease.grant = issuedGrant policy result.lease.source ∧ result.checkpoint ≠ "" ∧
  authorizedReplay result.lease.grant result.lease.grant result.lease.source.binding
    (contexts result.lease.source) (evaluators result.lease.source) 2
    ⟨result.lease.source.initial, []⟩ result.observations = some result.execution ∧
  SessionStopped result.lease (contexts result.lease.source) result.execution ∧
  result.lease.source.name ∉ state.consumed ∧ state.liveLease = some result.lease

instance completionValidDecidable (policy : AuthorityPolicy) (contexts : Contexts)
    (evaluators : Evaluators) (state : AuthorityState) (result : Completion) :
    Decidable (CompletionValid policy contexts evaluators state result) := by
  unfold CompletionValid
  infer_instance

def complete (policy : AuthorityPolicy) (contexts : Contexts) (evaluators : Evaluators)
    (expectedHead currentHead : String) (state : AuthorityState) (result : Completion) :
    Option AuthorityState :=
  if expectedHead = currentHead ∧ CompletionValid policy contexts evaluators state result then
    some { state with
      pending := none
      liveLease := none
      consumed := state.consumed ++ [result.lease.source.name]
      completed := state.completed ++ [result] }
  else none

theorem completed_spec (policy : AuthorityPolicy) (contexts : Contexts) (evaluators : Evaluators)
    (expectedHead currentHead : String) (state next : AuthorityState) (result : Completion)
    (completed : complete policy contexts evaluators expectedHead currentHead state result = some next) :
    expectedHead = currentHead ∧ CompletionValid policy contexts evaluators state result ∧
    next = { state with
      pending := none
      liveLease := none
      consumed := state.consumed ++ [result.lease.source.name]
      completed := state.completed ++ [result] } := by
  unfold complete at completed
  split at completed
  next valid => exact ⟨valid.1, valid.2, (Option.some.inj completed).symm⟩
  next invalid => cases completed

theorem completed_construct (policy : AuthorityPolicy) (contexts : Contexts) (evaluators : Evaluators)
    (head : String) (state : AuthorityState) (result : Completion)
    (valid : CompletionValid policy contexts evaluators state result) :
    complete policy contexts evaluators head head state result =
      some { state with
        pending := none
        liveLease := none
        consumed := state.consumed ++ [result.lease.source.name]
        completed := state.completed ++ [result] } := by
  simp [complete, valid]

theorem unissued_completion_refused (policy : AuthorityPolicy) (contexts : Contexts)
    (evaluators : Evaluators) (expectedHead currentHead : String) (state : AuthorityState)
    (result : Completion) (unissued : state.pending ≠ some result.lease) :
    complete policy contexts evaluators expectedHead currentHead state result = none := by
  have invalid : ¬ CompletionValid policy contexts evaluators state result := fun h => unissued h.1
  simp [complete, invalid]

theorem completed_exact_retention (policy : AuthorityPolicy) (contexts : Contexts)
    (evaluators : Evaluators) (expectedHead currentHead : String) (state next : AuthorityState)
    (result : Completion)
    (completed : complete policy contexts evaluators expectedHead currentHead state result = some next) :
    next.reservedAttempts = state.reservedAttempts ∧ next.nextSerial = state.nextSerial ∧
    next.pending = none ∧ next.consumed = state.consumed ++ [result.lease.source.name] ∧
    next.completed = state.completed ++ [result] := by
  rw [(completed_spec policy contexts evaluators expectedHead currentHead state next result completed).2.2]
  exact ⟨rfl, rfl, rfl, rfl, rfl⟩

theorem completed_cost_not_refunded (policy : AuthorityPolicy) (contexts : Contexts)
    (evaluators : Evaluators) (expectedHead currentHead : String) (state next : AuthorityState)
    (result : Completion)
    (completed : complete policy contexts evaluators expectedHead currentHead state result = some next) :
    reservedCost next = reservedCost state := by
  unfold reservedCost
  rw [(completed_exact_retention policy contexts evaluators expectedHead currentHead state next result completed).1]

theorem completed_vector_not_refunded (policy : AuthorityPolicy) (contexts : Contexts)
    (evaluators : Evaluators) (expectedHead currentHead : String) (state next : AuthorityState)
    (result : Completion)
    (completed : complete policy contexts evaluators expectedHead currentHead state result = some next) :
    reservedVector next = reservedVector state := by
  simp only [reservedVector,
    (completed_exact_retention policy contexts evaluators expectedHead currentHead state next result completed).1]

theorem completed_source_consumed (policy : AuthorityPolicy) (contexts : Contexts)
    (evaluators : Evaluators) (expectedHead currentHead : String) (state next : AuthorityState)
    (result : Completion)
    (completed : complete policy contexts evaluators expectedHead currentHead state result = some next) :
    result.lease.source.name ∈ next.consumed := by
  rw [(completed_exact_retention policy contexts evaluators expectedHead currentHead state next result completed).2.2.2.1]
  simp only [List.mem_append, List.mem_singleton, or_true]

theorem completed_no_replay (policy : AuthorityPolicy) (contexts : Contexts)
    (evaluators : Evaluators) (expectedHead currentHead : String) (state next : AuthorityState)
    (result : Completion)
    (completed : complete policy contexts evaluators expectedHead currentHead state result = some next)
    (followingHead : String) :
    complete policy contexts evaluators followingHead followingHead next result = none := by
  apply unissued_completion_refused
  rw [(completed_exact_retention policy contexts evaluators expectedHead currentHead state next result completed).2.2.1]
  simp

theorem completed_truthful_controller (policy : AuthorityPolicy) (contexts : Contexts)
    (evaluators : Evaluators) (expectedHead currentHead : String) (state next : AuthorityState)
    (result : Completion)
    (completed : complete policy contexts evaluators expectedHead currentHead state result = some next) :
    truthfulReplay (contexts result.lease.source) (evaluators result.lease.source)
      result.lease.source.initial result.observations = some result.execution.controller := by
  have valid := (completed_spec policy contexts evaluators expectedHead currentHead state next result completed).2.1
  exact authorized_replay_projects _ _ _ _ _ _ _ _ _ valid.2.2.2.2.2.2.2.1

theorem completed_controller_projection (policy : AuthorityPolicy) (contexts : Contexts)
    (evaluators : Evaluators) (expectedHead currentHead : String) (state next : AuthorityState)
    (result : Completion)
    (completed : complete policy contexts evaluators expectedHead currentHead state result = some next) :
    Phase17Controller.replay (contexts result.lease.source) result.lease.source.initial
      result.observations = some result.execution.controller :=
  truthful_replay_projects _ _ _ _ _
    (completed_truthful_controller policy contexts evaluators expectedHead currentHead state next result completed)

theorem completed_controller_invariant (policy : AuthorityPolicy) (contexts : Contexts)
    (evaluators : Evaluators) (expectedHead currentHead : String) (state next : AuthorityState)
    (result : Completion) (shape : Phase17Controller.ContextShape (contexts result.lease.source))
    (completed : complete policy contexts evaluators expectedHead currentHead state result = some next) :
    Phase17Controller.Invariant result.execution.controller := by
  have valid := (completed_spec policy contexts evaluators expectedHead currentHead state next result completed).2.1
  have replayed := completed_truthful_controller policy contexts evaluators expectedHead currentHead state next result completed
  rw [valid.2.2.2.2.1.2.2.2.2.2.1] at replayed
  exact truthful_replay_invariant _ shape _ _ _ _ replayed

theorem completed_exact_work (policy : AuthorityPolicy) (contexts : Contexts)
    (evaluators : Evaluators) (expectedHead currentHead : String) (state next : AuthorityState)
    (result : Completion)
    (completed : complete policy contexts evaluators expectedHead currentHead state result = some next) :
    result.execution.spent = traceCharges 2 result.observations := by
  have valid := (completed_spec policy contexts evaluators expectedHead currentHead state next result completed).2.1
  exact authorized_replay_exact_charges _ _ _ _ _ _ _ _ _ valid.2.2.2.2.2.2.2.1

theorem completed_within_issued_envelope (policy : AuthorityPolicy) (contexts : Contexts)
    (evaluators : Evaluators) (expectedHead currentHead : String) (state next : AuthorityState)
    (result : Completion)
    (completed : complete policy contexts evaluators expectedHead currentHead state result = some next) :
    Phase17Resource.Fits (issuedGrant policy result.lease.source).policy result.execution.spent := by
  have valid := (completed_spec policy contexts evaluators expectedHead currentHead state next result completed).2.1
  have fits := (authorized_replay_within_policy _ _ _ _ _ _ _ _ _
    valid.2.2.2.2.2.2.2.1).2
  rw [valid.2.2.2.2.2.1] at fits
  exact fits

theorem completed_actual_cost_bound (policy : AuthorityPolicy) (contexts : Contexts)
    (evaluators : Evaluators) (expectedHead currentHead : String) (state next : AuthorityState)
    (result : Completion)
    (completed : complete policy contexts evaluators expectedHead currentHead state result = some next) :
    Phase17Resource.totalCost result.execution.spent ≤ 112 * policy.sessionAttempts :=
  (completed_within_issued_envelope policy contexts evaluators expectedHead currentHead
    state next result completed).1

/-- No receipt or refund is synthesized for an interrupted pending session. -/
def interrupt (state : AuthorityState) : AuthorityState := { state with halted := true }

def stop (state : AuthorityState) : Option AuthorityState :=
  if state.pending = none ∧ state.halted = false then some (interrupt state) else none

theorem stop_retains_accounting (state next : AuthorityState) (stopped : stop state = some next) :
    next.reservedAttempts = state.reservedAttempts ∧ next.pending = none ∧ next.halted = true := by
  unfold stop at stopped
  split at stopped
  next valid =>
    have same : interrupt state = next := Option.some.inj stopped
    subst next
    exact ⟨rfl, valid.1, rfl⟩
  next invalid => cases stopped

theorem pending_stop_refused (state : AuthorityState) (pending : state.pending ≠ none) :
    stop state = none := by simp [stop, pending]

def DenyGuard (trusted supplied : AuthorityPolicy) (expectedHead currentHead : String)
    (state : AuthorityState) (source : Permit) : Prop :=
  supplied = trusted ∧ expectedHead = currentHead ∧ PolicyValid trusted ∧
  state.pending = none ∧ state.halted = false ∧ PermitBound trusted source ∧
  source.name ∉ state.consumed ∧
  trusted.poolAttempts < state.reservedAttempts + trusted.sessionAttempts

instance denyGuardDecidable (trusted supplied : AuthorityPolicy) (expectedHead currentHead : String)
    (state : AuthorityState) (source : Permit) :
    Decidable (DenyGuard trusted supplied expectedHead currentHead state source) := by
  unfold DenyGuard
  infer_instance

def deny (trusted supplied : AuthorityPolicy) (expectedHead currentHead : String)
    (state : AuthorityState) (source : Permit) : Option AuthorityState :=
  if DenyGuard trusted supplied expectedHead currentHead state source then
    some (interrupt state)
  else none

theorem denied_spec (trusted supplied : AuthorityPolicy) (expectedHead currentHead : String)
    (state next : AuthorityState) (source : Permit)
    (denied : deny trusted supplied expectedHead currentHead state source = some next) :
    DenyGuard trusted supplied expectedHead currentHead state source ∧ next = interrupt state := by
  unfold deny at denied
  split at denied
  next valid => exact ⟨valid, (Option.some.inj denied).symm⟩
  next invalid => cases denied

theorem denied_no_new_reservation (trusted supplied : AuthorityPolicy) (expectedHead currentHead : String)
    (state next : AuthorityState) (source : Permit)
    (denied : deny trusted supplied expectedHead currentHead state source = some next) :
    next.reservedAttempts = state.reservedAttempts ∧ next.nextSerial = state.nextSerial ∧
    next.pending = state.pending ∧ next.completed = state.completed := by
  rw [(denied_spec trusted supplied expectedHead currentHead state next source denied).2]
  exact ⟨rfl, rfl, rfl, rfl⟩

theorem denied_is_insufficient (trusted supplied : AuthorityPolicy) (expectedHead currentHead : String)
    (state next : AuthorityState) (source : Permit)
    (denied : deny trusted supplied expectedHead currentHead state source = some next) :
    issue trusted supplied expectedHead currentHead state source = none :=
  insufficient_pool_refused trusted supplied expectedHead currentHead state source
    (denied_spec trusted supplied expectedHead currentHead state next source denied).1.2.2.2.2.2.2.2

/-- Reading durable records restores no live process ownership. -/
def reopen (state : AuthorityState) : AuthorityState := { state with liveLease := none }

theorem reopened_state_retains_charges (state : AuthorityState) :
    (reopen state).pending = state.pending ∧
    (reopen state).reservedAttempts = state.reservedAttempts ∧
    (reopen state).consumed = state.consumed := ⟨rfl, rfl, rfl⟩

theorem reopened_pending_no_completion (policy : AuthorityPolicy) (contexts : Contexts)
    (evaluators : Evaluators) (expectedHead currentHead : String) (state : AuthorityState)
    (result : Completion) :
    complete policy contexts evaluators expectedHead currentHead (reopen state) result = none := by
  have invalid : ¬ CompletionValid policy contexts evaluators (reopen state) result := by
    intro valid
    have impossible := valid.2.2.2.2.2.2.2.2.2.2
    cases impossible
  simp [complete, invalid]

theorem interrupted_pending_retained (state : AuthorityState) :
    (interrupt state).pending = state.pending ∧
    (interrupt state).reservedAttempts = state.reservedAttempts ∧
    (interrupt state).completed = state.completed := ⟨rfl, rfl, rfl⟩

theorem interrupted_issuance_refused (trusted supplied : AuthorityPolicy) (expectedHead currentHead : String)
    (state : AuthorityState) (source : Permit) :
    issue trusted supplied expectedHead currentHead (interrupt state) source = none := by
  have invalid : ¬ IssueGuard trusted supplied expectedHead currentHead (interrupt state) source := by
    intro valid
    have contradiction := valid.2.2.2.2.1
    cases contradiction
  simp only [issue, invalid, if_false]

theorem interrupted_completion_refused (policy : AuthorityPolicy) (contexts : Contexts)
    (evaluators : Evaluators) (expectedHead currentHead : String) (state : AuthorityState)
    (result : Completion) :
    complete policy contexts evaluators expectedHead currentHead (interrupt state) result = none := by
  have invalid : ¬ CompletionValid policy contexts evaluators (interrupt state) result := by
    intro valid
    have contradiction := valid.2.1
    cases contradiction
  simp [complete, invalid]

theorem completed_stale_head_refused (policy : AuthorityPolicy) (contexts : Contexts)
    (evaluators : Evaluators) (expectedHead currentHead : String) (state : AuthorityState)
    (result : Completion) (stale : expectedHead ≠ currentHead) :
    complete policy contexts evaluators expectedHead currentHead state result = none := by
  simp only [complete, stale, false_and, if_false]

theorem completed_stopped (policy : AuthorityPolicy) (contexts : Contexts)
    (evaluators : Evaluators) (expectedHead currentHead : String) (state next : AuthorityState)
    (result : Completion)
    (completed : complete policy contexts evaluators expectedHead currentHead state result = some next) :
    SessionStopped result.lease (contexts result.lease.source) result.execution :=
  (completed_spec policy contexts evaluators expectedHead currentHead state next result completed).2.1.2.2.2.2.2.2.2.2.1

/-- Reachability rules are the public issuer protocol. In particular, a caller
    cannot insert an arbitrary pending lease into a reachable authority state. -/
inductive Reachable (policy : AuthorityPolicy) (contexts : Contexts) (evaluators : Evaluators) :
    AuthorityState → Prop where
  | initial : Reachable policy contexts evaluators initial
  | issue {state next : AuthorityState} (prior : Reachable policy contexts evaluators state)
      (supplied : AuthorityPolicy) (expectedHead currentHead : String) (source : Permit)
      (issued : issue policy supplied expectedHead currentHead state source = some next) :
      Reachable policy contexts evaluators next
  | complete {state next : AuthorityState} (prior : Reachable policy contexts evaluators state)
      (expectedHead currentHead : String) (result : Completion)
      (completed : complete policy contexts evaluators expectedHead currentHead state result = some next) :
      Reachable policy contexts evaluators next
  | interrupt {state : AuthorityState} (prior : Reachable policy contexts evaluators state) :
      Reachable policy contexts evaluators (interrupt state)
  | reopen {state : AuthorityState} (prior : Reachable policy contexts evaluators state) :
      Reachable policy contexts evaluators (reopen state)

theorem reachable_debit_exact (policy : AuthorityPolicy) (contexts : Contexts)
    (evaluators : Evaluators) (state : AuthorityState)
    (reachable : Reachable policy contexts evaluators state) :
    state.reservedAttempts = state.nextSerial * policy.sessionAttempts := by
  induction reachable with
  | initial => simp only [initial, Nat.zero_mul]
  | @issue priorState next prior supplied expectedHead currentHead source issued ih =>
      rcases issued_exact_reservation policy supplied expectedHead currentHead priorState next source issued with
        ⟨reserve, _, serial⟩
      rw [reserve, serial, ih, Nat.add_mul, Nat.one_mul]
  | @complete priorState next prior expectedHead currentHead result completed ih =>
      have same := completed_exact_retention policy contexts evaluators expectedHead currentHead
        priorState next result completed
      rw [same.1, same.2.1]
      exact ih
  | interrupt prior ih => exact ih
  | reopen prior ih => exact ih

theorem reachable_within_pool (policy : AuthorityPolicy) (contexts : Contexts)
    (evaluators : Evaluators) (state : AuthorityState)
    (reachable : Reachable policy contexts evaluators state) :
    state.reservedAttempts ≤ policy.poolAttempts := by
  induction reachable with
  | initial => exact Nat.zero_le _
  | @issue priorState next prior supplied expectedHead currentHead source issued ih =>
      exact issued_within_pool policy supplied expectedHead currentHead priorState next source issued
  | @complete priorState next prior expectedHead currentHead result completed ih =>
      rw [(completed_exact_retention policy contexts evaluators expectedHead currentHead priorState next
        result completed).1]
      exact ih
  | interrupt prior ih => exact ih
  | reopen prior ih => exact ih

theorem reachable_pending_issued (policy : AuthorityPolicy) (contexts : Contexts)
    (evaluators : Evaluators) (state : AuthorityState)
    (reachable : Reachable policy contexts evaluators state) (lease : Lease)
    (pending : state.pending = some lease) :
    ∃ source serial, lease = issuedLease policy source serial ∧ PermitBound policy source := by
  induction reachable with
  | initial => cases pending
  | @issue priorState next prior supplied expectedHead currentHead source issued ih =>
      have exactPending := (issued_exact_reservation policy supplied expectedHead currentHead
        priorState next source issued).2.1
      have same : lease = issuedLease policy source priorState.nextSerial := by
        rw [exactPending] at pending
        exact (Option.some.inj pending).symm
      exact ⟨source, priorState.nextSerial, same,
        (issued_spec policy supplied expectedHead currentHead priorState next source issued).1.2.2.2.2.2.1⟩
  | @complete priorState next prior expectedHead currentHead result completed ih =>
      have cleared := (completed_exact_retention policy contexts evaluators expectedHead currentHead
        priorState next result completed).2.2.1
      rw [cleared] at pending
      cases pending
  | interrupt prior ih => exact ih pending
  | reopen prior ih => exact ih pending

theorem reachable_completed_sources (policy : AuthorityPolicy) (contexts : Contexts)
    (evaluators : Evaluators) (state : AuthorityState)
    (reachable : Reachable policy contexts evaluators state) :
    state.consumed = state.completed.map (fun result => result.lease.source.name) := by
  induction reachable with
  | initial => rfl
  | @issue priorState next prior supplied expectedHead currentHead source issued ih =>
      rw [(issued_spec policy supplied expectedHead currentHead priorState next source issued).2]
      exact ih
  | @complete priorState next prior expectedHead currentHead result completed ih =>
      rw [(completed_spec policy contexts evaluators expectedHead currentHead priorState next result completed).2.2]
      simpa only [List.map_append, List.map_cons, List.map_nil] using
        congrArg (fun names => names ++ [result.lease.source.name]) ih
  | interrupt prior ih => exact ih
  | reopen prior ih => exact ih

theorem reachable_no_duplicate_sources (policy : AuthorityPolicy) (contexts : Contexts)
    (evaluators : Evaluators) (state : AuthorityState)
    (reachable : Reachable policy contexts evaluators state) : state.consumed.Nodup := by
  induction reachable with
  | initial => exact List.nodup_nil
  | @issue priorState next prior supplied expectedHead currentHead source issued ih =>
      rw [(issued_spec policy supplied expectedHead currentHead priorState next source issued).2]
      exact ih
  | @complete priorState next prior expectedHead currentHead result completed ih =>
      have valid := (completed_spec policy contexts evaluators expectedHead currentHead priorState next result completed).2.1
      have fresh := valid.2.2.2.2.2.2.2.2.2.1
      rw [(completed_exact_retention policy contexts evaluators expectedHead currentHead priorState next result completed).2.2.2.1]
      refine List.nodup_append.mpr ⟨ih, by simp, ?_⟩
      intro a member b singleton equal
      have ident : b = result.lease.source.name := List.mem_singleton.mp singleton
      exact fresh (ident ▸ equal ▸ member)
  | interrupt prior ih => exact ih
  | reopen prior ih => exact ih

/-- These sums count the declared reference tariff of completed AH sessions.
    A pending session retains its entire precharged envelope; unobserved work
    is neither a completed receipt nor a refunded allowance. -/
def completedCost (state : AuthorityState) : Nat :=
  (state.completed.map (fun result => Phase17Resource.totalCost result.execution.spent)).sum

def pendingCost (policy : AuthorityPolicy) (state : AuthorityState) : Nat :=
  if state.pending.isSome then 112 * policy.sessionAttempts else 0

theorem reachable_actual_cost_reserved (policy : AuthorityPolicy) (contexts : Contexts)
    (evaluators : Evaluators) (state : AuthorityState)
    (reachable : Reachable policy contexts evaluators state) :
    completedCost state + pendingCost policy state ≤ reservedCost state := by
  induction reachable with
  | initial => simp [initial, completedCost, pendingCost, reservedCost]
  | @issue priorState next prior supplied expectedHead currentHead source issued ih =>
      have spec := issued_spec policy supplied expectedHead currentHead priorState next source issued
      have priorBudget : completedCost priorState ≤ reservedCost priorState := by
        simpa only [pendingCost, spec.1.2.2.2.1, Option.isSome_none, Bool.false_eq_true,
          if_false, Nat.add_zero] using ih
      rw [spec.2]
      simpa only [completedCost, pendingCost, reservedCost, Option.isSome_some, if_true, Nat.mul_add]
        using Nat.add_le_add_right priorBudget (112 * policy.sessionAttempts)
  | @complete priorState next prior expectedHead currentHead result completed ih =>
      have spec := completed_spec policy contexts evaluators expectedHead currentHead
        priorState next result completed
      have priorBudget : completedCost priorState + 112 * policy.sessionAttempts ≤ reservedCost priorState := by
        simpa only [pendingCost, spec.2.1.1, Option.isSome_some, if_true] using ih
      have actual := completed_actual_cost_bound policy contexts evaluators expectedHead currentHead
        priorState next result completed
      have budget := (Nat.add_le_add_left actual (completedCost priorState)).trans priorBudget
      rw [spec.2.2]
      simpa [completedCost, pendingCost, reservedCost, List.map_append, List.sum_append] using budget
  | interrupt prior ih => exact ih
  | reopen prior ih => exact ih

theorem reachable_actual_cost_within_pool (policy : AuthorityPolicy) (contexts : Contexts)
    (evaluators : Evaluators) (state : AuthorityState)
    (reachable : Reachable policy contexts evaluators state) :
    completedCost state ≤ 112 * policy.poolAttempts := by
  have reserved := reachable_actual_cost_reserved policy contexts evaluators state reachable
  calc
    completedCost state ≤ reservedCost state := by omega
    _ ≤ 112 * policy.poolAttempts :=
      Nat.mul_le_mul_left 112 (reachable_within_pool policy contexts evaluators state reachable)

end Phase17ControllerAuthority

namespace Phase17ControllerAuthorityExamples
open Phase17ProducerDomain Phase17ControllerAuthority
set_option maxRecDepth 32768
set_option maxHeartbeats 16000000
-- Exact AI authority packet SHA256: 3534a0a4559a3fa963f9aa172b9d5357450a60534eaf537153efe634aca762c0
def permit0_0 : Permit := {
  name := "af_before"
  binding := {
    source := "129a6f016eebf0d84bfde3274f05f959f593a3fe8e1fbebeae7ab7e15e1e6676"
    request := "b7f4bb2d756f6d1ed022d4ddaa993c0e3b7d41357cfd71444eb1b95ce1cdf790"
    package := "b4036b3e31a6608e30b421c08906b1e58c3e7d61fef6eb6730881c597656434e"
    history := "f0fdfc3264fded4f92ea01a33e37f232fbfafd9ec72ebad58c6517eb86c9eb1f"
    context := "5a7d2d5c7015e588902b33385ca9e7e4c679346c74faa51cc8415944bf4fecc2"
    catalog := "511a8e2783bfa6b4d2dcfda2a700967e5a9e101ba7f57d8ff6b61b164034cf5d"
    evaluator := "phase17ah.fixed-ae-least-missing-contract-ag-acceptance.v1"
  }
  model := "b2227e7f64f0db1b5a0a8a6de5bfa1f0595429270cd0fb8cb8083ce361f9e2e6"
  prefixHash := "7417b05bf51285c8b174a8672a788d2d07e270b1cb45d1fe3670450a0d6e41d9"
  initial := Phase17Controller.initial 32
  checkpoint := "e005cc9a20d0a3dd5c90cc8b571c2aa9ed9f57ef700bd3bafd6134de9f041e9c"
  frozen := "144f7661fad1484f26b38bf3fdd3ccbd856e7243d0d91bf3a9357ac71d5ee9cd"
  objective := "phase17ai.fixed-ae-least-newly-realized-meaning.v1"
  evaluatorCode := "2bb118c98da7b55102703021892c71283823a8282005684854bde7c6a193dd63" }
def permit0_1 : Permit := {
  name := "af_after"
  binding := {
    source := "3659236854fc37d749f579879be16c8795efa1019b4180d3115dc1b66b7b5b8c"
    request := "7209828e591f70e3ea3fc158b58770ed7bb6cb62a36183cae1bcd597b820f5b7"
    package := "85bebb429b27104ee1d8ffabda71acd26c44847c2dd097dea249fa3ee5d4ae02"
    history := "572ec7c9c7a2eae68502fad30cfff120cfff90a438fe7047722a656799977695"
    context := "d0a6812be0e1d9799be1069336fae7002bb0cdfe907f9ee48c76f3cbccc480b5"
    catalog := "511a8e2783bfa6b4d2dcfda2a700967e5a9e101ba7f57d8ff6b61b164034cf5d"
    evaluator := "phase17ah.fixed-ae-least-missing-contract-ag-acceptance.v1"
  }
  model := "6ebfc9fbb128e595d3dda8ff92b7e9f6cad4299c1a2680cd1f96e116568a0c87"
  prefixHash := "80bab8c75b07b37d278189eca04ae356557b295ee5eb449ae90fac950adc4742"
  initial := Phase17Controller.initial 32
  checkpoint := "be322ec824836f825ea17015dfa48b2cf4bc37415560cb6a66ebc168290e3dee"
  frozen := "2072d3b384ea6b8d96d9f59975ee933be2bac6da2ae07f0de1e8a2957d98458c"
  objective := "phase17ai.fixed-ae-least-newly-realized-meaning.v1"
  evaluatorCode := "2bb118c98da7b55102703021892c71283823a8282005684854bde7c6a193dd63" }
def policy0 : AuthorityPolicy := {
  authority := "phase17ai.reference.shared_two_sources"
  policy := "320fd437158c85ece1b56a33027c80ee5e3418aae363063683e24a85b65d116e"
  catalog := "511a8e2783bfa6b4d2dcfda2a700967e5a9e101ba7f57d8ff6b61b164034cf5d"
  objective := "phase17ai.fixed-ae-least-newly-realized-meaning.v1"
  evaluator := "phase17ah.fixed-ae-least-missing-contract-ag-acceptance.v1"
  evaluatorCode := "2bb118c98da7b55102703021892c71283823a8282005684854bde7c6a193dd63"
  candidateCredits := 32
  sessionAttempts := 32
  poolAttempts := 64
  sources := [permit0_0, permit0_1] }
theorem policy_valid0 : PolicyValid policy0 := by decide +kernel
def contexts0 (source : Permit) : Phase17Provenance.Context :=
  if source.name = "af_before" then Phase17ProducerDomainExamples.context0 else Phase17ProducerDomainExamples.context1
def evaluators0 (source : Permit) : List Nat → Nat → Bool :=
  if source.name = "af_before" then Phase17ProducerDomainExamples.evaluator0 else Phase17ProducerDomainExamples.evaluator1
def state0_0 : AuthorityState := Phase17ControllerAuthority.initial
theorem reachable0_0 : Reachable policy0 contexts0 evaluators0 state0_0 := .initial
def lease0_0 : Lease := issuedLease policy0 permit0_0 0
def capturedGrant0_0 : Grant := {
  binding := {
    source := "129a6f016eebf0d84bfde3274f05f959f593a3fe8e1fbebeae7ab7e15e1e6676"
    request := "b7f4bb2d756f6d1ed022d4ddaa993c0e3b7d41357cfd71444eb1b95ce1cdf790"
    package := "b4036b3e31a6608e30b421c08906b1e58c3e7d61fef6eb6730881c597656434e"
    history := "f0fdfc3264fded4f92ea01a33e37f232fbfafd9ec72ebad58c6517eb86c9eb1f"
    context := "5a7d2d5c7015e588902b33385ca9e7e4c679346c74faa51cc8415944bf4fecc2"
    catalog := "511a8e2783bfa6b4d2dcfda2a700967e5a9e101ba7f57d8ff6b61b164034cf5d"
    evaluator := "phase17ah.fixed-ae-least-missing-contract-ag-acceptance.v1"
  }
  candidateLimit := 32
  referenceCandidateLimit := 32
  vectorLimit := 64
  inputLimit := 256
  outputLimit := 256
  costLimit := 3584 }
theorem grant_bound0_0 : lease0_0.grant = capturedGrant0_0 := by decide +kernel
def state0_1 : AuthorityState := { state0_0 with
  nextSerial := state0_0.nextSerial + 1
  reservedAttempts := state0_0.reservedAttempts + policy0.sessionAttempts
  pending := some lease0_0
  liveLease := some lease0_0 }
theorem issue0_0 : issue policy0 policy0 "f3b0cc8fca6969ad76b09daae9b5d38e8d310136fb5c999eda2c01af23d87e47" "f3b0cc8fca6969ad76b09daae9b5d38e8d310136fb5c999eda2c01af23d87e47"
    state0_0 permit0_0 = some state0_1 := by decide +kernel
theorem reachable0_1 : Reachable policy0 contexts0 evaluators0 state0_1 :=
  .issue reachable0_0 policy0 "f3b0cc8fca6969ad76b09daae9b5d38e8d310136fb5c999eda2c01af23d87e47" "f3b0cc8fca6969ad76b09daae9b5d38e8d310136fb5c999eda2c01af23d87e47" permit0_0 issue0_0
def completion0_0 : Completion := {
  lease := lease0_0
  observations := Phase17ProducerDomainExamples.observations0
  execution := Phase17ProducerDomainExamples.state0_1
  checkpoint := "9550542820416938b77b49372bec8671b3cbdbfe6f077a09d9e417d120b2d5ee" }
theorem valid_completion0_0 : CompletionValid policy0
    contexts0 evaluators0 state0_1 completion0_0 := by
  refine ⟨by decide +kernel, by decide +kernel, by decide +kernel, by decide +kernel,
    by decide +kernel, by decide +kernel, by decide +kernel, ?_, ?_,
    by decide +kernel, by decide +kernel⟩
  · exact Phase17ProducerDomainExamples.case_first_source
  · change SessionStopped lease0_0 Phase17ProducerDomainExamples.context0 Phase17ProducerDomainExamples.state0_1
    simp only [SessionStopped, Phase17ProducerDomainExamples.terminal0]
def state0_2 : AuthorityState := { state0_1 with
  pending := none
  liveLease := none
  consumed := state0_1.consumed ++ [completion0_0.lease.source.name]
  completed := state0_1.completed ++ [completion0_0] }
theorem complete0_0 : complete policy0 contexts0 evaluators0
    "9e52ac55aba74d638bb9741d48a7253a73a6b090ce4a7002c69a9581893d4531" "9e52ac55aba74d638bb9741d48a7253a73a6b090ce4a7002c69a9581893d4531" state0_1 completion0_0 = some state0_2 :=
  completed_construct policy0 contexts0 evaluators0 "9e52ac55aba74d638bb9741d48a7253a73a6b090ce4a7002c69a9581893d4531" state0_1
    completion0_0 valid_completion0_0
theorem reachable0_2 : Reachable policy0 contexts0 evaluators0 state0_2 :=
  .complete reachable0_1 "9e52ac55aba74d638bb9741d48a7253a73a6b090ce4a7002c69a9581893d4531" "9e52ac55aba74d638bb9741d48a7253a73a6b090ce4a7002c69a9581893d4531" completion0_0 complete0_0
def state0_reopened : AuthorityState := reopen state0_2
theorem reachable0_reopened : Reachable policy0 contexts0 evaluators0 state0_reopened := .reopen reachable0_2
def lease0_1 : Lease := issuedLease policy0 permit0_1 1
def capturedGrant0_1 : Grant := {
  binding := {
    source := "3659236854fc37d749f579879be16c8795efa1019b4180d3115dc1b66b7b5b8c"
    request := "7209828e591f70e3ea3fc158b58770ed7bb6cb62a36183cae1bcd597b820f5b7"
    package := "85bebb429b27104ee1d8ffabda71acd26c44847c2dd097dea249fa3ee5d4ae02"
    history := "572ec7c9c7a2eae68502fad30cfff120cfff90a438fe7047722a656799977695"
    context := "d0a6812be0e1d9799be1069336fae7002bb0cdfe907f9ee48c76f3cbccc480b5"
    catalog := "511a8e2783bfa6b4d2dcfda2a700967e5a9e101ba7f57d8ff6b61b164034cf5d"
    evaluator := "phase17ah.fixed-ae-least-missing-contract-ag-acceptance.v1"
  }
  candidateLimit := 32
  referenceCandidateLimit := 32
  vectorLimit := 64
  inputLimit := 256
  outputLimit := 256
  costLimit := 3584 }
theorem grant_bound0_1 : lease0_1.grant = capturedGrant0_1 := by decide +kernel
def state0_3 : AuthorityState := { state0_reopened with
  nextSerial := state0_reopened.nextSerial + 1
  reservedAttempts := state0_reopened.reservedAttempts + policy0.sessionAttempts
  pending := some lease0_1
  liveLease := some lease0_1 }
theorem issue0_1 : issue policy0 policy0 "fb3d4674fc1b52f57e2c431b04f8145436e0d9129ba58876df7dfc2ce068592f" "fb3d4674fc1b52f57e2c431b04f8145436e0d9129ba58876df7dfc2ce068592f"
    state0_reopened permit0_1 = some state0_3 := by decide +kernel
theorem reachable0_3 : Reachable policy0 contexts0 evaluators0 state0_3 :=
  .issue reachable0_reopened policy0 "fb3d4674fc1b52f57e2c431b04f8145436e0d9129ba58876df7dfc2ce068592f" "fb3d4674fc1b52f57e2c431b04f8145436e0d9129ba58876df7dfc2ce068592f" permit0_1 issue0_1
def completion0_1 : Completion := {
  lease := lease0_1
  observations := Phase17ProducerDomainExamples.observations1
  execution := Phase17ProducerDomainExamples.state1_8
  checkpoint := "9ceaeb2122f513e53ca46aedfee6e53f4f99a4cb373121c7bcd84a71aa4a9a24" }
theorem valid_completion0_1 : CompletionValid policy0
    contexts0 evaluators0 state0_3 completion0_1 := by
  refine ⟨by decide +kernel, by decide +kernel, by decide +kernel, by decide +kernel,
    by decide +kernel, by decide +kernel, by decide +kernel, ?_, ?_,
    by decide +kernel, by decide +kernel⟩
  · exact Phase17ProducerDomainExamples.case_second_source
  · change SessionStopped lease0_1 Phase17ProducerDomainExamples.context1 Phase17ProducerDomainExamples.state1_8
    simp only [SessionStopped, Phase17ProducerDomainExamples.terminal1]
def state0_4 : AuthorityState := { state0_3 with
  pending := none
  liveLease := none
  consumed := state0_3.consumed ++ [completion0_1.lease.source.name]
  completed := state0_3.completed ++ [completion0_1] }
theorem complete0_1 : complete policy0 contexts0 evaluators0
    "bd0a086831d9c9009fd598373831d5b78ec7cfb5694cbcade77b6b3d2e75d002" "bd0a086831d9c9009fd598373831d5b78ec7cfb5694cbcade77b6b3d2e75d002" state0_3 completion0_1 = some state0_4 :=
  completed_construct policy0 contexts0 evaluators0 "bd0a086831d9c9009fd598373831d5b78ec7cfb5694cbcade77b6b3d2e75d002" state0_3
    completion0_1 valid_completion0_1
theorem reachable0_4 : Reachable policy0 contexts0 evaluators0 state0_4 :=
  .complete reachable0_3 "bd0a086831d9c9009fd598373831d5b78ec7cfb5694cbcade77b6b3d2e75d002" "bd0a086831d9c9009fd598373831d5b78ec7cfb5694cbcade77b6b3d2e75d002" completion0_1 complete0_1
def state0_5 : AuthorityState := interrupt state0_4
theorem stop0 : stop state0_4 = some state0_5 := by decide +kernel
theorem reachable0_5 : Reachable policy0 contexts0 evaluators0 state0_5 :=
  .interrupt reachable0_4
theorem case_shared_two_sources : Reachable policy0 contexts0 evaluators0 state0_5 ∧
    reservedVector state0_5 = [64, 128, 512, 512] ∧ reservedCost state0_5 = 7168 ∧
    state0_5.nextSerial = 2 ∧ state0_5.consumed = ["af_before", "af_after"] :=
  ⟨reachable0_5, by decide +kernel, by decide +kernel, by decide +kernel, by decide +kernel⟩
def permit1_0 : Permit := {
  name := "af_before"
  binding := {
    source := "129a6f016eebf0d84bfde3274f05f959f593a3fe8e1fbebeae7ab7e15e1e6676"
    request := "b7f4bb2d756f6d1ed022d4ddaa993c0e3b7d41357cfd71444eb1b95ce1cdf790"
    package := "b4036b3e31a6608e30b421c08906b1e58c3e7d61fef6eb6730881c597656434e"
    history := "f0fdfc3264fded4f92ea01a33e37f232fbfafd9ec72ebad58c6517eb86c9eb1f"
    context := "5a7d2d5c7015e588902b33385ca9e7e4c679346c74faa51cc8415944bf4fecc2"
    catalog := "511a8e2783bfa6b4d2dcfda2a700967e5a9e101ba7f57d8ff6b61b164034cf5d"
    evaluator := "phase17ah.fixed-ae-least-missing-contract-ag-acceptance.v1"
  }
  model := "b2227e7f64f0db1b5a0a8a6de5bfa1f0595429270cd0fb8cb8083ce361f9e2e6"
  prefixHash := "7417b05bf51285c8b174a8672a788d2d07e270b1cb45d1fe3670450a0d6e41d9"
  initial := Phase17Controller.initial 32
  checkpoint := "e005cc9a20d0a3dd5c90cc8b571c2aa9ed9f57ef700bd3bafd6134de9f041e9c"
  frozen := "144f7661fad1484f26b38bf3fdd3ccbd856e7243d0d91bf3a9357ac71d5ee9cd"
  objective := "phase17ai.fixed-ae-least-newly-realized-meaning.v1"
  evaluatorCode := "2bb118c98da7b55102703021892c71283823a8282005684854bde7c6a193dd63" }
def permit1_1 : Permit := {
  name := "af_after"
  binding := {
    source := "3659236854fc37d749f579879be16c8795efa1019b4180d3115dc1b66b7b5b8c"
    request := "7209828e591f70e3ea3fc158b58770ed7bb6cb62a36183cae1bcd597b820f5b7"
    package := "85bebb429b27104ee1d8ffabda71acd26c44847c2dd097dea249fa3ee5d4ae02"
    history := "572ec7c9c7a2eae68502fad30cfff120cfff90a438fe7047722a656799977695"
    context := "d0a6812be0e1d9799be1069336fae7002bb0cdfe907f9ee48c76f3cbccc480b5"
    catalog := "511a8e2783bfa6b4d2dcfda2a700967e5a9e101ba7f57d8ff6b61b164034cf5d"
    evaluator := "phase17ah.fixed-ae-least-missing-contract-ag-acceptance.v1"
  }
  model := "6ebfc9fbb128e595d3dda8ff92b7e9f6cad4299c1a2680cd1f96e116568a0c87"
  prefixHash := "80bab8c75b07b37d278189eca04ae356557b295ee5eb449ae90fac950adc4742"
  initial := Phase17Controller.initial 32
  checkpoint := "be322ec824836f825ea17015dfa48b2cf4bc37415560cb6a66ebc168290e3dee"
  frozen := "2072d3b384ea6b8d96d9f59975ee933be2bac6da2ae07f0de1e8a2957d98458c"
  objective := "phase17ai.fixed-ae-least-newly-realized-meaning.v1"
  evaluatorCode := "2bb118c98da7b55102703021892c71283823a8282005684854bde7c6a193dd63" }
def policy1 : AuthorityPolicy := {
  authority := "phase17ai.reference.aggregate_denial"
  policy := "c2036e1ef39b3f9d7463537fbe66babf7a43d19dbeff5669e9a4ab21d7691883"
  catalog := "511a8e2783bfa6b4d2dcfda2a700967e5a9e101ba7f57d8ff6b61b164034cf5d"
  objective := "phase17ai.fixed-ae-least-newly-realized-meaning.v1"
  evaluator := "phase17ah.fixed-ae-least-missing-contract-ag-acceptance.v1"
  evaluatorCode := "2bb118c98da7b55102703021892c71283823a8282005684854bde7c6a193dd63"
  candidateCredits := 32
  sessionAttempts := 32
  poolAttempts := 32
  sources := [permit1_0, permit1_1] }
theorem policy_valid1 : PolicyValid policy1 := by decide +kernel
def contexts1 (source : Permit) : Phase17Provenance.Context :=
  if source.name = "af_before" then Phase17ProducerDomainExamples.context0 else Phase17ProducerDomainExamples.context1
def evaluators1 (source : Permit) : List Nat → Nat → Bool :=
  if source.name = "af_before" then Phase17ProducerDomainExamples.evaluator0 else Phase17ProducerDomainExamples.evaluator1
def state1_0 : AuthorityState := Phase17ControllerAuthority.initial
theorem reachable1_0 : Reachable policy1 contexts1 evaluators1 state1_0 := .initial
def lease1_0 : Lease := issuedLease policy1 permit1_0 0
def capturedGrant1_0 : Grant := {
  binding := {
    source := "129a6f016eebf0d84bfde3274f05f959f593a3fe8e1fbebeae7ab7e15e1e6676"
    request := "b7f4bb2d756f6d1ed022d4ddaa993c0e3b7d41357cfd71444eb1b95ce1cdf790"
    package := "b4036b3e31a6608e30b421c08906b1e58c3e7d61fef6eb6730881c597656434e"
    history := "f0fdfc3264fded4f92ea01a33e37f232fbfafd9ec72ebad58c6517eb86c9eb1f"
    context := "5a7d2d5c7015e588902b33385ca9e7e4c679346c74faa51cc8415944bf4fecc2"
    catalog := "511a8e2783bfa6b4d2dcfda2a700967e5a9e101ba7f57d8ff6b61b164034cf5d"
    evaluator := "phase17ah.fixed-ae-least-missing-contract-ag-acceptance.v1"
  }
  candidateLimit := 32
  referenceCandidateLimit := 32
  vectorLimit := 64
  inputLimit := 256
  outputLimit := 256
  costLimit := 3584 }
theorem grant_bound1_0 : lease1_0.grant = capturedGrant1_0 := by decide +kernel
def state1_1 : AuthorityState := { state1_0 with
  nextSerial := state1_0.nextSerial + 1
  reservedAttempts := state1_0.reservedAttempts + policy1.sessionAttempts
  pending := some lease1_0
  liveLease := some lease1_0 }
theorem issue1_0 : issue policy1 policy1 "931559debcf826fe53bead6b77aca4b251c38496f394dc60e3291f510a43a6bd" "931559debcf826fe53bead6b77aca4b251c38496f394dc60e3291f510a43a6bd"
    state1_0 permit1_0 = some state1_1 := by decide +kernel
theorem reachable1_1 : Reachable policy1 contexts1 evaluators1 state1_1 :=
  .issue reachable1_0 policy1 "931559debcf826fe53bead6b77aca4b251c38496f394dc60e3291f510a43a6bd" "931559debcf826fe53bead6b77aca4b251c38496f394dc60e3291f510a43a6bd" permit1_0 issue1_0
def completion1_0 : Completion := {
  lease := lease1_0
  observations := Phase17ProducerDomainExamples.observations0
  execution := Phase17ProducerDomainExamples.state0_1
  checkpoint := "9550542820416938b77b49372bec8671b3cbdbfe6f077a09d9e417d120b2d5ee" }
theorem valid_completion1_0 : CompletionValid policy1
    contexts1 evaluators1 state1_1 completion1_0 := by
  refine ⟨by decide +kernel, by decide +kernel, by decide +kernel, by decide +kernel,
    by decide +kernel, by decide +kernel, by decide +kernel, ?_, ?_,
    by decide +kernel, by decide +kernel⟩
  · exact Phase17ProducerDomainExamples.case_first_source
  · change SessionStopped lease1_0 Phase17ProducerDomainExamples.context0 Phase17ProducerDomainExamples.state0_1
    simp only [SessionStopped, Phase17ProducerDomainExamples.terminal0]
def state1_2 : AuthorityState := { state1_1 with
  pending := none
  liveLease := none
  consumed := state1_1.consumed ++ [completion1_0.lease.source.name]
  completed := state1_1.completed ++ [completion1_0] }
theorem complete1_0 : complete policy1 contexts1 evaluators1
    "0c1cfdf8ad6fc920e9bb8a4cbfa75685e0f572f458215fe03841b2b050a67d69" "0c1cfdf8ad6fc920e9bb8a4cbfa75685e0f572f458215fe03841b2b050a67d69" state1_1 completion1_0 = some state1_2 :=
  completed_construct policy1 contexts1 evaluators1 "0c1cfdf8ad6fc920e9bb8a4cbfa75685e0f572f458215fe03841b2b050a67d69" state1_1
    completion1_0 valid_completion1_0
theorem reachable1_2 : Reachable policy1 contexts1 evaluators1 state1_2 :=
  .complete reachable1_1 "0c1cfdf8ad6fc920e9bb8a4cbfa75685e0f572f458215fe03841b2b050a67d69" "0c1cfdf8ad6fc920e9bb8a4cbfa75685e0f572f458215fe03841b2b050a67d69" completion1_0 complete1_0
def state1_3 : AuthorityState := interrupt state1_2
theorem deny1 : deny policy1 policy1 "d2121a35d6b76439f5975b0fa8391bb5d791cbc137165f95d235d051c0bb68b2" "d2121a35d6b76439f5975b0fa8391bb5d791cbc137165f95d235d051c0bb68b2"
    state1_2 permit1_1 = some state1_3 := by decide +kernel
theorem reachable1_3 : Reachable policy1 contexts1 evaluators1 state1_3 :=
  .interrupt reachable1_2
theorem case_aggregate_denial : Reachable policy1 contexts1 evaluators1 state1_3 ∧
    reservedVector state1_3 = [32, 64, 256, 256] ∧ reservedCost state1_3 = 3584 ∧
    state1_3.nextSerial = 1 ∧ state1_3.consumed = ["af_before"] :=
  ⟨reachable1_3, by decide +kernel, by decide +kernel, by decide +kernel, by decide +kernel⟩
def permit2_0 : Permit := {
  name := "af_before"
  binding := {
    source := "129a6f016eebf0d84bfde3274f05f959f593a3fe8e1fbebeae7ab7e15e1e6676"
    request := "b7f4bb2d756f6d1ed022d4ddaa993c0e3b7d41357cfd71444eb1b95ce1cdf790"
    package := "b4036b3e31a6608e30b421c08906b1e58c3e7d61fef6eb6730881c597656434e"
    history := "f0fdfc3264fded4f92ea01a33e37f232fbfafd9ec72ebad58c6517eb86c9eb1f"
    context := "5a7d2d5c7015e588902b33385ca9e7e4c679346c74faa51cc8415944bf4fecc2"
    catalog := "511a8e2783bfa6b4d2dcfda2a700967e5a9e101ba7f57d8ff6b61b164034cf5d"
    evaluator := "phase17ah.fixed-ae-least-missing-contract-ag-acceptance.v1"
  }
  model := "b2227e7f64f0db1b5a0a8a6de5bfa1f0595429270cd0fb8cb8083ce361f9e2e6"
  prefixHash := "7417b05bf51285c8b174a8672a788d2d07e270b1cb45d1fe3670450a0d6e41d9"
  initial := Phase17Controller.initial 32
  checkpoint := "e005cc9a20d0a3dd5c90cc8b571c2aa9ed9f57ef700bd3bafd6134de9f041e9c"
  frozen := "144f7661fad1484f26b38bf3fdd3ccbd856e7243d0d91bf3a9357ac71d5ee9cd"
  objective := "phase17ai.fixed-ae-least-newly-realized-meaning.v1"
  evaluatorCode := "2bb118c98da7b55102703021892c71283823a8282005684854bde7c6a193dd63" }
def permit2_1 : Permit := {
  name := "af_after"
  binding := {
    source := "3659236854fc37d749f579879be16c8795efa1019b4180d3115dc1b66b7b5b8c"
    request := "7209828e591f70e3ea3fc158b58770ed7bb6cb62a36183cae1bcd597b820f5b7"
    package := "85bebb429b27104ee1d8ffabda71acd26c44847c2dd097dea249fa3ee5d4ae02"
    history := "572ec7c9c7a2eae68502fad30cfff120cfff90a438fe7047722a656799977695"
    context := "d0a6812be0e1d9799be1069336fae7002bb0cdfe907f9ee48c76f3cbccc480b5"
    catalog := "511a8e2783bfa6b4d2dcfda2a700967e5a9e101ba7f57d8ff6b61b164034cf5d"
    evaluator := "phase17ah.fixed-ae-least-missing-contract-ag-acceptance.v1"
  }
  model := "6ebfc9fbb128e595d3dda8ff92b7e9f6cad4299c1a2680cd1f96e116568a0c87"
  prefixHash := "80bab8c75b07b37d278189eca04ae356557b295ee5eb449ae90fac950adc4742"
  initial := Phase17Controller.initial 32
  checkpoint := "be322ec824836f825ea17015dfa48b2cf4bc37415560cb6a66ebc168290e3dee"
  frozen := "2072d3b384ea6b8d96d9f59975ee933be2bac6da2ae07f0de1e8a2957d98458c"
  objective := "phase17ai.fixed-ae-least-newly-realized-meaning.v1"
  evaluatorCode := "2bb118c98da7b55102703021892c71283823a8282005684854bde7c6a193dd63" }
def policy2 : AuthorityPolicy := {
  authority := "phase17ai.reference.reference_stop"
  policy := "f6bfb181240f14eb5582f7386f9386de65c212c9af07946f24ff79475f7cf782"
  catalog := "511a8e2783bfa6b4d2dcfda2a700967e5a9e101ba7f57d8ff6b61b164034cf5d"
  objective := "phase17ai.fixed-ae-least-newly-realized-meaning.v1"
  evaluator := "phase17ah.fixed-ae-least-missing-contract-ag-acceptance.v1"
  evaluatorCode := "2bb118c98da7b55102703021892c71283823a8282005684854bde7c6a193dd63"
  candidateCredits := 32
  sessionAttempts := 3
  poolAttempts := 3
  sources := [permit2_0, permit2_1] }
theorem policy_valid2 : PolicyValid policy2 := by decide +kernel
def contexts2 (source : Permit) : Phase17Provenance.Context :=
  if source.name = "af_before" then Phase17ProducerDomainExamples.context0 else Phase17ProducerDomainExamples.context1
def evaluators2 (source : Permit) : List Nat → Nat → Bool :=
  if source.name = "af_before" then Phase17ProducerDomainExamples.evaluator0 else Phase17ProducerDomainExamples.evaluator1
def state2_0 : AuthorityState := Phase17ControllerAuthority.initial
theorem reachable2_0 : Reachable policy2 contexts2 evaluators2 state2_0 := .initial
def lease2_0 : Lease := issuedLease policy2 permit2_1 0
def capturedGrant2_0 : Grant := {
  binding := {
    source := "3659236854fc37d749f579879be16c8795efa1019b4180d3115dc1b66b7b5b8c"
    request := "7209828e591f70e3ea3fc158b58770ed7bb6cb62a36183cae1bcd597b820f5b7"
    package := "85bebb429b27104ee1d8ffabda71acd26c44847c2dd097dea249fa3ee5d4ae02"
    history := "572ec7c9c7a2eae68502fad30cfff120cfff90a438fe7047722a656799977695"
    context := "d0a6812be0e1d9799be1069336fae7002bb0cdfe907f9ee48c76f3cbccc480b5"
    catalog := "511a8e2783bfa6b4d2dcfda2a700967e5a9e101ba7f57d8ff6b61b164034cf5d"
    evaluator := "phase17ah.fixed-ae-least-missing-contract-ag-acceptance.v1"
  }
  candidateLimit := 32
  referenceCandidateLimit := 3
  vectorLimit := 6
  inputLimit := 24
  outputLimit := 24
  costLimit := 336 }
theorem grant_bound2_0 : lease2_0.grant = capturedGrant2_0 := by decide +kernel
def state2_1 : AuthorityState := { state2_0 with
  nextSerial := state2_0.nextSerial + 1
  reservedAttempts := state2_0.reservedAttempts + policy2.sessionAttempts
  pending := some lease2_0
  liveLease := some lease2_0 }
theorem issue2_0 : issue policy2 policy2 "9524bf96e148006b1888c2071c58af28a8aebebe8f44a7ba84ae57ad7f0e0246" "9524bf96e148006b1888c2071c58af28a8aebebe8f44a7ba84ae57ad7f0e0246"
    state2_0 permit2_1 = some state2_1 := by decide +kernel
theorem reachable2_1 : Reachable policy2 contexts2 evaluators2 state2_1 :=
  .issue reachable2_0 policy2 "9524bf96e148006b1888c2071c58af28a8aebebe8f44a7ba84ae57ad7f0e0246" "9524bf96e148006b1888c2071c58af28a8aebebe8f44a7ba84ae57ad7f0e0246" permit2_1 issue2_0
def completion2_0 : Completion := {
  lease := lease2_0
  observations := Phase17ProducerDomainExamples.observations4
  execution := Phase17ProducerDomainExamples.state4_3
  checkpoint := "44d44ff798f8a4afd8906c297df68f766ce9db11c0832246bd69b2d752a7ed0c" }
theorem valid_completion2_0 : CompletionValid policy2
    contexts2 evaluators2 state2_1 completion2_0 := by
  refine ⟨by decide +kernel, by decide +kernel, by decide +kernel, by decide +kernel,
    by decide +kernel, by decide +kernel, by decide +kernel, ?_, ?_,
    by decide +kernel, by decide +kernel⟩
  · exact Phase17ProducerDomainExamples.case_second_source_resource_stop
  · change SessionStopped lease2_0 Phase17ProducerDomainExamples.context4 Phase17ProducerDomainExamples.state4_3
    simpa only [SessionStopped, Phase17ProducerDomainExamples.terminal4] using
      (show reserveTrial lease2_0.grant Phase17ProducerDomainExamples.state4_3.spent 2 = none from by decide +kernel)
def state2_2 : AuthorityState := { state2_1 with
  pending := none
  liveLease := none
  consumed := state2_1.consumed ++ [completion2_0.lease.source.name]
  completed := state2_1.completed ++ [completion2_0] }
theorem complete2_0 : complete policy2 contexts2 evaluators2
    "c5a62093f7bfcabab134c9a48c97121b6e149b9fa5908bd852ef7e87cfd628e9" "c5a62093f7bfcabab134c9a48c97121b6e149b9fa5908bd852ef7e87cfd628e9" state2_1 completion2_0 = some state2_2 :=
  completed_construct policy2 contexts2 evaluators2 "c5a62093f7bfcabab134c9a48c97121b6e149b9fa5908bd852ef7e87cfd628e9" state2_1
    completion2_0 valid_completion2_0
theorem reachable2_2 : Reachable policy2 contexts2 evaluators2 state2_2 :=
  .complete reachable2_1 "c5a62093f7bfcabab134c9a48c97121b6e149b9fa5908bd852ef7e87cfd628e9" "c5a62093f7bfcabab134c9a48c97121b6e149b9fa5908bd852ef7e87cfd628e9" completion2_0 complete2_0
def state2_3 : AuthorityState := interrupt state2_2
theorem stop2 : stop state2_2 = some state2_3 := by decide +kernel
theorem reachable2_3 : Reachable policy2 contexts2 evaluators2 state2_3 :=
  .interrupt reachable2_2
theorem case_reference_stop : Reachable policy2 contexts2 evaluators2 state2_3 ∧
    reservedVector state2_3 = [3, 6, 24, 24] ∧ reservedCost state2_3 = 336 ∧
    state2_3.nextSerial = 1 ∧ state2_3.consumed = ["af_after"] :=
  ⟨reachable2_3, by decide +kernel, by decide +kernel, by decide +kernel, by decide +kernel⟩
def permit3_0 : Permit := {
  name := "af_before"
  binding := {
    source := "129a6f016eebf0d84bfde3274f05f959f593a3fe8e1fbebeae7ab7e15e1e6676"
    request := "ef0ff78dea49d008f1bd22e27c306ba0fc75b1e6028b3e8604e5e302cfa867df"
    package := "b4036b3e31a6608e30b421c08906b1e58c3e7d61fef6eb6730881c597656434e"
    history := "f0fdfc3264fded4f92ea01a33e37f232fbfafd9ec72ebad58c6517eb86c9eb1f"
    context := "085d6972d3f8d363e6438dba3f191ec3534168ca43de4c0bfb04b32d72539d77"
    catalog := "511a8e2783bfa6b4d2dcfda2a700967e5a9e101ba7f57d8ff6b61b164034cf5d"
    evaluator := "phase17ah.fixed-ae-least-missing-contract-ag-acceptance.v1"
  }
  model := "b2227e7f64f0db1b5a0a8a6de5bfa1f0595429270cd0fb8cb8083ce361f9e2e6"
  prefixHash := "6392593f9d1d7ccfc2edf79572388a3b54671ffe7f30b626e31daa3f0357554a"
  initial := Phase17Controller.initial 4
  checkpoint := "20b8a64cef1227763e667cd66b1f88fea4a15eff56e0cd6b6dd6b168efc7d4c7"
  frozen := "144f7661fad1484f26b38bf3fdd3ccbd856e7243d0d91bf3a9357ac71d5ee9cd"
  objective := "phase17ai.fixed-ae-least-newly-realized-meaning.v1"
  evaluatorCode := "2bb118c98da7b55102703021892c71283823a8282005684854bde7c6a193dd63" }
def unselected3_0Context : Phase17Provenance.Context := {
  generator := "90391521aefb1f2daec066d84da943c307f9eab85fae2296107b9b13afb3b3a1"
  parentPackage := "b4036b3e31a6608e30b421c08906b1e58c3e7d61fef6eb6730881c597656434e"
  contextHash := "085d6972d3f8d363e6438dba3f191ec3534168ca43de4c0bfb04b32d72539d77"
  transcriptHash := "f0fdfc3264fded4f92ea01a33e37f232fbfafd9ec72ebad58c6517eb86c9eb1f"
  credits := 4
  offset := 15
  rows := [{ key := "07882cf428b45d8397698adabb728a847bbf96b0e3c6926d3f1d4d4088f9d72e", family := 6, baseScore := 18960, ties := [4067414476079179602, 1143632732032864453, 16861598504112071679, 15384015252139269389, 18310767783104935697] }, { key := "079464d9ed285120d4387203f867a81e2dc97fe24ac634cf7ba700ce52d468a4", family := 2, baseScore := 19470, ties := [13482613594219277050, 5469217485581563474, 10257095991479891409, 11151343383861201678, 6906722214430827221] }, { key := "0d313e2585c77f2d844d93fcbbf8e74c7422e6544804620d11e68ce2645d500b", family := 4, baseScore := 19508, ties := [13612602070832589573, 6136353106604528740, 4022276120731408208, 12508910830223200717, 1574879216556344613] }, { key := "12a42ce65856dd02f802c8029f2daf19578cd8bfbeddfe37e29997cde1b62ac8", family := 7, baseScore := 19496, ties := [18123742346597796565, 15121617768547652000, 9661723255900939993, 17347352500181138570, 9764312206222838187] }, { key := "1306284a64e0735108c79ea5b4f8e54070732f4e2401dd8b493be69169e7d5e9", family := 5, baseScore := 19472, ties := [10095354839296612401, 8343001766639313493, 6876812003579993481, 3289013143446074041, 6972954723787526484] }, { key := "22ff5f6188a0ba1bcacd416080df083ced5f1a9bff3e543769bd3389b6f167d9", family := 5, baseScore := 19507, ties := [9556741496105481830, 6521138168365943428, 1258425305099817531, 4549872774356196954, 4291925470698513438] }, { key := "27ed4335d4ad263283fd2219e3a1a351664a138191c78661dbe48445a82ed69e", family := 6, baseScore := 18944, ties := [6105405153937009509, 11969193772550575404, 2107889702351671880, 17584414889085524363, 18211847158849932671] }, { key := "3020a4a7bd86574b5692bd42e9077c2b79ede2b188e4cb0169ad8930ae8d10de", family := 7, baseScore := 19472, ties := [12674795809107633111, 8735109151167820480, 14124372684497732999, 349763004355627024, 3862256201561958792] }, { key := "450dfe81045365620206674af70ae6ec90c0c4fa8ec3a4f502f05bc9add7e52b", family := 3, baseScore := 19456, ties := [5370746308605319879, 6164419903216892597, 3508704870563999890, 489383493529843381, 4653336060926829210] }, { key := "4e1ab17b7adc4c2677d527190317442f8a1ed0cfdd07a52a061995480dfc3f60", family := 6, baseScore := 18957, ties := [8893161776254545735, 1891202225067676371, 8053596535700481150, 11571226399141116229, 7141746405652483532] }, { key := "50f6bd6b08806bf9b8df6945e3d7e9adfffbff2a22961008915cfe959f0a6c4a", family := 7, baseScore := 19499, ties := [9679313212414016952, 9089937520646898793, 12306276790941400625, 16390441772389930777, 18111387248499519432] }, { key := "5c48f5d5dbc7d5139f0e40836f503591aa7c3071642889e31c0aacd9efe91b73", family := 5, baseScore := 19477, ties := [1686630956470550365, 12348276636288601349, 7265205885161631248, 18323645672495100349, 9229631209322088685] }, { key := "641a0a443c3ecdf7694f6f2564baaac751dde5ff9232538110d03c5de6583ee8", family := 4, baseScore := 19461, ties := [11232546787352037718, 7537786374361850087, 12719215349116130922, 11365499214359821264, 10243774792397307870] }, { key := "653ba4de5e0906ed5243fb78736da3abd4aa77383140d24a146680f31ec09990", family := 1, baseScore := 19462, ties := [9760102627151895911, 4269376462830578271, 18168365562687126899, 3792784763376343727, 6995317989452125285] }, { key := "6ee86ea419985236275b631dacc0290507fff0e068190c6a3728674baaa1a98b", family := 2, baseScore := 19501, ties := [11802090995992626256, 8791636913409424657, 11924440666518944324, 12132760461712722275, 17301751405184835073] }, { key := "720a201348d162d103690550d5350535aaab543c183ed82b5defc90858adf40e", family := 4, baseScore := 19479, ties := [6612759970106008385, 13514820826156495252, 9190821328972898399, 18362970414329912214, 5722062530679313706] }, { key := "77727c49241dd038565749ba479fb19152d512b554ae590dd7c7ccc4c62b3828", family := 3, baseScore := 19481, ties := [11926746517751336661, 14541035729376544619, 12208184956818782405, 5512244166577998159, 7334111558886353376] }, { key := "81829dac0cb4609c35cd5e305ca88afdc7b7156566adbee4baac888b7b9d28e4", family := 0, baseScore := 19464, ties := [16518332695240133985, 568756587103267924, 17795617196010485594, 2607642015827511779, 17156279897057633711] }, { key := "87a0db958fe5c35c6ec49a670f961e0046fee892ec1793f1631472aecb4d769e", family := 2, baseScore := 19453, ties := [5901464650357490299, 5579327280384594495, 253034272031291111, 17104554580747672489, 12425396319390355629] }, { key := "8b9157eb7084166b6636e5d7bb57efa71cd929f09c3f2f8414ef0122fe8e6577", family := 1, baseScore := 19468, ties := [3506042129886810465, 9214908235753750225, 15725083257317116685, 14781502037922715866, 1677427951469179458] }, { key := "8e01c54efa55b98f3428eb3a12c6182bc96551e16ec14689bd538abc3708255c", family := 1, baseScore := 19501, ties := [1879747030503297813, 4231031703955250555, 17600132949162241598, 1333975721071733513, 7648874207536453584] }, { key := "9ba71bd7d621c2d02b13d9742ff9ec52bd1e1c97f48652cd1f5aec0b314ca36b", family := 1, baseScore := 19505, ties := [7975309339964375512, 6550324127271030517, 10476331802804152171, 5119642984881144404, 10217516072512059925] }, { key := "a403651a9e50607d7ca9601b212a6ad9c528b8888a314b3828667da158592d48", family := 5, baseScore := 19464, ties := [18202378182033565274, 7075035538533698310, 8365198709351112436, 15877617147546882527, 2314023604113503548] }, { key := "a6ae460c5df16a8d6c208e4dcbdeb4e3b37954b0796c459017e94f0e66b9efc8", family := 6, baseScore := 18998, ties := [7987115727688652744, 15487032685309554364, 8955788139047961274, 4889142308567352162, 2670098398921227938] }, { key := "b01857227df43043988ff2d7fb601ff629a8d71c340d84bcb09c750fc9b2fc49", family := 0, baseScore := 19481, ties := [8607332645611834342, 10531034799799481139, 12160336227489894607, 5096808467431222401, 6770608227068374516] }, { key := "b72f4059d60d2d4a5afdb76ad62defc3f62d4fe96db51c457750cae5abd377d9", family := 2, baseScore := 19466, ties := [6669701029395109215, 5856957169175542674, 1487578234978173705, 17790081782434534677, 5413377251973930479] }, { key := "b81a18b500c7ca818a616e63196cc3addd2145ec980e1d91aad9a1ca062db182", family := 4, baseScore := 19457, ties := [10586155769928991059, 5241797536902138588, 16423289231373946654, 142738471961533350, 14854837108458276609] }, { key := "b9b957bc4120f3c6b154a89750163c9416ab8e8cc3c7f1b79ec58897993d585e", family := 7, baseScore := 19460, ties := [1095656587249731324, 14290496605635945461, 14234615779449105149, 12457199882864015916, 1490997132813081410] }, { key := "be392ca3fddd70b2d0f02bc0baf2d4fec4ee3c425ecd06d634e5574ce7fa2518", family := 3, baseScore := 19450, ties := [17299591439524412511, 13939404801979848755, 13414325344623980203, 4586071826011419681, 9331775315561780333] }, { key := "c5a6780c1de5bdd5fa049ede1d7f2deb98235e648266a02d91af32ce97ade1aa", family := 3, baseScore := 19504, ties := [5671031807740714614, 5438000299292591274, 801492386737468072, 5637620230803865938, 11012347029589691182] }, { key := "c7e8b8e3c29edc92452562acebcfc5c9574a2f7e94d07d7ef3f4068f4010f823", family := 0, baseScore := 19541, ties := [3513290731377645443, 14365763167848964155, 14096591963623069607, 16289509393212528963, 2079474529533731873] }, { key := "e3c13e868433bc76a733a0a6119c7f4f5c755a95b02b6d671095ec1739566c52", family := 0, baseScore := 19501, ties := [1423082885769156603, 7092168848720255596, 258275870616071943, 1926726872688281918, 6275646520615301522] }] }
def unselected3_0Domain : Domain := ⟨unselected3_0Context, [("07882cf428b45d8397698adabb728a847bbf96b0e3c6926d3f1d4d4088f9d72e", { family := 6, variant := 3, a := (-12), b := (-11) }), ("079464d9ed285120d4387203f867a81e2dc97fe24ac634cf7ba700ce52d468a4", { family := 2, variant := 1, a := 12, b := 9 }), ("0d313e2585c77f2d844d93fcbbf8e74c7422e6544804620d11e68ce2645d500b", { family := 4, variant := 1, a := 12, b := 13 }), ("12a42ce65856dd02f802c8029f2daf19578cd8bfbeddfe37e29997cde1b62ac8", { family := 7, variant := 3, a := (-14), b := 12 }), ("1306284a64e0735108c79ea5b4f8e54070732f4e2401dd8b493be69169e7d5e9", { family := 5, variant := 0, a := 7, b := 7 }), ("22ff5f6188a0ba1bcacd416080df083ced5f1a9bff3e543769bd3389b6f167d9", { family := 5, variant := 2, a := (-8), b := 13 }), ("27ed4335d4ad263283fd2219e3a1a351664a138191c78661dbe48445a82ed69e", { family := 6, variant := 0, a := (-6), b := (-12) }), ("3020a4a7bd86574b5692bd42e9077c2b79ede2b188e4cb0169ad8930ae8d10de", { family := 7, variant := 1, a := (-6), b := 9 }), ("450dfe81045365620206674af70ae6ec90c0c4fa8ec3a4f502f05bc9add7e52b", { family := 3, variant := 1, a := 3, b := (-5) }), ("4e1ab17b7adc4c2677d527190317442f8a1ed0cfdd07a52a061995480dfc3f60", { family := 6, variant := 2, a := (-12), b := 3 }), ("50f6bd6b08806bf9b8df6945e3d7e9adfffbff2a22961008915cfe959f0a6c4a", { family := 7, variant := 2, a := 11, b := 1 }), ("5c48f5d5dbc7d5139f0e40836f503591aa7c3071642889e31c0aacd9efe91b73", { family := 5, variant := 3, a := 7, b := 16 }), ("641a0a443c3ecdf7694f6f2564baaac751dde5ff9232538110d03c5de6583ee8", { family := 4, variant := 3, a := 0, b := 8 }), ("653ba4de5e0906ed5243fb78736da3abd4aa77383140d24a146680f31ec09990", { family := 1, variant := 0, a := (-16), b := (-4) }), ("6ee86ea419985236275b631dacc0290507fff0e068190c6a3728674baaa1a98b", { family := 2, variant := 0, a := (-3), b := 10 }), ("720a201348d162d103690550d5350535aaab543c183ed82b5defc90858adf40e", { family := 4, variant := 0, a := 9, b := (-1) }), ("77727c49241dd038565749ba479fb19152d512b554ae590dd7c7ccc4c62b3828", { family := 3, variant := 0, a := 3, b := (-10) }), ("81829dac0cb4609c35cd5e305ca88afdc7b7156566adbee4baac888b7b9d28e4", { family := 0, variant := 2, a := (-1), b := (-12) }), ("87a0db958fe5c35c6ec49a670f961e0046fee892ec1793f1631472aecb4d769e", { family := 2, variant := 2, a := 10, b := 8 }), ("8b9157eb7084166b6636e5d7bb57efa71cd929f09c3f2f8414ef0122fe8e6577", { family := 1, variant := 3, a := (-7), b := 3 }), ("8e01c54efa55b98f3428eb3a12c6182bc96551e16ec14689bd538abc3708255c", { family := 1, variant := 1, a := 0, b := (-16) }), ("9ba71bd7d621c2d02b13d9742ff9ec52bd1e1c97f48652cd1f5aec0b314ca36b", { family := 1, variant := 2, a := (-8), b := 2 }), ("a403651a9e50607d7ca9601b212a6ad9c528b8888a314b3828667da158592d48", { family := 5, variant := 1, a := (-7), b := (-4) }), ("a6ae460c5df16a8d6c208e4dcbdeb4e3b37954b0796c459017e94f0e66b9efc8", { family := 6, variant := 1, a := (-16), b := 6 }), ("b01857227df43043988ff2d7fb601ff629a8d71c340d84bcb09c750fc9b2fc49", { family := 0, variant := 3, a := 1, b := (-4) }), ("b72f4059d60d2d4a5afdb76ad62defc3f62d4fe96db51c457750cae5abd377d9", { family := 2, variant := 3, a := (-1), b := (-3) }), ("b81a18b500c7ca818a616e63196cc3addd2145ec980e1d91aad9a1ca062db182", { family := 4, variant := 2, a := 14, b := (-5) }), ("b9b957bc4120f3c6b154a89750163c9416ab8e8cc3c7f1b79ec58897993d585e", { family := 7, variant := 0, a := (-4), b := 10 }), ("be392ca3fddd70b2d0f02bc0baf2d4fec4ee3c425ecd06d634e5574ce7fa2518", { family := 3, variant := 2, a := 16, b := 16 }), ("c5a6780c1de5bdd5fa049ede1d7f2deb98235e648266a02d91af32ce97ade1aa", { family := 3, variant := 3, a := (-1), b := 13 }), ("c7e8b8e3c29edc92452562acebcfc5c9574a2f7e94d07d7ef3f4068f4010f823", { family := 0, variant := 0, a := (-6), b := 7 }), ("e3c13e868433bc76a733a0a6119c7f4f5c755a95b02b6d671095ec1739566c52", { family := 0, variant := 1, a := 2, b := 7 })]⟩
def unselected3_0Identities : List String := ["", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "99b0b32ecc034a27fdba3f3472f7c297517ff65529229dc969ab5f1d76646850", "", "", "", "", "", "", "88fd55762f90166277ec264ca7eca6d6b35b6a4e818b869caabc2d55452078cc", "", "", "", "", "", "25a2b9d3c9c6ac36b69746215326b22083a0cb2e49046d4fbfce5156be679382", "96d63f3eecba085a98295735a513b812597ec5eceb3277d05ebfbcd796addb68"]
def unselected3_0Contexts (_source : Phase17Finite.State) := unselected3_0Context
def unselected3_0Builder (prior : List Nat) (index task : Nat) : Phase17TruthfulSuccessor.Offer :=
  constructOffer Phase17ProducerDomainExamples.fixed Phase17ProducerDomainExamples.source0 unselected3_0Domain (unselected3_0Identities.getD index "")
    prior index task (Phase17ProducerDomainExamples.cumulativeCharges prior)
def unselected3_0Evaluator : List Nat → Nat → Bool :=
  evaluate Phase17ProducerDomainExamples.fixed unselected3_0Contexts Phase17ProducerDomainExamples.chargesAt Phase17ProducerDomainExamples.source0 unselected3_0Domain unselected3_0Builder
def permit3_1 : Permit := {
  name := "af_after"
  binding := {
    source := "3659236854fc37d749f579879be16c8795efa1019b4180d3115dc1b66b7b5b8c"
    request := "72b9eeb5a48133255144abb0d3b28f2272e7477d51dc7878169afdee8ee3bc7d"
    package := "85bebb429b27104ee1d8ffabda71acd26c44847c2dd097dea249fa3ee5d4ae02"
    history := "572ec7c9c7a2eae68502fad30cfff120cfff90a438fe7047722a656799977695"
    context := "5f0c2149ea0a5aad7a5d3cbb364a23ecc6cacc8a74898b8fa00982eb9f4effa2"
    catalog := "511a8e2783bfa6b4d2dcfda2a700967e5a9e101ba7f57d8ff6b61b164034cf5d"
    evaluator := "phase17ah.fixed-ae-least-missing-contract-ag-acceptance.v1"
  }
  model := "6ebfc9fbb128e595d3dda8ff92b7e9f6cad4299c1a2680cd1f96e116568a0c87"
  prefixHash := "38386c9715aed301fdf5ba35d870648a3f9effa040e4e761da8a62d286422af3"
  initial := Phase17Controller.initial 4
  checkpoint := "991c256143d59498267dfb1ffab2bece4a3b2f901f1eab4578cdcd1afd4a0ddd"
  frozen := "2072d3b384ea6b8d96d9f59975ee933be2bac6da2ae07f0de1e8a2957d98458c"
  objective := "phase17ai.fixed-ae-least-newly-realized-meaning.v1"
  evaluatorCode := "2bb118c98da7b55102703021892c71283823a8282005684854bde7c6a193dd63" }
def policy3 : AuthorityPolicy := {
  authority := "phase17ai.reference.credit_stop"
  policy := "148adc2cf242df24ac7840e46b0d58693cf96eca8eede665df64755c0ed44086"
  catalog := "511a8e2783bfa6b4d2dcfda2a700967e5a9e101ba7f57d8ff6b61b164034cf5d"
  objective := "phase17ai.fixed-ae-least-newly-realized-meaning.v1"
  evaluator := "phase17ah.fixed-ae-least-missing-contract-ag-acceptance.v1"
  evaluatorCode := "2bb118c98da7b55102703021892c71283823a8282005684854bde7c6a193dd63"
  candidateCredits := 4
  sessionAttempts := 32
  poolAttempts := 32
  sources := [permit3_0, permit3_1] }
theorem policy_valid3 : PolicyValid policy3 := by decide +kernel
def contexts3 (source : Permit) : Phase17Provenance.Context :=
  if source.name = "af_before" then unselected3_0Context else Phase17ProducerDomainExamples.context2
def evaluators3 (source : Permit) : List Nat → Nat → Bool :=
  if source.name = "af_before" then unselected3_0Evaluator else Phase17ProducerDomainExamples.evaluator2
def state3_0 : AuthorityState := Phase17ControllerAuthority.initial
theorem reachable3_0 : Reachable policy3 contexts3 evaluators3 state3_0 := .initial
def lease3_0 : Lease := issuedLease policy3 permit3_1 0
def capturedGrant3_0 : Grant := {
  binding := {
    source := "3659236854fc37d749f579879be16c8795efa1019b4180d3115dc1b66b7b5b8c"
    request := "72b9eeb5a48133255144abb0d3b28f2272e7477d51dc7878169afdee8ee3bc7d"
    package := "85bebb429b27104ee1d8ffabda71acd26c44847c2dd097dea249fa3ee5d4ae02"
    history := "572ec7c9c7a2eae68502fad30cfff120cfff90a438fe7047722a656799977695"
    context := "5f0c2149ea0a5aad7a5d3cbb364a23ecc6cacc8a74898b8fa00982eb9f4effa2"
    catalog := "511a8e2783bfa6b4d2dcfda2a700967e5a9e101ba7f57d8ff6b61b164034cf5d"
    evaluator := "phase17ah.fixed-ae-least-missing-contract-ag-acceptance.v1"
  }
  candidateLimit := 4
  referenceCandidateLimit := 32
  vectorLimit := 64
  inputLimit := 256
  outputLimit := 256
  costLimit := 3584 }
theorem grant_bound3_0 : lease3_0.grant = capturedGrant3_0 := by decide +kernel
def state3_1 : AuthorityState := { state3_0 with
  nextSerial := state3_0.nextSerial + 1
  reservedAttempts := state3_0.reservedAttempts + policy3.sessionAttempts
  pending := some lease3_0
  liveLease := some lease3_0 }
theorem issue3_0 : issue policy3 policy3 "a4348f9e3643d5d46aae7c7f5ffc3995b62e0dc9b090522935e120d01c43771d" "a4348f9e3643d5d46aae7c7f5ffc3995b62e0dc9b090522935e120d01c43771d"
    state3_0 permit3_1 = some state3_1 := by decide +kernel
theorem reachable3_1 : Reachable policy3 contexts3 evaluators3 state3_1 :=
  .issue reachable3_0 policy3 "a4348f9e3643d5d46aae7c7f5ffc3995b62e0dc9b090522935e120d01c43771d" "a4348f9e3643d5d46aae7c7f5ffc3995b62e0dc9b090522935e120d01c43771d" permit3_1 issue3_0
def completion3_0 : Completion := {
  lease := lease3_0
  observations := Phase17ProducerDomainExamples.observations2
  execution := Phase17ProducerDomainExamples.state2_4
  checkpoint := "27aeda1e3222de27cf20a00f2c98dedc1727a996d22edfc2680707944192f2e8" }
theorem valid_completion3_0 : CompletionValid policy3
    contexts3 evaluators3 state3_1 completion3_0 := by
  refine ⟨by decide +kernel, by decide +kernel, by decide +kernel, by decide +kernel,
    by decide +kernel, by decide +kernel, by decide +kernel, ?_, ?_,
    by decide +kernel, by decide +kernel⟩
  · exact Phase17ProducerDomainExamples.case_second_source_credit_stop
  · change SessionStopped lease3_0 Phase17ProducerDomainExamples.context2 Phase17ProducerDomainExamples.state2_4
    simp only [SessionStopped, Phase17ProducerDomainExamples.terminal2]
def state3_2 : AuthorityState := { state3_1 with
  pending := none
  liveLease := none
  consumed := state3_1.consumed ++ [completion3_0.lease.source.name]
  completed := state3_1.completed ++ [completion3_0] }
theorem complete3_0 : complete policy3 contexts3 evaluators3
    "e3fbaeb253ee78cad1189fbaf1a06939d50693e94f834b4813149a901af117d8" "e3fbaeb253ee78cad1189fbaf1a06939d50693e94f834b4813149a901af117d8" state3_1 completion3_0 = some state3_2 :=
  completed_construct policy3 contexts3 evaluators3 "e3fbaeb253ee78cad1189fbaf1a06939d50693e94f834b4813149a901af117d8" state3_1
    completion3_0 valid_completion3_0
theorem reachable3_2 : Reachable policy3 contexts3 evaluators3 state3_2 :=
  .complete reachable3_1 "e3fbaeb253ee78cad1189fbaf1a06939d50693e94f834b4813149a901af117d8" "e3fbaeb253ee78cad1189fbaf1a06939d50693e94f834b4813149a901af117d8" completion3_0 complete3_0
def state3_3 : AuthorityState := interrupt state3_2
theorem stop3 : stop state3_2 = some state3_3 := by decide +kernel
theorem reachable3_3 : Reachable policy3 contexts3 evaluators3 state3_3 :=
  .interrupt reachable3_2
theorem case_credit_stop : Reachable policy3 contexts3 evaluators3 state3_3 ∧
    reservedVector state3_3 = [32, 64, 256, 256] ∧ reservedCost state3_3 = 3584 ∧
    state3_3.nextSerial = 1 ∧ state3_3.consumed = ["af_after"] :=
  ⟨reachable3_3, by decide +kernel, by decide +kernel, by decide +kernel, by decide +kernel⟩
def permit4_0 : Permit := {
  name := "af_before"
  binding := {
    source := "129a6f016eebf0d84bfde3274f05f959f593a3fe8e1fbebeae7ab7e15e1e6676"
    request := "b7f4bb2d756f6d1ed022d4ddaa993c0e3b7d41357cfd71444eb1b95ce1cdf790"
    package := "b4036b3e31a6608e30b421c08906b1e58c3e7d61fef6eb6730881c597656434e"
    history := "f0fdfc3264fded4f92ea01a33e37f232fbfafd9ec72ebad58c6517eb86c9eb1f"
    context := "5a7d2d5c7015e588902b33385ca9e7e4c679346c74faa51cc8415944bf4fecc2"
    catalog := "511a8e2783bfa6b4d2dcfda2a700967e5a9e101ba7f57d8ff6b61b164034cf5d"
    evaluator := "phase17ah.fixed-ae-least-missing-contract-ag-acceptance.v1"
  }
  model := "b2227e7f64f0db1b5a0a8a6de5bfa1f0595429270cd0fb8cb8083ce361f9e2e6"
  prefixHash := "7417b05bf51285c8b174a8672a788d2d07e270b1cb45d1fe3670450a0d6e41d9"
  initial := Phase17Controller.initial 32
  checkpoint := "e005cc9a20d0a3dd5c90cc8b571c2aa9ed9f57ef700bd3bafd6134de9f041e9c"
  frozen := "144f7661fad1484f26b38bf3fdd3ccbd856e7243d0d91bf3a9357ac71d5ee9cd"
  objective := "phase17ai.fixed-ae-least-newly-realized-meaning.v1"
  evaluatorCode := "2bb118c98da7b55102703021892c71283823a8282005684854bde7c6a193dd63" }
def permit4_1 : Permit := {
  name := "af_after"
  binding := {
    source := "3659236854fc37d749f579879be16c8795efa1019b4180d3115dc1b66b7b5b8c"
    request := "7209828e591f70e3ea3fc158b58770ed7bb6cb62a36183cae1bcd597b820f5b7"
    package := "85bebb429b27104ee1d8ffabda71acd26c44847c2dd097dea249fa3ee5d4ae02"
    history := "572ec7c9c7a2eae68502fad30cfff120cfff90a438fe7047722a656799977695"
    context := "d0a6812be0e1d9799be1069336fae7002bb0cdfe907f9ee48c76f3cbccc480b5"
    catalog := "511a8e2783bfa6b4d2dcfda2a700967e5a9e101ba7f57d8ff6b61b164034cf5d"
    evaluator := "phase17ah.fixed-ae-least-missing-contract-ag-acceptance.v1"
  }
  model := "6ebfc9fbb128e595d3dda8ff92b7e9f6cad4299c1a2680cd1f96e116568a0c87"
  prefixHash := "80bab8c75b07b37d278189eca04ae356557b295ee5eb449ae90fac950adc4742"
  initial := Phase17Controller.initial 32
  checkpoint := "be322ec824836f825ea17015dfa48b2cf4bc37415560cb6a66ebc168290e3dee"
  frozen := "2072d3b384ea6b8d96d9f59975ee933be2bac6da2ae07f0de1e8a2957d98458c"
  objective := "phase17ai.fixed-ae-least-newly-realized-meaning.v1"
  evaluatorCode := "2bb118c98da7b55102703021892c71283823a8282005684854bde7c6a193dd63" }
def policy4 : AuthorityPolicy := {
  authority := "phase17ai.reference.interrupted_reservation"
  policy := "e41399d6074c9e8f8809c35b6463081c0184ffdbf48aa7579288f9552005d78a"
  catalog := "511a8e2783bfa6b4d2dcfda2a700967e5a9e101ba7f57d8ff6b61b164034cf5d"
  objective := "phase17ai.fixed-ae-least-newly-realized-meaning.v1"
  evaluator := "phase17ah.fixed-ae-least-missing-contract-ag-acceptance.v1"
  evaluatorCode := "2bb118c98da7b55102703021892c71283823a8282005684854bde7c6a193dd63"
  candidateCredits := 32
  sessionAttempts := 32
  poolAttempts := 32
  sources := [permit4_0, permit4_1] }
theorem policy_valid4 : PolicyValid policy4 := by decide +kernel
def contexts4 (source : Permit) : Phase17Provenance.Context :=
  if source.name = "af_before" then Phase17ProducerDomainExamples.context0 else Phase17ProducerDomainExamples.context1
def evaluators4 (source : Permit) : List Nat → Nat → Bool :=
  if source.name = "af_before" then Phase17ProducerDomainExamples.evaluator0 else Phase17ProducerDomainExamples.evaluator1
def state4_0 : AuthorityState := Phase17ControllerAuthority.initial
theorem reachable4_0 : Reachable policy4 contexts4 evaluators4 state4_0 := .initial
def lease4_0 : Lease := issuedLease policy4 permit4_0 0
def capturedGrant4_0 : Grant := {
  binding := {
    source := "129a6f016eebf0d84bfde3274f05f959f593a3fe8e1fbebeae7ab7e15e1e6676"
    request := "b7f4bb2d756f6d1ed022d4ddaa993c0e3b7d41357cfd71444eb1b95ce1cdf790"
    package := "b4036b3e31a6608e30b421c08906b1e58c3e7d61fef6eb6730881c597656434e"
    history := "f0fdfc3264fded4f92ea01a33e37f232fbfafd9ec72ebad58c6517eb86c9eb1f"
    context := "5a7d2d5c7015e588902b33385ca9e7e4c679346c74faa51cc8415944bf4fecc2"
    catalog := "511a8e2783bfa6b4d2dcfda2a700967e5a9e101ba7f57d8ff6b61b164034cf5d"
    evaluator := "phase17ah.fixed-ae-least-missing-contract-ag-acceptance.v1"
  }
  candidateLimit := 32
  referenceCandidateLimit := 32
  vectorLimit := 64
  inputLimit := 256
  outputLimit := 256
  costLimit := 3584 }
theorem grant_bound4_0 : lease4_0.grant = capturedGrant4_0 := by decide +kernel
def state4_1 : AuthorityState := { state4_0 with
  nextSerial := state4_0.nextSerial + 1
  reservedAttempts := state4_0.reservedAttempts + policy4.sessionAttempts
  pending := some lease4_0
  liveLease := some lease4_0 }
theorem issue4_0 : issue policy4 policy4 "a513020e8bd10e7ee99da77e9d5d301105d30a12675fd3227ba49b8b16fa9579" "a513020e8bd10e7ee99da77e9d5d301105d30a12675fd3227ba49b8b16fa9579"
    state4_0 permit4_0 = some state4_1 := by decide +kernel
theorem reachable4_1 : Reachable policy4 contexts4 evaluators4 state4_1 :=
  .issue reachable4_0 policy4 "a513020e8bd10e7ee99da77e9d5d301105d30a12675fd3227ba49b8b16fa9579" "a513020e8bd10e7ee99da77e9d5d301105d30a12675fd3227ba49b8b16fa9579" permit4_0 issue4_0
theorem case_interrupted_reservation : Reachable policy4 contexts4 evaluators4 state4_1 ∧
    reservedVector state4_1 = [32, 64, 256, 256] ∧ reservedCost state4_1 = 3584 ∧
    state4_1.nextSerial = 1 ∧ state4_1.consumed = [] :=
  ⟨reachable4_1, by decide +kernel, by decide +kernel, by decide +kernel, by decide +kernel⟩

theorem main_issued_grants : lease0_0.grant = Phase17ProducerDomainExamples.grant0 ∧ lease0_1.grant = Phase17ProducerDomainExamples.grant1 := by decide +kernel

theorem main_exact_reservation : reservedVector state0_5 = [64, 128, 512, 512] ∧
    reservedCost state0_5 = 7168 := by decide +kernel

theorem main_actual_reference_work :
    Phase17Resource.totalCost completion0_0.execution.spent +
      Phase17Resource.totalCost completion0_1.execution.spent = 1008 := by decide +kernel

theorem main_unused_envelope_retained :
    Phase17Resource.totalCost completion0_0.execution.spent +
      Phase17Resource.totalCost completion0_1.execution.spent < reservedCost state0_5 := by decide +kernel

theorem main_checkpoints_updated : state0_5.completed = [completion0_0, completion0_1] ∧
    completion0_0.execution.controller = Phase17ProducerDomainExamples.state0_1.controller ∧
    completion0_1.execution.controller = Phase17ProducerDomainExamples.state1_8.controller := by decide +kernel

theorem main_reopen_preserves_budget : reservedCost state0_reopened = 3584 ∧
    state0_reopened.consumed = ["af_before"] ∧ state0_reopened.pending = none := by decide +kernel

theorem main_sources_consumed_once : state0_5.consumed.Nodup :=
  reachable_no_duplicate_sources policy0 contexts0 evaluators0 state0_5 reachable0_5

theorem first_completed_acceptance :
    Phase17TruthfulSuccessor.Accepted Phase17ProducerDomainExamples.fixed Phase17ProducerDomainExamples.contexts0 (Phase17ProducerDomainExamples.chargesAt [] 30)
      Phase17ProducerDomainExamples.source0 (Phase17ProducerDomainExamples.builder0 [] 30 41) := Phase17ProducerDomainExamples.first_source_reference_accepted

theorem second_completed_acceptance :
    Phase17TruthfulSuccessor.Accepted Phase17ProducerDomainExamples.fixed Phase17ProducerDomainExamples.contexts1
      (Phase17ProducerDomainExamples.chargesAt [19, 5, 18, 27, 13, 30, 15] 0) Phase17ProducerDomainExamples.source1
      (Phase17ProducerDomainExamples.builder1 [19, 5, 18, 27, 13, 30, 15] 0 56) := Phase17ProducerDomainExamples.second_source_reference_accepted

theorem fixed_policy_meanings : permit0_0.binding.catalog = policy0.catalog ∧
    permit0_1.binding.catalog = policy0.catalog ∧ permit0_0.objective = policy0.objective ∧
    permit0_1.objective = policy0.objective ∧ permit0_0.evaluatorCode = policy0.evaluatorCode ∧
    permit0_1.evaluatorCode = policy0.evaluatorCode := by decide +kernel

theorem aggregate_denial_no_new_lease : state1_3.nextSerial = 1 ∧
    reservedCost state1_3 = 3584 ∧ state1_3.pending = none ∧ state1_3.halted = true := by decide +kernel

theorem reference_stop_is_not_exhaustion :
    Phase17Controller.decision Phase17ProducerDomainExamples.context4 completion2_0.execution.controller = some (.evaluate 27) ∧
    reservedCost state2_3 = 336 := ⟨Phase17ProducerDomainExamples.terminal4, by decide +kernel⟩

theorem credit_stop_is_not_exhaustion :
    Phase17Controller.decision Phase17ProducerDomainExamples.context2 completion3_0.execution.controller = some .resourceExhausted ∧
    completion3_0.execution.controller.observations.length = 4 := ⟨Phase17ProducerDomainExamples.terminal2, by decide +kernel⟩

theorem pending_reopen_cannot_complete :
    (reopen state4_1).pending = some lease4_0 ∧ reservedCost (reopen state4_1) = 3584 ∧
    (reopen state4_1).liveLease = none := by decide +kernel

theorem pending_stop_is_refused : stop state4_1 = none := by decide +kernel

end Phase17ControllerAuthorityExamples
