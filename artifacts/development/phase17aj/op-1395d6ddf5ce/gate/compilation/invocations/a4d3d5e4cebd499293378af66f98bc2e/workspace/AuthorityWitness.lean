import ControllerAuthority

/- Phase 17AJ: one separately provisioned witness owns the current authority
   state. A successful request atomically consumes its exact revision/head and
   computes the unchanged AI transition. The model assumes one authoritative
   witness history. It does not establish physical anti-rollback storage,
   cryptographic key provenance, global uniqueness of witness replicas, or
   complete host-resource accounting. Identity strings are retained bindings.
   The executable wrapper checks its authenticated protocol separately. -/
namespace Phase17AuthorityWitness

structure Provision where
  identity : String
  witness : String
  credential : String
  implementation : String
  genesis : String
  policy : Phase17ControllerAuthority.AuthorityPolicy
  deriving DecidableEq

def ProvisionValid (p : Provision) : Prop :=
  p.identity ≠ "" ∧ p.witness ≠ "" ∧ p.credential ≠ "" ∧
  p.implementation ≠ "" ∧ p.genesis ≠ "" ∧ Phase17ControllerAuthority.PolicyValid p.policy

instance provisionValidDecidable (p : Provision) : Decidable (ProvisionValid p) := by
  unfold ProvisionValid
  infer_instance

structure WitnessState where
  provision : String
  revision : Nat
  head : String
  journal : String
  authority : Phase17ControllerAuthority.AuthorityState
  owner : Option String
  nonces : List String
  deriving DecidableEq

def initial (p : Provision) (journal : String) : WitnessState :=
  ⟨p.identity, 0, p.genesis, journal, Phase17ControllerAuthority.initial, none, []⟩

inductive Command where
  | reserve (owner : String) (source : Phase17ControllerAuthority.Permit)
  | execute (owner : String) (result : Phase17ControllerAuthority.Completion)
  | deny (source : Phase17ControllerAuthority.Permit)
  | stop
  | reopen
  deriving DecidableEq

structure Request where
  provision : String
  revision : Nat
  head : String
  journal : String
  nonce : String
  command : Command
  deriving DecidableEq

/-- An authenticated read returns a cursor, never a live execution owner. -/
structure ReadResponse where
  provision : String
  nonce : String
  revision : Nat
  head : String
  journal : String
  deriving DecidableEq

def readResponse (state : WitnessState) (nonce : String) : ReadResponse :=
  ⟨state.provision, nonce, state.revision, state.head, state.journal⟩

/-- Authenticity is a premise discharged by the configured protocol verifier,
    not a caller-controlled field of the response. A response describes the
    witness at its read point; a later mutation still requires a current CAS. -/
def ReadAccepted (authentic : ReadResponse → Prop) (p : Provision) (nonce : String)
    (state : WitnessState) (response : ReadResponse) : Prop :=
  authentic response ∧ state.provision = p.identity ∧ nonce ≠ "" ∧
  response = readResponse state nonce

instance readAcceptedDecidable (authentic : ReadResponse → Prop) [DecidablePred authentic]
    (p : Provision) (nonce : String) (state : WitnessState) (response : ReadResponse) :
    Decidable (ReadAccepted authentic p nonce state response) := by
  unfold ReadAccepted
  infer_instance

theorem accepted_read_exact (authentic : ReadResponse → Prop) (p : Provision)
    (nonce : String) (state : WitnessState) (response : ReadResponse)
    (accepted : ReadAccepted authentic p nonce state response) :
    response.provision = p.identity ∧ response.nonce = nonce ∧
    response.revision = state.revision ∧ response.head = state.head ∧
    response.journal = state.journal := by
  rcases accepted with ⟨_, bound, _, same⟩
  rw [same]
  exact ⟨bound, rfl, rfl, rfl, rfl⟩

theorem unauthenticated_read_refused (authentic : ReadResponse → Prop) (p : Provision)
    (nonce : String) (state : WitnessState) (response : ReadResponse)
    (invalid : ¬ authentic response) : ¬ ReadAccepted authentic p nonce state response :=
  fun accepted => invalid accepted.1

theorem wrong_nonce_read_refused (authentic : ReadResponse → Prop) (p : Provision)
    (nonce : String) (state : WitnessState) (response : ReadResponse)
    (different : response.nonce ≠ nonce) : ¬ ReadAccepted authentic p nonce state response := by
  intro accepted
  exact different (accepted_read_exact authentic p nonce state response accepted).2.1

theorem wrong_head_read_refused (authentic : ReadResponse → Prop) (p : Provision)
    (nonce : String) (state : WitnessState) (response : ReadResponse)
    (different : response.head ≠ state.head) : ¬ ReadAccepted authentic p nonce state response := by
  intro accepted
  exact different (accepted_read_exact authentic p nonce state response accepted).2.2.2.1

theorem read_does_not_supply_owner (state : WitnessState) (nonce : String) :
    readResponse { state with owner := none } nonce = readResponse state nonce := rfl

def perform (p : Provision) (contexts : Phase17ControllerAuthority.Contexts) (evaluators : Phase17ControllerAuthority.Evaluators)
    (state : WitnessState) (command : Command) : Option Phase17ControllerAuthority.AuthorityState :=
  match command with
  | .reserve owner source =>
      if owner ≠ "" ∧ state.owner = none then
        Phase17ControllerAuthority.issue p.policy p.policy state.journal state.journal state.authority source
      else none
  | .execute owner result =>
      if owner ≠ "" ∧ state.owner = some owner then
        Phase17ControllerAuthority.complete p.policy contexts evaluators state.journal state.journal state.authority result
      else none
  | .deny source =>
      if state.owner = none then
        Phase17ControllerAuthority.deny p.policy p.policy state.journal state.journal state.authority source
      else none
  | .stop => Phase17ControllerAuthority.stop state.authority
  | .reopen => some (Phase17ControllerAuthority.reopen state.authority)

def nextOwner : Command → Option String
  | .reserve owner _ => some owner
  | _ => none

def JournalBound (command : Command) (state : WitnessState) (nextJournal : String) : Prop :=
  match command with
  | .reopen => nextJournal = state.journal
  | _ => nextJournal ≠ "" ∧ nextJournal ≠ state.journal

instance journalBoundDecidable (command : Command) (state : WitnessState) (nextJournal : String) :
    Decidable (JournalBound command state nextJournal) := by
  cases command <;> unfold JournalBound <;> infer_instance

def AdvanceGuard (p : Provision) (state : WitnessState) (request : Request)
    (nextHead nextJournal : String) : Prop :=
  request.provision = p.identity ∧ state.provision = p.identity ∧ ProvisionValid p ∧
  request.revision = state.revision ∧ request.head = state.head ∧
  request.nonce ≠ "" ∧ request.nonce ∉ state.nonces ∧
  nextHead ≠ "" ∧ nextHead ≠ state.head ∧ JournalBound request.command state nextJournal ∧
  request.journal = state.journal

instance advanceGuardDecidable (p : Provision) (state : WitnessState) (request : Request)
    (nextHead nextJournal : String) : Decidable (AdvanceGuard p state request nextHead nextJournal) := by
  unfold AdvanceGuard
  infer_instance

def updated (state : WitnessState) (request : Request) (nextHead nextJournal : String)
    (authority : Phase17ControllerAuthority.AuthorityState) : WitnessState :=
  { state with
    revision := state.revision + 1
    head := nextHead
    journal := nextJournal
    authority := authority
    owner := nextOwner request.command
    nonces := state.nonces ++ [request.nonce] }

def advance (p : Provision) (contexts : Phase17ControllerAuthority.Contexts) (evaluators : Phase17ControllerAuthority.Evaluators)
    (state : WitnessState) (request : Request) (nextHead nextJournal : String) : Option WitnessState :=
  if AdvanceGuard p state request nextHead nextJournal then
    (perform p contexts evaluators state request.command).map
      (updated state request nextHead nextJournal)
  else none

theorem advanced_spec (p : Provision) (contexts : Phase17ControllerAuthority.Contexts) (evaluators : Phase17ControllerAuthority.Evaluators)
    (state next : WitnessState) (request : Request) (nextHead nextJournal : String)
    (accepted : advance p contexts evaluators state request nextHead nextJournal = some next) :
    AdvanceGuard p state request nextHead nextJournal ∧
    ∃ authority, perform p contexts evaluators state request.command = some authority ∧
      next = updated state request nextHead nextJournal authority := by
  unfold advance at accepted
  split at accepted
  next valid =>
    refine ⟨valid, ?_⟩
    cases outcome : perform p contexts evaluators state request.command with
    | none => simp only [outcome, Option.map_none] at accepted; cases accepted
    | some authority =>
        simp only [outcome, Option.map_some] at accepted
        exact ⟨authority, rfl, (Option.some.inj accepted).symm⟩
  next invalid => cases accepted

theorem advanced_construct (p : Provision) (contexts : Phase17ControllerAuthority.Contexts) (evaluators : Phase17ControllerAuthority.Evaluators)
    (state : WitnessState) (request : Request) (nextHead nextJournal : String)
    (authority : Phase17ControllerAuthority.AuthorityState)
    (guard : AdvanceGuard p state request nextHead nextJournal)
    (transition : perform p contexts evaluators state request.command = some authority) :
    advance p contexts evaluators state request nextHead nextJournal =
      some (updated state request nextHead nextJournal authority) := by
  simp only [advance, guard, if_true, transition, Option.map_some]

/-- The protocol admits a decoded mutation only after its configured verifier
    authenticates the request. No cryptographic correctness is inferred from
    an identity string, a fixture key, or a caller-supplied Boolean. -/
def AuthorizedAdvance (authentic : Request → Prop) (p : Provision)
    (contexts : Phase17ControllerAuthority.Contexts) (evaluators : Phase17ControllerAuthority.Evaluators)
    (state next : WitnessState) (request : Request) (nextHead nextJournal : String) : Prop :=
  authentic request ∧ advance p contexts evaluators state request nextHead nextJournal = some next

theorem authorized_advance_exact (authentic : Request → Prop) (p : Provision)
    (contexts : Phase17ControllerAuthority.Contexts) (evaluators : Phase17ControllerAuthority.Evaluators)
    (state next : WitnessState) (request : Request) (nextHead nextJournal : String)
    (accepted : AuthorizedAdvance authentic p contexts evaluators state next request nextHead nextJournal) :
    authentic request ∧ advance p contexts evaluators state request nextHead nextJournal = some next :=
  accepted

theorem unauthenticated_mutation_refused (authentic : Request → Prop) (p : Provision)
    (contexts : Phase17ControllerAuthority.Contexts) (evaluators : Phase17ControllerAuthority.Evaluators)
    (state next : WitnessState) (request : Request) (nextHead nextJournal : String)
    (invalid : ¬ authentic request) :
    ¬ AuthorizedAdvance authentic p contexts evaluators state next request nextHead nextJournal :=
  fun accepted => invalid accepted.1

theorem authorized_advance_recomputes (authentic : Request → Prop) (p : Provision)
    (contexts : Phase17ControllerAuthority.Contexts) (evaluators : Phase17ControllerAuthority.Evaluators)
    (state next : WitnessState) (request : Request) (nextHead nextJournal : String)
    (accepted : AuthorizedAdvance authentic p contexts evaluators state next request nextHead nextJournal) :
    AdvanceGuard p state request nextHead nextJournal ∧
    ∃ authority, perform p contexts evaluators state request.command = some authority ∧
      next = updated state request nextHead nextJournal authority :=
  advanced_spec p contexts evaluators state next request nextHead nextJournal accepted.2

