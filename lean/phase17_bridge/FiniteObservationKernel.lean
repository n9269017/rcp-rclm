/- Phase 17Q: a concrete kernel for the finite observations reconstructed from one
   inactive append-only package transition.  This template is appended after the
   unchanged typed/task/provenance/protected/resource templates.

   Its state is an explicit finite observation, not an arbitrary neural machine.
   The Python/physical-to-observation refinement is an external trust boundary.
   The fixed context describes one transaction and supplies no next-turn oracle.
   The declared reference-work tariff is not total physical resource accounting.
   No autonomous accepted step or active promotion is constructed here. -/
namespace Phase17Finite

open RcpRclmFormalCoreV2 RcpRclmFormalCoreV3

abbrev Program := Phase17TaskMeaning.Program
abbrev Image := Phase17LearnedBinding.Image
abbrev ProofObservation := String × String × String

/-- Complete finite projection used by this kernel.  The twelve frozen images
    retain the typed component separation; program contents and task meanings
    remain explicit data rather than a package hash or asserted success bit. -/
structure State where
  frozen : List Image
  keys : List String
  proofs : List ProofObservation
  programs : List (String × Program)
  declared : Finset Nat
  namedFrontier : Finset String
  semantic : Phase17Protected.Observation
  packageHash : String
  root : String
  deriving DecidableEq

/-- Fieldwise equality avoids reducing a proof transport inside a derived
    equality decision when independently represented finite sets are compared. -/
theorem state_ext (s t : State)
    (frozen : s.frozen = t.frozen) (keys : s.keys = t.keys)
    (proofs : s.proofs = t.proofs) (programs : s.programs = t.programs)
    (declared : s.declared = t.declared) (namedFrontier : s.namedFrontier = t.namedFrontier)
    (semantic : s.semantic = t.semantic) (packageHash : s.packageHash = t.packageHash)
    (root : s.root = t.root) : s = t := by
  cases s
  cases t
  simp only [State.mk.injEq]
  exact ⟨frozen, keys, proofs, programs, declared, namedFrontier, semantic, packageHash, root⟩

def ofObservations (root : String) (bound : Phase17LearnedBinding.BoundState)
    (tasks : Phase17TaskMeaning.ObservationState) (declared : Finset Nat)
    (semantic : Phase17Protected.Observation) : State :=
  { frozen := Phase17LearnedBinding.frozenView bound
    keys := bound.package.base
    proofs := tasks.proofs
    programs := tasks.programs
    declared := declared
    namedFrontier := bound.package.capabilityFrontier
    semantic := semantic
    packageHash := bound.packageHash
    root := root }

structure Update where
  key : String
  program : Program
  task : Nat
  taskName : String
  parentPackage : String
  candidatePackage : String
  contextHash : String
  charges : List Phase17Resource.Kind
  deriving DecidableEq

/-- Immutable interpretation, context, and work envelope for ONE transaction.
    In particular, candidate data cannot choose a new task catalog, goal target,
    producer history, root identity, or tariff to make its own checks pass. -/
structure Configuration where
  root : String
  catalog : Nat → Phase17TaskMeaning.Meaning
  taskName : Nat → String
  contract : Phase17Protected.Contract
  context : Phase17Provenance.Context
  policy : Phase17Resource.Policy
  expectedCharges : List Phase17Resource.Kind

structure Evidence where
  root : String
  parentPackage : String
  candidatePackage : String
  contextHash : String
  transcriptHash : String
  proposal : Phase17Provenance.Proposal
  charges : List Phase17Resource.Kind

def taskObservation (s : State) : Phase17TaskMeaning.ObservationState :=
  { proofs := s.proofs, programs := s.programs }

def frontier (cfg : Configuration) (s : State) : Finset Nat :=
  Phase17TaskMeaning.checkedFrontier s.declared cfg.catalog (taskObservation s)

def apply (s : State) (u : Update) : State :=
  { s with
    keys := s.keys ++ [u.key]
    programs := s.programs ++ [(u.key, u.program)]
    declared := insert u.task s.declared
    namedFrontier := insert u.taskName s.namedFrontier
    packageHash := u.candidatePackage }

/-- Candidate-tied inverse of the finite append operation.  It uses the actual
    observed successor and update metadata, not a constant predecessor oracle. -/
def recover (u : Update) (observed : State) : State :=
  { observed with
    keys := observed.keys.dropLast
    programs := observed.programs.dropLast
    declared := observed.declared.erase u.task
    namedFrontier := observed.namedFrontier.erase u.taskName
    packageHash := u.parentPackage }

abbrev Protected := List Image × List ProofObservation × Phase17Protected.Observation

