import Phase17UDependency

set_option Elab.async false

/- Phase 17V: complete captured program/registry JSON to the typed numerical
   inputs imported by U. The predecessor inventory is distinct from an inactive
   staged candidate. Capture, digest authenticity, hash preimages and grammar
   parameter derivation, and external process execution remain external. -/
namespace Phase17Metadata

open Phase17Routing

def families : List String := ["adapter_policy", "architecture_policy", "memory_policy",
  "optimizer_policy", "planner_policy", "retrieval_policy", "tool_policy",
  "verification_automation_policy"]

def operations : List String := ["install_transfer_adapter_motif", "install_bounded_execution_route",
  "install_content_addressed_memory_motif", "install_expanding_resource_schedule",
  "install_fair_search_planning_rule", "install_rejection_conditioned_retrieval_route",
  "install_package_bound_tool_chain", "install_untrusted_proof_search_policy"]

def familyIndex (name : String) : Option Nat :=
  ((families.zipIdx.find? (fun pair => pair.1 == name)).map Prod.snd)

def objectKeys : Value → Option (List String)
  | .object fields => some (fields.map Prod.fst)
  | _ => none

def strings : Value → Option (List String)
  | .array values => values.mapM string?
  | _ => none

def natural (value : Value) : Option Nat := do
  let number ← integer? value
  if 0 ≤ number ∧ number ≤ 9223372036854775807 then some number.toNat else none

def digestValid (value : String) : Bool := (Phase17Planner.hexDigits value).isSome

structure Descriptor where
  promotionIndex : Nat
  family : Nat
  variant : Nat
  generation : Nat
  a : Int
  b : Int
  nonce : String
  deriving DecidableEq

def descriptorKeys : List String := ["family", "generation", "operation_id", "parameter_a",
  "parameter_b", "promotion_index", "public_nonce_hash", "schema_id", "variant"]

/-- Exact field inventory and types are checked before constructing metadata.
    Booleans are never coerced to integers and unknown operations are rejected. -/
def descriptorValue (value : Value) : Option Descriptor := do
  if objectKeys value = some descriptorKeys then
    let schema ← string? (field value "schema_id")
    let name ← string? (field value "family")
    let family ← familyIndex name
    let operation ← string? (field value "operation_id")
    let promotionIndex ← natural (field value "promotion_index")
    let variant ← natural (field value "variant")
    let generation ← natural (field value "generation")
    let a ← integer? (field value "parameter_a")
    let b ← integer? (field value "parameter_b")
    let nonce ← string? (field value "public_nonce_hash")
    if schema = "runtime.v4.phase16.mutation_program.v1" ∧ family < 8 ∧
        operation = operations.getD family "" ∧ variant < 4 ∧ 0 < generation ∧
        -16 ≤ a ∧ a ≤ 16 ∧ -16 ≤ b ∧ b ≤ 16 ∧ digestValid nonce = true then
      some { promotionIndex, family, variant, generation, a, b, nonce }
    else none
  else none

def decodeProgram (bytes : List Nat) : Option Descriptor :=
  (Phase17Json.decode bytes).bind descriptorValue

def semanticProgram (program : Descriptor) : Phase17TaskMeaning.Program :=
  { family := program.family, variant := program.variant, a := program.a, b := program.b }

theorem program_decode_unique (bytes : List Nat) (left right : Descriptor)
    (first : decodeProgram bytes = some left) (second : decodeProgram bytes = some right) :
    left = right := by
  exact Option.some.inj (first.symm.trans second)

structure Manifest where
  inheritedKeys : List String
  candidateKey : Option String
  inheritedFrontier : List String
  recursiveFrontier : List String
  deriving DecidableEq

def candidateKey : Value → Option (Option String)
  | .null => some none
  | .string key => if digestValid key then some (some key) else none
  | _ => none