theorem advanced_revision (p : Provision) (contexts : Phase17ControllerAuthority.Contexts) (evaluators : Phase17ControllerAuthority.Evaluators)
    (state next : WitnessState) (request : Request) (nextHead nextJournal : String)
    (accepted : advance p contexts evaluators state request nextHead nextJournal = some next) :
    next.revision = state.revision + 1 := by
  rcases (advanced_spec p contexts evaluators state next request nextHead nextJournal accepted).2 with
    ⟨authority, _, same⟩
  rw [same]
  rfl

theorem advanced_fixed_provision (p : Provision) (contexts : Phase17ControllerAuthority.Contexts) (evaluators : Phase17ControllerAuthority.Evaluators)
    (state next : WitnessState) (request : Request) (nextHead nextJournal : String)
    (accepted : advance p contexts evaluators state request nextHead nextJournal = some next) :
    next.provision = p.identity := by
  have spec := advanced_spec p contexts evaluators state next request nextHead nextJournal accepted
  rcases spec.2 with ⟨authority, _, same⟩
  rw [same]
  exact spec.1.2.1

theorem advanced_heads (p : Provision) (contexts : Phase17ControllerAuthority.Contexts) (evaluators : Phase17ControllerAuthority.Evaluators)
    (state next : WitnessState) (request : Request) (nextHead nextJournal : String)
    (accepted : advance p contexts evaluators state request nextHead nextJournal = some next) :
    next.head = nextHead ∧ next.journal = nextJournal ∧ next.head ≠ state.head := by
  have spec := advanced_spec p contexts evaluators state next request nextHead nextJournal accepted
  rcases spec.2 with ⟨authority, _, same⟩
  rw [same]
  exact ⟨rfl, rfl, spec.1.2.2.2.2.2.2.2.2.1⟩

theorem advanced_nonce_consumed (p : Provision) (contexts : Phase17ControllerAuthority.Contexts) (evaluators : Phase17ControllerAuthority.Evaluators)
    (state next : WitnessState) (request : Request) (nextHead nextJournal : String)
    (accepted : advance p contexts evaluators state request nextHead nextJournal = some next) :
    next.nonces = state.nonces ++ [request.nonce] ∧ request.nonce ∈ next.nonces := by
  rcases (advanced_spec p contexts evaluators state next request nextHead nextJournal accepted).2 with
    ⟨authority, _, same⟩
  rw [same]
  exact ⟨rfl, by simp [updated]⟩

theorem wrong_provision_refused (p : Provision) (contexts : Phase17ControllerAuthority.Contexts) (evaluators : Phase17ControllerAuthority.Evaluators)
    (state : WitnessState) (request : Request) (nextHead nextJournal : String)
    (wrong : request.provision ≠ p.identity) :
    advance p contexts evaluators state request nextHead nextJournal = none := by
  have invalid : ¬ AdvanceGuard p state request nextHead nextJournal := fun valid => wrong valid.1
  simp only [advance, invalid, if_false]

theorem stale_revision_refused (p : Provision) (contexts : Phase17ControllerAuthority.Contexts) (evaluators : Phase17ControllerAuthority.Evaluators)
    (state : WitnessState) (request : Request) (nextHead nextJournal : String)
    (stale : request.revision ≠ state.revision) :
    advance p contexts evaluators state request nextHead nextJournal = none := by
  have invalid : ¬ AdvanceGuard p state request nextHead nextJournal :=
    fun valid => stale valid.2.2.2.1
  simp only [advance, invalid, if_false]

theorem stale_head_refused (p : Provision) (contexts : Phase17ControllerAuthority.Contexts) (evaluators : Phase17ControllerAuthority.Evaluators)
    (state : WitnessState) (request : Request) (nextHead nextJournal : String)
    (stale : request.head ≠ state.head) :
    advance p contexts evaluators state request nextHead nextJournal = none := by
  have invalid : ¬ AdvanceGuard p state request nextHead nextJournal :=
    fun valid => stale valid.2.2.2.2.1
  simp only [advance, invalid, if_false]

theorem reused_nonce_refused (p : Provision) (contexts : Phase17ControllerAuthority.Contexts) (evaluators : Phase17ControllerAuthority.Evaluators)
    (state : WitnessState) (request : Request) (nextHead nextJournal : String)
    (reused : request.nonce ∈ state.nonces) :
    advance p contexts evaluators state request nextHead nextJournal = none := by
  have invalid : ¬ AdvanceGuard p state request nextHead nextJournal :=
    fun valid => valid.2.2.2.2.2.2.1 reused
  simp only [advance, invalid, if_false]

theorem stale_authority_head_refused (p : Provision) (contexts : Phase17ControllerAuthority.Contexts)
    (evaluators : Phase17ControllerAuthority.Evaluators) (state : WitnessState)
    (request : Request) (nextHead nextJournal : String) (stale : request.journal ≠ state.journal) :
    advance p contexts evaluators state request nextHead nextJournal = none := by
  have invalid : ¬ AdvanceGuard p state request nextHead nextJournal :=
    fun valid => stale valid.2.2.2.2.2.2.2.2.2.2
  simp only [advance, invalid, if_false]

theorem unchanged_head_refused (p : Provision) (contexts : Phase17ControllerAuthority.Contexts) (evaluators : Phase17ControllerAuthority.Evaluators)
    (state : WitnessState) (request : Request) (nextJournal : String) :
    advance p contexts evaluators state request state.head nextJournal = none := by
  have invalid : ¬ AdvanceGuard p state request state.head nextJournal :=
    fun valid => valid.2.2.2.2.2.2.2.2.1 rfl
  simp only [advance, invalid, if_false]

theorem predecessor_consumed_once (p : Provision) (contexts : Phase17ControllerAuthority.Contexts) (evaluators : Phase17ControllerAuthority.Evaluators)
    (state next : WitnessState) (first competing : Request)
    (firstHead firstJournal competingHead competingJournal : String)
    (accepted : advance p contexts evaluators state first firstHead firstJournal = some next)
    (sameRevision : competing.revision = state.revision) :
    advance p contexts evaluators next competing competingHead competingJournal = none := by
  apply stale_revision_refused
  rw [sameRevision, advanced_revision p contexts evaluators state next first firstHead firstJournal accepted]
  omega

theorem successful_request_cannot_replay (p : Provision) (contexts : Phase17ControllerAuthority.Contexts) (evaluators : Phase17ControllerAuthority.Evaluators)
    (state next : WitnessState) (request : Request) (nextHead nextJournal otherHead otherJournal : String)
    (accepted : advance p contexts evaluators state request nextHead nextJournal = some next) :
    advance p contexts evaluators next request otherHead otherJournal = none :=
  reused_nonce_refused p contexts evaluators next request otherHead otherJournal
    (advanced_nonce_consumed p contexts evaluators state next request nextHead nextJournal accepted).2

theorem reserve_recomputes_issued_lease (p : Provision) (contexts : Phase17ControllerAuthority.Contexts) (evaluators : Phase17ControllerAuthority.Evaluators)
    (state : WitnessState) (next : Phase17ControllerAuthority.AuthorityState) (owner : String) (source : Phase17ControllerAuthority.Permit)
    (accepted : perform p contexts evaluators state (.reserve owner source) = some next) :
    owner ≠ "" ∧ state.owner = none ∧
    Phase17ControllerAuthority.issue p.policy p.policy state.journal state.journal state.authority source = some next := by
  change (if owner ≠ "" ∧ state.owner = none then
    Phase17ControllerAuthority.issue p.policy p.policy state.journal state.journal state.authority source
    else none) = some next at accepted
  split at accepted
  next valid => exact ⟨valid.1, valid.2, accepted⟩
  next invalid => cases accepted

theorem reserve_construct (p : Provision) (contexts : Phase17ControllerAuthority.Contexts)
    (evaluators : Phase17ControllerAuthority.Evaluators) (state : WitnessState)
    (next : Phase17ControllerAuthority.AuthorityState) (owner : String)
    (source : Phase17ControllerAuthority.Permit) (nonempty : owner ≠ "")
    (vacant : state.owner = none)
    (issued : Phase17ControllerAuthority.issue p.policy p.policy state.journal state.journal
      state.authority source = some next) :
    perform p contexts evaluators state (.reserve owner source) = some next := by
  change (if owner ≠ "" ∧ state.owner = none then
    Phase17ControllerAuthority.issue p.policy p.policy state.journal state.journal state.authority source
    else none) = some next
  rw [if_pos ⟨nonempty, vacant⟩]
  exact issued

theorem execute_requires_owner (p : Provision) (contexts : Phase17ControllerAuthority.Contexts) (evaluators : Phase17ControllerAuthority.Evaluators)
    (state : WitnessState) (next : Phase17ControllerAuthority.AuthorityState) (owner : String) (result : Phase17ControllerAuthority.Completion)
    (accepted : perform p contexts evaluators state (.execute owner result) = some next) :
    owner ≠ "" ∧ state.owner = some owner ∧
    Phase17ControllerAuthority.complete p.policy contexts evaluators state.journal state.journal state.authority result = some next := by
  change (if owner ≠ "" ∧ state.owner = some owner then
    Phase17ControllerAuthority.complete p.policy contexts evaluators state.journal state.journal state.authority result
    else none) = some next at accepted
  split at accepted
  next valid => exact ⟨valid.1, valid.2, accepted⟩
  next invalid => cases accepted

theorem execute_construct (p : Provision) (contexts : Phase17ControllerAuthority.Contexts)
    (evaluators : Phase17ControllerAuthority.Evaluators) (state : WitnessState)
    (next : Phase17ControllerAuthority.AuthorityState) (owner : String)
    (result : Phase17ControllerAuthority.Completion) (nonempty : owner ≠ "")
    (owned : state.owner = some owner)
    (completed : Phase17ControllerAuthority.complete p.policy contexts evaluators state.journal
      state.journal state.authority result = some next) :
    perform p contexts evaluators state (.execute owner result) = some next := by
  change (if owner ≠ "" ∧ state.owner = some owner then
    Phase17ControllerAuthority.complete p.policy contexts evaluators state.journal state.journal state.authority result
    else none) = some next
  rw [if_pos ⟨nonempty, owned⟩]
  exact completed

theorem missing_owner_execution_refused (p : Provision) (contexts : Phase17ControllerAuthority.Contexts) (evaluators : Phase17ControllerAuthority.Evaluators)
    (state : WitnessState) (owner : String) (result : Phase17ControllerAuthority.Completion) (missing : state.owner = none) :
    perform p contexts evaluators state (.execute owner result) = none := by
  simp only [perform, missing, reduceCtorEq, and_false, if_false]

theorem wrong_owner_execution_refused (p : Provision) (contexts : Phase17ControllerAuthority.Contexts) (evaluators : Phase17ControllerAuthority.Evaluators)
    (state : WitnessState) (owner : String) (result : Phase17ControllerAuthority.Completion) (wrong : state.owner ≠ some owner) :
    perform p contexts evaluators state (.execute owner result) = none := by
  simp only [perform, wrong, and_false, if_false]

theorem reserve_semantics_fixed (p : Provision) (contexts : Phase17ControllerAuthority.Contexts) (evaluators : Phase17ControllerAuthority.Evaluators)
    (state : WitnessState) (next : Phase17ControllerAuthority.AuthorityState) (owner : String) (source : Phase17ControllerAuthority.Permit)
    (accepted : perform p contexts evaluators state (.reserve owner source) = some next) :
    source.binding.catalog = p.policy.catalog ∧ source.binding.evaluator = p.policy.evaluator ∧
    source.objective = p.policy.objective ∧ source.evaluatorCode = p.policy.evaluatorCode :=
  Phase17ControllerAuthority.issued_semantics_fixed p.policy p.policy state.journal state.journal state.authority next source
    (reserve_recomputes_issued_lease p contexts evaluators state next owner source accepted).2.2

