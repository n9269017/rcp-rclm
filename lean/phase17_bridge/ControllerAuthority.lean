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
