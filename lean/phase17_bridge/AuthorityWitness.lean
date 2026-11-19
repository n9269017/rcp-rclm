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