theorem reserve_exact_charge (p : Provision) (contexts : Phase17ControllerAuthority.Contexts) (evaluators : Phase17ControllerAuthority.Evaluators)
    (state : WitnessState) (next : Phase17ControllerAuthority.AuthorityState) (owner : String) (source : Phase17ControllerAuthority.Permit)
    (accepted : perform p contexts evaluators state (.reserve owner source) = some next) :
    Phase17ControllerAuthority.reservedCost next = Phase17ControllerAuthority.reservedCost state.authority + 112 * p.policy.sessionAttempts :=
  Phase17ControllerAuthority.issued_cost_not_refunded p.policy p.policy state.journal state.journal state.authority next source
    (reserve_recomputes_issued_lease p contexts evaluators state next owner source accepted).2.2

theorem execution_recomputes_truthful_controller (p : Provision) (contexts : Phase17ControllerAuthority.Contexts)
    (evaluators : Phase17ControllerAuthority.Evaluators) (state : WitnessState) (next : Phase17ControllerAuthority.AuthorityState)
    (owner : String) (result : Phase17ControllerAuthority.Completion)
    (accepted : perform p contexts evaluators state (.execute owner result) = some next) :
    Phase17ControllerAuthority.CompletionValid p.policy contexts evaluators state.authority result :=
  (Phase17ControllerAuthority.completed_spec p.policy contexts evaluators state.journal state.journal state.authority next result
    (execute_requires_owner p contexts evaluators state next owner result accepted).2.2).2.1

theorem execution_never_refunds (p : Provision) (contexts : Phase17ControllerAuthority.Contexts)
    (evaluators : Phase17ControllerAuthority.Evaluators) (state : WitnessState) (next : Phase17ControllerAuthority.AuthorityState)
    (owner : String) (result : Phase17ControllerAuthority.Completion)
    (accepted : perform p contexts evaluators state (.execute owner result) = some next) :
    Phase17ControllerAuthority.reservedCost next = Phase17ControllerAuthority.reservedCost state.authority :=
  Phase17ControllerAuthority.completed_cost_not_refunded p.policy contexts evaluators state.journal state.journal
    state.authority next result
    (execute_requires_owner p contexts evaluators state next owner result accepted).2.2

theorem reopen_exact (p : Provision) (contexts : Phase17ControllerAuthority.Contexts) (evaluators : Phase17ControllerAuthority.Evaluators)
    (state : WitnessState) :
    perform p contexts evaluators state .reopen = some (Phase17ControllerAuthority.reopen state.authority) ∧
    nextOwner .reopen = none := ⟨rfl, rfl⟩

theorem reopened_owner_cannot_execute (p : Provision) (contexts : Phase17ControllerAuthority.Contexts) (evaluators : Phase17ControllerAuthority.Evaluators)
    (state next : WitnessState) (request : Request) (nextHead nextJournal owner : String)
    (result : Phase17ControllerAuthority.Completion) (kind : request.command = .reopen)
    (accepted : advance p contexts evaluators state request nextHead nextJournal = some next) :
    perform p contexts evaluators next (.execute owner result) = none := by
  rcases (advanced_spec p contexts evaluators state next request nextHead nextJournal accepted).2 with
    ⟨authority, _, same⟩
  apply missing_owner_execution_refused
  rw [same]
  simp only [updated, kind, nextOwner]

theorem reopened_pending_retained (p : Provision) (contexts : Phase17ControllerAuthority.Contexts) (evaluators : Phase17ControllerAuthority.Evaluators)
    (state next : WitnessState) (request : Request) (nextHead nextJournal : String)
    (kind : request.command = .reopen)
    (accepted : advance p contexts evaluators state request nextHead nextJournal = some next) :
    next.authority.pending = state.authority.pending ∧
    Phase17ControllerAuthority.reservedCost next.authority = Phase17ControllerAuthority.reservedCost state.authority ∧
    next.authority.liveLease = none ∧ next.journal = state.journal := by
  have spec := advanced_spec p contexts evaluators state next request nextHead nextJournal accepted
  rcases spec.2 with ⟨authority, transition, same⟩
  rw [kind] at transition
  have equal : authority = Phase17ControllerAuthority.reopen state.authority := (Option.some.inj transition).symm
  rw [same, equal]
  have journal := spec.1.2.2.2.2.2.2.2.2.2.1
  rw [kind] at journal
  exact ⟨rfl, rfl, rfl, journal⟩

theorem perform_preserves_authority_reachability (p : Provision) (contexts : Phase17ControllerAuthority.Contexts)
    (evaluators : Phase17ControllerAuthority.Evaluators) (state : WitnessState) (next : Phase17ControllerAuthority.AuthorityState)
    (command : Command) (reachable : Phase17ControllerAuthority.Reachable p.policy contexts evaluators state.authority)
    (accepted : perform p contexts evaluators state command = some next) :
    Phase17ControllerAuthority.Reachable p.policy contexts evaluators next := by
  cases command with
  | reserve owner source =>
      exact .issue reachable p.policy state.journal state.journal source
        (reserve_recomputes_issued_lease p contexts evaluators state next owner source accepted).2.2
  | execute owner result =>
      exact .complete reachable state.journal state.journal result
        (execute_requires_owner p contexts evaluators state next owner result accepted).2.2
  | deny source =>
      change (if state.owner = none then
        Phase17ControllerAuthority.deny p.policy p.policy state.journal state.journal state.authority source
        else none) = some next at accepted
      split at accepted
      next valid =>
        rw [(Phase17ControllerAuthority.denied_spec p.policy p.policy state.journal state.journal state.authority next source accepted).2]
        exact .interrupt reachable
      next invalid => cases accepted
  | stop =>
      change Phase17ControllerAuthority.stop state.authority = some next at accepted
      unfold Phase17ControllerAuthority.stop at accepted
      split at accepted
      next valid =>
        rw [← Option.some.inj accepted]
        exact .interrupt reachable
      next invalid => cases accepted
  | reopen =>
      have equal : next = Phase17ControllerAuthority.reopen state.authority := (Option.some.inj accepted).symm
      rw [equal]
      exact .reopen reachable

inductive Reachable (p : Provision) (contexts : Phase17ControllerAuthority.Contexts) (evaluators : Phase17ControllerAuthority.Evaluators)
    (initialJournal : String) : WitnessState → Prop where
  | initial : Reachable p contexts evaluators initialJournal (initial p initialJournal)
  | advance {state next : WitnessState}
      (prior : Reachable p contexts evaluators initialJournal state)
      (request : Request) (nextHead nextJournal : String)
      (accepted : advance p contexts evaluators state request nextHead nextJournal = some next) :
      Reachable p contexts evaluators initialJournal next

theorem reachable_authority (p : Provision) (contexts : Phase17ControllerAuthority.Contexts) (evaluators : Phase17ControllerAuthority.Evaluators)
    (initialJournal : String) (state : WitnessState)
    (reachable : Reachable p contexts evaluators initialJournal state) :
    Phase17ControllerAuthority.Reachable p.policy contexts evaluators state.authority := by
  induction reachable with
  | initial => exact .initial
  | @advance prior next priorReach request nextHead nextJournal accepted ih =>
      rcases (advanced_spec p contexts evaluators prior next request nextHead nextJournal accepted).2 with
        ⟨authority, transition, same⟩
      rw [same]
      exact perform_preserves_authority_reachability p contexts evaluators prior authority
        request.command ih transition

theorem reachable_nonces_unique (p : Provision) (contexts : Phase17ControllerAuthority.Contexts) (evaluators : Phase17ControllerAuthority.Evaluators)
    (initialJournal : String) (state : WitnessState)
    (reachable : Reachable p contexts evaluators initialJournal state) : state.nonces.Nodup := by
  induction reachable with
  | initial => exact List.nodup_nil
  | @advance prior next priorReach request nextHead nextJournal accepted ih =>
      have spec := advanced_spec p contexts evaluators prior next request nextHead nextJournal accepted
      have fresh := spec.1.2.2.2.2.2.2.1
      rw [(advanced_nonce_consumed p contexts evaluators prior next request nextHead nextJournal accepted).1]
      refine List.nodup_append.mpr ⟨ih, by simp, ?_⟩
      intro a member b singleton equal
      have ident : b = request.nonce := List.mem_singleton.mp singleton
      exact fresh (ident ▸ equal ▸ member)

theorem reachable_revision_exact (p : Provision) (contexts : Phase17ControllerAuthority.Contexts) (evaluators : Phase17ControllerAuthority.Evaluators)
    (initialJournal : String) (state : WitnessState)
    (reachable : Reachable p contexts evaluators initialJournal state) : state.revision = state.nonces.length := by
  induction reachable with
  | initial => rfl
  | @advance prior next priorReach request nextHead nextJournal accepted ih =>
      rw [advanced_revision p contexts evaluators prior next request nextHead nextJournal accepted,
        (advanced_nonce_consumed p contexts evaluators prior next request nextHead nextJournal accepted).1]
      simp only [List.length_append, List.length_cons, List.length_nil, Nat.zero_add]
      exact congrArg (fun n => n + 1) ih

theorem reachable_sources_consumed_once (p : Provision) (contexts : Phase17ControllerAuthority.Contexts) (evaluators : Phase17ControllerAuthority.Evaluators)
    (initialJournal : String) (state : WitnessState)
    (reachable : Reachable p contexts evaluators initialJournal state) : state.authority.consumed.Nodup :=
  Phase17ControllerAuthority.reachable_no_duplicate_sources p.policy contexts evaluators state.authority
    (reachable_authority p contexts evaluators initialJournal state reachable)

theorem reachable_exact_debit (p : Provision) (contexts : Phase17ControllerAuthority.Contexts) (evaluators : Phase17ControllerAuthority.Evaluators)
    (initialJournal : String) (state : WitnessState)
    (reachable : Reachable p contexts evaluators initialJournal state) :
    state.authority.reservedAttempts = state.authority.nextSerial * p.policy.sessionAttempts :=
  Phase17ControllerAuthority.reachable_debit_exact p.policy contexts evaluators state.authority
    (reachable_authority p contexts evaluators initialJournal state reachable)

theorem reachable_within_pool (p : Provision) (contexts : Phase17ControllerAuthority.Contexts) (evaluators : Phase17ControllerAuthority.Evaluators)
    (initialJournal : String) (state : WitnessState)
    (reachable : Reachable p contexts evaluators initialJournal state) :
    state.authority.reservedAttempts ≤ p.policy.poolAttempts :=
  Phase17ControllerAuthority.reachable_within_pool p.policy contexts evaluators state.authority
    (reachable_authority p contexts evaluators initialJournal state reachable)

theorem reachable_completed_and_pending_accounted (p : Provision) (contexts : Phase17ControllerAuthority.Contexts)
    (evaluators : Phase17ControllerAuthority.Evaluators) (initialJournal : String) (state : WitnessState)
    (reachable : Reachable p contexts evaluators initialJournal state) :
    Phase17ControllerAuthority.completedCost state.authority + Phase17ControllerAuthority.pendingCost p.policy state.authority ≤
      Phase17ControllerAuthority.reservedCost state.authority :=
  Phase17ControllerAuthority.reachable_actual_cost_reserved p.policy contexts evaluators state.authority
    (reachable_authority p contexts evaluators initialJournal state reachable)

theorem reachable_completed_work_within_pool (p : Provision) (contexts : Phase17ControllerAuthority.Contexts)
    (evaluators : Phase17ControllerAuthority.Evaluators) (initialJournal : String) (state : WitnessState)
    (reachable : Reachable p contexts evaluators initialJournal state) :
    Phase17ControllerAuthority.completedCost state.authority ≤ 112 * p.policy.poolAttempts :=
  Phase17ControllerAuthority.reachable_actual_cost_within_pool p.policy contexts evaluators state.authority
    (reachable_authority p contexts evaluators initialJournal state reachable)

end Phase17AuthorityWitness

