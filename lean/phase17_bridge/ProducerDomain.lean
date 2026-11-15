import TruthfulSuccessor

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
