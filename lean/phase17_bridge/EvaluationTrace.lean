/- Phase 17Z: the selected evaluator computation and producer verdict prefix.
   Programs and the opening come from the imported V/Y/Q certificates. Every
   target, inherited and attempted-candidate probe is evaluated by the unchanged
   Q integer semantics. JSON image equations bind supplied finite records to
   those values. Physical capture/execution, response and journal digest
   authenticity, fresh challenge generation, and general Python equivalence
   remain external. The selected tariff is reference work, not physical cost. -/
namespace Phase17Evaluation

open Phase17Routing

abbrev Vector := List Int
abbrev Matrix := List Vector
abbrev Program := Phase17TaskMeaning.Program
abbrev Opening := Phase17Objective.Opening
abbrev Descriptor := Phase17Metadata.Descriptor
abbrev Entry := String × Program
abbrev DescriptorEntry := String × Descriptor

def outputs (opening : Opening) (program : Program) : Matrix :=
  opening.probes.map (Phase17TaskMeaning.execute program)

def targets (opening : Opening) : Matrix := outputs opening opening.program

def programMatches (opening : Opening) (program : Program) : Bool :=
  decide (program.family = opening.program.family ∧ outputs opening program = targets opening)

def predecessorPass (opening : Opening) (inherited : List Entry) : Bool :=
  inherited.any (fun entry => programMatches opening entry.2)

def nontrivial (opening : Opening) : Bool := decide (targets opening ≠ opening.probes)

def passes (opening : Opening) (inherited : List Entry) (program : Program) : Bool :=
  nontrivial opening && !predecessorPass opening inherited && programMatches opening program

def probeMatches (actual expected : Matrix) : List Bool :=
  (actual.zip expected).map (fun pair => decide (pair.1 = pair.2))

def firstMismatch (actual expected : Matrix) : Option Nat :=
  ((probeMatches actual expected).zipIdx.find? (fun pair => !pair.1)).map Prod.snd

def verdict (passed : Bool) : String := if passed then "candidate_passed" else "reject"

def reasons (passed : Bool) : List String :=
  if passed then [] else ["bounded_challenge_rejected"]

structure Decision where
  nontrivial : Bool
  predecessorPass : Bool
  familyMatches : Bool
  probeMatches : List Bool
  firstMismatch : Option Nat
  candidatePass : Bool
  passed : Bool
  verdict : String
  reasons : List String
  deriving DecidableEq

def decision (opening : Opening) (inherited : List Entry) (program : Program) : Decision :=
  { nontrivial := nontrivial opening
    predecessorPass := predecessorPass opening inherited
    familyMatches := decide (program.family = opening.program.family)
    probeMatches := probeMatches (outputs opening program) (targets opening)
    firstMismatch := firstMismatch (outputs opening program) (targets opening)
    candidatePass := programMatches opening program
    passed := passes opening inherited program
    verdict := verdict (passes opening inherited program)
    reasons := reasons (passes opening inherited program) }

def Accepts (opening : Opening) (inherited : List Entry) (program : Program) : Prop :=
  targets opening ≠ opening.probes ∧ predecessorPass opening inherited = false ∧
    program.family = opening.program.family ∧ outputs opening program = targets opening

theorem evaluation_sound (opening : Opening) (inherited : List Entry) (program : Program) :
    passes opening inherited program = true ↔ Accepts opening inherited program := by
  simp [passes, nontrivial, programMatches, Accepts, Bool.and_eq_true, and_assoc]

theorem trivial_target_rejected (opening : Opening) (inherited : List Entry) (program : Program)
    (trivial : targets opening = opening.probes) : passes opening inherited program = false := by
  simp [passes, nontrivial, trivial]

theorem inherited_solution_rejected (opening : Opening) (inherited : List Entry)
    (program : Program) (solved : predecessorPass opening inherited = true) :
    passes opening inherited program = false := by
  simp [passes, solved]

theorem accepted_has_task_meaning (opening : Opening) (inherited : List Entry)
    (key : String) (program : Program) (accepted : passes opening inherited program = true) :
    (Phase17TaskMeaning.vectorMeaning (Phase17Objective.openingContract opening)).holds
      { proofs := [], programs := [(key, program)] } := by
  have checked := (evaluation_sound opening inherited program).mp accepted
  exact ⟨(key, program), by simp, checked.2.2.1, Or.inl rfl, checked.2.2.2⟩

theorem predecessor_check (opening : Opening) (inherited : List Entry) :
    (Phase17TaskMeaning.vectorMeaning (Phase17Objective.openingContract opening)).check
      { proofs := [], programs := inherited } = predecessorPass opening inherited := by
  simp [Phase17TaskMeaning.vectorMeaning, Phase17Objective.openingContract,
    predecessorPass, programMatches, outputs, targets]

def semanticEntries (entries : List DescriptorEntry) : List Entry :=
  entries.map (fun entry => (entry.1, Phase17Metadata.semanticProgram entry.2))

/-- Selection never defaults a missing index to another program. -/
def selectPrograms (all : List DescriptorEntry) (choices : List Nat) :
    Option (List DescriptorEntry) := choices.mapM (fun index => all[index]?)

def choiceKeys (context : Phase17Provenance.Context) (choices : List Nat) : List String :=
  choices.map (fun index => (Phase17Provenance.rowAt context index).key)

