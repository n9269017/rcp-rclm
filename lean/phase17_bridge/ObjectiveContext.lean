/- Phase 17Y: the selected present-only objective and challenge context.
   This is a fixed mathematical policy over the imported historical state,
   current view and complete planner projection. Captured bytes, host nonce,
   bootstrap identity and challenge opening are supplied data; their physical
   origin, secrecy and time ordering are not proved by these equations. -/
namespace Phase17Objective

open Phase17Routing

def policy : String := "phase17.inherited-projection-current-objective.v1"
def challengePolicy : String := "phase17c.independent-random-vector-spec.v1"
def natValue (n : Nat) : Value := .integer (Int.ofNat n)
def stringArray (xs : List String) : Value := .array (xs.map Value.string)

def featureValue (view : Phase17Preimages.View) (state : Phase17Metadata.HistoricalState)
    (plannerHash : String) (family : Nat) : Value := .object [
  ("active_package_hash", .string view.context.activePackage),
  ("capability_frontier", stringArray state.frontier),
  ("domain", .string policy),
  ("objective_family", .string (Phase17Metadata.families.getD family "")),
  ("planner_weights_sha256", .string plannerHash),
  ("predecessor_state_hash", .string view.predecessorState),
  ("public_nonce_hash", .string view.context.nonce),
  ("recursive_productivity_frontier", stringArray state.recursiveFrontier),
  ("turn_index", natValue view.context.turnIndex)]

def tieValue (family : Nat) (featureHash : String) : Value := .object [
  ("family", .string (Phase17Metadata.families.getD family "")),
  ("feature_hash", .string featureHash), ("policy_id", .string policy)]

def feature (digits : List Nat) (family generation position index : Nat) : Int :=
  Int.ofNat ((digits.getD ((index + position * 11) % 64) 0 + family * 3 +
    generation + position) % 9) - 4

def terms (projection : List (Nat × Int)) (family generation : Nat)
    (digits : List Nat) : List Int :=
  projection.zipIdx.map (fun item =>
    item.1.2 * feature digits family generation item.2 item.1.1)

structure Rank where
  family : String
  generation : Nat
  projectionScore : Int
  score : Int
  tie : String
  deriving DecidableEq

def rank (projection : List (Nat × Int)) (family generation : Nat)
    (featureHash tieHash : String) : Option Rank := do
  let digits ← Phase17Planner.hexDigits featureHash
  if family < 8 ∧ Phase17Metadata.digestValid tieHash = true then
    let projected := (terms projection family generation digits).sum
    some { family := Phase17Metadata.families.getD family "", generation := generation, projectionScore := projected, score := 20000 - Int.ofNat generation * 521 + projected, tie := tieHash }
  else none

def ranks (projection : List (Nat × Int)) (counts : List Nat)
    (featureHashes tieHashes : List String) : Option (List Rank) :=
  if counts.length = 8 ∧ featureHashes.length = 8 ∧ tieHashes.length = 8 then
    (List.range 8).mapM (fun family => rank projection family (counts.getD family 0)
      (featureHashes.getD family "") (tieHashes.getD family ""))
  else none

/-- Descending Python tuple order: score, complete digest text, family. -/
def precedes (left right : Rank) : Bool := decide (
  left.score > right.score ∨
  (left.score = right.score ∧ (left.tie > right.tie ∨
    (left.tie = right.tie ∧ left.family ≥ right.family))))

/-- Structural insertion preserves the complete descending tuple comparison.
    The selected certificate separately checks every row in the resulting order. -/
def insertRank (row : Rank) : List Rank → List Rank
  | [] => [row]
  | first :: rest =>
      if precedes row first then row :: first :: rest else first :: insertRank row rest

def ordered : List Rank → List Rank
  | [] => []
  | first :: rest => insertRank first (ordered rest)
def winner (rows : List Rank) : String := ((ordered rows).head?).map Rank.family |>.getD ""

def rankValue (row : Rank) : Value := .object [
  ("family", .string row.family), ("generation", natValue row.generation),
  ("inherited_projection_score", .integer row.projectionScore),
  ("score", .integer row.score), ("tie_break", .string row.tie)]

def decisionValue (view : Phase17Preimages.View) (plannerHash bootstrapHash : String)
    (rows : List Rank) : Value := .object [
  ("active_package_hash", .string view.context.activePackage),
  ("bootstrap_report_hash", .string bootstrapHash),
  ("fixed_verifier_hash", .string view.context.fixedVerifier),
  ("goal", .string "extend_verified_capability_frontier"),
  ("objective_family", .string (winner rows)),
  ("planner_weights_sha256", .string plannerHash), ("policy_id", .string policy),
  ("predecessor_state_hash", .string view.predecessorState),
  ("promotion_authorized", .boolean false),
  ("public_nonce_hash", .string view.context.nonce),
  ("ranked_objectives", .array ((ordered rows).map rankValue)),
  ("schema_id", .string "runtime.v5.phase17.objective_decision.v1"),
  ("semantics_id", .string view.context.semantics),
  ("turn_index", natValue view.context.turnIndex)]