namespace Phase17AuthorityWitnessExamples
open Phase17AuthorityWitness
set_option maxRecDepth 32768
set_option maxHeartbeats 16000000
-- Exact AJ witness packet SHA256: dd7a8197c66cc88beaa31c4c18dac5c88ced3c6cb754421a80bc94abeb552a2a
def provision0 : Provision := {
  identity := "fb96b3ace49fd6acbd7714227f4dd74459ced948330259ebbb093154b49baf25"
  witness := "phase17aj.reference.shared_two_sources"
  credential := "54a6c031d7ff83bb892708046c9d763bee29ad4290995f8db7efc05a9632deff"
  implementation := "13c252851490d937ae1c2f0e17c5d9c086893d7807f4b81add36045625caae99"
  genesis := "99061d1f972ad9b2f585f383f7cb8d36d0dbb081ed4563ffeaa6b161a5de606c"
  policy := Phase17ControllerAuthorityExamples.policy0 }
theorem provision_valid0 : ProvisionValid provision0 :=
  ⟨by decide +kernel, by decide +kernel, by decide +kernel, by decide +kernel,
    by decide +kernel, Phase17ControllerAuthorityExamples.policy_valid0⟩
def journal0 : String := "f3b0cc8fca6969ad76b09daae9b5d38e8d310136fb5c999eda2c01af23d87e47"
def witness0_0 : WitnessState := initial provision0 journal0
theorem reachable0_0 : Reachable provision0 Phase17ControllerAuthorityExamples.contexts0 Phase17ControllerAuthorityExamples.evaluators0
    journal0 witness0_0 := .initial
-- Retained AI state projection SHA256: 783d00bae6356c546646e8c5550667c005a0cb5bb9653bb7939fe2bb2b768b2b
def request0_1 : Request := {
  provision := provision0.identity
  revision := 0
  head := "99061d1f972ad9b2f585f383f7cb8d36d0dbb081ed4563ffeaa6b161a5de606c"
  journal := "f3b0cc8fca6969ad76b09daae9b5d38e8d310136fb5c999eda2c01af23d87e47"
  nonce := "4e181c7b912b3beaa3075c0c3cab45f09f1853c4fed35aa282d1e00eaa4d7df5"
  command := .reopen }
def witness0_1 : WitnessState := updated witness0_0 request0_1 "1fd3e5ae29519426c39c7ef77bdf8dea8c0c1a7d41d25a306ffd4de6fbac7121" "f3b0cc8fca6969ad76b09daae9b5d38e8d310136fb5c999eda2c01af23d87e47" (Phase17ControllerAuthority.reopen Phase17ControllerAuthorityExamples.state0_0)
theorem guard0_1 : AdvanceGuard provision0 witness0_0 request0_1
    "1fd3e5ae29519426c39c7ef77bdf8dea8c0c1a7d41d25a306ffd4de6fbac7121" "f3b0cc8fca6969ad76b09daae9b5d38e8d310136fb5c999eda2c01af23d87e47" :=
  ⟨rfl, rfl, provision_valid0, rfl, rfl, by decide +kernel, by decide +kernel,
    by decide +kernel, by decide +kernel, by decide +kernel, rfl⟩
theorem performed0_1 : perform provision0 Phase17ControllerAuthorityExamples.contexts0 Phase17ControllerAuthorityExamples.evaluators0
    witness0_0 request0_1.command = some (Phase17ControllerAuthority.reopen Phase17ControllerAuthorityExamples.state0_0) := by rfl
theorem step0_1 : advance provision0 Phase17ControllerAuthorityExamples.contexts0 Phase17ControllerAuthorityExamples.evaluators0
    witness0_0 request0_1 "1fd3e5ae29519426c39c7ef77bdf8dea8c0c1a7d41d25a306ffd4de6fbac7121" "f3b0cc8fca6969ad76b09daae9b5d38e8d310136fb5c999eda2c01af23d87e47" = some witness0_1 :=
  advanced_construct provision0 Phase17ControllerAuthorityExamples.contexts0 Phase17ControllerAuthorityExamples.evaluators0 witness0_0 request0_1
    "1fd3e5ae29519426c39c7ef77bdf8dea8c0c1a7d41d25a306ffd4de6fbac7121" "f3b0cc8fca6969ad76b09daae9b5d38e8d310136fb5c999eda2c01af23d87e47" (Phase17ControllerAuthority.reopen Phase17ControllerAuthorityExamples.state0_0) guard0_1 performed0_1
theorem reachable0_1 : Reachable provision0 Phase17ControllerAuthorityExamples.contexts0 Phase17ControllerAuthorityExamples.evaluators0
    journal0 witness0_1 :=
  .advance reachable0_0 request0_1 "1fd3e5ae29519426c39c7ef77bdf8dea8c0c1a7d41d25a306ffd4de6fbac7121" "f3b0cc8fca6969ad76b09daae9b5d38e8d310136fb5c999eda2c01af23d87e47" step0_1
-- Retained AI state projection SHA256: 3337c8c401e21ea00271bba0896fcd149b7a2a892cb5d238a3abb3a50d239a46
def request0_2 : Request := {
  provision := provision0.identity
  revision := 1
  head := "1fd3e5ae29519426c39c7ef77bdf8dea8c0c1a7d41d25a306ffd4de6fbac7121"
  journal := "f3b0cc8fca6969ad76b09daae9b5d38e8d310136fb5c999eda2c01af23d87e47"
  nonce := "670fa9ebaf20f10e892511b66158d2f0e1bd628331ae2f2f2cfc8ecfaf5a7279"
  command := .reserve "7fecda5b7b570e54d0998a9a01acfafdfdc88ba5b59de43ce666295cc086cd91" Phase17ControllerAuthorityExamples.permit0_0 }
def witness0_2 : WitnessState := updated witness0_1 request0_2 "acbad0038d7529df0b8ff3ba7a23bd3f5c8981c7c8f68ab9c31adc1982105720" "9e52ac55aba74d638bb9741d48a7253a73a6b090ce4a7002c69a9581893d4531" Phase17ControllerAuthorityExamples.state0_1
theorem guard0_2 : AdvanceGuard provision0 witness0_1 request0_2
    "acbad0038d7529df0b8ff3ba7a23bd3f5c8981c7c8f68ab9c31adc1982105720" "9e52ac55aba74d638bb9741d48a7253a73a6b090ce4a7002c69a9581893d4531" :=
  ⟨rfl, rfl, provision_valid0, rfl, rfl, by decide +kernel, by decide +kernel,
    by decide +kernel, by decide +kernel, by decide +kernel, rfl⟩
theorem performed0_2 : perform provision0 Phase17ControllerAuthorityExamples.contexts0 Phase17ControllerAuthorityExamples.evaluators0
    witness0_1 request0_2.command = some Phase17ControllerAuthorityExamples.state0_1 := by
  apply reserve_construct
  · decide +kernel
  · rfl
  · exact Phase17ControllerAuthorityExamples.issue0_0
theorem step0_2 : advance provision0 Phase17ControllerAuthorityExamples.contexts0 Phase17ControllerAuthorityExamples.evaluators0
    witness0_1 request0_2 "acbad0038d7529df0b8ff3ba7a23bd3f5c8981c7c8f68ab9c31adc1982105720" "9e52ac55aba74d638bb9741d48a7253a73a6b090ce4a7002c69a9581893d4531" = some witness0_2 :=
  advanced_construct provision0 Phase17ControllerAuthorityExamples.contexts0 Phase17ControllerAuthorityExamples.evaluators0 witness0_1 request0_2
    "acbad0038d7529df0b8ff3ba7a23bd3f5c8981c7c8f68ab9c31adc1982105720" "9e52ac55aba74d638bb9741d48a7253a73a6b090ce4a7002c69a9581893d4531" Phase17ControllerAuthorityExamples.state0_1 guard0_2 performed0_2
theorem reachable0_2 : Reachable provision0 Phase17ControllerAuthorityExamples.contexts0 Phase17ControllerAuthorityExamples.evaluators0
    journal0 witness0_2 :=
  .advance reachable0_1 request0_2 "acbad0038d7529df0b8ff3ba7a23bd3f5c8981c7c8f68ab9c31adc1982105720" "9e52ac55aba74d638bb9741d48a7253a73a6b090ce4a7002c69a9581893d4531" step0_2
-- Retained AI state projection SHA256: 6b3be86dc10d22d3c6f58034c5d11f0b37f39bd95f559305bda48dea5c78adc6
def request0_3 : Request := {
  provision := provision0.identity
  revision := 2
  head := "acbad0038d7529df0b8ff3ba7a23bd3f5c8981c7c8f68ab9c31adc1982105720"
  journal := "9e52ac55aba74d638bb9741d48a7253a73a6b090ce4a7002c69a9581893d4531"
  nonce := "ba6674aed6e1fd679dac49c111a02ab85286b5fa0b942fcb24f2c5663bece943"
  command := .execute "7fecda5b7b570e54d0998a9a01acfafdfdc88ba5b59de43ce666295cc086cd91" Phase17ControllerAuthorityExamples.completion0_0 }
def witness0_3 : WitnessState := updated witness0_2 request0_3 "f27bb361945f3bf7502a5f136af3d8c56e558fcac7def28d00bbeda5f4f56f4a" "fb3d4674fc1b52f57e2c431b04f8145436e0d9129ba58876df7dfc2ce068592f" Phase17ControllerAuthorityExamples.state0_2
theorem guard0_3 : AdvanceGuard provision0 witness0_2 request0_3
    "f27bb361945f3bf7502a5f136af3d8c56e558fcac7def28d00bbeda5f4f56f4a" "fb3d4674fc1b52f57e2c431b04f8145436e0d9129ba58876df7dfc2ce068592f" :=
  ⟨rfl, rfl, provision_valid0, rfl, rfl, by decide +kernel, by decide +kernel,
    by decide +kernel, by decide +kernel, by decide +kernel, rfl⟩
theorem performed0_3 : perform provision0 Phase17ControllerAuthorityExamples.contexts0 Phase17ControllerAuthorityExamples.evaluators0
    witness0_2 request0_3.command = some Phase17ControllerAuthorityExamples.state0_2 := by
  apply execute_construct
  · decide +kernel
  · rfl
  · exact Phase17ControllerAuthorityExamples.complete0_0
theorem step0_3 : advance provision0 Phase17ControllerAuthorityExamples.contexts0 Phase17ControllerAuthorityExamples.evaluators0
    witness0_2 request0_3 "f27bb361945f3bf7502a5f136af3d8c56e558fcac7def28d00bbeda5f4f56f4a" "fb3d4674fc1b52f57e2c431b04f8145436e0d9129ba58876df7dfc2ce068592f" = some witness0_3 :=
  advanced_construct provision0 Phase17ControllerAuthorityExamples.contexts0 Phase17ControllerAuthorityExamples.evaluators0 witness0_2 request0_3
    "f27bb361945f3bf7502a5f136af3d8c56e558fcac7def28d00bbeda5f4f56f4a" "fb3d4674fc1b52f57e2c431b04f8145436e0d9129ba58876df7dfc2ce068592f" Phase17ControllerAuthorityExamples.state0_2 guard0_3 performed0_3
theorem reachable0_3 : Reachable provision0 Phase17ControllerAuthorityExamples.contexts0 Phase17ControllerAuthorityExamples.evaluators0
    journal0 witness0_3 :=
  .advance reachable0_2 request0_3 "f27bb361945f3bf7502a5f136af3d8c56e558fcac7def28d00bbeda5f4f56f4a" "fb3d4674fc1b52f57e2c431b04f8145436e0d9129ba58876df7dfc2ce068592f" step0_3
