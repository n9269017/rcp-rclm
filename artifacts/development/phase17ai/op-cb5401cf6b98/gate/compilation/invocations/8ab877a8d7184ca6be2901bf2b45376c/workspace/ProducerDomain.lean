import TruthfulSuccessorInterface

/- Phase 17AH: source-indexed coverage of the declared producer grammar and
   truthful evaluation/controller composition. The complete row table is tied
   to the supplied source, its keys and descriptors. Python reconstructs the
   table from captured producer bytes; this module does not prove physical
   extraction or a general Python refinement. A caller's externally retained
   grant is an explicit authority parameter, not authority created by a hash.
   Resource facts concern only the listed reference-work charges. -/
namespace Phase17ProducerDomain

open RcpRclmFormalCoreV2 RcpRclmFormalCoreV3
open Phase17TaskInterpretation Phase17TruthfulSuccessor

structure Domain where
  context : Phase17Provenance.Context
  programs : List (String × Phase17Finite.Program)
  deriving DecidableEq

def rowProgram (domain : Domain) (index : Nat) : Phase17Finite.Program :=
  (domain.programs.getD index ("", ⟨0, 0, 0, 0⟩)).2

/-- The 32 rows are the exact eight-family/four-variant grammar at this source.
    The separate byte checks supply the captured descriptor/key association;
    no cryptographic authenticity is inferred from these finite equalities. -/
def DomainBound (s : State) (domain : Domain) : Prop :=
  domain.context.parentPackage = s.packageHash ∧
  Phase17Provenance.ContextValid domain.context ∧
  domain.programs.length = 32 ∧
  domain.programs.map Prod.fst = domain.context.rows.map Phase17Provenance.RankedProgram.key ∧
  (∀ i : Fin 32, (rowProgram domain i).family = (Phase17Provenance.rowAt domain.context i).family ∧
    (rowProgram domain i).family < 8 ∧ (rowProgram domain i).variant < 4) ∧
  (∀ family : Fin 8, ∀ variant : Fin 4, ∃ i : Fin 32,
    (rowProgram domain i).family = family ∧ (rowProgram domain i).variant = variant)

theorem domain_parent (s : State) (domain : Domain) (bound : DomainBound s domain) :
    domain.context.parentPackage = s.packageHash := bound.1

theorem domain_shape (s : State) (domain : Domain) (bound : DomainBound s domain) :
    Phase17Controller.ContextShape domain.context := ⟨bound.2.1.1, bound.2.1.2.2.1⟩

theorem stale_domain_rejected (s : State) (domain : Domain)
    (stale : domain.context.parentPackage ≠ s.packageHash) : ¬ DomainBound s domain := by
  intro bound
  exact stale bound.1

theorem row_descriptor_bound (s : State) (domain : Domain) (bound : DomainBound s domain)
    (index : Nat) (inside : index < 32) :
    (rowProgram domain index).family = (Phase17Provenance.rowAt domain.context index).family ∧
    (rowProgram domain index).family < 8 ∧ (rowProgram domain index).variant < 4 :=
  bound.2.2.2.2.1 ⟨index, inside⟩

theorem row_key_bound (s : State) (domain : Domain) (bound : DomainBound s domain)
    (index : Nat) :
    (domain.programs.getD index ("", ⟨0, 0, 0, 0⟩)).1 =
      (Phase17Provenance.rowAt domain.context index).key := by
  have keys := congrArg (fun (xs : List String) => xs.getD index "") bound.2.2.2.1
  calc
    _ = (domain.programs.map Prod.fst).getD index "" :=
      (List.getD_map (l := domain.programs) (d := ("", ⟨0, 0, 0, 0⟩)) (n := index) Prod.fst).symm
    _ = (domain.context.rows.map Phase17Provenance.RankedProgram.key).getD index "" := keys
    _ = _ := List.getD_map (l := domain.context.rows)
      (d := { key := "", family := 8, baseScore := 0, ties := [] }) (n := index)
      Phase17Provenance.RankedProgram.key

theorem grammar_slot_covered (s : State) (domain : Domain) (bound : DomainBound s domain)
    (family : Fin 8) (variant : Fin 4) :
    ∃ index : Fin 32, (rowProgram domain index).family = family ∧
      (rowProgram domain index).variant = variant := bound.2.2.2.2.2 family variant

/-- This order is the selector's counterfactual all-rejection order. It is used
    for coverage; it is never reported as an actual evaluator history. -/
def producerOrder (context : Phase17Provenance.Context) : List Nat :=
  ((Phase17Controller.rejectionRun context (Phase17Controller.initial 32) 32).map
    Phase17Controller.seen).getD []

theorem producer_order_spec (context : Phase17Provenance.Context)
    (shape : Phase17Controller.ContextShape context) :
    (producerOrder context).Nodup ∧ (producerOrder context).length = 32 ∧
      (producerOrder context).toFinset = Finset.range 32 := by
  obtain ⟨priorState, run, _, coverage, count, _⟩ :=
    Phase17Controller.all_rejections_exhaust context shape 32 le_rfl
  obtain ⟨observations, replayed, _, _⟩ :=
    Phase17Controller.rejection_run_replays context (Phase17Controller.initial 32) priorState 32 run
  have unique := Phase17Controller.replay_no_repeat context shape 32 observations priorState replayed
  simp only [producerOrder, run, Option.map_some, Option.getD_some]
  exact ⟨unique, by simpa only [Phase17Controller.seen, List.length_map] using count, coverage⟩

theorem producer_order_mem_iff (context : Phase17Provenance.Context)
    (shape : Phase17Controller.ContextShape context) (index : Nat) :
    index ∈ producerOrder context ↔ index < 32 := by
  rw [← List.mem_toFinset, (producer_order_spec context shape).2.2]
  exact Finset.mem_range

theorem ordered_grammar_coverage (s : State) (domain : Domain) (bound : DomainBound s domain)
    (family : Fin 8) (variant : Fin 4) :
    ∃ index ∈ producerOrder domain.context, (rowProgram domain index).family = family ∧
      (rowProgram domain index).variant = variant := by
  obtain ⟨index, covered⟩ := grammar_slot_covered s domain bound family variant
  exact ⟨index, (producer_order_mem_iff domain.context (domain_shape s domain bound) index).mpr
    index.isLt, covered⟩

def appendedObservation (s : State) (key : String) (program : Phase17Finite.Program) :
    Phase17TaskMeaning.ObservationState :=
  { proofs := s.proofs, programs := s.programs ++ [(key, program)] }

def newTaskCheck (fixed : Phase17Finite.Configuration) (s : State) (key : String)
    (program : Phase17Finite.Program) (task : Nat) : Bool :=
  !(fixed.catalog task).check (Phase17Finite.taskObservation s) &&
    (fixed.catalog task).check (appendedObservation s key program)

/-- The first missing realized meaning is chosen from the already fixed finite
    catalog. It is not a candidate-selected task interpretation. -/
def canonicalTask (fixed : Phase17Finite.Configuration) (s : State) (key : String)
    (program : Phase17Finite.Program) : Option Nat :=
  (List.range 282).find? (newTaskCheck fixed s key program)

theorem canonical_task_sound (fixed : Phase17Finite.Configuration) (s : State)
    (key : String) (program : Phase17Finite.Program) (task : Nat)
    (selected : canonicalTask fixed s key program = some task) :
    task < 282 ∧ (fixed.catalog task).check (Phase17Finite.taskObservation s) = false ∧
      (fixed.catalog task).check (appendedObservation s key program) = true := by
  have member := List.mem_of_find?_eq_some selected
  have checked := List.find?_some selected
  have pair : (!(fixed.catalog task).check (Phase17Finite.taskObservation s)) = true ∧
      (fixed.catalog task).check (appendedObservation s key program) = true := by
    simpa only [newTaskCheck, Bool.and_eq_true] using checked
  refine ⟨List.mem_range.mp member, ?_, pair.2⟩
  have no := pair.1
  cases before : (fixed.catalog task).check (Phase17Finite.taskObservation s) with
  | false => rfl
  | true => simp [before] at no

theorem canonical_none_iff (fixed : Phase17Finite.Configuration) (s : State)
    (key : String) (program : Phase17Finite.Program) :
    canonicalTask fixed s key program = none ↔
      ∀ task, task < 282 → newTaskCheck fixed s key program task = false := by
  simp only [canonicalTask, List.find?_eq_none, List.mem_range, Bool.eq_false_iff]

theorem canonical_task_first (fixed : Phase17Finite.Configuration) (s : State)
    (key : String) (program : Phase17Finite.Program) (task : Nat)
    (selected : canonicalTask fixed s key program = some task) :
    ∃ earlier later, List.range 282 = earlier ++ task :: later ∧
      ∀ prior ∈ earlier, newTaskCheck fixed s key program prior = false := by
  rcases List.find?_eq_some_iff_append.mp selected with ⟨_, earlier, later, order, rejected⟩
  refine ⟨earlier, later, order, ?_⟩
  intro prior member
  apply Bool.eq_false_iff.mpr
  intro passed
  have no := rejected prior member
  simp only [passed, Bool.not_true, Bool.false_eq_true] at no

theorem canonical_exists_iff (fixed : Phase17Finite.Configuration) (s : State)
    (key : String) (program : Phase17Finite.Program) :
    (∃ task, canonicalTask fixed s key program = some task) ↔
      ∃ task, task < 282 ∧ newTaskCheck fixed s key program task = true := by
  constructor
  · rintro ⟨task, selected⟩
    exact ⟨task, (canonical_task_sound fixed s key program task selected).1,
      List.find?_some selected⟩
  · rintro ⟨task, inside, checked⟩
    cases selected : canonicalTask fixed s key program with
    | some found => exact ⟨found, rfl⟩
    | none =>
        have refused := (canonical_none_iff fixed s key program).mp selected task inside
        rw [refused] at checked
        cases checked

theorem canonical_semantic_gain (fixed : Phase17Finite.Configuration)
    (complete : CatalogComplete fixed) (s : State) (key : String)
    (program : Phase17Finite.Program) (task : Nat)
    (selected : canonicalTask fixed s key program = some task) :
    ¬ (fixed.catalog task).holds (Phase17Finite.taskObservation s) ∧
      (fixed.catalog task).holds (appendedObservation s key program) := by
  rcases canonical_task_sound fixed s key program task selected with ⟨_, before, after⟩
  constructor
  · rw [← complete]
    exact Bool.eq_false_iff.mp before
  · exact (complete _ _).mp after

theorem no_task_no_semantic_gain (fixed : Phase17Finite.Configuration)
    (complete : CatalogComplete fixed) (s : State) (key : String)
    (program : Phase17Finite.Program) (none : canonicalTask fixed s key program = none)
    (task : Nat) (inside : task < 282) :
    ¬ (¬ (fixed.catalog task).holds (Phase17Finite.taskObservation s) ∧
      (fixed.catalog task).holds (appendedObservation s key program)) := by
  rintro ⟨before, after⟩
  have beforeFalse : (fixed.catalog task).check (Phase17Finite.taskObservation s) = false := by
    apply Bool.eq_false_iff.mpr
    intro h
    exact before ((complete _ _).mp h)
  have afterTrue := (complete _ _).mpr after
  have absent := (canonical_none_iff fixed s key program).mp none task inside
  simp [newTaskCheck, beforeFalse, afterTrue] at absent

def OfferBound (fixed : Phase17Finite.Configuration) (s : State) (domain : Domain)
    (index task : Nat) (offer : Offer) : Prop :=
  index < 32 ∧ canonicalTask fixed s (Phase17Provenance.rowAt domain.context index).key
      (rowProgram domain index) = some task ∧
  offer.update.key = (Phase17Provenance.rowAt domain.context index).key ∧
  offer.update.program = rowProgram domain index ∧ offer.update.task = task ∧
  offer.update.taskName = fixed.taskName task ∧ offer.update.parentPackage = s.packageHash ∧
  offer.update.contextHash = domain.context.contextHash ∧ offer.next = Phase17Finite.apply s offer.update

theorem offer_descriptor_cannot_substitute (fixed : Phase17Finite.Configuration) (s : State)
    (domain : Domain) (index task : Nat) (offer : Offer)
    (bound : OfferBound fixed s domain index task offer) :
    offer.update.key = (Phase17Provenance.rowAt domain.context index).key ∧
      offer.update.program = rowProgram domain index := ⟨bound.2.2.1, bound.2.2.2.1⟩

theorem offer_task_cannot_substitute (fixed : Phase17Finite.Configuration) (s : State)
    (domain : Domain) (index task : Nat) (offer : Offer)
    (bound : OfferBound fixed s domain index task offer) :
    offer.update.task = task ∧ canonicalTask fixed s
      (Phase17Provenance.rowAt domain.context index).key (rowProgram domain index) = some task :=
  ⟨bound.2.2.2.2.1, bound.2.1⟩

abbrev Builder := List Nat → Nat → Nat → Offer
abbrev ChargesAt := List Nat → Nat → Charges

/-- The candidate does not supply its descriptor, parent, context, task name,
    append projection or proposal ordering. The remaining package identity is
    a separately captured association, not a proven cryptographic computation. -/
def constructOffer (fixed : Phase17Finite.Configuration) (s : State) (domain : Domain)
    (packageIdentity : String) (prior : List Nat) (index task : Nat)
    (work : List Phase17Resource.Kind) : Offer :=
  let key := (Phase17Provenance.rowAt domain.context index).key
  let update : Phase17Finite.Update :=
    { key := key, program := rowProgram domain index, task := task,
      taskName := fixed.taskName task, parentPackage := s.packageHash,
      candidatePackage := packageIdentity, contextHash := domain.context.contextHash, charges := work }
  let proposal : Phase17Provenance.Proposal := {
    generator := domain.context.generator
    parentPackage := domain.context.parentPackage
    contextHash := domain.context.contextHash
    transcriptHash := domain.context.transcriptHash
    choices := prior ++ [index]
    verdicts := List.replicate prior.length false ++ [true]
    program := key
    candidatePackage := packageIdentity }
  let evidence : Evidence := {
    root := s.root
    parentPackage := s.packageHash
    candidatePackage := packageIdentity
    contextHash := domain.context.contextHash
    transcriptHash := domain.context.transcriptHash
    charges := work
    proposal := proposal }
  ⟨update, Phase17Finite.apply s update, evidence⟩

theorem constructed_offer_bound (fixed : Phase17Finite.Configuration) (s : State) (domain : Domain)
    (packageIdentity : String) (prior : List Nat) (index task : Nat)
    (work : List Phase17Resource.Kind) (inside : index < 32)
    (chosen : canonicalTask fixed s (Phase17Provenance.rowAt domain.context index).key
      (rowProgram domain index) = some task) :
    OfferBound fixed s domain index task
      (constructOffer fixed s domain packageIdentity prior index task work) := by
  exact ⟨inside, chosen, rfl, rfl, rfl, rfl, rfl, rfl, rfl⟩

instance offerBoundDecidable (fixed : Phase17Finite.Configuration) (s : State) (domain : Domain)
    (index task : Nat) (offer : Offer) : Decidable (OfferBound fixed s domain index task offer) := by
  unfold OfferBound
  infer_instance

instance domainBoundDecidable (s : State) (domain : Domain) : Decidable (DomainBound s domain) := by
  unfold DomainBound Phase17Provenance.ContextValid
  infer_instance

def RequestBound (contexts : Contexts) (s : State) (domain : Domain) : Prop :=
  contexts s = domain.context ∧ DomainBound s domain

instance requestBoundDecidable (contexts : Contexts) (s : State) (domain : Domain) :
    Decidable (RequestBound contexts s domain) := by
  unfold RequestBound
  infer_instance

def evaluate (fixed : Phase17Finite.Configuration) (contexts : Contexts) (charges : ChargesAt)
    (s : State) (domain : Domain) (build : Builder) (prior : List Nat) (index : Nat) : Bool :=
  match canonicalTask fixed s (Phase17Provenance.rowAt domain.context index).key
      (rowProgram domain index) with
  | none => false
  | some task => decide (RequestBound contexts s domain ∧
      OfferBound fixed s domain index task (build prior index task)) &&
      check fixed contexts (charges prior index) s (build prior index task)

theorem evaluation_of_checked (fixed : Phase17Finite.Configuration) (contexts : Contexts)
    (charges : ChargesAt) (s : State) (domain : Domain) (build : Builder)
    (prior : List Nat) (index task : Nat)
    (selected : canonicalTask fixed s (Phase17Provenance.rowAt domain.context index).key
      (rowProgram domain index) = some task)
    (requestBound : RequestBound contexts s domain)
    (offerBound : OfferBound fixed s domain index task (build prior index task))
    (checked : check fixed contexts (charges prior index) s (build prior index task) = true) :
    evaluate fixed contexts charges s domain build prior index = true := by
  unfold evaluate
  rw [selected]
  exact Bool.and_eq_true_iff.mpr ⟨decide_eq_true ⟨requestBound, offerBound⟩, checked⟩

theorem no_contract_refused (fixed : Phase17Finite.Configuration) (contexts : Contexts)
    (charges : ChargesAt) (s : State) (domain : Domain) (build : Builder)
    (prior : List Nat) (index : Nat)
    (absent : canonicalTask fixed s (Phase17Provenance.rowAt domain.context index).key
      (rowProgram domain index) = none) :
    evaluate fixed contexts charges s domain build prior index = false := by
  simp only [evaluate, absent]

theorem evaluation_acceptance (fixed : Phase17Finite.Configuration) (contexts : Contexts)
    (charges : ChargesAt) (complete : CatalogComplete fixed) (s : State) (domain : Domain)
    (build : Builder) (prior : List Nat) (index : Nat)
    (passed : evaluate fixed contexts charges s domain build prior index = true) :
    ∃ task, canonicalTask fixed s (Phase17Provenance.rowAt domain.context index).key
        (rowProgram domain index) = some task ∧
      RequestBound contexts s domain ∧
      OfferBound fixed s domain index task (build prior index task) ∧
      Accepted fixed contexts (charges prior index) s (build prior index task) := by
  unfold evaluate at passed
  cases chosen : canonicalTask fixed s (Phase17Provenance.rowAt domain.context index).key
      (rowProgram domain index) with
  | none => simp [chosen] at passed
  | some task =>
      have checked : (RequestBound contexts s domain ∧
          OfferBound fixed s domain index task (build prior index task)) ∧
          check fixed contexts (charges prior index) s (build prior index task) = true := by
        simpa only [chosen, Bool.and_eq_true, decide_eq_true_eq] using passed
      exact ⟨task, rfl, checked.1.1, checked.1.2,
        check_sound fixed contexts (charges prior index) complete s (build prior index task) checked.2⟩

/-- Every supplied Boolean must equal the source evaluator at the exact
    already-recorded priorState. Historical verdicts are not free premises. -/
def truthfulReplay (context : Phase17Provenance.Context) (evaluator : List Nat → Nat → Bool)
    (priorState : Phase17Controller.Prefix) : List Phase17Controller.Observation →
      Option Phase17Controller.Prefix
  | [] => some priorState
  | observation :: rest =>
      if observation.passed = evaluator (Phase17Controller.seen priorState) observation.index then
        (Phase17Controller.advance context priorState observation).bind
          (fun next => truthfulReplay context evaluator next rest)
      else none

