import Phase17YDependency

set_option Elab.async false

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

namespace Phase17Evaluation
open Phase17Routing RcpRclmFormalCoreV2 RcpRclmFormalCoreV3
set_option maxRecDepth 32768
set_option maxHeartbeats 64000000
-- Fresh Z packet SHA256: db767e3f3134dc3a021629eda42ba2214426b1f072e28ebe9cc8b24dc759553f
noncomputable def opening : Opening := Phase17Objective.opening
noncomputable def inheritedDescriptors : List DescriptorEntry := Phase17Metadata.beforeRegistry.inherited
noncomputable def inherited : List Entry := semanticEntries inheritedDescriptors
noncomputable def allDescriptors : List DescriptorEntry := (Phase17Metadata.candidateImages.map Prod.fst).zip Phase17Metadata.candidateDescriptors
noncomputable def choices : List Nat := [21, 28, 1, 29, 20, 5, 22, 7, 24]
noncomputable def inheritedWorkOrder : List Nat := [4, 0, 1, 3, 6, 7, 5, 2]
noncomputable def emptyDescriptor : Descriptor := { promotionIndex := 0, family := 8, variant := 0, generation := 0, a := 0, b := 0, nonce := "" }
noncomputable def inheritedDescriptor0 : DescriptorEntry := inheritedDescriptors.getD 0 ("", emptyDescriptor)
noncomputable def inheritedDescriptor1 : DescriptorEntry := inheritedDescriptors.getD 1 ("", emptyDescriptor)
noncomputable def inheritedDescriptor2 : DescriptorEntry := inheritedDescriptors.getD 2 ("", emptyDescriptor)
noncomputable def inheritedDescriptor3 : DescriptorEntry := inheritedDescriptors.getD 3 ("", emptyDescriptor)
noncomputable def inheritedDescriptor4 : DescriptorEntry := inheritedDescriptors.getD 4 ("", emptyDescriptor)
noncomputable def inheritedDescriptor5 : DescriptorEntry := inheritedDescriptors.getD 5 ("", emptyDescriptor)
noncomputable def inheritedDescriptor6 : DescriptorEntry := inheritedDescriptors.getD 6 ("", emptyDescriptor)
noncomputable def inheritedDescriptor7 : DescriptorEntry := inheritedDescriptors.getD 7 ("", emptyDescriptor)
noncomputable def workInherited : List DescriptorEntry := [inheritedDescriptor4, inheritedDescriptor0, inheritedDescriptor1, inheritedDescriptor3, inheritedDescriptor6, inheritedDescriptor7, inheritedDescriptor5, inheritedDescriptor2]
noncomputable def candidateDescriptor0 : DescriptorEntry := ("836a08670cdfdcb082f55c64677c8eaca60a62d0005749e54e72eb67f94554c0", Phase17Metadata.candidateDescriptor21)
noncomputable def candidateProgram0 : Program := Phase17Metadata.semanticProgram candidateDescriptor0.2
noncomputable def candidateDescriptor1 : DescriptorEntry := ("df564cb25de35976dfcbef5e28404498aafd1fce538d0a8aa0e454cf96b11b59", Phase17Metadata.candidateDescriptor28)
noncomputable def candidateProgram1 : Program := Phase17Metadata.semanticProgram candidateDescriptor1.2
noncomputable def candidateDescriptor2 : DescriptorEntry := ("0e14e91e830ffbf45bf7393807a5aade7d3ee8687c812c947e3cc2531cbf63ac", Phase17Metadata.candidateDescriptor1)
noncomputable def candidateProgram2 : Program := Phase17Metadata.semanticProgram candidateDescriptor2.2
noncomputable def candidateDescriptor3 : DescriptorEntry := ("e2654af87c885cf417002f13400f5bef1ac23eae87fd7b9fd479aae38f443d21", Phase17Metadata.candidateDescriptor29)
noncomputable def candidateProgram3 : Program := Phase17Metadata.semanticProgram candidateDescriptor3.2
noncomputable def candidateDescriptor4 : DescriptorEntry := ("7ec7d557c116962ac4a13ef48d12e24f0cb56c5262bae03a84c40d88cbc54d7d", Phase17Metadata.candidateDescriptor20)
noncomputable def candidateProgram4 : Program := Phase17Metadata.semanticProgram candidateDescriptor4.2
noncomputable def candidateDescriptor5 : DescriptorEntry := ("3c53b375ed7d796a6ead3f57edff0ca2bec48cd0d82d3f00e94891e20f67cf37", Phase17Metadata.candidateDescriptor5)
noncomputable def candidateProgram5 : Program := Phase17Metadata.semanticProgram candidateDescriptor5.2
noncomputable def candidateDescriptor6 : DescriptorEntry := ("9862ef65bf4a9113a26f1734ad6ec98e0640eb6656cb1a4334972a2f9be1c6ac", Phase17Metadata.candidateDescriptor22)
noncomputable def candidateProgram6 : Program := Phase17Metadata.semanticProgram candidateDescriptor6.2
noncomputable def candidateDescriptor7 : DescriptorEntry := ("4022426ee83c2c3f99e3575db0b0dfdb2ee9c21d84c0dcd4bd16beddc79e9f1e", Phase17Metadata.candidateDescriptor7)
noncomputable def candidateProgram7 : Program := Phase17Metadata.semanticProgram candidateDescriptor7.2
noncomputable def candidateDescriptor8 : DescriptorEntry := ("a4f37fb8f2f7d3a90829340f2f02b2f19dbc5dfa5caf7a7633e9092837265c0e", Phase17Metadata.candidateDescriptor24)
noncomputable def candidateProgram8 : Program := Phase17Metadata.semanticProgram candidateDescriptor8.2
noncomputable def candidateDescriptors : List DescriptorEntry := [candidateDescriptor0, candidateDescriptor1, candidateDescriptor2, candidateDescriptor3, candidateDescriptor4, candidateDescriptor5, candidateDescriptor6, candidateDescriptor7, candidateDescriptor8]
noncomputable def candidates : List Entry := semanticEntries candidateDescriptors
noncomputable def expectedTargets : Matrix := [[(7), (4), (-2), (-26)], [(-10), (-9), (-8), (-10)], [(15), (32), (24), (-9)], [(-13), (-10), (-12), (-7)], [(-21), (41), (-42), (-23)], [(-18), (20), (-42), (-1)], [(3), (41), (-42), (-25)], [(4), (27), (-58), (9)]]
noncomputable def inheritedOutput0 : Matrix := [[(11), (-24), (-3), (6)], [(-6), (-37), (-12), (22)], [(19), (4), (36), (23)], [(-9), (-38), (-18), (25)], [(-17), (13), (-63), (9)], [(-14), (-8), (-63), (31)], [(7), (13), (-63), (7)], [(8), (-1), (-87), (41)]]
noncomputable def inheritedOutput1 : Matrix := [[(7), (22), (38), (55)], [(3), (18), (34), (51)], [(45), (60), (76), (93)], [(1), (16), (32), (49)], [(-38), (-23), (-7), (10)], [(-13), (2), (18), (35)], [(-16), (-1), (15), (32)], [(11), (26), (42), (59)]]
noncomputable def inheritedOutput2 : Matrix := [[(31), (-26), (-3), (42)], [(30), (-58), (-6), (56)], [(-2), (56), (10), (-7)], [(30), (-64), (-8), (59)], [(-14), (8), (-23), (-45)], [(10), (-34), (-23), (25)], [(10), (8), (-23), (1)], [(33), (-36), (-31), (81)]]
noncomputable def inheritedOutput3 : Matrix := [[(106), (-42), (6), (-14)], [(102), (-106), (-6), (50)], [(-26), (122), (58), (54)], [(102), (-118), (-14), (62)], [(-74), (26), (-74), (-2)], [(22), (-58), (-74), (86)], [(22), (26), (-74), (-10)], [(114), (-62), (-106), (126)]]
noncomputable def inheritedOutput4 : Matrix := [[(-16), (9), (-33), (-26)], [(0), (8), (-49), (-29)], [(1), (-24), (8), (-13)], [(3), (8), (-52), (-31)], [(-13), (-36), (-16), (-46)], [(9), (-12), (-37), (-46)], [(-15), (-12), (-16), (-46)], [(19), (11), (-38), (-54)]]
noncomputable def inheritedOutput5 : Matrix := [[(-37), (-30), (-25), (0)], [(-53), (-28), (-14), (-1)], [(-33), (-13), (-12), (4)], [(-56), (-30), (-11), (-1)], [(-45), (-45), (-27), (-20)], [(-45), (-41), (-21), (-5)], [(-45), (-29), (-21), (-20)], [(-53), (-42), (2), (5)]]
noncomputable def inheritedOutput6 : Matrix := [[(-6), (-13), (-6), (-13)], [(10), (-29), (10), (-29)], [(11), (28), (11), (28)], [(13), (-32), (13), (-32)], [(-3), (4), (-3), (4)], [(19), (-17), (19), (-17)], [(-5), (4), (-5), (4)], [(29), (-18), (29), (-18)]]
noncomputable def inheritedOutput7 : Matrix := [[(9), (-13), (-1), (-6)], [(8), (-29), (-4), (10)], [(-24), (28), (12), (11)], [(8), (-32), (-6), (13)], [(-36), (4), (-21), (-3)], [(-12), (-17), (-21), (19)], [(-12), (4), (-21), (-5)], [(11), (-18), (-29), (29)]]
noncomputable def expectedInherited : List Matrix := [inheritedOutput0, inheritedOutput1, inheritedOutput2, inheritedOutput3, inheritedOutput4, inheritedOutput5, inheritedOutput6, inheritedOutput7]
noncomputable def candidateOutput0 : Matrix := [[(75), (-36), (0), (-15)], [(72), (-84), (-9), (33)], [(-24), (87), (39), (36)], [(72), (-93), (-15), (42)], [(-60), (15), (-60), (-6)], [(12), (-48), (-60), (60)], [(12), (15), (-60), (-12)], [(81), (-51), (-84), (90)]]
noncomputable def candidateOutput1 : Matrix := [[(55), (18), (30), (25)], [(54), (2), (27), (41)], [(22), (59), (43), (42)], [(54), (-1), (25), (44)], [(10), (35), (10), (28)], [(34), (14), (10), (50)], [(34), (35), (10), (26)], [(57), (13), (2), (60)]]
noncomputable def candidateOutput2 : Matrix := [[(58), (-16), (8), (-2)], [(56), (-48), (2), (30)], [(-8), (66), (34), (32)], [(56), (-54), (-2), (36)], [(-32), (18), (-32), (4)], [(16), (-24), (-32), (48)], [(16), (18), (-32), (0)], [(62), (-26), (-48), (68)]]
noncomputable def candidateOutput3 : Matrix := [[(79), (-69), (-21), (-41)], [(75), (-133), (-33), (23)], [(-53), (95), (31), (27)], [(75), (-145), (-41), (35)], [(-101), (-1), (-101), (-29)], [(-5), (-85), (-101), (59)], [(-5), (-1), (-101), (-37)], [(87), (-89), (-133), (99)]]
noncomputable def candidateOutput4 : Matrix := [[(-13), (-13), (-13), (-13)], [(-29), (-29), (-29), (-29)], [(28), (28), (28), (28)], [(-32), (-32), (-32), (-32)], [(4), (4), (4), (4)], [(-17), (-17), (-17), (-17)], [(4), (4), (4), (4)], [(-18), (-18), (-18), (-18)]]
noncomputable def candidateOutput5 : Matrix := [[(-25), (-1), (-6), (24)], [(-41), (-4), (10), (23)], [(16), (12), (11), (-9)], [(-44), (-6), (13), (23)], [(-8), (-21), (-3), (-21)], [(-29), (-21), (19), (3)], [(-8), (-21), (-5), (3)], [(-30), (-29), (29), (26)]]
noncomputable def candidateOutput6 : Matrix := [[(19), (-39), (-1), (66)], [(18), (-87), (-4), (79)], [(-14), (84), (12), (-16)], [(18), (-96), (-6), (82)], [(-26), (12), (-21), (-66)], [(-2), (-51), (-21), (28)], [(-2), (12), (-21), (4)], [(21), (-54), (-29), (107)]]
noncomputable def candidateOutput7 : Matrix := [[(1), (24), (-13), (-1)], [(17), (23), (-29), (-4)], [(18), (-9), (28), (12)], [(20), (23), (-32), (-6)], [(4), (-21), (4), (-21)], [(26), (3), (-17), (-21)], [(2), (3), (4), (-21)], [(36), (26), (-18), (-29)]]
noncomputable def candidateOutput8 : Matrix := [[(7), (4), (-2), (-26)], [(-10), (-9), (-8), (-10)], [(15), (32), (24), (-9)], [(-13), (-10), (-12), (-7)], [(-21), (41), (-42), (-23)], [(-18), (20), (-42), (-1)], [(3), (41), (-42), (-25)], [(4), (27), (-58), (9)]]
noncomputable def expectedCandidates : List Matrix := [candidateOutput0, candidateOutput1, candidateOutput2, candidateOutput3, candidateOutput4, candidateOutput5, candidateOutput6, candidateOutput7, candidateOutput8]
noncomputable def expectedDecision0 : Decision := { nontrivial := true, predecessorPass := false, familyMatches := false, probeMatches := [false, false, false, false, false, false, false, false], firstMismatch := some 0, candidatePass := false, passed := false, verdict := "reject", reasons := ["bounded_challenge_rejected"] }
noncomputable def responseMetadata0 : ResponseMetadata := { artifactHash := "e065209a2f56d71b9f4f61aa5bab80749d677ef7a3339ff9e3be65b5524b67be", candidateFreezeHash := "778cb73e1e5832ff1b1a027a2a35dd284ec1dc4b8f6a9eb06d9929900ce33a83", evaluationHash := "776d9faf504502eb4ec23306d766d9feeb3c4d8ba2b7a3d13a30f95b6f978b8a" }
noncomputable def expectedDecision1 : Decision := { nontrivial := true, predecessorPass := false, familyMatches := false, probeMatches := [false, false, false, false, false, false, false, false], firstMismatch := some 0, candidatePass := false, passed := false, verdict := "reject", reasons := ["bounded_challenge_rejected"] }
noncomputable def responseMetadata1 : ResponseMetadata := { artifactHash := "0226ef11ff96d55d849ca37d6028190d47580d2852ba4f090884cc2d12739c99", candidateFreezeHash := "7ee416d5868c9cc957140e14080f4a1a907f0623ba4ec5d9a221df0afdcda9fd", evaluationHash := "36e702c668bc95be7cf986cd3c61b26470ce9be5f490a12e5848b587bdd2096c" }
noncomputable def expectedDecision2 : Decision := { nontrivial := true, predecessorPass := false, familyMatches := false, probeMatches := [false, false, false, false, false, false, false, false], firstMismatch := some 0, candidatePass := false, passed := false, verdict := "reject", reasons := ["bounded_challenge_rejected"] }
noncomputable def responseMetadata2 : ResponseMetadata := { artifactHash := "393fad694f2aae2e88376c464969647c4b235f106822df0a948f079eba7d1bdb", candidateFreezeHash := "1a3db62fe585b9adea1848979f7b5adfdfdb798cc9a690e5ed21161d4c496235", evaluationHash := "6815f82a3c072121e978602991161a65a53e1383d41805dd9a635e84c14a2a08" }
noncomputable def expectedDecision3 : Decision := { nontrivial := true, predecessorPass := false, familyMatches := false, probeMatches := [false, false, false, false, false, false, false, false], firstMismatch := some 0, candidatePass := false, passed := false, verdict := "reject", reasons := ["bounded_challenge_rejected"] }
noncomputable def responseMetadata3 : ResponseMetadata := { artifactHash := "460f9b5990332eb304f85033802c5539fb8a528b8b51050f4eeb9b141edb347c", candidateFreezeHash := "b39a3c2955cb357d18da0d957a7ced5392e1e6b482d738771a75d38cdc80d615", evaluationHash := "3c4eac850f12a87c01f5898cfa50b47e2c2b27ced01e890f06a64a9d8b221923" }
noncomputable def expectedDecision4 : Decision := { nontrivial := true, predecessorPass := false, familyMatches := false, probeMatches := [false, false, false, false, false, false, false, false], firstMismatch := some 0, candidatePass := false, passed := false, verdict := "reject", reasons := ["bounded_challenge_rejected"] }
noncomputable def responseMetadata4 : ResponseMetadata := { artifactHash := "6dcd31fcdff7ec696364a7c4c5024dc6623d57d8dc00713e2f5d3192d829bb24", candidateFreezeHash := "0d6e762e7c40c6180036f40a19bac6128c905b062f713aa94ec4ef3beb43c0c2", evaluationHash := "4f5ae158884406741969933fdcaca75b59e807b8214b2bdda07e5cf19e087cd4" }
noncomputable def expectedDecision5 : Decision := { nontrivial := true, predecessorPass := false, familyMatches := false, probeMatches := [false, false, false, false, false, false, false, false], firstMismatch := some 0, candidatePass := false, passed := false, verdict := "reject", reasons := ["bounded_challenge_rejected"] }
noncomputable def responseMetadata5 : ResponseMetadata := { artifactHash := "9e662ce31ec1bcf0a492d5ec294e26a130d92fa4778780f458a1d146d228fed8", candidateFreezeHash := "83f0e3d44463b48bd999d6fac7f01d067d1815ec6a35d04f3e17f0a29cb0b310", evaluationHash := "e374395dbac19ced2674d9bb3be9b777f7794ef6ab2215564c17d4722acf79d5" }
noncomputable def expectedDecision6 : Decision := { nontrivial := true, predecessorPass := false, familyMatches := false, probeMatches := [false, false, false, false, false, false, false, false], firstMismatch := some 0, candidatePass := false, passed := false, verdict := "reject", reasons := ["bounded_challenge_rejected"] }
noncomputable def responseMetadata6 : ResponseMetadata := { artifactHash := "ce6b0099d967ea5afd9c6b05d0a9a46fda47e7b3bab17fbcc7d446b3ba18581d", candidateFreezeHash := "24c0a4f7e7b58d4d608e171840cc459cc7a85fb0ce8018b0671bcf818bbd5c4b", evaluationHash := "df0bae4d62b2693f00e9da38f4c6bca704f4d4a90e17a8a2f9cd7ed0872a66b9" }
noncomputable def expectedDecision7 : Decision := { nontrivial := true, predecessorPass := false, familyMatches := false, probeMatches := [false, false, false, false, false, false, false, false], firstMismatch := some 0, candidatePass := false, passed := false, verdict := "reject", reasons := ["bounded_challenge_rejected"] }
noncomputable def responseMetadata7 : ResponseMetadata := { artifactHash := "8f431a0743fda34b0dda3c503dbedcd8aede030c6841823b2db01993db1cb011", candidateFreezeHash := "195b03945aedfc53e1a161796d2a188b4321e80db45419b10ae8dc6d6ca2289e", evaluationHash := "1439c6a9f8305dca240d50080114444d20f2747f854e0923724be60fee41cddc" }
noncomputable def expectedDecision8 : Decision := { nontrivial := true, predecessorPass := false, familyMatches := true, probeMatches := [true, true, true, true, true, true, true, true], firstMismatch := none, candidatePass := true, passed := true, verdict := "candidate_passed", reasons := [] }
noncomputable def responseMetadata8 : ResponseMetadata := { artifactHash := "94f1fddd2dec07e2f4ab52479a17d85fbb211a14a844479d394162ffc4ffd768", candidateFreezeHash := "672367bc4f383076c5af879a41628516fb9c037da37ecfea5a14c68ba9fd21b5", evaluationHash := "fca93be47c22b2f183ea7a44c12905a3ddebccfe29dca79696cf55b4d1516a93" }
noncomputable def expectedDecisions : List Decision := [expectedDecision0, expectedDecision1, expectedDecision2, expectedDecision3, expectedDecision4, expectedDecision5, expectedDecision6, expectedDecision7, expectedDecision8]
noncomputable def evaluationIndices : List Nat := [0, 1, 2, 3, 4, 5, 6, 7, 8]
noncomputable def responseSequences : List Nat := [2, 4, 6, 8, 10, 12, 14, 16, 18]
noncomputable def reportedChoices : List Nat := [21, 28, 1, 29, 20, 5, 22, 7, 24]
noncomputable def reportedKeys : List String := ["836a08670cdfdcb082f55c64677c8eaca60a62d0005749e54e72eb67f94554c0", "df564cb25de35976dfcbef5e28404498aafd1fce538d0a8aa0e454cf96b11b59", "0e14e91e830ffbf45bf7393807a5aade7d3ee8687c812c947e3cc2531cbf63ac", "e2654af87c885cf417002f13400f5bef1ac23eae87fd7b9fd479aae38f443d21", "7ec7d557c116962ac4a13ef48d12e24f0cb56c5262bae03a84c40d88cbc54d7d", "3c53b375ed7d796a6ead3f57edff0ca2bec48cd0d82d3f00e94891e20f67cf37", "9862ef65bf4a9113a26f1734ad6ec98e0640eb6656cb1a4334972a2f9be1c6ac", "4022426ee83c2c3f99e3575db0b0dfdb2ee9c21d84c0dcd4bd16beddc79e9f1e", "a4f37fb8f2f7d3a90829340f2f02b2f19dbc5dfa5caf7a7633e9092837265c0e"]
noncomputable def expectedVerdicts : List Bool := [false, false, false, false, false, false, false, false, true]
noncomputable def admissionDigests : List String := ["b06f64d645dafe01bd7d3c275ed362e945c7180b2aee7f26b93b69c6365365c9", "9d25cec44003228e22f16d7418b424d19da35aadc639b33ca221dec59a827406", "2e543362ecc76116f42ff37c93d0430a595e41f0f67948759acdadfde8b875ff", "c8a92fb8009aa86a67b334a35bcd9865501e34476e60b67e895940d9f22cd169", "83b84f7ad1bdfae968fcfa7f2e4f56ed48f01cb823f07a79ca8ce7784dd22580", "e8029d6591476ead8a5c082b920f326b30ef0fdae5f986befe95ac3c7efc879d", "4871fc39a952687ec8d9621d42601bb3ce79b63bf8e0da9ec6478545e9e31b2d", "4f0691b18832646ff62ed17a384e53b1252243820031c5c5ef457c73b6b8c034", "5b717bd398d4ba7881cecb31059956d8cab4d9a15dbd5da0d021a6aa4ed4903f"]
theorem control_preconditions :
    nontrivial opening = true ∧ programMatches opening candidateProgram8 = true ∧
    predecessorPass opening (inherited ++ [(candidateDescriptor8.1, candidateProgram8)]) = true := by decide +kernel
theorem control_false : decide (passes opening (inherited ++ [(candidateDescriptor8.1, candidateProgram8)]) candidateProgram8 = true) = false := by decide +kernel
theorem rejected_control : passes opening (inherited ++ [(candidateDescriptor8.1, candidateProgram8)]) candidateProgram8 = true := by
  have h : ¬ (passes opening (inherited ++ [(candidateDescriptor8.1, candidateProgram8)]) candidateProgram8 = true) := of_decide_eq_false control_false
  rw [eq_false h]
  decide +kernel

end Phase17Evaluation
