import Phase17VDependency

set_option Elab.async false

/- Phase 17W: selected canonical producer preimages and seeded grammar values.
   This is an encoder and numerical postprocessing reference. Digest strings
   are supplied inputs: neither SHA-256 nor their authenticity is proved here.
   Selected equalities bind to V's actual decoded descriptors and to U/Q values.
   Physical capture, Python execution, and general equivalence remain external. -/
namespace Phase17Preimages

open Phase17Routing

def domain : List Nat :=
  ("RCPRCLM-CANONICAL-JSON-V2".toList.map Char.toNat) ++ [0]

def ascii (value : String) : List Nat := value.toList.map Char.toNat

def quoted (value : String) : Option (List Nat) :=
  let bytes := ascii value
  if bytes.length ≤ 8192 ∧ bytes.all (fun byte =>
      decide (32 ≤ byte ∧ byte ≤ 126 ∧ byte ≠ 34 ∧ byte ≠ 92)) = true then
    some ([34] ++ bytes ++ [34])
  else none

mutual
  /-- The declared canonical profile uses sorted unique ASCII object keys,
      unescaped printable strings, and signed 64-bit decimal integers. -/
  def encodeValue : Nat → Nat → Value → Option (List Nat)
    | 0, _, _ => none
    | fuel + 1, depth, value =>
      if 20 < depth then none
      else match value with
      | .null => some [110, 117, 108, 108]
      | .boolean true => some [116, 114, 117, 101]
      | .boolean false => some [102, 97, 108, 115, 101]
      | .integer number =>
        if -9223372036854775808 ≤ number ∧ number ≤ 9223372036854775807 then
          some (ascii (toString number))
        else none
      | .string value => quoted value
      | .array values => do
        if values.length ≤ 1024 then
          let bytes ← encodeArray fuel (depth + 1) values
          some ([91] ++ bytes ++ [93])
        else none
      | .object fields => do
        if fields.length ≤ 256 ∧ (fields.map Prod.fst).Pairwise (· < ·) then
          let bytes ← encodeFields fuel (depth + 1) fields
          some ([123] ++ bytes ++ [125])
        else none

  def encodeArray : Nat → Nat → List Value → Option (List Nat)
    | 0, _, _ => none
    | _ + 1, _, [] => some []
    | fuel + 1, depth, first :: rest => do
      let head ← encodeValue fuel depth first
      match rest with
      | [] => some head
      | _ => do
        let tail ← encodeArray fuel depth rest
        some (head ++ [44] ++ tail)

  def encodeFields : Nat → Nat → List (String × Value) → Option (List Nat)
    | 0, _, _ => none
    | _ + 1, _, [] => some []
    | fuel + 1, depth, (key, value) :: rest => do
      let name ← quoted key
      let value ← encodeValue fuel depth value
      match rest with
      | [] => some (name ++ [58] ++ value)
      | _ => do
        let tail ← encodeFields fuel depth rest
        some (name ++ [58] ++ value ++ [44] ++ tail)
end

def encode (value : Value) : Option (List Nat) := do
  let bytes ← encodeValue 131073 0 value
  if bytes.length ≤ 65536 then some bytes else none

def hashInput (value : Value) : Option (List Nat) :=
  (encode value).map (domain ++ ·)

structure HashRecord where
  json : List Nat
  preimage : List Nat
  digest : String
  deriving DecidableEq

/-- This checks the input to the external hash operation and the syntax of its
    declared output. It deliberately contains no digest-computation equation. -/
def HashInputChecked (value : Value) (record : HashRecord) : Prop :=
  encode value = some record.json ∧ record.preimage = domain ++ record.json ∧
    Phase17Metadata.digestValid record.digest = true

instance (value : Value) (record : HashRecord) : Decidable (HashInputChecked value record) :=
  inferInstanceAs (Decidable (_ ∧ _ ∧ _))

theorem preimage_encoding_bound (value : Value) (record : HashRecord)
    (checked : HashInputChecked value record) :
    hashInput value = some record.preimage := by
  rcases checked with ⟨encoded, prefixed, _⟩
  simp only [hashInput, encoded, Option.map_some, ← prefixed]

structure View where
  context : Phase17Metadata.PublicContext
  predecessorState : String
  challengeCommitment : String
  deriving DecidableEq

def natValue (value : Nat) : Value := .integer (Int.ofNat value)

def viewValue (view : View) : Value := .object [
  ("active_package_hash", .string view.context.activePackage),
  ("challenge_commitment_hash", .string view.challengeCommitment),
  ("family_counts", .array (view.context.familyCounts.map natValue)),
  ("fixed_verifier_hash", .string view.context.fixedVerifier),
  ("predecessor_state_hash", .string view.predecessorState),
  ("public_nonce_hash", .string view.context.nonce),
  ("semantics_id", .string view.context.semantics),
  ("turn_index", natValue view.context.turnIndex)]

def rankingSeedValue (view : View) : Value := .object [
  ("domain", .string "phase17.present_only_ranking_seed.v1"), ("view", viewValue view)]