-- Retained AI state projection SHA256: 6b3be86dc10d22d3c6f58034c5d11f0b37f39bd95f559305bda48dea5c78adc6
def request0_4 : Request := {
  provision := provision0.identity
  revision := 3
  head := "f27bb361945f3bf7502a5f136af3d8c56e558fcac7def28d00bbeda5f4f56f4a"
  journal := "fb3d4674fc1b52f57e2c431b04f8145436e0d9129ba58876df7dfc2ce068592f"
  nonce := "0f0e4504c544b399da883cc571200333f978ce9ab5a0231f84593bbc373d2850"
  command := .reopen }
def witness0_4 : WitnessState := updated witness0_3 request0_4 "68e493bb549b3ffbf11d581efa870b1dcb9465d1bf99b4738aeeb02b5df3c44e" "fb3d4674fc1b52f57e2c431b04f8145436e0d9129ba58876df7dfc2ce068592f" (Phase17ControllerAuthority.reopen Phase17ControllerAuthorityExamples.state0_2)
theorem guard0_4 : AdvanceGuard provision0 witness0_3 request0_4
    "68e493bb549b3ffbf11d581efa870b1dcb9465d1bf99b4738aeeb02b5df3c44e" "fb3d4674fc1b52f57e2c431b04f8145436e0d9129ba58876df7dfc2ce068592f" :=
  ⟨rfl, rfl, provision_valid0, rfl, rfl, by decide +kernel, by decide +kernel,
    by decide +kernel, by decide +kernel, by decide +kernel, rfl⟩
theorem performed0_4 : perform provision0 Phase17ControllerAuthorityExamples.contexts0 Phase17ControllerAuthorityExamples.evaluators0
    witness0_3 request0_4.command = some (Phase17ControllerAuthority.reopen Phase17ControllerAuthorityExamples.state0_2) := by rfl
theorem step0_4 : advance provision0 Phase17ControllerAuthorityExamples.contexts0 Phase17ControllerAuthorityExamples.evaluators0
    witness0_3 request0_4 "68e493bb549b3ffbf11d581efa870b1dcb9465d1bf99b4738aeeb02b5df3c44e" "fb3d4674fc1b52f57e2c431b04f8145436e0d9129ba58876df7dfc2ce068592f" = some witness0_4 :=
  advanced_construct provision0 Phase17ControllerAuthorityExamples.contexts0 Phase17ControllerAuthorityExamples.evaluators0 witness0_3 request0_4
    "68e493bb549b3ffbf11d581efa870b1dcb9465d1bf99b4738aeeb02b5df3c44e" "fb3d4674fc1b52f57e2c431b04f8145436e0d9129ba58876df7dfc2ce068592f" (Phase17ControllerAuthority.reopen Phase17ControllerAuthorityExamples.state0_2) guard0_4 performed0_4
theorem reachable0_4 : Reachable provision0 Phase17ControllerAuthorityExamples.contexts0 Phase17ControllerAuthorityExamples.evaluators0
    journal0 witness0_4 :=
  .advance reachable0_3 request0_4 "68e493bb549b3ffbf11d581efa870b1dcb9465d1bf99b4738aeeb02b5df3c44e" "fb3d4674fc1b52f57e2c431b04f8145436e0d9129ba58876df7dfc2ce068592f" step0_4
-- Retained AI state projection SHA256: 625f3bee970393bcbdc0b0d01c4c9cde89df75a908b4474c4bc6d6976831f996
def request0_5 : Request := {
  provision := provision0.identity
  revision := 4
  head := "68e493bb549b3ffbf11d581efa870b1dcb9465d1bf99b4738aeeb02b5df3c44e"
  journal := "fb3d4674fc1b52f57e2c431b04f8145436e0d9129ba58876df7dfc2ce068592f"
  nonce := "b0b02bc00961098fb35dc4fa69fe11d3b5ad125ffa6c0fd979e8ee87cb53bb48"
  command := .reserve "15f5c3504f70920e34821223b1b58c69773de96191173651c78a3f3df4729d11" Phase17ControllerAuthorityExamples.permit0_1 }
def witness0_5 : WitnessState := updated witness0_4 request0_5 "6a6a4698fdc7009910e9ef4b0099ccc1209d013d7d63641ed43f92f7a9604244" "bd0a086831d9c9009fd598373831d5b78ec7cfb5694cbcade77b6b3d2e75d002" Phase17ControllerAuthorityExamples.state0_3
theorem guard0_5 : AdvanceGuard provision0 witness0_4 request0_5
    "6a6a4698fdc7009910e9ef4b0099ccc1209d013d7d63641ed43f92f7a9604244" "bd0a086831d9c9009fd598373831d5b78ec7cfb5694cbcade77b6b3d2e75d002" :=
  ⟨rfl, rfl, provision_valid0, rfl, rfl, by decide +kernel, by decide +kernel,
    by decide +kernel, by decide +kernel, by decide +kernel, rfl⟩
theorem performed0_5 : perform provision0 Phase17ControllerAuthorityExamples.contexts0 Phase17ControllerAuthorityExamples.evaluators0
    witness0_4 request0_5.command = some Phase17ControllerAuthorityExamples.state0_3 := by
  apply reserve_construct
  · decide +kernel
  · rfl
  · exact Phase17ControllerAuthorityExamples.issue0_1
theorem step0_5 : advance provision0 Phase17ControllerAuthorityExamples.contexts0 Phase17ControllerAuthorityExamples.evaluators0
    witness0_4 request0_5 "6a6a4698fdc7009910e9ef4b0099ccc1209d013d7d63641ed43f92f7a9604244" "bd0a086831d9c9009fd598373831d5b78ec7cfb5694cbcade77b6b3d2e75d002" = some witness0_5 :=
  advanced_construct provision0 Phase17ControllerAuthorityExamples.contexts0 Phase17ControllerAuthorityExamples.evaluators0 witness0_4 request0_5
    "6a6a4698fdc7009910e9ef4b0099ccc1209d013d7d63641ed43f92f7a9604244" "bd0a086831d9c9009fd598373831d5b78ec7cfb5694cbcade77b6b3d2e75d002" Phase17ControllerAuthorityExamples.state0_3 guard0_5 performed0_5
theorem reachable0_5 : Reachable provision0 Phase17ControllerAuthorityExamples.contexts0 Phase17ControllerAuthorityExamples.evaluators0
    journal0 witness0_5 :=
  .advance reachable0_4 request0_5 "6a6a4698fdc7009910e9ef4b0099ccc1209d013d7d63641ed43f92f7a9604244" "bd0a086831d9c9009fd598373831d5b78ec7cfb5694cbcade77b6b3d2e75d002" step0_5
-- Retained AI state projection SHA256: 5e39e3c6d3a7fb373167f73bd3bda63077115fa619cb1d39b9b35b9eebdcfdaa
def request0_6 : Request := {
  provision := provision0.identity
  revision := 5
  head := "6a6a4698fdc7009910e9ef4b0099ccc1209d013d7d63641ed43f92f7a9604244"
  journal := "bd0a086831d9c9009fd598373831d5b78ec7cfb5694cbcade77b6b3d2e75d002"
  nonce := "31f114ad5f05d7a7a072829a5dc26aa60ee12dfd7337a50ceb567d70c1d8ead7"
  command := .execute "15f5c3504f70920e34821223b1b58c69773de96191173651c78a3f3df4729d11" Phase17ControllerAuthorityExamples.completion0_1 }
def witness0_6 : WitnessState := updated witness0_5 request0_6 "b3f476fd53993fe1a5075ddc0a29d0074d7579bf3d2aa5ebd7ae610f089adea0" "88ee8fe5c5ea2899d1490e8be781eea2d838e03324642272b0498008665c7ea0" Phase17ControllerAuthorityExamples.state0_4
theorem guard0_6 : AdvanceGuard provision0 witness0_5 request0_6
    "b3f476fd53993fe1a5075ddc0a29d0074d7579bf3d2aa5ebd7ae610f089adea0" "88ee8fe5c5ea2899d1490e8be781eea2d838e03324642272b0498008665c7ea0" :=
  ⟨rfl, rfl, provision_valid0, rfl, rfl, by decide +kernel, by decide +kernel,
    by decide +kernel, by decide +kernel, by decide +kernel, rfl⟩
theorem performed0_6 : perform provision0 Phase17ControllerAuthorityExamples.contexts0 Phase17ControllerAuthorityExamples.evaluators0
    witness0_5 request0_6.command = some Phase17ControllerAuthorityExamples.state0_4 := by
  apply execute_construct
  · decide +kernel
  · rfl
  · exact Phase17ControllerAuthorityExamples.complete0_1
theorem step0_6 : advance provision0 Phase17ControllerAuthorityExamples.contexts0 Phase17ControllerAuthorityExamples.evaluators0
    witness0_5 request0_6 "b3f476fd53993fe1a5075ddc0a29d0074d7579bf3d2aa5ebd7ae610f089adea0" "88ee8fe5c5ea2899d1490e8be781eea2d838e03324642272b0498008665c7ea0" = some witness0_6 :=
  advanced_construct provision0 Phase17ControllerAuthorityExamples.contexts0 Phase17ControllerAuthorityExamples.evaluators0 witness0_5 request0_6
    "b3f476fd53993fe1a5075ddc0a29d0074d7579bf3d2aa5ebd7ae610f089adea0" "88ee8fe5c5ea2899d1490e8be781eea2d838e03324642272b0498008665c7ea0" Phase17ControllerAuthorityExamples.state0_4 guard0_6 performed0_6
theorem reachable0_6 : Reachable provision0 Phase17ControllerAuthorityExamples.contexts0 Phase17ControllerAuthorityExamples.evaluators0
    journal0 witness0_6 :=
  .advance reachable0_5 request0_6 "b3f476fd53993fe1a5075ddc0a29d0074d7579bf3d2aa5ebd7ae610f089adea0" "88ee8fe5c5ea2899d1490e8be781eea2d838e03324642272b0498008665c7ea0" step0_6
-- Retained AI state projection SHA256: ce936be0ae9e476ef41c4a01fc6e4bea196a06bd3392a33b8f96a9cf64754d90
def request0_7 : Request := {
  provision := provision0.identity
  revision := 6
  head := "b3f476fd53993fe1a5075ddc0a29d0074d7579bf3d2aa5ebd7ae610f089adea0"
  journal := "88ee8fe5c5ea2899d1490e8be781eea2d838e03324642272b0498008665c7ea0"
  nonce := "236ecb861803116d225183be3a78d220617a89a1138206bd7ec621236347a364"
  command := .stop }
def witness0_7 : WitnessState := updated witness0_6 request0_7 "afd83ef187e9bf89c225c5ba056421563e36d711d033ec251a6b72fed057f155" "bfbdb68e1fca2418d452f18a1bc1c6a3c8ee71de375a0eef617672b1a58008c4" Phase17ControllerAuthorityExamples.state0_5
theorem guard0_7 : AdvanceGuard provision0 witness0_6 request0_7
    "afd83ef187e9bf89c225c5ba056421563e36d711d033ec251a6b72fed057f155" "bfbdb68e1fca2418d452f18a1bc1c6a3c8ee71de375a0eef617672b1a58008c4" :=
  ⟨rfl, rfl, provision_valid0, rfl, rfl, by decide +kernel, by decide +kernel,
    by decide +kernel, by decide +kernel, by decide +kernel, rfl⟩
theorem performed0_7 : perform provision0 Phase17ControllerAuthorityExamples.contexts0 Phase17ControllerAuthorityExamples.evaluators0
    witness0_6 request0_7.command = some Phase17ControllerAuthorityExamples.state0_5 := by exact Phase17ControllerAuthorityExamples.stop0