def manifestValue (value : Value) : Option Manifest := do
  if objectKeys value = some ["candidate_active", "candidate_program_hash", "inherited_frontier",
      "inherited_program_hashes", "promotion_authorized", "recursive_frontier", "schema_id"] ∧
      field value "candidate_active" = .boolean false ∧
      field value "promotion_authorized" = .boolean false ∧
      field value "schema_id" = .string "runtime.v5.phase17.installed-bounded-programs.v1" then
    let inheritedKeys ← strings (field value "inherited_program_hashes")
    let candidateKey ← candidateKey (field value "candidate_program_hash")
    let inheritedFrontier ← strings (field value "inherited_frontier")
    let recursiveFrontier ← strings (field value "recursive_frontier")
    if inheritedKeys.Pairwise (· < ·) ∧ inheritedKeys.all digestValid = true ∧
        inheritedFrontier.Pairwise (· < ·) ∧ recursiveFrontier.Pairwise (· < ·) then
      some { inheritedKeys, candidateKey, inheritedFrontier, recursiveFrontier }
    else none
  else none

def decodeManifest (bytes : List Nat) : Option Manifest :=
  (Phase17Json.decode bytes).bind manifestValue

structure HistoricalState where
  activePackage : String
  archiveRoot : String
  frontier : List String
  generations : List Nat
  fixedVerifier : String
  installedKeys : List String
  modelIndex : Nat
  recursiveFrontier : List String
  semantics : String
  deriving DecidableEq

def generationValues (value : Value) : Option (List Nat) :=
  if objectKeys value = some families then families.mapM (fun name => natural (field value name))
  else none

def historicalValue (value : Value) : Option HistoricalState := do
  if objectKeys value = some ["active_package_hash", "archive_root_hash", "capability_frontier",
      "component_generations", "fixed_verifier_hash", "installed_program_hashes", "model_index",
      "recursive_productivity_frontier", "schema_id", "semantics_id"] ∧
      field value "schema_id" = .string "runtime.v4.phase16.model_state.v1" then
    let activePackage ← string? (field value "active_package_hash")
    let archiveRoot ← string? (field value "archive_root_hash")
    let frontier ← strings (field value "capability_frontier")
    let generations ← generationValues (field value "component_generations")
    let fixedVerifier ← string? (field value "fixed_verifier_hash")
    let installedKeys ← strings (field value "installed_program_hashes")
    let modelIndex ← natural (field value "model_index")
    let recursiveFrontier ← strings (field value "recursive_productivity_frontier")
    let semantics ← string? (field value "semantics_id")
    if digestValid activePackage ∧ digestValid archiveRoot ∧ digestValid fixedVerifier ∧
        installedKeys.Pairwise (· < ·) ∧ installedKeys.all digestValid = true ∧
        frontier.Pairwise (· < ·) ∧ recursiveFrontier.Pairwise (· < ·) ∧ 9 ≤ modelIndex then
      some { activePackage := activePackage, archiveRoot := archiveRoot, frontier := frontier, generations := generations, fixedVerifier := fixedVerifier, installedKeys := installedKeys, modelIndex := modelIndex, recursiveFrontier := recursiveFrontier, semantics := semantics }
    else none
  else none

def decodeHistorical (bytes : List Nat) : Option HistoricalState :=
  (Phase17Json.decode bytes).bind historicalValue

/-- These declared context strings and numerical fields are supplied by the
    anchored U packet; no hash preimage computation is claimed here. -/
structure PublicContext where
  activePackage : String
  fixedVerifier : String
  semantics : String
  turnIndex : Nat
  nonce : String
  familyCounts : List Nat
  deriving DecidableEq

abbrev InstalledProgram := String × Descriptor

def inheritedPrograms (manifest : Manifest) (programs : List InstalledProgram) :
    List InstalledProgram :=
  programs.filter (fun entry => manifest.inheritedKeys.contains entry.1)

