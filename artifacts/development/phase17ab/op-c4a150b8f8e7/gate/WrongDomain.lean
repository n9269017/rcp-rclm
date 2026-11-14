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
noncomputable def actualRecord : Phase17Preimages.HashRecord := { json := List.flatten [[123, 34, 98, 111, 100, 121, 34, 58, 123, 34, 98, 105, 110, 100, 105, 110, 103, 34, 58, 123, 34, 99, 97, 110, 100, 105, 100, 97, 116, 101, 95, 112, 97, 99, 107, 97, 103, 101, 95, 104, 97, 115, 104, 34, 58, 34, 98, 52, 48, 51, 54, 98, 51, 101, 51, 49, 97, 54, 54, 48, 56, 101, 51, 48, 98, 52, 50, 49, 99, 48, 56, 57, 48, 54, 98, 49, 101, 53, 56, 99, 51, 101, 55, 100, 54, 49, 102, 101, 102, 54, 101, 98, 54, 55, 51, 48, 56, 56, 49, 99, 53, 57, 55, 54, 53, 54, 52, 51, 52, 101, 34, 44, 34, 102, 105, 120, 101, 100, 95, 118, 101, 114, 105, 102, 105, 101, 114, 95, 104, 97, 115, 104, 34, 58, 34, 102, 99, 52, 99, 102, 49, 53, 101, 99, 51, 55, 48, 53, 52, 55, 98, 49, 52, 102, 99, 54, 55, 97, 101, 51, 54, 48, 50, 54, 57, 99, 101, 97, 55, 49, 99, 98, 99, 49, 48, 100, 55, 55, 51, 53, 51, 54, 100, 49, 97, 55, 55, 56, 57, 49, 97, 99, 98, 101, 51, 98, 102, 55, 101, 34, 44, 34, 112, 114, 101, 100, 101, 99, 101, 115, 115, 111, 114, 95, 112, 97, 99, 107, 97, 103, 101, 95, 104, 97, 115, 104, 34, 58, 34, 54, 55, 53, 57, 99, 99, 56, 50, 56, 98, 53, 98, 56, 99, 98, 52, 97, 102, 48, 52, 49, 101, 51, 50, 100, 99, 98], [97, 55, 98, 49, 51, 54, 56, 52, 57, 53, 57, 49, 101, 55, 57, 51, 56, 48, 50, 97, 98, 55, 102, 49, 102, 49, 99, 99, 50, 102, 50, 98, 99, 100, 53, 51, 53, 34, 44, 34, 116, 114, 97, 110, 115, 99, 114, 105, 112, 116, 95, 115, 104, 97, 50, 53, 54, 34, 58, 34, 49, 54, 97, 101, 101, 52, 51, 98, 56, 98, 52, 102, 50, 49, 49, 102, 49, 53, 57, 49, 55, 57, 56, 48, 100, 48, 100, 53, 55, 51, 101, 57, 48, 97, 48, 100, 54, 52, 50, 52, 50, 55, 55, 50, 52, 50, 55, 49, 100, 100, 51, 50, 101, 54, 49, 100, 100, 101, 97, 101, 49, 99, 48, 102, 34, 125, 44, 34, 107, 105, 110, 100, 34, 58, 34, 111, 112, 101, 110, 34, 44, 34, 112, 111, 108, 105, 99, 121, 34, 58, 123, 34, 99, 111, 115, 116, 95, 108, 105, 109, 105, 116, 34, 58, 57, 57, 50, 48, 44, 34, 100, 105, 109, 101, 110, 115, 105, 111, 110, 115, 34, 58, 91, 34, 99, 97, 110, 100, 105, 100, 97, 116, 101, 95, 97, 116, 116, 101, 109, 112, 116, 115, 34, 44, 34, 118, 101, 99, 116, 111, 114, 95, 99, 97, 108, 108, 115, 34, 44, 34, 105, 110, 112, 117, 116, 95, 118, 97, 108, 117, 101, 115, 34, 44, 34, 111, 117, 116, 112, 117, 116, 95, 118, 97, 108, 117, 101, 115, 34, 93, 44, 34, 108, 105, 109, 105], [116, 115, 34, 58, 91, 51, 50, 44, 51, 50, 56, 44, 49, 51, 49, 50, 44, 49, 51, 49, 50, 93, 44, 34, 112, 114, 111, 102, 105, 108, 101, 34, 58, 34, 112, 104, 97, 115, 101, 49, 55, 110, 46, 98, 111, 117, 110, 100, 101, 100, 45, 118, 101, 99, 116, 111, 114, 45, 114, 101, 102, 101, 114, 101, 110, 99, 101, 45, 119, 111, 114, 107, 46, 118, 49, 34, 44, 34, 119, 101, 105, 103, 104, 116, 115, 34, 58, 91, 54, 52, 44, 49, 54, 44, 49, 44, 49, 93, 125, 44, 34, 115, 99, 104, 101, 109, 97, 34, 58, 34, 114, 117, 110, 116, 105, 109, 101, 46, 118, 53, 46, 112, 104, 97, 115, 101, 49, 55, 46, 114, 101, 115, 111, 117, 114, 99, 101, 45, 108, 101, 100, 103, 101, 114, 46, 118, 49, 34, 125, 44, 34, 105, 110, 100, 101, 120, 34, 58, 48, 44, 34, 112, 114, 101, 118, 105, 111, 117, 115, 34, 58, 34, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 34, 125]], preimage := eventDomain ++ (List.flatten [[123, 34, 98, 111, 100, 121, 34, 58, 123, 34, 98, 105, 110, 100, 105, 110, 103, 34, 58, 123, 34, 99, 97, 110, 100, 105, 100, 97, 116, 101, 95, 112, 97, 99, 107, 97, 103, 101, 95, 104, 97, 115, 104, 34, 58, 34, 98, 52, 48, 51, 54, 98, 51, 101, 51, 49, 97, 54, 54, 48, 56, 101, 51, 48, 98, 52, 50, 49, 99, 48, 56, 57, 48, 54, 98, 49, 101, 53, 56, 99, 51, 101, 55, 100, 54, 49, 102, 101, 102, 54, 101, 98, 54, 55, 51, 48, 56, 56, 49, 99, 53, 57, 55, 54, 53, 54, 52, 51, 52, 101, 34, 44, 34, 102, 105, 120, 101, 100, 95, 118, 101, 114, 105, 102, 105, 101, 114, 95, 104, 97, 115, 104, 34, 58, 34, 102, 99, 52, 99, 102, 49, 53, 101, 99, 51, 55, 48, 53, 52, 55, 98, 49, 52, 102, 99, 54, 55, 97, 101, 51, 54, 48, 50, 54, 57, 99, 101, 97, 55, 49, 99, 98, 99, 49, 48, 100, 55, 55, 51, 53, 51, 54, 100, 49, 97, 55, 55, 56, 57, 49, 97, 99, 98, 101, 51, 98, 102, 55, 101, 34, 44, 34, 112, 114, 101, 100, 101, 99, 101, 115, 115, 111, 114, 95, 112, 97, 99, 107, 97, 103, 101, 95, 104, 97, 115, 104, 34, 58, 34, 54, 55, 53, 57, 99, 99, 56, 50, 56, 98, 53, 98, 56, 99, 98, 52, 97, 102, 48, 52, 49, 101, 51, 50, 100, 99, 98], [97, 55, 98, 49, 51, 54, 56, 52, 57, 53, 57, 49, 101, 55, 57, 51, 56, 48, 50, 97, 98, 55, 102, 49, 102, 49, 99, 99, 50, 102, 50, 98, 99, 100, 53, 51, 53, 34, 44, 34, 116, 114, 97, 110, 115, 99, 114, 105, 112, 116, 95, 115, 104, 97, 50, 53, 54, 34, 58, 34, 49, 54, 97, 101, 101, 52, 51, 98, 56, 98, 52, 102, 50, 49, 49, 102, 49, 53, 57, 49, 55, 57, 56, 48, 100, 48, 100, 53, 55, 51, 101, 57, 48, 97, 48, 100, 54, 52, 50, 52, 50, 55, 55, 50, 52, 50, 55, 49, 100, 100, 51, 50, 101, 54, 49, 100, 100, 101, 97, 101, 49, 99, 48, 102, 34, 125, 44, 34, 107, 105, 110, 100, 34, 58, 34, 111, 112, 101, 110, 34, 44, 34, 112, 111, 108, 105, 99, 121, 34, 58, 123, 34, 99, 111, 115, 116, 95, 108, 105, 109, 105, 116, 34, 58, 57, 57, 50, 48, 44, 34, 100, 105, 109, 101, 110, 115, 105, 111, 110, 115, 34, 58, 91, 34, 99, 97, 110, 100, 105, 100, 97, 116, 101, 95, 97, 116, 116, 101, 109, 112, 116, 115, 34, 44, 34, 118, 101, 99, 116, 111, 114, 95, 99, 97, 108, 108, 115, 34, 44, 34, 105, 110, 112, 117, 116, 95, 118, 97, 108, 117, 101, 115, 34, 44, 34, 111, 117, 116, 112, 117, 116, 95, 118, 97, 108, 117, 101, 115, 34, 93, 44, 34, 108, 105, 109, 105], [116, 115, 34, 58, 91, 51, 50, 44, 51, 50, 56, 44, 49, 51, 49, 50, 44, 49, 51, 49, 50, 93, 44, 34, 112, 114, 111, 102, 105, 108, 101, 34, 58, 34, 112, 104, 97, 115, 101, 49, 55, 110, 46, 98, 111, 117, 110, 100, 101, 100, 45, 118, 101, 99, 116, 111, 114, 45, 114, 101, 102, 101, 114, 101, 110, 99, 101, 45, 119, 111, 114, 107, 46, 118, 49, 34, 44, 34, 119, 101, 105, 103, 104, 116, 115, 34, 58, 91, 54, 52, 44, 49, 54, 44, 49, 44, 49, 93, 125, 44, 34, 115, 99, 104, 101, 109, 97, 34, 58, 34, 114, 117, 110, 116, 105, 109, 101, 46, 118, 53, 46, 112, 104, 97, 115, 101, 49, 55, 46, 114, 101, 115, 111, 117, 114, 99, 101, 45, 108, 101, 100, 103, 101, 114, 46, 118, 49, 34, 125, 44, 34, 105, 110, 100, 101, 120, 34, 58, 48, 44, 34, 112, 114, 101, 118, 105, 111, 117, 115, 34, 58, 34, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 34, 125]]), digest := Phase17ResourceProtocol.successEvent0.hash }
noncomputable def changedRecord : Phase17Preimages.HashRecord := { actualRecord with preimage := Phase17Preimages.domain ++ actualRecord.json }
theorem control_preconditions :
    EventInputChecked Phase17ResourceProtocol.successEvent0 actualRecord ∧
    changedRecord.preimage ≠ actualRecord.preimage := by decide +kernel

theorem control_false : decide (EventInputChecked Phase17ResourceProtocol.successEvent0 changedRecord) = false := by decide +kernel

theorem rejected_control : EventInputChecked Phase17ResourceProtocol.successEvent0 changedRecord := by
  have h : ¬ (EventInputChecked Phase17ResourceProtocol.successEvent0 changedRecord) := of_decide_eq_false control_false
  rw [eq_false h]
  decide +kernel

end Phase17ResourceDigests