def derivedVerdicts (opening : Opening) (inherited candidates : List Entry) : List Bool :=
  candidates.map (fun entry => passes opening inherited entry.2)

def PrefixBound (opening : Opening) (inherited candidates : List Entry)
    (context : Phase17Provenance.Context) (proposal : Phase17Provenance.Proposal) : Prop :=
  Phase17Provenance.Produced context proposal ∧
    candidates.map Prod.fst = choiceKeys context proposal.choices ∧
    derivedVerdicts opening inherited candidates = proposal.verdicts

def vectorValue (values : Vector) : Value := .array (values.map Value.integer)

structure WorkView where
  identity : String
  kind : Phase17Resource.Kind
  input : Value
  output : Value
  deriving DecidableEq

structure WorkImage where
  identity : String
  kind : Phase17Resource.Kind
  inputImage : List Nat
  outputImage : List Nat

def WorkChecked (image : WorkImage) (expected : WorkView) : Prop :=
  image.identity = expected.identity ∧ image.kind = expected.kind ∧
    Phase17Json.decode image.inputImage = some expected.input ∧
    Phase17Json.decode image.outputImage = some expected.output

instance (image : WorkImage) (expected : WorkView) : Decidable (WorkChecked image expected) :=
  inferInstanceAs (Decidable (_ ∧ _ ∧ _ ∧ _))

def targetWork (opening : Opening) (probe : Vector) (index : Nat) : WorkView :=
  { identity := "target:" ++ toString index, kind := .vector
    input := .object [
      ("parameters", .array [
        .string (Phase17Metadata.families.getD opening.program.family ""),
        Phase17Preimages.natValue opening.program.variant,
        .integer opening.program.a, .integer opening.program.b]),
      ("role", .string "target"), ("vector", vectorValue probe)]
    output := vectorValue (Phase17TaskMeaning.execute opening.program probe) }

def inheritedWork (entry : DescriptorEntry) (programIndex : Nat)
    (probe : Vector) (probeIndex : Nat) : WorkView :=
  { identity := "inherited:" ++ toString programIndex ++ ":" ++ toString probeIndex
    kind := .vector
    input := .object [("program", Phase17Preimages.descriptorValue entry.2),
      ("role", .string "inherited"), ("vector", vectorValue probe)]
    output := vectorValue (Phase17TaskMeaning.execute (Phase17Metadata.semanticProgram entry.2) probe) }

/-- The admission result carries the retained raw-descriptor digest. Its hash
    computation is explicitly not established by this evaluator module. -/
def candidateAdmission (entry : DescriptorEntry) (index : Nat) (rawDigest : String) : WorkView :=
  { identity := "candidate:" ++ toString index, kind := .candidate
    input := .object [("program", Phase17Preimages.descriptorValue entry.2)]
    output := .object [("program_sha256", .string rawDigest)] }

def candidateWork (entry : DescriptorEntry) (programIndex : Nat)
    (probe : Vector) (probeIndex : Nat) : WorkView :=
  { identity := "candidate:" ++ toString programIndex ++ ":probe:" ++ toString probeIndex
    kind := .vector
    input := .object [("program", Phase17Preimages.descriptorValue entry.2),
      ("role", .string "candidate"), ("vector", vectorValue probe)]
    output := vectorValue (Phase17TaskMeaning.execute (Phase17Metadata.semanticProgram entry.2) probe) }

def workViews (opening : Opening) (inherited candidates : List DescriptorEntry)
    (admissionDigests : List String) : List WorkView :=
  opening.probes.zipIdx.map (fun pair => targetWork opening pair.1 pair.2) ++
  inherited.zipIdx.flatMap (fun entry => opening.probes.zipIdx.map
    (fun probe => inheritedWork entry.1 entry.2 probe.1 probe.2)) ++
  candidates.zipIdx.flatMap (fun entry =>
    [candidateAdmission entry.1 entry.2 (admissionDigests.getD entry.2 "")] ++
    opening.probes.zipIdx.map (fun probe => candidateWork entry.1 entry.2 probe.1 probe.2))

structure ResponseMetadata where
  artifactHash : String
  candidateFreezeHash : String
  evaluationHash : String
  deriving DecidableEq

def responseClaims : Value := .object [
  ("egc0_started", .boolean false), ("fresh_lean_verification", .boolean false),
  ("full_frontier_recertified", .boolean false), ("gate_e_closed", .boolean false),
  ("os_security_sandbox", .boolean false), ("phase17_exit_closed", .boolean false),
  ("phase18_independent_replay", .boolean false), ("promotion_authorized", .boolean false)]

/-- All fields of the retained evaluator payload are compared. The three
    opaque metadata digests are supplied identities, not new digest proofs. -/
def responseValue (metadata : ResponseMetadata) (index : Nat) (key challenge state : String)
    (result : Decision) : Value := .object [
  ("artifact_hash", .string metadata.artifactHash),
  ("candidate_freeze_hash", .string metadata.candidateFreezeHash),
  ("challenge_commitment_hash", .string challenge), ("claims", responseClaims),
  ("evaluation_hash", .string metadata.evaluationHash),
  ("evaluation_index", Phase17Preimages.natValue index),
  ("event", .string "candidate_evaluated"), ("predecessor_state_hash", .string state),
  ("program_hash", .string key), ("reason_codes", .array (result.reasons.map Value.string)),
  ("verdict", .string result.verdict)]

end Phase17Evaluation