theorem step0_7 : advance provision0 Phase17ControllerAuthorityExamples.contexts0 Phase17ControllerAuthorityExamples.evaluators0
    witness0_6 request0_7 "afd83ef187e9bf89c225c5ba056421563e36d711d033ec251a6b72fed057f155" "bfbdb68e1fca2418d452f18a1bc1c6a3c8ee71de375a0eef617672b1a58008c4" = some witness0_7 :=
  advanced_construct provision0 Phase17ControllerAuthorityExamples.contexts0 Phase17ControllerAuthorityExamples.evaluators0 witness0_6 request0_7
    "afd83ef187e9bf89c225c5ba056421563e36d711d033ec251a6b72fed057f155" "bfbdb68e1fca2418d452f18a1bc1c6a3c8ee71de375a0eef617672b1a58008c4" Phase17ControllerAuthorityExamples.state0_5 guard0_7 performed0_7
theorem reachable0_7 : Reachable provision0 Phase17ControllerAuthorityExamples.contexts0 Phase17ControllerAuthorityExamples.evaluators0
    journal0 witness0_7 :=
  .advance reachable0_6 request0_7 "afd83ef187e9bf89c225c5ba056421563e36d711d033ec251a6b72fed057f155" "bfbdb68e1fca2418d452f18a1bc1c6a3c8ee71de375a0eef617672b1a58008c4" step0_7
theorem case_shared_two_sources : Reachable provision0 Phase17ControllerAuthorityExamples.contexts0 Phase17ControllerAuthorityExamples.evaluators0
    journal0 witness0_7 ∧ witness0_7.revision = 7 ∧
    witness0_7.authority = Phase17ControllerAuthorityExamples.state0_5 := ⟨reachable0_7, rfl, rfl⟩
def provision1 : Provision := {
  identity := "cf8e9b7d33ce14d7bb624efabe74fc6f02e896b50a2dba2cc9eed4a6c01b60d3"
  witness := "phase17aj.reference.interrupted_reservation"
  credential := "54a6c031d7ff83bb892708046c9d763bee29ad4290995f8db7efc05a9632deff"
  implementation := "13c252851490d937ae1c2f0e17c5d9c086893d7807f4b81add36045625caae99"
  genesis := "50c6b9a56d8b06fa16fdff5a2b9a4eff97698b83b7ec17264380183243d4572b"
  policy := Phase17ControllerAuthorityExamples.policy4 }
theorem provision_valid1 : ProvisionValid provision1 :=
  ⟨by decide +kernel, by decide +kernel, by decide +kernel, by decide +kernel,
    by decide +kernel, Phase17ControllerAuthorityExamples.policy_valid4⟩
def journal1 : String := "a513020e8bd10e7ee99da77e9d5d301105d30a12675fd3227ba49b8b16fa9579"
def witness1_0 : WitnessState := initial provision1 journal1
theorem reachable1_0 : Reachable provision1 Phase17ControllerAuthorityExamples.contexts4 Phase17ControllerAuthorityExamples.evaluators4
    journal1 witness1_0 := .initial
-- Retained AI state projection SHA256: fda434f33457d324b1431694ddbebcd02ac3083062d92bbbc8cc6621867530c3
def request1_1 : Request := {
  provision := provision1.identity
  revision := 0
  head := "50c6b9a56d8b06fa16fdff5a2b9a4eff97698b83b7ec17264380183243d4572b"
  journal := "a513020e8bd10e7ee99da77e9d5d301105d30a12675fd3227ba49b8b16fa9579"
  nonce := "dca4543466d287910ef9800e4bbb08795d895eaf50cf7e657ffe90ce5c04c304"
  command := .reopen }
def witness1_1 : WitnessState := updated witness1_0 request1_1 "e9878786338e388f89128feb2b6c6aba9ad7ffe02e7ca7b11b18be2b92e2c744" "a513020e8bd10e7ee99da77e9d5d301105d30a12675fd3227ba49b8b16fa9579" (Phase17ControllerAuthority.reopen Phase17ControllerAuthorityExamples.state4_0)
theorem guard1_1 : AdvanceGuard provision1 witness1_0 request1_1
    "e9878786338e388f89128feb2b6c6aba9ad7ffe02e7ca7b11b18be2b92e2c744" "a513020e8bd10e7ee99da77e9d5d301105d30a12675fd3227ba49b8b16fa9579" :=
  ⟨rfl, rfl, provision_valid1, rfl, rfl, by decide +kernel, by decide +kernel,
    by decide +kernel, by decide +kernel, by decide +kernel, rfl⟩
theorem performed1_1 : perform provision1 Phase17ControllerAuthorityExamples.contexts4 Phase17ControllerAuthorityExamples.evaluators4
    witness1_0 request1_1.command = some (Phase17ControllerAuthority.reopen Phase17ControllerAuthorityExamples.state4_0) := by rfl
theorem step1_1 : advance provision1 Phase17ControllerAuthorityExamples.contexts4 Phase17ControllerAuthorityExamples.evaluators4
    witness1_0 request1_1 "e9878786338e388f89128feb2b6c6aba9ad7ffe02e7ca7b11b18be2b92e2c744" "a513020e8bd10e7ee99da77e9d5d301105d30a12675fd3227ba49b8b16fa9579" = some witness1_1 :=
  advanced_construct provision1 Phase17ControllerAuthorityExamples.contexts4 Phase17ControllerAuthorityExamples.evaluators4 witness1_0 request1_1
    "e9878786338e388f89128feb2b6c6aba9ad7ffe02e7ca7b11b18be2b92e2c744" "a513020e8bd10e7ee99da77e9d5d301105d30a12675fd3227ba49b8b16fa9579" (Phase17ControllerAuthority.reopen Phase17ControllerAuthorityExamples.state4_0) guard1_1 performed1_1
theorem reachable1_1 : Reachable provision1 Phase17ControllerAuthorityExamples.contexts4 Phase17ControllerAuthorityExamples.evaluators4
    journal1 witness1_1 :=
  .advance reachable1_0 request1_1 "e9878786338e388f89128feb2b6c6aba9ad7ffe02e7ca7b11b18be2b92e2c744" "a513020e8bd10e7ee99da77e9d5d301105d30a12675fd3227ba49b8b16fa9579" step1_1
-- Retained AI state projection SHA256: 4b753cf20728d8afa9092b75911638f3252450b191dc9af1e2af5f1f8977df89
def request1_2 : Request := {
  provision := provision1.identity
  revision := 1
  head := "e9878786338e388f89128feb2b6c6aba9ad7ffe02e7ca7b11b18be2b92e2c744"
  journal := "a513020e8bd10e7ee99da77e9d5d301105d30a12675fd3227ba49b8b16fa9579"
  nonce := "e31d269143d98a81c525e1c6b1c4b6d2b22a444ee23adec075d057ee6766e40c"
  command := .reserve "fafe3de9d176b831fe6ef2c6dc66892484117a2dc29dae3e407f53d5d6f27ab3" Phase17ControllerAuthorityExamples.permit4_0 }
def witness1_2 : WitnessState := updated witness1_1 request1_2 "8cfae036808c82ec7cf2c4d38ad013560f25c514d22ff7a20d0065f81ce1039c" "db5d3431c4e5b7c6e533dc2b725672d5daf8c3bf053b7999da057f754b672a13" Phase17ControllerAuthorityExamples.state4_1
theorem guard1_2 : AdvanceGuard provision1 witness1_1 request1_2
    "8cfae036808c82ec7cf2c4d38ad013560f25c514d22ff7a20d0065f81ce1039c" "db5d3431c4e5b7c6e533dc2b725672d5daf8c3bf053b7999da057f754b672a13" :=
  ⟨rfl, rfl, provision_valid1, rfl, rfl, by decide +kernel, by decide +kernel,
    by decide +kernel, by decide +kernel, by decide +kernel, rfl⟩
theorem performed1_2 : perform provision1 Phase17ControllerAuthorityExamples.contexts4 Phase17ControllerAuthorityExamples.evaluators4
    witness1_1 request1_2.command = some Phase17ControllerAuthorityExamples.state4_1 := by
  apply reserve_construct
  · decide +kernel
  · rfl
  · exact Phase17ControllerAuthorityExamples.issue4_0
theorem step1_2 : advance provision1 Phase17ControllerAuthorityExamples.contexts4 Phase17ControllerAuthorityExamples.evaluators4
    witness1_1 request1_2 "8cfae036808c82ec7cf2c4d38ad013560f25c514d22ff7a20d0065f81ce1039c" "db5d3431c4e5b7c6e533dc2b725672d5daf8c3bf053b7999da057f754b672a13" = some witness1_2 :=
  advanced_construct provision1 Phase17ControllerAuthorityExamples.contexts4 Phase17ControllerAuthorityExamples.evaluators4 witness1_1 request1_2
    "8cfae036808c82ec7cf2c4d38ad013560f25c514d22ff7a20d0065f81ce1039c" "db5d3431c4e5b7c6e533dc2b725672d5daf8c3bf053b7999da057f754b672a13" Phase17ControllerAuthorityExamples.state4_1 guard1_2 performed1_2
theorem reachable1_2 : Reachable provision1 Phase17ControllerAuthorityExamples.contexts4 Phase17ControllerAuthorityExamples.evaluators4
    journal1 witness1_2 :=
  .advance reachable1_1 request1_2 "8cfae036808c82ec7cf2c4d38ad013560f25c514d22ff7a20d0065f81ce1039c" "db5d3431c4e5b7c6e533dc2b725672d5daf8c3bf053b7999da057f754b672a13" step1_2
-- Retained AI state projection SHA256: 4b753cf20728d8afa9092b75911638f3252450b191dc9af1e2af5f1f8977df89
def request1_3 : Request := {
  provision := provision1.identity
  revision := 2
  head := "8cfae036808c82ec7cf2c4d38ad013560f25c514d22ff7a20d0065f81ce1039c"
  journal := "db5d3431c4e5b7c6e533dc2b725672d5daf8c3bf053b7999da057f754b672a13"
  nonce := "73ec55c9a505fdae43887e53277f779468262b0b00f93b2fbb16260b8412e53f"
  command := .reopen }
def witness1_3 : WitnessState := updated witness1_2 request1_3 "80d7f418ada561fc9cfb3a7e654ceecee397d4d9bd10f06b4c2f9a6fc4fd5d12" "db5d3431c4e5b7c6e533dc2b725672d5daf8c3bf053b7999da057f754b672a13" (Phase17ControllerAuthority.reopen Phase17ControllerAuthorityExamples.state4_1)
theorem guard1_3 : AdvanceGuard provision1 witness1_2 request1_3
    "80d7f418ada561fc9cfb3a7e654ceecee397d4d9bd10f06b4c2f9a6fc4fd5d12" "db5d3431c4e5b7c6e533dc2b725672d5daf8c3bf053b7999da057f754b672a13" :=
  ⟨rfl, rfl, provision_valid1, rfl, rfl, by decide +kernel, by decide +kernel,
    by decide +kernel, by decide +kernel, by decide +kernel, rfl⟩
theorem performed1_3 : perform provision1 Phase17ControllerAuthorityExamples.contexts4 Phase17ControllerAuthorityExamples.evaluators4
    witness1_2 request1_3.command = some (Phase17ControllerAuthority.reopen Phase17ControllerAuthorityExamples.state4_1) := by rfl
theorem step1_3 : advance provision1 Phase17ControllerAuthorityExamples.contexts4 Phase17ControllerAuthorityExamples.evaluators4
    witness1_2 request1_3 "80d7f418ada561fc9cfb3a7e654ceecee397d4d9bd10f06b4c2f9a6fc4fd5d12" "db5d3431c4e5b7c6e533dc2b725672d5daf8c3bf053b7999da057f754b672a13" = some witness1_3 :=
  advanced_construct provision1 Phase17ControllerAuthorityExamples.contexts4 Phase17ControllerAuthorityExamples.evaluators4 witness1_2 request1_3
    "80d7f418ada561fc9cfb3a7e654ceecee397d4d9bd10f06b4c2f9a6fc4fd5d12" "db5d3431c4e5b7c6e533dc2b725672d5daf8c3bf053b7999da057f754b672a13" (Phase17ControllerAuthority.reopen Phase17ControllerAuthorityExamples.state4_1) guard1_3 performed1_3