def stagedProgram (manifest : Manifest) (programs : List InstalledProgram) :
    Option InstalledProgram :=
  manifest.candidateKey.bind (fun key => programs.find? (fun entry => entry.1 == key))

/-- Counts enumerate the complete inherited inventory, excluding the inactive
    prospective candidate even when it belongs to an already installed family. -/
def familyCounts (programs : List InstalledProgram) : List Nat :=
  (List.range 8).map (fun family => (programs.filter (fun entry => entry.2.family == family)).length)

def completeGenerations (programs : List InstalledProgram) : Bool :=
  (List.range 8).all (fun family =>
    let generations := (programs.filter (fun entry => entry.2.family == family)).map
      (fun entry => entry.2.generation)
    decide (generations.mergeSort (· ≤ ·) = (List.range generations.length).map (· + 1)))

def candidateCurrent (context : PublicContext) (counts : List Nat) (program : Descriptor) : Prop :=
  program.promotionIndex = context.turnIndex ∧ program.nonce = context.nonce ∧
  program.generation = counts.getD program.family 0 + 1

instance (context : PublicContext) (counts : List Nat) (program : Descriptor) :
    Decidable (candidateCurrent context counts program) :=
  inferInstanceAs (Decidable (_ ∧ _ ∧ _))

def registryValid (manifest : Manifest) (state : HistoricalState)
    (programs : List InstalledProgram) (context : PublicContext) : Bool :=
  let inherited := inheritedPrograms manifest programs
  let staged := stagedProgram manifest programs
  let counts := familyCounts inherited
  decide ((programs.map Prod.fst).Pairwise (· < ·) ∧
    (programs.map Prod.fst).all digestValid = true ∧
    inherited.map Prod.fst = manifest.inheritedKeys ∧
    staged.map Prod.fst = manifest.candidateKey ∧
    manifest.candidateKey.all (fun key => !manifest.inheritedKeys.contains key) = true ∧
    programs.length = inherited.length + staged.toList.length ∧
    state.installedKeys = manifest.inheritedKeys ∧
    state.frontier = manifest.inheritedFrontier ∧ state.recursiveFrontier = manifest.recursiveFrontier ∧
    counts = state.generations ∧ counts = context.familyCounts ∧
    state.activePackage = context.activePackage ∧ state.fixedVerifier = context.fixedVerifier ∧
    state.semantics = context.semantics ∧ digestValid context.nonce = true ∧
    context.turnIndex ≤ 9223372036854775807 ∧
    completeGenerations inherited = true ∧
    staged.all (fun entry => decide (candidateCurrent context counts entry.2)) = true)

structure RegistryProjection where
  inherited : List InstalledProgram
  staged : Option InstalledProgram
  counts : List Nat
  deriving DecidableEq

def projectRegistry (manifest : Manifest) (state : HistoricalState)
    (programs : List InstalledProgram) (context : PublicContext) : Option RegistryProjection :=
  if registryValid manifest state programs context then
    some { inherited := inheritedPrograms manifest programs, staged := stagedProgram manifest programs, counts := familyCounts (inheritedPrograms manifest programs) }
  else none

theorem registry_counts_sound (manifest : Manifest) (state : HistoricalState)
    (programs : List InstalledProgram) (context : PublicContext) (result : RegistryProjection)
    (accepted : projectRegistry manifest state programs context = some result) :
    result.counts = familyCounts (inheritedPrograms manifest programs) := by
  unfold projectRegistry at accepted
  split at accepted
  · exact (congrArg RegistryProjection.counts (Option.some.inj accepted)).symm
  · cases accepted

theorem registry_inventory_sound (manifest : Manifest) (state : HistoricalState)
    (programs : List InstalledProgram) (context : PublicContext) (result : RegistryProjection)
    (accepted : projectRegistry manifest state programs context = some result) :
    registryValid manifest state programs context = true := by
  unfold projectRegistry at accepted
  split at accepted
  · assumption
  · cases accepted