theorem truthful_replay_projects (context : Phase17Provenance.Context)
    (evaluator : List Nat → Nat → Bool) (priorState final : Phase17Controller.Prefix)
    (observations : List Phase17Controller.Observation)
    (truthful : truthfulReplay context evaluator priorState observations = some final) :
    Phase17Controller.replay context priorState observations = some final := by
  induction observations generalizing priorState with
  | nil => exact truthful
  | cons observation rest ih =>
      by_cases same : observation.passed = evaluator (Phase17Controller.seen priorState) observation.index
      · cases advanced : Phase17Controller.advance context priorState observation with
        | none => simp [truthfulReplay, same, advanced] at truthful
        | some next =>
            have tail : truthfulReplay context evaluator next rest = some final := by
              simpa only [truthfulReplay, same, if_true, advanced, Option.bind_some] using truthful
            simpa only [Phase17Controller.replay, advanced, Option.bind_some] using ih next tail
      · simp [truthfulReplay, same] at truthful

theorem truthful_head (context : Phase17Provenance.Context) (evaluator : List Nat → Nat → Bool)
    (priorState final : Phase17Controller.Prefix) (observation : Phase17Controller.Observation)
    (rest : List Phase17Controller.Observation)
    (truthful : truthfulReplay context evaluator priorState (observation :: rest) = some final) :
    observation.passed = evaluator (Phase17Controller.seen priorState) observation.index := by
  by_contra different
  simp [truthfulReplay, different] at truthful

theorem forged_verdict_refused (context : Phase17Provenance.Context)
    (evaluator : List Nat → Nat → Bool) (priorState : Phase17Controller.Prefix)
    (observation : Phase17Controller.Observation) (rest : List Phase17Controller.Observation)
    (different : observation.passed ≠ evaluator (Phase17Controller.seen priorState) observation.index) :
    truthfulReplay context evaluator priorState (observation :: rest) = none := by
  simp [truthfulReplay, different]

theorem truthful_replay_invariant (context : Phase17Provenance.Context)
    (shape : Phase17Controller.ContextShape context) (evaluator : List Nat → Nat → Bool)
    (credits : Nat) (observations : List Phase17Controller.Observation)
    (final : Phase17Controller.Prefix)
    (truthful : truthfulReplay context evaluator (Phase17Controller.initial credits)
      observations = some final) : Phase17Controller.Invariant final :=
  Phase17Controller.replay_invariant context shape _ final observations
    (Phase17Controller.initial_invariant credits)
    (truthful_replay_projects context evaluator _ final observations truthful)

theorem truthful_exhaustion_covers (context : Phase17Provenance.Context)
    (shape : Phase17Controller.ContextShape context) (evaluator : List Nat → Nat → Bool)
    (credits : Nat) (observations : List Phase17Controller.Observation)
    (final : Phase17Controller.Prefix)
    (truthful : truthfulReplay context evaluator (Phase17Controller.initial credits)
      observations = some final)
    (exhausted : Phase17Controller.decision context final = some .searchExhausted) :
    (Phase17Controller.seen final).toFinset = Finset.range 32 :=
  Phase17Controller.exhaustion_covers_grammar context shape credits observations final
    (truthful_replay_projects context evaluator _ final observations truthful) exhausted

theorem truthful_terminal_cannot_continue (context : Phase17Provenance.Context)
    (evaluator : List Nat → Nat → Bool) (priorState : Phase17Controller.Prefix)
    (action : Phase17Controller.Action) (terminal : Phase17Controller.Terminal action)
    (stopped : Phase17Controller.decision context priorState = some action)
    (observation : Phase17Controller.Observation) (rest : List Phase17Controller.Observation) :
    truthfulReplay context evaluator priorState (observation :: rest) = none := by
  have no := Phase17Controller.terminal_cannot_advance context priorState action terminal stopped observation
  by_cases same : observation.passed = evaluator (Phase17Controller.seen priorState) observation.index
  · simp [truthfulReplay, same, no]
  · simp [truthfulReplay, same]

private theorem advance_last (context : Phase17Provenance.Context)
    (before after : Phase17Controller.Prefix) (observation : Phase17Controller.Observation)
    (step : Phase17Controller.advance context before observation = some after) :
    Phase17Controller.lastPassed after = observation.passed := by
  rcases Phase17Controller.advance_spec context before after observation step with ⟨_, _, _, rfl⟩
  simp [Phase17Controller.lastPassed]

private theorem replay_nonempty_requires_rejection (context : Phase17Provenance.Context)
    (before final : Phase17Controller.Prefix) (observation : Phase17Controller.Observation)
    (rest : List Phase17Controller.Observation)
    (run : Phase17Controller.replay context before (observation :: rest) = some final) :
    Phase17Controller.lastPassed before = false := by
  cases step : Phase17Controller.advance context before observation with
  | none => simp [Phase17Controller.replay, step] at run
  | some next =>
      obtain ⟨i, selected, _, _⟩ := Phase17Controller.advance_spec context before next observation step
      exact ((Phase17Controller.decision_evaluate_iff context before i).mp selected).2.1

private theorem replay_all_rejected (context : Phase17Provenance.Context)
    (before final : Phase17Controller.Prefix) (observations : List Phase17Controller.Observation)
    (run : Phase17Controller.replay context before observations = some final)
    (last : Phase17Controller.lastPassed final = false) :
    ∀ observation ∈ observations, observation.passed = false := by
  induction observations generalizing before with
  | nil => simp
  | cons observation rest ih =>
      cases step : Phase17Controller.advance context before observation with
      | none => simp [Phase17Controller.replay, step] at run
      | some next =>
          have tail : Phase17Controller.replay context next rest = some final := by
            simpa only [Phase17Controller.replay, step, Option.bind_some] using run
          have head : observation.passed = false := by
            have exactLast := advance_last context before next observation step
            cases rest with
            | nil =>
                have equal : next = final := by simpa only [Phase17Controller.replay, Option.some.injEq] using tail
                rw [equal] at exactLast
                exact exactLast.symm.trans last
            | cons x xs =>
                exact exactLast.symm.trans
                  (replay_nonempty_requires_rejection context next final x xs tail)
          intro item member
          rcases List.mem_cons.mp member with rfl | member
          · exact head
          · exact ih next tail item member

/-- Exhaustion contains 32 distinct actual inspections and every receipt is a
    rejection. Truth is at each recorded prefix; no history-independent verdict
    or existence claim for another source or grammar is inferred. -/
theorem truthful_exhaustion_rejections (context : Phase17Provenance.Context)
    (shape : Phase17Controller.ContextShape context) (evaluator : List Nat → Nat → Bool)
    (credits : Nat) (observations : List Phase17Controller.Observation)
    (final : Phase17Controller.Prefix)
    (truthful : truthfulReplay context evaluator (Phase17Controller.initial credits)
      observations = some final)
    (exhausted : Phase17Controller.decision context final = some .searchExhausted) :
    (Phase17Controller.seen final).toFinset = Finset.range 32 ∧
      ∀ observation ∈ observations, observation.passed = false := by
  have run := truthful_replay_projects context evaluator _ final observations truthful
  have openState : final.stop = none :=
    (Phase17Controller.replay_result context _ final observations run).2.2
  have rejected : Phase17Controller.lastPassed final = false := by
    cases result : Phase17Controller.lastPassed final with
    | false => rfl
    | true => simp [Phase17Controller.decision, openState, result] at exhausted
  exact ⟨truthful_exhaustion_covers context shape evaluator credits observations final truthful exhausted,
    replay_all_rejected context _ final observations run rejected⟩

structure Binding where
  source : String
  request : String
  package : String
  history : String
  context : String
  catalog : String
  evaluator : String
  deriving DecidableEq

structure Grant where
  binding : Binding
  candidateLimit : Nat
  referenceCandidateLimit : Nat
  vectorLimit : Nat
  inputLimit : Nat
  outputLimit : Nat
  costLimit : Nat
  deriving DecidableEq

def Grant.policy (grant : Grant) : Phase17Resource.Policy :=
  { limits := fun i => [grant.referenceCandidateLimit, grant.vectorLimit, grant.inputLimit,
      grant.outputLimit].getD i.val 0, costLimit := grant.costLimit }

/-- `expected` is retained outside the request. This validates finite scope and
    identity; external authorization of that expected grant remains a premise. -/
def Authorized (expected supplied : Grant) (source : Binding) : Prop :=
  supplied = expected ∧ supplied.binding = source ∧ supplied.candidateLimit ≤ 32

theorem grant_cannot_self_authorize (expected supplied : Grant) (source : Binding)
    (different : supplied ≠ expected) : ¬ Authorized expected supplied source := by
  intro authorized
  exact different authorized.1

theorem stale_grant_refused (expected supplied : Grant) (source : Binding)
    (stale : supplied.binding ≠ source) : ¬ Authorized expected supplied source := by
  intro authorized
  exact stale authorized.2.1

instance fitsDecidable (grant : Grant) (spent : List Phase17Resource.Kind) :
    Decidable (Phase17Resource.Fits grant.policy spent) := by
  unfold Phase17Resource.Fits
  infer_instance

def reserve (grant : Grant) (spent : List Phase17Resource.Kind) (kind : Phase17Resource.Kind) :
    Option (List Phase17Resource.Kind) :=
  if Phase17Resource.Fits grant.policy (spent ++ [kind]) then some (spent ++ [kind]) else none

theorem reservation_appends_exact_charge (grant : Grant) (spent next : List Phase17Resource.Kind)
    (kind : Phase17Resource.Kind) (reserved : reserve grant spent kind = some next) :
    next = spent ++ [kind] ∧ Phase17Resource.Fits grant.policy next := by
  unfold reserve at reserved
  split at reserved
  next fits => exact ⟨(Option.some.inj reserved).symm, (Option.some.inj reserved) ▸ fits⟩
  next no => cases reserved

theorem refused_reservation_no_charge (grant : Grant) (spent : List Phase17Resource.Kind)
    (kind : Phase17Resource.Kind)
    (exceeded : ¬ Phase17Resource.Fits grant.policy (spent ++ [kind])) :
    reserve grant spent kind = none := by simp [reserve, exceeded]

theorem granted_prefix_within_policy (grant : Grant) (priorState suffix : List Phase17Resource.Kind)
    (bounded : Phase17Resource.Fits grant.policy (priorState ++ suffix)) :
    Phase17Resource.Fits grant.policy priorState :=
  Phase17Resource.bounded_final_implies_bounded_prefix grant.policy priorState suffix bounded

theorem reserved_cost_not_refunded (grant : Grant) (spent next : List Phase17Resource.Kind)
    (kind : Phase17Resource.Kind) (reserved : reserve grant spent kind = some next) :
    Phase17Resource.totalCost spent ≤ Phase17Resource.totalCost next := by
  rw [(reservation_appends_exact_charge grant spent next kind reserved).1]
  exact Phase17Resource.appended_charge_not_refunded spent kind

/-- Reference work for one completed inspection: admission followed by the
    declared number of vector calls. Physical CPU, storage and preparation work
    are not inferred from this finite schedule. -/
def trialCharges (vectorCalls : Nat) : List Phase17Resource.Kind :=
  .candidate :: List.replicate vectorCalls .vector

def reserveTrial (grant : Grant) (spent : List Phase17Resource.Kind) (vectorCalls : Nat) :
    Option (List Phase17Resource.Kind) :=
  if Phase17Resource.Fits grant.policy (spent ++ trialCharges vectorCalls) then
    some (spent ++ trialCharges vectorCalls)
  else none

structure ExecutionState where
  controller : Phase17Controller.Prefix
  spent : List Phase17Resource.Kind
  deriving DecidableEq

def admissibleExecution (expected supplied : Grant) (source : Binding)
    (context : Phase17Provenance.Context) (state : ExecutionState) : Prop :=
  Authorized expected supplied source ∧ state.controller.initialCredits = supplied.candidateLimit ∧
    Phase17Resource.Fits supplied.policy state.spent ∧ source.context = context.contextHash ∧
    source.package = context.parentPackage ∧ source.history = context.transcriptHash ∧
    context.credits = supplied.candidateLimit

instance authorizedDecidable (expected supplied : Grant) (source : Binding) :
    Decidable (Authorized expected supplied source) := by
  unfold Authorized
  infer_instance

instance executionDecidable (expected supplied : Grant) (source : Binding)
    (context : Phase17Provenance.Context) (state : ExecutionState) :
    Decidable (admissibleExecution expected supplied source context state) := by
  unfold admissibleExecution
  infer_instance

/-- Reservation is a guard before a completed evaluator receipt can advance
    the controller. This is a finite protocol ordering theorem, not a claim that
    arbitrary physical callbacks execute with no other costs or side effects. -/
def authorizedStep (expected supplied : Grant) (source : Binding)
    (context : Phase17Provenance.Context) (evaluator : List Nat → Nat → Bool)
    (vectorCalls : Nat) (state : ExecutionState) (observation : Phase17Controller.Observation) :
    Option ExecutionState :=
  if admissibleExecution expected supplied source context state then
    (reserveTrial supplied state.spent vectorCalls).bind fun charged =>
      if observation.passed = evaluator (Phase17Controller.seen state.controller) observation.index then
        (Phase17Controller.advance context state.controller observation).map
          (fun next => ⟨next, charged⟩)
      else none
  else none

theorem unauthorized_step_refused (expected supplied : Grant) (source : Binding)
    (context : Phase17Provenance.Context) (evaluator : List Nat → Nat → Bool)
    (vectorCalls : Nat) (state : ExecutionState) (observation : Phase17Controller.Observation)
    (unauthorized : ¬ Authorized expected supplied source) :
    authorizedStep expected supplied source context evaluator vectorCalls state observation = none := by
  have no : ¬ admissibleExecution expected supplied source context state := fun h => unauthorized h.1
  simp [authorizedStep, no]

theorem retargeted_context_no_receipt (expected supplied : Grant) (source : Binding)
    (context : Phase17Provenance.Context) (evaluator : List Nat → Nat → Bool)
    (vectorCalls : Nat) (state : ExecutionState) (observation : Phase17Controller.Observation)
    (retargeted : source.context ≠ context.contextHash ∨ source.package ≠ context.parentPackage ∨
      source.history ≠ context.transcriptHash ∨ context.credits ≠ supplied.candidateLimit) :
    authorizedStep expected supplied source context evaluator vectorCalls state observation = none := by
  have no : ¬ admissibleExecution expected supplied source context state := by
    intro valid
    rcases retargeted with different | different | different | different
    · exact different valid.2.2.2.1
    · exact different valid.2.2.2.2.1
    · exact different valid.2.2.2.2.2.1
    · exact different valid.2.2.2.2.2.2
  simp [authorizedStep, no]

theorem insufficient_allowance_no_receipt (expected supplied : Grant) (source : Binding)
    (context : Phase17Provenance.Context) (evaluator : List Nat → Nat → Bool)
    (vectorCalls : Nat) (state : ExecutionState) (observation : Phase17Controller.Observation)
    (insufficient : ¬ Phase17Resource.Fits supplied.policy
      (state.spent ++ trialCharges vectorCalls)) :
    authorizedStep expected supplied source context evaluator vectorCalls state observation = none := by
  by_cases valid : admissibleExecution expected supplied source context state
  · simp [authorizedStep, valid, reserveTrial, insufficient]
  · simp [authorizedStep, valid]

theorem authorized_step_spec (expected supplied : Grant) (source : Binding)
    (context : Phase17Provenance.Context) (evaluator : List Nat → Nat → Bool)
    (vectorCalls : Nat) (state next : ExecutionState) (observation : Phase17Controller.Observation)
    (stepped : authorizedStep expected supplied source context evaluator vectorCalls state observation =
      some next) :
    admissibleExecution expected supplied source context state ∧
      next.spent = state.spent ++ trialCharges vectorCalls ∧
      Phase17Resource.Fits supplied.policy next.spent ∧
      observation.passed = evaluator (Phase17Controller.seen state.controller) observation.index ∧
      Phase17Controller.advance context state.controller observation = some next.controller := by
  unfold authorizedStep at stepped
  split at stepped
  next valid =>
    by_cases fits : Phase17Resource.Fits supplied.policy (state.spent ++ trialCharges vectorCalls)
    · simp only [reserveTrial, fits, if_true, Option.bind_some] at stepped
      split at stepped
      next truthful =>
        cases advanced : Phase17Controller.advance context state.controller observation with
        | none => simp [advanced] at stepped
        | some following =>
            have eq : (⟨following, state.spent ++ trialCharges vectorCalls⟩ : ExecutionState) = next := by
              simpa only [advanced, Option.map_some, Option.some.injEq] using stepped
            subst next
            exact ⟨valid, rfl, fits, truthful, rfl⟩
      next different => cases stepped
    · simp [reserveTrial, fits] at stepped
  next invalid => cases stepped

theorem authorized_step_construct (expected supplied : Grant) (source : Binding)
    (context : Phase17Provenance.Context) (evaluator : List Nat → Nat → Bool)
    (vectorCalls : Nat) (state : ExecutionState) (next : Phase17Controller.Prefix)
    (observation : Phase17Controller.Observation)
    (valid : admissibleExecution expected supplied source context state)
    (fits : Phase17Resource.Fits supplied.policy (state.spent ++ trialCharges vectorCalls))
    (truthful : observation.passed = evaluator (Phase17Controller.seen state.controller) observation.index)
    (advanced : Phase17Controller.advance context state.controller observation = some next) :
    authorizedStep expected supplied source context evaluator vectorCalls state observation =
      some ⟨next, state.spent ++ trialCharges vectorCalls⟩ := by
  simp only [authorizedStep, valid, if_true, reserveTrial, fits, Option.bind_some,
    truthful, advanced, Option.map_some]

def authorizedReplay (expected supplied : Grant) (source : Binding)
    (context : Phase17Provenance.Context) (evaluator : List Nat → Nat → Bool)
    (vectorCalls : Nat) (state : ExecutionState) : List Phase17Controller.Observation → Option ExecutionState
  | [] => if admissibleExecution expected supplied source context state then some state else none
  | observation :: rest =>
      (authorizedStep expected supplied source context evaluator vectorCalls state observation).bind
        (fun next => authorizedReplay expected supplied source context evaluator vectorCalls next rest)

theorem authorized_replay_projects (expected supplied : Grant) (source : Binding)
    (context : Phase17Provenance.Context) (evaluator : List Nat → Nat → Bool)
    (vectorCalls : Nat) (state final : ExecutionState) (observations : List Phase17Controller.Observation)
    (run : authorizedReplay expected supplied source context evaluator vectorCalls state observations =
      some final) : truthfulReplay context evaluator state.controller observations = some final.controller := by
  induction observations generalizing state with
  | nil =>
      by_cases valid : admissibleExecution expected supplied source context state
      · have eq : state = final := by simpa [authorizedReplay, valid] using run
        simpa [truthfulReplay] using congrArg (fun s => some s.controller) eq
      · simp [authorizedReplay, valid] at run
  | cons observation rest ih =>
      cases step : authorizedStep expected supplied source context evaluator vectorCalls state observation with
      | none => simp [authorizedReplay, step] at run
      | some next =>
          have tail : authorizedReplay expected supplied source context evaluator vectorCalls next rest =
              some final := by simpa only [authorizedReplay, step, Option.bind_some] using run
          have facts := authorized_step_spec expected supplied source context evaluator vectorCalls
            state next observation step
          simpa only [truthfulReplay, facts.2.2.2.1, if_true, facts.2.2.2.2, Option.bind_some] using ih next tail