def protectedView (s : State) : Protected := (s.frozen, s.proofs, s.semantic)

noncomputable def protectedValue (s : State) (p : Protected) : ℝ :=
  if protectedView s = p then 1 else 0

noncomputable def distance (s t : State) : ℝ := if s = t then 0 else 1

def admissible (cfg : Configuration) (s : State) : Prop :=
  s.root = cfg.root ∧ s.root ≠ "" ∧ s.packageHash ≠ "" ∧
  s.frozen.length = 12 ∧ s.keys = s.programs.map Prod.fst ∧ s.keys.Nodup ∧
  s.namedFrontier = s.declared.image cfg.taskName ∧ frontier cfg s = s.declared ∧
  Phase17Protected.WellFormed s.semantic ∧ s.semantic.goals = cfg.contract.expectedGoals

def UpdateValid (cfg : Configuration) (s : State) (u : Update) : Prop :=
  u.parentPackage = s.packageHash ∧ u.contextHash = cfg.context.contextHash ∧
  u.key ≠ "" ∧ u.key ∉ s.keys ∧ u.task ∉ s.declared ∧
  u.taskName ∉ s.namedFrontier ∧ u.taskName = cfg.taskName u.task ∧ u.taskName ≠ "" ∧
  u.candidatePackage ≠ s.packageHash ∧ u.candidatePackage ≠ "" ∧
  u.program.family < 8 ∧ u.program.variant < 4

def candidateView (c : RCP.Candidate State Update) : Phase17Provenance.CandidateView :=
  { parentPackage := c.update.parentPackage
    contextHash := c.update.contextHash
    program := c.update.key
    package := c.next.packageHash }

def trustValid (cfg : Configuration) (s : State) (c : RCP.Candidate State Update)
    (e : Evidence) : Prop :=
  e.root = cfg.root ∧ s.root = cfg.root ∧ c.next.root = cfg.root ∧ cfg.root ≠ "" ∧
  e.parentPackage = s.packageHash ∧ e.candidatePackage = c.next.packageHash ∧
  e.contextHash = cfg.context.contextHash ∧ e.transcriptHash = cfg.context.transcriptHash ∧
  cfg.context.parentPackage = s.packageHash ∧ cfg.context.generator ≠ "" ∧
  cfg.context.contextHash ≠ "" ∧ cfg.context.transcriptHash ≠ "" ∧
  Phase17Provenance.ContextValid cfg.context

def resourceValid (cfg : Configuration) (c : RCP.Candidate State Update) (e : Evidence) : Prop :=
  e.charges = c.update.charges ∧ e.charges = cfg.expectedCharges ∧
    Phase17Resource.Fits cfg.policy e.charges

def realityContained (cfg : Configuration) (s : State) (c : RCP.Candidate State Update)
    (e : Evidence) : Prop :=
  c.next = apply s c.update ∧ UpdateValid cfg s c.update ∧
  Phase17Provenance.CandidateMatches cfg.context e.proposal (candidateView c) ∧
  e.charges = cfg.expectedCharges

inductive ResidualIndex where
  | total
  | dimension (index : Phase17Resource.Dimension)

noncomputable def residual (cfg : Configuration) (e : Evidence) : ResidualIndex → ℝ
  | .total => (Phase17Resource.totalCost e.charges : ℝ) - (cfg.policy.costLimit : ℝ)
  | .dimension i => (Phase17Resource.counter e.charges i : ℝ) - (cfg.policy.limits i : ℝ)

private def emptyState : State :=
  ⟨[], [], [], [], ∅, ∅, ⟨[], [], []⟩, "", ""⟩

private def emptyUpdate : Update := ⟨"", ⟨0, 0, 0, 0⟩, 0, "", "", "", "", []⟩

private def emptyEvidence : Evidence :=
  ⟨"", "", "", "", "", ⟨"", "", "", "", [], [], "", ""⟩, []⟩

/-- This is an actual RCP kernel.  The protected observation indicator,
    per-dimension work residuals, and rejectable structural transition relation
    satisfy the immutable root's three anti-vacuity requirements. -/