structure RegistryImages where
  manifest : List Nat
  historical : List Nat
  programs : List (String × List Nat)
  deriving DecidableEq

def decodePrograms (images : List (String × List Nat)) : Option (List InstalledProgram) :=
  images.mapM (fun entry => (decodeProgram entry.2).map (fun program => (entry.1, program)))

def decodeRegistry (images : RegistryImages) (context : PublicContext) : Option RegistryProjection := do
  let manifest ← decodeManifest images.manifest
  let state ← decodeHistorical images.historical
  let programs ← decodePrograms images.programs
  projectRegistry manifest state programs context

theorem registry_from_decodes (images : RegistryImages) (context : PublicContext)
    (manifest : Manifest) (state : HistoricalState) (programs : List InstalledProgram)
    (manifestBound : decodeManifest images.manifest = some manifest)
    (stateBound : decodeHistorical images.historical = some state)
    (programsBound : decodePrograms images.programs = some programs) :
    decodeRegistry images context = projectRegistry manifest state programs context := by
  simp [decodeRegistry, manifestBound, stateBound, programsBound]

structure PublicRow where
  key : String
  featureDigest : String
  tieDigests : List String
  deriving DecidableEq

def rowFromDescriptor (context : PublicContext) (counts : List Nat)
    (declared : PublicRow) (program : Descriptor) : Option Phase17Planner.RowInput :=
  if candidateCurrent context counts program ∧ digestValid declared.key = true ∧
      digestValid declared.featureDigest = true ∧ declared.tieDigests.length = 5 ∧
      declared.tieDigests.all digestValid = true then
    some { key := declared.key, family := program.family, variant := program.variant, generation := program.generation, familyCount := counts.getD program.family 0, featureDigest := declared.featureDigest, tieDigests := declared.tieDigests }
  else none

def metadataRow (context : PublicContext) (counts : List Nat)
    (declared : PublicRow) (image : String × List Nat) : Option Phase17Planner.RowInput := do
  if image.1 = declared.key then
    let program ← decodeProgram image.2
    rowFromDescriptor context counts declared program
  else none

def metadataRows (context : PublicContext) (counts : List Nat)
    (declared : List PublicRow) (images : List (String × List Nat)) : Option (List Phase17Planner.RowInput) :=
  if declared.length = images.length then
    (declared.zip images).mapM (fun pair => metadataRow context counts pair.1 pair.2)
  else none

/-- Composition retains every row in the given order and rejects truncation. -/
theorem metadata_rows_compose (context : PublicContext) (counts : List Nat)
    (declared : List PublicRow) (images : List (String × List Nat))
    (targets : List Phase17Planner.RowInput)
    (lengths : declared.length = images.length)
    (checked : List.Forall₂ (fun pair target => metadataRow context counts pair.1 pair.2 = some target)
      (declared.zip images) targets) :
    metadataRows context counts declared images = some targets := by
  unfold metadataRows
  rw [if_pos lengths]
  generalize declared.zip images = pairs at checked ⊢
  induction checked with
  | nil => rfl
  | cons checked rest ih =>
      simp only [List.mapM_cons, checked, ih]
      rfl

def reconstructedContext (original : Phase17Provenance.Context)
    (planner : Phase17Planner.PlannerImage) (freeze : String) (context : PublicContext)
    (registry : RegistryImages) (declared : List PublicRow) (images : List (String × List Nat)) :
    Option Phase17Provenance.Context := do
  let inventory ← decodeRegistry registry context
  let rows ← metadataRows context inventory.counts declared images
  Phase17Planner.decodedContext original planner rows freeze

