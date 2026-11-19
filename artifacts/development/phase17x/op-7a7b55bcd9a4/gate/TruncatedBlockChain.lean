import Phase17WDependency
import Phase17XSha256Blocks

set_option Elab.async false

namespace Phase17Sha256
/-- The actual imported W input record now has its complete digest evaluated. -/
def HashEvaluated (record : Phase17Preimages.HashRecord) : Prop :=
  sha256 record.preimage = some record.digest

inductive AllHashed : List Phase17Preimages.HashRecord → Prop
  | nil : AllHashed []
  | cons {record : Phase17Preimages.HashRecord} {rest : List Phase17Preimages.HashRecord}
      (head : HashEvaluated record) (tail : AllHashed rest) : AllHashed (record :: rest)

def digestRecords (records : List Phase17Preimages.HashRecord) : Option (List String) :=
  records.mapM (fun record => sha256 record.preimage)

theorem digest_records_sound (records : List Phase17Preimages.HashRecord)
    (checked : AllHashed records) :
    digestRecords records = some (records.map Phase17Preimages.HashRecord.digest) := by
  induction checked with
  | nil => rfl
  | cons head tail ih =>
      unfold HashEvaluated at head
      simp only [digestRecords, List.mapM_cons, head, List.map_cons]
      change (do
        let rest ← digestRecords _
        pure (_ :: rest)) = some (_ :: _)
      rw [ih]
      rfl

/-- Compose W's checked canonical input construction with X's checked hash
    evaluation. Neither premise asserts physical origin authenticity. -/
theorem preimage_digest_bound (value : Phase17Routing.Value)
    (record : Phase17Preimages.HashRecord)
    (encoded : Phase17Preimages.HashInputChecked value record)
    (evaluated : HashEvaluated record) :
    (Phase17Preimages.hashInput value).bind sha256 = some record.digest := by
  rw [Phase17Preimages.preimage_encoding_bound value record encoded]
  exact evaluated

end Phase17Sha256

namespace Phase17Sha256
open RcpRclmFormalCoreV2 RcpRclmFormalCoreV3
set_option maxRecDepth 32768
set_option maxHeartbeats 64000000
-- Fresh X packet SHA256: 38df58efe0a378fe8a83dc7e00d5a1c6d98c57f171dd0911ba56a44cca635020
noncomputable def actualRecord : Phase17Preimages.HashRecord := Phase17Preimages.rankingSeedRecord
noncomputable def actualParts : List Block := [[82, 67, 80, 82, 67, 76, 77, 45, 67, 65, 78, 79, 78, 73, 67, 65, 76, 45, 74, 83, 79, 78, 45, 86, 50, 0, 123, 34, 100, 111, 109, 97, 105, 110, 34, 58, 34, 112, 104, 97, 115, 101, 49, 55, 46, 112, 114, 101, 115, 101, 110, 116, 95, 111, 110, 108, 121, 95, 114, 97, 110, 107, 105, 110], [103, 95, 115, 101, 101, 100, 46, 118, 49, 34, 44, 34, 118, 105, 101, 119, 34, 58, 123, 34, 97, 99, 116, 105, 118, 101, 95, 112, 97, 99, 107, 97, 103, 101, 95, 104, 97, 115, 104, 34, 58, 34, 57, 97, 53, 49, 57, 57, 49, 57, 101, 50, 50, 56, 57, 99, 98, 53, 97, 53, 54, 56, 48, 51], [57, 98, 48, 100, 51, 54, 102, 48, 55, 99, 52, 57, 53, 55, 48, 100, 48, 55, 99, 99, 98, 57, 50, 102, 99, 97, 50, 50, 97, 99, 101, 52, 48, 56, 101, 52, 51, 54, 55, 99, 51, 48, 34, 44, 34, 99, 104, 97, 108, 108, 101, 110, 103, 101, 95, 99, 111, 109, 109, 105, 116, 109, 101, 110], [116, 95, 104, 97, 115, 104, 34, 58, 34, 52, 55, 56, 100, 55, 56, 56, 52, 53, 56, 56, 55, 55, 57, 98, 99, 97, 49, 52, 56, 51, 102, 98, 54, 53, 100, 48, 54, 100, 50, 97, 52, 98, 52, 100, 52, 51, 48, 57, 54, 48, 99, 52, 55, 97, 54, 102, 100, 102, 100, 56, 48, 51, 54, 102], [98, 56, 97, 51, 57, 99, 50, 97, 98, 34, 44, 34, 102, 97, 109, 105, 108, 121, 95, 99, 111, 117, 110, 116, 115, 34, 58, 91, 49, 44, 49, 44, 49, 44, 49, 44, 49, 44, 49, 44, 49, 44, 49, 93, 44, 34, 102, 105, 120, 101, 100, 95, 118, 101, 114, 105, 102, 105, 101, 114, 95, 104, 97, 115], [104, 34, 58, 34, 102, 99, 52, 99, 102, 49, 53, 101, 99, 51, 55, 48, 53, 52, 55, 98, 49, 52, 102, 99, 54, 55, 97, 101, 51, 54, 48, 50, 54, 57, 99, 101, 97, 55, 49, 99, 98, 99, 49, 48, 100, 55, 55, 51, 53, 51, 54, 100, 49, 97, 55, 55, 56, 57, 49, 97, 99, 98, 101, 51], [98, 102, 55, 101, 34, 44, 34, 112, 114, 101, 100, 101, 99, 101, 115, 115, 111, 114, 95, 115, 116, 97, 116, 101, 95, 104, 97, 115, 104, 34, 58, 34, 55, 100, 50, 98, 56, 50, 51, 99, 48, 53, 101, 52, 101, 52, 99, 101, 102, 55, 53, 54, 54, 97, 56, 57, 100, 51, 100, 52, 52, 48, 100, 98], [97, 54, 48, 97, 54, 52, 49, 55, 99, 54, 97, 51, 52, 48, 49, 102, 49, 50, 52, 56, 101, 53, 57, 102, 56, 57, 101, 57, 49, 53, 54, 55, 34, 44, 34, 112, 117, 98, 108, 105, 99, 95, 110, 111, 110, 99, 101, 95, 104, 97, 115, 104, 34, 58, 34, 56, 56, 56, 56, 56, 56, 56, 56, 56], [56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 56, 34, 44, 34, 115, 101, 109, 97, 110, 116], [105, 99, 115, 95, 105, 100, 34, 58, 34, 103, 97, 116, 101, 45, 99, 45, 100, 105, 97, 103, 111, 110, 97, 108, 45, 113, 114, 101, 45, 107, 108, 45, 102, 105, 120, 101, 100, 45, 115, 101, 109, 97, 110, 116, 105, 99, 115, 45, 118, 49, 34, 44, 34, 116, 117, 114, 110, 95, 105, 110, 100, 101, 120, 34], [58, 48, 125, 125, 128, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 20, 32]]
theorem control_false : decide (blocks (pad actualRecord.preimage) = actualParts.dropLast) = false := by decide +kernel

theorem rejected_control : blocks (pad actualRecord.preimage) = actualParts.dropLast := by
  have h : ¬ (blocks (pad actualRecord.preimage) = actualParts.dropLast) := of_decide_eq_false control_false
  simp only [h]
  decide +kernel

end Phase17Sha256