noncomputable def base (cfg : Configuration) :
    RCP.Kernel State Update Evidence Protected ResidualIndex where
  apply := apply
  admissible := admissible cfg
  protectedInvariant := admissible cfg
  protectedValue := protectedValue
  protectedValue_nonconstant := by
    let changed : State := { emptyState with semantic := ⟨[], [], [[1]]⟩ }
    refine ⟨emptyState, protectedView emptyState, changed, protectedView emptyState, ?_⟩
    norm_num [protectedValue, protectedView, emptyState, changed]
  transportProtected := fun _ _ p => p
  lossBudget := fun _ _ => 0
  lossBudget_nonnegative := by intros; exact le_rfl
  stateDistance := distance
  stateDistance_nonnegative := by intros; unfold distance; split <;> norm_num
  recover := fun _ c observed => recover c.update observed
  recoveryBudget := fun _ _ => 0
  recoveryBudget_nonnegative := by intros; exact le_rfl
  progress := fun s => ((frontier cfg s).card : ℝ)
  strictWitness := fun s c _ => c.update.task ∉ frontier cfg s ∧ c.update.task ∈ frontier cfg c.next
  residual := fun _ _ e i => residual cfg e i
  residual_nonconstant := by
    let c : RCP.Candidate State Update := ⟨emptyUpdate, emptyState⟩
    refine ⟨emptyState, c, emptyEvidence, emptyState, c,
      { emptyEvidence with charges := [.candidate] }, .total, ?_⟩
    norm_num [residual, emptyEvidence, Phase17Resource.totalCost,
      Phase17Resource.unitCost]
    linarith
  trustValid := trustValid cfg
  resourceValid := fun _ c e => resourceValid cfg c e
  realityContained := realityContained cfg
  realityContained_not_universal := by
    refine ⟨emptyState, ⟨emptyUpdate, emptyState⟩, emptyEvidence, ?_⟩
    intro h
    have invalid := h.2.1.2.2.1
    exact invalid rfl

theorem protected_view_preserved (s : State) (u : Update) :
    protectedView (apply s u) = protectedView s := rfl

theorem exact_recovery (s : State) (u : Update)
    (parent : u.parentPackage = s.packageHash)
    (freshTask : u.task ∉ s.declared) (freshName : u.taskName ∉ s.namedFrontier) :
    recover u (apply s u) = s := by
  simp [recover, apply, freshTask, freshName, parent]

theorem residuals_nonpositive (cfg : Configuration) (e : Evidence)
    (fits : Phase17Resource.Fits cfg.policy e.charges) :
    ∀ i, residual cfg e i ≤ 0 := by
  intro i
  cases i with
  | total => exact sub_nonpos.mpr (by exact_mod_cast fits.1)
  | dimension i => exact sub_nonpos.mpr (by exact_mod_cast fits.2 i)

/-- Every learned field is supplied here; no unspecified compatible kernel is
    an argument.  Proposal authority is restricted to the fixed current parent.
    A new transaction requires a newly authenticated context, not reuse of this
    context as an implicit successor-produced history. -/
noncomputable def learned (cfg : Configuration) :
    Learned.FrontierKernel (Task := Nat) (Generator := String)
      (Proposal := Phase17Provenance.Proposal) (PackageHash := String) (base cfg) where
  frontier := frontier cfg
  solves := fun s t => (cfg.catalog t).holds (taskObservation s)
  frontierSound := by
    intro s t h
    exact Phase17TaskMeaning.checked_frontier_sound s.declared cfg.catalog (taskObservation s) h
  activeGenerator := fun _ => cfg.context.generator
  activePackageHash := fun s => s.packageHash
  generatorBound := fun s g => g = cfg.context.generator ∧
    cfg.context.parentPackage = s.packageHash ∧ Phase17Provenance.ContextValid cfg.context
  proposalProducedBy := fun g s p => g = cfg.context.generator ∧
    cfg.context.parentPackage = s.packageHash ∧ Phase17Provenance.Produced cfg.context p
  proposalBindsCandidate := fun s p c => cfg.context.parentPackage = s.packageHash ∧
    Phase17Provenance.CandidateMatches cfg.context p (candidateView c)
  packageHashBound := fun s g hash => g = cfg.context.generator ∧ hash = s.packageHash ∧
    cfg.context.parentPackage = s.packageHash ∧ Phase17Provenance.ContextValid cfg.context
  goalDrift := fun s c => Phase17Protected.goalDistance s.semantic.goals c.next.semantic.goals
  goalDriftBudget := fun _ _ => 0
  resourceUsed := fun _ c => Phase17Resource.totalCost c.update.charges
  resourceBudget := fun _ _ => cfg.policy.costLimit
  informationValue := fun s => Phase17Protected.informationValue cfg.contract s.semantic
  informationBudget := fun _ _ => 0
  informationBudget_nonnegative := by intros; exact le_rfl

/-- Finite, independently checkable conditions for one observation transition.
    These are propositions over the supplied literals, not a caller acceptance
    flag, physical-execution assertion, or a remaining abstract base kernel. -/