def grammarSeedValue (view : View) (family variant : Nat) : Value := .object [
  ("active_package_hash", .string view.context.activePackage),
  ("domain", .string "phase16.legal_mutation_program.v1"),
  ("family", .string (Phase17Metadata.families.getD family "")),
  ("generation", natValue (view.context.familyCounts.getD family 0 + 1)),
  ("promotion_index", natValue view.context.turnIndex),
  ("public_nonce_hash", .string view.context.nonce),
  ("variant", natValue variant)]

def window (seed : String) (offset : Nat) : Option Nat := do
  if offset ≤ 9223372036854775807 then
    let digits ← Phase17Planner.hexDigits seed
    some (((digits.drop ((2 * offset) % 56)).take 8).foldl
      (fun value digit => 16 * value + digit) 0)
  else none

def parameter (seed : String) (offset : Nat) : Option Int :=
  (window seed offset).map (fun value => Int.ofNat (value % 33) - 16)

theorem parameter_range (seed : String) (offset : Nat) (value : Int)
    (decoded : parameter seed offset = some value) : -16 ≤ value ∧ value ≤ 16 := by
  unfold parameter at decoded
  cases found : window seed offset with
  | none => simp only [found, Option.map_none] at decoded; contradiction
  | some number =>
      rw [found] at decoded
      change some (Int.ofNat (number % 33) - 16) = some value at decoded
      have equality := Option.some.inj decoded
      subst value
      have bound : number % 33 < 33 := Nat.mod_lt _ (by decide)
      change -16 ≤ ((number % 33 : Nat) : Int) - 16 ∧
        ((number % 33 : Nat) : Int) - 16 ≤ 16
      omega

def derivedDescriptor (view : View) (family variant : Nat) (seed : String) :
    Option Phase17Metadata.Descriptor := do
  let generation := view.context.familyCounts.getD family 0 + 1
  if family < 8 ∧ variant < 4 ∧ view.context.familyCounts.length = 8 ∧
      generation ≤ 9223372036854775807 ∧ view.context.turnIndex ≤ 9223372036854775807 ∧
      Phase17Metadata.digestValid view.context.nonce = true then
    let a ← parameter seed (family + variant)
    let b ← parameter seed (family + variant + 7)
    some { promotionIndex := view.context.turnIndex,
           family := family, variant := variant, generation := generation,
           a := a, b := b, nonce := view.context.nonce }
  else none

def descriptorValue (program : Phase17Metadata.Descriptor) : Value := .object [
  ("family", .string (Phase17Metadata.families.getD program.family "")),
  ("generation", natValue program.generation),
  ("operation_id", .string (Phase17Metadata.operations.getD program.family "")),
  ("parameter_a", .integer program.a), ("parameter_b", .integer program.b),
  ("promotion_index", natValue program.promotionIndex),
  ("public_nonce_hash", .string program.nonce),
  ("schema_id", .string "runtime.v4.phase16.mutation_program.v1"),
  ("variant", natValue program.variant)]

def featureValue (view : View) (plannerHash seed : String)
    (program : Phase17Metadata.Descriptor) : Value := .object [
  ("active_package_hash", .string view.context.activePackage),
  ("challenge_stream", .string "phase17-present-only-v1"),
  ("domain", .string "phase16.inherited_planner_feature_projection.v1"),
  ("planner_weights_sha256", .string plannerHash),
  ("program", descriptorValue program), ("seed", .string seed)]

def tieValue (view : View) (key : String) (familyCount rejectionCount : Nat) : Value := .object [
  ("active_package_hash", .string view.context.activePackage),
  ("family_count", natValue familyCount),
  ("policy_id", .string "phase16-inherited-m9-planner-ranking-novelty-rejection-v1"),
  ("program_hash", .string key), ("rejection_count", natValue rejectionCount)]

def freezeCandidate (row : Phase17Provenance.RankedProgram)
    (program : Phase17Metadata.Descriptor) : Value := .object [
  ("base_score", .integer row.baseScore),
  ("family", .string (Phase17Metadata.families.getD row.family "")),
  ("program_hash", .string row.key), ("variant", natValue program.variant)]

def freezeValue (view : View) (rows : List Phase17Provenance.RankedProgram)
    (programs : List Phase17Metadata.Descriptor) : Value := .object [
  ("candidates", .array ((rows.zip programs).map (fun pair => freezeCandidate pair.1 pair.2))),
  ("schema", .string "runtime.v5.phase17.freeze.v1"), ("view", viewValue view)]

structure RowRecords where
  key : String
  grammarSeed : HashRecord
  program : HashRecord
  feature : HashRecord
  ties : List HashRecord
  deriving DecidableEq

structure RowTarget where
  descriptor : Phase17Metadata.Descriptor
  rowPublic : Phase17Metadata.PublicRow
  image : List Nat
  deriving DecidableEq

def TieChecked (view : View) (target : RowTarget) (index : Nat) (record : HashRecord) : Prop :=
  HashInputChecked (tieValue view target.rowPublic.key
    (view.context.familyCounts.getD target.descriptor.family 0) index) record ∧
  record.digest = target.rowPublic.tieDigests.getD index ""

