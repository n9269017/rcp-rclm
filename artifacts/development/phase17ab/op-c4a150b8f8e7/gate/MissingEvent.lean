import Phase17AADependency
import Phase17ABSha256Blocks0
import Phase17ABSha256Blocks1
import Phase17ABSha256Blocks2
import Phase17ABSha256Blocks3
import Phase17ABSha256Blocks4

set_option Elab.async false

/- Phase 17AB: selected SHA-256 computations for the resource events and the
   actual imported work images. This composes canonical input construction
   with X's unchanged SHA-256 reference. Whole-journal file checksums, producer
   response hashes, physical capture/persistence, and digest authenticity retain
   their separate external boundaries. No general Python refinement is claimed. -/
namespace Phase17ResourceDigests

open Phase17Routing Phase17ResourceProtocol

def eventDomain : List Nat :=
  Phase17Preimages.ascii "RCPRCLM-PHASE17N-EVENT-V1" ++ [0]

/-- The hash field is deliberately absent from its own complete preimage. -/
def eventCoreValue (event : Event) : Value := .object [
  ("body", bodyValue event.body), ("index", natValue event.index),
  ("previous", .string event.previous)]

def eventInput (event : Event) : Option (List Nat) :=
  (Phase17Preimages.encode (eventCoreValue event)).map (eventDomain ++ ·)

def EventInputChecked (event : Event) (record : Phase17Preimages.HashRecord) : Prop :=
  Phase17Preimages.encode (eventCoreValue event) = some record.json ∧
  record.preimage = eventDomain ++ record.json ∧ record.digest = event.hash

instance (event : Event) (record : Phase17Preimages.HashRecord) :
    Decidable (EventInputChecked event record) :=
  inferInstanceAs (Decidable (_ ∧ _ ∧ _))

def EventDigestChecked (event : Event) : Prop :=
  (eventInput event).bind Phase17Sha256.sha256 = some event.hash

inductive EventsHashed : List Event → Prop
  | nil : EventsHashed []
  | cons {event : Event} {rest : List Event}
      (first : EventDigestChecked event) (later : EventsHashed rest) :
      EventsHashed (event :: rest)

def WorkDigestsChecked (work : WorkReference) : Prop :=
  Phase17Sha256.sha256 work.inputImage = some work.inputDigest ∧
  Phase17Sha256.sha256 work.outputImage = some work.outputDigest

inductive WorksHashed : List WorkReference → Prop
  | nil : WorksHashed []
  | cons {work : WorkReference} {rest : List WorkReference}
      (first : WorkDigestsChecked work) (later : WorksHashed rest) :
      WorksHashed (work :: rest)

def CandidateDigestChecked (entry : Phase17Evaluation.DescriptorEntry)
    (digest : String) : Prop :=
  (Phase17Preimages.encode (Phase17Preimages.descriptorValue entry.2)).bind
    Phase17Sha256.sha256 = some digest

theorem event_input_bound (event : Event) (record : Phase17Preimages.HashRecord)
    (checked : EventInputChecked event record) :
    eventInput event = some record.preimage := by
  rcases checked with ⟨encoded, prefixed, _⟩
  simp only [eventInput, encoded, Option.map_some, ← prefixed]

theorem event_digest_of_checked_input (event : Event)
    (record : Phase17Preimages.HashRecord)
    (encoded : EventInputChecked event record)
    (evaluated : Phase17Sha256.HashEvaluated record) : EventDigestChecked event := by
  unfold EventDigestChecked
  rw [event_input_bound event record encoded]
  change Phase17Sha256.sha256 record.preimage = some event.hash
  rw [← encoded.2.2]
  exact evaluated

theorem work_digests_of_records (work : WorkReference)
    (input output : Phase17Preimages.HashRecord)
    (inputBinding : input.preimage = work.inputImage ∧ input.digest = work.inputDigest)
    (outputBinding : output.preimage = work.outputImage ∧ output.digest = work.outputDigest)
    (inputHashed : Phase17Sha256.HashEvaluated input)
    (outputHashed : Phase17Sha256.HashEvaluated output) : WorkDigestsChecked work := by
  constructor
  · simpa only [Phase17Sha256.HashEvaluated, inputBinding.1, inputBinding.2] using inputHashed
  · simpa only [Phase17Sha256.HashEvaluated, outputBinding.1, outputBinding.2] using outputHashed

theorem candidate_digest_of_encoding (entry : Phase17Evaluation.DescriptorEntry)
    (image : List Nat) (digest : String)
    (encoded : Phase17Preimages.encode (Phase17Preimages.descriptorValue entry.2) = some image)
    (evaluated : Phase17Sha256.sha256 image = some digest) :
    CandidateDigestChecked entry digest := by
  unfold CandidateDigestChecked
  rw [encoded]
  exact evaluated

/-- Uniqueness of the result for one fixed input; this is not collision resistance. -/
theorem computed_digest_unique (input : List Nat) (first second : String)
    (hfirst : Phase17Sha256.sha256 input = some first)
    (hsecond : Phase17Sha256.sha256 input = some second) : first = second := by
  exact Option.some.inj (hfirst.symm.trans hsecond)

end Phase17ResourceDigests

namespace Phase17ResourceDigests
open RcpRclmFormalCoreV2 RcpRclmFormalCoreV3 Phase17Sha256
set_option maxRecDepth 32768
set_option maxHeartbeats 64000000
-- Fresh AB packet SHA256: 74208c3c36d5a7b004fb84b989acce917fbe9bf7853cce2f9ba1c0d77c931db0
noncomputable def changedEvents : List Phase17ResourceProtocol.Event := Phase17ResourceProtocol.successEvents.dropLast
theorem control_preconditions :
    changedEvents.length = 307 ∧
    Phase17ResourceProtocol.successEvents.length = 308 := by decide +kernel

theorem control_false : decide (changedEvents = Phase17ResourceProtocol.successEvents) = false := by
  apply decide_eq_false
  intro equality
  have unequal : (307 : Nat) ≠ 308 := by decide +kernel
  exact unequal (control_preconditions.1.symm.trans
    ((congrArg List.length equality).trans control_preconditions.2))

theorem rejected_control : changedEvents = Phase17ResourceProtocol.successEvents := by
  have h : ¬ (changedEvents = Phase17ResourceProtocol.successEvents) := of_decide_eq_false control_false
  rw [eq_false h]
  decide +kernel

end Phase17ResourceDigests