structure Facts (cfg : Configuration) (s : State) (c : RCP.Candidate State Update)
    (e : Evidence) : Prop where
  beforeAdmissible : admissible cfg s
  afterAdmissible : admissible cfg c.next
  typed : c.next = apply s c.update
  updateValid : UpdateValid cfg s c.update
  trusted : trustValid cfg s c e
  resources : resourceValid cfg c e
  matched : Phase17Provenance.CandidateMatches cfg.context e.proposal (candidateView c)
  expansion : frontier cfg s ⊆ frontier cfg c.next ∧
    (frontier cfg s).card < (frontier cfg c.next).card

theorem base_step (cfg : Configuration) (s : State) (c : RCP.Candidate State Update)
    (e : Evidence) (facts : Facts cfg s c e) :
    RCP.StepObligations (base cfg) s c e := by
  rcases facts.updateValid with ⟨parent, _, _, _, freshTask, freshName, _⟩
  constructor
  · exact facts.typed
  · exact residuals_nonpositive cfg e facts.resources.2.2
  · intro p
    change protectedValue s p ≤ protectedValue c.next p + 0
    rw [facts.typed]
    change protectedValue s p ≤ protectedValue s p + 0
    simpa only [add_zero] using (le_refl (protectedValue s p))
  · change distance (recover c.update c.next) s ≤ 0
    rw [facts.typed, exact_recovery s c.update parent freshTask freshName]
    simp [distance]
  · exact facts.afterAdmissible
  · change ((frontier cfg s).card : ℝ) ≤ ((frontier cfg c.next).card : ℝ)
    exact_mod_cast facts.expansion.2.le
  · intro _
    change ((frontier cfg s).card : ℝ) < ((frontier cfg c.next).card : ℝ)
    exact_mod_cast facts.expansion.2
  · exact facts.trusted
  · exact facts.resources
  · exact ⟨facts.typed, facts.updateValid, facts.matched, facts.resources.2.1⟩
  · exact facts.afterAdmissible

def packet (cfg : Configuration) (s : State) (e : Evidence) :
    Learned.CertificatePacket Evidence Nat String Phase17Provenance.Proposal String :=
  { base := e
    protectedFrontier := frontier cfg s
    generator := cfg.context.generator
    proposal := e.proposal
    generatorPackageHash := s.packageHash }

/-- Fully instantiated base and learned obligations for the stated finite model.
    Applying this theorem to measured literals still does not prove their physical
    refinement, arbitrary neural semantics, autonomous continuation, or promotion. -/
theorem accepted (cfg : Configuration) (s : State) (c : RCP.Candidate State Update)
    (e : Evidence) (facts : Facts cfg s c e) :
    Learned.LearnedAcceptedStep (learned cfg) s c (packet cfg s e) := by
  rcases facts.trusted with ⟨_, _, _, _, _, _, _, _, parent, _, _, _, contextValid⟩
  have produced : Phase17Provenance.Produced cfg.context e.proposal := facts.matched.1
  refine { baseObligations := base_step cfg s c e facts, learnedObligations := ?_ }
  constructor
  · intro t h; exact h
  · exact facts.expansion.1
  · exact facts.expansion
  · rfl
  · exact ⟨rfl, parent, contextValid⟩
  · exact ⟨rfl, parent, produced⟩
  · exact ⟨parent, facts.matched⟩
  · rfl
  · exact ⟨rfl, rfl, parent, contextValid⟩
  · change Phase17Protected.goalDistance s.semantic.goals c.next.semantic.goals ≤ 0
    rw [facts.typed]
    exact (Phase17Protected.goal_distance_self s.semantic.goals).le
  · change Phase17Resource.totalCost c.update.charges ≤ cfg.policy.costLimit
    rw [← facts.resources.1]
    exact facts.resources.2.2.1
  · change Phase17Protected.informationValue cfg.contract c.next.semantic ≤
      Phase17Protected.informationValue cfg.contract s.semantic + 0
    rw [facts.typed]
    exact le_of_eq (add_zero _).symm

theorem accepted_protected_frontier (cfg : Configuration) (s : State)
    (c : RCP.Candidate State Update) (e : Evidence) (facts : Facts cfg s c e) :
    (packet cfg s e).protectedFrontier = (learned cfg).frontier s ∧
    (learned cfg).frontier s ⊆ (learned cfg).frontier c.next ∧
    ((learned cfg).frontier s).card < ((learned cfg).frontier c.next).card :=
  ⟨rfl, facts.expansion⟩

theorem accepted_all_resource_dimensions (cfg : Configuration) (s : State)
    (c : RCP.Candidate State Update) (e : Evidence) (facts : Facts cfg s c e) :
    e.charges = c.update.charges ∧ e.charges = cfg.expectedCharges ∧
      Phase17Resource.Fits cfg.policy e.charges :=
  facts.resources

end Phase17Finite