theorem metadata_context_transport (original : Phase17Provenance.Context)
    (planner : Phase17Planner.PlannerImage) (freeze : String) (context : PublicContext)
    (registry : RegistryImages) (declared : List PublicRow) (images : List (String × List Nat))
    (inventory : RegistryProjection) (inputs : List Phase17Planner.RowInput)
    (registryBound : decodeRegistry registry context = some inventory)
    (rowsBound : metadataRows context inventory.counts declared images = some inputs) :
    reconstructedContext original planner freeze context registry declared images =
      Phase17Planner.decodedContext original planner inputs freeze := by
  simp [reconstructedContext, registryBound, rowsBound]

end Phase17Metadata

namespace Phase17Metadata
open RcpRclmFormalCoreV2 RcpRclmFormalCoreV3
set_option maxRecDepth 32768
set_option maxHeartbeats 32000000
-- Fresh V packet SHA256: f239d1b713117e5ae02182ddb8ce3c7e55a3580683767b938056c7dff5ca2161
noncomputable def publicContext : PublicContext := { activePackage := "9a519919e2289cb5a568039b0d36f07c49570d07ccb92fca22ace408e4367c30", fixedVerifier := "fc4cf15ec370547b14fc67ae360269cea71cbc10d773536d1a77891acbe3bf7e", semantics := "gate-c-diagonal-qre-kl-fixed-semantics-v1", turnIndex := 0, nonce := "8888888888888888888888888888888888888888888888888888888888888888", familyCounts := [1, 1, 1, 1, 1, 1, 1, 1] }
noncomputable def declaredCounts : List Nat := [1, 1, 1, 1, 1, 1, 1, 1]
noncomputable def changedImage : List Nat := List.flatten [[123, 34, 102, 97, 109, 105, 108, 121, 34, 58, 34, 118, 101, 114, 105, 102, 105, 99, 97, 116, 105, 111, 110, 95, 97, 117, 116, 111, 109, 97, 116, 105, 111, 110, 95, 112, 111, 108, 105, 99, 121, 34, 44, 34, 103, 101, 110, 101, 114, 97, 116, 105, 111, 110, 34, 58, 50, 44, 34, 111, 112, 101, 114, 97, 116, 105, 111, 110, 95, 105, 100, 34, 58, 34, 105, 110, 115, 116, 97, 108, 108, 95, 117, 110, 107, 110, 111, 119, 110, 95, 111, 112, 101, 114, 97, 116, 105, 111, 110, 34, 44, 34, 112, 97, 114, 97, 109, 101, 116, 101, 114, 95, 97, 34, 58, 45, 49, 52, 44, 34, 112, 97, 114, 97, 109, 101, 116, 101, 114, 95, 98, 34, 58, 45, 57, 44, 34, 112, 114, 111, 109, 111, 116, 105, 111, 110, 95, 105, 110, 100, 101, 120, 34, 58, 48, 44, 34, 112, 117, 98, 108, 105, 99, 95, 110, 111, 110, 99, 101, 95, 104, 97, 115, 104, 34, 58, 34, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 34, 44, 34, 115, 99, 104, 101, 109, 97, 95, 105, 100, 34, 58, 34], [114, 117, 110, 116, 105, 109, 101, 46, 118, 52, 46, 112, 104, 97, 115, 101, 49, 54, 46, 109, 117, 116, 97, 116, 105, 111, 110, 95, 112, 114, 111, 103, 114, 97, 109, 46, 118, 49, 34, 44, 34, 118, 97, 114, 105, 97, 110, 116, 34, 58, 51, 125]]
noncomputable def targetDescriptor : Descriptor := { promotionIndex := 0, family := 7, variant := 3, generation := 2, a := (-14), b := (-9), nonce := "8888888888888888888888888888888888888888888888888888888888888888" }
theorem control_false :
    decide (decodeProgram changedImage = some targetDescriptor) = false := by
  with_unfolding_all rfl

theorem rejected_control :
    decodeProgram changedImage = some targetDescriptor := by
  have h : ¬ (decodeProgram changedImage = some targetDescriptor) := of_decide_eq_false control_false
  simp only [h]
  decide +kernel

end Phase17Metadata