theorem reachable1_3 : Reachable provision1 Phase17ControllerAuthorityExamples.contexts4 Phase17ControllerAuthorityExamples.evaluators4
    journal1 witness1_3 :=
  .advance reachable1_2 request1_3 "80d7f418ada561fc9cfb3a7e654ceecee397d4d9bd10f06b4c2f9a6fc4fd5d12" "db5d3431c4e5b7c6e533dc2b725672d5daf8c3bf053b7999da057f754b672a13" step1_3
theorem case_interrupted_reservation : Reachable provision1 Phase17ControllerAuthorityExamples.contexts4 Phase17ControllerAuthorityExamples.evaluators4
    journal1 witness1_3 ∧ witness1_3.revision = 3 ∧
    witness1_3.authority = (Phase17ControllerAuthority.reopen Phase17ControllerAuthorityExamples.state4_1) := ⟨reachable1_3, rfl, rfl⟩
def provision2 : Provision := {
  identity := "b551ab1b86af090a9cdb3384fef01036155465505af368ef6a9a761b343c74e3"
  witness := "phase17aj.reference.aggregate_denial"
  credential := "54a6c031d7ff83bb892708046c9d763bee29ad4290995f8db7efc05a9632deff"
  implementation := "13c252851490d937ae1c2f0e17c5d9c086893d7807f4b81add36045625caae99"
  genesis := "553d4a85bf32ab3f99c5a1c50daf3462d04af964fad020ef39fafccd169d9f7b"
  policy := Phase17ControllerAuthorityExamples.policy1 }
theorem provision_valid2 : ProvisionValid provision2 :=
  ⟨by decide +kernel, by decide +kernel, by decide +kernel, by decide +kernel,
    by decide +kernel, Phase17ControllerAuthorityExamples.policy_valid1⟩
def journal2 : String := "931559debcf826fe53bead6b77aca4b251c38496f394dc60e3291f510a43a6bd"
def witness2_0 : WitnessState := initial provision2 journal2
theorem reachable2_0 : Reachable provision2 Phase17ControllerAuthorityExamples.contexts1 Phase17ControllerAuthorityExamples.evaluators1
    journal2 witness2_0 := .initial
-- Retained AI state projection SHA256: 89a0aaa239601c0697704a1581cfc2e084a3718cbbbff3caf20ae14a2198db89
def request2_1 : Request := {
  provision := provision2.identity
  revision := 0
  head := "553d4a85bf32ab3f99c5a1c50daf3462d04af964fad020ef39fafccd169d9f7b"
  journal := "931559debcf826fe53bead6b77aca4b251c38496f394dc60e3291f510a43a6bd"
  nonce := "b721ae86b3748c4ed6449670647d6b6e3304c3fe6a650882cc2b61872fb2743e"
  command := .reopen }
def witness2_1 : WitnessState := updated witness2_0 request2_1 "bf8c20e2e42daf70ebe2d884e82f0837e865003358e995e41c862e42acd18bed" "931559debcf826fe53bead6b77aca4b251c38496f394dc60e3291f510a43a6bd" (Phase17ControllerAuthority.reopen Phase17ControllerAuthorityExamples.state1_0)
theorem guard2_1 : AdvanceGuard provision2 witness2_0 request2_1
    "bf8c20e2e42daf70ebe2d884e82f0837e865003358e995e41c862e42acd18bed" "931559debcf826fe53bead6b77aca4b251c38496f394dc60e3291f510a43a6bd" :=
  ⟨rfl, rfl, provision_valid2, rfl, rfl, by decide +kernel, by decide +kernel,
    by decide +kernel, by decide +kernel, by decide +kernel, rfl⟩
theorem performed2_1 : perform provision2 Phase17ControllerAuthorityExamples.contexts1 Phase17ControllerAuthorityExamples.evaluators1
    witness2_0 request2_1.command = some (Phase17ControllerAuthority.reopen Phase17ControllerAuthorityExamples.state1_0) := by rfl
theorem step2_1 : advance provision2 Phase17ControllerAuthorityExamples.contexts1 Phase17ControllerAuthorityExamples.evaluators1
    witness2_0 request2_1 "bf8c20e2e42daf70ebe2d884e82f0837e865003358e995e41c862e42acd18bed" "931559debcf826fe53bead6b77aca4b251c38496f394dc60e3291f510a43a6bd" = some witness2_1 :=
  advanced_construct provision2 Phase17ControllerAuthorityExamples.contexts1 Phase17ControllerAuthorityExamples.evaluators1 witness2_0 request2_1
    "bf8c20e2e42daf70ebe2d884e82f0837e865003358e995e41c862e42acd18bed" "931559debcf826fe53bead6b77aca4b251c38496f394dc60e3291f510a43a6bd" (Phase17ControllerAuthority.reopen Phase17ControllerAuthorityExamples.state1_0) guard2_1 performed2_1
theorem reachable2_1 : Reachable provision2 Phase17ControllerAuthorityExamples.contexts1 Phase17ControllerAuthorityExamples.evaluators1
    journal2 witness2_1 :=
  .advance reachable2_0 request2_1 "bf8c20e2e42daf70ebe2d884e82f0837e865003358e995e41c862e42acd18bed" "931559debcf826fe53bead6b77aca4b251c38496f394dc60e3291f510a43a6bd" step2_1
-- Retained AI state projection SHA256: 09394ce1fe1491b5e1d078a388b099bc21e6cf7de76072ee1fb7ab5ff6263f90
def request2_2 : Request := {
  provision := provision2.identity
  revision := 1
  head := "bf8c20e2e42daf70ebe2d884e82f0837e865003358e995e41c862e42acd18bed"
  journal := "931559debcf826fe53bead6b77aca4b251c38496f394dc60e3291f510a43a6bd"
  nonce := "0113fae3f92e42b81ecd744e50b7036475d972e01befce2955639d57b84ac20e"
  command := .reserve "904a70cc81d20cf4278a6ecc632203c514635162fb773cf658f18b9ee4eaa038" Phase17ControllerAuthorityExamples.permit1_0 }
def witness2_2 : WitnessState := updated witness2_1 request2_2 "c4d748e09d6b4d2e996573ede28e3569990197e5573f2b3373a890f1536abddc" "0c1cfdf8ad6fc920e9bb8a4cbfa75685e0f572f458215fe03841b2b050a67d69" Phase17ControllerAuthorityExamples.state1_1
theorem guard2_2 : AdvanceGuard provision2 witness2_1 request2_2
    "c4d748e09d6b4d2e996573ede28e3569990197e5573f2b3373a890f1536abddc" "0c1cfdf8ad6fc920e9bb8a4cbfa75685e0f572f458215fe03841b2b050a67d69" :=
  ⟨rfl, rfl, provision_valid2, rfl, rfl, by decide +kernel, by decide +kernel,
    by decide +kernel, by decide +kernel, by decide +kernel, rfl⟩
theorem performed2_2 : perform provision2 Phase17ControllerAuthorityExamples.contexts1 Phase17ControllerAuthorityExamples.evaluators1
    witness2_1 request2_2.command = some Phase17ControllerAuthorityExamples.state1_1 := by
  apply reserve_construct
  · decide +kernel
  · rfl
  · exact Phase17ControllerAuthorityExamples.issue1_0
theorem step2_2 : advance provision2 Phase17ControllerAuthorityExamples.contexts1 Phase17ControllerAuthorityExamples.evaluators1
    witness2_1 request2_2 "c4d748e09d6b4d2e996573ede28e3569990197e5573f2b3373a890f1536abddc" "0c1cfdf8ad6fc920e9bb8a4cbfa75685e0f572f458215fe03841b2b050a67d69" = some witness2_2 :=
  advanced_construct provision2 Phase17ControllerAuthorityExamples.contexts1 Phase17ControllerAuthorityExamples.evaluators1 witness2_1 request2_2
    "c4d748e09d6b4d2e996573ede28e3569990197e5573f2b3373a890f1536abddc" "0c1cfdf8ad6fc920e9bb8a4cbfa75685e0f572f458215fe03841b2b050a67d69" Phase17ControllerAuthorityExamples.state1_1 guard2_2 performed2_2
theorem reachable2_2 : Reachable provision2 Phase17ControllerAuthorityExamples.contexts1 Phase17ControllerAuthorityExamples.evaluators1
    journal2 witness2_2 :=
  .advance reachable2_1 request2_2 "c4d748e09d6b4d2e996573ede28e3569990197e5573f2b3373a890f1536abddc" "0c1cfdf8ad6fc920e9bb8a4cbfa75685e0f572f458215fe03841b2b050a67d69" step2_2
-- Retained AI state projection SHA256: 1bf3fe1179120f9216d54805caac1bc246ce718a4ee81e038d434e311dbd6925
def request2_3 : Request := {
  provision := provision2.identity
  revision := 2
  head := "c4d748e09d6b4d2e996573ede28e3569990197e5573f2b3373a890f1536abddc"
  journal := "0c1cfdf8ad6fc920e9bb8a4cbfa75685e0f572f458215fe03841b2b050a67d69"
  nonce := "4710af0337b781254a26424fb663ce615cd4e5b91ad4d01cbbb424d045e1a0e6"
  command := .execute "904a70cc81d20cf4278a6ecc632203c514635162fb773cf658f18b9ee4eaa038" Phase17ControllerAuthorityExamples.completion1_0 }
def witness2_3 : WitnessState := updated witness2_2 request2_3 "d2b26a087694a4862ff18bcb7e1ab0bb210e73c04e97863423d7fc87e25d81e1" "d2121a35d6b76439f5975b0fa8391bb5d791cbc137165f95d235d051c0bb68b2" Phase17ControllerAuthorityExamples.state1_2
theorem guard2_3 : AdvanceGuard provision2 witness2_2 request2_3
    "d2b26a087694a4862ff18bcb7e1ab0bb210e73c04e97863423d7fc87e25d81e1" "d2121a35d6b76439f5975b0fa8391bb5d791cbc137165f95d235d051c0bb68b2" :=
  ⟨rfl, rfl, provision_valid2, rfl, rfl, by decide +kernel, by decide +kernel,
    by decide +kernel, by decide +kernel, by decide +kernel, rfl⟩
theorem performed2_3 : perform provision2 Phase17ControllerAuthorityExamples.contexts1 Phase17ControllerAuthorityExamples.evaluators1
    witness2_2 request2_3.command = some Phase17ControllerAuthorityExamples.state1_2 := by
  apply execute_construct
  · decide +kernel
  · rfl
  · exact Phase17ControllerAuthorityExamples.complete1_0
theorem step2_3 : advance provision2 Phase17ControllerAuthorityExamples.contexts1 Phase17ControllerAuthorityExamples.evaluators1
    witness2_2 request2_3 "d2b26a087694a4862ff18bcb7e1ab0bb210e73c04e97863423d7fc87e25d81e1" "d2121a35d6b76439f5975b0fa8391bb5d791cbc137165f95d235d051c0bb68b2" = some witness2_3 :=
  advanced_construct provision2 Phase17ControllerAuthorityExamples.contexts1 Phase17ControllerAuthorityExamples.evaluators1 witness2_2 request2_3
    "d2b26a087694a4862ff18bcb7e1ab0bb210e73c04e97863423d7fc87e25d81e1" "d2121a35d6b76439f5975b0fa8391bb5d791cbc137165f95d235d051c0bb68b2" Phase17ControllerAuthorityExamples.state1_2 guard2_3 performed2_3