theorem authorized_replay_within_policy (expected supplied : Grant) (source : Binding)
    (context : Phase17Provenance.Context) (evaluator : List Nat → Nat → Bool)
    (vectorCalls : Nat) (state final : ExecutionState) (observations : List Phase17Controller.Observation)
    (run : authorizedReplay expected supplied source context evaluator vectorCalls state observations =
      some final) : Authorized expected supplied source ∧ Phase17Resource.Fits supplied.policy final.spent := by
  induction observations generalizing state with
  | nil =>
      by_cases valid : admissibleExecution expected supplied source context state
      · have eq : state = final := by simpa [authorizedReplay, valid] using run
        subst final
        exact ⟨valid.1, valid.2.2.1⟩
      · simp [authorizedReplay, valid] at run
  | cons observation rest ih =>
      cases step : authorizedStep expected supplied source context evaluator vectorCalls state observation with
      | none => simp [authorizedReplay, step] at run
      | some next =>
          exact ih next (by simpa only [authorizedReplay, step, Option.bind_some] using run)

def traceCharges (vectorCalls : Nat) (observations : List Phase17Controller.Observation) :
    List Phase17Resource.Kind := observations.flatMap (fun _ => trialCharges vectorCalls)

theorem authorized_replay_exact_charges (expected supplied : Grant) (source : Binding)
    (context : Phase17Provenance.Context) (evaluator : List Nat → Nat → Bool)
    (vectorCalls : Nat) (state final : ExecutionState) (observations : List Phase17Controller.Observation)
    (run : authorizedReplay expected supplied source context evaluator vectorCalls state observations =
      some final) : final.spent = state.spent ++ traceCharges vectorCalls observations := by
  induction observations generalizing state with
  | nil =>
      by_cases valid : admissibleExecution expected supplied source context state
      · have eq : state = final := by simpa [authorizedReplay, valid] using run
        subst final
        simp [traceCharges]
      · simp [authorizedReplay, valid] at run
  | cons observation rest ih =>
      cases step : authorizedStep expected supplied source context evaluator vectorCalls state observation with
      | none => simp [authorizedReplay, step] at run
      | some next =>
          have tail : authorizedReplay expected supplied source context evaluator vectorCalls next rest =
              some final := by simpa only [authorizedReplay, step, Option.bind_some] using run
          have charges := (authorized_step_spec expected supplied source context evaluator vectorCalls
            state next observation step).2.1
          simpa [traceCharges, charges, List.append_assoc] using ih next tail

theorem authorized_evaluated_acceptance (fixed : Phase17Finite.Configuration)
    (contexts : Contexts) (charges : ChargesAt) (complete : CatalogComplete fixed)
    (s : State) (domain : Domain) (build : Builder) (expected supplied : Grant)
    (source : Binding) (vectorCalls : Nat) (state next : ExecutionState)
    (observation : Phase17Controller.Observation)
    (stepped : authorizedStep expected supplied source domain.context
      (evaluate fixed contexts charges s domain build) vectorCalls state observation = some next)
    (passed : observation.passed = true) :
    Authorized expected supplied source ∧ source.package = s.packageHash ∧
      ∃ task, OfferBound fixed s domain observation.index task
          (build (Phase17Controller.seen state.controller) observation.index task) ∧
        Accepted fixed contexts (charges (Phase17Controller.seen state.controller) observation.index)
          s (build (Phase17Controller.seen state.controller) observation.index task) := by
  have facts := authorized_step_spec expected supplied source domain.context
    (evaluate fixed contexts charges s domain build) vectorCalls state next observation stepped
  have checked : evaluate fixed contexts charges s domain build
      (Phase17Controller.seen state.controller) observation.index = true :=
    facts.2.2.2.1.symm.trans passed
  obtain ⟨task, _, requestBound, offerBound, accepted⟩ :=
    evaluation_acceptance fixed contexts charges complete s domain build
      (Phase17Controller.seen state.controller) observation.index checked
  exact ⟨facts.1.1, facts.1.2.2.2.2.1.trans requestBound.2.1, task, offerBound, accepted⟩

/-- The explicit correspondence premise connects AG's transaction charges to
    the work actually reserved by this source-specific protocol step. Selected
    certificates prove it from the cumulative schedule; an arbitrary provider
    is not silently identified with the reservation journal. -/
theorem authorized_accepted_exact_charges (fixed : Phase17Finite.Configuration)
    (contexts : Contexts) (charges : ChargesAt) (complete : CatalogComplete fixed)
    (s : State) (domain : Domain) (build : Builder) (expected supplied : Grant)
    (source : Binding) (vectorCalls : Nat) (state next : ExecutionState)
    (observation : Phase17Controller.Observation)
    (stepped : authorizedStep expected supplied source domain.context
      (evaluate fixed contexts charges s domain build) vectorCalls state observation = some next)
    (passed : observation.passed = true)
    (chargeBinding : (charges (Phase17Controller.seen state.controller) observation.index) s =
      state.spent ++ trialCharges vectorCalls) :
    ∃ task, OfferBound fixed s domain observation.index task
        (build (Phase17Controller.seen state.controller) observation.index task) ∧
      Accepted fixed contexts (charges (Phase17Controller.seen state.controller) observation.index)
        s (build (Phase17Controller.seen state.controller) observation.index task) ∧
      (build (Phase17Controller.seen state.controller) observation.index task).evidence.charges = next.spent ∧
      (build (Phase17Controller.seen state.controller) observation.index task).update.charges = next.spent := by
  have stepFacts := authorized_step_spec expected supplied source domain.context
    (evaluate fixed contexts charges s domain build) vectorCalls state next observation stepped
  obtain ⟨_, _, task, bound, accepted⟩ := authorized_evaluated_acceptance fixed contexts charges
    complete s domain build expected supplied source vectorCalls state next observation stepped passed
  let offered := build (Phase17Controller.seen state.controller) observation.index task
  have resources : offered.evidence.charges = offered.update.charges ∧
      offered.evidence.charges = (charges (Phase17Controller.seen state.controller) observation.index) s ∧
      Phase17Resource.Fits fixed.policy offered.evidence.charges :=
    accepted.baseObligations.resourceValid
  have exactSpend : offered.evidence.charges = next.spent :=
    resources.2.1.trans (chargeBinding.trans stepFacts.2.1.symm)
  exact ⟨task, bound, accepted, exactSpend, resources.1.symm.trans exactSpend⟩

end Phase17ProducerDomain

namespace Phase17ProducerDomainExamples
open RcpRclmFormalCoreV2 RcpRclmFormalCoreV3
open Phase17TaskInterpretation Phase17TruthfulSuccessor Phase17ProducerDomain
set_option maxRecDepth 32768
set_option maxHeartbeats 16000000

def fixed : Phase17Finite.Configuration := Phase17SecondStep.fixed
def source0 : State := Phase17SecondStep.observedBefore
def source1 : State := Phase17SecondStep.observedAfter

theorem retained_source_chain : source0 = Phase17Finite.selectedAfter ∧
    source1 = Phase17SecondStep.secondCandidate.next :=
  ⟨Phase17SecondStep.second_before_matches, rfl⟩

def cumulativeCharges (prior : List Nat) : List Phase17Resource.Kind :=
  (List.replicate (prior.length + 1) (trialCharges 2)).flatten

def chargesAt (prior : List Nat) (_index : Nat) (_source : State) : List Phase17Resource.Kind :=
  cumulativeCharges prior
-- Complete AH input packet SHA256: 55d3b9cdc9bf37629fa7c8e7a3d2e821410992703c1038aa30ab9a9cd300dafe
def context0 : Phase17Provenance.Context := {
  generator := "90391521aefb1f2daec066d84da943c307f9eab85fae2296107b9b13afb3b3a1"
  parentPackage := "b4036b3e31a6608e30b421c08906b1e58c3e7d61fef6eb6730881c597656434e"
  contextHash := "5a7d2d5c7015e588902b33385ca9e7e4c679346c74faa51cc8415944bf4fecc2"
  transcriptHash := "f0fdfc3264fded4f92ea01a33e37f232fbfafd9ec72ebad58c6517eb86c9eb1f"
  credits := 32
  offset := 15
  rows := [{ key := "07882cf428b45d8397698adabb728a847bbf96b0e3c6926d3f1d4d4088f9d72e", family := 6, baseScore := 18960, ties := [4067414476079179602, 1143632732032864453, 16861598504112071679, 15384015252139269389, 18310767783104935697] }, { key := "079464d9ed285120d4387203f867a81e2dc97fe24ac634cf7ba700ce52d468a4", family := 2, baseScore := 19470, ties := [13482613594219277050, 5469217485581563474, 10257095991479891409, 11151343383861201678, 6906722214430827221] }, { key := "0d313e2585c77f2d844d93fcbbf8e74c7422e6544804620d11e68ce2645d500b", family := 4, baseScore := 19508, ties := [13612602070832589573, 6136353106604528740, 4022276120731408208, 12508910830223200717, 1574879216556344613] }, { key := "12a42ce65856dd02f802c8029f2daf19578cd8bfbeddfe37e29997cde1b62ac8", family := 7, baseScore := 19496, ties := [18123742346597796565, 15121617768547652000, 9661723255900939993, 17347352500181138570, 9764312206222838187] }, { key := "1306284a64e0735108c79ea5b4f8e54070732f4e2401dd8b493be69169e7d5e9", family := 5, baseScore := 19472, ties := [10095354839296612401, 8343001766639313493, 6876812003579993481, 3289013143446074041, 6972954723787526484] }, { key := "22ff5f6188a0ba1bcacd416080df083ced5f1a9bff3e543769bd3389b6f167d9", family := 5, baseScore := 19507, ties := [9556741496105481830, 6521138168365943428, 1258425305099817531, 4549872774356196954, 4291925470698513438] }, { key := "27ed4335d4ad263283fd2219e3a1a351664a138191c78661dbe48445a82ed69e", family := 6, baseScore := 18944, ties := [6105405153937009509, 11969193772550575404, 2107889702351671880, 17584414889085524363, 18211847158849932671] }, { key := "3020a4a7bd86574b5692bd42e9077c2b79ede2b188e4cb0169ad8930ae8d10de", family := 7, baseScore := 19472, ties := [12674795809107633111, 8735109151167820480, 14124372684497732999, 349763004355627024, 3862256201561958792] }, { key := "450dfe81045365620206674af70ae6ec90c0c4fa8ec3a4f502f05bc9add7e52b", family := 3, baseScore := 19456, ties := [5370746308605319879, 6164419903216892597, 3508704870563999890, 489383493529843381, 4653336060926829210] }, { key := "4e1ab17b7adc4c2677d527190317442f8a1ed0cfdd07a52a061995480dfc3f60", family := 6, baseScore := 18957, ties := [8893161776254545735, 1891202225067676371, 8053596535700481150, 11571226399141116229, 7141746405652483532] }, { key := "50f6bd6b08806bf9b8df6945e3d7e9adfffbff2a22961008915cfe959f0a6c4a", family := 7, baseScore := 19499, ties := [9679313212414016952, 9089937520646898793, 12306276790941400625, 16390441772389930777, 18111387248499519432] }, { key := "5c48f5d5dbc7d5139f0e40836f503591aa7c3071642889e31c0aacd9efe91b73", family := 5, baseScore := 19477, ties := [1686630956470550365, 12348276636288601349, 7265205885161631248, 18323645672495100349, 9229631209322088685] }, { key := "641a0a443c3ecdf7694f6f2564baaac751dde5ff9232538110d03c5de6583ee8", family := 4, baseScore := 19461, ties := [11232546787352037718, 7537786374361850087, 12719215349116130922, 11365499214359821264, 10243774792397307870] }, { key := "653ba4de5e0906ed5243fb78736da3abd4aa77383140d24a146680f31ec09990", family := 1, baseScore := 19462, ties := [9760102627151895911, 4269376462830578271, 18168365562687126899, 3792784763376343727, 6995317989452125285] }, { key := "6ee86ea419985236275b631dacc0290507fff0e068190c6a3728674baaa1a98b", family := 2, baseScore := 19501, ties := [11802090995992626256, 8791636913409424657, 11924440666518944324, 12132760461712722275, 17301751405184835073] }, { key := "720a201348d162d103690550d5350535aaab543c183ed82b5defc90858adf40e", family := 4, baseScore := 19479, ties := [6612759970106008385, 13514820826156495252, 9190821328972898399, 18362970414329912214, 5722062530679313706] }, { key := "77727c49241dd038565749ba479fb19152d512b554ae590dd7c7ccc4c62b3828", family := 3, baseScore := 19481, ties := [11926746517751336661, 14541035729376544619, 12208184956818782405, 5512244166577998159, 7334111558886353376] }, { key := "81829dac0cb4609c35cd5e305ca88afdc7b7156566adbee4baac888b7b9d28e4", family := 0, baseScore := 19464, ties := [16518332695240133985, 568756587103267924, 17795617196010485594, 2607642015827511779, 17156279897057633711] }, { key := "87a0db958fe5c35c6ec49a670f961e0046fee892ec1793f1631472aecb4d769e", family := 2, baseScore := 19453, ties := [5901464650357490299, 5579327280384594495, 253034272031291111, 17104554580747672489, 12425396319390355629] }, { key := "8b9157eb7084166b6636e5d7bb57efa71cd929f09c3f2f8414ef0122fe8e6577", family := 1, baseScore := 19468, ties := [3506042129886810465, 9214908235753750225, 15725083257317116685, 14781502037922715866, 1677427951469179458] }, { key := "8e01c54efa55b98f3428eb3a12c6182bc96551e16ec14689bd538abc3708255c", family := 1, baseScore := 19501, ties := [1879747030503297813, 4231031703955250555, 17600132949162241598, 1333975721071733513, 7648874207536453584] }, { key := "9ba71bd7d621c2d02b13d9742ff9ec52bd1e1c97f48652cd1f5aec0b314ca36b", family := 1, baseScore := 19505, ties := [7975309339964375512, 6550324127271030517, 10476331802804152171, 5119642984881144404, 10217516072512059925] }, { key := "a403651a9e50607d7ca9601b212a6ad9c528b8888a314b3828667da158592d48", family := 5, baseScore := 19464, ties := [18202378182033565274, 7075035538533698310, 8365198709351112436, 15877617147546882527, 2314023604113503548] }, { key := "a6ae460c5df16a8d6c208e4dcbdeb4e3b37954b0796c459017e94f0e66b9efc8", family := 6, baseScore := 18998, ties := [7987115727688652744, 15487032685309554364, 8955788139047961274, 4889142308567352162, 2670098398921227938] }, { key := "b01857227df43043988ff2d7fb601ff629a8d71c340d84bcb09c750fc9b2fc49", family := 0, baseScore := 19481, ties := [8607332645611834342, 10531034799799481139, 12160336227489894607, 5096808467431222401, 6770608227068374516] }, { key := "b72f4059d60d2d4a5afdb76ad62defc3f62d4fe96db51c457750cae5abd377d9", family := 2, baseScore := 19466, ties := [6669701029395109215, 5856957169175542674, 1487578234978173705, 17790081782434534677, 5413377251973930479] }, { key := "b81a18b500c7ca818a616e63196cc3addd2145ec980e1d91aad9a1ca062db182", family := 4, baseScore := 19457, ties := [10586155769928991059, 5241797536902138588, 16423289231373946654, 142738471961533350, 14854837108458276609] }, { key := "b9b957bc4120f3c6b154a89750163c9416ab8e8cc3c7f1b79ec58897993d585e", family := 7, baseScore := 19460, ties := [1095656587249731324, 14290496605635945461, 14234615779449105149, 12457199882864015916, 1490997132813081410] }, { key := "be392ca3fddd70b2d0f02bc0baf2d4fec4ee3c425ecd06d634e5574ce7fa2518", family := 3, baseScore := 19450, ties := [17299591439524412511, 13939404801979848755, 13414325344623980203, 4586071826011419681, 9331775315561780333] }, { key := "c5a6780c1de5bdd5fa049ede1d7f2deb98235e648266a02d91af32ce97ade1aa", family := 3, baseScore := 19504, ties := [5671031807740714614, 5438000299292591274, 801492386737468072, 5637620230803865938, 11012347029589691182] }, { key := "c7e8b8e3c29edc92452562acebcfc5c9574a2f7e94d07d7ef3f4068f4010f823", family := 0, baseScore := 19541, ties := [3513290731377645443, 14365763167848964155, 14096591963623069607, 16289509393212528963, 2079474529533731873] }, { key := "e3c13e868433bc76a733a0a6119c7f4f5c755a95b02b6d671095ec1739566c52", family := 0, baseScore := 19501, ties := [1423082885769156603, 7092168848720255596, 258275870616071943, 1926726872688281918, 6275646520615301522] }] }