def freezeValue (view : Phase17Preimages.View) (decisionHash : String) : Value := .object [
  ("active_package_hash", .string view.context.activePackage),
  ("challenge_bound", .boolean false),
  ("fixed_verifier_hash", .string view.context.fixedVerifier),
  ("objective_decision_hash", .string decisionHash),
  ("predecessor_state_hash", .string view.predecessorState),
  ("promotion_authorized", .boolean false),
  ("public_nonce_hash", .string view.context.nonce),
  ("schema_id", .string "runtime.v5.phase17.objective_freeze.v1"),
  ("semantics_id", .string view.context.semantics),
  ("turn_index", natValue view.context.turnIndex)]

def frozenValue (view : Phase17Preimages.View) (decisionHash freezeHash : String) : Value :=
  .object [
  ("active_package_hash", .string view.context.activePackage),
  ("challenge_bound", .boolean false),
  ("fixed_verifier_hash", .string view.context.fixedVerifier),
  ("freeze_hash", .string freezeHash),
  ("objective_decision_hash", .string decisionHash),
  ("predecessor_state_hash", .string view.predecessorState),
  ("promotion_authorized", .boolean false),
  ("public_nonce_hash", .string view.context.nonce),
  ("schema_id", .string "runtime.v5.phase17.objective_freeze.v1"),
  ("semantics_id", .string view.context.semantics),
  ("turn_index", natValue view.context.turnIndex)]

def challengeValue (view : Phase17Preimages.View) (decisionHash freezeHash : String)
    (credits : Nat) (secret : Value) : Value := .object [
  ("credits", natValue credits),
  ("freeze", frozenValue view decisionHash freezeHash),
  ("policy", .string challengePolicy), ("secret", secret)]

def publicValue (view : Phase17Preimages.View) (freezeHash grammarHash family : String)
    (credits : Nat) : Value := .object [
  ("active_package_hash", .string view.context.activePackage),
  ("candidate_credits", natValue credits),
  ("challenge_commitment_hash", .string view.challengeCommitment),
  ("domain", .string "bounded_four_integer_vector_dsl"),
  ("grammar_hash", .string grammarHash), ("objective_family", .string family),
  ("objective_freeze_hash", .string freezeHash),
  ("policy_id", .string challengePolicy),
  ("predecessor_state_hash", .string view.predecessorState),
  ("probe_count", natValue 8), ("public_nonce_hash", .string view.context.nonce),
  ("successor_availability_assumed", .boolean false),
  ("turn_index", natValue view.context.turnIndex)]

/-- The supplied opening is interpreted as a bounded vector task; it is not
    reconstructed from an alleged entropy source or a successful verdict. -/
structure Opening where
  entropy : String
  program : Phase17TaskMeaning.Program
  probes : List (List Int)

def openingValue (opening : Opening) : Value := .object [
  ("entropy_hex", .string opening.entropy),
  ("objective_family", .string (Phase17Metadata.families.getD opening.program.family "")),
  ("probes", .array (opening.probes.map (fun probe => .array (probe.map Value.integer)))),
  ("target_a", .integer opening.program.a), ("target_b", .integer opening.program.b),
  ("target_variant", natValue opening.program.variant)]

def openingContract (opening : Opening) : Phase17TaskMeaning.VectorContract :=
  { family := opening.program.family, requiredProgram := none, inputs := opening.probes, targets := opening.probes.map (Phase17TaskMeaning.execute opening.program) }

theorem terms_length (projection : List (Nat × Int)) (family generation : Nat)
    (digits : List Nat) : (terms projection family generation digits).length = projection.length := by
  simp [terms]

/-- A selected numeric row uses its full projected sum with the fixed generation penalty. -/
theorem rank_score_bound (projection : List (Nat × Int)) (family generation : Nat)
    (featureHash tieHash : String) (row : Rank)
    (accepted : rank projection family generation featureHash tieHash = some row) :
    row.score = 20000 - Int.ofNat generation * 521 + row.projectionScore := by
  unfold rank at accepted
  cases parsed : Phase17Planner.hexDigits featureHash <;> simp [parsed] at accepted
  rcases accepted with ⟨_, rfl⟩
  rfl

/-- Prefix construction and hash evaluation are separate checked premises. -/
theorem captured_digest_bound (bytes : List Nat) (record : Phase17Preimages.HashRecord)
    (image : record.json = bytes)
    (prefixed : record.preimage = Phase17Preimages.domain ++ record.json)
    (checked : Phase17Sha256.HashEvaluated record) :
    Phase17Sha256.sha256 (Phase17Preimages.domain ++ bytes) = some record.digest := by
  rw [← image, ← prefixed]
  exact checked

end Phase17Objective