theorem reachable2_3 : Reachable provision2 Phase17ControllerAuthorityExamples.contexts1 Phase17ControllerAuthorityExamples.evaluators1
    journal2 witness2_3 :=
  .advance reachable2_2 request2_3 "d2b26a087694a4862ff18bcb7e1ab0bb210e73c04e97863423d7fc87e25d81e1" "d2121a35d6b76439f5975b0fa8391bb5d791cbc137165f95d235d051c0bb68b2" step2_3
-- Retained AI state projection SHA256: 77973cd7c78aca2b71601ae4b048be6a244e31edd6346e979aab3bc666051d29
def request2_4 : Request := {
  provision := provision2.identity
  revision := 3
  head := "d2b26a087694a4862ff18bcb7e1ab0bb210e73c04e97863423d7fc87e25d81e1"
  journal := "d2121a35d6b76439f5975b0fa8391bb5d791cbc137165f95d235d051c0bb68b2"
  nonce := "01e9278faafdac6dbb2c2fa2968f4ea67f918f76af58158d2503ff770d14eb8c"
  command := .deny Phase17ControllerAuthorityExamples.permit1_1 }
def witness2_4 : WitnessState := updated witness2_3 request2_4 "904fa5222288d4088f9e723fb94ff544bc4cb2df961ae20e9d05abbf3d3692e1" "ab3145569ac226a514f549d5bfd2c0b79d321adbd46933658295b0069f9528e0" Phase17ControllerAuthorityExamples.state1_3
theorem guard2_4 : AdvanceGuard provision2 witness2_3 request2_4
    "904fa5222288d4088f9e723fb94ff544bc4cb2df961ae20e9d05abbf3d3692e1" "ab3145569ac226a514f549d5bfd2c0b79d321adbd46933658295b0069f9528e0" :=
  ⟨rfl, rfl, provision_valid2, rfl, rfl, by decide +kernel, by decide +kernel,
    by decide +kernel, by decide +kernel, by decide +kernel, rfl⟩
theorem performed2_4 : perform provision2 Phase17ControllerAuthorityExamples.contexts1 Phase17ControllerAuthorityExamples.evaluators1
    witness2_3 request2_4.command = some Phase17ControllerAuthorityExamples.state1_3 := by
  change Phase17ControllerAuthority.deny Phase17ControllerAuthorityExamples.policy1 Phase17ControllerAuthorityExamples.policy1 "d2121a35d6b76439f5975b0fa8391bb5d791cbc137165f95d235d051c0bb68b2"
    "d2121a35d6b76439f5975b0fa8391bb5d791cbc137165f95d235d051c0bb68b2" Phase17ControllerAuthorityExamples.state1_2 Phase17ControllerAuthorityExamples.permit1_1 = some Phase17ControllerAuthorityExamples.state1_3
  exact Phase17ControllerAuthorityExamples.deny1
theorem step2_4 : advance provision2 Phase17ControllerAuthorityExamples.contexts1 Phase17ControllerAuthorityExamples.evaluators1
    witness2_3 request2_4 "904fa5222288d4088f9e723fb94ff544bc4cb2df961ae20e9d05abbf3d3692e1" "ab3145569ac226a514f549d5bfd2c0b79d321adbd46933658295b0069f9528e0" = some witness2_4 :=
  advanced_construct provision2 Phase17ControllerAuthorityExamples.contexts1 Phase17ControllerAuthorityExamples.evaluators1 witness2_3 request2_4
    "904fa5222288d4088f9e723fb94ff544bc4cb2df961ae20e9d05abbf3d3692e1" "ab3145569ac226a514f549d5bfd2c0b79d321adbd46933658295b0069f9528e0" Phase17ControllerAuthorityExamples.state1_3 guard2_4 performed2_4
theorem reachable2_4 : Reachable provision2 Phase17ControllerAuthorityExamples.contexts1 Phase17ControllerAuthorityExamples.evaluators1
    journal2 witness2_4 :=
  .advance reachable2_3 request2_4 "904fa5222288d4088f9e723fb94ff544bc4cb2df961ae20e9d05abbf3d3692e1" "ab3145569ac226a514f549d5bfd2c0b79d321adbd46933658295b0069f9528e0" step2_4
theorem case_aggregate_denial : Reachable provision2 Phase17ControllerAuthorityExamples.contexts1 Phase17ControllerAuthorityExamples.evaluators1
    journal2 witness2_4 ∧ witness2_4.revision = 4 ∧
    witness2_4.authority = Phase17ControllerAuthorityExamples.state1_3 := ⟨reachable2_4, rfl, rfl⟩

theorem main_exact_reservation : Phase17ControllerAuthority.reservedVector witness0_7.authority = [64, 128, 512, 512] ∧
    Phase17ControllerAuthority.reservedCost witness0_7.authority = 7168 :=
  Phase17ControllerAuthorityExamples.main_exact_reservation

theorem main_actual_reference_work : Phase17ControllerAuthority.completedCost witness0_7.authority = 1008 := by decide +kernel

theorem main_accounted_reservation :
    Phase17ControllerAuthority.completedCost witness0_7.authority +
      Phase17ControllerAuthority.pendingCost provision0.policy witness0_7.authority ≤
      Phase17ControllerAuthority.reservedCost witness0_7.authority :=
  reachable_completed_and_pending_accounted provision0 Phase17ControllerAuthorityExamples.contexts0
    Phase17ControllerAuthorityExamples.evaluators0 journal0 witness0_7 reachable0_7

theorem main_fixed_policy_meanings : provision0.policy = Phase17ControllerAuthorityExamples.policy0 ∧
    Phase17ControllerAuthorityExamples.permit0_0.objective = provision0.policy.objective ∧
    Phase17ControllerAuthorityExamples.permit0_1.objective = provision0.policy.objective ∧
    Phase17ControllerAuthorityExamples.permit0_0.evaluatorCode = provision0.policy.evaluatorCode ∧
    Phase17ControllerAuthorityExamples.permit0_1.evaluatorCode = provision0.policy.evaluatorCode := by decide +kernel

theorem main_reopen_retains_completed_state : witness0_4.authority =
    Phase17ControllerAuthority.reopen witness0_3.authority ∧ witness0_4.owner = none ∧
    witness0_4.journal = witness0_3.journal ∧
    Phase17ControllerAuthority.reservedCost witness0_4.authority = 3584 :=
  ⟨rfl, rfl, rfl, by decide +kernel⟩

theorem main_consumed_sources_once : witness0_7.authority.consumed.Nodup :=
  reachable_sources_consumed_once provision0 Phase17ControllerAuthorityExamples.contexts0
    Phase17ControllerAuthorityExamples.evaluators0 journal0 witness0_7 reachable0_7

theorem main_requests_consumed_once : witness0_7.nonces.Nodup :=
  reachable_nonces_unique provision0 Phase17ControllerAuthorityExamples.contexts0
    Phase17ControllerAuthorityExamples.evaluators0 journal0 witness0_7 reachable0_7

theorem main_revision_exact : witness0_7.revision = witness0_7.nonces.length :=
  reachable_revision_exact provision0 Phase17ControllerAuthorityExamples.contexts0
    Phase17ControllerAuthorityExamples.evaluators0 journal0 witness0_7 reachable0_7

theorem first_lease_recomputes_authority :
    perform provision0 Phase17ControllerAuthorityExamples.contexts0 Phase17ControllerAuthorityExamples.evaluators0
      witness0_1 request0_2.command = some Phase17ControllerAuthorityExamples.state0_1 := performed0_2

theorem second_lease_recomputes_authority :
    perform provision0 Phase17ControllerAuthorityExamples.contexts0 Phase17ControllerAuthorityExamples.evaluators0
      witness0_4 request0_5.command = some Phase17ControllerAuthorityExamples.state0_3 := performed0_5

theorem first_completion_recomputes_controller :
    Phase17ControllerAuthority.CompletionValid provision0.policy Phase17ControllerAuthorityExamples.contexts0
      Phase17ControllerAuthorityExamples.evaluators0 witness0_2.authority Phase17ControllerAuthorityExamples.completion0_0 := by
  apply execution_recomputes_truthful_controller
  exact performed0_3

theorem second_completion_recomputes_controller :
    Phase17ControllerAuthority.CompletionValid provision0.policy Phase17ControllerAuthorityExamples.contexts0
      Phase17ControllerAuthorityExamples.evaluators0 witness0_5.authority Phase17ControllerAuthorityExamples.completion0_1 := by
  apply execution_recomputes_truthful_controller
  exact performed0_6

def clonedRequest : Request := { request0_2 with
  nonce := "fresh-competing-nonce"
  command := .reserve "different-controller-owner" Phase17ControllerAuthorityExamples.permit0_1 }

theorem cloned_controller_cursor_refused :
    advance provision0 Phase17ControllerAuthorityExamples.contexts0 Phase17ControllerAuthorityExamples.evaluators0
      witness0_2 clonedRequest "competing-head" "competing-journal" = none := by
  apply stale_revision_refused
  decide +kernel

theorem old_read_nonce_refused (authentic : ReadResponse → Prop) :
    ¬ ReadAccepted authentic provision0 "fresh-read" witness0_1 (readResponse witness0_1 "old-read") := by
  apply wrong_nonce_read_refused
  decide +kernel

theorem old_read_after_advance_is_not_current (authentic : ReadResponse → Prop) :
    ¬ ReadAccepted authentic provision0 "same-read" witness0_2 (readResponse witness0_1 "same-read") := by
  apply wrong_head_read_refused
  decide +kernel

theorem pending_reopen_preserves_charges :
    witness1_3.authority.pending = some Phase17ControllerAuthorityExamples.lease4_0 ∧
    Phase17ControllerAuthority.reservedCost witness1_3.authority = 3584 ∧
    witness1_3.authority.liveLease = none ∧ witness1_3.owner = none ∧
    witness1_3.journal = witness1_2.journal := by decide +kernel

theorem pending_reopen_cannot_execute (owner : String) (result : Phase17ControllerAuthority.Completion) :
    perform provision1 Phase17ControllerAuthorityExamples.contexts4 Phase17ControllerAuthorityExamples.evaluators4
      witness1_3 (.execute owner result) = none :=
  missing_owner_execution_refused provision1 Phase17ControllerAuthorityExamples.contexts4
    Phase17ControllerAuthorityExamples.evaluators4 witness1_3 owner result rfl

theorem pending_reopen_cannot_issue :
    perform provision1 Phase17ControllerAuthorityExamples.contexts4 Phase17ControllerAuthorityExamples.evaluators4
      witness1_3 (.reserve "new-owner" Phase17ControllerAuthorityExamples.permit4_1) = none := by decide +kernel

theorem pending_reopen_cannot_stop :
    perform provision1 Phase17ControllerAuthorityExamples.contexts4 Phase17ControllerAuthorityExamples.evaluators4
      witness1_3 .stop = none := by decide +kernel

theorem aggregate_denial_preserves_charges :
    witness2_4.authority.nextSerial = 1 ∧ Phase17ControllerAuthority.reservedCost witness2_4.authority = 3584 ∧
    witness2_4.authority.pending = none ∧ witness2_4.authority.halted = true :=
  Phase17ControllerAuthorityExamples.aggregate_denial_no_new_lease

/-- Restoring the witness itself to a former trusted state re-enables that
    state's valid request. The controller-snapshot result cannot rule this out. -/
theorem witness_rollback_is_outside_guarantee :
    advance provision0 Phase17ControllerAuthorityExamples.contexts0 Phase17ControllerAuthorityExamples.evaluators0
      witness0_1 request0_2 witness0_2.head witness0_2.journal ≠ none := by
  have accepted : advance provision0 Phase17ControllerAuthorityExamples.contexts0
      Phase17ControllerAuthorityExamples.evaluators0 witness0_1 request0_2
      witness0_2.head witness0_2.journal = some witness0_2 := step0_2
  rw [accepted]
  exact Option.some_ne_none _

end Phase17AuthorityWitnessExamples