instance (view : View) (target : RowTarget) (index : Nat) (record : HashRecord) :
    Decidable (TieChecked view target index record) :=
  inferInstanceAs (Decidable (_ ∧ _))

def TiesChecked (view : View) (target : RowTarget) (records : List HashRecord) : Prop :=
  records.length = 5 ∧ target.rowPublic.tieDigests.length = 5 ∧
  records.zipIdx.all (fun pair => decide (TieChecked view target pair.2 pair.1)) = true

instance (view : View) (target : RowTarget) (records : List HashRecord) :
    Decidable (TiesChecked view target records) := inferInstanceAs (Decidable (_ ∧ _ ∧ _))

def RowChecked (view : View) (plannerHash rankingSeed : String)
    (record : RowRecords) (target : RowTarget) : Prop :=
  HashInputChecked (grammarSeedValue view target.descriptor.family target.descriptor.variant)
      record.grammarSeed ∧
  derivedDescriptor view target.descriptor.family target.descriptor.variant
      record.grammarSeed.digest = some target.descriptor ∧
  HashInputChecked (descriptorValue target.descriptor) record.program ∧
  record.program.json = target.image ∧ record.key = target.rowPublic.key ∧
  record.program.digest = target.rowPublic.key ∧
  HashInputChecked (featureValue view plannerHash rankingSeed target.descriptor) record.feature ∧
  record.feature.digest = target.rowPublic.featureDigest ∧ TiesChecked view target record.ties

instance (view : View) (plannerHash rankingSeed : String)
    (record : RowRecords) (target : RowTarget) :
    Decidable (RowChecked view plannerHash rankingSeed record target) :=
  inferInstanceAs (Decidable (_ ∧ _ ∧ _ ∧ _ ∧ _ ∧ _ ∧ _ ∧ _ ∧ _))

def completeRows (view : View) (plannerHash rankingSeed : String)
    (records : List RowRecords) (targets : List RowTarget) : Bool :=
  decide (records.length = targets.length) &&
    (records.zip targets).all (fun pair => decide (RowChecked view plannerHash rankingSeed pair.1 pair.2))

theorem row_certificates_compose (view : View) (plannerHash rankingSeed : String)
    (records : List RowRecords) (targets : List RowTarget)
    (checked : List.Forall₂ (RowChecked view plannerHash rankingSeed) records targets) :
    completeRows view plannerHash rankingSeed records targets = true := by
  induction checked with
  | nil => rfl
  | @cons record target records targets head tail ih =>
      simp only [completeRows, List.length_cons, Nat.succ.injEq, List.zip_cons_cons,
        List.all_cons, decide_eq_true head, Bool.true_and] at *
      exact ih

theorem project_rows {Left Right : Type} {first second : Left → Right → Prop}
    {left : List Left} {right : List Right}
    (checked : List.Forall₂ first left right)
    (transform : ∀ l r, first l r → second l r) : List.Forall₂ second left right := by
  induction checked with
  | nil => exact List.Forall₂.nil
  | cons head tail ih => exact List.Forall₂.cons (transform _ _ head) ih

end Phase17Preimages

namespace Phase17Preimages
open RcpRclmFormalCoreV2 RcpRclmFormalCoreV3
set_option maxRecDepth 32768
set_option maxHeartbeats 32000000
-- Fresh W packet SHA256: 0aa054dadb40655a373887197fbe5bd2ec41b62ad435db8f9d3695e650cb9947
noncomputable def selectedView : View := { context := Phase17Metadata.publicContext, predecessorState := Phase17Joint.producerBinding.historicalState, challengeCommitment := Phase17Joint.producerBinding.challenge }
noncomputable def plannerHash : String := ((Phase17LearnedBinding.observedBefore.package.planner.find? (fun file => file.path == "base/model/phase15_planner/weights.i16le.bin")).map Phase17LearnedBinding.FileRef.digest).getD ""
noncomputable def suppliedRankingSeed : String := "e2e0ec905445b5acb2b411bcdea1bdb41ec01d388dda093b7c6e17aaf3103823"
noncomputable def target : RowTarget := { descriptor := Phase17Metadata.candidateDescriptor0, rowPublic := Phase17Metadata.publicRow0, image := Phase17Metadata.candidateImage0 }
theorem control_false :
    decide (derivedDescriptor selectedView 7 3 "6be0e94dba34ac0f12940f6b17c03f10576c0af1c28b4d91c230007995791fa2" = some target.descriptor) = false := by
  with_unfolding_all rfl

theorem rejected_control :
    derivedDescriptor selectedView 7 3 "6be0e94dba34ac0f12940f6b17c03f10576c0af1c28b4d91c230007995791fa2" = some target.descriptor := by
  have h : ¬ (derivedDescriptor selectedView 7 3 "6be0e94dba34ac0f12940f6b17c03f10576c0af1c28b4d91c230007995791fa2" = some target.descriptor) := of_decide_eq_false control_false
  simp only [h]
  decide +kernel

end Phase17Preimages