def domain0 : Domain := ⟨context0, [("07882cf428b45d8397698adabb728a847bbf96b0e3c6926d3f1d4d4088f9d72e", { family := 6, variant := 3, a := (-12), b := (-11) }), ("079464d9ed285120d4387203f867a81e2dc97fe24ac634cf7ba700ce52d468a4", { family := 2, variant := 1, a := 12, b := 9 }), ("0d313e2585c77f2d844d93fcbbf8e74c7422e6544804620d11e68ce2645d500b", { family := 4, variant := 1, a := 12, b := 13 }), ("12a42ce65856dd02f802c8029f2daf19578cd8bfbeddfe37e29997cde1b62ac8", { family := 7, variant := 3, a := (-14), b := 12 }), ("1306284a64e0735108c79ea5b4f8e54070732f4e2401dd8b493be69169e7d5e9", { family := 5, variant := 0, a := 7, b := 7 }), ("22ff5f6188a0ba1bcacd416080df083ced5f1a9bff3e543769bd3389b6f167d9", { family := 5, variant := 2, a := (-8), b := 13 }), ("27ed4335d4ad263283fd2219e3a1a351664a138191c78661dbe48445a82ed69e", { family := 6, variant := 0, a := (-6), b := (-12) }), ("3020a4a7bd86574b5692bd42e9077c2b79ede2b188e4cb0169ad8930ae8d10de", { family := 7, variant := 1, a := (-6), b := 9 }), ("450dfe81045365620206674af70ae6ec90c0c4fa8ec3a4f502f05bc9add7e52b", { family := 3, variant := 1, a := 3, b := (-5) }), ("4e1ab17b7adc4c2677d527190317442f8a1ed0cfdd07a52a061995480dfc3f60", { family := 6, variant := 2, a := (-12), b := 3 }), ("50f6bd6b08806bf9b8df6945e3d7e9adfffbff2a22961008915cfe959f0a6c4a", { family := 7, variant := 2, a := 11, b := 1 }), ("5c48f5d5dbc7d5139f0e40836f503591aa7c3071642889e31c0aacd9efe91b73", { family := 5, variant := 3, a := 7, b := 16 }), ("641a0a443c3ecdf7694f6f2564baaac751dde5ff9232538110d03c5de6583ee8", { family := 4, variant := 3, a := 0, b := 8 }), ("653ba4de5e0906ed5243fb78736da3abd4aa77383140d24a146680f31ec09990", { family := 1, variant := 0, a := (-16), b := (-4) }), ("6ee86ea419985236275b631dacc0290507fff0e068190c6a3728674baaa1a98b", { family := 2, variant := 0, a := (-3), b := 10 }), ("720a201348d162d103690550d5350535aaab543c183ed82b5defc90858adf40e", { family := 4, variant := 0, a := 9, b := (-1) }), ("77727c49241dd038565749ba479fb19152d512b554ae590dd7c7ccc4c62b3828", { family := 3, variant := 0, a := 3, b := (-10) }), ("81829dac0cb4609c35cd5e305ca88afdc7b7156566adbee4baac888b7b9d28e4", { family := 0, variant := 2, a := (-1), b := (-12) }), ("87a0db958fe5c35c6ec49a670f961e0046fee892ec1793f1631472aecb4d769e", { family := 2, variant := 2, a := 10, b := 8 }), ("8b9157eb7084166b6636e5d7bb57efa71cd929f09c3f2f8414ef0122fe8e6577", { family := 1, variant := 3, a := (-7), b := 3 }), ("8e01c54efa55b98f3428eb3a12c6182bc96551e16ec14689bd538abc3708255c", { family := 1, variant := 1, a := 0, b := (-16) }), ("9ba71bd7d621c2d02b13d9742ff9ec52bd1e1c97f48652cd1f5aec0b314ca36b", { family := 1, variant := 2, a := (-8), b := 2 }), ("a403651a9e50607d7ca9601b212a6ad9c528b8888a314b3828667da158592d48", { family := 5, variant := 1, a := (-7), b := (-4) }), ("a6ae460c5df16a8d6c208e4dcbdeb4e3b37954b0796c459017e94f0e66b9efc8", { family := 6, variant := 1, a := (-16), b := 6 }), ("b01857227df43043988ff2d7fb601ff629a8d71c340d84bcb09c750fc9b2fc49", { family := 0, variant := 3, a := 1, b := (-4) }), ("b72f4059d60d2d4a5afdb76ad62defc3f62d4fe96db51c457750cae5abd377d9", { family := 2, variant := 3, a := (-1), b := (-3) }), ("b81a18b500c7ca818a616e63196cc3addd2145ec980e1d91aad9a1ca062db182", { family := 4, variant := 2, a := 14, b := (-5) }), ("b9b957bc4120f3c6b154a89750163c9416ab8e8cc3c7f1b79ec58897993d585e", { family := 7, variant := 0, a := (-4), b := 10 }), ("be392ca3fddd70b2d0f02bc0baf2d4fec4ee3c425ecd06d634e5574ce7fa2518", { family := 3, variant := 2, a := 16, b := 16 }), ("c5a6780c1de5bdd5fa049ede1d7f2deb98235e648266a02d91af32ce97ade1aa", { family := 3, variant := 3, a := (-1), b := 13 }), ("c7e8b8e3c29edc92452562acebcfc5c9574a2f7e94d07d7ef3f4068f4010f823", { family := 0, variant := 0, a := (-6), b := 7 }), ("e3c13e868433bc76a733a0a6119c7f4f5c755a95b02b6d671095ec1739566c52", { family := 0, variant := 1, a := 2, b := 7 })]⟩
def contexts0 (_source : State) : Phase17Provenance.Context := context0
-- Identity table is a finite constructor association, not an evaluator history.
def identities0 : List String := ["", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "e9575b945911df8cda99d65d083746b9ed29e2f42562d089a233036d84761589", "", "", "", "", "", "", "9e4d2f7a168929ce0077ef0d1297ee98e2e8fd3c2378aba735a7a570a93b0453", "", "", "", "", "", "fd805716b3499ddf0605e098501fd3a23aaa5c2611d61d999d3644e6a847feb7", "d4b73e2795a27e4d8f4a48dbc40c6868e29891b4921d75a0633f06b1bd84556d"]
def builder0 (prior : List Nat) (index task : Nat) : Offer :=
  constructOffer fixed source0 domain0 (identities0.getD index "")
    prior index task (cumulativeCharges prior)
def evaluator0 : List Nat → Nat → Bool :=
  evaluate fixed contexts0 chargesAt source0 domain0 builder0
def grant0 : Grant := {
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
theorem domain_bound0 : DomainBound source0 domain0 := by
  refine ⟨rfl, ?_, rfl, rfl, ?_, ?_⟩
  · exact Phase17SecondStep.second_context_valid
  · intro index
    fin_cases index <;> decide +kernel
  · intro family variant
    fin_cases family <;> fin_cases variant
    · exact ⟨⟨30, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨31, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨17, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨24, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨13, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨20, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨21, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨19, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨14, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨1, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨18, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨25, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨16, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨8, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨28, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨29, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨15, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨2, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨26, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨12, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨4, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨22, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨5, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨11, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨6, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨23, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨9, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨0, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨27, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨7, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨10, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨3, by decide⟩, rfl, rfl⟩
def observations0 : List Phase17Controller.Observation := [⟨30, true⟩]
def state0_0 : ExecutionState :=
  ⟨⟨32, [], none⟩, []⟩
def state0_1 : ExecutionState :=
  ⟨⟨32, [⟨30, true⟩], none⟩, [.candidate, .vector, .vector]⟩
theorem choice0_0 : canonicalTask fixed source0 (Phase17Provenance.rowAt context0 30).key (rowProgram domain0 30) = some 41 := by decide +kernel
theorem check0_0 : check fixed contexts0 (chargesAt [] 30) source0 (builder0 [] 30 41) = true := by decide +kernel
theorem evaluation0_0 : evaluator0 [] 30 = true := by
  have requestBound : RequestBound contexts0 source0 domain0 := ⟨rfl, domain_bound0⟩
  have offerBound : OfferBound fixed source0 domain0 30 41 (builder0 [] 30 41) :=
    constructed_offer_bound fixed source0 domain0 _ [] 30 41 _ (by decide) choice0_0
  exact evaluation_of_checked fixed contexts0 chargesAt source0 domain0 builder0 [] 30 41
    choice0_0 requestBound offerBound check0_0
theorem step0_0 : authorizedStep grant0 grant0 grant0.binding
    context0 evaluator0 2 state0_0 ⟨30, true⟩ = some state0_1 := by
  apply authorized_step_construct
  · decide +kernel
  · decide +kernel
  · exact (evaluation0_0).symm
  · decide +kernel
theorem case_first_source : authorizedReplay grant0 grant0 grant0.binding
    context0 evaluator0 2 state0_0 observations0 = some state0_1 := by
  have finalAllowed : admissibleExecution grant0 grant0 grant0.binding context0 state0_1 := by decide +kernel
  simp only [observations0, authorizedReplay, step0_0, Option.bind_some, finalAllowed, if_true]
theorem terminal0 : Phase17Controller.decision context0 state0_1.controller = some .awaitRoot := by decide +kernel
def context1 : Phase17Provenance.Context := {
  generator := "d78909d7d6d01024fccd0389f7556b45cef14ce229a846d2e4b24d242bd5e6ca"
  parentPackage := "85bebb429b27104ee1d8ffabda71acd26c44847c2dd097dea249fa3ee5d4ae02"
  contextHash := "d0a6812be0e1d9799be1069336fae7002bb0cdfe907f9ee48c76f3cbccc480b5"
  transcriptHash := "572ec7c9c7a2eae68502fad30cfff120cfff90a438fe7047722a656799977695"
  credits := 32
  offset := 13
  rows := [{ key := "00249ca0b7a67c15459a63436150df40b37e902ef4c8e982e96771b088efd180", family := 0, baseScore := 18979, ties := [4553607917419594186, 15630213348677571363, 6491470184965233070, 12975236029994362483, 9199608038457457419] }, { key := "0285dff171e0f02e9b860d18f00b95b44877bf7a3c73b9c5391421fd99bd0867", family := 7, baseScore := 19470, ties := [1235608626286219260, 14589305888208094634, 6012042459752446848, 1401537048990591301, 12548572882181379052] }, { key := "06116e73fb137a69f4207ea8915ca755b626c24078922db00e07e5b645eb365c", family := 1, baseScore := 19500, ties := [14779831714415871226, 14561845555793468901, 2597147493736101661, 10153577625387614155, 6316066677961894881] }, { key := "0aba9c83eefc68880e4a6b53c51c1761b9e77dbf7bb19f640b4ad3a5b8f2d2ea", family := 6, baseScore := 18961, ties := [6626467606468221162, 10377777079204700371, 4244831773562338702, 13838918378892720663, 17244208607420248773] }, { key := "0cc4d094b87b5f39cc487ac5f4a724ed40998e7f5dfc4745526a09cddd41d53a", family := 2, baseScore := 19465, ties := [6964417313513196287, 1937854464768571333, 6117199747458864962, 5629045087522162107, 16090330734450513172] }, { key := "16af37fa62383c0cb646c247cb5d9fc0535852285252c33b84d8f40bc552344b", family := 3, baseScore := 19484, ties := [18320742210603957192, 13685684753086744671, 12460789157455486836, 2606637140937366133, 1819276498982317089] }, { key := "1a4227ba1f0a966a22e16bded3af275f2c271d890155c3bd51fc64f197fc3844", family := 0, baseScore := 18938, ties := [6641821706485704339, 13302170244109756866, 11418188377995284119, 12841108583499365900, 12866350796943133768] }, { key := "2272ec8df233ce2e4d34665f06c6f1a7dd64bfdeb8e3ac274f09ffe23804593e", family := 4, baseScore := 19456, ties := [17440073036088024076, 17850800124352804877, 9277323740050615842, 9771922068205556620, 17192901834255228013] }, { key := "2e8e78477230e75ccb5c319cf0b76de4d530b01e82ea6a3c18630abecddc5fff", family := 4, baseScore := 19481, ties := [18285665064460180787, 5660530768491281904, 11379962485541547881, 10809849345758430066, 11587677409377468715] }, { key := "33553591c35e07d8788165246c638307b37b0f522837f5d192778524efbcb6d1", family := 1, baseScore := 19480, ties := [17861271631964304855, 8122504493604679585, 18314044924554156242, 7498463703266124334, 3391635388111775017] }, { key := "3f36bf49ab6cc0ad7edb2a54b22609ce4d9b6d65439f5049762c6289ba52e210", family := 4, baseScore := 19505, ties := [16635933426665611828, 6858093571604301732, 5732091328645710249, 7822549142922163405, 18314702954586983950] }, { key := "41091e0d83d3ca41d10190bc538d303e511a79113c9df9f3edb400e5d7f06806", family := 2, baseScore := 19509, ties := [8911718324786314464, 7812307280058208589, 5167504732806915598, 11449473658666200729, 17221710378744447916] }, { key := "4cfe5f09bcf72872500b1c0604c0e7bceb63f387d74396856c238cab79ccd982", family := 1, baseScore := 19505, ties := [17341774770462319288, 4313188716980430563, 15744894512023544329, 7579211954982347478, 7723141427290801174] }, { key := "57a3367bb9ed42229a83b27586a131a0ba39c68ae2616d7865183b11394fa202", family := 6, baseScore := 18971, ties := [17823677709858021513, 8898656616282283843, 8291955824474563455, 16887769684259994195, 13355909568892680471] }, { key := "5de02c4fe1758e7198e688b25fbbdf2e2653921e3626f0ccbe8b24a3be35c478", family := 1, baseScore := 19509, ties := [14807191708322662213, 17044965354008738285, 18443313728954636047, 10243819765663942441, 3620524776556645995] }, { key := "6dd4b508318bd1750e02227959102f95ccc3e6dcedaca4e3a1b4cece77e0b1ba", family := 6, baseScore := 18963, ties := [4611825008557849227, 12068062198346940845, 9264110086434342255, 11730042552289615760, 17606951110930597123] }, { key := "73d333c33a7c893ef65b0e5fe74093bef5bb51e9c4dcfa47938d7055446fe726", family := 5, baseScore := 19495, ties := [11482589328235147740, 1068453299199746736, 5378424396541192917, 15634196418256437704, 4956110018302537069] }, { key := "7e2bc001d065c188a53be853a0f851fdd13c0f2de4beaf7edf74b99295a21153", family := 7, baseScore := 19446, ties := [7269785910583463666, 5034351993244807247, 4796688542921649101, 8497389830871718492, 3107514905629775783] }, { key := "9151999095e5e261489d580791558f6a716a55ad5515286f1857837d57670554", family := 3, baseScore := 19467, ties := [16278487536480062638, 7069003754947579151, 3365949586702625898, 7167415787254846713, 7074187969969243679] }, { key := "964de7415dc5e4e47c6fdca408a553f6c1d9364360dc1b24c0ea8477c97d2477", family := 3, baseScore := 19536, ties := [14893870574831223063, 17082743386262297389, 12883058327497221215, 10034842100876355881, 4285547786177124656] }, { key := "965372954524542df02c4e6d3edc0b7c5068bd73c2a511dfd2b633b08eac55ce", family := 2, baseScore := 19460, ties := [10602356374792532036, 14633862890172536179, 7996815289223726113, 4714145402830052898, 11799739847749970126] }, { key := "99b406f5b59529ffae97e34bef4410c6d55b6df1ad89d4a1668dc909a8bef2dc", family := 6, baseScore := 18974, ties := [10251213045696955239, 8277559809786887086, 5177563136290298210, 15546223716982519149, 1147826290981145593] }, { key := "a81860939523b8a89c1057eba532b96499612047fc01742df3be9cc579f2bc8b", family := 7, baseScore := 19486, ties := [4983646346911007955, 15991257719540894265, 7392099215831283465, 9351590683087415241, 4891173289025094829] }, { key := "ae7cbfc791101dfe44fd483199848f9de565da63d63433a94f2d7aa700277a98", family := 5, baseScore := 19473, ties := [11916698324925651244, 3779034800305266545, 6723460190554234405, 4996725434995486014, 9123272532919935628] }, { key := "b88f309e3eedc1201be67286e71146a82f3c98b605cd9a98095dfb4a4435eb12", family := 7, baseScore := 19488, ties := [8236809976806246490, 9592656197184993850, 13395775239428778536, 16521712693720081845, 6612592757519420357] }, { key := "bbc1ff8710f17883bab1263fa3a97a43dce6afbeb51ee87298705a13dc97d3fe", family := 4, baseScore := 19507, ties := [9895441269519714204, 10567975818667182412, 2949762867666745447, 15358263284222592413, 7818756811871304356] }, { key := "be48dbf0eab9b1c6cb1b383a4a819ba03b1fbe5def5a2ede1abeff841e86a340", family := 0, baseScore := 18940, ties := [12051271293274815325, 8498763912633731322, 16214678916157904758, 5852676273995598448, 7762158363813604185] }, { key := "beb74d988214ab69ce6d5579b8a135d6b9bb7cfe55ef5f639731f4b5945dfa76", family := 3, baseScore := 19451, ties := [6687728494088923561, 15688533194881422083, 11054250652464361855, 3431282234277072745, 16283540379544306886] }, { key := "c1ec7b3347051f6043ed84e712320056358447de8d23eb2e9bc1537de1767283", family := 2, baseScore := 19467, ties := [13285210797448947710, 14708564226017442511, 5426189561929132630, 9367810302013171095, 11203445840724478819] }, { key := "c2cafaf439159f3bf4ff17d47a0ac33f22866b324b8b44a02c91a4aa8c9365e0", family := 0, baseScore := 18964, ties := [11311766996352523566, 11946356079815518726, 10786483167680738130, 9785448311272348928, 5814422632839180568] }, { key := "d2c17eb8f048b3c3ed3cbde41e95d021928a189d589d7a98e4b23364f500047a", family := 5, baseScore := 19480, ties := [2478731396848945458, 10946844841225976487, 4382384839441706234, 12669902370179852976, 7955262276166890039] }, { key := "efd52e8c0b30256601b60f3dd4e489739da9b0eb1a2dcc086665b01b8b6f4a39", family := 5, baseScore := 19477, ties := [12568675729554285567, 4996633094436695344, 15449578570687309064, 12529300530850918538, 10646814677314777144] }] }
def domain1 : Domain := ⟨context1, [("00249ca0b7a67c15459a63436150df40b37e902ef4c8e982e96771b088efd180", { family := 0, variant := 0, a := (-14), b := (-16) }), ("0285dff171e0f02e9b860d18f00b95b44877bf7a3c73b9c5391421fd99bd0867", { family := 7, variant := 3, a := 16, b := (-16) }), ("06116e73fb137a69f4207ea8915ca755b626c24078922db00e07e5b645eb365c", { family := 1, variant := 0, a := (-12), b := 13 }), ("0aba9c83eefc68880e4a6b53c51c1761b9e77dbf7bb19f640b4ad3a5b8f2d2ea", { family := 6, variant := 3, a := 15, b := (-12) }), ("0cc4d094b87b5f39cc487ac5f4a724ed40998e7f5dfc4745526a09cddd41d53a", { family := 2, variant := 0, a := 11, b := 14 }), ("16af37fa62383c0cb646c247cb5d9fc0535852285252c33b84d8f40bc552344b", { family := 3, variant := 3, a := 6, b := (-5) }), ("1a4227ba1f0a966a22e16bded3af275f2c271d890155c3bd51fc64f197fc3844", { family := 0, variant := 1, a := 1, b := (-14) }), ("2272ec8df233ce2e4d34665f06c6f1a7dd64bfdeb8e3ac274f09ffe23804593e", { family := 4, variant := 3, a := (-7), b := 5 }), ("2e8e78477230e75ccb5c319cf0b76de4d530b01e82ea6a3c18630abecddc5fff", { family := 4, variant := 2, a := (-9), b := (-6) }), ("33553591c35e07d8788165246c638307b37b0f522837f5d192778524efbcb6d1", { family := 1, variant := 1, a := (-10), b := (-6) }), ("3f36bf49ab6cc0ad7edb2a54b22609ce4d9b6d65439f5049762c6289ba52e210", { family := 4, variant := 0, a := 16, b := (-10) }), ("41091e0d83d3ca41d10190bc538d303e511a79113c9df9f3edb400e5d7f06806", { family := 2, variant := 3, a := (-16), b := (-5) }), ("4cfe5f09bcf72872500b1c0604c0e7bceb63f387d74396856c238cab79ccd982", { family := 1, variant := 3, a := 14, b := (-5) }), ("57a3367bb9ed42229a83b27586a131a0ba39c68ae2616d7865183b11394fa202", { family := 6, variant := 1, a := 0, b := 4 }), ("5de02c4fe1758e7198e688b25fbbdf2e2653921e3626f0ccbe8b24a3be35c478", { family := 1, variant := 2, a := (-9), b := (-8) }), ("6dd4b508318bd1750e02227959102f95ccc3e6dcedaca4e3a1b4cece77e0b1ba", { family := 6, variant := 2, a := (-10), b := (-6) }), ("73d333c33a7c893ef65b0e5fe74093bef5bb51e9c4dcfa47938d7055446fe726", { family := 5, variant := 0, a := 2, b := 9 }), ("7e2bc001d065c188a53be853a0f851fdd13c0f2de4beaf7edf74b99295a21153", { family := 7, variant := 0, a := (-11), b := 14 }), ("9151999095e5e261489d580791558f6a716a55ad5515286f1857837d57670554", { family := 3, variant := 1, a := 0, b := 15 }), ("964de7415dc5e4e47c6fdca408a553f6c1d9364360dc1b24c0ea8477c97d2477", { family := 3, variant := 2, a := (-13), b := (-15) }), ("965372954524542df02c4e6d3edc0b7c5068bd73c2a511dfd2b633b08eac55ce", { family := 2, variant := 2, a := 0, b := 10 }), ("99b406f5b59529ffae97e34bef4410c6d55b6df1ad89d4a1668dc909a8bef2dc", { family := 6, variant := 0, a := 1, b := (-5) }), ("a81860939523b8a89c1057eba532b96499612047fc01742df3be9cc579f2bc8b", { family := 7, variant := 1, a := 14, b := (-3) }), ("ae7cbfc791101dfe44fd483199848f9de565da63d63433a94f2d7aa700277a98", { family := 5, variant := 2, a := 6, b := 9 }), ("b88f309e3eedc1201be67286e71146a82f3c98b605cd9a98095dfb4a4435eb12", { family := 7, variant := 2, a := 5, b := 7 }), ("bbc1ff8710f17883bab1263fa3a97a43dce6afbeb51ee87298705a13dc97d3fe", { family := 4, variant := 1, a := 15, b := 15 }), ("be48dbf0eab9b1c6cb1b383a4a819ba03b1fbe5def5a2ede1abeff841e86a340", { family := 0, variant := 3, a := (-12), b := 7 }), ("beb74d988214ab69ce6d5579b8a135d6b9bb7cfe55ef5f639731f4b5945dfa76", { family := 3, variant := 0, a := (-8), b := (-9) }), ("c1ec7b3347051f6043ed84e712320056358447de8d23eb2e9bc1537de1767283", { family := 2, variant := 1, a := (-1), b := 1 }), ("c2cafaf439159f3bf4ff17d47a0ac33f22866b324b8b44a02c91a4aa8c9365e0", { family := 0, variant := 2, a := 10, b := 3 }), ("d2c17eb8f048b3c3ed3cbde41e95d021928a189d589d7a98e4b23364f500047a", { family := 5, variant := 1, a := 8, b := 13 }), ("efd52e8c0b30256601b60f3dd4e489739da9b0eb1a2dcc086665b01b8b6f4a39", { family := 5, variant := 3, a := 10, b := (-12) })]⟩
def contexts1 (_source : State) : Phase17Provenance.Context := context1
-- Identity table is a finite constructor association, not an evaluator history.
def identities1 : List String := ["81fa575052a351b6a3bb244a8cc4d31439de25371ce56783b38d828b6e51204a", "", "", "", "", "", "4e6d4c959a8fc3605734dd8c5e757552fd4d8dacc03e15748e4742b0d74eed2b", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "dc81fe223bfff94e28d90f1ec3b951473b03677d8b98bb52d4e71e181122045b", "", "", "d5f52fa682df0d237799fb069dfd5458a4345785c0d228621db8c13afeaae5eb", "", ""]
def builder1 (prior : List Nat) (index task : Nat) : Offer :=
  constructOffer fixed source1 domain1 (identities1.getD index "")
    prior index task (cumulativeCharges prior)
def evaluator1 : List Nat → Nat → Bool :=
  evaluate fixed contexts1 chargesAt source1 domain1 builder1
def grant1 : Grant := {
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
theorem domain_bound1 : DomainBound source1 domain1 := by
  refine ⟨rfl, ?_, rfl, rfl, ?_, ?_⟩
  · unfold Phase17Provenance.ContextValid
    refine ⟨rfl, by decide, by decide, ?_, ?_⟩
    · decide +kernel
    · decide +kernel
  · intro index
    fin_cases index <;> decide +kernel
  · intro family variant
    fin_cases family <;> fin_cases variant
    · exact ⟨⟨0, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨6, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨29, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨26, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨2, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨9, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨14, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨12, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨4, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨28, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨20, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨11, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨27, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨18, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨19, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨5, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨10, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨25, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨8, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨7, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨16, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨30, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨23, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨31, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨21, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨13, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨15, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨3, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨17, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨22, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨24, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨1, by decide⟩, rfl, rfl⟩
def observations1 : List Phase17Controller.Observation := [⟨19, false⟩, ⟨5, false⟩, ⟨18, false⟩, ⟨27, false⟩, ⟨13, false⟩, ⟨30, false⟩, ⟨15, false⟩, ⟨0, true⟩]
def state1_0 : ExecutionState :=
  ⟨⟨32, [], none⟩, []⟩
def state1_1 : ExecutionState :=
  ⟨⟨32, [⟨19, false⟩], none⟩, [.candidate, .vector, .vector]⟩
def state1_2 : ExecutionState :=
  ⟨⟨32, [⟨19, false⟩, ⟨5, false⟩], none⟩, [.candidate, .vector, .vector, .candidate, .vector, .vector]⟩
def state1_3 : ExecutionState :=
  ⟨⟨32, [⟨19, false⟩, ⟨5, false⟩, ⟨18, false⟩], none⟩, [.candidate, .vector, .vector, .candidate, .vector, .vector, .candidate, .vector, .vector]⟩
def state1_4 : ExecutionState :=
  ⟨⟨32, [⟨19, false⟩, ⟨5, false⟩, ⟨18, false⟩, ⟨27, false⟩], none⟩, [.candidate, .vector, .vector, .candidate, .vector, .vector, .candidate, .vector, .vector, .candidate, .vector, .vector]⟩
def state1_5 : ExecutionState :=
  ⟨⟨32, [⟨19, false⟩, ⟨5, false⟩, ⟨18, false⟩, ⟨27, false⟩, ⟨13, false⟩], none⟩, [.candidate, .vector, .vector, .candidate, .vector, .vector, .candidate, .vector, .vector, .candidate, .vector, .vector, .candidate, .vector, .vector]⟩
def state1_6 : ExecutionState :=
  ⟨⟨32, [⟨19, false⟩, ⟨5, false⟩, ⟨18, false⟩, ⟨27, false⟩, ⟨13, false⟩, ⟨30, false⟩], none⟩, [.candidate, .vector, .vector, .candidate, .vector, .vector, .candidate, .vector, .vector, .candidate, .vector, .vector, .candidate, .vector, .vector, .candidate, .vector, .vector]⟩
def state1_7 : ExecutionState :=
  ⟨⟨32, [⟨19, false⟩, ⟨5, false⟩, ⟨18, false⟩, ⟨27, false⟩, ⟨13, false⟩, ⟨30, false⟩, ⟨15, false⟩], none⟩, [.candidate, .vector, .vector, .candidate, .vector, .vector, .candidate, .vector, .vector, .candidate, .vector, .vector, .candidate, .vector, .vector, .candidate, .vector, .vector, .candidate, .vector, .vector]⟩
def state1_8 : ExecutionState :=
  ⟨⟨32, [⟨19, false⟩, ⟨5, false⟩, ⟨18, false⟩, ⟨27, false⟩, ⟨13, false⟩, ⟨30, false⟩, ⟨15, false⟩, ⟨0, true⟩], none⟩, [.candidate, .vector, .vector, .candidate, .vector, .vector, .candidate, .vector, .vector, .candidate, .vector, .vector, .candidate, .vector, .vector, .candidate, .vector, .vector, .candidate, .vector, .vector, .candidate, .vector, .vector]⟩
theorem choice1_0 : canonicalTask fixed source1 (Phase17Provenance.rowAt context1 19).key (rowProgram domain1 19) = none := by decide +kernel
theorem evaluation1_0 (prior : List Nat) : evaluator1 prior 19 = false :=
  no_contract_refused fixed contexts1 chargesAt source1 domain1 builder1 prior 19 choice1_0
theorem step1_0 : authorizedStep grant1 grant1 grant1.binding
    context1 evaluator1 2 state1_0 ⟨19, false⟩ = some state1_1 := by
  apply authorized_step_construct
  · decide +kernel
  · decide +kernel
  · exact (evaluation1_0 []).symm
  · decide +kernel
theorem choice1_1 : canonicalTask fixed source1 (Phase17Provenance.rowAt context1 5).key (rowProgram domain1 5) = none := by decide +kernel
theorem evaluation1_1 (prior : List Nat) : evaluator1 prior 5 = false :=
  no_contract_refused fixed contexts1 chargesAt source1 domain1 builder1 prior 5 choice1_1
theorem step1_1 : authorizedStep grant1 grant1 grant1.binding
    context1 evaluator1 2 state1_1 ⟨5, false⟩ = some state1_2 := by
  apply authorized_step_construct
  · decide +kernel
  · decide +kernel
  · exact (evaluation1_1 [19]).symm
  · decide +kernel
theorem choice1_2 : canonicalTask fixed source1 (Phase17Provenance.rowAt context1 18).key (rowProgram domain1 18) = none := by decide +kernel
theorem evaluation1_2 (prior : List Nat) : evaluator1 prior 18 = false :=
  no_contract_refused fixed contexts1 chargesAt source1 domain1 builder1 prior 18 choice1_2
theorem step1_2 : authorizedStep grant1 grant1 grant1.binding
    context1 evaluator1 2 state1_2 ⟨18, false⟩ = some state1_3 := by
  apply authorized_step_construct
  · decide +kernel
  · decide +kernel
  · exact (evaluation1_2 [19, 5]).symm
  · decide +kernel
theorem choice1_3 : canonicalTask fixed source1 (Phase17Provenance.rowAt context1 27).key (rowProgram domain1 27) = none := by decide +kernel
theorem evaluation1_3 (prior : List Nat) : evaluator1 prior 27 = false :=
  no_contract_refused fixed contexts1 chargesAt source1 domain1 builder1 prior 27 choice1_3
theorem step1_3 : authorizedStep grant1 grant1 grant1.binding
    context1 evaluator1 2 state1_3 ⟨27, false⟩ = some state1_4 := by
  apply authorized_step_construct
  · decide +kernel
  · decide +kernel
  · exact (evaluation1_3 [19, 5, 18]).symm
  · decide +kernel
theorem choice1_4 : canonicalTask fixed source1 (Phase17Provenance.rowAt context1 13).key (rowProgram domain1 13) = none := by decide +kernel
theorem evaluation1_4 (prior : List Nat) : evaluator1 prior 13 = false :=
  no_contract_refused fixed contexts1 chargesAt source1 domain1 builder1 prior 13 choice1_4
theorem step1_4 : authorizedStep grant1 grant1 grant1.binding
    context1 evaluator1 2 state1_4 ⟨13, false⟩ = some state1_5 := by
  apply authorized_step_construct
  · decide +kernel
  · decide +kernel
  · exact (evaluation1_4 [19, 5, 18, 27]).symm
  · decide +kernel
theorem choice1_5 : canonicalTask fixed source1 (Phase17Provenance.rowAt context1 30).key (rowProgram domain1 30) = none := by decide +kernel
theorem evaluation1_5 (prior : List Nat) : evaluator1 prior 30 = false :=
  no_contract_refused fixed contexts1 chargesAt source1 domain1 builder1 prior 30 choice1_5
theorem step1_5 : authorizedStep grant1 grant1 grant1.binding
    context1 evaluator1 2 state1_5 ⟨30, false⟩ = some state1_6 := by
  apply authorized_step_construct
  · decide +kernel
  · decide +kernel
  · exact (evaluation1_5 [19, 5, 18, 27, 13]).symm
  · decide +kernel
theorem choice1_6 : canonicalTask fixed source1 (Phase17Provenance.rowAt context1 15).key (rowProgram domain1 15) = none := by decide +kernel
theorem evaluation1_6 (prior : List Nat) : evaluator1 prior 15 = false :=
  no_contract_refused fixed contexts1 chargesAt source1 domain1 builder1 prior 15 choice1_6
theorem step1_6 : authorizedStep grant1 grant1 grant1.binding
    context1 evaluator1 2 state1_6 ⟨15, false⟩ = some state1_7 := by
  apply authorized_step_construct
  · decide +kernel
  · decide +kernel
  · exact (evaluation1_6 [19, 5, 18, 27, 13, 30]).symm
  · decide +kernel
theorem choice1_7 : canonicalTask fixed source1 (Phase17Provenance.rowAt context1 0).key (rowProgram domain1 0) = some 56 := by decide +kernel
theorem check1_7 : check fixed contexts1 (chargesAt [19, 5, 18, 27, 13, 30, 15] 0) source1 (builder1 [19, 5, 18, 27, 13, 30, 15] 0 56) = true := by decide +kernel
theorem evaluation1_7 : evaluator1 [19, 5, 18, 27, 13, 30, 15] 0 = true := by
  have requestBound : RequestBound contexts1 source1 domain1 := ⟨rfl, domain_bound1⟩
  have offerBound : OfferBound fixed source1 domain1 0 56 (builder1 [19, 5, 18, 27, 13, 30, 15] 0 56) :=
    constructed_offer_bound fixed source1 domain1 _ [19, 5, 18, 27, 13, 30, 15] 0 56 _ (by decide) choice1_7
  exact evaluation_of_checked fixed contexts1 chargesAt source1 domain1 builder1 [19, 5, 18, 27, 13, 30, 15] 0 56
    choice1_7 requestBound offerBound check1_7
theorem step1_7 : authorizedStep grant1 grant1 grant1.binding
    context1 evaluator1 2 state1_7 ⟨0, true⟩ = some state1_8 := by
  apply authorized_step_construct
  · decide +kernel
  · decide +kernel
  · exact (evaluation1_7).symm
  · decide +kernel
theorem case_second_source : authorizedReplay grant1 grant1 grant1.binding
    context1 evaluator1 2 state1_0 observations1 = some state1_8 := by
  have finalAllowed : admissibleExecution grant1 grant1 grant1.binding context1 state1_8 := by decide +kernel
  simp only [observations1, authorizedReplay, step1_0, step1_1, step1_2, step1_3, step1_4, step1_5, step1_6, step1_7, Option.bind_some, finalAllowed, if_true]
theorem terminal1 : Phase17Controller.decision context1 state1_8.controller = some .awaitRoot := by decide +kernel
def context2 : Phase17Provenance.Context := {
  generator := "d78909d7d6d01024fccd0389f7556b45cef14ce229a846d2e4b24d242bd5e6ca"
  parentPackage := "85bebb429b27104ee1d8ffabda71acd26c44847c2dd097dea249fa3ee5d4ae02"
  contextHash := "5f0c2149ea0a5aad7a5d3cbb364a23ecc6cacc8a74898b8fa00982eb9f4effa2"
  transcriptHash := "572ec7c9c7a2eae68502fad30cfff120cfff90a438fe7047722a656799977695"
  credits := 4
  offset := 13
  rows := [{ key := "00249ca0b7a67c15459a63436150df40b37e902ef4c8e982e96771b088efd180", family := 0, baseScore := 18979, ties := [4553607917419594186, 15630213348677571363, 6491470184965233070, 12975236029994362483, 9199608038457457419] }, { key := "0285dff171e0f02e9b860d18f00b95b44877bf7a3c73b9c5391421fd99bd0867", family := 7, baseScore := 19470, ties := [1235608626286219260, 14589305888208094634, 6012042459752446848, 1401537048990591301, 12548572882181379052] }, { key := "06116e73fb137a69f4207ea8915ca755b626c24078922db00e07e5b645eb365c", family := 1, baseScore := 19500, ties := [14779831714415871226, 14561845555793468901, 2597147493736101661, 10153577625387614155, 6316066677961894881] }, { key := "0aba9c83eefc68880e4a6b53c51c1761b9e77dbf7bb19f640b4ad3a5b8f2d2ea", family := 6, baseScore := 18961, ties := [6626467606468221162, 10377777079204700371, 4244831773562338702, 13838918378892720663, 17244208607420248773] }, { key := "0cc4d094b87b5f39cc487ac5f4a724ed40998e7f5dfc4745526a09cddd41d53a", family := 2, baseScore := 19465, ties := [6964417313513196287, 1937854464768571333, 6117199747458864962, 5629045087522162107, 16090330734450513172] }, { key := "16af37fa62383c0cb646c247cb5d9fc0535852285252c33b84d8f40bc552344b", family := 3, baseScore := 19484, ties := [18320742210603957192, 13685684753086744671, 12460789157455486836, 2606637140937366133, 1819276498982317089] }, { key := "1a4227ba1f0a966a22e16bded3af275f2c271d890155c3bd51fc64f197fc3844", family := 0, baseScore := 18938, ties := [6641821706485704339, 13302170244109756866, 11418188377995284119, 12841108583499365900, 12866350796943133768] }, { key := "2272ec8df233ce2e4d34665f06c6f1a7dd64bfdeb8e3ac274f09ffe23804593e", family := 4, baseScore := 19456, ties := [17440073036088024076, 17850800124352804877, 9277323740050615842, 9771922068205556620, 17192901834255228013] }, { key := "2e8e78477230e75ccb5c319cf0b76de4d530b01e82ea6a3c18630abecddc5fff", family := 4, baseScore := 19481, ties := [18285665064460180787, 5660530768491281904, 11379962485541547881, 10809849345758430066, 11587677409377468715] }, { key := "33553591c35e07d8788165246c638307b37b0f522837f5d192778524efbcb6d1", family := 1, baseScore := 19480, ties := [17861271631964304855, 8122504493604679585, 18314044924554156242, 7498463703266124334, 3391635388111775017] }, { key := "3f36bf49ab6cc0ad7edb2a54b22609ce4d9b6d65439f5049762c6289ba52e210", family := 4, baseScore := 19505, ties := [16635933426665611828, 6858093571604301732, 5732091328645710249, 7822549142922163405, 18314702954586983950] }, { key := "41091e0d83d3ca41d10190bc538d303e511a79113c9df9f3edb400e5d7f06806", family := 2, baseScore := 19509, ties := [8911718324786314464, 7812307280058208589, 5167504732806915598, 11449473658666200729, 17221710378744447916] }, { key := "4cfe5f09bcf72872500b1c0604c0e7bceb63f387d74396856c238cab79ccd982", family := 1, baseScore := 19505, ties := [17341774770462319288, 4313188716980430563, 15744894512023544329, 7579211954982347478, 7723141427290801174] }, { key := "57a3367bb9ed42229a83b27586a131a0ba39c68ae2616d7865183b11394fa202", family := 6, baseScore := 18971, ties := [17823677709858021513, 8898656616282283843, 8291955824474563455, 16887769684259994195, 13355909568892680471] }, { key := "5de02c4fe1758e7198e688b25fbbdf2e2653921e3626f0ccbe8b24a3be35c478", family := 1, baseScore := 19509, ties := [14807191708322662213, 17044965354008738285, 18443313728954636047, 10243819765663942441, 3620524776556645995] }, { key := "6dd4b508318bd1750e02227959102f95ccc3e6dcedaca4e3a1b4cece77e0b1ba", family := 6, baseScore := 18963, ties := [4611825008557849227, 12068062198346940845, 9264110086434342255, 11730042552289615760, 17606951110930597123] }, { key := "73d333c33a7c893ef65b0e5fe74093bef5bb51e9c4dcfa47938d7055446fe726", family := 5, baseScore := 19495, ties := [11482589328235147740, 1068453299199746736, 5378424396541192917, 15634196418256437704, 4956110018302537069] }, { key := "7e2bc001d065c188a53be853a0f851fdd13c0f2de4beaf7edf74b99295a21153", family := 7, baseScore := 19446, ties := [7269785910583463666, 5034351993244807247, 4796688542921649101, 8497389830871718492, 3107514905629775783] }, { key := "9151999095e5e261489d580791558f6a716a55ad5515286f1857837d57670554", family := 3, baseScore := 19467, ties := [16278487536480062638, 7069003754947579151, 3365949586702625898, 7167415787254846713, 7074187969969243679] }, { key := "964de7415dc5e4e47c6fdca408a553f6c1d9364360dc1b24c0ea8477c97d2477", family := 3, baseScore := 19536, ties := [14893870574831223063, 17082743386262297389, 12883058327497221215, 10034842100876355881, 4285547786177124656] }, { key := "965372954524542df02c4e6d3edc0b7c5068bd73c2a511dfd2b633b08eac55ce", family := 2, baseScore := 19460, ties := [10602356374792532036, 14633862890172536179, 7996815289223726113, 4714145402830052898, 11799739847749970126] }, { key := "99b406f5b59529ffae97e34bef4410c6d55b6df1ad89d4a1668dc909a8bef2dc", family := 6, baseScore := 18974, ties := [10251213045696955239, 8277559809786887086, 5177563136290298210, 15546223716982519149, 1147826290981145593] }, { key := "a81860939523b8a89c1057eba532b96499612047fc01742df3be9cc579f2bc8b", family := 7, baseScore := 19486, ties := [4983646346911007955, 15991257719540894265, 7392099215831283465, 9351590683087415241, 4891173289025094829] }, { key := "ae7cbfc791101dfe44fd483199848f9de565da63d63433a94f2d7aa700277a98", family := 5, baseScore := 19473, ties := [11916698324925651244, 3779034800305266545, 6723460190554234405, 4996725434995486014, 9123272532919935628] }, { key := "b88f309e3eedc1201be67286e71146a82f3c98b605cd9a98095dfb4a4435eb12", family := 7, baseScore := 19488, ties := [8236809976806246490, 9592656197184993850, 13395775239428778536, 16521712693720081845, 6612592757519420357] }, { key := "bbc1ff8710f17883bab1263fa3a97a43dce6afbeb51ee87298705a13dc97d3fe", family := 4, baseScore := 19507, ties := [9895441269519714204, 10567975818667182412, 2949762867666745447, 15358263284222592413, 7818756811871304356] }, { key := "be48dbf0eab9b1c6cb1b383a4a819ba03b1fbe5def5a2ede1abeff841e86a340", family := 0, baseScore := 18940, ties := [12051271293274815325, 8498763912633731322, 16214678916157904758, 5852676273995598448, 7762158363813604185] }, { key := "beb74d988214ab69ce6d5579b8a135d6b9bb7cfe55ef5f639731f4b5945dfa76", family := 3, baseScore := 19451, ties := [6687728494088923561, 15688533194881422083, 11054250652464361855, 3431282234277072745, 16283540379544306886] }, { key := "c1ec7b3347051f6043ed84e712320056358447de8d23eb2e9bc1537de1767283", family := 2, baseScore := 19467, ties := [13285210797448947710, 14708564226017442511, 5426189561929132630, 9367810302013171095, 11203445840724478819] }, { key := "c2cafaf439159f3bf4ff17d47a0ac33f22866b324b8b44a02c91a4aa8c9365e0", family := 0, baseScore := 18964, ties := [11311766996352523566, 11946356079815518726, 10786483167680738130, 9785448311272348928, 5814422632839180568] }, { key := "d2c17eb8f048b3c3ed3cbde41e95d021928a189d589d7a98e4b23364f500047a", family := 5, baseScore := 19480, ties := [2478731396848945458, 10946844841225976487, 4382384839441706234, 12669902370179852976, 7955262276166890039] }, { key := "efd52e8c0b30256601b60f3dd4e489739da9b0eb1a2dcc086665b01b8b6f4a39", family := 5, baseScore := 19477, ties := [12568675729554285567, 4996633094436695344, 15449578570687309064, 12529300530850918538, 10646814677314777144] }] }
def domain2 : Domain := ⟨context2, [("00249ca0b7a67c15459a63436150df40b37e902ef4c8e982e96771b088efd180", { family := 0, variant := 0, a := (-14), b := (-16) }), ("0285dff171e0f02e9b860d18f00b95b44877bf7a3c73b9c5391421fd99bd0867", { family := 7, variant := 3, a := 16, b := (-16) }), ("06116e73fb137a69f4207ea8915ca755b626c24078922db00e07e5b645eb365c", { family := 1, variant := 0, a := (-12), b := 13 }), ("0aba9c83eefc68880e4a6b53c51c1761b9e77dbf7bb19f640b4ad3a5b8f2d2ea", { family := 6, variant := 3, a := 15, b := (-12) }), ("0cc4d094b87b5f39cc487ac5f4a724ed40998e7f5dfc4745526a09cddd41d53a", { family := 2, variant := 0, a := 11, b := 14 }), ("16af37fa62383c0cb646c247cb5d9fc0535852285252c33b84d8f40bc552344b", { family := 3, variant := 3, a := 6, b := (-5) }), ("1a4227ba1f0a966a22e16bded3af275f2c271d890155c3bd51fc64f197fc3844", { family := 0, variant := 1, a := 1, b := (-14) }), ("2272ec8df233ce2e4d34665f06c6f1a7dd64bfdeb8e3ac274f09ffe23804593e", { family := 4, variant := 3, a := (-7), b := 5 }), ("2e8e78477230e75ccb5c319cf0b76de4d530b01e82ea6a3c18630abecddc5fff", { family := 4, variant := 2, a := (-9), b := (-6) }), ("33553591c35e07d8788165246c638307b37b0f522837f5d192778524efbcb6d1", { family := 1, variant := 1, a := (-10), b := (-6) }), ("3f36bf49ab6cc0ad7edb2a54b22609ce4d9b6d65439f5049762c6289ba52e210", { family := 4, variant := 0, a := 16, b := (-10) }), ("41091e0d83d3ca41d10190bc538d303e511a79113c9df9f3edb400e5d7f06806", { family := 2, variant := 3, a := (-16), b := (-5) }), ("4cfe5f09bcf72872500b1c0604c0e7bceb63f387d74396856c238cab79ccd982", { family := 1, variant := 3, a := 14, b := (-5) }), ("57a3367bb9ed42229a83b27586a131a0ba39c68ae2616d7865183b11394fa202", { family := 6, variant := 1, a := 0, b := 4 }), ("5de02c4fe1758e7198e688b25fbbdf2e2653921e3626f0ccbe8b24a3be35c478", { family := 1, variant := 2, a := (-9), b := (-8) }), ("6dd4b508318bd1750e02227959102f95ccc3e6dcedaca4e3a1b4cece77e0b1ba", { family := 6, variant := 2, a := (-10), b := (-6) }), ("73d333c33a7c893ef65b0e5fe74093bef5bb51e9c4dcfa47938d7055446fe726", { family := 5, variant := 0, a := 2, b := 9 }), ("7e2bc001d065c188a53be853a0f851fdd13c0f2de4beaf7edf74b99295a21153", { family := 7, variant := 0, a := (-11), b := 14 }), ("9151999095e5e261489d580791558f6a716a55ad5515286f1857837d57670554", { family := 3, variant := 1, a := 0, b := 15 }), ("964de7415dc5e4e47c6fdca408a553f6c1d9364360dc1b24c0ea8477c97d2477", { family := 3, variant := 2, a := (-13), b := (-15) }), ("965372954524542df02c4e6d3edc0b7c5068bd73c2a511dfd2b633b08eac55ce", { family := 2, variant := 2, a := 0, b := 10 }), ("99b406f5b59529ffae97e34bef4410c6d55b6df1ad89d4a1668dc909a8bef2dc", { family := 6, variant := 0, a := 1, b := (-5) }), ("a81860939523b8a89c1057eba532b96499612047fc01742df3be9cc579f2bc8b", { family := 7, variant := 1, a := 14, b := (-3) }), ("ae7cbfc791101dfe44fd483199848f9de565da63d63433a94f2d7aa700277a98", { family := 5, variant := 2, a := 6, b := 9 }), ("b88f309e3eedc1201be67286e71146a82f3c98b605cd9a98095dfb4a4435eb12", { family := 7, variant := 2, a := 5, b := 7 }), ("bbc1ff8710f17883bab1263fa3a97a43dce6afbeb51ee87298705a13dc97d3fe", { family := 4, variant := 1, a := 15, b := 15 }), ("be48dbf0eab9b1c6cb1b383a4a819ba03b1fbe5def5a2ede1abeff841e86a340", { family := 0, variant := 3, a := (-12), b := 7 }), ("beb74d988214ab69ce6d5579b8a135d6b9bb7cfe55ef5f639731f4b5945dfa76", { family := 3, variant := 0, a := (-8), b := (-9) }), ("c1ec7b3347051f6043ed84e712320056358447de8d23eb2e9bc1537de1767283", { family := 2, variant := 1, a := (-1), b := 1 }), ("c2cafaf439159f3bf4ff17d47a0ac33f22866b324b8b44a02c91a4aa8c9365e0", { family := 0, variant := 2, a := 10, b := 3 }), ("d2c17eb8f048b3c3ed3cbde41e95d021928a189d589d7a98e4b23364f500047a", { family := 5, variant := 1, a := 8, b := 13 }), ("efd52e8c0b30256601b60f3dd4e489739da9b0eb1a2dcc086665b01b8b6f4a39", { family := 5, variant := 3, a := 10, b := (-12) })]⟩
def contexts2 (_source : State) : Phase17Provenance.Context := context2
-- Identity table is a finite constructor association, not an evaluator history.
def identities2 : List String := ["3bdf7e6bfe5f1a2739e5556be03a28fc3126451f43be492eca0d9b1c9b4f9d1b", "", "", "", "", "", "0b2f83430a16465f4dbe458d3d576ec81d691905ebde84334745b663de65f170", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "3023a96b4de60fff577c052f31f53e1472ea2472771eb2fd5129c4ab3e79dd6d", "", "", "c9c8cb680495758dacedc38e0d5a46454849932ade1e589dbd25e3226aa5ecba", "", ""]
def builder2 (prior : List Nat) (index task : Nat) : Offer :=
  constructOffer fixed source1 domain2 (identities2.getD index "")
    prior index task (cumulativeCharges prior)
def evaluator2 : List Nat → Nat → Bool :=
  evaluate fixed contexts2 chargesAt source1 domain2 builder2
def grant2 : Grant := {
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
theorem domain_bound2 : DomainBound source1 domain2 := by
  refine ⟨rfl, ?_, rfl, rfl, ?_, ?_⟩
  · rcases domain_bound1.2.1 with ⟨length, _, offset, keys, rows⟩
    exact ⟨length, by decide, offset, keys, rows⟩
  · intro index
    fin_cases index <;> decide +kernel
  · intro family variant
    fin_cases family <;> fin_cases variant
    · exact ⟨⟨0, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨6, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨29, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨26, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨2, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨9, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨14, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨12, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨4, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨28, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨20, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨11, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨27, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨18, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨19, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨5, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨10, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨25, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨8, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨7, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨16, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨30, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨23, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨31, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨21, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨13, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨15, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨3, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨17, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨22, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨24, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨1, by decide⟩, rfl, rfl⟩
def observations2 : List Phase17Controller.Observation := [⟨19, false⟩, ⟨5, false⟩, ⟨18, false⟩, ⟨27, false⟩]
def state2_0 : ExecutionState :=
  ⟨⟨4, [], none⟩, []⟩
def state2_1 : ExecutionState :=
  ⟨⟨4, [⟨19, false⟩], none⟩, [.candidate, .vector, .vector]⟩
def state2_2 : ExecutionState :=
  ⟨⟨4, [⟨19, false⟩, ⟨5, false⟩], none⟩, [.candidate, .vector, .vector, .candidate, .vector, .vector]⟩
def state2_3 : ExecutionState :=
  ⟨⟨4, [⟨19, false⟩, ⟨5, false⟩, ⟨18, false⟩], none⟩, [.candidate, .vector, .vector, .candidate, .vector, .vector, .candidate, .vector, .vector]⟩
def state2_4 : ExecutionState :=
  ⟨⟨4, [⟨19, false⟩, ⟨5, false⟩, ⟨18, false⟩, ⟨27, false⟩], none⟩, [.candidate, .vector, .vector, .candidate, .vector, .vector, .candidate, .vector, .vector, .candidate, .vector, .vector]⟩
theorem choice2_0 : canonicalTask fixed source1 (Phase17Provenance.rowAt context2 19).key (rowProgram domain2 19) = none := by decide +kernel
theorem evaluation2_0 (prior : List Nat) : evaluator2 prior 19 = false :=
  no_contract_refused fixed contexts2 chargesAt source1 domain2 builder2 prior 19 choice2_0
theorem step2_0 : authorizedStep grant2 grant2 grant2.binding
    context2 evaluator2 2 state2_0 ⟨19, false⟩ = some state2_1 := by
  apply authorized_step_construct
  · decide +kernel
  · decide +kernel
  · exact (evaluation2_0 []).symm
  · decide +kernel
theorem choice2_1 : canonicalTask fixed source1 (Phase17Provenance.rowAt context2 5).key (rowProgram domain2 5) = none := by decide +kernel
theorem evaluation2_1 (prior : List Nat) : evaluator2 prior 5 = false :=
  no_contract_refused fixed contexts2 chargesAt source1 domain2 builder2 prior 5 choice2_1
theorem step2_1 : authorizedStep grant2 grant2 grant2.binding
    context2 evaluator2 2 state2_1 ⟨5, false⟩ = some state2_2 := by
  apply authorized_step_construct
  · decide +kernel
  · decide +kernel
  · exact (evaluation2_1 [19]).symm
  · decide +kernel
theorem choice2_2 : canonicalTask fixed source1 (Phase17Provenance.rowAt context2 18).key (rowProgram domain2 18) = none := by decide +kernel
theorem evaluation2_2 (prior : List Nat) : evaluator2 prior 18 = false :=
  no_contract_refused fixed contexts2 chargesAt source1 domain2 builder2 prior 18 choice2_2
theorem step2_2 : authorizedStep grant2 grant2 grant2.binding
    context2 evaluator2 2 state2_2 ⟨18, false⟩ = some state2_3 := by
  apply authorized_step_construct
  · decide +kernel
  · decide +kernel
  · exact (evaluation2_2 [19, 5]).symm
  · decide +kernel
theorem choice2_3 : canonicalTask fixed source1 (Phase17Provenance.rowAt context2 27).key (rowProgram domain2 27) = none := by decide +kernel
theorem evaluation2_3 (prior : List Nat) : evaluator2 prior 27 = false :=
  no_contract_refused fixed contexts2 chargesAt source1 domain2 builder2 prior 27 choice2_3
theorem step2_3 : authorizedStep grant2 grant2 grant2.binding
    context2 evaluator2 2 state2_3 ⟨27, false⟩ = some state2_4 := by
  apply authorized_step_construct
  · decide +kernel
  · decide +kernel
  · exact (evaluation2_3 [19, 5, 18]).symm
  · decide +kernel
theorem case_second_source_credit_stop : authorizedReplay grant2 grant2 grant2.binding
    context2 evaluator2 2 state2_0 observations2 = some state2_4 := by
  have finalAllowed : admissibleExecution grant2 grant2 grant2.binding context2 state2_4 := by decide +kernel
  simp only [observations2, authorizedReplay, step2_0, step2_1, step2_2, step2_3, Option.bind_some, finalAllowed, if_true]
theorem terminal2 : Phase17Controller.decision context2 state2_4.controller = some .resourceExhausted := by decide +kernel
def context3 : Phase17Provenance.Context := {
  generator := "d78909d7d6d01024fccd0389f7556b45cef14ce229a846d2e4b24d242bd5e6ca"
  parentPackage := "85bebb429b27104ee1d8ffabda71acd26c44847c2dd097dea249fa3ee5d4ae02"
  contextHash := "96caa41a876156e528e0f62cacd5fc32e8902f38b3bae32780b6f5c33d28181d"
  transcriptHash := "572ec7c9c7a2eae68502fad30cfff120cfff90a438fe7047722a656799977695"
  credits := 0
  offset := 13
  rows := [{ key := "00249ca0b7a67c15459a63436150df40b37e902ef4c8e982e96771b088efd180", family := 0, baseScore := 18979, ties := [4553607917419594186, 15630213348677571363, 6491470184965233070, 12975236029994362483, 9199608038457457419] }, { key := "0285dff171e0f02e9b860d18f00b95b44877bf7a3c73b9c5391421fd99bd0867", family := 7, baseScore := 19470, ties := [1235608626286219260, 14589305888208094634, 6012042459752446848, 1401537048990591301, 12548572882181379052] }, { key := "06116e73fb137a69f4207ea8915ca755b626c24078922db00e07e5b645eb365c", family := 1, baseScore := 19500, ties := [14779831714415871226, 14561845555793468901, 2597147493736101661, 10153577625387614155, 6316066677961894881] }, { key := "0aba9c83eefc68880e4a6b53c51c1761b9e77dbf7bb19f640b4ad3a5b8f2d2ea", family := 6, baseScore := 18961, ties := [6626467606468221162, 10377777079204700371, 4244831773562338702, 13838918378892720663, 17244208607420248773] }, { key := "0cc4d094b87b5f39cc487ac5f4a724ed40998e7f5dfc4745526a09cddd41d53a", family := 2, baseScore := 19465, ties := [6964417313513196287, 1937854464768571333, 6117199747458864962, 5629045087522162107, 16090330734450513172] }, { key := "16af37fa62383c0cb646c247cb5d9fc0535852285252c33b84d8f40bc552344b", family := 3, baseScore := 19484, ties := [18320742210603957192, 13685684753086744671, 12460789157455486836, 2606637140937366133, 1819276498982317089] }, { key := "1a4227ba1f0a966a22e16bded3af275f2c271d890155c3bd51fc64f197fc3844", family := 0, baseScore := 18938, ties := [6641821706485704339, 13302170244109756866, 11418188377995284119, 12841108583499365900, 12866350796943133768] }, { key := "2272ec8df233ce2e4d34665f06c6f1a7dd64bfdeb8e3ac274f09ffe23804593e", family := 4, baseScore := 19456, ties := [17440073036088024076, 17850800124352804877, 9277323740050615842, 9771922068205556620, 17192901834255228013] }, { key := "2e8e78477230e75ccb5c319cf0b76de4d530b01e82ea6a3c18630abecddc5fff", family := 4, baseScore := 19481, ties := [18285665064460180787, 5660530768491281904, 11379962485541547881, 10809849345758430066, 11587677409377468715] }, { key := "33553591c35e07d8788165246c638307b37b0f522837f5d192778524efbcb6d1", family := 1, baseScore := 19480, ties := [17861271631964304855, 8122504493604679585, 18314044924554156242, 7498463703266124334, 3391635388111775017] }, { key := "3f36bf49ab6cc0ad7edb2a54b22609ce4d9b6d65439f5049762c6289ba52e210", family := 4, baseScore := 19505, ties := [16635933426665611828, 6858093571604301732, 5732091328645710249, 7822549142922163405, 18314702954586983950] }, { key := "41091e0d83d3ca41d10190bc538d303e511a79113c9df9f3edb400e5d7f06806", family := 2, baseScore := 19509, ties := [8911718324786314464, 7812307280058208589, 5167504732806915598, 11449473658666200729, 17221710378744447916] }, { key := "4cfe5f09bcf72872500b1c0604c0e7bceb63f387d74396856c238cab79ccd982", family := 1, baseScore := 19505, ties := [17341774770462319288, 4313188716980430563, 15744894512023544329, 7579211954982347478, 7723141427290801174] }, { key := "57a3367bb9ed42229a83b27586a131a0ba39c68ae2616d7865183b11394fa202", family := 6, baseScore := 18971, ties := [17823677709858021513, 8898656616282283843, 8291955824474563455, 16887769684259994195, 13355909568892680471] }, { key := "5de02c4fe1758e7198e688b25fbbdf2e2653921e3626f0ccbe8b24a3be35c478", family := 1, baseScore := 19509, ties := [14807191708322662213, 17044965354008738285, 18443313728954636047, 10243819765663942441, 3620524776556645995] }, { key := "6dd4b508318bd1750e02227959102f95ccc3e6dcedaca4e3a1b4cece77e0b1ba", family := 6, baseScore := 18963, ties := [4611825008557849227, 12068062198346940845, 9264110086434342255, 11730042552289615760, 17606951110930597123] }, { key := "73d333c33a7c893ef65b0e5fe74093bef5bb51e9c4dcfa47938d7055446fe726", family := 5, baseScore := 19495, ties := [11482589328235147740, 1068453299199746736, 5378424396541192917, 15634196418256437704, 4956110018302537069] }, { key := "7e2bc001d065c188a53be853a0f851fdd13c0f2de4beaf7edf74b99295a21153", family := 7, baseScore := 19446, ties := [7269785910583463666, 5034351993244807247, 4796688542921649101, 8497389830871718492, 3107514905629775783] }, { key := "9151999095e5e261489d580791558f6a716a55ad5515286f1857837d57670554", family := 3, baseScore := 19467, ties := [16278487536480062638, 7069003754947579151, 3365949586702625898, 7167415787254846713, 7074187969969243679] }, { key := "964de7415dc5e4e47c6fdca408a553f6c1d9364360dc1b24c0ea8477c97d2477", family := 3, baseScore := 19536, ties := [14893870574831223063, 17082743386262297389, 12883058327497221215, 10034842100876355881, 4285547786177124656] }, { key := "965372954524542df02c4e6d3edc0b7c5068bd73c2a511dfd2b633b08eac55ce", family := 2, baseScore := 19460, ties := [10602356374792532036, 14633862890172536179, 7996815289223726113, 4714145402830052898, 11799739847749970126] }, { key := "99b406f5b59529ffae97e34bef4410c6d55b6df1ad89d4a1668dc909a8bef2dc", family := 6, baseScore := 18974, ties := [10251213045696955239, 8277559809786887086, 5177563136290298210, 15546223716982519149, 1147826290981145593] }, { key := "a81860939523b8a89c1057eba532b96499612047fc01742df3be9cc579f2bc8b", family := 7, baseScore := 19486, ties := [4983646346911007955, 15991257719540894265, 7392099215831283465, 9351590683087415241, 4891173289025094829] }, { key := "ae7cbfc791101dfe44fd483199848f9de565da63d63433a94f2d7aa700277a98", family := 5, baseScore := 19473, ties := [11916698324925651244, 3779034800305266545, 6723460190554234405, 4996725434995486014, 9123272532919935628] }, { key := "b88f309e3eedc1201be67286e71146a82f3c98b605cd9a98095dfb4a4435eb12", family := 7, baseScore := 19488, ties := [8236809976806246490, 9592656197184993850, 13395775239428778536, 16521712693720081845, 6612592757519420357] }, { key := "bbc1ff8710f17883bab1263fa3a97a43dce6afbeb51ee87298705a13dc97d3fe", family := 4, baseScore := 19507, ties := [9895441269519714204, 10567975818667182412, 2949762867666745447, 15358263284222592413, 7818756811871304356] }, { key := "be48dbf0eab9b1c6cb1b383a4a819ba03b1fbe5def5a2ede1abeff841e86a340", family := 0, baseScore := 18940, ties := [12051271293274815325, 8498763912633731322, 16214678916157904758, 5852676273995598448, 7762158363813604185] }, { key := "beb74d988214ab69ce6d5579b8a135d6b9bb7cfe55ef5f639731f4b5945dfa76", family := 3, baseScore := 19451, ties := [6687728494088923561, 15688533194881422083, 11054250652464361855, 3431282234277072745, 16283540379544306886] }, { key := "c1ec7b3347051f6043ed84e712320056358447de8d23eb2e9bc1537de1767283", family := 2, baseScore := 19467, ties := [13285210797448947710, 14708564226017442511, 5426189561929132630, 9367810302013171095, 11203445840724478819] }, { key := "c2cafaf439159f3bf4ff17d47a0ac33f22866b324b8b44a02c91a4aa8c9365e0", family := 0, baseScore := 18964, ties := [11311766996352523566, 11946356079815518726, 10786483167680738130, 9785448311272348928, 5814422632839180568] }, { key := "d2c17eb8f048b3c3ed3cbde41e95d021928a189d589d7a98e4b23364f500047a", family := 5, baseScore := 19480, ties := [2478731396848945458, 10946844841225976487, 4382384839441706234, 12669902370179852976, 7955262276166890039] }, { key := "efd52e8c0b30256601b60f3dd4e489739da9b0eb1a2dcc086665b01b8b6f4a39", family := 5, baseScore := 19477, ties := [12568675729554285567, 4996633094436695344, 15449578570687309064, 12529300530850918538, 10646814677314777144] }] }
def domain3 : Domain := ⟨context3, [("00249ca0b7a67c15459a63436150df40b37e902ef4c8e982e96771b088efd180", { family := 0, variant := 0, a := (-14), b := (-16) }), ("0285dff171e0f02e9b860d18f00b95b44877bf7a3c73b9c5391421fd99bd0867", { family := 7, variant := 3, a := 16, b := (-16) }), ("06116e73fb137a69f4207ea8915ca755b626c24078922db00e07e5b645eb365c", { family := 1, variant := 0, a := (-12), b := 13 }), ("0aba9c83eefc68880e4a6b53c51c1761b9e77dbf7bb19f640b4ad3a5b8f2d2ea", { family := 6, variant := 3, a := 15, b := (-12) }), ("0cc4d094b87b5f39cc487ac5f4a724ed40998e7f5dfc4745526a09cddd41d53a", { family := 2, variant := 0, a := 11, b := 14 }), ("16af37fa62383c0cb646c247cb5d9fc0535852285252c33b84d8f40bc552344b", { family := 3, variant := 3, a := 6, b := (-5) }), ("1a4227ba1f0a966a22e16bded3af275f2c271d890155c3bd51fc64f197fc3844", { family := 0, variant := 1, a := 1, b := (-14) }), ("2272ec8df233ce2e4d34665f06c6f1a7dd64bfdeb8e3ac274f09ffe23804593e", { family := 4, variant := 3, a := (-7), b := 5 }), ("2e8e78477230e75ccb5c319cf0b76de4d530b01e82ea6a3c18630abecddc5fff", { family := 4, variant := 2, a := (-9), b := (-6) }), ("33553591c35e07d8788165246c638307b37b0f522837f5d192778524efbcb6d1", { family := 1, variant := 1, a := (-10), b := (-6) }), ("3f36bf49ab6cc0ad7edb2a54b22609ce4d9b6d65439f5049762c6289ba52e210", { family := 4, variant := 0, a := 16, b := (-10) }), ("41091e0d83d3ca41d10190bc538d303e511a79113c9df9f3edb400e5d7f06806", { family := 2, variant := 3, a := (-16), b := (-5) }), ("4cfe5f09bcf72872500b1c0604c0e7bceb63f387d74396856c238cab79ccd982", { family := 1, variant := 3, a := 14, b := (-5) }), ("57a3367bb9ed42229a83b27586a131a0ba39c68ae2616d7865183b11394fa202", { family := 6, variant := 1, a := 0, b := 4 }), ("5de02c4fe1758e7198e688b25fbbdf2e2653921e3626f0ccbe8b24a3be35c478", { family := 1, variant := 2, a := (-9), b := (-8) }), ("6dd4b508318bd1750e02227959102f95ccc3e6dcedaca4e3a1b4cece77e0b1ba", { family := 6, variant := 2, a := (-10), b := (-6) }), ("73d333c33a7c893ef65b0e5fe74093bef5bb51e9c4dcfa47938d7055446fe726", { family := 5, variant := 0, a := 2, b := 9 }), ("7e2bc001d065c188a53be853a0f851fdd13c0f2de4beaf7edf74b99295a21153", { family := 7, variant := 0, a := (-11), b := 14 }), ("9151999095e5e261489d580791558f6a716a55ad5515286f1857837d57670554", { family := 3, variant := 1, a := 0, b := 15 }), ("964de7415dc5e4e47c6fdca408a553f6c1d9364360dc1b24c0ea8477c97d2477", { family := 3, variant := 2, a := (-13), b := (-15) }), ("965372954524542df02c4e6d3edc0b7c5068bd73c2a511dfd2b633b08eac55ce", { family := 2, variant := 2, a := 0, b := 10 }), ("99b406f5b59529ffae97e34bef4410c6d55b6df1ad89d4a1668dc909a8bef2dc", { family := 6, variant := 0, a := 1, b := (-5) }), ("a81860939523b8a89c1057eba532b96499612047fc01742df3be9cc579f2bc8b", { family := 7, variant := 1, a := 14, b := (-3) }), ("ae7cbfc791101dfe44fd483199848f9de565da63d63433a94f2d7aa700277a98", { family := 5, variant := 2, a := 6, b := 9 }), ("b88f309e3eedc1201be67286e71146a82f3c98b605cd9a98095dfb4a4435eb12", { family := 7, variant := 2, a := 5, b := 7 }), ("bbc1ff8710f17883bab1263fa3a97a43dce6afbeb51ee87298705a13dc97d3fe", { family := 4, variant := 1, a := 15, b := 15 }), ("be48dbf0eab9b1c6cb1b383a4a819ba03b1fbe5def5a2ede1abeff841e86a340", { family := 0, variant := 3, a := (-12), b := 7 }), ("beb74d988214ab69ce6d5579b8a135d6b9bb7cfe55ef5f639731f4b5945dfa76", { family := 3, variant := 0, a := (-8), b := (-9) }), ("c1ec7b3347051f6043ed84e712320056358447de8d23eb2e9bc1537de1767283", { family := 2, variant := 1, a := (-1), b := 1 }), ("c2cafaf439159f3bf4ff17d47a0ac33f22866b324b8b44a02c91a4aa8c9365e0", { family := 0, variant := 2, a := 10, b := 3 }), ("d2c17eb8f048b3c3ed3cbde41e95d021928a189d589d7a98e4b23364f500047a", { family := 5, variant := 1, a := 8, b := 13 }), ("efd52e8c0b30256601b60f3dd4e489739da9b0eb1a2dcc086665b01b8b6f4a39", { family := 5, variant := 3, a := 10, b := (-12) })]⟩
def contexts3 (_source : State) : Phase17Provenance.Context := context3
-- Identity table is a finite constructor association, not an evaluator history.
def identities3 : List String := ["6573ef8362908f22c9820d9632a4c79206cde1c502f1474c71cf997112d2f5b1", "", "", "", "", "", "de1f75efec9be328731c9fb56bc0c0918554b488b9b4adf4b20555ee18e2fb39", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "7161d4d39fbcbe6baf00d25de6bf16d958d381797427f64b0c17af42d464d418", "", "", "f46a84b70145df957be6d6c7b293ff131818136582d1445ec0873155ee75aece", "", ""]
def builder3 (prior : List Nat) (index task : Nat) : Offer :=
  constructOffer fixed source1 domain3 (identities3.getD index "")
    prior index task (cumulativeCharges prior)
def evaluator3 : List Nat → Nat → Bool :=
  evaluate fixed contexts3 chargesAt source1 domain3 builder3
def grant3 : Grant := {
  binding := {
    source := "3659236854fc37d749f579879be16c8795efa1019b4180d3115dc1b66b7b5b8c"
    request := "1b7372e22f9b36d7b59b6d3942a5493a7d3a24b438ff5cbeb38029866b5d0c3a"
    package := "85bebb429b27104ee1d8ffabda71acd26c44847c2dd097dea249fa3ee5d4ae02"
    history := "572ec7c9c7a2eae68502fad30cfff120cfff90a438fe7047722a656799977695"
    context := "96caa41a876156e528e0f62cacd5fc32e8902f38b3bae32780b6f5c33d28181d"
    catalog := "511a8e2783bfa6b4d2dcfda2a700967e5a9e101ba7f57d8ff6b61b164034cf5d"
    evaluator := "phase17ah.fixed-ae-least-missing-contract-ag-acceptance.v1"
  }
  candidateLimit := 0
  referenceCandidateLimit := 32
  vectorLimit := 64
  inputLimit := 256
  outputLimit := 256
  costLimit := 3584 }
theorem domain_bound3 : DomainBound source1 domain3 := by
  refine ⟨rfl, ?_, rfl, rfl, ?_, ?_⟩
  · rcases domain_bound1.2.1 with ⟨length, _, offset, keys, rows⟩
    exact ⟨length, by decide, offset, keys, rows⟩
  · intro index
    fin_cases index <;> decide +kernel
  · intro family variant
    fin_cases family <;> fin_cases variant
    · exact ⟨⟨0, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨6, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨29, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨26, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨2, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨9, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨14, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨12, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨4, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨28, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨20, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨11, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨27, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨18, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨19, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨5, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨10, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨25, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨8, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨7, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨16, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨30, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨23, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨31, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨21, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨13, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨15, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨3, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨17, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨22, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨24, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨1, by decide⟩, rfl, rfl⟩
def observations3 : List Phase17Controller.Observation := []
def state3_0 : ExecutionState :=
  ⟨⟨0, [], none⟩, []⟩
theorem case_second_source_zero_credit : authorizedReplay grant3 grant3 grant3.binding
    context3 evaluator3 2 state3_0 observations3 = some state3_0 := by
  have finalAllowed : admissibleExecution grant3 grant3 grant3.binding context3 state3_0 := by decide +kernel
  simp only [observations3, authorizedReplay, finalAllowed, if_true]
theorem terminal3 : Phase17Controller.decision context3 state3_0.controller = some .resourceExhausted := by decide +kernel
def context4 : Phase17Provenance.Context := {
  generator := "d78909d7d6d01024fccd0389f7556b45cef14ce229a846d2e4b24d242bd5e6ca"
  parentPackage := "85bebb429b27104ee1d8ffabda71acd26c44847c2dd097dea249fa3ee5d4ae02"
  contextHash := "d0a6812be0e1d9799be1069336fae7002bb0cdfe907f9ee48c76f3cbccc480b5"
  transcriptHash := "572ec7c9c7a2eae68502fad30cfff120cfff90a438fe7047722a656799977695"
  credits := 32
  offset := 13
  rows := [{ key := "00249ca0b7a67c15459a63436150df40b37e902ef4c8e982e96771b088efd180", family := 0, baseScore := 18979, ties := [4553607917419594186, 15630213348677571363, 6491470184965233070, 12975236029994362483, 9199608038457457419] }, { key := "0285dff171e0f02e9b860d18f00b95b44877bf7a3c73b9c5391421fd99bd0867", family := 7, baseScore := 19470, ties := [1235608626286219260, 14589305888208094634, 6012042459752446848, 1401537048990591301, 12548572882181379052] }, { key := "06116e73fb137a69f4207ea8915ca755b626c24078922db00e07e5b645eb365c", family := 1, baseScore := 19500, ties := [14779831714415871226, 14561845555793468901, 2597147493736101661, 10153577625387614155, 6316066677961894881] }, { key := "0aba9c83eefc68880e4a6b53c51c1761b9e77dbf7bb19f640b4ad3a5b8f2d2ea", family := 6, baseScore := 18961, ties := [6626467606468221162, 10377777079204700371, 4244831773562338702, 13838918378892720663, 17244208607420248773] }, { key := "0cc4d094b87b5f39cc487ac5f4a724ed40998e7f5dfc4745526a09cddd41d53a", family := 2, baseScore := 19465, ties := [6964417313513196287, 1937854464768571333, 6117199747458864962, 5629045087522162107, 16090330734450513172] }, { key := "16af37fa62383c0cb646c247cb5d9fc0535852285252c33b84d8f40bc552344b", family := 3, baseScore := 19484, ties := [18320742210603957192, 13685684753086744671, 12460789157455486836, 2606637140937366133, 1819276498982317089] }, { key := "1a4227ba1f0a966a22e16bded3af275f2c271d890155c3bd51fc64f197fc3844", family := 0, baseScore := 18938, ties := [6641821706485704339, 13302170244109756866, 11418188377995284119, 12841108583499365900, 12866350796943133768] }, { key := "2272ec8df233ce2e4d34665f06c6f1a7dd64bfdeb8e3ac274f09ffe23804593e", family := 4, baseScore := 19456, ties := [17440073036088024076, 17850800124352804877, 9277323740050615842, 9771922068205556620, 17192901834255228013] }, { key := "2e8e78477230e75ccb5c319cf0b76de4d530b01e82ea6a3c18630abecddc5fff", family := 4, baseScore := 19481, ties := [18285665064460180787, 5660530768491281904, 11379962485541547881, 10809849345758430066, 11587677409377468715] }, { key := "33553591c35e07d8788165246c638307b37b0f522837f5d192778524efbcb6d1", family := 1, baseScore := 19480, ties := [17861271631964304855, 8122504493604679585, 18314044924554156242, 7498463703266124334, 3391635388111775017] }, { key := "3f36bf49ab6cc0ad7edb2a54b22609ce4d9b6d65439f5049762c6289ba52e210", family := 4, baseScore := 19505, ties := [16635933426665611828, 6858093571604301732, 5732091328645710249, 7822549142922163405, 18314702954586983950] }, { key := "41091e0d83d3ca41d10190bc538d303e511a79113c9df9f3edb400e5d7f06806", family := 2, baseScore := 19509, ties := [8911718324786314464, 7812307280058208589, 5167504732806915598, 11449473658666200729, 17221710378744447916] }, { key := "4cfe5f09bcf72872500b1c0604c0e7bceb63f387d74396856c238cab79ccd982", family := 1, baseScore := 19505, ties := [17341774770462319288, 4313188716980430563, 15744894512023544329, 7579211954982347478, 7723141427290801174] }, { key := "57a3367bb9ed42229a83b27586a131a0ba39c68ae2616d7865183b11394fa202", family := 6, baseScore := 18971, ties := [17823677709858021513, 8898656616282283843, 8291955824474563455, 16887769684259994195, 13355909568892680471] }, { key := "5de02c4fe1758e7198e688b25fbbdf2e2653921e3626f0ccbe8b24a3be35c478", family := 1, baseScore := 19509, ties := [14807191708322662213, 17044965354008738285, 18443313728954636047, 10243819765663942441, 3620524776556645995] }, { key := "6dd4b508318bd1750e02227959102f95ccc3e6dcedaca4e3a1b4cece77e0b1ba", family := 6, baseScore := 18963, ties := [4611825008557849227, 12068062198346940845, 9264110086434342255, 11730042552289615760, 17606951110930597123] }, { key := "73d333c33a7c893ef65b0e5fe74093bef5bb51e9c4dcfa47938d7055446fe726", family := 5, baseScore := 19495, ties := [11482589328235147740, 1068453299199746736, 5378424396541192917, 15634196418256437704, 4956110018302537069] }, { key := "7e2bc001d065c188a53be853a0f851fdd13c0f2de4beaf7edf74b99295a21153", family := 7, baseScore := 19446, ties := [7269785910583463666, 5034351993244807247, 4796688542921649101, 8497389830871718492, 3107514905629775783] }, { key := "9151999095e5e261489d580791558f6a716a55ad5515286f1857837d57670554", family := 3, baseScore := 19467, ties := [16278487536480062638, 7069003754947579151, 3365949586702625898, 7167415787254846713, 7074187969969243679] }, { key := "964de7415dc5e4e47c6fdca408a553f6c1d9364360dc1b24c0ea8477c97d2477", family := 3, baseScore := 19536, ties := [14893870574831223063, 17082743386262297389, 12883058327497221215, 10034842100876355881, 4285547786177124656] }, { key := "965372954524542df02c4e6d3edc0b7c5068bd73c2a511dfd2b633b08eac55ce", family := 2, baseScore := 19460, ties := [10602356374792532036, 14633862890172536179, 7996815289223726113, 4714145402830052898, 11799739847749970126] }, { key := "99b406f5b59529ffae97e34bef4410c6d55b6df1ad89d4a1668dc909a8bef2dc", family := 6, baseScore := 18974, ties := [10251213045696955239, 8277559809786887086, 5177563136290298210, 15546223716982519149, 1147826290981145593] }, { key := "a81860939523b8a89c1057eba532b96499612047fc01742df3be9cc579f2bc8b", family := 7, baseScore := 19486, ties := [4983646346911007955, 15991257719540894265, 7392099215831283465, 9351590683087415241, 4891173289025094829] }, { key := "ae7cbfc791101dfe44fd483199848f9de565da63d63433a94f2d7aa700277a98", family := 5, baseScore := 19473, ties := [11916698324925651244, 3779034800305266545, 6723460190554234405, 4996725434995486014, 9123272532919935628] }, { key := "b88f309e3eedc1201be67286e71146a82f3c98b605cd9a98095dfb4a4435eb12", family := 7, baseScore := 19488, ties := [8236809976806246490, 9592656197184993850, 13395775239428778536, 16521712693720081845, 6612592757519420357] }, { key := "bbc1ff8710f17883bab1263fa3a97a43dce6afbeb51ee87298705a13dc97d3fe", family := 4, baseScore := 19507, ties := [9895441269519714204, 10567975818667182412, 2949762867666745447, 15358263284222592413, 7818756811871304356] }, { key := "be48dbf0eab9b1c6cb1b383a4a819ba03b1fbe5def5a2ede1abeff841e86a340", family := 0, baseScore := 18940, ties := [12051271293274815325, 8498763912633731322, 16214678916157904758, 5852676273995598448, 7762158363813604185] }, { key := "beb74d988214ab69ce6d5579b8a135d6b9bb7cfe55ef5f639731f4b5945dfa76", family := 3, baseScore := 19451, ties := [6687728494088923561, 15688533194881422083, 11054250652464361855, 3431282234277072745, 16283540379544306886] }, { key := "c1ec7b3347051f6043ed84e712320056358447de8d23eb2e9bc1537de1767283", family := 2, baseScore := 19467, ties := [13285210797448947710, 14708564226017442511, 5426189561929132630, 9367810302013171095, 11203445840724478819] }, { key := "c2cafaf439159f3bf4ff17d47a0ac33f22866b324b8b44a02c91a4aa8c9365e0", family := 0, baseScore := 18964, ties := [11311766996352523566, 11946356079815518726, 10786483167680738130, 9785448311272348928, 5814422632839180568] }, { key := "d2c17eb8f048b3c3ed3cbde41e95d021928a189d589d7a98e4b23364f500047a", family := 5, baseScore := 19480, ties := [2478731396848945458, 10946844841225976487, 4382384839441706234, 12669902370179852976, 7955262276166890039] }, { key := "efd52e8c0b30256601b60f3dd4e489739da9b0eb1a2dcc086665b01b8b6f4a39", family := 5, baseScore := 19477, ties := [12568675729554285567, 4996633094436695344, 15449578570687309064, 12529300530850918538, 10646814677314777144] }] }
def domain4 : Domain := ⟨context4, [("00249ca0b7a67c15459a63436150df40b37e902ef4c8e982e96771b088efd180", { family := 0, variant := 0, a := (-14), b := (-16) }), ("0285dff171e0f02e9b860d18f00b95b44877bf7a3c73b9c5391421fd99bd0867", { family := 7, variant := 3, a := 16, b := (-16) }), ("06116e73fb137a69f4207ea8915ca755b626c24078922db00e07e5b645eb365c", { family := 1, variant := 0, a := (-12), b := 13 }), ("0aba9c83eefc68880e4a6b53c51c1761b9e77dbf7bb19f640b4ad3a5b8f2d2ea", { family := 6, variant := 3, a := 15, b := (-12) }), ("0cc4d094b87b5f39cc487ac5f4a724ed40998e7f5dfc4745526a09cddd41d53a", { family := 2, variant := 0, a := 11, b := 14 }), ("16af37fa62383c0cb646c247cb5d9fc0535852285252c33b84d8f40bc552344b", { family := 3, variant := 3, a := 6, b := (-5) }), ("1a4227ba1f0a966a22e16bded3af275f2c271d890155c3bd51fc64f197fc3844", { family := 0, variant := 1, a := 1, b := (-14) }), ("2272ec8df233ce2e4d34665f06c6f1a7dd64bfdeb8e3ac274f09ffe23804593e", { family := 4, variant := 3, a := (-7), b := 5 }), ("2e8e78477230e75ccb5c319cf0b76de4d530b01e82ea6a3c18630abecddc5fff", { family := 4, variant := 2, a := (-9), b := (-6) }), ("33553591c35e07d8788165246c638307b37b0f522837f5d192778524efbcb6d1", { family := 1, variant := 1, a := (-10), b := (-6) }), ("3f36bf49ab6cc0ad7edb2a54b22609ce4d9b6d65439f5049762c6289ba52e210", { family := 4, variant := 0, a := 16, b := (-10) }), ("41091e0d83d3ca41d10190bc538d303e511a79113c9df9f3edb400e5d7f06806", { family := 2, variant := 3, a := (-16), b := (-5) }), ("4cfe5f09bcf72872500b1c0604c0e7bceb63f387d74396856c238cab79ccd982", { family := 1, variant := 3, a := 14, b := (-5) }), ("57a3367bb9ed42229a83b27586a131a0ba39c68ae2616d7865183b11394fa202", { family := 6, variant := 1, a := 0, b := 4 }), ("5de02c4fe1758e7198e688b25fbbdf2e2653921e3626f0ccbe8b24a3be35c478", { family := 1, variant := 2, a := (-9), b := (-8) }), ("6dd4b508318bd1750e02227959102f95ccc3e6dcedaca4e3a1b4cece77e0b1ba", { family := 6, variant := 2, a := (-10), b := (-6) }), ("73d333c33a7c893ef65b0e5fe74093bef5bb51e9c4dcfa47938d7055446fe726", { family := 5, variant := 0, a := 2, b := 9 }), ("7e2bc001d065c188a53be853a0f851fdd13c0f2de4beaf7edf74b99295a21153", { family := 7, variant := 0, a := (-11), b := 14 }), ("9151999095e5e261489d580791558f6a716a55ad5515286f1857837d57670554", { family := 3, variant := 1, a := 0, b := 15 }), ("964de7415dc5e4e47c6fdca408a553f6c1d9364360dc1b24c0ea8477c97d2477", { family := 3, variant := 2, a := (-13), b := (-15) }), ("965372954524542df02c4e6d3edc0b7c5068bd73c2a511dfd2b633b08eac55ce", { family := 2, variant := 2, a := 0, b := 10 }), ("99b406f5b59529ffae97e34bef4410c6d55b6df1ad89d4a1668dc909a8bef2dc", { family := 6, variant := 0, a := 1, b := (-5) }), ("a81860939523b8a89c1057eba532b96499612047fc01742df3be9cc579f2bc8b", { family := 7, variant := 1, a := 14, b := (-3) }), ("ae7cbfc791101dfe44fd483199848f9de565da63d63433a94f2d7aa700277a98", { family := 5, variant := 2, a := 6, b := 9 }), ("b88f309e3eedc1201be67286e71146a82f3c98b605cd9a98095dfb4a4435eb12", { family := 7, variant := 2, a := 5, b := 7 }), ("bbc1ff8710f17883bab1263fa3a97a43dce6afbeb51ee87298705a13dc97d3fe", { family := 4, variant := 1, a := 15, b := 15 }), ("be48dbf0eab9b1c6cb1b383a4a819ba03b1fbe5def5a2ede1abeff841e86a340", { family := 0, variant := 3, a := (-12), b := 7 }), ("beb74d988214ab69ce6d5579b8a135d6b9bb7cfe55ef5f639731f4b5945dfa76", { family := 3, variant := 0, a := (-8), b := (-9) }), ("c1ec7b3347051f6043ed84e712320056358447de8d23eb2e9bc1537de1767283", { family := 2, variant := 1, a := (-1), b := 1 }), ("c2cafaf439159f3bf4ff17d47a0ac33f22866b324b8b44a02c91a4aa8c9365e0", { family := 0, variant := 2, a := 10, b := 3 }), ("d2c17eb8f048b3c3ed3cbde41e95d021928a189d589d7a98e4b23364f500047a", { family := 5, variant := 1, a := 8, b := 13 }), ("efd52e8c0b30256601b60f3dd4e489739da9b0eb1a2dcc086665b01b8b6f4a39", { family := 5, variant := 3, a := 10, b := (-12) })]⟩
def contexts4 (_source : State) : Phase17Provenance.Context := context4
-- Identity table is a finite constructor association, not an evaluator history.
def identities4 : List String := ["81fa575052a351b6a3bb244a8cc4d31439de25371ce56783b38d828b6e51204a", "", "", "", "", "", "4e6d4c959a8fc3605734dd8c5e757552fd4d8dacc03e15748e4742b0d74eed2b", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "dc81fe223bfff94e28d90f1ec3b951473b03677d8b98bb52d4e71e181122045b", "", "", "d5f52fa682df0d237799fb069dfd5458a4345785c0d228621db8c13afeaae5eb", "", ""]
def builder4 (prior : List Nat) (index task : Nat) : Offer :=
  constructOffer fixed source1 domain4 (identities4.getD index "")
    prior index task (cumulativeCharges prior)
def evaluator4 : List Nat → Nat → Bool :=
  evaluate fixed contexts4 chargesAt source1 domain4 builder4
def grant4 : Grant := {
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
theorem domain_bound4 : DomainBound source1 domain4 := by
  refine ⟨rfl, ?_, rfl, rfl, ?_, ?_⟩
  · rcases domain_bound1.2.1 with ⟨length, _, offset, keys, rows⟩
    exact ⟨length, by decide, offset, keys, rows⟩
  · intro index
    fin_cases index <;> decide +kernel
  · intro family variant
    fin_cases family <;> fin_cases variant
    · exact ⟨⟨0, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨6, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨29, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨26, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨2, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨9, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨14, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨12, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨4, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨28, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨20, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨11, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨27, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨18, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨19, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨5, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨10, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨25, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨8, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨7, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨16, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨30, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨23, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨31, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨21, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨13, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨15, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨3, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨17, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨22, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨24, by decide⟩, rfl, rfl⟩
    · exact ⟨⟨1, by decide⟩, rfl, rfl⟩
def observations4 : List Phase17Controller.Observation := [⟨19, false⟩, ⟨5, false⟩, ⟨18, false⟩]
def state4_0 : ExecutionState :=
  ⟨⟨32, [], none⟩, []⟩
def state4_1 : ExecutionState :=
  ⟨⟨32, [⟨19, false⟩], none⟩, [.candidate, .vector, .vector]⟩
def state4_2 : ExecutionState :=
  ⟨⟨32, [⟨19, false⟩, ⟨5, false⟩], none⟩, [.candidate, .vector, .vector, .candidate, .vector, .vector]⟩
def state4_3 : ExecutionState :=
  ⟨⟨32, [⟨19, false⟩, ⟨5, false⟩, ⟨18, false⟩], none⟩, [.candidate, .vector, .vector, .candidate, .vector, .vector, .candidate, .vector, .vector]⟩
theorem choice4_0 : canonicalTask fixed source1 (Phase17Provenance.rowAt context4 19).key (rowProgram domain4 19) = none := by decide +kernel
theorem evaluation4_0 (prior : List Nat) : evaluator4 prior 19 = false :=
  no_contract_refused fixed contexts4 chargesAt source1 domain4 builder4 prior 19 choice4_0
theorem step4_0 : authorizedStep grant4 grant4 grant4.binding
    context4 evaluator4 2 state4_0 ⟨19, false⟩ = some state4_1 := by
  apply authorized_step_construct
  · decide +kernel
  · decide +kernel
  · exact (evaluation4_0 []).symm
  · decide +kernel
theorem choice4_1 : canonicalTask fixed source1 (Phase17Provenance.rowAt context4 5).key (rowProgram domain4 5) = none := by decide +kernel
theorem evaluation4_1 (prior : List Nat) : evaluator4 prior 5 = false :=
  no_contract_refused fixed contexts4 chargesAt source1 domain4 builder4 prior 5 choice4_1
theorem step4_1 : authorizedStep grant4 grant4 grant4.binding
    context4 evaluator4 2 state4_1 ⟨5, false⟩ = some state4_2 := by
  apply authorized_step_construct
  · decide +kernel
  · decide +kernel
  · exact (evaluation4_1 [19]).symm
  · decide +kernel
theorem choice4_2 : canonicalTask fixed source1 (Phase17Provenance.rowAt context4 18).key (rowProgram domain4 18) = none := by decide +kernel
theorem evaluation4_2 (prior : List Nat) : evaluator4 prior 18 = false :=
  no_contract_refused fixed contexts4 chargesAt source1 domain4 builder4 prior 18 choice4_2
theorem step4_2 : authorizedStep grant4 grant4 grant4.binding
    context4 evaluator4 2 state4_2 ⟨18, false⟩ = some state4_3 := by
  apply authorized_step_construct
  · decide +kernel
  · decide +kernel
  · exact (evaluation4_2 [19, 5]).symm
  · decide +kernel
theorem case_second_source_resource_stop : authorizedReplay grant4 grant4 grant4.binding
    context4 evaluator4 2 state4_0 observations4 = some state4_3 := by
  have finalAllowed : admissibleExecution grant4 grant4 grant4.binding context4 state4_3 := by decide +kernel
  simp only [observations4, authorizedReplay, step4_0, step4_1, step4_2, Option.bind_some, finalAllowed, if_true]
theorem terminal4 : Phase17Controller.decision context4 state4_3.controller = some (.evaluate 27) := by decide +kernel

theorem first_domain_bound : DomainBound source0 domain0 := domain_bound0
theorem second_domain_bound : DomainBound source1 domain1 := domain_bound1

theorem first_domain_coverage : (producerOrder context0).Nodup ∧
    (producerOrder context0).length = 32 ∧ (producerOrder context0).toFinset = Finset.range 32 :=
  producer_order_spec context0 (domain_shape source0 domain0 first_domain_bound)

theorem second_domain_coverage : (producerOrder context1).Nodup ∧
    (producerOrder context1).length = 32 ∧ (producerOrder context1).toFinset = Finset.range 32 :=
  producer_order_spec context1 (domain_shape source1 domain1 second_domain_bound)

theorem first_source_reference_accepted :
    Accepted fixed contexts0 (chargesAt [] 30) source0 (builder0 [] 30 41) :=
  check_sound fixed contexts0 (chargesAt [] 30) Phase17SecondStep.selected_catalog_complete
    source0 (builder0 [] 30 41) check0_0

theorem second_source_reference_accepted :
    Accepted fixed contexts1 (chargesAt [19, 5, 18, 27, 13, 30, 15] 0) source1
      (builder1 [19, 5, 18, 27, 13, 30, 15] 0 56) :=
  check_sound fixed contexts1 (chargesAt [19, 5, 18, 27, 13, 30, 15] 0)
    Phase17SecondStep.selected_catalog_complete source1
    (builder1 [19, 5, 18, 27, 13, 30, 15] 0 56) check1_7

theorem first_accepted_charges_reserved :
    (builder0 [] 30 41).evidence.charges = state0_1.spent ∧
    (builder0 [] 30 41).update.charges = state0_1.spent ∧
    Phase17Resource.Fits grant0.policy state0_1.spent := by decide +kernel

theorem second_accepted_charges_reserved :
    (builder1 [19, 5, 18, 27, 13, 30, 15] 0 56).evidence.charges = state1_8.spent ∧
    (builder1 [19, 5, 18, 27, 13, 30, 15] 0 56).update.charges = state1_8.spent ∧
    Phase17Resource.Fits grant1.policy state1_8.spent := by decide +kernel

theorem second_source_seven_refusals :
    evaluator1 [] 19 = false ∧ evaluator1 [19] 5 = false ∧
    evaluator1 [19, 5] 18 = false ∧ evaluator1 [19, 5, 18] 27 = false ∧
    evaluator1 [19, 5, 18, 27] 13 = false ∧ evaluator1 [19, 5, 18, 27, 13] 30 = false ∧
    evaluator1 [19, 5, 18, 27, 13, 30] 15 = false :=
  ⟨evaluation1_0 _, evaluation1_1 _, evaluation1_2 _, evaluation1_3 _,
    evaluation1_4 _, evaluation1_5 _, evaluation1_6 _⟩

theorem source_contexts_differ : source0.packageHash ≠ source1.packageHash ∧
    context0.parentPackage ≠ context1.parentPackage ∧ context0.contextHash ≠ context1.contextHash := by
  decide +kernel

theorem first_reference_cost : Phase17Resource.totalCost state0_1.spent = 112 ∧
    Phase17Resource.Fits grant0.policy state0_1.spent := by decide +kernel

theorem second_reference_cost : Phase17Resource.totalCost state1_8.spent = 896 ∧
    Phase17Resource.Fits grant1.policy state1_8.spent := by decide +kernel

theorem resource_denial_no_receipt :
    authorizedStep grant4 grant4 grant4.binding context4 evaluator4 2 state4_3 ⟨27, false⟩ = none :=
  insufficient_allowance_no_receipt grant4 grant4 grant4.binding context4 evaluator4 2
    state4_3 ⟨27, false⟩ (by decide +kernel)

theorem credit_stop_is_not_grammar_exhaustion :
    Phase17Controller.decision context2 state2_4.controller = some .resourceExhausted ∧
      state2_4.controller.observations.length < 32 := ⟨terminal2, by decide⟩

theorem reference_stop_is_not_grammar_exhaustion :
    Phase17Controller.decision context4 state4_3.controller = some (.evaluate 27) ∧
      state4_3.controller.observations.length < 32 := ⟨terminal4, by decide⟩

end Phase17ProducerDomainExamples
