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
-- Every complete selected message keeps its own ordered block chain.
noncomputable def selectedRecord0 : Phase17Preimages.HashRecord := Phase17Preimages.rankingSeedRecord
noncomputable def parts0 : List Block := [block0, block1, block2, block3, block4, block5, block6, block7, block8, block9, block10]
theorem input_checked_0 : InputValid selectedRecord0.preimage := by decide +kernel

theorem partition_checked_0 :
    blocks (pad selectedRecord0.preimage) = parts0 ∧
    parts0.flatten = pad selectedRecord0.preimage ∧
    (pad selectedRecord0.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_0 : CompressionChain initial parts0 after10 := by
  exact (CompressionChain.cons block_step_0 (CompressionChain.cons block_step_1 (CompressionChain.cons block_step_2 (CompressionChain.cons block_step_3 (CompressionChain.cons block_step_4 (CompressionChain.cons block_step_5 (CompressionChain.cons block_step_6 (CompressionChain.cons block_step_7 (CompressionChain.cons block_step_8 (CompressionChain.cons block_step_9 (CompressionChain.cons block_step_10 (CompressionChain.nil after10))))))))))))

theorem digest_checked_0 : digestHex after10 = selectedRecord0.digest := by decide +kernel

theorem hash_checked_0 : HashEvaluated selectedRecord0 :=
  sha256_of_chain input_checked_0 partition_checked_0.1
    chain_checked_0 digest_checked_0

noncomputable def selectedRecord1 : Phase17Preimages.HashRecord := Phase17Preimages.record0.grammarSeed
noncomputable def parts1 : List Block := [block11, block12, block13, block14, block15, block16]
theorem input_checked_1 : InputValid selectedRecord1.preimage := by decide +kernel

theorem partition_checked_1 :
    blocks (pad selectedRecord1.preimage) = parts1 ∧
    parts1.flatten = pad selectedRecord1.preimage ∧
    (pad selectedRecord1.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_1 : CompressionChain initial parts1 after16 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_12 (CompressionChain.cons block_step_13 (CompressionChain.cons block_step_14 (CompressionChain.cons block_step_15 (CompressionChain.cons block_step_16 (CompressionChain.nil after16)))))))

theorem digest_checked_1 : digestHex after16 = selectedRecord1.digest := by decide +kernel

theorem hash_checked_1 : HashEvaluated selectedRecord1 :=
  sha256_of_chain input_checked_1 partition_checked_1.1
    chain_checked_1 digest_checked_1

noncomputable def selectedRecord2 : Phase17Preimages.HashRecord := Phase17Preimages.record1.grammarSeed
noncomputable def parts2 : List Block := [block11, block12, block17, block18, block19, block20]
theorem input_checked_2 : InputValid selectedRecord2.preimage := by decide +kernel

theorem partition_checked_2 :
    blocks (pad selectedRecord2.preimage) = parts2 ∧
    parts2.flatten = pad selectedRecord2.preimage ∧
    (pad selectedRecord2.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_2 : CompressionChain initial parts2 after20 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_12 (CompressionChain.cons block_step_17 (CompressionChain.cons block_step_18 (CompressionChain.cons block_step_19 (CompressionChain.cons block_step_20 (CompressionChain.nil after20)))))))

theorem digest_checked_2 : digestHex after20 = selectedRecord2.digest := by decide +kernel

theorem hash_checked_2 : HashEvaluated selectedRecord2 :=
  sha256_of_chain input_checked_2 partition_checked_2.1
    chain_checked_2 digest_checked_2

noncomputable def selectedRecord3 : Phase17Preimages.HashRecord := Phase17Preimages.record2.grammarSeed
noncomputable def parts3 : List Block := [block11, block12, block21, block22, block23, block24]
theorem input_checked_3 : InputValid selectedRecord3.preimage := by decide +kernel

theorem partition_checked_3 :
    blocks (pad selectedRecord3.preimage) = parts3 ∧
    parts3.flatten = pad selectedRecord3.preimage ∧
    (pad selectedRecord3.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_3 : CompressionChain initial parts3 after24 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_12 (CompressionChain.cons block_step_21 (CompressionChain.cons block_step_22 (CompressionChain.cons block_step_23 (CompressionChain.cons block_step_24 (CompressionChain.nil after24)))))))

theorem digest_checked_3 : digestHex after24 = selectedRecord3.digest := by decide +kernel

theorem hash_checked_3 : HashEvaluated selectedRecord3 :=
  sha256_of_chain input_checked_3 partition_checked_3.1
    chain_checked_3 digest_checked_3

noncomputable def selectedRecord4 : Phase17Preimages.HashRecord := Phase17Preimages.record3.grammarSeed
noncomputable def parts4 : List Block := [block11, block12, block21, block22, block25, block26]
theorem input_checked_4 : InputValid selectedRecord4.preimage := by decide +kernel

theorem partition_checked_4 :
    blocks (pad selectedRecord4.preimage) = parts4 ∧
    parts4.flatten = pad selectedRecord4.preimage ∧
    (pad selectedRecord4.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_4 : CompressionChain initial parts4 after26 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_12 (CompressionChain.cons block_step_21 (CompressionChain.cons block_step_22 (CompressionChain.cons block_step_25 (CompressionChain.cons block_step_26 (CompressionChain.nil after26)))))))

theorem digest_checked_4 : digestHex after26 = selectedRecord4.digest := by decide +kernel

theorem hash_checked_4 : HashEvaluated selectedRecord4 :=
  sha256_of_chain input_checked_4 partition_checked_4.1
    chain_checked_4 digest_checked_4

noncomputable def selectedRecord5 : Phase17Preimages.HashRecord := Phase17Preimages.record4.grammarSeed
noncomputable def parts5 : List Block := [block11, block12, block13, block14, block15, block27]
theorem input_checked_5 : InputValid selectedRecord5.preimage := by decide +kernel

theorem partition_checked_5 :
    blocks (pad selectedRecord5.preimage) = parts5 ∧
    parts5.flatten = pad selectedRecord5.preimage ∧
    (pad selectedRecord5.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_5 : CompressionChain initial parts5 after27 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_12 (CompressionChain.cons block_step_13 (CompressionChain.cons block_step_14 (CompressionChain.cons block_step_15 (CompressionChain.cons block_step_27 (CompressionChain.nil after27)))))))

theorem digest_checked_5 : digestHex after27 = selectedRecord5.digest := by decide +kernel

theorem hash_checked_5 : HashEvaluated selectedRecord5 :=
  sha256_of_chain input_checked_5 partition_checked_5.1
    chain_checked_5 digest_checked_5

noncomputable def selectedRecord6 : Phase17Preimages.HashRecord := Phase17Preimages.record5.grammarSeed
noncomputable def parts6 : List Block := [block11, block12, block28, block29, block30, block31]
theorem input_checked_6 : InputValid selectedRecord6.preimage := by decide +kernel

theorem partition_checked_6 :
    blocks (pad selectedRecord6.preimage) = parts6 ∧
    parts6.flatten = pad selectedRecord6.preimage ∧
    (pad selectedRecord6.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_6 : CompressionChain initial parts6 after31 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_12 (CompressionChain.cons block_step_28 (CompressionChain.cons block_step_29 (CompressionChain.cons block_step_30 (CompressionChain.cons block_step_31 (CompressionChain.nil after31)))))))

theorem digest_checked_6 : digestHex after31 = selectedRecord6.digest := by decide +kernel

theorem hash_checked_6 : HashEvaluated selectedRecord6 :=
  sha256_of_chain input_checked_6 partition_checked_6.1
    chain_checked_6 digest_checked_6

noncomputable def selectedRecord7 : Phase17Preimages.HashRecord := Phase17Preimages.record6.grammarSeed
noncomputable def parts7 : List Block := [block11, block12, block32, block33, block34, block35]
theorem input_checked_7 : InputValid selectedRecord7.preimage := by decide +kernel

theorem partition_checked_7 :
    blocks (pad selectedRecord7.preimage) = parts7 ∧
    parts7.flatten = pad selectedRecord7.preimage ∧
    (pad selectedRecord7.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_7 : CompressionChain initial parts7 after35 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_12 (CompressionChain.cons block_step_32 (CompressionChain.cons block_step_33 (CompressionChain.cons block_step_34 (CompressionChain.cons block_step_35 (CompressionChain.nil after35)))))))

theorem digest_checked_7 : digestHex after35 = selectedRecord7.digest := by decide +kernel

theorem hash_checked_7 : HashEvaluated selectedRecord7 :=
  sha256_of_chain input_checked_7 partition_checked_7.1
    chain_checked_7 digest_checked_7

noncomputable def selectedRecord8 : Phase17Preimages.HashRecord := Phase17Preimages.record7.grammarSeed
noncomputable def parts8 : List Block := [block11, block12, block28, block29, block36, block37]
theorem input_checked_8 : InputValid selectedRecord8.preimage := by decide +kernel

theorem partition_checked_8 :
    blocks (pad selectedRecord8.preimage) = parts8 ∧
    parts8.flatten = pad selectedRecord8.preimage ∧
    (pad selectedRecord8.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_8 : CompressionChain initial parts8 after37 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_12 (CompressionChain.cons block_step_28 (CompressionChain.cons block_step_29 (CompressionChain.cons block_step_36 (CompressionChain.cons block_step_37 (CompressionChain.nil after37)))))))

theorem digest_checked_8 : digestHex after37 = selectedRecord8.digest := by decide +kernel

theorem hash_checked_8 : HashEvaluated selectedRecord8 :=
  sha256_of_chain input_checked_8 partition_checked_8.1
    chain_checked_8 digest_checked_8

noncomputable def selectedRecord9 : Phase17Preimages.HashRecord := Phase17Preimages.record8.grammarSeed
noncomputable def parts9 : List Block := [block11, block12, block32, block33, block34, block38]
theorem input_checked_9 : InputValid selectedRecord9.preimage := by decide +kernel

theorem partition_checked_9 :
    blocks (pad selectedRecord9.preimage) = parts9 ∧
    parts9.flatten = pad selectedRecord9.preimage ∧
    (pad selectedRecord9.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_9 : CompressionChain initial parts9 after38 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_12 (CompressionChain.cons block_step_32 (CompressionChain.cons block_step_33 (CompressionChain.cons block_step_34 (CompressionChain.cons block_step_38 (CompressionChain.nil after38)))))))

theorem digest_checked_9 : digestHex after38 = selectedRecord9.digest := by decide +kernel

theorem hash_checked_9 : HashEvaluated selectedRecord9 :=
  sha256_of_chain input_checked_9 partition_checked_9.1
    chain_checked_9 digest_checked_9

noncomputable def selectedRecord10 : Phase17Preimages.HashRecord := Phase17Preimages.record9.grammarSeed
noncomputable def parts10 : List Block := [block11, block12, block39, block40, block41, block42]
theorem input_checked_10 : InputValid selectedRecord10.preimage := by decide +kernel

theorem partition_checked_10 :
    blocks (pad selectedRecord10.preimage) = parts10 ∧
    parts10.flatten = pad selectedRecord10.preimage ∧
    (pad selectedRecord10.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_10 : CompressionChain initial parts10 after42 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_12 (CompressionChain.cons block_step_39 (CompressionChain.cons block_step_40 (CompressionChain.cons block_step_41 (CompressionChain.cons block_step_42 (CompressionChain.nil after42)))))))

theorem digest_checked_10 : digestHex after42 = selectedRecord10.digest := by decide +kernel

theorem hash_checked_10 : HashEvaluated selectedRecord10 :=
  sha256_of_chain input_checked_10 partition_checked_10.1
    chain_checked_10 digest_checked_10

noncomputable def selectedRecord11 : Phase17Preimages.HashRecord := Phase17Preimages.record10.grammarSeed
noncomputable def parts11 : List Block := [block11, block12, block43, block44, block45, block46]
theorem input_checked_11 : InputValid selectedRecord11.preimage := by decide +kernel

theorem partition_checked_11 :
    blocks (pad selectedRecord11.preimage) = parts11 ∧
    parts11.flatten = pad selectedRecord11.preimage ∧
    (pad selectedRecord11.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_11 : CompressionChain initial parts11 after46 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_12 (CompressionChain.cons block_step_43 (CompressionChain.cons block_step_44 (CompressionChain.cons block_step_45 (CompressionChain.cons block_step_46 (CompressionChain.nil after46)))))))

theorem digest_checked_11 : digestHex after46 = selectedRecord11.digest := by decide +kernel

theorem hash_checked_11 : HashEvaluated selectedRecord11 :=
  sha256_of_chain input_checked_11 partition_checked_11.1
    chain_checked_11 digest_checked_11

noncomputable def selectedRecord12 : Phase17Preimages.HashRecord := Phase17Preimages.record11.grammarSeed
noncomputable def parts12 : List Block := [block11, block12, block47, block48, block49, block50]
theorem input_checked_12 : InputValid selectedRecord12.preimage := by decide +kernel

theorem partition_checked_12 :
    blocks (pad selectedRecord12.preimage) = parts12 ∧
    parts12.flatten = pad selectedRecord12.preimage ∧
    (pad selectedRecord12.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_12 : CompressionChain initial parts12 after50 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_12 (CompressionChain.cons block_step_47 (CompressionChain.cons block_step_48 (CompressionChain.cons block_step_49 (CompressionChain.cons block_step_50 (CompressionChain.nil after50)))))))

theorem digest_checked_12 : digestHex after50 = selectedRecord12.digest := by decide +kernel

theorem hash_checked_12 : HashEvaluated selectedRecord12 :=
  sha256_of_chain input_checked_12 partition_checked_12.1
    chain_checked_12 digest_checked_12

noncomputable def selectedRecord13 : Phase17Preimages.HashRecord := Phase17Preimages.record12.grammarSeed
noncomputable def parts13 : List Block := [block11, block12, block21, block22, block51, block52]
theorem input_checked_13 : InputValid selectedRecord13.preimage := by decide +kernel

theorem partition_checked_13 :
    blocks (pad selectedRecord13.preimage) = parts13 ∧
    parts13.flatten = pad selectedRecord13.preimage ∧
    (pad selectedRecord13.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_13 : CompressionChain initial parts13 after52 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_12 (CompressionChain.cons block_step_21 (CompressionChain.cons block_step_22 (CompressionChain.cons block_step_51 (CompressionChain.cons block_step_52 (CompressionChain.nil after52)))))))

theorem digest_checked_13 : digestHex after52 = selectedRecord13.digest := by decide +kernel

theorem hash_checked_13 : HashEvaluated selectedRecord13 :=
  sha256_of_chain input_checked_13 partition_checked_13.1
    chain_checked_13 digest_checked_13

noncomputable def selectedRecord14 : Phase17Preimages.HashRecord := Phase17Preimages.record13.grammarSeed
noncomputable def parts14 : List Block := [block11, block12, block43, block44, block45, block53]
theorem input_checked_14 : InputValid selectedRecord14.preimage := by decide +kernel

theorem partition_checked_14 :
    blocks (pad selectedRecord14.preimage) = parts14 ∧
    parts14.flatten = pad selectedRecord14.preimage ∧
    (pad selectedRecord14.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_14 : CompressionChain initial parts14 after53 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_12 (CompressionChain.cons block_step_43 (CompressionChain.cons block_step_44 (CompressionChain.cons block_step_45 (CompressionChain.cons block_step_53 (CompressionChain.nil after53)))))))

theorem digest_checked_14 : digestHex after53 = selectedRecord14.digest := by decide +kernel

theorem hash_checked_14 : HashEvaluated selectedRecord14 :=
  sha256_of_chain input_checked_14 partition_checked_14.1
    chain_checked_14 digest_checked_14

noncomputable def selectedRecord15 : Phase17Preimages.HashRecord := Phase17Preimages.record14.grammarSeed
noncomputable def parts15 : List Block := [block11, block12, block47, block48, block54, block55]
theorem input_checked_15 : InputValid selectedRecord15.preimage := by decide +kernel

theorem partition_checked_15 :
    blocks (pad selectedRecord15.preimage) = parts15 ∧
    parts15.flatten = pad selectedRecord15.preimage ∧
    (pad selectedRecord15.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_15 : CompressionChain initial parts15 after55 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_12 (CompressionChain.cons block_step_47 (CompressionChain.cons block_step_48 (CompressionChain.cons block_step_54 (CompressionChain.cons block_step_55 (CompressionChain.nil after55)))))))

theorem digest_checked_15 : digestHex after55 = selectedRecord15.digest := by decide +kernel

theorem hash_checked_15 : HashEvaluated selectedRecord15 :=
  sha256_of_chain input_checked_15 partition_checked_15.1
    chain_checked_15 digest_checked_15

noncomputable def selectedRecord16 : Phase17Preimages.HashRecord := Phase17Preimages.record15.grammarSeed
noncomputable def parts16 : List Block := [block11, block12, block32, block33, block34, block56]
theorem input_checked_16 : InputValid selectedRecord16.preimage := by decide +kernel

theorem partition_checked_16 :
    blocks (pad selectedRecord16.preimage) = parts16 ∧
    parts16.flatten = pad selectedRecord16.preimage ∧
    (pad selectedRecord16.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_16 : CompressionChain initial parts16 after56 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_12 (CompressionChain.cons block_step_32 (CompressionChain.cons block_step_33 (CompressionChain.cons block_step_34 (CompressionChain.cons block_step_56 (CompressionChain.nil after56)))))))

theorem digest_checked_16 : digestHex after56 = selectedRecord16.digest := by decide +kernel

theorem hash_checked_16 : HashEvaluated selectedRecord16 :=
  sha256_of_chain input_checked_16 partition_checked_16.1
    chain_checked_16 digest_checked_16

noncomputable def selectedRecord17 : Phase17Preimages.HashRecord := Phase17Preimages.record16.grammarSeed
noncomputable def parts17 : List Block := [block11, block12, block28, block29, block57, block58]
theorem input_checked_17 : InputValid selectedRecord17.preimage := by decide +kernel

theorem partition_checked_17 :
    blocks (pad selectedRecord17.preimage) = parts17 ∧
    parts17.flatten = pad selectedRecord17.preimage ∧
    (pad selectedRecord17.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_17 : CompressionChain initial parts17 after58 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_12 (CompressionChain.cons block_step_28 (CompressionChain.cons block_step_29 (CompressionChain.cons block_step_57 (CompressionChain.cons block_step_58 (CompressionChain.nil after58)))))))

theorem digest_checked_17 : digestHex after58 = selectedRecord17.digest := by decide +kernel

theorem hash_checked_17 : HashEvaluated selectedRecord17 :=
  sha256_of_chain input_checked_17 partition_checked_17.1
    chain_checked_17 digest_checked_17

noncomputable def selectedRecord18 : Phase17Preimages.HashRecord := Phase17Preimages.record17.grammarSeed
noncomputable def parts18 : List Block := [block11, block12, block32, block33, block34, block59]
theorem input_checked_18 : InputValid selectedRecord18.preimage := by decide +kernel

theorem partition_checked_18 :
    blocks (pad selectedRecord18.preimage) = parts18 ∧
    parts18.flatten = pad selectedRecord18.preimage ∧
    (pad selectedRecord18.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_18 : CompressionChain initial parts18 after59 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_12 (CompressionChain.cons block_step_32 (CompressionChain.cons block_step_33 (CompressionChain.cons block_step_34 (CompressionChain.cons block_step_59 (CompressionChain.nil after59)))))))

theorem digest_checked_18 : digestHex after59 = selectedRecord18.digest := by decide +kernel

theorem hash_checked_18 : HashEvaluated selectedRecord18 :=
  sha256_of_chain input_checked_18 partition_checked_18.1
    chain_checked_18 digest_checked_18

noncomputable def selectedRecord19 : Phase17Preimages.HashRecord := Phase17Preimages.record18.grammarSeed
noncomputable def parts19 : List Block := [block11, block12, block39, block40, block41, block60]
theorem input_checked_19 : InputValid selectedRecord19.preimage := by decide +kernel

theorem partition_checked_19 :
    blocks (pad selectedRecord19.preimage) = parts19 ∧
    parts19.flatten = pad selectedRecord19.preimage ∧
    (pad selectedRecord19.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_19 : CompressionChain initial parts19 after60 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_12 (CompressionChain.cons block_step_39 (CompressionChain.cons block_step_40 (CompressionChain.cons block_step_41 (CompressionChain.cons block_step_60 (CompressionChain.nil after60)))))))

theorem digest_checked_19 : digestHex after60 = selectedRecord19.digest := by decide +kernel

theorem hash_checked_19 : HashEvaluated selectedRecord19 :=
  sha256_of_chain input_checked_19 partition_checked_19.1
    chain_checked_19 digest_checked_19

noncomputable def selectedRecord20 : Phase17Preimages.HashRecord := Phase17Preimages.record19.grammarSeed
noncomputable def parts20 : List Block := [block11, block12, block13, block14, block15, block61]
theorem input_checked_20 : InputValid selectedRecord20.preimage := by decide +kernel

theorem partition_checked_20 :
    blocks (pad selectedRecord20.preimage) = parts20 ∧
    parts20.flatten = pad selectedRecord20.preimage ∧
    (pad selectedRecord20.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_20 : CompressionChain initial parts20 after61 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_12 (CompressionChain.cons block_step_13 (CompressionChain.cons block_step_14 (CompressionChain.cons block_step_15 (CompressionChain.cons block_step_61 (CompressionChain.nil after61)))))))

theorem digest_checked_20 : digestHex after61 = selectedRecord20.digest := by decide +kernel

theorem hash_checked_20 : HashEvaluated selectedRecord20 :=
  sha256_of_chain input_checked_20 partition_checked_20.1
    chain_checked_20 digest_checked_20

noncomputable def selectedRecord21 : Phase17Preimages.HashRecord := Phase17Preimages.record20.grammarSeed
noncomputable def parts21 : List Block := [block11, block12, block39, block40, block41, block62]
theorem input_checked_21 : InputValid selectedRecord21.preimage := by decide +kernel

theorem partition_checked_21 :
    blocks (pad selectedRecord21.preimage) = parts21 ∧
    parts21.flatten = pad selectedRecord21.preimage ∧
    (pad selectedRecord21.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_21 : CompressionChain initial parts21 after62 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_12 (CompressionChain.cons block_step_39 (CompressionChain.cons block_step_40 (CompressionChain.cons block_step_41 (CompressionChain.cons block_step_62 (CompressionChain.nil after62)))))))

theorem digest_checked_21 : digestHex after62 = selectedRecord21.digest := by decide +kernel

theorem hash_checked_21 : HashEvaluated selectedRecord21 :=
  sha256_of_chain input_checked_21 partition_checked_21.1
    chain_checked_21 digest_checked_21

noncomputable def selectedRecord22 : Phase17Preimages.HashRecord := Phase17Preimages.record21.grammarSeed
noncomputable def parts22 : List Block := [block11, block12, block17, block18, block63, block64]
theorem input_checked_22 : InputValid selectedRecord22.preimage := by decide +kernel

theorem partition_checked_22 :
    blocks (pad selectedRecord22.preimage) = parts22 ∧
    parts22.flatten = pad selectedRecord22.preimage ∧
    (pad selectedRecord22.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_22 : CompressionChain initial parts22 after64 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_12 (CompressionChain.cons block_step_17 (CompressionChain.cons block_step_18 (CompressionChain.cons block_step_63 (CompressionChain.cons block_step_64 (CompressionChain.nil after64)))))))

theorem digest_checked_22 : digestHex after64 = selectedRecord22.digest := by decide +kernel

theorem hash_checked_22 : HashEvaluated selectedRecord22 :=
  sha256_of_chain input_checked_22 partition_checked_22.1
    chain_checked_22 digest_checked_22

noncomputable def selectedRecord23 : Phase17Preimages.HashRecord := Phase17Preimages.record22.grammarSeed
noncomputable def parts23 : List Block := [block11, block12, block21, block22, block65, block66]
theorem input_checked_23 : InputValid selectedRecord23.preimage := by decide +kernel

theorem partition_checked_23 :
    blocks (pad selectedRecord23.preimage) = parts23 ∧
    parts23.flatten = pad selectedRecord23.preimage ∧
    (pad selectedRecord23.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_23 : CompressionChain initial parts23 after66 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_12 (CompressionChain.cons block_step_21 (CompressionChain.cons block_step_22 (CompressionChain.cons block_step_65 (CompressionChain.cons block_step_66 (CompressionChain.nil after66)))))))

theorem digest_checked_23 : digestHex after66 = selectedRecord23.digest := by decide +kernel

theorem hash_checked_23 : HashEvaluated selectedRecord23 :=
  sha256_of_chain input_checked_23 partition_checked_23.1
    chain_checked_23 digest_checked_23

noncomputable def selectedRecord24 : Phase17Preimages.HashRecord := Phase17Preimages.record23.grammarSeed
noncomputable def parts24 : List Block := [block11, block12, block39, block40, block41, block67]
theorem input_checked_24 : InputValid selectedRecord24.preimage := by decide +kernel

theorem partition_checked_24 :
    blocks (pad selectedRecord24.preimage) = parts24 ∧
    parts24.flatten = pad selectedRecord24.preimage ∧
    (pad selectedRecord24.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_24 : CompressionChain initial parts24 after67 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_12 (CompressionChain.cons block_step_39 (CompressionChain.cons block_step_40 (CompressionChain.cons block_step_41 (CompressionChain.cons block_step_67 (CompressionChain.nil after67)))))))

theorem digest_checked_24 : digestHex after67 = selectedRecord24.digest := by decide +kernel

theorem hash_checked_24 : HashEvaluated selectedRecord24 :=
  sha256_of_chain input_checked_24 partition_checked_24.1
    chain_checked_24 digest_checked_24

noncomputable def selectedRecord25 : Phase17Preimages.HashRecord := Phase17Preimages.record24.grammarSeed
noncomputable def parts25 : List Block := [block11, block12, block47, block48, block68, block69]
theorem input_checked_25 : InputValid selectedRecord25.preimage := by decide +kernel

theorem partition_checked_25 :
    blocks (pad selectedRecord25.preimage) = parts25 ∧
    parts25.flatten = pad selectedRecord25.preimage ∧
    (pad selectedRecord25.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_25 : CompressionChain initial parts25 after69 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_12 (CompressionChain.cons block_step_47 (CompressionChain.cons block_step_48 (CompressionChain.cons block_step_68 (CompressionChain.cons block_step_69 (CompressionChain.nil after69)))))))

theorem digest_checked_25 : digestHex after69 = selectedRecord25.digest := by decide +kernel

theorem hash_checked_25 : HashEvaluated selectedRecord25 :=
  sha256_of_chain input_checked_25 partition_checked_25.1
    chain_checked_25 digest_checked_25

noncomputable def selectedRecord26 : Phase17Preimages.HashRecord := Phase17Preimages.record25.grammarSeed
noncomputable def parts26 : List Block := [block11, block12, block28, block29, block70, block71]
theorem input_checked_26 : InputValid selectedRecord26.preimage := by decide +kernel

theorem partition_checked_26 :
    blocks (pad selectedRecord26.preimage) = parts26 ∧
    parts26.flatten = pad selectedRecord26.preimage ∧
    (pad selectedRecord26.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_26 : CompressionChain initial parts26 after71 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_12 (CompressionChain.cons block_step_28 (CompressionChain.cons block_step_29 (CompressionChain.cons block_step_70 (CompressionChain.cons block_step_71 (CompressionChain.nil after71)))))))

theorem digest_checked_26 : digestHex after71 = selectedRecord26.digest := by decide +kernel

theorem hash_checked_26 : HashEvaluated selectedRecord26 :=
  sha256_of_chain input_checked_26 partition_checked_26.1
    chain_checked_26 digest_checked_26

noncomputable def selectedRecord27 : Phase17Preimages.HashRecord := Phase17Preimages.record26.grammarSeed
noncomputable def parts27 : List Block := [block11, block12, block13, block14, block15, block72]
theorem input_checked_27 : InputValid selectedRecord27.preimage := by decide +kernel

theorem partition_checked_27 :
    blocks (pad selectedRecord27.preimage) = parts27 ∧
    parts27.flatten = pad selectedRecord27.preimage ∧
    (pad selectedRecord27.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_27 : CompressionChain initial parts27 after72 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_12 (CompressionChain.cons block_step_13 (CompressionChain.cons block_step_14 (CompressionChain.cons block_step_15 (CompressionChain.cons block_step_72 (CompressionChain.nil after72)))))))

theorem digest_checked_27 : digestHex after72 = selectedRecord27.digest := by decide +kernel

theorem hash_checked_27 : HashEvaluated selectedRecord27 :=
  sha256_of_chain input_checked_27 partition_checked_27.1
    chain_checked_27 digest_checked_27

noncomputable def selectedRecord28 : Phase17Preimages.HashRecord := Phase17Preimages.record27.grammarSeed
noncomputable def parts28 : List Block := [block11, block12, block43, block44, block45, block73]
theorem input_checked_28 : InputValid selectedRecord28.preimage := by decide +kernel

theorem partition_checked_28 :
    blocks (pad selectedRecord28.preimage) = parts28 ∧
    parts28.flatten = pad selectedRecord28.preimage ∧
    (pad selectedRecord28.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_28 : CompressionChain initial parts28 after73 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_12 (CompressionChain.cons block_step_43 (CompressionChain.cons block_step_44 (CompressionChain.cons block_step_45 (CompressionChain.cons block_step_73 (CompressionChain.nil after73)))))))

theorem digest_checked_28 : digestHex after73 = selectedRecord28.digest := by decide +kernel

theorem hash_checked_28 : HashEvaluated selectedRecord28 :=
  sha256_of_chain input_checked_28 partition_checked_28.1
    chain_checked_28 digest_checked_28

noncomputable def selectedRecord29 : Phase17Preimages.HashRecord := Phase17Preimages.record28.grammarSeed
noncomputable def parts29 : List Block := [block11, block12, block17, block18, block74, block75]
theorem input_checked_29 : InputValid selectedRecord29.preimage := by decide +kernel

theorem partition_checked_29 :
    blocks (pad selectedRecord29.preimage) = parts29 ∧
    parts29.flatten = pad selectedRecord29.preimage ∧
    (pad selectedRecord29.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_29 : CompressionChain initial parts29 after75 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_12 (CompressionChain.cons block_step_17 (CompressionChain.cons block_step_18 (CompressionChain.cons block_step_74 (CompressionChain.cons block_step_75 (CompressionChain.nil after75)))))))

theorem digest_checked_29 : digestHex after75 = selectedRecord29.digest := by decide +kernel

theorem hash_checked_29 : HashEvaluated selectedRecord29 :=
  sha256_of_chain input_checked_29 partition_checked_29.1
    chain_checked_29 digest_checked_29

noncomputable def selectedRecord30 : Phase17Preimages.HashRecord := Phase17Preimages.record29.grammarSeed
noncomputable def parts30 : List Block := [block11, block12, block17, block18, block76, block77]
theorem input_checked_30 : InputValid selectedRecord30.preimage := by decide +kernel

theorem partition_checked_30 :
    blocks (pad selectedRecord30.preimage) = parts30 ∧
    parts30.flatten = pad selectedRecord30.preimage ∧
    (pad selectedRecord30.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_30 : CompressionChain initial parts30 after77 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_12 (CompressionChain.cons block_step_17 (CompressionChain.cons block_step_18 (CompressionChain.cons block_step_76 (CompressionChain.cons block_step_77 (CompressionChain.nil after77)))))))

theorem digest_checked_30 : digestHex after77 = selectedRecord30.digest := by decide +kernel

theorem hash_checked_30 : HashEvaluated selectedRecord30 :=
  sha256_of_chain input_checked_30 partition_checked_30.1
    chain_checked_30 digest_checked_30

noncomputable def selectedRecord31 : Phase17Preimages.HashRecord := Phase17Preimages.record30.grammarSeed
noncomputable def parts31 : List Block := [block11, block12, block47, block48, block78, block79]
theorem input_checked_31 : InputValid selectedRecord31.preimage := by decide +kernel

theorem partition_checked_31 :
    blocks (pad selectedRecord31.preimage) = parts31 ∧
    parts31.flatten = pad selectedRecord31.preimage ∧
    (pad selectedRecord31.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_31 : CompressionChain initial parts31 after79 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_12 (CompressionChain.cons block_step_47 (CompressionChain.cons block_step_48 (CompressionChain.cons block_step_78 (CompressionChain.cons block_step_79 (CompressionChain.nil after79)))))))

theorem digest_checked_31 : digestHex after79 = selectedRecord31.digest := by decide +kernel

theorem hash_checked_31 : HashEvaluated selectedRecord31 :=
  sha256_of_chain input_checked_31 partition_checked_31.1
    chain_checked_31 digest_checked_31

noncomputable def selectedRecord32 : Phase17Preimages.HashRecord := Phase17Preimages.record31.grammarSeed
noncomputable def parts32 : List Block := [block11, block12, block43, block44, block45, block80]
theorem input_checked_32 : InputValid selectedRecord32.preimage := by decide +kernel

theorem partition_checked_32 :
    blocks (pad selectedRecord32.preimage) = parts32 ∧
    parts32.flatten = pad selectedRecord32.preimage ∧
    (pad selectedRecord32.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_32 : CompressionChain initial parts32 after80 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_12 (CompressionChain.cons block_step_43 (CompressionChain.cons block_step_44 (CompressionChain.cons block_step_45 (CompressionChain.cons block_step_80 (CompressionChain.nil after80)))))))

theorem digest_checked_32 : digestHex after80 = selectedRecord32.digest := by decide +kernel

theorem hash_checked_32 : HashEvaluated selectedRecord32 :=
  sha256_of_chain input_checked_32 partition_checked_32.1
    chain_checked_32 digest_checked_32

noncomputable def selectedRecord33 : Phase17Preimages.HashRecord := Phase17Preimages.record0.program
noncomputable def parts33 : List Block := [block81, block82, block83, block84, block85, block86]
theorem input_checked_33 : InputValid selectedRecord33.preimage := by decide +kernel

theorem partition_checked_33 :
    blocks (pad selectedRecord33.preimage) = parts33 ∧
    parts33.flatten = pad selectedRecord33.preimage ∧
    (pad selectedRecord33.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_33 : CompressionChain initial parts33 after86 := by
  exact (CompressionChain.cons block_step_81 (CompressionChain.cons block_step_82 (CompressionChain.cons block_step_83 (CompressionChain.cons block_step_84 (CompressionChain.cons block_step_85 (CompressionChain.cons block_step_86 (CompressionChain.nil after86)))))))

theorem digest_checked_33 : digestHex after86 = selectedRecord33.digest := by decide +kernel

theorem hash_checked_33 : HashEvaluated selectedRecord33 :=
  sha256_of_chain input_checked_33 partition_checked_33.1
    chain_checked_33 digest_checked_33

noncomputable def selectedRecord34 : Phase17Preimages.HashRecord := Phase17Preimages.record1.program
noncomputable def parts34 : List Block := [block87, block88, block89, block90, block91, block92]
theorem input_checked_34 : InputValid selectedRecord34.preimage := by decide +kernel

theorem partition_checked_34 :
    blocks (pad selectedRecord34.preimage) = parts34 ∧
    parts34.flatten = pad selectedRecord34.preimage ∧
    (pad selectedRecord34.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_34 : CompressionChain initial parts34 after92 := by
  exact (CompressionChain.cons block_step_87 (CompressionChain.cons block_step_88 (CompressionChain.cons block_step_89 (CompressionChain.cons block_step_90 (CompressionChain.cons block_step_91 (CompressionChain.cons block_step_92 (CompressionChain.nil after92)))))))

theorem digest_checked_34 : digestHex after92 = selectedRecord34.digest := by decide +kernel

theorem hash_checked_34 : HashEvaluated selectedRecord34 :=
  sha256_of_chain input_checked_34 partition_checked_34.1
    chain_checked_34 digest_checked_34

noncomputable def selectedRecord35 : Phase17Preimages.HashRecord := Phase17Preimages.record2.program
noncomputable def parts35 : List Block := [block93, block94, block95, block96, block97, block98]
theorem input_checked_35 : InputValid selectedRecord35.preimage := by decide +kernel

theorem partition_checked_35 :
    blocks (pad selectedRecord35.preimage) = parts35 ∧
    parts35.flatten = pad selectedRecord35.preimage ∧
    (pad selectedRecord35.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_35 : CompressionChain initial parts35 after98 := by
  exact (CompressionChain.cons block_step_93 (CompressionChain.cons block_step_94 (CompressionChain.cons block_step_95 (CompressionChain.cons block_step_96 (CompressionChain.cons block_step_97 (CompressionChain.cons block_step_98 (CompressionChain.nil after98)))))))

theorem digest_checked_35 : digestHex after98 = selectedRecord35.digest := by decide +kernel

theorem hash_checked_35 : HashEvaluated selectedRecord35 :=
  sha256_of_chain input_checked_35 partition_checked_35.1
    chain_checked_35 digest_checked_35

noncomputable def selectedRecord36 : Phase17Preimages.HashRecord := Phase17Preimages.record3.program
noncomputable def parts36 : List Block := [block93, block94, block99, block100, block101, block102]
theorem input_checked_36 : InputValid selectedRecord36.preimage := by decide +kernel

theorem partition_checked_36 :
    blocks (pad selectedRecord36.preimage) = parts36 ∧
    parts36.flatten = pad selectedRecord36.preimage ∧
    (pad selectedRecord36.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_36 : CompressionChain initial parts36 after102 := by
  exact (CompressionChain.cons block_step_93 (CompressionChain.cons block_step_94 (CompressionChain.cons block_step_99 (CompressionChain.cons block_step_100 (CompressionChain.cons block_step_101 (CompressionChain.cons block_step_102 (CompressionChain.nil after102)))))))

theorem digest_checked_36 : digestHex after102 = selectedRecord36.digest := by decide +kernel

theorem hash_checked_36 : HashEvaluated selectedRecord36 :=
  sha256_of_chain input_checked_36 partition_checked_36.1
    chain_checked_36 digest_checked_36

noncomputable def selectedRecord37 : Phase17Preimages.HashRecord := Phase17Preimages.record4.program
noncomputable def parts37 : List Block := [block81, block82, block103, block104, block105, block106]
theorem input_checked_37 : InputValid selectedRecord37.preimage := by decide +kernel

theorem partition_checked_37 :
    blocks (pad selectedRecord37.preimage) = parts37 ∧
    parts37.flatten = pad selectedRecord37.preimage ∧
    (pad selectedRecord37.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_37 : CompressionChain initial parts37 after106 := by
  exact (CompressionChain.cons block_step_81 (CompressionChain.cons block_step_82 (CompressionChain.cons block_step_103 (CompressionChain.cons block_step_104 (CompressionChain.cons block_step_105 (CompressionChain.cons block_step_106 (CompressionChain.nil after106)))))))

theorem digest_checked_37 : digestHex after106 = selectedRecord37.digest := by decide +kernel

theorem hash_checked_37 : HashEvaluated selectedRecord37 :=
  sha256_of_chain input_checked_37 partition_checked_37.1
    chain_checked_37 digest_checked_37

noncomputable def selectedRecord38 : Phase17Preimages.HashRecord := Phase17Preimages.record5.program
noncomputable def parts38 : List Block := [block107, block108, block109, block110, block111, block112]
theorem input_checked_38 : InputValid selectedRecord38.preimage := by decide +kernel

theorem partition_checked_38 :
    blocks (pad selectedRecord38.preimage) = parts38 ∧
    parts38.flatten = pad selectedRecord38.preimage ∧
    (pad selectedRecord38.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_38 : CompressionChain initial parts38 after112 := by
  exact (CompressionChain.cons block_step_107 (CompressionChain.cons block_step_108 (CompressionChain.cons block_step_109 (CompressionChain.cons block_step_110 (CompressionChain.cons block_step_111 (CompressionChain.cons block_step_112 (CompressionChain.nil after112)))))))

theorem digest_checked_38 : digestHex after112 = selectedRecord38.digest := by decide +kernel

theorem hash_checked_38 : HashEvaluated selectedRecord38 :=
  sha256_of_chain input_checked_38 partition_checked_38.1
    chain_checked_38 digest_checked_38

noncomputable def selectedRecord39 : Phase17Preimages.HashRecord := Phase17Preimages.record6.program
noncomputable def parts39 : List Block := [block113, block114, block115, block116, block117, block118]
theorem input_checked_39 : InputValid selectedRecord39.preimage := by decide +kernel

theorem partition_checked_39 :
    blocks (pad selectedRecord39.preimage) = parts39 ∧
    parts39.flatten = pad selectedRecord39.preimage ∧
    (pad selectedRecord39.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_39 : CompressionChain initial parts39 after118 := by
  exact (CompressionChain.cons block_step_113 (CompressionChain.cons block_step_114 (CompressionChain.cons block_step_115 (CompressionChain.cons block_step_116 (CompressionChain.cons block_step_117 (CompressionChain.cons block_step_118 (CompressionChain.nil after118)))))))

theorem digest_checked_39 : digestHex after118 = selectedRecord39.digest := by decide +kernel

theorem hash_checked_39 : HashEvaluated selectedRecord39 :=
  sha256_of_chain input_checked_39 partition_checked_39.1
    chain_checked_39 digest_checked_39

noncomputable def selectedRecord40 : Phase17Preimages.HashRecord := Phase17Preimages.record7.program
noncomputable def parts40 : List Block := [block107, block108, block119, block120, block121, block122]
theorem input_checked_40 : InputValid selectedRecord40.preimage := by decide +kernel

theorem partition_checked_40 :
    blocks (pad selectedRecord40.preimage) = parts40 ∧
    parts40.flatten = pad selectedRecord40.preimage ∧
    (pad selectedRecord40.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_40 : CompressionChain initial parts40 after122 := by
  exact (CompressionChain.cons block_step_107 (CompressionChain.cons block_step_108 (CompressionChain.cons block_step_119 (CompressionChain.cons block_step_120 (CompressionChain.cons block_step_121 (CompressionChain.cons block_step_122 (CompressionChain.nil after122)))))))

theorem digest_checked_40 : digestHex after122 = selectedRecord40.digest := by decide +kernel

theorem hash_checked_40 : HashEvaluated selectedRecord40 :=
  sha256_of_chain input_checked_40 partition_checked_40.1
    chain_checked_40 digest_checked_40

noncomputable def selectedRecord41 : Phase17Preimages.HashRecord := Phase17Preimages.record8.program
noncomputable def parts41 : List Block := [block113, block114, block123, block124, block125, block126]
theorem input_checked_41 : InputValid selectedRecord41.preimage := by decide +kernel

theorem partition_checked_41 :
    blocks (pad selectedRecord41.preimage) = parts41 ∧
    parts41.flatten = pad selectedRecord41.preimage ∧
    (pad selectedRecord41.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_41 : CompressionChain initial parts41 after126 := by
  exact (CompressionChain.cons block_step_113 (CompressionChain.cons block_step_114 (CompressionChain.cons block_step_123 (CompressionChain.cons block_step_124 (CompressionChain.cons block_step_125 (CompressionChain.cons block_step_126 (CompressionChain.nil after126)))))))

theorem digest_checked_41 : digestHex after126 = selectedRecord41.digest := by decide +kernel

theorem hash_checked_41 : HashEvaluated selectedRecord41 :=
  sha256_of_chain input_checked_41 partition_checked_41.1
    chain_checked_41 digest_checked_41

noncomputable def selectedRecord42 : Phase17Preimages.HashRecord := Phase17Preimages.record9.program
noncomputable def parts42 : List Block := [block127, block128, block129, block130, block131, block132]
theorem input_checked_42 : InputValid selectedRecord42.preimage := by decide +kernel

theorem partition_checked_42 :
    blocks (pad selectedRecord42.preimage) = parts42 ∧
    parts42.flatten = pad selectedRecord42.preimage ∧
    (pad selectedRecord42.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_42 : CompressionChain initial parts42 after132 := by
  exact (CompressionChain.cons block_step_127 (CompressionChain.cons block_step_128 (CompressionChain.cons block_step_129 (CompressionChain.cons block_step_130 (CompressionChain.cons block_step_131 (CompressionChain.cons block_step_132 (CompressionChain.nil after132)))))))

theorem digest_checked_42 : digestHex after132 = selectedRecord42.digest := by decide +kernel

theorem hash_checked_42 : HashEvaluated selectedRecord42 :=
  sha256_of_chain input_checked_42 partition_checked_42.1
    chain_checked_42 digest_checked_42

noncomputable def selectedRecord43 : Phase17Preimages.HashRecord := Phase17Preimages.record10.program
noncomputable def parts43 : List Block := [block133, block134, block135, block136, block137, block138]
theorem input_checked_43 : InputValid selectedRecord43.preimage := by decide +kernel

theorem partition_checked_43 :
    blocks (pad selectedRecord43.preimage) = parts43 ∧
    parts43.flatten = pad selectedRecord43.preimage ∧
    (pad selectedRecord43.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_43 : CompressionChain initial parts43 after138 := by
  exact (CompressionChain.cons block_step_133 (CompressionChain.cons block_step_134 (CompressionChain.cons block_step_135 (CompressionChain.cons block_step_136 (CompressionChain.cons block_step_137 (CompressionChain.cons block_step_138 (CompressionChain.nil after138)))))))

theorem digest_checked_43 : digestHex after138 = selectedRecord43.digest := by decide +kernel

theorem hash_checked_43 : HashEvaluated selectedRecord43 :=
  sha256_of_chain input_checked_43 partition_checked_43.1
    chain_checked_43 digest_checked_43

noncomputable def selectedRecord44 : Phase17Preimages.HashRecord := Phase17Preimages.record11.program
noncomputable def parts44 : List Block := [block139, block140, block141, block142, block143, block144]
theorem input_checked_44 : InputValid selectedRecord44.preimage := by decide +kernel

theorem partition_checked_44 :
    blocks (pad selectedRecord44.preimage) = parts44 ∧
    parts44.flatten = pad selectedRecord44.preimage ∧
    (pad selectedRecord44.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_44 : CompressionChain initial parts44 after144 := by
  exact (CompressionChain.cons block_step_139 (CompressionChain.cons block_step_140 (CompressionChain.cons block_step_141 (CompressionChain.cons block_step_142 (CompressionChain.cons block_step_143 (CompressionChain.cons block_step_144 (CompressionChain.nil after144)))))))

theorem digest_checked_44 : digestHex after144 = selectedRecord44.digest := by decide +kernel

theorem hash_checked_44 : HashEvaluated selectedRecord44 :=
  sha256_of_chain input_checked_44 partition_checked_44.1
    chain_checked_44 digest_checked_44

noncomputable def selectedRecord45 : Phase17Preimages.HashRecord := Phase17Preimages.record12.program
noncomputable def parts45 : List Block := [block93, block94, block145, block146, block147, block148]
theorem input_checked_45 : InputValid selectedRecord45.preimage := by decide +kernel

theorem partition_checked_45 :
    blocks (pad selectedRecord45.preimage) = parts45 ∧
    parts45.flatten = pad selectedRecord45.preimage ∧
    (pad selectedRecord45.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_45 : CompressionChain initial parts45 after148 := by
  exact (CompressionChain.cons block_step_93 (CompressionChain.cons block_step_94 (CompressionChain.cons block_step_145 (CompressionChain.cons block_step_146 (CompressionChain.cons block_step_147 (CompressionChain.cons block_step_148 (CompressionChain.nil after148)))))))

theorem digest_checked_45 : digestHex after148 = selectedRecord45.digest := by decide +kernel

theorem hash_checked_45 : HashEvaluated selectedRecord45 :=
  sha256_of_chain input_checked_45 partition_checked_45.1
    chain_checked_45 digest_checked_45

noncomputable def selectedRecord46 : Phase17Preimages.HashRecord := Phase17Preimages.record13.program
noncomputable def parts46 : List Block := [block133, block134, block149, block150, block151, block152]
theorem input_checked_46 : InputValid selectedRecord46.preimage := by decide +kernel

theorem partition_checked_46 :
    blocks (pad selectedRecord46.preimage) = parts46 ∧
    parts46.flatten = pad selectedRecord46.preimage ∧
    (pad selectedRecord46.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_46 : CompressionChain initial parts46 after152 := by
  exact (CompressionChain.cons block_step_133 (CompressionChain.cons block_step_134 (CompressionChain.cons block_step_149 (CompressionChain.cons block_step_150 (CompressionChain.cons block_step_151 (CompressionChain.cons block_step_152 (CompressionChain.nil after152)))))))

theorem digest_checked_46 : digestHex after152 = selectedRecord46.digest := by decide +kernel

theorem hash_checked_46 : HashEvaluated selectedRecord46 :=
  sha256_of_chain input_checked_46 partition_checked_46.1
    chain_checked_46 digest_checked_46

noncomputable def selectedRecord47 : Phase17Preimages.HashRecord := Phase17Preimages.record14.program
noncomputable def parts47 : List Block := [block139, block140, block153, block154, block155, block156]
theorem input_checked_47 : InputValid selectedRecord47.preimage := by decide +kernel

theorem partition_checked_47 :
    blocks (pad selectedRecord47.preimage) = parts47 ∧
    parts47.flatten = pad selectedRecord47.preimage ∧
    (pad selectedRecord47.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_47 : CompressionChain initial parts47 after156 := by
  exact (CompressionChain.cons block_step_139 (CompressionChain.cons block_step_140 (CompressionChain.cons block_step_153 (CompressionChain.cons block_step_154 (CompressionChain.cons block_step_155 (CompressionChain.cons block_step_156 (CompressionChain.nil after156)))))))

theorem digest_checked_47 : digestHex after156 = selectedRecord47.digest := by decide +kernel

theorem hash_checked_47 : HashEvaluated selectedRecord47 :=
  sha256_of_chain input_checked_47 partition_checked_47.1
    chain_checked_47 digest_checked_47

noncomputable def selectedRecord48 : Phase17Preimages.HashRecord := Phase17Preimages.record15.program
noncomputable def parts48 : List Block := [block113, block114, block157, block158, block159, block160]
theorem input_checked_48 : InputValid selectedRecord48.preimage := by decide +kernel

theorem partition_checked_48 :
    blocks (pad selectedRecord48.preimage) = parts48 ∧
    parts48.flatten = pad selectedRecord48.preimage ∧
    (pad selectedRecord48.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_48 : CompressionChain initial parts48 after160 := by
  exact (CompressionChain.cons block_step_113 (CompressionChain.cons block_step_114 (CompressionChain.cons block_step_157 (CompressionChain.cons block_step_158 (CompressionChain.cons block_step_159 (CompressionChain.cons block_step_160 (CompressionChain.nil after160)))))))

theorem digest_checked_48 : digestHex after160 = selectedRecord48.digest := by decide +kernel

theorem hash_checked_48 : HashEvaluated selectedRecord48 :=
  sha256_of_chain input_checked_48 partition_checked_48.1
    chain_checked_48 digest_checked_48

noncomputable def selectedRecord49 : Phase17Preimages.HashRecord := Phase17Preimages.record16.program
noncomputable def parts49 : List Block := [block107, block108, block161, block162, block163, block164]
theorem input_checked_49 : InputValid selectedRecord49.preimage := by decide +kernel

theorem partition_checked_49 :
    blocks (pad selectedRecord49.preimage) = parts49 ∧
    parts49.flatten = pad selectedRecord49.preimage ∧
    (pad selectedRecord49.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_49 : CompressionChain initial parts49 after164 := by
  exact (CompressionChain.cons block_step_107 (CompressionChain.cons block_step_108 (CompressionChain.cons block_step_161 (CompressionChain.cons block_step_162 (CompressionChain.cons block_step_163 (CompressionChain.cons block_step_164 (CompressionChain.nil after164)))))))

theorem digest_checked_49 : digestHex after164 = selectedRecord49.digest := by decide +kernel

theorem hash_checked_49 : HashEvaluated selectedRecord49 :=
  sha256_of_chain input_checked_49 partition_checked_49.1
    chain_checked_49 digest_checked_49

noncomputable def selectedRecord50 : Phase17Preimages.HashRecord := Phase17Preimages.record17.program
noncomputable def parts50 : List Block := [block113, block114, block165, block166, block167, block168]
theorem input_checked_50 : InputValid selectedRecord50.preimage := by decide +kernel

theorem partition_checked_50 :
    blocks (pad selectedRecord50.preimage) = parts50 ∧
    parts50.flatten = pad selectedRecord50.preimage ∧
    (pad selectedRecord50.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_50 : CompressionChain initial parts50 after168 := by
  exact (CompressionChain.cons block_step_113 (CompressionChain.cons block_step_114 (CompressionChain.cons block_step_165 (CompressionChain.cons block_step_166 (CompressionChain.cons block_step_167 (CompressionChain.cons block_step_168 (CompressionChain.nil after168)))))))

theorem digest_checked_50 : digestHex after168 = selectedRecord50.digest := by decide +kernel

theorem hash_checked_50 : HashEvaluated selectedRecord50 :=
  sha256_of_chain input_checked_50 partition_checked_50.1
    chain_checked_50 digest_checked_50

noncomputable def selectedRecord51 : Phase17Preimages.HashRecord := Phase17Preimages.record18.program
noncomputable def parts51 : List Block := [block127, block128, block169, block170, block171, block172]
theorem input_checked_51 : InputValid selectedRecord51.preimage := by decide +kernel

theorem partition_checked_51 :
    blocks (pad selectedRecord51.preimage) = parts51 ∧
    parts51.flatten = pad selectedRecord51.preimage ∧
    (pad selectedRecord51.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_51 : CompressionChain initial parts51 after172 := by
  exact (CompressionChain.cons block_step_127 (CompressionChain.cons block_step_128 (CompressionChain.cons block_step_169 (CompressionChain.cons block_step_170 (CompressionChain.cons block_step_171 (CompressionChain.cons block_step_172 (CompressionChain.nil after172)))))))

theorem digest_checked_51 : digestHex after172 = selectedRecord51.digest := by decide +kernel

theorem hash_checked_51 : HashEvaluated selectedRecord51 :=
  sha256_of_chain input_checked_51 partition_checked_51.1
    chain_checked_51 digest_checked_51

noncomputable def selectedRecord52 : Phase17Preimages.HashRecord := Phase17Preimages.record19.program
noncomputable def parts52 : List Block := [block81, block82, block173, block174, block175, block176]
theorem input_checked_52 : InputValid selectedRecord52.preimage := by decide +kernel

theorem partition_checked_52 :
    blocks (pad selectedRecord52.preimage) = parts52 ∧
    parts52.flatten = pad selectedRecord52.preimage ∧
    (pad selectedRecord52.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_52 : CompressionChain initial parts52 after176 := by
  exact (CompressionChain.cons block_step_81 (CompressionChain.cons block_step_82 (CompressionChain.cons block_step_173 (CompressionChain.cons block_step_174 (CompressionChain.cons block_step_175 (CompressionChain.cons block_step_176 (CompressionChain.nil after176)))))))

theorem digest_checked_52 : digestHex after176 = selectedRecord52.digest := by decide +kernel

theorem hash_checked_52 : HashEvaluated selectedRecord52 :=
  sha256_of_chain input_checked_52 partition_checked_52.1
    chain_checked_52 digest_checked_52

noncomputable def selectedRecord53 : Phase17Preimages.HashRecord := Phase17Preimages.record20.program
noncomputable def parts53 : List Block := [block127, block128, block177, block178, block179, block180]
theorem input_checked_53 : InputValid selectedRecord53.preimage := by decide +kernel

theorem partition_checked_53 :
    blocks (pad selectedRecord53.preimage) = parts53 ∧
    parts53.flatten = pad selectedRecord53.preimage ∧
    (pad selectedRecord53.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_53 : CompressionChain initial parts53 after180 := by
  exact (CompressionChain.cons block_step_127 (CompressionChain.cons block_step_128 (CompressionChain.cons block_step_177 (CompressionChain.cons block_step_178 (CompressionChain.cons block_step_179 (CompressionChain.cons block_step_180 (CompressionChain.nil after180)))))))

theorem digest_checked_53 : digestHex after180 = selectedRecord53.digest := by decide +kernel

theorem hash_checked_53 : HashEvaluated selectedRecord53 :=
  sha256_of_chain input_checked_53 partition_checked_53.1
    chain_checked_53 digest_checked_53

noncomputable def selectedRecord54 : Phase17Preimages.HashRecord := Phase17Preimages.record21.program
noncomputable def parts54 : List Block := [block87, block88, block181, block182, block183, block184]
theorem input_checked_54 : InputValid selectedRecord54.preimage := by decide +kernel

theorem partition_checked_54 :
    blocks (pad selectedRecord54.preimage) = parts54 ∧
    parts54.flatten = pad selectedRecord54.preimage ∧
    (pad selectedRecord54.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_54 : CompressionChain initial parts54 after184 := by
  exact (CompressionChain.cons block_step_87 (CompressionChain.cons block_step_88 (CompressionChain.cons block_step_181 (CompressionChain.cons block_step_182 (CompressionChain.cons block_step_183 (CompressionChain.cons block_step_184 (CompressionChain.nil after184)))))))

theorem digest_checked_54 : digestHex after184 = selectedRecord54.digest := by decide +kernel

theorem hash_checked_54 : HashEvaluated selectedRecord54 :=
  sha256_of_chain input_checked_54 partition_checked_54.1
    chain_checked_54 digest_checked_54

noncomputable def selectedRecord55 : Phase17Preimages.HashRecord := Phase17Preimages.record22.program
noncomputable def parts55 : List Block := [block93, block94, block185, block186, block187, block188]
theorem input_checked_55 : InputValid selectedRecord55.preimage := by decide +kernel

theorem partition_checked_55 :
    blocks (pad selectedRecord55.preimage) = parts55 ∧
    parts55.flatten = pad selectedRecord55.preimage ∧
    (pad selectedRecord55.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_55 : CompressionChain initial parts55 after188 := by
  exact (CompressionChain.cons block_step_93 (CompressionChain.cons block_step_94 (CompressionChain.cons block_step_185 (CompressionChain.cons block_step_186 (CompressionChain.cons block_step_187 (CompressionChain.cons block_step_188 (CompressionChain.nil after188)))))))

theorem digest_checked_55 : digestHex after188 = selectedRecord55.digest := by decide +kernel

theorem hash_checked_55 : HashEvaluated selectedRecord55 :=
  sha256_of_chain input_checked_55 partition_checked_55.1
    chain_checked_55 digest_checked_55

noncomputable def selectedRecord56 : Phase17Preimages.HashRecord := Phase17Preimages.record23.program
noncomputable def parts56 : List Block := [block127, block128, block189, block190, block191, block192]
theorem input_checked_56 : InputValid selectedRecord56.preimage := by decide +kernel

theorem partition_checked_56 :
    blocks (pad selectedRecord56.preimage) = parts56 ∧
    parts56.flatten = pad selectedRecord56.preimage ∧
    (pad selectedRecord56.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_56 : CompressionChain initial parts56 after192 := by
  exact (CompressionChain.cons block_step_127 (CompressionChain.cons block_step_128 (CompressionChain.cons block_step_189 (CompressionChain.cons block_step_190 (CompressionChain.cons block_step_191 (CompressionChain.cons block_step_192 (CompressionChain.nil after192)))))))

theorem digest_checked_56 : digestHex after192 = selectedRecord56.digest := by decide +kernel

theorem hash_checked_56 : HashEvaluated selectedRecord56 :=
  sha256_of_chain input_checked_56 partition_checked_56.1
    chain_checked_56 digest_checked_56

noncomputable def selectedRecord57 : Phase17Preimages.HashRecord := Phase17Preimages.record24.program
noncomputable def parts57 : List Block := [block139, block140, block193, block194, block195, block196]
theorem input_checked_57 : InputValid selectedRecord57.preimage := by decide +kernel

theorem partition_checked_57 :
    blocks (pad selectedRecord57.preimage) = parts57 ∧
    parts57.flatten = pad selectedRecord57.preimage ∧
    (pad selectedRecord57.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_57 : CompressionChain initial parts57 after196 := by
  exact (CompressionChain.cons block_step_139 (CompressionChain.cons block_step_140 (CompressionChain.cons block_step_193 (CompressionChain.cons block_step_194 (CompressionChain.cons block_step_195 (CompressionChain.cons block_step_196 (CompressionChain.nil after196)))))))

theorem digest_checked_57 : digestHex after196 = selectedRecord57.digest := by decide +kernel

theorem hash_checked_57 : HashEvaluated selectedRecord57 :=
  sha256_of_chain input_checked_57 partition_checked_57.1
    chain_checked_57 digest_checked_57

noncomputable def selectedRecord58 : Phase17Preimages.HashRecord := Phase17Preimages.record25.program
noncomputable def parts58 : List Block := [block107, block108, block197, block198, block199, block200]
theorem input_checked_58 : InputValid selectedRecord58.preimage := by decide +kernel

theorem partition_checked_58 :
    blocks (pad selectedRecord58.preimage) = parts58 ∧
    parts58.flatten = pad selectedRecord58.preimage ∧
    (pad selectedRecord58.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_58 : CompressionChain initial parts58 after200 := by
  exact (CompressionChain.cons block_step_107 (CompressionChain.cons block_step_108 (CompressionChain.cons block_step_197 (CompressionChain.cons block_step_198 (CompressionChain.cons block_step_199 (CompressionChain.cons block_step_200 (CompressionChain.nil after200)))))))

theorem digest_checked_58 : digestHex after200 = selectedRecord58.digest := by decide +kernel

theorem hash_checked_58 : HashEvaluated selectedRecord58 :=
  sha256_of_chain input_checked_58 partition_checked_58.1
    chain_checked_58 digest_checked_58

noncomputable def selectedRecord59 : Phase17Preimages.HashRecord := Phase17Preimages.record26.program
noncomputable def parts59 : List Block := [block81, block82, block201, block202, block203, block204]
theorem input_checked_59 : InputValid selectedRecord59.preimage := by decide +kernel

theorem partition_checked_59 :
    blocks (pad selectedRecord59.preimage) = parts59 ∧
    parts59.flatten = pad selectedRecord59.preimage ∧
    (pad selectedRecord59.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_59 : CompressionChain initial parts59 after204 := by
  exact (CompressionChain.cons block_step_81 (CompressionChain.cons block_step_82 (CompressionChain.cons block_step_201 (CompressionChain.cons block_step_202 (CompressionChain.cons block_step_203 (CompressionChain.cons block_step_204 (CompressionChain.nil after204)))))))

theorem digest_checked_59 : digestHex after204 = selectedRecord59.digest := by decide +kernel

theorem hash_checked_59 : HashEvaluated selectedRecord59 :=
  sha256_of_chain input_checked_59 partition_checked_59.1
    chain_checked_59 digest_checked_59

noncomputable def selectedRecord60 : Phase17Preimages.HashRecord := Phase17Preimages.record27.program
noncomputable def parts60 : List Block := [block133, block134, block205, block206, block207, block208]
theorem input_checked_60 : InputValid selectedRecord60.preimage := by decide +kernel

theorem partition_checked_60 :
    blocks (pad selectedRecord60.preimage) = parts60 ∧
    parts60.flatten = pad selectedRecord60.preimage ∧
    (pad selectedRecord60.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_60 : CompressionChain initial parts60 after208 := by
  exact (CompressionChain.cons block_step_133 (CompressionChain.cons block_step_134 (CompressionChain.cons block_step_205 (CompressionChain.cons block_step_206 (CompressionChain.cons block_step_207 (CompressionChain.cons block_step_208 (CompressionChain.nil after208)))))))

theorem digest_checked_60 : digestHex after208 = selectedRecord60.digest := by decide +kernel

theorem hash_checked_60 : HashEvaluated selectedRecord60 :=
  sha256_of_chain input_checked_60 partition_checked_60.1
    chain_checked_60 digest_checked_60

noncomputable def selectedRecord61 : Phase17Preimages.HashRecord := Phase17Preimages.record28.program
noncomputable def parts61 : List Block := [block87, block88, block209, block210, block211, block212]
theorem input_checked_61 : InputValid selectedRecord61.preimage := by decide +kernel

theorem partition_checked_61 :
    blocks (pad selectedRecord61.preimage) = parts61 ∧
    parts61.flatten = pad selectedRecord61.preimage ∧
    (pad selectedRecord61.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_61 : CompressionChain initial parts61 after212 := by
  exact (CompressionChain.cons block_step_87 (CompressionChain.cons block_step_88 (CompressionChain.cons block_step_209 (CompressionChain.cons block_step_210 (CompressionChain.cons block_step_211 (CompressionChain.cons block_step_212 (CompressionChain.nil after212)))))))

theorem digest_checked_61 : digestHex after212 = selectedRecord61.digest := by decide +kernel

theorem hash_checked_61 : HashEvaluated selectedRecord61 :=
  sha256_of_chain input_checked_61 partition_checked_61.1
    chain_checked_61 digest_checked_61

noncomputable def selectedRecord62 : Phase17Preimages.HashRecord := Phase17Preimages.record29.program
noncomputable def parts62 : List Block := [block87, block88, block213, block214, block215, block216]
theorem input_checked_62 : InputValid selectedRecord62.preimage := by decide +kernel

theorem partition_checked_62 :
    blocks (pad selectedRecord62.preimage) = parts62 ∧
    parts62.flatten = pad selectedRecord62.preimage ∧
    (pad selectedRecord62.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_62 : CompressionChain initial parts62 after216 := by
  exact (CompressionChain.cons block_step_87 (CompressionChain.cons block_step_88 (CompressionChain.cons block_step_213 (CompressionChain.cons block_step_214 (CompressionChain.cons block_step_215 (CompressionChain.cons block_step_216 (CompressionChain.nil after216)))))))

theorem digest_checked_62 : digestHex after216 = selectedRecord62.digest := by decide +kernel

theorem hash_checked_62 : HashEvaluated selectedRecord62 :=
  sha256_of_chain input_checked_62 partition_checked_62.1
    chain_checked_62 digest_checked_62

noncomputable def selectedRecord63 : Phase17Preimages.HashRecord := Phase17Preimages.record30.program
noncomputable def parts63 : List Block := [block139, block140, block217, block218, block219, block220]
theorem input_checked_63 : InputValid selectedRecord63.preimage := by decide +kernel

theorem partition_checked_63 :
    blocks (pad selectedRecord63.preimage) = parts63 ∧
    parts63.flatten = pad selectedRecord63.preimage ∧
    (pad selectedRecord63.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_63 : CompressionChain initial parts63 after220 := by
  exact (CompressionChain.cons block_step_139 (CompressionChain.cons block_step_140 (CompressionChain.cons block_step_217 (CompressionChain.cons block_step_218 (CompressionChain.cons block_step_219 (CompressionChain.cons block_step_220 (CompressionChain.nil after220)))))))

theorem digest_checked_63 : digestHex after220 = selectedRecord63.digest := by decide +kernel

theorem hash_checked_63 : HashEvaluated selectedRecord63 :=
  sha256_of_chain input_checked_63 partition_checked_63.1
    chain_checked_63 digest_checked_63

noncomputable def selectedRecord64 : Phase17Preimages.HashRecord := Phase17Preimages.record31.program
noncomputable def parts64 : List Block := [block133, block134, block221, block222, block223, block224]
theorem input_checked_64 : InputValid selectedRecord64.preimage := by decide +kernel

theorem partition_checked_64 :
    blocks (pad selectedRecord64.preimage) = parts64 ∧
    parts64.flatten = pad selectedRecord64.preimage ∧
    (pad selectedRecord64.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_64 : CompressionChain initial parts64 after224 := by
  exact (CompressionChain.cons block_step_133 (CompressionChain.cons block_step_134 (CompressionChain.cons block_step_221 (CompressionChain.cons block_step_222 (CompressionChain.cons block_step_223 (CompressionChain.cons block_step_224 (CompressionChain.nil after224)))))))

theorem digest_checked_64 : digestHex after224 = selectedRecord64.digest := by decide +kernel

theorem hash_checked_64 : HashEvaluated selectedRecord64 :=
  sha256_of_chain input_checked_64 partition_checked_64.1
    chain_checked_64 digest_checked_64

noncomputable def selectedRecord65 : Phase17Preimages.HashRecord := Phase17Preimages.record0.feature
noncomputable def parts65 : List Block := [block11, block225, block226, block227, block228, block229, block230, block231, block232, block233, block234, block235]
theorem input_checked_65 : InputValid selectedRecord65.preimage := by decide +kernel

theorem partition_checked_65 :
    blocks (pad selectedRecord65.preimage) = parts65 ∧
    parts65.flatten = pad selectedRecord65.preimage ∧
    (pad selectedRecord65.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_65 : CompressionChain initial parts65 after235 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_225 (CompressionChain.cons block_step_226 (CompressionChain.cons block_step_227 (CompressionChain.cons block_step_228 (CompressionChain.cons block_step_229 (CompressionChain.cons block_step_230 (CompressionChain.cons block_step_231 (CompressionChain.cons block_step_232 (CompressionChain.cons block_step_233 (CompressionChain.cons block_step_234 (CompressionChain.cons block_step_235 (CompressionChain.nil after235)))))))))))))

theorem digest_checked_65 : digestHex after235 = selectedRecord65.digest := by decide +kernel

theorem hash_checked_65 : HashEvaluated selectedRecord65 :=
  sha256_of_chain input_checked_65 partition_checked_65.1
    chain_checked_65 digest_checked_65

noncomputable def selectedRecord66 : Phase17Preimages.HashRecord := Phase17Preimages.record1.feature
noncomputable def parts66 : List Block := [block11, block225, block226, block227, block228, block236, block237, block238, block239, block240, block241]
theorem input_checked_66 : InputValid selectedRecord66.preimage := by decide +kernel

theorem partition_checked_66 :
    blocks (pad selectedRecord66.preimage) = parts66 ∧
    parts66.flatten = pad selectedRecord66.preimage ∧
    (pad selectedRecord66.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_66 : CompressionChain initial parts66 after241 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_225 (CompressionChain.cons block_step_226 (CompressionChain.cons block_step_227 (CompressionChain.cons block_step_228 (CompressionChain.cons block_step_236 (CompressionChain.cons block_step_237 (CompressionChain.cons block_step_238 (CompressionChain.cons block_step_239 (CompressionChain.cons block_step_240 (CompressionChain.cons block_step_241 (CompressionChain.nil after241))))))))))))

theorem digest_checked_66 : digestHex after241 = selectedRecord66.digest := by decide +kernel

theorem hash_checked_66 : HashEvaluated selectedRecord66 :=
  sha256_of_chain input_checked_66 partition_checked_66.1
    chain_checked_66 digest_checked_66

noncomputable def selectedRecord67 : Phase17Preimages.HashRecord := Phase17Preimages.record2.feature
noncomputable def parts67 : List Block := [block11, block225, block226, block227, block228, block242, block243, block244, block245, block246, block247]
theorem input_checked_67 : InputValid selectedRecord67.preimage := by decide +kernel

theorem partition_checked_67 :
    blocks (pad selectedRecord67.preimage) = parts67 ∧
    parts67.flatten = pad selectedRecord67.preimage ∧
    (pad selectedRecord67.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_67 : CompressionChain initial parts67 after247 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_225 (CompressionChain.cons block_step_226 (CompressionChain.cons block_step_227 (CompressionChain.cons block_step_228 (CompressionChain.cons block_step_242 (CompressionChain.cons block_step_243 (CompressionChain.cons block_step_244 (CompressionChain.cons block_step_245 (CompressionChain.cons block_step_246 (CompressionChain.cons block_step_247 (CompressionChain.nil after247))))))))))))

theorem digest_checked_67 : digestHex after247 = selectedRecord67.digest := by decide +kernel

theorem hash_checked_67 : HashEvaluated selectedRecord67 :=
  sha256_of_chain input_checked_67 partition_checked_67.1
    chain_checked_67 digest_checked_67

noncomputable def selectedRecord68 : Phase17Preimages.HashRecord := Phase17Preimages.record3.feature
noncomputable def parts68 : List Block := [block11, block225, block226, block227, block228, block242, block248, block249, block250, block251, block252, block253]
theorem input_checked_68 : InputValid selectedRecord68.preimage := by decide +kernel

theorem partition_checked_68 :
    blocks (pad selectedRecord68.preimage) = parts68 ∧
    parts68.flatten = pad selectedRecord68.preimage ∧
    (pad selectedRecord68.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_68 : CompressionChain initial parts68 after253 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_225 (CompressionChain.cons block_step_226 (CompressionChain.cons block_step_227 (CompressionChain.cons block_step_228 (CompressionChain.cons block_step_242 (CompressionChain.cons block_step_248 (CompressionChain.cons block_step_249 (CompressionChain.cons block_step_250 (CompressionChain.cons block_step_251 (CompressionChain.cons block_step_252 (CompressionChain.cons block_step_253 (CompressionChain.nil after253)))))))))))))

theorem digest_checked_68 : digestHex after253 = selectedRecord68.digest := by decide +kernel

theorem hash_checked_68 : HashEvaluated selectedRecord68 :=
  sha256_of_chain input_checked_68 partition_checked_68.1
    chain_checked_68 digest_checked_68

noncomputable def selectedRecord69 : Phase17Preimages.HashRecord := Phase17Preimages.record4.feature
noncomputable def parts69 : List Block := [block11, block225, block226, block227, block228, block229, block230, block254, block255, block256, block257, block258]
theorem input_checked_69 : InputValid selectedRecord69.preimage := by decide +kernel

theorem partition_checked_69 :
    blocks (pad selectedRecord69.preimage) = parts69 ∧
    parts69.flatten = pad selectedRecord69.preimage ∧
    (pad selectedRecord69.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_69 : CompressionChain initial parts69 after258 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_225 (CompressionChain.cons block_step_226 (CompressionChain.cons block_step_227 (CompressionChain.cons block_step_228 (CompressionChain.cons block_step_229 (CompressionChain.cons block_step_230 (CompressionChain.cons block_step_254 (CompressionChain.cons block_step_255 (CompressionChain.cons block_step_256 (CompressionChain.cons block_step_257 (CompressionChain.cons block_step_258 (CompressionChain.nil after258)))))))))))))

theorem digest_checked_69 : digestHex after258 = selectedRecord69.digest := by decide +kernel

theorem hash_checked_69 : HashEvaluated selectedRecord69 :=
  sha256_of_chain input_checked_69 partition_checked_69.1
    chain_checked_69 digest_checked_69

noncomputable def selectedRecord70 : Phase17Preimages.HashRecord := Phase17Preimages.record5.feature
noncomputable def parts70 : List Block := [block11, block225, block226, block227, block228, block259, block260, block261, block262, block263, block264, block265]
theorem input_checked_70 : InputValid selectedRecord70.preimage := by decide +kernel

theorem partition_checked_70 :
    blocks (pad selectedRecord70.preimage) = parts70 ∧
    parts70.flatten = pad selectedRecord70.preimage ∧
    (pad selectedRecord70.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_70 : CompressionChain initial parts70 after265 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_225 (CompressionChain.cons block_step_226 (CompressionChain.cons block_step_227 (CompressionChain.cons block_step_228 (CompressionChain.cons block_step_259 (CompressionChain.cons block_step_260 (CompressionChain.cons block_step_261 (CompressionChain.cons block_step_262 (CompressionChain.cons block_step_263 (CompressionChain.cons block_step_264 (CompressionChain.cons block_step_265 (CompressionChain.nil after265)))))))))))))

theorem digest_checked_70 : digestHex after265 = selectedRecord70.digest := by decide +kernel

theorem hash_checked_70 : HashEvaluated selectedRecord70 :=
  sha256_of_chain input_checked_70 partition_checked_70.1
    chain_checked_70 digest_checked_70

noncomputable def selectedRecord71 : Phase17Preimages.HashRecord := Phase17Preimages.record6.feature
noncomputable def parts71 : List Block := [block11, block225, block226, block227, block228, block266, block267, block268, block269, block270, block271, block272]
theorem input_checked_71 : InputValid selectedRecord71.preimage := by decide +kernel

theorem partition_checked_71 :
    blocks (pad selectedRecord71.preimage) = parts71 ∧
    parts71.flatten = pad selectedRecord71.preimage ∧
    (pad selectedRecord71.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_71 : CompressionChain initial parts71 after272 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_225 (CompressionChain.cons block_step_226 (CompressionChain.cons block_step_227 (CompressionChain.cons block_step_228 (CompressionChain.cons block_step_266 (CompressionChain.cons block_step_267 (CompressionChain.cons block_step_268 (CompressionChain.cons block_step_269 (CompressionChain.cons block_step_270 (CompressionChain.cons block_step_271 (CompressionChain.cons block_step_272 (CompressionChain.nil after272)))))))))))))

theorem digest_checked_71 : digestHex after272 = selectedRecord71.digest := by decide +kernel

theorem hash_checked_71 : HashEvaluated selectedRecord71 :=
  sha256_of_chain input_checked_71 partition_checked_71.1
    chain_checked_71 digest_checked_71

noncomputable def selectedRecord72 : Phase17Preimages.HashRecord := Phase17Preimages.record7.feature
noncomputable def parts72 : List Block := [block11, block225, block226, block227, block228, block259, block273, block274, block275, block276, block277, block278]
theorem input_checked_72 : InputValid selectedRecord72.preimage := by decide +kernel

theorem partition_checked_72 :
    blocks (pad selectedRecord72.preimage) = parts72 ∧
    parts72.flatten = pad selectedRecord72.preimage ∧
    (pad selectedRecord72.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_72 : CompressionChain initial parts72 after278 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_225 (CompressionChain.cons block_step_226 (CompressionChain.cons block_step_227 (CompressionChain.cons block_step_228 (CompressionChain.cons block_step_259 (CompressionChain.cons block_step_273 (CompressionChain.cons block_step_274 (CompressionChain.cons block_step_275 (CompressionChain.cons block_step_276 (CompressionChain.cons block_step_277 (CompressionChain.cons block_step_278 (CompressionChain.nil after278)))))))))))))

theorem digest_checked_72 : digestHex after278 = selectedRecord72.digest := by decide +kernel

theorem hash_checked_72 : HashEvaluated selectedRecord72 :=
  sha256_of_chain input_checked_72 partition_checked_72.1
    chain_checked_72 digest_checked_72

noncomputable def selectedRecord73 : Phase17Preimages.HashRecord := Phase17Preimages.record8.feature
noncomputable def parts73 : List Block := [block11, block225, block226, block227, block228, block266, block279, block280, block281, block282, block283, block284]
theorem input_checked_73 : InputValid selectedRecord73.preimage := by decide +kernel

theorem partition_checked_73 :
    blocks (pad selectedRecord73.preimage) = parts73 ∧
    parts73.flatten = pad selectedRecord73.preimage ∧
    (pad selectedRecord73.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_73 : CompressionChain initial parts73 after284 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_225 (CompressionChain.cons block_step_226 (CompressionChain.cons block_step_227 (CompressionChain.cons block_step_228 (CompressionChain.cons block_step_266 (CompressionChain.cons block_step_279 (CompressionChain.cons block_step_280 (CompressionChain.cons block_step_281 (CompressionChain.cons block_step_282 (CompressionChain.cons block_step_283 (CompressionChain.cons block_step_284 (CompressionChain.nil after284)))))))))))))

theorem digest_checked_73 : digestHex after284 = selectedRecord73.digest := by decide +kernel

theorem hash_checked_73 : HashEvaluated selectedRecord73 :=
  sha256_of_chain input_checked_73 partition_checked_73.1
    chain_checked_73 digest_checked_73

noncomputable def selectedRecord74 : Phase17Preimages.HashRecord := Phase17Preimages.record9.feature
noncomputable def parts74 : List Block := [block11, block225, block226, block227, block228, block285, block286, block287, block288, block289, block290, block291]
theorem input_checked_74 : InputValid selectedRecord74.preimage := by decide +kernel

theorem partition_checked_74 :
    blocks (pad selectedRecord74.preimage) = parts74 ∧
    parts74.flatten = pad selectedRecord74.preimage ∧
    (pad selectedRecord74.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_74 : CompressionChain initial parts74 after291 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_225 (CompressionChain.cons block_step_226 (CompressionChain.cons block_step_227 (CompressionChain.cons block_step_228 (CompressionChain.cons block_step_285 (CompressionChain.cons block_step_286 (CompressionChain.cons block_step_287 (CompressionChain.cons block_step_288 (CompressionChain.cons block_step_289 (CompressionChain.cons block_step_290 (CompressionChain.cons block_step_291 (CompressionChain.nil after291)))))))))))))

theorem digest_checked_74 : digestHex after291 = selectedRecord74.digest := by decide +kernel

theorem hash_checked_74 : HashEvaluated selectedRecord74 :=
  sha256_of_chain input_checked_74 partition_checked_74.1
    chain_checked_74 digest_checked_74

noncomputable def selectedRecord75 : Phase17Preimages.HashRecord := Phase17Preimages.record10.feature
noncomputable def parts75 : List Block := [block11, block225, block226, block227, block228, block292, block293, block294, block295, block296, block297, block298]
theorem input_checked_75 : InputValid selectedRecord75.preimage := by decide +kernel

theorem partition_checked_75 :
    blocks (pad selectedRecord75.preimage) = parts75 ∧
    parts75.flatten = pad selectedRecord75.preimage ∧
    (pad selectedRecord75.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_75 : CompressionChain initial parts75 after298 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_225 (CompressionChain.cons block_step_226 (CompressionChain.cons block_step_227 (CompressionChain.cons block_step_228 (CompressionChain.cons block_step_292 (CompressionChain.cons block_step_293 (CompressionChain.cons block_step_294 (CompressionChain.cons block_step_295 (CompressionChain.cons block_step_296 (CompressionChain.cons block_step_297 (CompressionChain.cons block_step_298 (CompressionChain.nil after298)))))))))))))

theorem digest_checked_75 : digestHex after298 = selectedRecord75.digest := by decide +kernel

theorem hash_checked_75 : HashEvaluated selectedRecord75 :=
  sha256_of_chain input_checked_75 partition_checked_75.1
    chain_checked_75 digest_checked_75

noncomputable def selectedRecord76 : Phase17Preimages.HashRecord := Phase17Preimages.record11.feature
noncomputable def parts76 : List Block := [block11, block225, block226, block227, block228, block299, block300, block301, block302, block303, block304]
theorem input_checked_76 : InputValid selectedRecord76.preimage := by decide +kernel

theorem partition_checked_76 :
    blocks (pad selectedRecord76.preimage) = parts76 ∧
    parts76.flatten = pad selectedRecord76.preimage ∧
    (pad selectedRecord76.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_76 : CompressionChain initial parts76 after304 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_225 (CompressionChain.cons block_step_226 (CompressionChain.cons block_step_227 (CompressionChain.cons block_step_228 (CompressionChain.cons block_step_299 (CompressionChain.cons block_step_300 (CompressionChain.cons block_step_301 (CompressionChain.cons block_step_302 (CompressionChain.cons block_step_303 (CompressionChain.cons block_step_304 (CompressionChain.nil after304))))))))))))

theorem digest_checked_76 : digestHex after304 = selectedRecord76.digest := by decide +kernel

theorem hash_checked_76 : HashEvaluated selectedRecord76 :=
  sha256_of_chain input_checked_76 partition_checked_76.1
    chain_checked_76 digest_checked_76

noncomputable def selectedRecord77 : Phase17Preimages.HashRecord := Phase17Preimages.record12.feature
noncomputable def parts77 : List Block := [block11, block225, block226, block227, block228, block242, block305, block306, block307, block308, block309, block310]
theorem input_checked_77 : InputValid selectedRecord77.preimage := by decide +kernel

theorem partition_checked_77 :
    blocks (pad selectedRecord77.preimage) = parts77 ∧
    parts77.flatten = pad selectedRecord77.preimage ∧
    (pad selectedRecord77.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_77 : CompressionChain initial parts77 after310 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_225 (CompressionChain.cons block_step_226 (CompressionChain.cons block_step_227 (CompressionChain.cons block_step_228 (CompressionChain.cons block_step_242 (CompressionChain.cons block_step_305 (CompressionChain.cons block_step_306 (CompressionChain.cons block_step_307 (CompressionChain.cons block_step_308 (CompressionChain.cons block_step_309 (CompressionChain.cons block_step_310 (CompressionChain.nil after310)))))))))))))

theorem digest_checked_77 : digestHex after310 = selectedRecord77.digest := by decide +kernel

theorem hash_checked_77 : HashEvaluated selectedRecord77 :=
  sha256_of_chain input_checked_77 partition_checked_77.1
    chain_checked_77 digest_checked_77

noncomputable def selectedRecord78 : Phase17Preimages.HashRecord := Phase17Preimages.record13.feature
noncomputable def parts78 : List Block := [block11, block225, block226, block227, block228, block292, block311, block312, block313, block314, block315, block316]
theorem input_checked_78 : InputValid selectedRecord78.preimage := by decide +kernel

theorem partition_checked_78 :
    blocks (pad selectedRecord78.preimage) = parts78 ∧
    parts78.flatten = pad selectedRecord78.preimage ∧
    (pad selectedRecord78.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_78 : CompressionChain initial parts78 after316 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_225 (CompressionChain.cons block_step_226 (CompressionChain.cons block_step_227 (CompressionChain.cons block_step_228 (CompressionChain.cons block_step_292 (CompressionChain.cons block_step_311 (CompressionChain.cons block_step_312 (CompressionChain.cons block_step_313 (CompressionChain.cons block_step_314 (CompressionChain.cons block_step_315 (CompressionChain.cons block_step_316 (CompressionChain.nil after316)))))))))))))

theorem digest_checked_78 : digestHex after316 = selectedRecord78.digest := by decide +kernel

theorem hash_checked_78 : HashEvaluated selectedRecord78 :=
  sha256_of_chain input_checked_78 partition_checked_78.1
    chain_checked_78 digest_checked_78

noncomputable def selectedRecord79 : Phase17Preimages.HashRecord := Phase17Preimages.record14.feature
noncomputable def parts79 : List Block := [block11, block225, block226, block227, block228, block299, block317, block318, block319, block320, block321]
theorem input_checked_79 : InputValid selectedRecord79.preimage := by decide +kernel

theorem partition_checked_79 :
    blocks (pad selectedRecord79.preimage) = parts79 ∧
    parts79.flatten = pad selectedRecord79.preimage ∧
    (pad selectedRecord79.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_79 : CompressionChain initial parts79 after321 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_225 (CompressionChain.cons block_step_226 (CompressionChain.cons block_step_227 (CompressionChain.cons block_step_228 (CompressionChain.cons block_step_299 (CompressionChain.cons block_step_317 (CompressionChain.cons block_step_318 (CompressionChain.cons block_step_319 (CompressionChain.cons block_step_320 (CompressionChain.cons block_step_321 (CompressionChain.nil after321))))))))))))

theorem digest_checked_79 : digestHex after321 = selectedRecord79.digest := by decide +kernel

theorem hash_checked_79 : HashEvaluated selectedRecord79 :=
  sha256_of_chain input_checked_79 partition_checked_79.1
    chain_checked_79 digest_checked_79

noncomputable def selectedRecord80 : Phase17Preimages.HashRecord := Phase17Preimages.record15.feature
noncomputable def parts80 : List Block := [block11, block225, block226, block227, block228, block266, block322, block323, block324, block325, block326, block327]
theorem input_checked_80 : InputValid selectedRecord80.preimage := by decide +kernel

theorem partition_checked_80 :
    blocks (pad selectedRecord80.preimage) = parts80 ∧
    parts80.flatten = pad selectedRecord80.preimage ∧
    (pad selectedRecord80.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_80 : CompressionChain initial parts80 after327 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_225 (CompressionChain.cons block_step_226 (CompressionChain.cons block_step_227 (CompressionChain.cons block_step_228 (CompressionChain.cons block_step_266 (CompressionChain.cons block_step_322 (CompressionChain.cons block_step_323 (CompressionChain.cons block_step_324 (CompressionChain.cons block_step_325 (CompressionChain.cons block_step_326 (CompressionChain.cons block_step_327 (CompressionChain.nil after327)))))))))))))

theorem digest_checked_80 : digestHex after327 = selectedRecord80.digest := by decide +kernel

theorem hash_checked_80 : HashEvaluated selectedRecord80 :=
  sha256_of_chain input_checked_80 partition_checked_80.1
    chain_checked_80 digest_checked_80

noncomputable def selectedRecord81 : Phase17Preimages.HashRecord := Phase17Preimages.record16.feature
noncomputable def parts81 : List Block := [block11, block225, block226, block227, block228, block259, block260, block328, block329, block330, block331, block332]
theorem input_checked_81 : InputValid selectedRecord81.preimage := by decide +kernel

theorem partition_checked_81 :
    blocks (pad selectedRecord81.preimage) = parts81 ∧
    parts81.flatten = pad selectedRecord81.preimage ∧
    (pad selectedRecord81.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_81 : CompressionChain initial parts81 after332 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_225 (CompressionChain.cons block_step_226 (CompressionChain.cons block_step_227 (CompressionChain.cons block_step_228 (CompressionChain.cons block_step_259 (CompressionChain.cons block_step_260 (CompressionChain.cons block_step_328 (CompressionChain.cons block_step_329 (CompressionChain.cons block_step_330 (CompressionChain.cons block_step_331 (CompressionChain.cons block_step_332 (CompressionChain.nil after332)))))))))))))

theorem digest_checked_81 : digestHex after332 = selectedRecord81.digest := by decide +kernel

theorem hash_checked_81 : HashEvaluated selectedRecord81 :=
  sha256_of_chain input_checked_81 partition_checked_81.1
    chain_checked_81 digest_checked_81

noncomputable def selectedRecord82 : Phase17Preimages.HashRecord := Phase17Preimages.record17.feature
noncomputable def parts82 : List Block := [block11, block225, block226, block227, block228, block266, block333, block334, block335, block336, block337, block338]
theorem input_checked_82 : InputValid selectedRecord82.preimage := by decide +kernel

theorem partition_checked_82 :
    blocks (pad selectedRecord82.preimage) = parts82 ∧
    parts82.flatten = pad selectedRecord82.preimage ∧
    (pad selectedRecord82.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_82 : CompressionChain initial parts82 after338 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_225 (CompressionChain.cons block_step_226 (CompressionChain.cons block_step_227 (CompressionChain.cons block_step_228 (CompressionChain.cons block_step_266 (CompressionChain.cons block_step_333 (CompressionChain.cons block_step_334 (CompressionChain.cons block_step_335 (CompressionChain.cons block_step_336 (CompressionChain.cons block_step_337 (CompressionChain.cons block_step_338 (CompressionChain.nil after338)))))))))))))

theorem digest_checked_82 : digestHex after338 = selectedRecord82.digest := by decide +kernel

theorem hash_checked_82 : HashEvaluated selectedRecord82 :=
  sha256_of_chain input_checked_82 partition_checked_82.1
    chain_checked_82 digest_checked_82

noncomputable def selectedRecord83 : Phase17Preimages.HashRecord := Phase17Preimages.record18.feature
noncomputable def parts83 : List Block := [block11, block225, block226, block227, block228, block285, block339, block340, block341, block342, block343, block344]
theorem input_checked_83 : InputValid selectedRecord83.preimage := by decide +kernel

theorem partition_checked_83 :
    blocks (pad selectedRecord83.preimage) = parts83 ∧
    parts83.flatten = pad selectedRecord83.preimage ∧
    (pad selectedRecord83.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_83 : CompressionChain initial parts83 after344 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_225 (CompressionChain.cons block_step_226 (CompressionChain.cons block_step_227 (CompressionChain.cons block_step_228 (CompressionChain.cons block_step_285 (CompressionChain.cons block_step_339 (CompressionChain.cons block_step_340 (CompressionChain.cons block_step_341 (CompressionChain.cons block_step_342 (CompressionChain.cons block_step_343 (CompressionChain.cons block_step_344 (CompressionChain.nil after344)))))))))))))

theorem digest_checked_83 : digestHex after344 = selectedRecord83.digest := by decide +kernel

theorem hash_checked_83 : HashEvaluated selectedRecord83 :=
  sha256_of_chain input_checked_83 partition_checked_83.1
    chain_checked_83 digest_checked_83

noncomputable def selectedRecord84 : Phase17Preimages.HashRecord := Phase17Preimages.record19.feature
noncomputable def parts84 : List Block := [block11, block225, block226, block227, block228, block229, block230, block345, block346, block347, block348, block349]
theorem input_checked_84 : InputValid selectedRecord84.preimage := by decide +kernel

theorem partition_checked_84 :
    blocks (pad selectedRecord84.preimage) = parts84 ∧
    parts84.flatten = pad selectedRecord84.preimage ∧
    (pad selectedRecord84.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_84 : CompressionChain initial parts84 after349 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_225 (CompressionChain.cons block_step_226 (CompressionChain.cons block_step_227 (CompressionChain.cons block_step_228 (CompressionChain.cons block_step_229 (CompressionChain.cons block_step_230 (CompressionChain.cons block_step_345 (CompressionChain.cons block_step_346 (CompressionChain.cons block_step_347 (CompressionChain.cons block_step_348 (CompressionChain.cons block_step_349 (CompressionChain.nil after349)))))))))))))

theorem digest_checked_84 : digestHex after349 = selectedRecord84.digest := by decide +kernel

theorem hash_checked_84 : HashEvaluated selectedRecord84 :=
  sha256_of_chain input_checked_84 partition_checked_84.1
    chain_checked_84 digest_checked_84

noncomputable def selectedRecord85 : Phase17Preimages.HashRecord := Phase17Preimages.record20.feature
noncomputable def parts85 : List Block := [block11, block225, block226, block227, block228, block285, block350, block351, block352, block353, block354, block355]
theorem input_checked_85 : InputValid selectedRecord85.preimage := by decide +kernel

theorem partition_checked_85 :
    blocks (pad selectedRecord85.preimage) = parts85 ∧
    parts85.flatten = pad selectedRecord85.preimage ∧
    (pad selectedRecord85.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_85 : CompressionChain initial parts85 after355 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_225 (CompressionChain.cons block_step_226 (CompressionChain.cons block_step_227 (CompressionChain.cons block_step_228 (CompressionChain.cons block_step_285 (CompressionChain.cons block_step_350 (CompressionChain.cons block_step_351 (CompressionChain.cons block_step_352 (CompressionChain.cons block_step_353 (CompressionChain.cons block_step_354 (CompressionChain.cons block_step_355 (CompressionChain.nil after355)))))))))))))

theorem digest_checked_85 : digestHex after355 = selectedRecord85.digest := by decide +kernel

theorem hash_checked_85 : HashEvaluated selectedRecord85 :=
  sha256_of_chain input_checked_85 partition_checked_85.1
    chain_checked_85 digest_checked_85

noncomputable def selectedRecord86 : Phase17Preimages.HashRecord := Phase17Preimages.record21.feature
noncomputable def parts86 : List Block := [block11, block225, block226, block227, block228, block236, block356, block357, block358, block359, block360]
theorem input_checked_86 : InputValid selectedRecord86.preimage := by decide +kernel

theorem partition_checked_86 :
    blocks (pad selectedRecord86.preimage) = parts86 ∧
    parts86.flatten = pad selectedRecord86.preimage ∧
    (pad selectedRecord86.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_86 : CompressionChain initial parts86 after360 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_225 (CompressionChain.cons block_step_226 (CompressionChain.cons block_step_227 (CompressionChain.cons block_step_228 (CompressionChain.cons block_step_236 (CompressionChain.cons block_step_356 (CompressionChain.cons block_step_357 (CompressionChain.cons block_step_358 (CompressionChain.cons block_step_359 (CompressionChain.cons block_step_360 (CompressionChain.nil after360))))))))))))

theorem digest_checked_86 : digestHex after360 = selectedRecord86.digest := by decide +kernel

theorem hash_checked_86 : HashEvaluated selectedRecord86 :=
  sha256_of_chain input_checked_86 partition_checked_86.1
    chain_checked_86 digest_checked_86

noncomputable def selectedRecord87 : Phase17Preimages.HashRecord := Phase17Preimages.record22.feature
noncomputable def parts87 : List Block := [block11, block225, block226, block227, block228, block242, block361, block362, block363, block364, block365]
theorem input_checked_87 : InputValid selectedRecord87.preimage := by decide +kernel

theorem partition_checked_87 :
    blocks (pad selectedRecord87.preimage) = parts87 ∧
    parts87.flatten = pad selectedRecord87.preimage ∧
    (pad selectedRecord87.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_87 : CompressionChain initial parts87 after365 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_225 (CompressionChain.cons block_step_226 (CompressionChain.cons block_step_227 (CompressionChain.cons block_step_228 (CompressionChain.cons block_step_242 (CompressionChain.cons block_step_361 (CompressionChain.cons block_step_362 (CompressionChain.cons block_step_363 (CompressionChain.cons block_step_364 (CompressionChain.cons block_step_365 (CompressionChain.nil after365))))))))))))

theorem digest_checked_87 : digestHex after365 = selectedRecord87.digest := by decide +kernel

theorem hash_checked_87 : HashEvaluated selectedRecord87 :=
  sha256_of_chain input_checked_87 partition_checked_87.1
    chain_checked_87 digest_checked_87

noncomputable def selectedRecord88 : Phase17Preimages.HashRecord := Phase17Preimages.record23.feature
noncomputable def parts88 : List Block := [block11, block225, block226, block227, block228, block285, block366, block367, block368, block369, block370, block371]
theorem input_checked_88 : InputValid selectedRecord88.preimage := by decide +kernel

theorem partition_checked_88 :
    blocks (pad selectedRecord88.preimage) = parts88 ∧
    parts88.flatten = pad selectedRecord88.preimage ∧
    (pad selectedRecord88.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_88 : CompressionChain initial parts88 after371 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_225 (CompressionChain.cons block_step_226 (CompressionChain.cons block_step_227 (CompressionChain.cons block_step_228 (CompressionChain.cons block_step_285 (CompressionChain.cons block_step_366 (CompressionChain.cons block_step_367 (CompressionChain.cons block_step_368 (CompressionChain.cons block_step_369 (CompressionChain.cons block_step_370 (CompressionChain.cons block_step_371 (CompressionChain.nil after371)))))))))))))

theorem digest_checked_88 : digestHex after371 = selectedRecord88.digest := by decide +kernel

theorem hash_checked_88 : HashEvaluated selectedRecord88 :=
  sha256_of_chain input_checked_88 partition_checked_88.1
    chain_checked_88 digest_checked_88

noncomputable def selectedRecord89 : Phase17Preimages.HashRecord := Phase17Preimages.record24.feature
noncomputable def parts89 : List Block := [block11, block225, block226, block227, block228, block299, block372, block373, block374, block375, block376]
theorem input_checked_89 : InputValid selectedRecord89.preimage := by decide +kernel

theorem partition_checked_89 :
    blocks (pad selectedRecord89.preimage) = parts89 ∧
    parts89.flatten = pad selectedRecord89.preimage ∧
    (pad selectedRecord89.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_89 : CompressionChain initial parts89 after376 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_225 (CompressionChain.cons block_step_226 (CompressionChain.cons block_step_227 (CompressionChain.cons block_step_228 (CompressionChain.cons block_step_299 (CompressionChain.cons block_step_372 (CompressionChain.cons block_step_373 (CompressionChain.cons block_step_374 (CompressionChain.cons block_step_375 (CompressionChain.cons block_step_376 (CompressionChain.nil after376))))))))))))

theorem digest_checked_89 : digestHex after376 = selectedRecord89.digest := by decide +kernel

theorem hash_checked_89 : HashEvaluated selectedRecord89 :=
  sha256_of_chain input_checked_89 partition_checked_89.1
    chain_checked_89 digest_checked_89

noncomputable def selectedRecord90 : Phase17Preimages.HashRecord := Phase17Preimages.record25.feature
noncomputable def parts90 : List Block := [block11, block225, block226, block227, block228, block259, block377, block378, block379, block380, block381, block382]
theorem input_checked_90 : InputValid selectedRecord90.preimage := by decide +kernel

theorem partition_checked_90 :
    blocks (pad selectedRecord90.preimage) = parts90 ∧
    parts90.flatten = pad selectedRecord90.preimage ∧
    (pad selectedRecord90.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_90 : CompressionChain initial parts90 after382 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_225 (CompressionChain.cons block_step_226 (CompressionChain.cons block_step_227 (CompressionChain.cons block_step_228 (CompressionChain.cons block_step_259 (CompressionChain.cons block_step_377 (CompressionChain.cons block_step_378 (CompressionChain.cons block_step_379 (CompressionChain.cons block_step_380 (CompressionChain.cons block_step_381 (CompressionChain.cons block_step_382 (CompressionChain.nil after382)))))))))))))

theorem digest_checked_90 : digestHex after382 = selectedRecord90.digest := by decide +kernel

theorem hash_checked_90 : HashEvaluated selectedRecord90 :=
  sha256_of_chain input_checked_90 partition_checked_90.1
    chain_checked_90 digest_checked_90

noncomputable def selectedRecord91 : Phase17Preimages.HashRecord := Phase17Preimages.record26.feature
noncomputable def parts91 : List Block := [block11, block225, block226, block227, block228, block229, block230, block383, block384, block385, block386, block387]
theorem input_checked_91 : InputValid selectedRecord91.preimage := by decide +kernel

theorem partition_checked_91 :
    blocks (pad selectedRecord91.preimage) = parts91 ∧
    parts91.flatten = pad selectedRecord91.preimage ∧
    (pad selectedRecord91.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_91 : CompressionChain initial parts91 after387 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_225 (CompressionChain.cons block_step_226 (CompressionChain.cons block_step_227 (CompressionChain.cons block_step_228 (CompressionChain.cons block_step_229 (CompressionChain.cons block_step_230 (CompressionChain.cons block_step_383 (CompressionChain.cons block_step_384 (CompressionChain.cons block_step_385 (CompressionChain.cons block_step_386 (CompressionChain.cons block_step_387 (CompressionChain.nil after387)))))))))))))

theorem digest_checked_91 : digestHex after387 = selectedRecord91.digest := by decide +kernel

theorem hash_checked_91 : HashEvaluated selectedRecord91 :=
  sha256_of_chain input_checked_91 partition_checked_91.1
    chain_checked_91 digest_checked_91

noncomputable def selectedRecord92 : Phase17Preimages.HashRecord := Phase17Preimages.record27.feature
noncomputable def parts92 : List Block := [block11, block225, block226, block227, block228, block292, block388, block389, block390, block391, block392, block393]
theorem input_checked_92 : InputValid selectedRecord92.preimage := by decide +kernel

theorem partition_checked_92 :
    blocks (pad selectedRecord92.preimage) = parts92 ∧
    parts92.flatten = pad selectedRecord92.preimage ∧
    (pad selectedRecord92.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_92 : CompressionChain initial parts92 after393 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_225 (CompressionChain.cons block_step_226 (CompressionChain.cons block_step_227 (CompressionChain.cons block_step_228 (CompressionChain.cons block_step_292 (CompressionChain.cons block_step_388 (CompressionChain.cons block_step_389 (CompressionChain.cons block_step_390 (CompressionChain.cons block_step_391 (CompressionChain.cons block_step_392 (CompressionChain.cons block_step_393 (CompressionChain.nil after393)))))))))))))

theorem digest_checked_92 : digestHex after393 = selectedRecord92.digest := by decide +kernel

theorem hash_checked_92 : HashEvaluated selectedRecord92 :=
  sha256_of_chain input_checked_92 partition_checked_92.1
    chain_checked_92 digest_checked_92

noncomputable def selectedRecord93 : Phase17Preimages.HashRecord := Phase17Preimages.record28.feature
noncomputable def parts93 : List Block := [block11, block225, block226, block227, block228, block236, block394, block395, block396, block397, block398]
theorem input_checked_93 : InputValid selectedRecord93.preimage := by decide +kernel

theorem partition_checked_93 :
    blocks (pad selectedRecord93.preimage) = parts93 ∧
    parts93.flatten = pad selectedRecord93.preimage ∧
    (pad selectedRecord93.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_93 : CompressionChain initial parts93 after398 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_225 (CompressionChain.cons block_step_226 (CompressionChain.cons block_step_227 (CompressionChain.cons block_step_228 (CompressionChain.cons block_step_236 (CompressionChain.cons block_step_394 (CompressionChain.cons block_step_395 (CompressionChain.cons block_step_396 (CompressionChain.cons block_step_397 (CompressionChain.cons block_step_398 (CompressionChain.nil after398))))))))))))

theorem digest_checked_93 : digestHex after398 = selectedRecord93.digest := by decide +kernel

theorem hash_checked_93 : HashEvaluated selectedRecord93 :=
  sha256_of_chain input_checked_93 partition_checked_93.1
    chain_checked_93 digest_checked_93

noncomputable def selectedRecord94 : Phase17Preimages.HashRecord := Phase17Preimages.record29.feature
noncomputable def parts94 : List Block := [block11, block225, block226, block227, block228, block236, block399, block400, block401, block402, block403]
theorem input_checked_94 : InputValid selectedRecord94.preimage := by decide +kernel

theorem partition_checked_94 :
    blocks (pad selectedRecord94.preimage) = parts94 ∧
    parts94.flatten = pad selectedRecord94.preimage ∧
    (pad selectedRecord94.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_94 : CompressionChain initial parts94 after403 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_225 (CompressionChain.cons block_step_226 (CompressionChain.cons block_step_227 (CompressionChain.cons block_step_228 (CompressionChain.cons block_step_236 (CompressionChain.cons block_step_399 (CompressionChain.cons block_step_400 (CompressionChain.cons block_step_401 (CompressionChain.cons block_step_402 (CompressionChain.cons block_step_403 (CompressionChain.nil after403))))))))))))

theorem digest_checked_94 : digestHex after403 = selectedRecord94.digest := by decide +kernel

theorem hash_checked_94 : HashEvaluated selectedRecord94 :=
  sha256_of_chain input_checked_94 partition_checked_94.1
    chain_checked_94 digest_checked_94

noncomputable def selectedRecord95 : Phase17Preimages.HashRecord := Phase17Preimages.record30.feature
noncomputable def parts95 : List Block := [block11, block225, block226, block227, block228, block299, block404, block405, block406, block407, block408]
theorem input_checked_95 : InputValid selectedRecord95.preimage := by decide +kernel

theorem partition_checked_95 :
    blocks (pad selectedRecord95.preimage) = parts95 ∧
    parts95.flatten = pad selectedRecord95.preimage ∧
    (pad selectedRecord95.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_95 : CompressionChain initial parts95 after408 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_225 (CompressionChain.cons block_step_226 (CompressionChain.cons block_step_227 (CompressionChain.cons block_step_228 (CompressionChain.cons block_step_299 (CompressionChain.cons block_step_404 (CompressionChain.cons block_step_405 (CompressionChain.cons block_step_406 (CompressionChain.cons block_step_407 (CompressionChain.cons block_step_408 (CompressionChain.nil after408))))))))))))

theorem digest_checked_95 : digestHex after408 = selectedRecord95.digest := by decide +kernel

theorem hash_checked_95 : HashEvaluated selectedRecord95 :=
  sha256_of_chain input_checked_95 partition_checked_95.1
    chain_checked_95 digest_checked_95

noncomputable def selectedRecord96 : Phase17Preimages.HashRecord := Phase17Preimages.record31.feature
noncomputable def parts96 : List Block := [block11, block225, block226, block227, block228, block292, block409, block410, block411, block412, block413, block414]
theorem input_checked_96 : InputValid selectedRecord96.preimage := by decide +kernel

theorem partition_checked_96 :
    blocks (pad selectedRecord96.preimage) = parts96 ∧
    parts96.flatten = pad selectedRecord96.preimage ∧
    (pad selectedRecord96.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_96 : CompressionChain initial parts96 after414 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_225 (CompressionChain.cons block_step_226 (CompressionChain.cons block_step_227 (CompressionChain.cons block_step_228 (CompressionChain.cons block_step_292 (CompressionChain.cons block_step_409 (CompressionChain.cons block_step_410 (CompressionChain.cons block_step_411 (CompressionChain.cons block_step_412 (CompressionChain.cons block_step_413 (CompressionChain.cons block_step_414 (CompressionChain.nil after414)))))))))))))

theorem digest_checked_96 : digestHex after414 = selectedRecord96.digest := by decide +kernel

theorem hash_checked_96 : HashEvaluated selectedRecord96 :=
  sha256_of_chain input_checked_96 partition_checked_96.1
    chain_checked_96 digest_checked_96

noncomputable def selectedRecord97 : Phase17Preimages.HashRecord := (Phase17Preimages.record0.ties.getD 0 { json := [], preimage := [], digest := "" })
noncomputable def parts97 : List Block := [block11, block415, block416, block417, block418]
theorem input_checked_97 : InputValid selectedRecord97.preimage := by decide +kernel

theorem partition_checked_97 :
    blocks (pad selectedRecord97.preimage) = parts97 ∧
    parts97.flatten = pad selectedRecord97.preimage ∧
    (pad selectedRecord97.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_97 : CompressionChain initial parts97 after418 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_417 (CompressionChain.cons block_step_418 (CompressionChain.nil after418))))))

theorem digest_checked_97 : digestHex after418 = selectedRecord97.digest := by decide +kernel

theorem hash_checked_97 : HashEvaluated selectedRecord97 :=
  sha256_of_chain input_checked_97 partition_checked_97.1
    chain_checked_97 digest_checked_97

noncomputable def selectedRecord98 : Phase17Preimages.HashRecord := (Phase17Preimages.record0.ties.getD 1 { json := [], preimage := [], digest := "" })
noncomputable def parts98 : List Block := [block11, block415, block416, block417, block419]
theorem input_checked_98 : InputValid selectedRecord98.preimage := by decide +kernel

theorem partition_checked_98 :
    blocks (pad selectedRecord98.preimage) = parts98 ∧
    parts98.flatten = pad selectedRecord98.preimage ∧
    (pad selectedRecord98.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_98 : CompressionChain initial parts98 after419 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_417 (CompressionChain.cons block_step_419 (CompressionChain.nil after419))))))

theorem digest_checked_98 : digestHex after419 = selectedRecord98.digest := by decide +kernel

theorem hash_checked_98 : HashEvaluated selectedRecord98 :=
  sha256_of_chain input_checked_98 partition_checked_98.1
    chain_checked_98 digest_checked_98

noncomputable def selectedRecord99 : Phase17Preimages.HashRecord := (Phase17Preimages.record0.ties.getD 2 { json := [], preimage := [], digest := "" })
noncomputable def parts99 : List Block := [block11, block415, block416, block417, block420]
theorem input_checked_99 : InputValid selectedRecord99.preimage := by decide +kernel

theorem partition_checked_99 :
    blocks (pad selectedRecord99.preimage) = parts99 ∧
    parts99.flatten = pad selectedRecord99.preimage ∧
    (pad selectedRecord99.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_99 : CompressionChain initial parts99 after420 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_417 (CompressionChain.cons block_step_420 (CompressionChain.nil after420))))))

theorem digest_checked_99 : digestHex after420 = selectedRecord99.digest := by decide +kernel

theorem hash_checked_99 : HashEvaluated selectedRecord99 :=
  sha256_of_chain input_checked_99 partition_checked_99.1
    chain_checked_99 digest_checked_99

noncomputable def selectedRecord100 : Phase17Preimages.HashRecord := (Phase17Preimages.record0.ties.getD 3 { json := [], preimage := [], digest := "" })
noncomputable def parts100 : List Block := [block11, block415, block416, block417, block421]
theorem input_checked_100 : InputValid selectedRecord100.preimage := by decide +kernel

theorem partition_checked_100 :
    blocks (pad selectedRecord100.preimage) = parts100 ∧
    parts100.flatten = pad selectedRecord100.preimage ∧
    (pad selectedRecord100.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_100 : CompressionChain initial parts100 after421 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_417 (CompressionChain.cons block_step_421 (CompressionChain.nil after421))))))

theorem digest_checked_100 : digestHex after421 = selectedRecord100.digest := by decide +kernel

theorem hash_checked_100 : HashEvaluated selectedRecord100 :=
  sha256_of_chain input_checked_100 partition_checked_100.1
    chain_checked_100 digest_checked_100

noncomputable def selectedRecord101 : Phase17Preimages.HashRecord := (Phase17Preimages.record0.ties.getD 4 { json := [], preimage := [], digest := "" })
noncomputable def parts101 : List Block := [block11, block415, block416, block417, block422]
theorem input_checked_101 : InputValid selectedRecord101.preimage := by decide +kernel

theorem partition_checked_101 :
    blocks (pad selectedRecord101.preimage) = parts101 ∧
    parts101.flatten = pad selectedRecord101.preimage ∧
    (pad selectedRecord101.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_101 : CompressionChain initial parts101 after422 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_417 (CompressionChain.cons block_step_422 (CompressionChain.nil after422))))))

theorem digest_checked_101 : digestHex after422 = selectedRecord101.digest := by decide +kernel

theorem hash_checked_101 : HashEvaluated selectedRecord101 :=
  sha256_of_chain input_checked_101 partition_checked_101.1
    chain_checked_101 digest_checked_101

noncomputable def selectedRecord102 : Phase17Preimages.HashRecord := (Phase17Preimages.record1.ties.getD 0 { json := [], preimage := [], digest := "" })
noncomputable def parts102 : List Block := [block11, block415, block416, block423, block424]
theorem input_checked_102 : InputValid selectedRecord102.preimage := by decide +kernel

theorem partition_checked_102 :
    blocks (pad selectedRecord102.preimage) = parts102 ∧
    parts102.flatten = pad selectedRecord102.preimage ∧
    (pad selectedRecord102.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_102 : CompressionChain initial parts102 after424 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_423 (CompressionChain.cons block_step_424 (CompressionChain.nil after424))))))

theorem digest_checked_102 : digestHex after424 = selectedRecord102.digest := by decide +kernel

theorem hash_checked_102 : HashEvaluated selectedRecord102 :=
  sha256_of_chain input_checked_102 partition_checked_102.1
    chain_checked_102 digest_checked_102

noncomputable def selectedRecord103 : Phase17Preimages.HashRecord := (Phase17Preimages.record1.ties.getD 1 { json := [], preimage := [], digest := "" })
noncomputable def parts103 : List Block := [block11, block415, block416, block423, block425]
theorem input_checked_103 : InputValid selectedRecord103.preimage := by decide +kernel

theorem partition_checked_103 :
    blocks (pad selectedRecord103.preimage) = parts103 ∧
    parts103.flatten = pad selectedRecord103.preimage ∧
    (pad selectedRecord103.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_103 : CompressionChain initial parts103 after425 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_423 (CompressionChain.cons block_step_425 (CompressionChain.nil after425))))))

theorem digest_checked_103 : digestHex after425 = selectedRecord103.digest := by decide +kernel

theorem hash_checked_103 : HashEvaluated selectedRecord103 :=
  sha256_of_chain input_checked_103 partition_checked_103.1
    chain_checked_103 digest_checked_103

noncomputable def selectedRecord104 : Phase17Preimages.HashRecord := (Phase17Preimages.record1.ties.getD 2 { json := [], preimage := [], digest := "" })
noncomputable def parts104 : List Block := [block11, block415, block416, block423, block426]
theorem input_checked_104 : InputValid selectedRecord104.preimage := by decide +kernel

theorem partition_checked_104 :
    blocks (pad selectedRecord104.preimage) = parts104 ∧
    parts104.flatten = pad selectedRecord104.preimage ∧
    (pad selectedRecord104.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_104 : CompressionChain initial parts104 after426 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_423 (CompressionChain.cons block_step_426 (CompressionChain.nil after426))))))

theorem digest_checked_104 : digestHex after426 = selectedRecord104.digest := by decide +kernel

theorem hash_checked_104 : HashEvaluated selectedRecord104 :=
  sha256_of_chain input_checked_104 partition_checked_104.1
    chain_checked_104 digest_checked_104

noncomputable def selectedRecord105 : Phase17Preimages.HashRecord := (Phase17Preimages.record1.ties.getD 3 { json := [], preimage := [], digest := "" })
noncomputable def parts105 : List Block := [block11, block415, block416, block423, block427]
theorem input_checked_105 : InputValid selectedRecord105.preimage := by decide +kernel

theorem partition_checked_105 :
    blocks (pad selectedRecord105.preimage) = parts105 ∧
    parts105.flatten = pad selectedRecord105.preimage ∧
    (pad selectedRecord105.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_105 : CompressionChain initial parts105 after427 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_423 (CompressionChain.cons block_step_427 (CompressionChain.nil after427))))))

theorem digest_checked_105 : digestHex after427 = selectedRecord105.digest := by decide +kernel

theorem hash_checked_105 : HashEvaluated selectedRecord105 :=
  sha256_of_chain input_checked_105 partition_checked_105.1
    chain_checked_105 digest_checked_105

noncomputable def selectedRecord106 : Phase17Preimages.HashRecord := (Phase17Preimages.record1.ties.getD 4 { json := [], preimage := [], digest := "" })
noncomputable def parts106 : List Block := [block11, block415, block416, block423, block428]
theorem input_checked_106 : InputValid selectedRecord106.preimage := by decide +kernel

theorem partition_checked_106 :
    blocks (pad selectedRecord106.preimage) = parts106 ∧
    parts106.flatten = pad selectedRecord106.preimage ∧
    (pad selectedRecord106.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_106 : CompressionChain initial parts106 after428 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_423 (CompressionChain.cons block_step_428 (CompressionChain.nil after428))))))

theorem digest_checked_106 : digestHex after428 = selectedRecord106.digest := by decide +kernel

theorem hash_checked_106 : HashEvaluated selectedRecord106 :=
  sha256_of_chain input_checked_106 partition_checked_106.1
    chain_checked_106 digest_checked_106

noncomputable def selectedRecord107 : Phase17Preimages.HashRecord := (Phase17Preimages.record2.ties.getD 0 { json := [], preimage := [], digest := "" })
noncomputable def parts107 : List Block := [block11, block415, block416, block429, block430]
theorem input_checked_107 : InputValid selectedRecord107.preimage := by decide +kernel

theorem partition_checked_107 :
    blocks (pad selectedRecord107.preimage) = parts107 ∧
    parts107.flatten = pad selectedRecord107.preimage ∧
    (pad selectedRecord107.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_107 : CompressionChain initial parts107 after430 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_429 (CompressionChain.cons block_step_430 (CompressionChain.nil after430))))))

theorem digest_checked_107 : digestHex after430 = selectedRecord107.digest := by decide +kernel

theorem hash_checked_107 : HashEvaluated selectedRecord107 :=
  sha256_of_chain input_checked_107 partition_checked_107.1
    chain_checked_107 digest_checked_107

noncomputable def selectedRecord108 : Phase17Preimages.HashRecord := (Phase17Preimages.record2.ties.getD 1 { json := [], preimage := [], digest := "" })
noncomputable def parts108 : List Block := [block11, block415, block416, block429, block431]
theorem input_checked_108 : InputValid selectedRecord108.preimage := by decide +kernel

theorem partition_checked_108 :
    blocks (pad selectedRecord108.preimage) = parts108 ∧
    parts108.flatten = pad selectedRecord108.preimage ∧
    (pad selectedRecord108.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_108 : CompressionChain initial parts108 after431 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_429 (CompressionChain.cons block_step_431 (CompressionChain.nil after431))))))

theorem digest_checked_108 : digestHex after431 = selectedRecord108.digest := by decide +kernel

theorem hash_checked_108 : HashEvaluated selectedRecord108 :=
  sha256_of_chain input_checked_108 partition_checked_108.1
    chain_checked_108 digest_checked_108

noncomputable def selectedRecord109 : Phase17Preimages.HashRecord := (Phase17Preimages.record2.ties.getD 2 { json := [], preimage := [], digest := "" })
noncomputable def parts109 : List Block := [block11, block415, block416, block429, block432]
theorem input_checked_109 : InputValid selectedRecord109.preimage := by decide +kernel

theorem partition_checked_109 :
    blocks (pad selectedRecord109.preimage) = parts109 ∧
    parts109.flatten = pad selectedRecord109.preimage ∧
    (pad selectedRecord109.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_109 : CompressionChain initial parts109 after432 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_429 (CompressionChain.cons block_step_432 (CompressionChain.nil after432))))))

theorem digest_checked_109 : digestHex after432 = selectedRecord109.digest := by decide +kernel

theorem hash_checked_109 : HashEvaluated selectedRecord109 :=
  sha256_of_chain input_checked_109 partition_checked_109.1
    chain_checked_109 digest_checked_109

noncomputable def selectedRecord110 : Phase17Preimages.HashRecord := (Phase17Preimages.record2.ties.getD 3 { json := [], preimage := [], digest := "" })
noncomputable def parts110 : List Block := [block11, block415, block416, block429, block433]
theorem input_checked_110 : InputValid selectedRecord110.preimage := by decide +kernel

theorem partition_checked_110 :
    blocks (pad selectedRecord110.preimage) = parts110 ∧
    parts110.flatten = pad selectedRecord110.preimage ∧
    (pad selectedRecord110.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_110 : CompressionChain initial parts110 after433 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_429 (CompressionChain.cons block_step_433 (CompressionChain.nil after433))))))

theorem digest_checked_110 : digestHex after433 = selectedRecord110.digest := by decide +kernel

theorem hash_checked_110 : HashEvaluated selectedRecord110 :=
  sha256_of_chain input_checked_110 partition_checked_110.1
    chain_checked_110 digest_checked_110

noncomputable def selectedRecord111 : Phase17Preimages.HashRecord := (Phase17Preimages.record2.ties.getD 4 { json := [], preimage := [], digest := "" })
noncomputable def parts111 : List Block := [block11, block415, block416, block429, block434]
theorem input_checked_111 : InputValid selectedRecord111.preimage := by decide +kernel

theorem partition_checked_111 :
    blocks (pad selectedRecord111.preimage) = parts111 ∧
    parts111.flatten = pad selectedRecord111.preimage ∧
    (pad selectedRecord111.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_111 : CompressionChain initial parts111 after434 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_429 (CompressionChain.cons block_step_434 (CompressionChain.nil after434))))))

theorem digest_checked_111 : digestHex after434 = selectedRecord111.digest := by decide +kernel

theorem hash_checked_111 : HashEvaluated selectedRecord111 :=
  sha256_of_chain input_checked_111 partition_checked_111.1
    chain_checked_111 digest_checked_111

noncomputable def selectedRecord112 : Phase17Preimages.HashRecord := (Phase17Preimages.record3.ties.getD 0 { json := [], preimage := [], digest := "" })
noncomputable def parts112 : List Block := [block11, block415, block416, block435, block436]
theorem input_checked_112 : InputValid selectedRecord112.preimage := by decide +kernel

theorem partition_checked_112 :
    blocks (pad selectedRecord112.preimage) = parts112 ∧
    parts112.flatten = pad selectedRecord112.preimage ∧
    (pad selectedRecord112.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_112 : CompressionChain initial parts112 after436 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_435 (CompressionChain.cons block_step_436 (CompressionChain.nil after436))))))

theorem digest_checked_112 : digestHex after436 = selectedRecord112.digest := by decide +kernel

theorem hash_checked_112 : HashEvaluated selectedRecord112 :=
  sha256_of_chain input_checked_112 partition_checked_112.1
    chain_checked_112 digest_checked_112

noncomputable def selectedRecord113 : Phase17Preimages.HashRecord := (Phase17Preimages.record3.ties.getD 1 { json := [], preimage := [], digest := "" })
noncomputable def parts113 : List Block := [block11, block415, block416, block435, block437]
theorem input_checked_113 : InputValid selectedRecord113.preimage := by decide +kernel

theorem partition_checked_113 :
    blocks (pad selectedRecord113.preimage) = parts113 ∧
    parts113.flatten = pad selectedRecord113.preimage ∧
    (pad selectedRecord113.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_113 : CompressionChain initial parts113 after437 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_435 (CompressionChain.cons block_step_437 (CompressionChain.nil after437))))))

theorem digest_checked_113 : digestHex after437 = selectedRecord113.digest := by decide +kernel

theorem hash_checked_113 : HashEvaluated selectedRecord113 :=
  sha256_of_chain input_checked_113 partition_checked_113.1
    chain_checked_113 digest_checked_113

noncomputable def selectedRecord114 : Phase17Preimages.HashRecord := (Phase17Preimages.record3.ties.getD 2 { json := [], preimage := [], digest := "" })
noncomputable def parts114 : List Block := [block11, block415, block416, block435, block438]
theorem input_checked_114 : InputValid selectedRecord114.preimage := by decide +kernel

theorem partition_checked_114 :
    blocks (pad selectedRecord114.preimage) = parts114 ∧
    parts114.flatten = pad selectedRecord114.preimage ∧
    (pad selectedRecord114.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_114 : CompressionChain initial parts114 after438 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_435 (CompressionChain.cons block_step_438 (CompressionChain.nil after438))))))

theorem digest_checked_114 : digestHex after438 = selectedRecord114.digest := by decide +kernel

theorem hash_checked_114 : HashEvaluated selectedRecord114 :=
  sha256_of_chain input_checked_114 partition_checked_114.1
    chain_checked_114 digest_checked_114

noncomputable def selectedRecord115 : Phase17Preimages.HashRecord := (Phase17Preimages.record3.ties.getD 3 { json := [], preimage := [], digest := "" })
noncomputable def parts115 : List Block := [block11, block415, block416, block435, block439]
theorem input_checked_115 : InputValid selectedRecord115.preimage := by decide +kernel

theorem partition_checked_115 :
    blocks (pad selectedRecord115.preimage) = parts115 ∧
    parts115.flatten = pad selectedRecord115.preimage ∧
    (pad selectedRecord115.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_115 : CompressionChain initial parts115 after439 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_435 (CompressionChain.cons block_step_439 (CompressionChain.nil after439))))))

theorem digest_checked_115 : digestHex after439 = selectedRecord115.digest := by decide +kernel

theorem hash_checked_115 : HashEvaluated selectedRecord115 :=
  sha256_of_chain input_checked_115 partition_checked_115.1
    chain_checked_115 digest_checked_115

noncomputable def selectedRecord116 : Phase17Preimages.HashRecord := (Phase17Preimages.record3.ties.getD 4 { json := [], preimage := [], digest := "" })
noncomputable def parts116 : List Block := [block11, block415, block416, block435, block440]
theorem input_checked_116 : InputValid selectedRecord116.preimage := by decide +kernel

theorem partition_checked_116 :
    blocks (pad selectedRecord116.preimage) = parts116 ∧
    parts116.flatten = pad selectedRecord116.preimage ∧
    (pad selectedRecord116.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_116 : CompressionChain initial parts116 after440 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_435 (CompressionChain.cons block_step_440 (CompressionChain.nil after440))))))

theorem digest_checked_116 : digestHex after440 = selectedRecord116.digest := by decide +kernel

theorem hash_checked_116 : HashEvaluated selectedRecord116 :=
  sha256_of_chain input_checked_116 partition_checked_116.1
    chain_checked_116 digest_checked_116

noncomputable def selectedRecord117 : Phase17Preimages.HashRecord := (Phase17Preimages.record4.ties.getD 0 { json := [], preimage := [], digest := "" })
noncomputable def parts117 : List Block := [block11, block415, block416, block441, block442]
theorem input_checked_117 : InputValid selectedRecord117.preimage := by decide +kernel

theorem partition_checked_117 :
    blocks (pad selectedRecord117.preimage) = parts117 ∧
    parts117.flatten = pad selectedRecord117.preimage ∧
    (pad selectedRecord117.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_117 : CompressionChain initial parts117 after442 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_441 (CompressionChain.cons block_step_442 (CompressionChain.nil after442))))))

theorem digest_checked_117 : digestHex after442 = selectedRecord117.digest := by decide +kernel

theorem hash_checked_117 : HashEvaluated selectedRecord117 :=
  sha256_of_chain input_checked_117 partition_checked_117.1
    chain_checked_117 digest_checked_117

noncomputable def selectedRecord118 : Phase17Preimages.HashRecord := (Phase17Preimages.record4.ties.getD 1 { json := [], preimage := [], digest := "" })
noncomputable def parts118 : List Block := [block11, block415, block416, block441, block443]
theorem input_checked_118 : InputValid selectedRecord118.preimage := by decide +kernel

theorem partition_checked_118 :
    blocks (pad selectedRecord118.preimage) = parts118 ∧
    parts118.flatten = pad selectedRecord118.preimage ∧
    (pad selectedRecord118.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_118 : CompressionChain initial parts118 after443 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_441 (CompressionChain.cons block_step_443 (CompressionChain.nil after443))))))

theorem digest_checked_118 : digestHex after443 = selectedRecord118.digest := by decide +kernel

theorem hash_checked_118 : HashEvaluated selectedRecord118 :=
  sha256_of_chain input_checked_118 partition_checked_118.1
    chain_checked_118 digest_checked_118

noncomputable def selectedRecord119 : Phase17Preimages.HashRecord := (Phase17Preimages.record4.ties.getD 2 { json := [], preimage := [], digest := "" })
noncomputable def parts119 : List Block := [block11, block415, block416, block441, block444]
theorem input_checked_119 : InputValid selectedRecord119.preimage := by decide +kernel

theorem partition_checked_119 :
    blocks (pad selectedRecord119.preimage) = parts119 ∧
    parts119.flatten = pad selectedRecord119.preimage ∧
    (pad selectedRecord119.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_119 : CompressionChain initial parts119 after444 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_441 (CompressionChain.cons block_step_444 (CompressionChain.nil after444))))))

theorem digest_checked_119 : digestHex after444 = selectedRecord119.digest := by decide +kernel

theorem hash_checked_119 : HashEvaluated selectedRecord119 :=
  sha256_of_chain input_checked_119 partition_checked_119.1
    chain_checked_119 digest_checked_119

noncomputable def selectedRecord120 : Phase17Preimages.HashRecord := (Phase17Preimages.record4.ties.getD 3 { json := [], preimage := [], digest := "" })
noncomputable def parts120 : List Block := [block11, block415, block416, block441, block445]
theorem input_checked_120 : InputValid selectedRecord120.preimage := by decide +kernel

theorem partition_checked_120 :
    blocks (pad selectedRecord120.preimage) = parts120 ∧
    parts120.flatten = pad selectedRecord120.preimage ∧
    (pad selectedRecord120.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_120 : CompressionChain initial parts120 after445 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_441 (CompressionChain.cons block_step_445 (CompressionChain.nil after445))))))

theorem digest_checked_120 : digestHex after445 = selectedRecord120.digest := by decide +kernel

theorem hash_checked_120 : HashEvaluated selectedRecord120 :=
  sha256_of_chain input_checked_120 partition_checked_120.1
    chain_checked_120 digest_checked_120

noncomputable def selectedRecord121 : Phase17Preimages.HashRecord := (Phase17Preimages.record4.ties.getD 4 { json := [], preimage := [], digest := "" })
noncomputable def parts121 : List Block := [block11, block415, block416, block441, block446]
theorem input_checked_121 : InputValid selectedRecord121.preimage := by decide +kernel

theorem partition_checked_121 :
    blocks (pad selectedRecord121.preimage) = parts121 ∧
    parts121.flatten = pad selectedRecord121.preimage ∧
    (pad selectedRecord121.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_121 : CompressionChain initial parts121 after446 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_441 (CompressionChain.cons block_step_446 (CompressionChain.nil after446))))))

theorem digest_checked_121 : digestHex after446 = selectedRecord121.digest := by decide +kernel

theorem hash_checked_121 : HashEvaluated selectedRecord121 :=
  sha256_of_chain input_checked_121 partition_checked_121.1
    chain_checked_121 digest_checked_121

noncomputable def selectedRecord122 : Phase17Preimages.HashRecord := (Phase17Preimages.record5.ties.getD 0 { json := [], preimage := [], digest := "" })
noncomputable def parts122 : List Block := [block11, block415, block416, block447, block448]
theorem input_checked_122 : InputValid selectedRecord122.preimage := by decide +kernel

theorem partition_checked_122 :
    blocks (pad selectedRecord122.preimage) = parts122 ∧
    parts122.flatten = pad selectedRecord122.preimage ∧
    (pad selectedRecord122.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_122 : CompressionChain initial parts122 after448 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_447 (CompressionChain.cons block_step_448 (CompressionChain.nil after448))))))

theorem digest_checked_122 : digestHex after448 = selectedRecord122.digest := by decide +kernel

theorem hash_checked_122 : HashEvaluated selectedRecord122 :=
  sha256_of_chain input_checked_122 partition_checked_122.1
    chain_checked_122 digest_checked_122

noncomputable def selectedRecord123 : Phase17Preimages.HashRecord := (Phase17Preimages.record5.ties.getD 1 { json := [], preimage := [], digest := "" })
noncomputable def parts123 : List Block := [block11, block415, block416, block447, block449]
theorem input_checked_123 : InputValid selectedRecord123.preimage := by decide +kernel

theorem partition_checked_123 :
    blocks (pad selectedRecord123.preimage) = parts123 ∧
    parts123.flatten = pad selectedRecord123.preimage ∧
    (pad selectedRecord123.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_123 : CompressionChain initial parts123 after449 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_447 (CompressionChain.cons block_step_449 (CompressionChain.nil after449))))))

theorem digest_checked_123 : digestHex after449 = selectedRecord123.digest := by decide +kernel

theorem hash_checked_123 : HashEvaluated selectedRecord123 :=
  sha256_of_chain input_checked_123 partition_checked_123.1
    chain_checked_123 digest_checked_123

noncomputable def selectedRecord124 : Phase17Preimages.HashRecord := (Phase17Preimages.record5.ties.getD 2 { json := [], preimage := [], digest := "" })
noncomputable def parts124 : List Block := [block11, block415, block416, block447, block450]
theorem input_checked_124 : InputValid selectedRecord124.preimage := by decide +kernel

theorem partition_checked_124 :
    blocks (pad selectedRecord124.preimage) = parts124 ∧
    parts124.flatten = pad selectedRecord124.preimage ∧
    (pad selectedRecord124.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_124 : CompressionChain initial parts124 after450 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_447 (CompressionChain.cons block_step_450 (CompressionChain.nil after450))))))

theorem digest_checked_124 : digestHex after450 = selectedRecord124.digest := by decide +kernel

theorem hash_checked_124 : HashEvaluated selectedRecord124 :=
  sha256_of_chain input_checked_124 partition_checked_124.1
    chain_checked_124 digest_checked_124

noncomputable def selectedRecord125 : Phase17Preimages.HashRecord := (Phase17Preimages.record5.ties.getD 3 { json := [], preimage := [], digest := "" })
noncomputable def parts125 : List Block := [block11, block415, block416, block447, block451]
theorem input_checked_125 : InputValid selectedRecord125.preimage := by decide +kernel

theorem partition_checked_125 :
    blocks (pad selectedRecord125.preimage) = parts125 ∧
    parts125.flatten = pad selectedRecord125.preimage ∧
    (pad selectedRecord125.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_125 : CompressionChain initial parts125 after451 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_447 (CompressionChain.cons block_step_451 (CompressionChain.nil after451))))))

theorem digest_checked_125 : digestHex after451 = selectedRecord125.digest := by decide +kernel

theorem hash_checked_125 : HashEvaluated selectedRecord125 :=
  sha256_of_chain input_checked_125 partition_checked_125.1
    chain_checked_125 digest_checked_125

noncomputable def selectedRecord126 : Phase17Preimages.HashRecord := (Phase17Preimages.record5.ties.getD 4 { json := [], preimage := [], digest := "" })
noncomputable def parts126 : List Block := [block11, block415, block416, block447, block452]
theorem input_checked_126 : InputValid selectedRecord126.preimage := by decide +kernel

theorem partition_checked_126 :
    blocks (pad selectedRecord126.preimage) = parts126 ∧
    parts126.flatten = pad selectedRecord126.preimage ∧
    (pad selectedRecord126.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_126 : CompressionChain initial parts126 after452 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_447 (CompressionChain.cons block_step_452 (CompressionChain.nil after452))))))

theorem digest_checked_126 : digestHex after452 = selectedRecord126.digest := by decide +kernel

theorem hash_checked_126 : HashEvaluated selectedRecord126 :=
  sha256_of_chain input_checked_126 partition_checked_126.1
    chain_checked_126 digest_checked_126

noncomputable def selectedRecord127 : Phase17Preimages.HashRecord := (Phase17Preimages.record6.ties.getD 0 { json := [], preimage := [], digest := "" })
noncomputable def parts127 : List Block := [block11, block415, block416, block453, block454]
theorem input_checked_127 : InputValid selectedRecord127.preimage := by decide +kernel

theorem partition_checked_127 :
    blocks (pad selectedRecord127.preimage) = parts127 ∧
    parts127.flatten = pad selectedRecord127.preimage ∧
    (pad selectedRecord127.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_127 : CompressionChain initial parts127 after454 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_453 (CompressionChain.cons block_step_454 (CompressionChain.nil after454))))))

theorem digest_checked_127 : digestHex after454 = selectedRecord127.digest := by decide +kernel

theorem hash_checked_127 : HashEvaluated selectedRecord127 :=
  sha256_of_chain input_checked_127 partition_checked_127.1
    chain_checked_127 digest_checked_127

noncomputable def selectedRecord128 : Phase17Preimages.HashRecord := (Phase17Preimages.record6.ties.getD 1 { json := [], preimage := [], digest := "" })
noncomputable def parts128 : List Block := [block11, block415, block416, block453, block455]
theorem input_checked_128 : InputValid selectedRecord128.preimage := by decide +kernel

theorem partition_checked_128 :
    blocks (pad selectedRecord128.preimage) = parts128 ∧
    parts128.flatten = pad selectedRecord128.preimage ∧
    (pad selectedRecord128.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_128 : CompressionChain initial parts128 after455 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_453 (CompressionChain.cons block_step_455 (CompressionChain.nil after455))))))

theorem digest_checked_128 : digestHex after455 = selectedRecord128.digest := by decide +kernel

theorem hash_checked_128 : HashEvaluated selectedRecord128 :=
  sha256_of_chain input_checked_128 partition_checked_128.1
    chain_checked_128 digest_checked_128

noncomputable def selectedRecord129 : Phase17Preimages.HashRecord := (Phase17Preimages.record6.ties.getD 2 { json := [], preimage := [], digest := "" })
noncomputable def parts129 : List Block := [block11, block415, block416, block453, block456]
theorem input_checked_129 : InputValid selectedRecord129.preimage := by decide +kernel

theorem partition_checked_129 :
    blocks (pad selectedRecord129.preimage) = parts129 ∧
    parts129.flatten = pad selectedRecord129.preimage ∧
    (pad selectedRecord129.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_129 : CompressionChain initial parts129 after456 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_453 (CompressionChain.cons block_step_456 (CompressionChain.nil after456))))))

theorem digest_checked_129 : digestHex after456 = selectedRecord129.digest := by decide +kernel

theorem hash_checked_129 : HashEvaluated selectedRecord129 :=
  sha256_of_chain input_checked_129 partition_checked_129.1
    chain_checked_129 digest_checked_129

noncomputable def selectedRecord130 : Phase17Preimages.HashRecord := (Phase17Preimages.record6.ties.getD 3 { json := [], preimage := [], digest := "" })
noncomputable def parts130 : List Block := [block11, block415, block416, block453, block457]
theorem input_checked_130 : InputValid selectedRecord130.preimage := by decide +kernel

theorem partition_checked_130 :
    blocks (pad selectedRecord130.preimage) = parts130 ∧
    parts130.flatten = pad selectedRecord130.preimage ∧
    (pad selectedRecord130.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_130 : CompressionChain initial parts130 after457 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_453 (CompressionChain.cons block_step_457 (CompressionChain.nil after457))))))

theorem digest_checked_130 : digestHex after457 = selectedRecord130.digest := by decide +kernel

theorem hash_checked_130 : HashEvaluated selectedRecord130 :=
  sha256_of_chain input_checked_130 partition_checked_130.1
    chain_checked_130 digest_checked_130

noncomputable def selectedRecord131 : Phase17Preimages.HashRecord := (Phase17Preimages.record6.ties.getD 4 { json := [], preimage := [], digest := "" })
noncomputable def parts131 : List Block := [block11, block415, block416, block453, block458]
theorem input_checked_131 : InputValid selectedRecord131.preimage := by decide +kernel

theorem partition_checked_131 :
    blocks (pad selectedRecord131.preimage) = parts131 ∧
    parts131.flatten = pad selectedRecord131.preimage ∧
    (pad selectedRecord131.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_131 : CompressionChain initial parts131 after458 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_453 (CompressionChain.cons block_step_458 (CompressionChain.nil after458))))))

theorem digest_checked_131 : digestHex after458 = selectedRecord131.digest := by decide +kernel

theorem hash_checked_131 : HashEvaluated selectedRecord131 :=
  sha256_of_chain input_checked_131 partition_checked_131.1
    chain_checked_131 digest_checked_131

noncomputable def selectedRecord132 : Phase17Preimages.HashRecord := (Phase17Preimages.record7.ties.getD 0 { json := [], preimage := [], digest := "" })
noncomputable def parts132 : List Block := [block11, block415, block416, block459, block460]
theorem input_checked_132 : InputValid selectedRecord132.preimage := by decide +kernel

theorem partition_checked_132 :
    blocks (pad selectedRecord132.preimage) = parts132 ∧
    parts132.flatten = pad selectedRecord132.preimage ∧
    (pad selectedRecord132.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_132 : CompressionChain initial parts132 after460 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_459 (CompressionChain.cons block_step_460 (CompressionChain.nil after460))))))

theorem digest_checked_132 : digestHex after460 = selectedRecord132.digest := by decide +kernel

theorem hash_checked_132 : HashEvaluated selectedRecord132 :=
  sha256_of_chain input_checked_132 partition_checked_132.1
    chain_checked_132 digest_checked_132

noncomputable def selectedRecord133 : Phase17Preimages.HashRecord := (Phase17Preimages.record7.ties.getD 1 { json := [], preimage := [], digest := "" })
noncomputable def parts133 : List Block := [block11, block415, block416, block459, block461]
theorem input_checked_133 : InputValid selectedRecord133.preimage := by decide +kernel

theorem partition_checked_133 :
    blocks (pad selectedRecord133.preimage) = parts133 ∧
    parts133.flatten = pad selectedRecord133.preimage ∧
    (pad selectedRecord133.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_133 : CompressionChain initial parts133 after461 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_459 (CompressionChain.cons block_step_461 (CompressionChain.nil after461))))))

theorem digest_checked_133 : digestHex after461 = selectedRecord133.digest := by decide +kernel

theorem hash_checked_133 : HashEvaluated selectedRecord133 :=
  sha256_of_chain input_checked_133 partition_checked_133.1
    chain_checked_133 digest_checked_133

noncomputable def selectedRecord134 : Phase17Preimages.HashRecord := (Phase17Preimages.record7.ties.getD 2 { json := [], preimage := [], digest := "" })
noncomputable def parts134 : List Block := [block11, block415, block416, block459, block462]
theorem input_checked_134 : InputValid selectedRecord134.preimage := by decide +kernel

theorem partition_checked_134 :
    blocks (pad selectedRecord134.preimage) = parts134 ∧
    parts134.flatten = pad selectedRecord134.preimage ∧
    (pad selectedRecord134.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_134 : CompressionChain initial parts134 after462 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_459 (CompressionChain.cons block_step_462 (CompressionChain.nil after462))))))

theorem digest_checked_134 : digestHex after462 = selectedRecord134.digest := by decide +kernel

theorem hash_checked_134 : HashEvaluated selectedRecord134 :=
  sha256_of_chain input_checked_134 partition_checked_134.1
    chain_checked_134 digest_checked_134

noncomputable def selectedRecord135 : Phase17Preimages.HashRecord := (Phase17Preimages.record7.ties.getD 3 { json := [], preimage := [], digest := "" })
noncomputable def parts135 : List Block := [block11, block415, block416, block459, block463]
theorem input_checked_135 : InputValid selectedRecord135.preimage := by decide +kernel

theorem partition_checked_135 :
    blocks (pad selectedRecord135.preimage) = parts135 ∧
    parts135.flatten = pad selectedRecord135.preimage ∧
    (pad selectedRecord135.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_135 : CompressionChain initial parts135 after463 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_459 (CompressionChain.cons block_step_463 (CompressionChain.nil after463))))))

theorem digest_checked_135 : digestHex after463 = selectedRecord135.digest := by decide +kernel

theorem hash_checked_135 : HashEvaluated selectedRecord135 :=
  sha256_of_chain input_checked_135 partition_checked_135.1
    chain_checked_135 digest_checked_135

noncomputable def selectedRecord136 : Phase17Preimages.HashRecord := (Phase17Preimages.record7.ties.getD 4 { json := [], preimage := [], digest := "" })
noncomputable def parts136 : List Block := [block11, block415, block416, block459, block464]
theorem input_checked_136 : InputValid selectedRecord136.preimage := by decide +kernel

theorem partition_checked_136 :
    blocks (pad selectedRecord136.preimage) = parts136 ∧
    parts136.flatten = pad selectedRecord136.preimage ∧
    (pad selectedRecord136.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_136 : CompressionChain initial parts136 after464 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_459 (CompressionChain.cons block_step_464 (CompressionChain.nil after464))))))

theorem digest_checked_136 : digestHex after464 = selectedRecord136.digest := by decide +kernel

theorem hash_checked_136 : HashEvaluated selectedRecord136 :=
  sha256_of_chain input_checked_136 partition_checked_136.1
    chain_checked_136 digest_checked_136

noncomputable def selectedRecord137 : Phase17Preimages.HashRecord := (Phase17Preimages.record8.ties.getD 0 { json := [], preimage := [], digest := "" })
noncomputable def parts137 : List Block := [block11, block415, block416, block465, block466]
theorem input_checked_137 : InputValid selectedRecord137.preimage := by decide +kernel

theorem partition_checked_137 :
    blocks (pad selectedRecord137.preimage) = parts137 ∧
    parts137.flatten = pad selectedRecord137.preimage ∧
    (pad selectedRecord137.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_137 : CompressionChain initial parts137 after466 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_465 (CompressionChain.cons block_step_466 (CompressionChain.nil after466))))))

theorem digest_checked_137 : digestHex after466 = selectedRecord137.digest := by decide +kernel

theorem hash_checked_137 : HashEvaluated selectedRecord137 :=
  sha256_of_chain input_checked_137 partition_checked_137.1
    chain_checked_137 digest_checked_137

noncomputable def selectedRecord138 : Phase17Preimages.HashRecord := (Phase17Preimages.record8.ties.getD 1 { json := [], preimage := [], digest := "" })
noncomputable def parts138 : List Block := [block11, block415, block416, block465, block467]
theorem input_checked_138 : InputValid selectedRecord138.preimage := by decide +kernel

theorem partition_checked_138 :
    blocks (pad selectedRecord138.preimage) = parts138 ∧
    parts138.flatten = pad selectedRecord138.preimage ∧
    (pad selectedRecord138.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_138 : CompressionChain initial parts138 after467 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_465 (CompressionChain.cons block_step_467 (CompressionChain.nil after467))))))

theorem digest_checked_138 : digestHex after467 = selectedRecord138.digest := by decide +kernel

theorem hash_checked_138 : HashEvaluated selectedRecord138 :=
  sha256_of_chain input_checked_138 partition_checked_138.1
    chain_checked_138 digest_checked_138

noncomputable def selectedRecord139 : Phase17Preimages.HashRecord := (Phase17Preimages.record8.ties.getD 2 { json := [], preimage := [], digest := "" })
noncomputable def parts139 : List Block := [block11, block415, block416, block465, block468]
theorem input_checked_139 : InputValid selectedRecord139.preimage := by decide +kernel

theorem partition_checked_139 :
    blocks (pad selectedRecord139.preimage) = parts139 ∧
    parts139.flatten = pad selectedRecord139.preimage ∧
    (pad selectedRecord139.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_139 : CompressionChain initial parts139 after468 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_465 (CompressionChain.cons block_step_468 (CompressionChain.nil after468))))))

theorem digest_checked_139 : digestHex after468 = selectedRecord139.digest := by decide +kernel

theorem hash_checked_139 : HashEvaluated selectedRecord139 :=
  sha256_of_chain input_checked_139 partition_checked_139.1
    chain_checked_139 digest_checked_139

noncomputable def selectedRecord140 : Phase17Preimages.HashRecord := (Phase17Preimages.record8.ties.getD 3 { json := [], preimage := [], digest := "" })
noncomputable def parts140 : List Block := [block11, block415, block416, block465, block469]
theorem input_checked_140 : InputValid selectedRecord140.preimage := by decide +kernel

theorem partition_checked_140 :
    blocks (pad selectedRecord140.preimage) = parts140 ∧
    parts140.flatten = pad selectedRecord140.preimage ∧
    (pad selectedRecord140.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_140 : CompressionChain initial parts140 after469 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_465 (CompressionChain.cons block_step_469 (CompressionChain.nil after469))))))

theorem digest_checked_140 : digestHex after469 = selectedRecord140.digest := by decide +kernel

theorem hash_checked_140 : HashEvaluated selectedRecord140 :=
  sha256_of_chain input_checked_140 partition_checked_140.1
    chain_checked_140 digest_checked_140

noncomputable def selectedRecord141 : Phase17Preimages.HashRecord := (Phase17Preimages.record8.ties.getD 4 { json := [], preimage := [], digest := "" })
noncomputable def parts141 : List Block := [block11, block415, block416, block465, block470]
theorem input_checked_141 : InputValid selectedRecord141.preimage := by decide +kernel

theorem partition_checked_141 :
    blocks (pad selectedRecord141.preimage) = parts141 ∧
    parts141.flatten = pad selectedRecord141.preimage ∧
    (pad selectedRecord141.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_141 : CompressionChain initial parts141 after470 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_465 (CompressionChain.cons block_step_470 (CompressionChain.nil after470))))))

theorem digest_checked_141 : digestHex after470 = selectedRecord141.digest := by decide +kernel

theorem hash_checked_141 : HashEvaluated selectedRecord141 :=
  sha256_of_chain input_checked_141 partition_checked_141.1
    chain_checked_141 digest_checked_141

noncomputable def selectedRecord142 : Phase17Preimages.HashRecord := (Phase17Preimages.record9.ties.getD 0 { json := [], preimage := [], digest := "" })
noncomputable def parts142 : List Block := [block11, block415, block416, block471, block472]
theorem input_checked_142 : InputValid selectedRecord142.preimage := by decide +kernel

theorem partition_checked_142 :
    blocks (pad selectedRecord142.preimage) = parts142 ∧
    parts142.flatten = pad selectedRecord142.preimage ∧
    (pad selectedRecord142.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_142 : CompressionChain initial parts142 after472 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_471 (CompressionChain.cons block_step_472 (CompressionChain.nil after472))))))

theorem digest_checked_142 : digestHex after472 = selectedRecord142.digest := by decide +kernel

theorem hash_checked_142 : HashEvaluated selectedRecord142 :=
  sha256_of_chain input_checked_142 partition_checked_142.1
    chain_checked_142 digest_checked_142

noncomputable def selectedRecord143 : Phase17Preimages.HashRecord := (Phase17Preimages.record9.ties.getD 1 { json := [], preimage := [], digest := "" })
noncomputable def parts143 : List Block := [block11, block415, block416, block471, block473]
theorem input_checked_143 : InputValid selectedRecord143.preimage := by decide +kernel

theorem partition_checked_143 :
    blocks (pad selectedRecord143.preimage) = parts143 ∧
    parts143.flatten = pad selectedRecord143.preimage ∧
    (pad selectedRecord143.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_143 : CompressionChain initial parts143 after473 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_471 (CompressionChain.cons block_step_473 (CompressionChain.nil after473))))))

theorem digest_checked_143 : digestHex after473 = selectedRecord143.digest := by decide +kernel

theorem hash_checked_143 : HashEvaluated selectedRecord143 :=
  sha256_of_chain input_checked_143 partition_checked_143.1
    chain_checked_143 digest_checked_143

noncomputable def selectedRecord144 : Phase17Preimages.HashRecord := (Phase17Preimages.record9.ties.getD 2 { json := [], preimage := [], digest := "" })
noncomputable def parts144 : List Block := [block11, block415, block416, block471, block474]
theorem input_checked_144 : InputValid selectedRecord144.preimage := by decide +kernel

theorem partition_checked_144 :
    blocks (pad selectedRecord144.preimage) = parts144 ∧
    parts144.flatten = pad selectedRecord144.preimage ∧
    (pad selectedRecord144.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_144 : CompressionChain initial parts144 after474 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_471 (CompressionChain.cons block_step_474 (CompressionChain.nil after474))))))

theorem digest_checked_144 : digestHex after474 = selectedRecord144.digest := by decide +kernel

theorem hash_checked_144 : HashEvaluated selectedRecord144 :=
  sha256_of_chain input_checked_144 partition_checked_144.1
    chain_checked_144 digest_checked_144

noncomputable def selectedRecord145 : Phase17Preimages.HashRecord := (Phase17Preimages.record9.ties.getD 3 { json := [], preimage := [], digest := "" })
noncomputable def parts145 : List Block := [block11, block415, block416, block471, block475]
theorem input_checked_145 : InputValid selectedRecord145.preimage := by decide +kernel

theorem partition_checked_145 :
    blocks (pad selectedRecord145.preimage) = parts145 ∧
    parts145.flatten = pad selectedRecord145.preimage ∧
    (pad selectedRecord145.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_145 : CompressionChain initial parts145 after475 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_471 (CompressionChain.cons block_step_475 (CompressionChain.nil after475))))))

theorem digest_checked_145 : digestHex after475 = selectedRecord145.digest := by decide +kernel

theorem hash_checked_145 : HashEvaluated selectedRecord145 :=
  sha256_of_chain input_checked_145 partition_checked_145.1
    chain_checked_145 digest_checked_145

noncomputable def selectedRecord146 : Phase17Preimages.HashRecord := (Phase17Preimages.record9.ties.getD 4 { json := [], preimage := [], digest := "" })
noncomputable def parts146 : List Block := [block11, block415, block416, block471, block476]
theorem input_checked_146 : InputValid selectedRecord146.preimage := by decide +kernel

theorem partition_checked_146 :
    blocks (pad selectedRecord146.preimage) = parts146 ∧
    parts146.flatten = pad selectedRecord146.preimage ∧
    (pad selectedRecord146.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_146 : CompressionChain initial parts146 after476 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_471 (CompressionChain.cons block_step_476 (CompressionChain.nil after476))))))

theorem digest_checked_146 : digestHex after476 = selectedRecord146.digest := by decide +kernel

theorem hash_checked_146 : HashEvaluated selectedRecord146 :=
  sha256_of_chain input_checked_146 partition_checked_146.1
    chain_checked_146 digest_checked_146

noncomputable def selectedRecord147 : Phase17Preimages.HashRecord := (Phase17Preimages.record10.ties.getD 0 { json := [], preimage := [], digest := "" })
noncomputable def parts147 : List Block := [block11, block415, block416, block477, block478]
theorem input_checked_147 : InputValid selectedRecord147.preimage := by decide +kernel

theorem partition_checked_147 :
    blocks (pad selectedRecord147.preimage) = parts147 ∧
    parts147.flatten = pad selectedRecord147.preimage ∧
    (pad selectedRecord147.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_147 : CompressionChain initial parts147 after478 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_477 (CompressionChain.cons block_step_478 (CompressionChain.nil after478))))))

theorem digest_checked_147 : digestHex after478 = selectedRecord147.digest := by decide +kernel

theorem hash_checked_147 : HashEvaluated selectedRecord147 :=
  sha256_of_chain input_checked_147 partition_checked_147.1
    chain_checked_147 digest_checked_147

noncomputable def selectedRecord148 : Phase17Preimages.HashRecord := (Phase17Preimages.record10.ties.getD 1 { json := [], preimage := [], digest := "" })
noncomputable def parts148 : List Block := [block11, block415, block416, block477, block479]
theorem input_checked_148 : InputValid selectedRecord148.preimage := by decide +kernel

theorem partition_checked_148 :
    blocks (pad selectedRecord148.preimage) = parts148 ∧
    parts148.flatten = pad selectedRecord148.preimage ∧
    (pad selectedRecord148.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_148 : CompressionChain initial parts148 after479 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_477 (CompressionChain.cons block_step_479 (CompressionChain.nil after479))))))

theorem digest_checked_148 : digestHex after479 = selectedRecord148.digest := by decide +kernel

theorem hash_checked_148 : HashEvaluated selectedRecord148 :=
  sha256_of_chain input_checked_148 partition_checked_148.1
    chain_checked_148 digest_checked_148

noncomputable def selectedRecord149 : Phase17Preimages.HashRecord := (Phase17Preimages.record10.ties.getD 2 { json := [], preimage := [], digest := "" })
noncomputable def parts149 : List Block := [block11, block415, block416, block477, block480]
theorem input_checked_149 : InputValid selectedRecord149.preimage := by decide +kernel

theorem partition_checked_149 :
    blocks (pad selectedRecord149.preimage) = parts149 ∧
    parts149.flatten = pad selectedRecord149.preimage ∧
    (pad selectedRecord149.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_149 : CompressionChain initial parts149 after480 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_477 (CompressionChain.cons block_step_480 (CompressionChain.nil after480))))))

theorem digest_checked_149 : digestHex after480 = selectedRecord149.digest := by decide +kernel

theorem hash_checked_149 : HashEvaluated selectedRecord149 :=
  sha256_of_chain input_checked_149 partition_checked_149.1
    chain_checked_149 digest_checked_149

noncomputable def selectedRecord150 : Phase17Preimages.HashRecord := (Phase17Preimages.record10.ties.getD 3 { json := [], preimage := [], digest := "" })
noncomputable def parts150 : List Block := [block11, block415, block416, block477, block481]
theorem input_checked_150 : InputValid selectedRecord150.preimage := by decide +kernel

theorem partition_checked_150 :
    blocks (pad selectedRecord150.preimage) = parts150 ∧
    parts150.flatten = pad selectedRecord150.preimage ∧
    (pad selectedRecord150.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_150 : CompressionChain initial parts150 after481 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_477 (CompressionChain.cons block_step_481 (CompressionChain.nil after481))))))

theorem digest_checked_150 : digestHex after481 = selectedRecord150.digest := by decide +kernel

theorem hash_checked_150 : HashEvaluated selectedRecord150 :=
  sha256_of_chain input_checked_150 partition_checked_150.1
    chain_checked_150 digest_checked_150

noncomputable def selectedRecord151 : Phase17Preimages.HashRecord := (Phase17Preimages.record10.ties.getD 4 { json := [], preimage := [], digest := "" })
noncomputable def parts151 : List Block := [block11, block415, block416, block477, block482]
theorem input_checked_151 : InputValid selectedRecord151.preimage := by decide +kernel

theorem partition_checked_151 :
    blocks (pad selectedRecord151.preimage) = parts151 ∧
    parts151.flatten = pad selectedRecord151.preimage ∧
    (pad selectedRecord151.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_151 : CompressionChain initial parts151 after482 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_477 (CompressionChain.cons block_step_482 (CompressionChain.nil after482))))))

theorem digest_checked_151 : digestHex after482 = selectedRecord151.digest := by decide +kernel

theorem hash_checked_151 : HashEvaluated selectedRecord151 :=
  sha256_of_chain input_checked_151 partition_checked_151.1
    chain_checked_151 digest_checked_151

noncomputable def selectedRecord152 : Phase17Preimages.HashRecord := (Phase17Preimages.record11.ties.getD 0 { json := [], preimage := [], digest := "" })
noncomputable def parts152 : List Block := [block11, block415, block416, block483, block484]
theorem input_checked_152 : InputValid selectedRecord152.preimage := by decide +kernel

theorem partition_checked_152 :
    blocks (pad selectedRecord152.preimage) = parts152 ∧
    parts152.flatten = pad selectedRecord152.preimage ∧
    (pad selectedRecord152.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_152 : CompressionChain initial parts152 after484 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_483 (CompressionChain.cons block_step_484 (CompressionChain.nil after484))))))

theorem digest_checked_152 : digestHex after484 = selectedRecord152.digest := by decide +kernel

theorem hash_checked_152 : HashEvaluated selectedRecord152 :=
  sha256_of_chain input_checked_152 partition_checked_152.1
    chain_checked_152 digest_checked_152

noncomputable def selectedRecord153 : Phase17Preimages.HashRecord := (Phase17Preimages.record11.ties.getD 1 { json := [], preimage := [], digest := "" })
noncomputable def parts153 : List Block := [block11, block415, block416, block483, block485]
theorem input_checked_153 : InputValid selectedRecord153.preimage := by decide +kernel

theorem partition_checked_153 :
    blocks (pad selectedRecord153.preimage) = parts153 ∧
    parts153.flatten = pad selectedRecord153.preimage ∧
    (pad selectedRecord153.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_153 : CompressionChain initial parts153 after485 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_483 (CompressionChain.cons block_step_485 (CompressionChain.nil after485))))))

theorem digest_checked_153 : digestHex after485 = selectedRecord153.digest := by decide +kernel

theorem hash_checked_153 : HashEvaluated selectedRecord153 :=
  sha256_of_chain input_checked_153 partition_checked_153.1
    chain_checked_153 digest_checked_153

noncomputable def selectedRecord154 : Phase17Preimages.HashRecord := (Phase17Preimages.record11.ties.getD 2 { json := [], preimage := [], digest := "" })
noncomputable def parts154 : List Block := [block11, block415, block416, block483, block486]
theorem input_checked_154 : InputValid selectedRecord154.preimage := by decide +kernel

theorem partition_checked_154 :
    blocks (pad selectedRecord154.preimage) = parts154 ∧
    parts154.flatten = pad selectedRecord154.preimage ∧
    (pad selectedRecord154.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_154 : CompressionChain initial parts154 after486 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_483 (CompressionChain.cons block_step_486 (CompressionChain.nil after486))))))

theorem digest_checked_154 : digestHex after486 = selectedRecord154.digest := by decide +kernel

theorem hash_checked_154 : HashEvaluated selectedRecord154 :=
  sha256_of_chain input_checked_154 partition_checked_154.1
    chain_checked_154 digest_checked_154

noncomputable def selectedRecord155 : Phase17Preimages.HashRecord := (Phase17Preimages.record11.ties.getD 3 { json := [], preimage := [], digest := "" })
noncomputable def parts155 : List Block := [block11, block415, block416, block483, block487]
theorem input_checked_155 : InputValid selectedRecord155.preimage := by decide +kernel

theorem partition_checked_155 :
    blocks (pad selectedRecord155.preimage) = parts155 ∧
    parts155.flatten = pad selectedRecord155.preimage ∧
    (pad selectedRecord155.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_155 : CompressionChain initial parts155 after487 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_483 (CompressionChain.cons block_step_487 (CompressionChain.nil after487))))))

theorem digest_checked_155 : digestHex after487 = selectedRecord155.digest := by decide +kernel

theorem hash_checked_155 : HashEvaluated selectedRecord155 :=
  sha256_of_chain input_checked_155 partition_checked_155.1
    chain_checked_155 digest_checked_155

noncomputable def selectedRecord156 : Phase17Preimages.HashRecord := (Phase17Preimages.record11.ties.getD 4 { json := [], preimage := [], digest := "" })
noncomputable def parts156 : List Block := [block11, block415, block416, block483, block488]
theorem input_checked_156 : InputValid selectedRecord156.preimage := by decide +kernel

theorem partition_checked_156 :
    blocks (pad selectedRecord156.preimage) = parts156 ∧
    parts156.flatten = pad selectedRecord156.preimage ∧
    (pad selectedRecord156.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_156 : CompressionChain initial parts156 after488 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_483 (CompressionChain.cons block_step_488 (CompressionChain.nil after488))))))

theorem digest_checked_156 : digestHex after488 = selectedRecord156.digest := by decide +kernel

theorem hash_checked_156 : HashEvaluated selectedRecord156 :=
  sha256_of_chain input_checked_156 partition_checked_156.1
    chain_checked_156 digest_checked_156

noncomputable def selectedRecord157 : Phase17Preimages.HashRecord := (Phase17Preimages.record12.ties.getD 0 { json := [], preimage := [], digest := "" })
noncomputable def parts157 : List Block := [block11, block415, block416, block489, block490]
theorem input_checked_157 : InputValid selectedRecord157.preimage := by decide +kernel

theorem partition_checked_157 :
    blocks (pad selectedRecord157.preimage) = parts157 ∧
    parts157.flatten = pad selectedRecord157.preimage ∧
    (pad selectedRecord157.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_157 : CompressionChain initial parts157 after490 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_489 (CompressionChain.cons block_step_490 (CompressionChain.nil after490))))))

theorem digest_checked_157 : digestHex after490 = selectedRecord157.digest := by decide +kernel

theorem hash_checked_157 : HashEvaluated selectedRecord157 :=
  sha256_of_chain input_checked_157 partition_checked_157.1
    chain_checked_157 digest_checked_157

noncomputable def selectedRecord158 : Phase17Preimages.HashRecord := (Phase17Preimages.record12.ties.getD 1 { json := [], preimage := [], digest := "" })
noncomputable def parts158 : List Block := [block11, block415, block416, block489, block491]
theorem input_checked_158 : InputValid selectedRecord158.preimage := by decide +kernel

theorem partition_checked_158 :
    blocks (pad selectedRecord158.preimage) = parts158 ∧
    parts158.flatten = pad selectedRecord158.preimage ∧
    (pad selectedRecord158.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_158 : CompressionChain initial parts158 after491 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_489 (CompressionChain.cons block_step_491 (CompressionChain.nil after491))))))

theorem digest_checked_158 : digestHex after491 = selectedRecord158.digest := by decide +kernel

theorem hash_checked_158 : HashEvaluated selectedRecord158 :=
  sha256_of_chain input_checked_158 partition_checked_158.1
    chain_checked_158 digest_checked_158

noncomputable def selectedRecord159 : Phase17Preimages.HashRecord := (Phase17Preimages.record12.ties.getD 2 { json := [], preimage := [], digest := "" })
noncomputable def parts159 : List Block := [block11, block415, block416, block489, block492]
theorem input_checked_159 : InputValid selectedRecord159.preimage := by decide +kernel

theorem partition_checked_159 :
    blocks (pad selectedRecord159.preimage) = parts159 ∧
    parts159.flatten = pad selectedRecord159.preimage ∧
    (pad selectedRecord159.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_159 : CompressionChain initial parts159 after492 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_489 (CompressionChain.cons block_step_492 (CompressionChain.nil after492))))))

theorem digest_checked_159 : digestHex after492 = selectedRecord159.digest := by decide +kernel

theorem hash_checked_159 : HashEvaluated selectedRecord159 :=
  sha256_of_chain input_checked_159 partition_checked_159.1
    chain_checked_159 digest_checked_159

noncomputable def selectedRecord160 : Phase17Preimages.HashRecord := (Phase17Preimages.record12.ties.getD 3 { json := [], preimage := [], digest := "" })
noncomputable def parts160 : List Block := [block11, block415, block416, block489, block493]
theorem input_checked_160 : InputValid selectedRecord160.preimage := by decide +kernel

theorem partition_checked_160 :
    blocks (pad selectedRecord160.preimage) = parts160 ∧
    parts160.flatten = pad selectedRecord160.preimage ∧
    (pad selectedRecord160.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_160 : CompressionChain initial parts160 after493 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_489 (CompressionChain.cons block_step_493 (CompressionChain.nil after493))))))

theorem digest_checked_160 : digestHex after493 = selectedRecord160.digest := by decide +kernel

theorem hash_checked_160 : HashEvaluated selectedRecord160 :=
  sha256_of_chain input_checked_160 partition_checked_160.1
    chain_checked_160 digest_checked_160

noncomputable def selectedRecord161 : Phase17Preimages.HashRecord := (Phase17Preimages.record12.ties.getD 4 { json := [], preimage := [], digest := "" })
noncomputable def parts161 : List Block := [block11, block415, block416, block489, block494]
theorem input_checked_161 : InputValid selectedRecord161.preimage := by decide +kernel

theorem partition_checked_161 :
    blocks (pad selectedRecord161.preimage) = parts161 ∧
    parts161.flatten = pad selectedRecord161.preimage ∧
    (pad selectedRecord161.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_161 : CompressionChain initial parts161 after494 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_489 (CompressionChain.cons block_step_494 (CompressionChain.nil after494))))))

theorem digest_checked_161 : digestHex after494 = selectedRecord161.digest := by decide +kernel

theorem hash_checked_161 : HashEvaluated selectedRecord161 :=
  sha256_of_chain input_checked_161 partition_checked_161.1
    chain_checked_161 digest_checked_161

noncomputable def selectedRecord162 : Phase17Preimages.HashRecord := (Phase17Preimages.record13.ties.getD 0 { json := [], preimage := [], digest := "" })
noncomputable def parts162 : List Block := [block11, block415, block416, block495, block496]
theorem input_checked_162 : InputValid selectedRecord162.preimage := by decide +kernel

theorem partition_checked_162 :
    blocks (pad selectedRecord162.preimage) = parts162 ∧
    parts162.flatten = pad selectedRecord162.preimage ∧
    (pad selectedRecord162.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_162 : CompressionChain initial parts162 after496 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_495 (CompressionChain.cons block_step_496 (CompressionChain.nil after496))))))

theorem digest_checked_162 : digestHex after496 = selectedRecord162.digest := by decide +kernel

theorem hash_checked_162 : HashEvaluated selectedRecord162 :=
  sha256_of_chain input_checked_162 partition_checked_162.1
    chain_checked_162 digest_checked_162

noncomputable def selectedRecord163 : Phase17Preimages.HashRecord := (Phase17Preimages.record13.ties.getD 1 { json := [], preimage := [], digest := "" })
noncomputable def parts163 : List Block := [block11, block415, block416, block495, block497]
theorem input_checked_163 : InputValid selectedRecord163.preimage := by decide +kernel

theorem partition_checked_163 :
    blocks (pad selectedRecord163.preimage) = parts163 ∧
    parts163.flatten = pad selectedRecord163.preimage ∧
    (pad selectedRecord163.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_163 : CompressionChain initial parts163 after497 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_495 (CompressionChain.cons block_step_497 (CompressionChain.nil after497))))))

theorem digest_checked_163 : digestHex after497 = selectedRecord163.digest := by decide +kernel

theorem hash_checked_163 : HashEvaluated selectedRecord163 :=
  sha256_of_chain input_checked_163 partition_checked_163.1
    chain_checked_163 digest_checked_163

noncomputable def selectedRecord164 : Phase17Preimages.HashRecord := (Phase17Preimages.record13.ties.getD 2 { json := [], preimage := [], digest := "" })
noncomputable def parts164 : List Block := [block11, block415, block416, block495, block498]
theorem input_checked_164 : InputValid selectedRecord164.preimage := by decide +kernel

theorem partition_checked_164 :
    blocks (pad selectedRecord164.preimage) = parts164 ∧
    parts164.flatten = pad selectedRecord164.preimage ∧
    (pad selectedRecord164.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_164 : CompressionChain initial parts164 after498 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_495 (CompressionChain.cons block_step_498 (CompressionChain.nil after498))))))

theorem digest_checked_164 : digestHex after498 = selectedRecord164.digest := by decide +kernel

theorem hash_checked_164 : HashEvaluated selectedRecord164 :=
  sha256_of_chain input_checked_164 partition_checked_164.1
    chain_checked_164 digest_checked_164

noncomputable def selectedRecord165 : Phase17Preimages.HashRecord := (Phase17Preimages.record13.ties.getD 3 { json := [], preimage := [], digest := "" })
noncomputable def parts165 : List Block := [block11, block415, block416, block495, block499]
theorem input_checked_165 : InputValid selectedRecord165.preimage := by decide +kernel

theorem partition_checked_165 :
    blocks (pad selectedRecord165.preimage) = parts165 ∧
    parts165.flatten = pad selectedRecord165.preimage ∧
    (pad selectedRecord165.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_165 : CompressionChain initial parts165 after499 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_495 (CompressionChain.cons block_step_499 (CompressionChain.nil after499))))))

theorem digest_checked_165 : digestHex after499 = selectedRecord165.digest := by decide +kernel

theorem hash_checked_165 : HashEvaluated selectedRecord165 :=
  sha256_of_chain input_checked_165 partition_checked_165.1
    chain_checked_165 digest_checked_165

noncomputable def selectedRecord166 : Phase17Preimages.HashRecord := (Phase17Preimages.record13.ties.getD 4 { json := [], preimage := [], digest := "" })
noncomputable def parts166 : List Block := [block11, block415, block416, block495, block500]
theorem input_checked_166 : InputValid selectedRecord166.preimage := by decide +kernel

theorem partition_checked_166 :
    blocks (pad selectedRecord166.preimage) = parts166 ∧
    parts166.flatten = pad selectedRecord166.preimage ∧
    (pad selectedRecord166.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_166 : CompressionChain initial parts166 after500 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_495 (CompressionChain.cons block_step_500 (CompressionChain.nil after500))))))

theorem digest_checked_166 : digestHex after500 = selectedRecord166.digest := by decide +kernel

theorem hash_checked_166 : HashEvaluated selectedRecord166 :=
  sha256_of_chain input_checked_166 partition_checked_166.1
    chain_checked_166 digest_checked_166

noncomputable def selectedRecord167 : Phase17Preimages.HashRecord := (Phase17Preimages.record14.ties.getD 0 { json := [], preimage := [], digest := "" })
noncomputable def parts167 : List Block := [block11, block415, block416, block501, block502]
theorem input_checked_167 : InputValid selectedRecord167.preimage := by decide +kernel

theorem partition_checked_167 :
    blocks (pad selectedRecord167.preimage) = parts167 ∧
    parts167.flatten = pad selectedRecord167.preimage ∧
    (pad selectedRecord167.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_167 : CompressionChain initial parts167 after502 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_501 (CompressionChain.cons block_step_502 (CompressionChain.nil after502))))))

theorem digest_checked_167 : digestHex after502 = selectedRecord167.digest := by decide +kernel

theorem hash_checked_167 : HashEvaluated selectedRecord167 :=
  sha256_of_chain input_checked_167 partition_checked_167.1
    chain_checked_167 digest_checked_167

noncomputable def selectedRecord168 : Phase17Preimages.HashRecord := (Phase17Preimages.record14.ties.getD 1 { json := [], preimage := [], digest := "" })
noncomputable def parts168 : List Block := [block11, block415, block416, block501, block503]
theorem input_checked_168 : InputValid selectedRecord168.preimage := by decide +kernel

theorem partition_checked_168 :
    blocks (pad selectedRecord168.preimage) = parts168 ∧
    parts168.flatten = pad selectedRecord168.preimage ∧
    (pad selectedRecord168.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_168 : CompressionChain initial parts168 after503 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_501 (CompressionChain.cons block_step_503 (CompressionChain.nil after503))))))

theorem digest_checked_168 : digestHex after503 = selectedRecord168.digest := by decide +kernel

theorem hash_checked_168 : HashEvaluated selectedRecord168 :=
  sha256_of_chain input_checked_168 partition_checked_168.1
    chain_checked_168 digest_checked_168

noncomputable def selectedRecord169 : Phase17Preimages.HashRecord := (Phase17Preimages.record14.ties.getD 2 { json := [], preimage := [], digest := "" })
noncomputable def parts169 : List Block := [block11, block415, block416, block501, block504]
theorem input_checked_169 : InputValid selectedRecord169.preimage := by decide +kernel

theorem partition_checked_169 :
    blocks (pad selectedRecord169.preimage) = parts169 ∧
    parts169.flatten = pad selectedRecord169.preimage ∧
    (pad selectedRecord169.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_169 : CompressionChain initial parts169 after504 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_501 (CompressionChain.cons block_step_504 (CompressionChain.nil after504))))))

theorem digest_checked_169 : digestHex after504 = selectedRecord169.digest := by decide +kernel

theorem hash_checked_169 : HashEvaluated selectedRecord169 :=
  sha256_of_chain input_checked_169 partition_checked_169.1
    chain_checked_169 digest_checked_169

noncomputable def selectedRecord170 : Phase17Preimages.HashRecord := (Phase17Preimages.record14.ties.getD 3 { json := [], preimage := [], digest := "" })
noncomputable def parts170 : List Block := [block11, block415, block416, block501, block505]
theorem input_checked_170 : InputValid selectedRecord170.preimage := by decide +kernel

theorem partition_checked_170 :
    blocks (pad selectedRecord170.preimage) = parts170 ∧
    parts170.flatten = pad selectedRecord170.preimage ∧
    (pad selectedRecord170.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_170 : CompressionChain initial parts170 after505 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_501 (CompressionChain.cons block_step_505 (CompressionChain.nil after505))))))

theorem digest_checked_170 : digestHex after505 = selectedRecord170.digest := by decide +kernel

theorem hash_checked_170 : HashEvaluated selectedRecord170 :=
  sha256_of_chain input_checked_170 partition_checked_170.1
    chain_checked_170 digest_checked_170

noncomputable def selectedRecord171 : Phase17Preimages.HashRecord := (Phase17Preimages.record14.ties.getD 4 { json := [], preimage := [], digest := "" })
noncomputable def parts171 : List Block := [block11, block415, block416, block501, block506]
theorem input_checked_171 : InputValid selectedRecord171.preimage := by decide +kernel

theorem partition_checked_171 :
    blocks (pad selectedRecord171.preimage) = parts171 ∧
    parts171.flatten = pad selectedRecord171.preimage ∧
    (pad selectedRecord171.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_171 : CompressionChain initial parts171 after506 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_501 (CompressionChain.cons block_step_506 (CompressionChain.nil after506))))))

theorem digest_checked_171 : digestHex after506 = selectedRecord171.digest := by decide +kernel

theorem hash_checked_171 : HashEvaluated selectedRecord171 :=
  sha256_of_chain input_checked_171 partition_checked_171.1
    chain_checked_171 digest_checked_171

noncomputable def selectedRecord172 : Phase17Preimages.HashRecord := (Phase17Preimages.record15.ties.getD 0 { json := [], preimage := [], digest := "" })
noncomputable def parts172 : List Block := [block11, block415, block416, block507, block508]
theorem input_checked_172 : InputValid selectedRecord172.preimage := by decide +kernel

theorem partition_checked_172 :
    blocks (pad selectedRecord172.preimage) = parts172 ∧
    parts172.flatten = pad selectedRecord172.preimage ∧
    (pad selectedRecord172.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_172 : CompressionChain initial parts172 after508 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_507 (CompressionChain.cons block_step_508 (CompressionChain.nil after508))))))

theorem digest_checked_172 : digestHex after508 = selectedRecord172.digest := by decide +kernel

theorem hash_checked_172 : HashEvaluated selectedRecord172 :=
  sha256_of_chain input_checked_172 partition_checked_172.1
    chain_checked_172 digest_checked_172

noncomputable def selectedRecord173 : Phase17Preimages.HashRecord := (Phase17Preimages.record15.ties.getD 1 { json := [], preimage := [], digest := "" })
noncomputable def parts173 : List Block := [block11, block415, block416, block507, block509]
theorem input_checked_173 : InputValid selectedRecord173.preimage := by decide +kernel

theorem partition_checked_173 :
    blocks (pad selectedRecord173.preimage) = parts173 ∧
    parts173.flatten = pad selectedRecord173.preimage ∧
    (pad selectedRecord173.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_173 : CompressionChain initial parts173 after509 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_507 (CompressionChain.cons block_step_509 (CompressionChain.nil after509))))))

theorem digest_checked_173 : digestHex after509 = selectedRecord173.digest := by decide +kernel

theorem hash_checked_173 : HashEvaluated selectedRecord173 :=
  sha256_of_chain input_checked_173 partition_checked_173.1
    chain_checked_173 digest_checked_173

noncomputable def selectedRecord174 : Phase17Preimages.HashRecord := (Phase17Preimages.record15.ties.getD 2 { json := [], preimage := [], digest := "" })
noncomputable def parts174 : List Block := [block11, block415, block416, block507, block510]
theorem input_checked_174 : InputValid selectedRecord174.preimage := by decide +kernel

theorem partition_checked_174 :
    blocks (pad selectedRecord174.preimage) = parts174 ∧
    parts174.flatten = pad selectedRecord174.preimage ∧
    (pad selectedRecord174.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_174 : CompressionChain initial parts174 after510 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_507 (CompressionChain.cons block_step_510 (CompressionChain.nil after510))))))

theorem digest_checked_174 : digestHex after510 = selectedRecord174.digest := by decide +kernel

theorem hash_checked_174 : HashEvaluated selectedRecord174 :=
  sha256_of_chain input_checked_174 partition_checked_174.1
    chain_checked_174 digest_checked_174

noncomputable def selectedRecord175 : Phase17Preimages.HashRecord := (Phase17Preimages.record15.ties.getD 3 { json := [], preimage := [], digest := "" })
noncomputable def parts175 : List Block := [block11, block415, block416, block507, block511]
theorem input_checked_175 : InputValid selectedRecord175.preimage := by decide +kernel

theorem partition_checked_175 :
    blocks (pad selectedRecord175.preimage) = parts175 ∧
    parts175.flatten = pad selectedRecord175.preimage ∧
    (pad selectedRecord175.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_175 : CompressionChain initial parts175 after511 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_507 (CompressionChain.cons block_step_511 (CompressionChain.nil after511))))))

theorem digest_checked_175 : digestHex after511 = selectedRecord175.digest := by decide +kernel

theorem hash_checked_175 : HashEvaluated selectedRecord175 :=
  sha256_of_chain input_checked_175 partition_checked_175.1
    chain_checked_175 digest_checked_175

noncomputable def selectedRecord176 : Phase17Preimages.HashRecord := (Phase17Preimages.record15.ties.getD 4 { json := [], preimage := [], digest := "" })
noncomputable def parts176 : List Block := [block11, block415, block416, block507, block512]
theorem input_checked_176 : InputValid selectedRecord176.preimage := by decide +kernel

theorem partition_checked_176 :
    blocks (pad selectedRecord176.preimage) = parts176 ∧
    parts176.flatten = pad selectedRecord176.preimage ∧
    (pad selectedRecord176.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_176 : CompressionChain initial parts176 after512 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_507 (CompressionChain.cons block_step_512 (CompressionChain.nil after512))))))

theorem digest_checked_176 : digestHex after512 = selectedRecord176.digest := by decide +kernel

theorem hash_checked_176 : HashEvaluated selectedRecord176 :=
  sha256_of_chain input_checked_176 partition_checked_176.1
    chain_checked_176 digest_checked_176

noncomputable def selectedRecord177 : Phase17Preimages.HashRecord := (Phase17Preimages.record16.ties.getD 0 { json := [], preimage := [], digest := "" })
noncomputable def parts177 : List Block := [block11, block415, block416, block513, block514]
theorem input_checked_177 : InputValid selectedRecord177.preimage := by decide +kernel

theorem partition_checked_177 :
    blocks (pad selectedRecord177.preimage) = parts177 ∧
    parts177.flatten = pad selectedRecord177.preimage ∧
    (pad selectedRecord177.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_177 : CompressionChain initial parts177 after514 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_513 (CompressionChain.cons block_step_514 (CompressionChain.nil after514))))))

theorem digest_checked_177 : digestHex after514 = selectedRecord177.digest := by decide +kernel

theorem hash_checked_177 : HashEvaluated selectedRecord177 :=
  sha256_of_chain input_checked_177 partition_checked_177.1
    chain_checked_177 digest_checked_177

noncomputable def selectedRecord178 : Phase17Preimages.HashRecord := (Phase17Preimages.record16.ties.getD 1 { json := [], preimage := [], digest := "" })
noncomputable def parts178 : List Block := [block11, block415, block416, block513, block515]
theorem input_checked_178 : InputValid selectedRecord178.preimage := by decide +kernel

theorem partition_checked_178 :
    blocks (pad selectedRecord178.preimage) = parts178 ∧
    parts178.flatten = pad selectedRecord178.preimage ∧
    (pad selectedRecord178.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_178 : CompressionChain initial parts178 after515 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_513 (CompressionChain.cons block_step_515 (CompressionChain.nil after515))))))

theorem digest_checked_178 : digestHex after515 = selectedRecord178.digest := by decide +kernel

theorem hash_checked_178 : HashEvaluated selectedRecord178 :=
  sha256_of_chain input_checked_178 partition_checked_178.1
    chain_checked_178 digest_checked_178

noncomputable def selectedRecord179 : Phase17Preimages.HashRecord := (Phase17Preimages.record16.ties.getD 2 { json := [], preimage := [], digest := "" })
noncomputable def parts179 : List Block := [block11, block415, block416, block513, block516]
theorem input_checked_179 : InputValid selectedRecord179.preimage := by decide +kernel

theorem partition_checked_179 :
    blocks (pad selectedRecord179.preimage) = parts179 ∧
    parts179.flatten = pad selectedRecord179.preimage ∧
    (pad selectedRecord179.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_179 : CompressionChain initial parts179 after516 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_513 (CompressionChain.cons block_step_516 (CompressionChain.nil after516))))))

theorem digest_checked_179 : digestHex after516 = selectedRecord179.digest := by decide +kernel

theorem hash_checked_179 : HashEvaluated selectedRecord179 :=
  sha256_of_chain input_checked_179 partition_checked_179.1
    chain_checked_179 digest_checked_179

noncomputable def selectedRecord180 : Phase17Preimages.HashRecord := (Phase17Preimages.record16.ties.getD 3 { json := [], preimage := [], digest := "" })
noncomputable def parts180 : List Block := [block11, block415, block416, block513, block517]
theorem input_checked_180 : InputValid selectedRecord180.preimage := by decide +kernel

theorem partition_checked_180 :
    blocks (pad selectedRecord180.preimage) = parts180 ∧
    parts180.flatten = pad selectedRecord180.preimage ∧
    (pad selectedRecord180.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_180 : CompressionChain initial parts180 after517 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_513 (CompressionChain.cons block_step_517 (CompressionChain.nil after517))))))

theorem digest_checked_180 : digestHex after517 = selectedRecord180.digest := by decide +kernel

theorem hash_checked_180 : HashEvaluated selectedRecord180 :=
  sha256_of_chain input_checked_180 partition_checked_180.1
    chain_checked_180 digest_checked_180

noncomputable def selectedRecord181 : Phase17Preimages.HashRecord := (Phase17Preimages.record16.ties.getD 4 { json := [], preimage := [], digest := "" })
noncomputable def parts181 : List Block := [block11, block415, block416, block513, block518]
theorem input_checked_181 : InputValid selectedRecord181.preimage := by decide +kernel

theorem partition_checked_181 :
    blocks (pad selectedRecord181.preimage) = parts181 ∧
    parts181.flatten = pad selectedRecord181.preimage ∧
    (pad selectedRecord181.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_181 : CompressionChain initial parts181 after518 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_513 (CompressionChain.cons block_step_518 (CompressionChain.nil after518))))))

theorem digest_checked_181 : digestHex after518 = selectedRecord181.digest := by decide +kernel

theorem hash_checked_181 : HashEvaluated selectedRecord181 :=
  sha256_of_chain input_checked_181 partition_checked_181.1
    chain_checked_181 digest_checked_181

noncomputable def selectedRecord182 : Phase17Preimages.HashRecord := (Phase17Preimages.record17.ties.getD 0 { json := [], preimage := [], digest := "" })
noncomputable def parts182 : List Block := [block11, block415, block416, block519, block520]
theorem input_checked_182 : InputValid selectedRecord182.preimage := by decide +kernel

theorem partition_checked_182 :
    blocks (pad selectedRecord182.preimage) = parts182 ∧
    parts182.flatten = pad selectedRecord182.preimage ∧
    (pad selectedRecord182.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_182 : CompressionChain initial parts182 after520 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_519 (CompressionChain.cons block_step_520 (CompressionChain.nil after520))))))

theorem digest_checked_182 : digestHex after520 = selectedRecord182.digest := by decide +kernel

theorem hash_checked_182 : HashEvaluated selectedRecord182 :=
  sha256_of_chain input_checked_182 partition_checked_182.1
    chain_checked_182 digest_checked_182

noncomputable def selectedRecord183 : Phase17Preimages.HashRecord := (Phase17Preimages.record17.ties.getD 1 { json := [], preimage := [], digest := "" })
noncomputable def parts183 : List Block := [block11, block415, block416, block519, block521]
theorem input_checked_183 : InputValid selectedRecord183.preimage := by decide +kernel

theorem partition_checked_183 :
    blocks (pad selectedRecord183.preimage) = parts183 ∧
    parts183.flatten = pad selectedRecord183.preimage ∧
    (pad selectedRecord183.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_183 : CompressionChain initial parts183 after521 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_519 (CompressionChain.cons block_step_521 (CompressionChain.nil after521))))))

theorem digest_checked_183 : digestHex after521 = selectedRecord183.digest := by decide +kernel

theorem hash_checked_183 : HashEvaluated selectedRecord183 :=
  sha256_of_chain input_checked_183 partition_checked_183.1
    chain_checked_183 digest_checked_183

noncomputable def selectedRecord184 : Phase17Preimages.HashRecord := (Phase17Preimages.record17.ties.getD 2 { json := [], preimage := [], digest := "" })
noncomputable def parts184 : List Block := [block11, block415, block416, block519, block522]
theorem input_checked_184 : InputValid selectedRecord184.preimage := by decide +kernel

theorem partition_checked_184 :
    blocks (pad selectedRecord184.preimage) = parts184 ∧
    parts184.flatten = pad selectedRecord184.preimage ∧
    (pad selectedRecord184.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_184 : CompressionChain initial parts184 after522 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_519 (CompressionChain.cons block_step_522 (CompressionChain.nil after522))))))

theorem digest_checked_184 : digestHex after522 = selectedRecord184.digest := by decide +kernel

theorem hash_checked_184 : HashEvaluated selectedRecord184 :=
  sha256_of_chain input_checked_184 partition_checked_184.1
    chain_checked_184 digest_checked_184

noncomputable def selectedRecord185 : Phase17Preimages.HashRecord := (Phase17Preimages.record17.ties.getD 3 { json := [], preimage := [], digest := "" })
noncomputable def parts185 : List Block := [block11, block415, block416, block519, block523]
theorem input_checked_185 : InputValid selectedRecord185.preimage := by decide +kernel

theorem partition_checked_185 :
    blocks (pad selectedRecord185.preimage) = parts185 ∧
    parts185.flatten = pad selectedRecord185.preimage ∧
    (pad selectedRecord185.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_185 : CompressionChain initial parts185 after523 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_519 (CompressionChain.cons block_step_523 (CompressionChain.nil after523))))))

theorem digest_checked_185 : digestHex after523 = selectedRecord185.digest := by decide +kernel

theorem hash_checked_185 : HashEvaluated selectedRecord185 :=
  sha256_of_chain input_checked_185 partition_checked_185.1
    chain_checked_185 digest_checked_185

noncomputable def selectedRecord186 : Phase17Preimages.HashRecord := (Phase17Preimages.record17.ties.getD 4 { json := [], preimage := [], digest := "" })
noncomputable def parts186 : List Block := [block11, block415, block416, block519, block524]
theorem input_checked_186 : InputValid selectedRecord186.preimage := by decide +kernel

theorem partition_checked_186 :
    blocks (pad selectedRecord186.preimage) = parts186 ∧
    parts186.flatten = pad selectedRecord186.preimage ∧
    (pad selectedRecord186.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_186 : CompressionChain initial parts186 after524 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_519 (CompressionChain.cons block_step_524 (CompressionChain.nil after524))))))

theorem digest_checked_186 : digestHex after524 = selectedRecord186.digest := by decide +kernel

theorem hash_checked_186 : HashEvaluated selectedRecord186 :=
  sha256_of_chain input_checked_186 partition_checked_186.1
    chain_checked_186 digest_checked_186

noncomputable def selectedRecord187 : Phase17Preimages.HashRecord := (Phase17Preimages.record18.ties.getD 0 { json := [], preimage := [], digest := "" })
noncomputable def parts187 : List Block := [block11, block415, block416, block525, block526]
theorem input_checked_187 : InputValid selectedRecord187.preimage := by decide +kernel

theorem partition_checked_187 :
    blocks (pad selectedRecord187.preimage) = parts187 ∧
    parts187.flatten = pad selectedRecord187.preimage ∧
    (pad selectedRecord187.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_187 : CompressionChain initial parts187 after526 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_525 (CompressionChain.cons block_step_526 (CompressionChain.nil after526))))))

theorem digest_checked_187 : digestHex after526 = selectedRecord187.digest := by decide +kernel

theorem hash_checked_187 : HashEvaluated selectedRecord187 :=
  sha256_of_chain input_checked_187 partition_checked_187.1
    chain_checked_187 digest_checked_187

noncomputable def selectedRecord188 : Phase17Preimages.HashRecord := (Phase17Preimages.record18.ties.getD 1 { json := [], preimage := [], digest := "" })
noncomputable def parts188 : List Block := [block11, block415, block416, block525, block527]
theorem input_checked_188 : InputValid selectedRecord188.preimage := by decide +kernel

theorem partition_checked_188 :
    blocks (pad selectedRecord188.preimage) = parts188 ∧
    parts188.flatten = pad selectedRecord188.preimage ∧
    (pad selectedRecord188.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_188 : CompressionChain initial parts188 after527 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_525 (CompressionChain.cons block_step_527 (CompressionChain.nil after527))))))

theorem digest_checked_188 : digestHex after527 = selectedRecord188.digest := by decide +kernel

theorem hash_checked_188 : HashEvaluated selectedRecord188 :=
  sha256_of_chain input_checked_188 partition_checked_188.1
    chain_checked_188 digest_checked_188

noncomputable def selectedRecord189 : Phase17Preimages.HashRecord := (Phase17Preimages.record18.ties.getD 2 { json := [], preimage := [], digest := "" })
noncomputable def parts189 : List Block := [block11, block415, block416, block525, block528]
theorem input_checked_189 : InputValid selectedRecord189.preimage := by decide +kernel

theorem partition_checked_189 :
    blocks (pad selectedRecord189.preimage) = parts189 ∧
    parts189.flatten = pad selectedRecord189.preimage ∧
    (pad selectedRecord189.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_189 : CompressionChain initial parts189 after528 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_525 (CompressionChain.cons block_step_528 (CompressionChain.nil after528))))))

theorem digest_checked_189 : digestHex after528 = selectedRecord189.digest := by decide +kernel

theorem hash_checked_189 : HashEvaluated selectedRecord189 :=
  sha256_of_chain input_checked_189 partition_checked_189.1
    chain_checked_189 digest_checked_189

noncomputable def selectedRecord190 : Phase17Preimages.HashRecord := (Phase17Preimages.record18.ties.getD 3 { json := [], preimage := [], digest := "" })
noncomputable def parts190 : List Block := [block11, block415, block416, block525, block529]
theorem input_checked_190 : InputValid selectedRecord190.preimage := by decide +kernel

theorem partition_checked_190 :
    blocks (pad selectedRecord190.preimage) = parts190 ∧
    parts190.flatten = pad selectedRecord190.preimage ∧
    (pad selectedRecord190.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_190 : CompressionChain initial parts190 after529 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_525 (CompressionChain.cons block_step_529 (CompressionChain.nil after529))))))

theorem digest_checked_190 : digestHex after529 = selectedRecord190.digest := by decide +kernel

theorem hash_checked_190 : HashEvaluated selectedRecord190 :=
  sha256_of_chain input_checked_190 partition_checked_190.1
    chain_checked_190 digest_checked_190

noncomputable def selectedRecord191 : Phase17Preimages.HashRecord := (Phase17Preimages.record18.ties.getD 4 { json := [], preimage := [], digest := "" })
noncomputable def parts191 : List Block := [block11, block415, block416, block525, block530]
theorem input_checked_191 : InputValid selectedRecord191.preimage := by decide +kernel

theorem partition_checked_191 :
    blocks (pad selectedRecord191.preimage) = parts191 ∧
    parts191.flatten = pad selectedRecord191.preimage ∧
    (pad selectedRecord191.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_191 : CompressionChain initial parts191 after530 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_525 (CompressionChain.cons block_step_530 (CompressionChain.nil after530))))))

theorem digest_checked_191 : digestHex after530 = selectedRecord191.digest := by decide +kernel

theorem hash_checked_191 : HashEvaluated selectedRecord191 :=
  sha256_of_chain input_checked_191 partition_checked_191.1
    chain_checked_191 digest_checked_191

noncomputable def selectedRecord192 : Phase17Preimages.HashRecord := (Phase17Preimages.record19.ties.getD 0 { json := [], preimage := [], digest := "" })
noncomputable def parts192 : List Block := [block11, block415, block416, block531, block532]
theorem input_checked_192 : InputValid selectedRecord192.preimage := by decide +kernel

theorem partition_checked_192 :
    blocks (pad selectedRecord192.preimage) = parts192 ∧
    parts192.flatten = pad selectedRecord192.preimage ∧
    (pad selectedRecord192.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_192 : CompressionChain initial parts192 after532 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_531 (CompressionChain.cons block_step_532 (CompressionChain.nil after532))))))

theorem digest_checked_192 : digestHex after532 = selectedRecord192.digest := by decide +kernel

theorem hash_checked_192 : HashEvaluated selectedRecord192 :=
  sha256_of_chain input_checked_192 partition_checked_192.1
    chain_checked_192 digest_checked_192

noncomputable def selectedRecord193 : Phase17Preimages.HashRecord := (Phase17Preimages.record19.ties.getD 1 { json := [], preimage := [], digest := "" })
noncomputable def parts193 : List Block := [block11, block415, block416, block531, block533]
theorem input_checked_193 : InputValid selectedRecord193.preimage := by decide +kernel

theorem partition_checked_193 :
    blocks (pad selectedRecord193.preimage) = parts193 ∧
    parts193.flatten = pad selectedRecord193.preimage ∧
    (pad selectedRecord193.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_193 : CompressionChain initial parts193 after533 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_531 (CompressionChain.cons block_step_533 (CompressionChain.nil after533))))))

theorem digest_checked_193 : digestHex after533 = selectedRecord193.digest := by decide +kernel

theorem hash_checked_193 : HashEvaluated selectedRecord193 :=
  sha256_of_chain input_checked_193 partition_checked_193.1
    chain_checked_193 digest_checked_193

noncomputable def selectedRecord194 : Phase17Preimages.HashRecord := (Phase17Preimages.record19.ties.getD 2 { json := [], preimage := [], digest := "" })
noncomputable def parts194 : List Block := [block11, block415, block416, block531, block534]
theorem input_checked_194 : InputValid selectedRecord194.preimage := by decide +kernel

theorem partition_checked_194 :
    blocks (pad selectedRecord194.preimage) = parts194 ∧
    parts194.flatten = pad selectedRecord194.preimage ∧
    (pad selectedRecord194.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_194 : CompressionChain initial parts194 after534 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_531 (CompressionChain.cons block_step_534 (CompressionChain.nil after534))))))

theorem digest_checked_194 : digestHex after534 = selectedRecord194.digest := by decide +kernel

theorem hash_checked_194 : HashEvaluated selectedRecord194 :=
  sha256_of_chain input_checked_194 partition_checked_194.1
    chain_checked_194 digest_checked_194

noncomputable def selectedRecord195 : Phase17Preimages.HashRecord := (Phase17Preimages.record19.ties.getD 3 { json := [], preimage := [], digest := "" })
noncomputable def parts195 : List Block := [block11, block415, block416, block531, block535]
theorem input_checked_195 : InputValid selectedRecord195.preimage := by decide +kernel

theorem partition_checked_195 :
    blocks (pad selectedRecord195.preimage) = parts195 ∧
    parts195.flatten = pad selectedRecord195.preimage ∧
    (pad selectedRecord195.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_195 : CompressionChain initial parts195 after535 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_531 (CompressionChain.cons block_step_535 (CompressionChain.nil after535))))))

theorem digest_checked_195 : digestHex after535 = selectedRecord195.digest := by decide +kernel

theorem hash_checked_195 : HashEvaluated selectedRecord195 :=
  sha256_of_chain input_checked_195 partition_checked_195.1
    chain_checked_195 digest_checked_195

noncomputable def selectedRecord196 : Phase17Preimages.HashRecord := (Phase17Preimages.record19.ties.getD 4 { json := [], preimage := [], digest := "" })
noncomputable def parts196 : List Block := [block11, block415, block416, block531, block536]
theorem input_checked_196 : InputValid selectedRecord196.preimage := by decide +kernel

theorem partition_checked_196 :
    blocks (pad selectedRecord196.preimage) = parts196 ∧
    parts196.flatten = pad selectedRecord196.preimage ∧
    (pad selectedRecord196.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_196 : CompressionChain initial parts196 after536 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_531 (CompressionChain.cons block_step_536 (CompressionChain.nil after536))))))

theorem digest_checked_196 : digestHex after536 = selectedRecord196.digest := by decide +kernel

theorem hash_checked_196 : HashEvaluated selectedRecord196 :=
  sha256_of_chain input_checked_196 partition_checked_196.1
    chain_checked_196 digest_checked_196

noncomputable def selectedRecord197 : Phase17Preimages.HashRecord := (Phase17Preimages.record20.ties.getD 0 { json := [], preimage := [], digest := "" })
noncomputable def parts197 : List Block := [block11, block415, block416, block537, block538]
theorem input_checked_197 : InputValid selectedRecord197.preimage := by decide +kernel

theorem partition_checked_197 :
    blocks (pad selectedRecord197.preimage) = parts197 ∧
    parts197.flatten = pad selectedRecord197.preimage ∧
    (pad selectedRecord197.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_197 : CompressionChain initial parts197 after538 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_537 (CompressionChain.cons block_step_538 (CompressionChain.nil after538))))))

theorem digest_checked_197 : digestHex after538 = selectedRecord197.digest := by decide +kernel

theorem hash_checked_197 : HashEvaluated selectedRecord197 :=
  sha256_of_chain input_checked_197 partition_checked_197.1
    chain_checked_197 digest_checked_197

noncomputable def selectedRecord198 : Phase17Preimages.HashRecord := (Phase17Preimages.record20.ties.getD 1 { json := [], preimage := [], digest := "" })
noncomputable def parts198 : List Block := [block11, block415, block416, block537, block539]
theorem input_checked_198 : InputValid selectedRecord198.preimage := by decide +kernel

theorem partition_checked_198 :
    blocks (pad selectedRecord198.preimage) = parts198 ∧
    parts198.flatten = pad selectedRecord198.preimage ∧
    (pad selectedRecord198.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_198 : CompressionChain initial parts198 after539 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_537 (CompressionChain.cons block_step_539 (CompressionChain.nil after539))))))

theorem digest_checked_198 : digestHex after539 = selectedRecord198.digest := by decide +kernel

theorem hash_checked_198 : HashEvaluated selectedRecord198 :=
  sha256_of_chain input_checked_198 partition_checked_198.1
    chain_checked_198 digest_checked_198

noncomputable def selectedRecord199 : Phase17Preimages.HashRecord := (Phase17Preimages.record20.ties.getD 2 { json := [], preimage := [], digest := "" })
noncomputable def parts199 : List Block := [block11, block415, block416, block537, block540]
theorem input_checked_199 : InputValid selectedRecord199.preimage := by decide +kernel

theorem partition_checked_199 :
    blocks (pad selectedRecord199.preimage) = parts199 ∧
    parts199.flatten = pad selectedRecord199.preimage ∧
    (pad selectedRecord199.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_199 : CompressionChain initial parts199 after540 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_537 (CompressionChain.cons block_step_540 (CompressionChain.nil after540))))))

theorem digest_checked_199 : digestHex after540 = selectedRecord199.digest := by decide +kernel

theorem hash_checked_199 : HashEvaluated selectedRecord199 :=
  sha256_of_chain input_checked_199 partition_checked_199.1
    chain_checked_199 digest_checked_199

noncomputable def selectedRecord200 : Phase17Preimages.HashRecord := (Phase17Preimages.record20.ties.getD 3 { json := [], preimage := [], digest := "" })
noncomputable def parts200 : List Block := [block11, block415, block416, block537, block541]
theorem input_checked_200 : InputValid selectedRecord200.preimage := by decide +kernel

theorem partition_checked_200 :
    blocks (pad selectedRecord200.preimage) = parts200 ∧
    parts200.flatten = pad selectedRecord200.preimage ∧
    (pad selectedRecord200.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_200 : CompressionChain initial parts200 after541 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_537 (CompressionChain.cons block_step_541 (CompressionChain.nil after541))))))

theorem digest_checked_200 : digestHex after541 = selectedRecord200.digest := by decide +kernel

theorem hash_checked_200 : HashEvaluated selectedRecord200 :=
  sha256_of_chain input_checked_200 partition_checked_200.1
    chain_checked_200 digest_checked_200

noncomputable def selectedRecord201 : Phase17Preimages.HashRecord := (Phase17Preimages.record20.ties.getD 4 { json := [], preimage := [], digest := "" })
noncomputable def parts201 : List Block := [block11, block415, block416, block537, block542]
theorem input_checked_201 : InputValid selectedRecord201.preimage := by decide +kernel

theorem partition_checked_201 :
    blocks (pad selectedRecord201.preimage) = parts201 ∧
    parts201.flatten = pad selectedRecord201.preimage ∧
    (pad selectedRecord201.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_201 : CompressionChain initial parts201 after542 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_537 (CompressionChain.cons block_step_542 (CompressionChain.nil after542))))))

theorem digest_checked_201 : digestHex after542 = selectedRecord201.digest := by decide +kernel

theorem hash_checked_201 : HashEvaluated selectedRecord201 :=
  sha256_of_chain input_checked_201 partition_checked_201.1
    chain_checked_201 digest_checked_201

noncomputable def selectedRecord202 : Phase17Preimages.HashRecord := (Phase17Preimages.record21.ties.getD 0 { json := [], preimage := [], digest := "" })
noncomputable def parts202 : List Block := [block11, block415, block416, block543, block544]
theorem input_checked_202 : InputValid selectedRecord202.preimage := by decide +kernel

theorem partition_checked_202 :
    blocks (pad selectedRecord202.preimage) = parts202 ∧
    parts202.flatten = pad selectedRecord202.preimage ∧
    (pad selectedRecord202.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_202 : CompressionChain initial parts202 after544 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_543 (CompressionChain.cons block_step_544 (CompressionChain.nil after544))))))

theorem digest_checked_202 : digestHex after544 = selectedRecord202.digest := by decide +kernel

theorem hash_checked_202 : HashEvaluated selectedRecord202 :=
  sha256_of_chain input_checked_202 partition_checked_202.1
    chain_checked_202 digest_checked_202

noncomputable def selectedRecord203 : Phase17Preimages.HashRecord := (Phase17Preimages.record21.ties.getD 1 { json := [], preimage := [], digest := "" })
noncomputable def parts203 : List Block := [block11, block415, block416, block543, block545]
theorem input_checked_203 : InputValid selectedRecord203.preimage := by decide +kernel

theorem partition_checked_203 :
    blocks (pad selectedRecord203.preimage) = parts203 ∧
    parts203.flatten = pad selectedRecord203.preimage ∧
    (pad selectedRecord203.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_203 : CompressionChain initial parts203 after545 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_543 (CompressionChain.cons block_step_545 (CompressionChain.nil after545))))))

theorem digest_checked_203 : digestHex after545 = selectedRecord203.digest := by decide +kernel

theorem hash_checked_203 : HashEvaluated selectedRecord203 :=
  sha256_of_chain input_checked_203 partition_checked_203.1
    chain_checked_203 digest_checked_203

noncomputable def selectedRecord204 : Phase17Preimages.HashRecord := (Phase17Preimages.record21.ties.getD 2 { json := [], preimage := [], digest := "" })
noncomputable def parts204 : List Block := [block11, block415, block416, block543, block546]
theorem input_checked_204 : InputValid selectedRecord204.preimage := by decide +kernel

theorem partition_checked_204 :
    blocks (pad selectedRecord204.preimage) = parts204 ∧
    parts204.flatten = pad selectedRecord204.preimage ∧
    (pad selectedRecord204.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_204 : CompressionChain initial parts204 after546 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_543 (CompressionChain.cons block_step_546 (CompressionChain.nil after546))))))

theorem digest_checked_204 : digestHex after546 = selectedRecord204.digest := by decide +kernel

theorem hash_checked_204 : HashEvaluated selectedRecord204 :=
  sha256_of_chain input_checked_204 partition_checked_204.1
    chain_checked_204 digest_checked_204

noncomputable def selectedRecord205 : Phase17Preimages.HashRecord := (Phase17Preimages.record21.ties.getD 3 { json := [], preimage := [], digest := "" })
noncomputable def parts205 : List Block := [block11, block415, block416, block543, block547]
theorem input_checked_205 : InputValid selectedRecord205.preimage := by decide +kernel

theorem partition_checked_205 :
    blocks (pad selectedRecord205.preimage) = parts205 ∧
    parts205.flatten = pad selectedRecord205.preimage ∧
    (pad selectedRecord205.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_205 : CompressionChain initial parts205 after547 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_543 (CompressionChain.cons block_step_547 (CompressionChain.nil after547))))))

theorem digest_checked_205 : digestHex after547 = selectedRecord205.digest := by decide +kernel

theorem hash_checked_205 : HashEvaluated selectedRecord205 :=
  sha256_of_chain input_checked_205 partition_checked_205.1
    chain_checked_205 digest_checked_205

noncomputable def selectedRecord206 : Phase17Preimages.HashRecord := (Phase17Preimages.record21.ties.getD 4 { json := [], preimage := [], digest := "" })
noncomputable def parts206 : List Block := [block11, block415, block416, block543, block548]
theorem input_checked_206 : InputValid selectedRecord206.preimage := by decide +kernel

theorem partition_checked_206 :
    blocks (pad selectedRecord206.preimage) = parts206 ∧
    parts206.flatten = pad selectedRecord206.preimage ∧
    (pad selectedRecord206.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_206 : CompressionChain initial parts206 after548 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_543 (CompressionChain.cons block_step_548 (CompressionChain.nil after548))))))

theorem digest_checked_206 : digestHex after548 = selectedRecord206.digest := by decide +kernel

theorem hash_checked_206 : HashEvaluated selectedRecord206 :=
  sha256_of_chain input_checked_206 partition_checked_206.1
    chain_checked_206 digest_checked_206

noncomputable def selectedRecord207 : Phase17Preimages.HashRecord := (Phase17Preimages.record22.ties.getD 0 { json := [], preimage := [], digest := "" })
noncomputable def parts207 : List Block := [block11, block415, block416, block549, block550]
theorem input_checked_207 : InputValid selectedRecord207.preimage := by decide +kernel

theorem partition_checked_207 :
    blocks (pad selectedRecord207.preimage) = parts207 ∧
    parts207.flatten = pad selectedRecord207.preimage ∧
    (pad selectedRecord207.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_207 : CompressionChain initial parts207 after550 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_549 (CompressionChain.cons block_step_550 (CompressionChain.nil after550))))))

theorem digest_checked_207 : digestHex after550 = selectedRecord207.digest := by decide +kernel

theorem hash_checked_207 : HashEvaluated selectedRecord207 :=
  sha256_of_chain input_checked_207 partition_checked_207.1
    chain_checked_207 digest_checked_207

noncomputable def selectedRecord208 : Phase17Preimages.HashRecord := (Phase17Preimages.record22.ties.getD 1 { json := [], preimage := [], digest := "" })
noncomputable def parts208 : List Block := [block11, block415, block416, block549, block551]
theorem input_checked_208 : InputValid selectedRecord208.preimage := by decide +kernel

theorem partition_checked_208 :
    blocks (pad selectedRecord208.preimage) = parts208 ∧
    parts208.flatten = pad selectedRecord208.preimage ∧
    (pad selectedRecord208.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_208 : CompressionChain initial parts208 after551 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_549 (CompressionChain.cons block_step_551 (CompressionChain.nil after551))))))

theorem digest_checked_208 : digestHex after551 = selectedRecord208.digest := by decide +kernel

theorem hash_checked_208 : HashEvaluated selectedRecord208 :=
  sha256_of_chain input_checked_208 partition_checked_208.1
    chain_checked_208 digest_checked_208

noncomputable def selectedRecord209 : Phase17Preimages.HashRecord := (Phase17Preimages.record22.ties.getD 2 { json := [], preimage := [], digest := "" })
noncomputable def parts209 : List Block := [block11, block415, block416, block549, block552]
theorem input_checked_209 : InputValid selectedRecord209.preimage := by decide +kernel

theorem partition_checked_209 :
    blocks (pad selectedRecord209.preimage) = parts209 ∧
    parts209.flatten = pad selectedRecord209.preimage ∧
    (pad selectedRecord209.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_209 : CompressionChain initial parts209 after552 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_549 (CompressionChain.cons block_step_552 (CompressionChain.nil after552))))))

theorem digest_checked_209 : digestHex after552 = selectedRecord209.digest := by decide +kernel

theorem hash_checked_209 : HashEvaluated selectedRecord209 :=
  sha256_of_chain input_checked_209 partition_checked_209.1
    chain_checked_209 digest_checked_209

noncomputable def selectedRecord210 : Phase17Preimages.HashRecord := (Phase17Preimages.record22.ties.getD 3 { json := [], preimage := [], digest := "" })
noncomputable def parts210 : List Block := [block11, block415, block416, block549, block553]
theorem input_checked_210 : InputValid selectedRecord210.preimage := by decide +kernel

theorem partition_checked_210 :
    blocks (pad selectedRecord210.preimage) = parts210 ∧
    parts210.flatten = pad selectedRecord210.preimage ∧
    (pad selectedRecord210.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_210 : CompressionChain initial parts210 after553 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_549 (CompressionChain.cons block_step_553 (CompressionChain.nil after553))))))

theorem digest_checked_210 : digestHex after553 = selectedRecord210.digest := by decide +kernel

theorem hash_checked_210 : HashEvaluated selectedRecord210 :=
  sha256_of_chain input_checked_210 partition_checked_210.1
    chain_checked_210 digest_checked_210

noncomputable def selectedRecord211 : Phase17Preimages.HashRecord := (Phase17Preimages.record22.ties.getD 4 { json := [], preimage := [], digest := "" })
noncomputable def parts211 : List Block := [block11, block415, block416, block549, block554]
theorem input_checked_211 : InputValid selectedRecord211.preimage := by decide +kernel

theorem partition_checked_211 :
    blocks (pad selectedRecord211.preimage) = parts211 ∧
    parts211.flatten = pad selectedRecord211.preimage ∧
    (pad selectedRecord211.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_211 : CompressionChain initial parts211 after554 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_549 (CompressionChain.cons block_step_554 (CompressionChain.nil after554))))))

theorem digest_checked_211 : digestHex after554 = selectedRecord211.digest := by decide +kernel

theorem hash_checked_211 : HashEvaluated selectedRecord211 :=
  sha256_of_chain input_checked_211 partition_checked_211.1
    chain_checked_211 digest_checked_211

noncomputable def selectedRecord212 : Phase17Preimages.HashRecord := (Phase17Preimages.record23.ties.getD 0 { json := [], preimage := [], digest := "" })
noncomputable def parts212 : List Block := [block11, block415, block416, block555, block556]
theorem input_checked_212 : InputValid selectedRecord212.preimage := by decide +kernel

theorem partition_checked_212 :
    blocks (pad selectedRecord212.preimage) = parts212 ∧
    parts212.flatten = pad selectedRecord212.preimage ∧
    (pad selectedRecord212.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_212 : CompressionChain initial parts212 after556 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_555 (CompressionChain.cons block_step_556 (CompressionChain.nil after556))))))

theorem digest_checked_212 : digestHex after556 = selectedRecord212.digest := by decide +kernel

theorem hash_checked_212 : HashEvaluated selectedRecord212 :=
  sha256_of_chain input_checked_212 partition_checked_212.1
    chain_checked_212 digest_checked_212

noncomputable def selectedRecord213 : Phase17Preimages.HashRecord := (Phase17Preimages.record23.ties.getD 1 { json := [], preimage := [], digest := "" })
noncomputable def parts213 : List Block := [block11, block415, block416, block555, block557]
theorem input_checked_213 : InputValid selectedRecord213.preimage := by decide +kernel

theorem partition_checked_213 :
    blocks (pad selectedRecord213.preimage) = parts213 ∧
    parts213.flatten = pad selectedRecord213.preimage ∧
    (pad selectedRecord213.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_213 : CompressionChain initial parts213 after557 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_555 (CompressionChain.cons block_step_557 (CompressionChain.nil after557))))))

theorem digest_checked_213 : digestHex after557 = selectedRecord213.digest := by decide +kernel

theorem hash_checked_213 : HashEvaluated selectedRecord213 :=
  sha256_of_chain input_checked_213 partition_checked_213.1
    chain_checked_213 digest_checked_213

noncomputable def selectedRecord214 : Phase17Preimages.HashRecord := (Phase17Preimages.record23.ties.getD 2 { json := [], preimage := [], digest := "" })
noncomputable def parts214 : List Block := [block11, block415, block416, block555, block558]
theorem input_checked_214 : InputValid selectedRecord214.preimage := by decide +kernel

theorem partition_checked_214 :
    blocks (pad selectedRecord214.preimage) = parts214 ∧
    parts214.flatten = pad selectedRecord214.preimage ∧
    (pad selectedRecord214.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_214 : CompressionChain initial parts214 after558 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_555 (CompressionChain.cons block_step_558 (CompressionChain.nil after558))))))

theorem digest_checked_214 : digestHex after558 = selectedRecord214.digest := by decide +kernel

theorem hash_checked_214 : HashEvaluated selectedRecord214 :=
  sha256_of_chain input_checked_214 partition_checked_214.1
    chain_checked_214 digest_checked_214

noncomputable def selectedRecord215 : Phase17Preimages.HashRecord := (Phase17Preimages.record23.ties.getD 3 { json := [], preimage := [], digest := "" })
noncomputable def parts215 : List Block := [block11, block415, block416, block555, block559]
theorem input_checked_215 : InputValid selectedRecord215.preimage := by decide +kernel

theorem partition_checked_215 :
    blocks (pad selectedRecord215.preimage) = parts215 ∧
    parts215.flatten = pad selectedRecord215.preimage ∧
    (pad selectedRecord215.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_215 : CompressionChain initial parts215 after559 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_555 (CompressionChain.cons block_step_559 (CompressionChain.nil after559))))))

theorem digest_checked_215 : digestHex after559 = selectedRecord215.digest := by decide +kernel

theorem hash_checked_215 : HashEvaluated selectedRecord215 :=
  sha256_of_chain input_checked_215 partition_checked_215.1
    chain_checked_215 digest_checked_215

noncomputable def selectedRecord216 : Phase17Preimages.HashRecord := (Phase17Preimages.record23.ties.getD 4 { json := [], preimage := [], digest := "" })
noncomputable def parts216 : List Block := [block11, block415, block416, block555, block560]
theorem input_checked_216 : InputValid selectedRecord216.preimage := by decide +kernel

theorem partition_checked_216 :
    blocks (pad selectedRecord216.preimage) = parts216 ∧
    parts216.flatten = pad selectedRecord216.preimage ∧
    (pad selectedRecord216.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_216 : CompressionChain initial parts216 after560 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_555 (CompressionChain.cons block_step_560 (CompressionChain.nil after560))))))

theorem digest_checked_216 : digestHex after560 = selectedRecord216.digest := by decide +kernel

theorem hash_checked_216 : HashEvaluated selectedRecord216 :=
  sha256_of_chain input_checked_216 partition_checked_216.1
    chain_checked_216 digest_checked_216

noncomputable def selectedRecord217 : Phase17Preimages.HashRecord := (Phase17Preimages.record24.ties.getD 0 { json := [], preimage := [], digest := "" })
noncomputable def parts217 : List Block := [block11, block415, block416, block561, block562]
theorem input_checked_217 : InputValid selectedRecord217.preimage := by decide +kernel

theorem partition_checked_217 :
    blocks (pad selectedRecord217.preimage) = parts217 ∧
    parts217.flatten = pad selectedRecord217.preimage ∧
    (pad selectedRecord217.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_217 : CompressionChain initial parts217 after562 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_561 (CompressionChain.cons block_step_562 (CompressionChain.nil after562))))))

theorem digest_checked_217 : digestHex after562 = selectedRecord217.digest := by decide +kernel

theorem hash_checked_217 : HashEvaluated selectedRecord217 :=
  sha256_of_chain input_checked_217 partition_checked_217.1
    chain_checked_217 digest_checked_217

noncomputable def selectedRecord218 : Phase17Preimages.HashRecord := (Phase17Preimages.record24.ties.getD 1 { json := [], preimage := [], digest := "" })
noncomputable def parts218 : List Block := [block11, block415, block416, block561, block563]
theorem input_checked_218 : InputValid selectedRecord218.preimage := by decide +kernel

theorem partition_checked_218 :
    blocks (pad selectedRecord218.preimage) = parts218 ∧
    parts218.flatten = pad selectedRecord218.preimage ∧
    (pad selectedRecord218.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_218 : CompressionChain initial parts218 after563 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_561 (CompressionChain.cons block_step_563 (CompressionChain.nil after563))))))

theorem digest_checked_218 : digestHex after563 = selectedRecord218.digest := by decide +kernel

theorem hash_checked_218 : HashEvaluated selectedRecord218 :=
  sha256_of_chain input_checked_218 partition_checked_218.1
    chain_checked_218 digest_checked_218

noncomputable def selectedRecord219 : Phase17Preimages.HashRecord := (Phase17Preimages.record24.ties.getD 2 { json := [], preimage := [], digest := "" })
noncomputable def parts219 : List Block := [block11, block415, block416, block561, block564]
theorem input_checked_219 : InputValid selectedRecord219.preimage := by decide +kernel

theorem partition_checked_219 :
    blocks (pad selectedRecord219.preimage) = parts219 ∧
    parts219.flatten = pad selectedRecord219.preimage ∧
    (pad selectedRecord219.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_219 : CompressionChain initial parts219 after564 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_561 (CompressionChain.cons block_step_564 (CompressionChain.nil after564))))))

theorem digest_checked_219 : digestHex after564 = selectedRecord219.digest := by decide +kernel

theorem hash_checked_219 : HashEvaluated selectedRecord219 :=
  sha256_of_chain input_checked_219 partition_checked_219.1
    chain_checked_219 digest_checked_219

noncomputable def selectedRecord220 : Phase17Preimages.HashRecord := (Phase17Preimages.record24.ties.getD 3 { json := [], preimage := [], digest := "" })
noncomputable def parts220 : List Block := [block11, block415, block416, block561, block565]
theorem input_checked_220 : InputValid selectedRecord220.preimage := by decide +kernel

theorem partition_checked_220 :
    blocks (pad selectedRecord220.preimage) = parts220 ∧
    parts220.flatten = pad selectedRecord220.preimage ∧
    (pad selectedRecord220.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_220 : CompressionChain initial parts220 after565 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_561 (CompressionChain.cons block_step_565 (CompressionChain.nil after565))))))

theorem digest_checked_220 : digestHex after565 = selectedRecord220.digest := by decide +kernel

theorem hash_checked_220 : HashEvaluated selectedRecord220 :=
  sha256_of_chain input_checked_220 partition_checked_220.1
    chain_checked_220 digest_checked_220

noncomputable def selectedRecord221 : Phase17Preimages.HashRecord := (Phase17Preimages.record24.ties.getD 4 { json := [], preimage := [], digest := "" })
noncomputable def parts221 : List Block := [block11, block415, block416, block561, block566]
theorem input_checked_221 : InputValid selectedRecord221.preimage := by decide +kernel

theorem partition_checked_221 :
    blocks (pad selectedRecord221.preimage) = parts221 ∧
    parts221.flatten = pad selectedRecord221.preimage ∧
    (pad selectedRecord221.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_221 : CompressionChain initial parts221 after566 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_561 (CompressionChain.cons block_step_566 (CompressionChain.nil after566))))))

theorem digest_checked_221 : digestHex after566 = selectedRecord221.digest := by decide +kernel

theorem hash_checked_221 : HashEvaluated selectedRecord221 :=
  sha256_of_chain input_checked_221 partition_checked_221.1
    chain_checked_221 digest_checked_221

noncomputable def selectedRecord222 : Phase17Preimages.HashRecord := (Phase17Preimages.record25.ties.getD 0 { json := [], preimage := [], digest := "" })
noncomputable def parts222 : List Block := [block11, block415, block416, block567, block568]
theorem input_checked_222 : InputValid selectedRecord222.preimage := by decide +kernel

theorem partition_checked_222 :
    blocks (pad selectedRecord222.preimage) = parts222 ∧
    parts222.flatten = pad selectedRecord222.preimage ∧
    (pad selectedRecord222.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_222 : CompressionChain initial parts222 after568 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_567 (CompressionChain.cons block_step_568 (CompressionChain.nil after568))))))

theorem digest_checked_222 : digestHex after568 = selectedRecord222.digest := by decide +kernel

theorem hash_checked_222 : HashEvaluated selectedRecord222 :=
  sha256_of_chain input_checked_222 partition_checked_222.1
    chain_checked_222 digest_checked_222

noncomputable def selectedRecord223 : Phase17Preimages.HashRecord := (Phase17Preimages.record25.ties.getD 1 { json := [], preimage := [], digest := "" })
noncomputable def parts223 : List Block := [block11, block415, block416, block567, block569]
theorem input_checked_223 : InputValid selectedRecord223.preimage := by decide +kernel

theorem partition_checked_223 :
    blocks (pad selectedRecord223.preimage) = parts223 ∧
    parts223.flatten = pad selectedRecord223.preimage ∧
    (pad selectedRecord223.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_223 : CompressionChain initial parts223 after569 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_567 (CompressionChain.cons block_step_569 (CompressionChain.nil after569))))))

theorem digest_checked_223 : digestHex after569 = selectedRecord223.digest := by decide +kernel

theorem hash_checked_223 : HashEvaluated selectedRecord223 :=
  sha256_of_chain input_checked_223 partition_checked_223.1
    chain_checked_223 digest_checked_223

noncomputable def selectedRecord224 : Phase17Preimages.HashRecord := (Phase17Preimages.record25.ties.getD 2 { json := [], preimage := [], digest := "" })
noncomputable def parts224 : List Block := [block11, block415, block416, block567, block570]
theorem input_checked_224 : InputValid selectedRecord224.preimage := by decide +kernel

theorem partition_checked_224 :
    blocks (pad selectedRecord224.preimage) = parts224 ∧
    parts224.flatten = pad selectedRecord224.preimage ∧
    (pad selectedRecord224.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_224 : CompressionChain initial parts224 after570 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_567 (CompressionChain.cons block_step_570 (CompressionChain.nil after570))))))

theorem digest_checked_224 : digestHex after570 = selectedRecord224.digest := by decide +kernel

theorem hash_checked_224 : HashEvaluated selectedRecord224 :=
  sha256_of_chain input_checked_224 partition_checked_224.1
    chain_checked_224 digest_checked_224

noncomputable def selectedRecord225 : Phase17Preimages.HashRecord := (Phase17Preimages.record25.ties.getD 3 { json := [], preimage := [], digest := "" })
noncomputable def parts225 : List Block := [block11, block415, block416, block567, block571]
theorem input_checked_225 : InputValid selectedRecord225.preimage := by decide +kernel

theorem partition_checked_225 :
    blocks (pad selectedRecord225.preimage) = parts225 ∧
    parts225.flatten = pad selectedRecord225.preimage ∧
    (pad selectedRecord225.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_225 : CompressionChain initial parts225 after571 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_567 (CompressionChain.cons block_step_571 (CompressionChain.nil after571))))))

theorem digest_checked_225 : digestHex after571 = selectedRecord225.digest := by decide +kernel

theorem hash_checked_225 : HashEvaluated selectedRecord225 :=
  sha256_of_chain input_checked_225 partition_checked_225.1
    chain_checked_225 digest_checked_225

noncomputable def selectedRecord226 : Phase17Preimages.HashRecord := (Phase17Preimages.record25.ties.getD 4 { json := [], preimage := [], digest := "" })
noncomputable def parts226 : List Block := [block11, block415, block416, block567, block572]
theorem input_checked_226 : InputValid selectedRecord226.preimage := by decide +kernel

theorem partition_checked_226 :
    blocks (pad selectedRecord226.preimage) = parts226 ∧
    parts226.flatten = pad selectedRecord226.preimage ∧
    (pad selectedRecord226.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_226 : CompressionChain initial parts226 after572 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_567 (CompressionChain.cons block_step_572 (CompressionChain.nil after572))))))

theorem digest_checked_226 : digestHex after572 = selectedRecord226.digest := by decide +kernel

theorem hash_checked_226 : HashEvaluated selectedRecord226 :=
  sha256_of_chain input_checked_226 partition_checked_226.1
    chain_checked_226 digest_checked_226

noncomputable def selectedRecord227 : Phase17Preimages.HashRecord := (Phase17Preimages.record26.ties.getD 0 { json := [], preimage := [], digest := "" })
noncomputable def parts227 : List Block := [block11, block415, block416, block573, block574]
theorem input_checked_227 : InputValid selectedRecord227.preimage := by decide +kernel

theorem partition_checked_227 :
    blocks (pad selectedRecord227.preimage) = parts227 ∧
    parts227.flatten = pad selectedRecord227.preimage ∧
    (pad selectedRecord227.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_227 : CompressionChain initial parts227 after574 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_573 (CompressionChain.cons block_step_574 (CompressionChain.nil after574))))))

theorem digest_checked_227 : digestHex after574 = selectedRecord227.digest := by decide +kernel

theorem hash_checked_227 : HashEvaluated selectedRecord227 :=
  sha256_of_chain input_checked_227 partition_checked_227.1
    chain_checked_227 digest_checked_227

noncomputable def selectedRecord228 : Phase17Preimages.HashRecord := (Phase17Preimages.record26.ties.getD 1 { json := [], preimage := [], digest := "" })
noncomputable def parts228 : List Block := [block11, block415, block416, block573, block575]
theorem input_checked_228 : InputValid selectedRecord228.preimage := by decide +kernel

theorem partition_checked_228 :
    blocks (pad selectedRecord228.preimage) = parts228 ∧
    parts228.flatten = pad selectedRecord228.preimage ∧
    (pad selectedRecord228.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_228 : CompressionChain initial parts228 after575 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_573 (CompressionChain.cons block_step_575 (CompressionChain.nil after575))))))

theorem digest_checked_228 : digestHex after575 = selectedRecord228.digest := by decide +kernel

theorem hash_checked_228 : HashEvaluated selectedRecord228 :=
  sha256_of_chain input_checked_228 partition_checked_228.1
    chain_checked_228 digest_checked_228

noncomputable def selectedRecord229 : Phase17Preimages.HashRecord := (Phase17Preimages.record26.ties.getD 2 { json := [], preimage := [], digest := "" })
noncomputable def parts229 : List Block := [block11, block415, block416, block573, block576]
theorem input_checked_229 : InputValid selectedRecord229.preimage := by decide +kernel

theorem partition_checked_229 :
    blocks (pad selectedRecord229.preimage) = parts229 ∧
    parts229.flatten = pad selectedRecord229.preimage ∧
    (pad selectedRecord229.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_229 : CompressionChain initial parts229 after576 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_573 (CompressionChain.cons block_step_576 (CompressionChain.nil after576))))))

theorem digest_checked_229 : digestHex after576 = selectedRecord229.digest := by decide +kernel

theorem hash_checked_229 : HashEvaluated selectedRecord229 :=
  sha256_of_chain input_checked_229 partition_checked_229.1
    chain_checked_229 digest_checked_229

noncomputable def selectedRecord230 : Phase17Preimages.HashRecord := (Phase17Preimages.record26.ties.getD 3 { json := [], preimage := [], digest := "" })
noncomputable def parts230 : List Block := [block11, block415, block416, block573, block577]
theorem input_checked_230 : InputValid selectedRecord230.preimage := by decide +kernel

theorem partition_checked_230 :
    blocks (pad selectedRecord230.preimage) = parts230 ∧
    parts230.flatten = pad selectedRecord230.preimage ∧
    (pad selectedRecord230.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_230 : CompressionChain initial parts230 after577 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_573 (CompressionChain.cons block_step_577 (CompressionChain.nil after577))))))

theorem digest_checked_230 : digestHex after577 = selectedRecord230.digest := by decide +kernel

theorem hash_checked_230 : HashEvaluated selectedRecord230 :=
  sha256_of_chain input_checked_230 partition_checked_230.1
    chain_checked_230 digest_checked_230

noncomputable def selectedRecord231 : Phase17Preimages.HashRecord := (Phase17Preimages.record26.ties.getD 4 { json := [], preimage := [], digest := "" })
noncomputable def parts231 : List Block := [block11, block415, block416, block573, block578]
theorem input_checked_231 : InputValid selectedRecord231.preimage := by decide +kernel

theorem partition_checked_231 :
    blocks (pad selectedRecord231.preimage) = parts231 ∧
    parts231.flatten = pad selectedRecord231.preimage ∧
    (pad selectedRecord231.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_231 : CompressionChain initial parts231 after578 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_573 (CompressionChain.cons block_step_578 (CompressionChain.nil after578))))))

theorem digest_checked_231 : digestHex after578 = selectedRecord231.digest := by decide +kernel

theorem hash_checked_231 : HashEvaluated selectedRecord231 :=
  sha256_of_chain input_checked_231 partition_checked_231.1
    chain_checked_231 digest_checked_231

noncomputable def selectedRecord232 : Phase17Preimages.HashRecord := (Phase17Preimages.record27.ties.getD 0 { json := [], preimage := [], digest := "" })
noncomputable def parts232 : List Block := [block11, block415, block416, block579, block580]
theorem input_checked_232 : InputValid selectedRecord232.preimage := by decide +kernel

theorem partition_checked_232 :
    blocks (pad selectedRecord232.preimage) = parts232 ∧
    parts232.flatten = pad selectedRecord232.preimage ∧
    (pad selectedRecord232.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_232 : CompressionChain initial parts232 after580 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_579 (CompressionChain.cons block_step_580 (CompressionChain.nil after580))))))

theorem digest_checked_232 : digestHex after580 = selectedRecord232.digest := by decide +kernel

theorem hash_checked_232 : HashEvaluated selectedRecord232 :=
  sha256_of_chain input_checked_232 partition_checked_232.1
    chain_checked_232 digest_checked_232

noncomputable def selectedRecord233 : Phase17Preimages.HashRecord := (Phase17Preimages.record27.ties.getD 1 { json := [], preimage := [], digest := "" })
noncomputable def parts233 : List Block := [block11, block415, block416, block579, block581]
theorem input_checked_233 : InputValid selectedRecord233.preimage := by decide +kernel

theorem partition_checked_233 :
    blocks (pad selectedRecord233.preimage) = parts233 ∧
    parts233.flatten = pad selectedRecord233.preimage ∧
    (pad selectedRecord233.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_233 : CompressionChain initial parts233 after581 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_579 (CompressionChain.cons block_step_581 (CompressionChain.nil after581))))))

theorem digest_checked_233 : digestHex after581 = selectedRecord233.digest := by decide +kernel

theorem hash_checked_233 : HashEvaluated selectedRecord233 :=
  sha256_of_chain input_checked_233 partition_checked_233.1
    chain_checked_233 digest_checked_233

noncomputable def selectedRecord234 : Phase17Preimages.HashRecord := (Phase17Preimages.record27.ties.getD 2 { json := [], preimage := [], digest := "" })
noncomputable def parts234 : List Block := [block11, block415, block416, block579, block582]
theorem input_checked_234 : InputValid selectedRecord234.preimage := by decide +kernel

theorem partition_checked_234 :
    blocks (pad selectedRecord234.preimage) = parts234 ∧
    parts234.flatten = pad selectedRecord234.preimage ∧
    (pad selectedRecord234.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_234 : CompressionChain initial parts234 after582 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_579 (CompressionChain.cons block_step_582 (CompressionChain.nil after582))))))

theorem digest_checked_234 : digestHex after582 = selectedRecord234.digest := by decide +kernel

theorem hash_checked_234 : HashEvaluated selectedRecord234 :=
  sha256_of_chain input_checked_234 partition_checked_234.1
    chain_checked_234 digest_checked_234

noncomputable def selectedRecord235 : Phase17Preimages.HashRecord := (Phase17Preimages.record27.ties.getD 3 { json := [], preimage := [], digest := "" })
noncomputable def parts235 : List Block := [block11, block415, block416, block579, block583]
theorem input_checked_235 : InputValid selectedRecord235.preimage := by decide +kernel

theorem partition_checked_235 :
    blocks (pad selectedRecord235.preimage) = parts235 ∧
    parts235.flatten = pad selectedRecord235.preimage ∧
    (pad selectedRecord235.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_235 : CompressionChain initial parts235 after583 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_579 (CompressionChain.cons block_step_583 (CompressionChain.nil after583))))))

theorem digest_checked_235 : digestHex after583 = selectedRecord235.digest := by decide +kernel

theorem hash_checked_235 : HashEvaluated selectedRecord235 :=
  sha256_of_chain input_checked_235 partition_checked_235.1
    chain_checked_235 digest_checked_235

noncomputable def selectedRecord236 : Phase17Preimages.HashRecord := (Phase17Preimages.record27.ties.getD 4 { json := [], preimage := [], digest := "" })
noncomputable def parts236 : List Block := [block11, block415, block416, block579, block584]
theorem input_checked_236 : InputValid selectedRecord236.preimage := by decide +kernel

theorem partition_checked_236 :
    blocks (pad selectedRecord236.preimage) = parts236 ∧
    parts236.flatten = pad selectedRecord236.preimage ∧
    (pad selectedRecord236.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_236 : CompressionChain initial parts236 after584 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_579 (CompressionChain.cons block_step_584 (CompressionChain.nil after584))))))

theorem digest_checked_236 : digestHex after584 = selectedRecord236.digest := by decide +kernel

theorem hash_checked_236 : HashEvaluated selectedRecord236 :=
  sha256_of_chain input_checked_236 partition_checked_236.1
    chain_checked_236 digest_checked_236

noncomputable def selectedRecord237 : Phase17Preimages.HashRecord := (Phase17Preimages.record28.ties.getD 0 { json := [], preimage := [], digest := "" })
noncomputable def parts237 : List Block := [block11, block415, block416, block585, block586]
theorem input_checked_237 : InputValid selectedRecord237.preimage := by decide +kernel

theorem partition_checked_237 :
    blocks (pad selectedRecord237.preimage) = parts237 ∧
    parts237.flatten = pad selectedRecord237.preimage ∧
    (pad selectedRecord237.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_237 : CompressionChain initial parts237 after586 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_585 (CompressionChain.cons block_step_586 (CompressionChain.nil after586))))))

theorem digest_checked_237 : digestHex after586 = selectedRecord237.digest := by decide +kernel

theorem hash_checked_237 : HashEvaluated selectedRecord237 :=
  sha256_of_chain input_checked_237 partition_checked_237.1
    chain_checked_237 digest_checked_237

noncomputable def selectedRecord238 : Phase17Preimages.HashRecord := (Phase17Preimages.record28.ties.getD 1 { json := [], preimage := [], digest := "" })
noncomputable def parts238 : List Block := [block11, block415, block416, block585, block587]
theorem input_checked_238 : InputValid selectedRecord238.preimage := by decide +kernel

theorem partition_checked_238 :
    blocks (pad selectedRecord238.preimage) = parts238 ∧
    parts238.flatten = pad selectedRecord238.preimage ∧
    (pad selectedRecord238.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_238 : CompressionChain initial parts238 after587 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_585 (CompressionChain.cons block_step_587 (CompressionChain.nil after587))))))

theorem digest_checked_238 : digestHex after587 = selectedRecord238.digest := by decide +kernel

theorem hash_checked_238 : HashEvaluated selectedRecord238 :=
  sha256_of_chain input_checked_238 partition_checked_238.1
    chain_checked_238 digest_checked_238

noncomputable def selectedRecord239 : Phase17Preimages.HashRecord := (Phase17Preimages.record28.ties.getD 2 { json := [], preimage := [], digest := "" })
noncomputable def parts239 : List Block := [block11, block415, block416, block585, block588]
theorem input_checked_239 : InputValid selectedRecord239.preimage := by decide +kernel

theorem partition_checked_239 :
    blocks (pad selectedRecord239.preimage) = parts239 ∧
    parts239.flatten = pad selectedRecord239.preimage ∧
    (pad selectedRecord239.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_239 : CompressionChain initial parts239 after588 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_585 (CompressionChain.cons block_step_588 (CompressionChain.nil after588))))))

theorem digest_checked_239 : digestHex after588 = selectedRecord239.digest := by decide +kernel

theorem hash_checked_239 : HashEvaluated selectedRecord239 :=
  sha256_of_chain input_checked_239 partition_checked_239.1
    chain_checked_239 digest_checked_239

noncomputable def selectedRecord240 : Phase17Preimages.HashRecord := (Phase17Preimages.record28.ties.getD 3 { json := [], preimage := [], digest := "" })
noncomputable def parts240 : List Block := [block11, block415, block416, block585, block589]
theorem input_checked_240 : InputValid selectedRecord240.preimage := by decide +kernel

theorem partition_checked_240 :
    blocks (pad selectedRecord240.preimage) = parts240 ∧
    parts240.flatten = pad selectedRecord240.preimage ∧
    (pad selectedRecord240.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_240 : CompressionChain initial parts240 after589 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_585 (CompressionChain.cons block_step_589 (CompressionChain.nil after589))))))

theorem digest_checked_240 : digestHex after589 = selectedRecord240.digest := by decide +kernel

theorem hash_checked_240 : HashEvaluated selectedRecord240 :=
  sha256_of_chain input_checked_240 partition_checked_240.1
    chain_checked_240 digest_checked_240

noncomputable def selectedRecord241 : Phase17Preimages.HashRecord := (Phase17Preimages.record28.ties.getD 4 { json := [], preimage := [], digest := "" })
noncomputable def parts241 : List Block := [block11, block415, block416, block585, block590]
theorem input_checked_241 : InputValid selectedRecord241.preimage := by decide +kernel

theorem partition_checked_241 :
    blocks (pad selectedRecord241.preimage) = parts241 ∧
    parts241.flatten = pad selectedRecord241.preimage ∧
    (pad selectedRecord241.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_241 : CompressionChain initial parts241 after590 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_585 (CompressionChain.cons block_step_590 (CompressionChain.nil after590))))))

theorem digest_checked_241 : digestHex after590 = selectedRecord241.digest := by decide +kernel

theorem hash_checked_241 : HashEvaluated selectedRecord241 :=
  sha256_of_chain input_checked_241 partition_checked_241.1
    chain_checked_241 digest_checked_241

noncomputable def selectedRecord242 : Phase17Preimages.HashRecord := (Phase17Preimages.record29.ties.getD 0 { json := [], preimage := [], digest := "" })
noncomputable def parts242 : List Block := [block11, block415, block416, block591, block592]
theorem input_checked_242 : InputValid selectedRecord242.preimage := by decide +kernel

theorem partition_checked_242 :
    blocks (pad selectedRecord242.preimage) = parts242 ∧
    parts242.flatten = pad selectedRecord242.preimage ∧
    (pad selectedRecord242.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_242 : CompressionChain initial parts242 after592 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_591 (CompressionChain.cons block_step_592 (CompressionChain.nil after592))))))

theorem digest_checked_242 : digestHex after592 = selectedRecord242.digest := by decide +kernel

theorem hash_checked_242 : HashEvaluated selectedRecord242 :=
  sha256_of_chain input_checked_242 partition_checked_242.1
    chain_checked_242 digest_checked_242

noncomputable def selectedRecord243 : Phase17Preimages.HashRecord := (Phase17Preimages.record29.ties.getD 1 { json := [], preimage := [], digest := "" })
noncomputable def parts243 : List Block := [block11, block415, block416, block591, block593]
theorem input_checked_243 : InputValid selectedRecord243.preimage := by decide +kernel

theorem partition_checked_243 :
    blocks (pad selectedRecord243.preimage) = parts243 ∧
    parts243.flatten = pad selectedRecord243.preimage ∧
    (pad selectedRecord243.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_243 : CompressionChain initial parts243 after593 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_591 (CompressionChain.cons block_step_593 (CompressionChain.nil after593))))))

theorem digest_checked_243 : digestHex after593 = selectedRecord243.digest := by decide +kernel

theorem hash_checked_243 : HashEvaluated selectedRecord243 :=
  sha256_of_chain input_checked_243 partition_checked_243.1
    chain_checked_243 digest_checked_243

noncomputable def selectedRecord244 : Phase17Preimages.HashRecord := (Phase17Preimages.record29.ties.getD 2 { json := [], preimage := [], digest := "" })
noncomputable def parts244 : List Block := [block11, block415, block416, block591, block594]
theorem input_checked_244 : InputValid selectedRecord244.preimage := by decide +kernel

theorem partition_checked_244 :
    blocks (pad selectedRecord244.preimage) = parts244 ∧
    parts244.flatten = pad selectedRecord244.preimage ∧
    (pad selectedRecord244.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_244 : CompressionChain initial parts244 after594 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_591 (CompressionChain.cons block_step_594 (CompressionChain.nil after594))))))

theorem digest_checked_244 : digestHex after594 = selectedRecord244.digest := by decide +kernel

theorem hash_checked_244 : HashEvaluated selectedRecord244 :=
  sha256_of_chain input_checked_244 partition_checked_244.1
    chain_checked_244 digest_checked_244

noncomputable def selectedRecord245 : Phase17Preimages.HashRecord := (Phase17Preimages.record29.ties.getD 3 { json := [], preimage := [], digest := "" })
noncomputable def parts245 : List Block := [block11, block415, block416, block591, block595]
theorem input_checked_245 : InputValid selectedRecord245.preimage := by decide +kernel

theorem partition_checked_245 :
    blocks (pad selectedRecord245.preimage) = parts245 ∧
    parts245.flatten = pad selectedRecord245.preimage ∧
    (pad selectedRecord245.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_245 : CompressionChain initial parts245 after595 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_591 (CompressionChain.cons block_step_595 (CompressionChain.nil after595))))))

theorem digest_checked_245 : digestHex after595 = selectedRecord245.digest := by decide +kernel

theorem hash_checked_245 : HashEvaluated selectedRecord245 :=
  sha256_of_chain input_checked_245 partition_checked_245.1
    chain_checked_245 digest_checked_245

noncomputable def selectedRecord246 : Phase17Preimages.HashRecord := (Phase17Preimages.record29.ties.getD 4 { json := [], preimage := [], digest := "" })
noncomputable def parts246 : List Block := [block11, block415, block416, block591, block596]
theorem input_checked_246 : InputValid selectedRecord246.preimage := by decide +kernel

theorem partition_checked_246 :
    blocks (pad selectedRecord246.preimage) = parts246 ∧
    parts246.flatten = pad selectedRecord246.preimage ∧
    (pad selectedRecord246.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_246 : CompressionChain initial parts246 after596 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_591 (CompressionChain.cons block_step_596 (CompressionChain.nil after596))))))

theorem digest_checked_246 : digestHex after596 = selectedRecord246.digest := by decide +kernel

theorem hash_checked_246 : HashEvaluated selectedRecord246 :=
  sha256_of_chain input_checked_246 partition_checked_246.1
    chain_checked_246 digest_checked_246

noncomputable def selectedRecord247 : Phase17Preimages.HashRecord := (Phase17Preimages.record30.ties.getD 0 { json := [], preimage := [], digest := "" })
noncomputable def parts247 : List Block := [block11, block415, block416, block597, block598]
theorem input_checked_247 : InputValid selectedRecord247.preimage := by decide +kernel

theorem partition_checked_247 :
    blocks (pad selectedRecord247.preimage) = parts247 ∧
    parts247.flatten = pad selectedRecord247.preimage ∧
    (pad selectedRecord247.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_247 : CompressionChain initial parts247 after598 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_597 (CompressionChain.cons block_step_598 (CompressionChain.nil after598))))))

theorem digest_checked_247 : digestHex after598 = selectedRecord247.digest := by decide +kernel

theorem hash_checked_247 : HashEvaluated selectedRecord247 :=
  sha256_of_chain input_checked_247 partition_checked_247.1
    chain_checked_247 digest_checked_247

noncomputable def selectedRecord248 : Phase17Preimages.HashRecord := (Phase17Preimages.record30.ties.getD 1 { json := [], preimage := [], digest := "" })
noncomputable def parts248 : List Block := [block11, block415, block416, block597, block599]
theorem input_checked_248 : InputValid selectedRecord248.preimage := by decide +kernel

theorem partition_checked_248 :
    blocks (pad selectedRecord248.preimage) = parts248 ∧
    parts248.flatten = pad selectedRecord248.preimage ∧
    (pad selectedRecord248.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_248 : CompressionChain initial parts248 after599 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_597 (CompressionChain.cons block_step_599 (CompressionChain.nil after599))))))

theorem digest_checked_248 : digestHex after599 = selectedRecord248.digest := by decide +kernel

theorem hash_checked_248 : HashEvaluated selectedRecord248 :=
  sha256_of_chain input_checked_248 partition_checked_248.1
    chain_checked_248 digest_checked_248

noncomputable def selectedRecord249 : Phase17Preimages.HashRecord := (Phase17Preimages.record30.ties.getD 2 { json := [], preimage := [], digest := "" })
noncomputable def parts249 : List Block := [block11, block415, block416, block597, block600]
theorem input_checked_249 : InputValid selectedRecord249.preimage := by decide +kernel

theorem partition_checked_249 :
    blocks (pad selectedRecord249.preimage) = parts249 ∧
    parts249.flatten = pad selectedRecord249.preimage ∧
    (pad selectedRecord249.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_249 : CompressionChain initial parts249 after600 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_597 (CompressionChain.cons block_step_600 (CompressionChain.nil after600))))))

theorem digest_checked_249 : digestHex after600 = selectedRecord249.digest := by decide +kernel

theorem hash_checked_249 : HashEvaluated selectedRecord249 :=
  sha256_of_chain input_checked_249 partition_checked_249.1
    chain_checked_249 digest_checked_249

noncomputable def selectedRecord250 : Phase17Preimages.HashRecord := (Phase17Preimages.record30.ties.getD 3 { json := [], preimage := [], digest := "" })
noncomputable def parts250 : List Block := [block11, block415, block416, block597, block601]
theorem input_checked_250 : InputValid selectedRecord250.preimage := by decide +kernel

theorem partition_checked_250 :
    blocks (pad selectedRecord250.preimage) = parts250 ∧
    parts250.flatten = pad selectedRecord250.preimage ∧
    (pad selectedRecord250.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_250 : CompressionChain initial parts250 after601 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_597 (CompressionChain.cons block_step_601 (CompressionChain.nil after601))))))

theorem digest_checked_250 : digestHex after601 = selectedRecord250.digest := by decide +kernel

theorem hash_checked_250 : HashEvaluated selectedRecord250 :=
  sha256_of_chain input_checked_250 partition_checked_250.1
    chain_checked_250 digest_checked_250

noncomputable def selectedRecord251 : Phase17Preimages.HashRecord := (Phase17Preimages.record30.ties.getD 4 { json := [], preimage := [], digest := "" })
noncomputable def parts251 : List Block := [block11, block415, block416, block597, block602]
theorem input_checked_251 : InputValid selectedRecord251.preimage := by decide +kernel

theorem partition_checked_251 :
    blocks (pad selectedRecord251.preimage) = parts251 ∧
    parts251.flatten = pad selectedRecord251.preimage ∧
    (pad selectedRecord251.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_251 : CompressionChain initial parts251 after602 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_597 (CompressionChain.cons block_step_602 (CompressionChain.nil after602))))))

theorem digest_checked_251 : digestHex after602 = selectedRecord251.digest := by decide +kernel

theorem hash_checked_251 : HashEvaluated selectedRecord251 :=
  sha256_of_chain input_checked_251 partition_checked_251.1
    chain_checked_251 digest_checked_251

noncomputable def selectedRecord252 : Phase17Preimages.HashRecord := (Phase17Preimages.record31.ties.getD 0 { json := [], preimage := [], digest := "" })
noncomputable def parts252 : List Block := [block11, block415, block416, block603, block604]
theorem input_checked_252 : InputValid selectedRecord252.preimage := by decide +kernel

theorem partition_checked_252 :
    blocks (pad selectedRecord252.preimage) = parts252 ∧
    parts252.flatten = pad selectedRecord252.preimage ∧
    (pad selectedRecord252.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_252 : CompressionChain initial parts252 after604 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_603 (CompressionChain.cons block_step_604 (CompressionChain.nil after604))))))

theorem digest_checked_252 : digestHex after604 = selectedRecord252.digest := by decide +kernel

theorem hash_checked_252 : HashEvaluated selectedRecord252 :=
  sha256_of_chain input_checked_252 partition_checked_252.1
    chain_checked_252 digest_checked_252

noncomputable def selectedRecord253 : Phase17Preimages.HashRecord := (Phase17Preimages.record31.ties.getD 1 { json := [], preimage := [], digest := "" })
noncomputable def parts253 : List Block := [block11, block415, block416, block603, block605]
theorem input_checked_253 : InputValid selectedRecord253.preimage := by decide +kernel

theorem partition_checked_253 :
    blocks (pad selectedRecord253.preimage) = parts253 ∧
    parts253.flatten = pad selectedRecord253.preimage ∧
    (pad selectedRecord253.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_253 : CompressionChain initial parts253 after605 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_603 (CompressionChain.cons block_step_605 (CompressionChain.nil after605))))))

theorem digest_checked_253 : digestHex after605 = selectedRecord253.digest := by decide +kernel

theorem hash_checked_253 : HashEvaluated selectedRecord253 :=
  sha256_of_chain input_checked_253 partition_checked_253.1
    chain_checked_253 digest_checked_253

noncomputable def selectedRecord254 : Phase17Preimages.HashRecord := (Phase17Preimages.record31.ties.getD 2 { json := [], preimage := [], digest := "" })
noncomputable def parts254 : List Block := [block11, block415, block416, block603, block606]
theorem input_checked_254 : InputValid selectedRecord254.preimage := by decide +kernel

theorem partition_checked_254 :
    blocks (pad selectedRecord254.preimage) = parts254 ∧
    parts254.flatten = pad selectedRecord254.preimage ∧
    (pad selectedRecord254.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_254 : CompressionChain initial parts254 after606 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_603 (CompressionChain.cons block_step_606 (CompressionChain.nil after606))))))

theorem digest_checked_254 : digestHex after606 = selectedRecord254.digest := by decide +kernel

theorem hash_checked_254 : HashEvaluated selectedRecord254 :=
  sha256_of_chain input_checked_254 partition_checked_254.1
    chain_checked_254 digest_checked_254

noncomputable def selectedRecord255 : Phase17Preimages.HashRecord := (Phase17Preimages.record31.ties.getD 3 { json := [], preimage := [], digest := "" })
noncomputable def parts255 : List Block := [block11, block415, block416, block603, block607]
theorem input_checked_255 : InputValid selectedRecord255.preimage := by decide +kernel

theorem partition_checked_255 :
    blocks (pad selectedRecord255.preimage) = parts255 ∧
    parts255.flatten = pad selectedRecord255.preimage ∧
    (pad selectedRecord255.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_255 : CompressionChain initial parts255 after607 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_603 (CompressionChain.cons block_step_607 (CompressionChain.nil after607))))))

theorem digest_checked_255 : digestHex after607 = selectedRecord255.digest := by decide +kernel

theorem hash_checked_255 : HashEvaluated selectedRecord255 :=
  sha256_of_chain input_checked_255 partition_checked_255.1
    chain_checked_255 digest_checked_255

noncomputable def selectedRecord256 : Phase17Preimages.HashRecord := (Phase17Preimages.record31.ties.getD 4 { json := [], preimage := [], digest := "" })
noncomputable def parts256 : List Block := [block11, block415, block416, block603, block608]
theorem input_checked_256 : InputValid selectedRecord256.preimage := by decide +kernel

theorem partition_checked_256 :
    blocks (pad selectedRecord256.preimage) = parts256 ∧
    parts256.flatten = pad selectedRecord256.preimage ∧
    (pad selectedRecord256.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_256 : CompressionChain initial parts256 after608 := by
  exact (CompressionChain.cons block_step_11 (CompressionChain.cons block_step_415 (CompressionChain.cons block_step_416 (CompressionChain.cons block_step_603 (CompressionChain.cons block_step_608 (CompressionChain.nil after608))))))

theorem digest_checked_256 : digestHex after608 = selectedRecord256.digest := by decide +kernel

theorem hash_checked_256 : HashEvaluated selectedRecord256 :=
  sha256_of_chain input_checked_256 partition_checked_256.1
    chain_checked_256 digest_checked_256

noncomputable def selectedRecord257 : Phase17Preimages.HashRecord := Phase17Preimages.freezeRecord
noncomputable def parts257 : List Block := [block609, block610, block611, block612, block613, block614, block615, block616, block617, block618, block619, block620, block621, block622, block623, block624, block625, block626, block627, block628, block629, block630, block631, block632, block633, block634, block635, block636, block637, block638, block639, block640, block641, block642, block643, block644, block645, block646, block647, block648, block649, block650, block651, block652, block653, block654, block655, block656, block657, block658, block659, block660, block661, block662, block663, block664, block665, block666, block667, block668, block669, block670, block671, block672, block673, block674, block675, block676, block677, block678, block679, block680, block681, block682, block683, block684, block685, block686, block687, block688, block689, block690, block691]
theorem input_checked_257 : InputValid selectedRecord257.preimage := by decide +kernel

theorem partition_checked_257 :
    blocks (pad selectedRecord257.preimage) = parts257 ∧
    parts257.flatten = pad selectedRecord257.preimage ∧
    (pad selectedRecord257.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_257 : CompressionChain initial parts257 after691 := by
  exact (CompressionChain.cons block_step_609 (CompressionChain.cons block_step_610 (CompressionChain.cons block_step_611 (CompressionChain.cons block_step_612 (CompressionChain.cons block_step_613 (CompressionChain.cons block_step_614 (CompressionChain.cons block_step_615 (CompressionChain.cons block_step_616 (CompressionChain.cons block_step_617 (CompressionChain.cons block_step_618 (CompressionChain.cons block_step_619 (CompressionChain.cons block_step_620 (CompressionChain.cons block_step_621 (CompressionChain.cons block_step_622 (CompressionChain.cons block_step_623 (CompressionChain.cons block_step_624 (CompressionChain.cons block_step_625 (CompressionChain.cons block_step_626 (CompressionChain.cons block_step_627 (CompressionChain.cons block_step_628 (CompressionChain.cons block_step_629 (CompressionChain.cons block_step_630 (CompressionChain.cons block_step_631 (CompressionChain.cons block_step_632 (CompressionChain.cons block_step_633 (CompressionChain.cons block_step_634 (CompressionChain.cons block_step_635 (CompressionChain.cons block_step_636 (CompressionChain.cons block_step_637 (CompressionChain.cons block_step_638 (CompressionChain.cons block_step_639 (CompressionChain.cons block_step_640 (CompressionChain.cons block_step_641 (CompressionChain.cons block_step_642 (CompressionChain.cons block_step_643 (CompressionChain.cons block_step_644 (CompressionChain.cons block_step_645 (CompressionChain.cons block_step_646 (CompressionChain.cons block_step_647 (CompressionChain.cons block_step_648 (CompressionChain.cons block_step_649 (CompressionChain.cons block_step_650 (CompressionChain.cons block_step_651 (CompressionChain.cons block_step_652 (CompressionChain.cons block_step_653 (CompressionChain.cons block_step_654 (CompressionChain.cons block_step_655 (CompressionChain.cons block_step_656 (CompressionChain.cons block_step_657 (CompressionChain.cons block_step_658 (CompressionChain.cons block_step_659 (CompressionChain.cons block_step_660 (CompressionChain.cons block_step_661 (CompressionChain.cons block_step_662 (CompressionChain.cons block_step_663 (CompressionChain.cons block_step_664 (CompressionChain.cons block_step_665 (CompressionChain.cons block_step_666 (CompressionChain.cons block_step_667 (CompressionChain.cons block_step_668 (CompressionChain.cons block_step_669 (CompressionChain.cons block_step_670 (CompressionChain.cons block_step_671 (CompressionChain.cons block_step_672 (CompressionChain.cons block_step_673 (CompressionChain.cons block_step_674 (CompressionChain.cons block_step_675 (CompressionChain.cons block_step_676 (CompressionChain.cons block_step_677 (CompressionChain.cons block_step_678 (CompressionChain.cons block_step_679 (CompressionChain.cons block_step_680 (CompressionChain.cons block_step_681 (CompressionChain.cons block_step_682 (CompressionChain.cons block_step_683 (CompressionChain.cons block_step_684 (CompressionChain.cons block_step_685 (CompressionChain.cons block_step_686 (CompressionChain.cons block_step_687 (CompressionChain.cons block_step_688 (CompressionChain.cons block_step_689 (CompressionChain.cons block_step_690 (CompressionChain.cons block_step_691 (CompressionChain.nil after691))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))

theorem digest_checked_257 : digestHex after691 = selectedRecord257.digest := by decide +kernel

theorem hash_checked_257 : HashEvaluated selectedRecord257 :=
  sha256_of_chain input_checked_257 partition_checked_257.1
    chain_checked_257 digest_checked_257

noncomputable def selectedRecord258 : Phase17Preimages.HashRecord := { json := [], preimage := [], digest := "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855" }
noncomputable def parts258 : List Block := [block692]
theorem input_checked_258 : InputValid selectedRecord258.preimage := by decide +kernel

theorem partition_checked_258 :
    blocks (pad selectedRecord258.preimage) = parts258 ∧
    parts258.flatten = pad selectedRecord258.preimage ∧
    (pad selectedRecord258.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_258 : CompressionChain initial parts258 after692 := by
  exact (CompressionChain.cons block_step_692 (CompressionChain.nil after692))

theorem digest_checked_258 : digestHex after692 = selectedRecord258.digest := by decide +kernel

theorem hash_checked_258 : HashEvaluated selectedRecord258 :=
  sha256_of_chain input_checked_258 partition_checked_258.1
    chain_checked_258 digest_checked_258

noncomputable def selectedRecord259 : Phase17Preimages.HashRecord := { json := [], preimage := [97, 98, 99], digest := "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad" }
noncomputable def parts259 : List Block := [block693]
theorem input_checked_259 : InputValid selectedRecord259.preimage := by decide +kernel

theorem partition_checked_259 :
    blocks (pad selectedRecord259.preimage) = parts259 ∧
    parts259.flatten = pad selectedRecord259.preimage ∧
    (pad selectedRecord259.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_259 : CompressionChain initial parts259 after693 := by
  exact (CompressionChain.cons block_step_693 (CompressionChain.nil after693))

theorem digest_checked_259 : digestHex after693 = selectedRecord259.digest := by decide +kernel

theorem hash_checked_259 : HashEvaluated selectedRecord259 :=
  sha256_of_chain input_checked_259 partition_checked_259.1
    chain_checked_259 digest_checked_259

noncomputable def selectedRecord260 : Phase17Preimages.HashRecord := { json := [], preimage := [97, 98, 99, 100, 98, 99, 100, 101, 99, 100, 101, 102, 100, 101, 102, 103, 101, 102, 103, 104, 102, 103, 104, 105, 103, 104, 105, 106, 104, 105, 106, 107, 105, 106, 107, 108, 106, 107, 108, 109, 107, 108, 109, 110, 108, 109, 110, 111, 109, 110, 111, 112, 110, 111, 112, 113], digest := "248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1" }
noncomputable def parts260 : List Block := [block694, block695]
theorem input_checked_260 : InputValid selectedRecord260.preimage := by decide +kernel

theorem partition_checked_260 :
    blocks (pad selectedRecord260.preimage) = parts260 ∧
    parts260.flatten = pad selectedRecord260.preimage ∧
    (pad selectedRecord260.preimage).length % 64 = 0 := by decide +kernel

theorem chain_checked_260 : CompressionChain initial parts260 after695 := by
  exact (CompressionChain.cons block_step_694 (CompressionChain.cons block_step_695 (CompressionChain.nil after695)))

theorem digest_checked_260 : digestHex after695 = selectedRecord260.digest := by decide +kernel

theorem hash_checked_260 : HashEvaluated selectedRecord260 :=
  sha256_of_chain input_checked_260 partition_checked_260.1
    chain_checked_260 digest_checked_260

noncomputable def selectedRecords : List Phase17Preimages.HashRecord := [selectedRecord0, selectedRecord1, selectedRecord2, selectedRecord3, selectedRecord4, selectedRecord5, selectedRecord6, selectedRecord7, selectedRecord8, selectedRecord9, selectedRecord10, selectedRecord11, selectedRecord12, selectedRecord13, selectedRecord14, selectedRecord15, selectedRecord16, selectedRecord17, selectedRecord18, selectedRecord19, selectedRecord20, selectedRecord21, selectedRecord22, selectedRecord23, selectedRecord24, selectedRecord25, selectedRecord26, selectedRecord27, selectedRecord28, selectedRecord29, selectedRecord30, selectedRecord31, selectedRecord32, selectedRecord33, selectedRecord34, selectedRecord35, selectedRecord36, selectedRecord37, selectedRecord38, selectedRecord39, selectedRecord40, selectedRecord41, selectedRecord42, selectedRecord43, selectedRecord44, selectedRecord45, selectedRecord46, selectedRecord47, selectedRecord48, selectedRecord49, selectedRecord50, selectedRecord51, selectedRecord52, selectedRecord53, selectedRecord54, selectedRecord55, selectedRecord56, selectedRecord57, selectedRecord58, selectedRecord59, selectedRecord60, selectedRecord61, selectedRecord62, selectedRecord63, selectedRecord64, selectedRecord65, selectedRecord66, selectedRecord67, selectedRecord68, selectedRecord69, selectedRecord70, selectedRecord71, selectedRecord72, selectedRecord73, selectedRecord74, selectedRecord75, selectedRecord76, selectedRecord77, selectedRecord78, selectedRecord79, selectedRecord80, selectedRecord81, selectedRecord82, selectedRecord83, selectedRecord84, selectedRecord85, selectedRecord86, selectedRecord87, selectedRecord88, selectedRecord89, selectedRecord90, selectedRecord91, selectedRecord92, selectedRecord93, selectedRecord94, selectedRecord95, selectedRecord96, selectedRecord97, selectedRecord98, selectedRecord99, selectedRecord100, selectedRecord101, selectedRecord102, selectedRecord103, selectedRecord104, selectedRecord105, selectedRecord106, selectedRecord107, selectedRecord108, selectedRecord109, selectedRecord110, selectedRecord111, selectedRecord112, selectedRecord113, selectedRecord114, selectedRecord115, selectedRecord116, selectedRecord117, selectedRecord118, selectedRecord119, selectedRecord120, selectedRecord121, selectedRecord122, selectedRecord123, selectedRecord124, selectedRecord125, selectedRecord126, selectedRecord127, selectedRecord128, selectedRecord129, selectedRecord130, selectedRecord131, selectedRecord132, selectedRecord133, selectedRecord134, selectedRecord135, selectedRecord136, selectedRecord137, selectedRecord138, selectedRecord139, selectedRecord140, selectedRecord141, selectedRecord142, selectedRecord143, selectedRecord144, selectedRecord145, selectedRecord146, selectedRecord147, selectedRecord148, selectedRecord149, selectedRecord150, selectedRecord151, selectedRecord152, selectedRecord153, selectedRecord154, selectedRecord155, selectedRecord156, selectedRecord157, selectedRecord158, selectedRecord159, selectedRecord160, selectedRecord161, selectedRecord162, selectedRecord163, selectedRecord164, selectedRecord165, selectedRecord166, selectedRecord167, selectedRecord168, selectedRecord169, selectedRecord170, selectedRecord171, selectedRecord172, selectedRecord173, selectedRecord174, selectedRecord175, selectedRecord176, selectedRecord177, selectedRecord178, selectedRecord179, selectedRecord180, selectedRecord181, selectedRecord182, selectedRecord183, selectedRecord184, selectedRecord185, selectedRecord186, selectedRecord187, selectedRecord188, selectedRecord189, selectedRecord190, selectedRecord191, selectedRecord192, selectedRecord193, selectedRecord194, selectedRecord195, selectedRecord196, selectedRecord197, selectedRecord198, selectedRecord199, selectedRecord200, selectedRecord201, selectedRecord202, selectedRecord203, selectedRecord204, selectedRecord205, selectedRecord206, selectedRecord207, selectedRecord208, selectedRecord209, selectedRecord210, selectedRecord211, selectedRecord212, selectedRecord213, selectedRecord214, selectedRecord215, selectedRecord216, selectedRecord217, selectedRecord218, selectedRecord219, selectedRecord220, selectedRecord221, selectedRecord222, selectedRecord223, selectedRecord224, selectedRecord225, selectedRecord226, selectedRecord227, selectedRecord228, selectedRecord229, selectedRecord230, selectedRecord231, selectedRecord232, selectedRecord233, selectedRecord234, selectedRecord235, selectedRecord236, selectedRecord237, selectedRecord238, selectedRecord239, selectedRecord240, selectedRecord241, selectedRecord242, selectedRecord243, selectedRecord244, selectedRecord245, selectedRecord246, selectedRecord247, selectedRecord248, selectedRecord249, selectedRecord250, selectedRecord251, selectedRecord252, selectedRecord253, selectedRecord254, selectedRecord255, selectedRecord256, selectedRecord257]
theorem all_selected_hashed : AllHashed selectedRecords := (AllHashed.cons hash_checked_0 (AllHashed.cons hash_checked_1 (AllHashed.cons hash_checked_2 (AllHashed.cons hash_checked_3 (AllHashed.cons hash_checked_4 (AllHashed.cons hash_checked_5 (AllHashed.cons hash_checked_6 (AllHashed.cons hash_checked_7 (AllHashed.cons hash_checked_8 (AllHashed.cons hash_checked_9 (AllHashed.cons hash_checked_10 (AllHashed.cons hash_checked_11 (AllHashed.cons hash_checked_12 (AllHashed.cons hash_checked_13 (AllHashed.cons hash_checked_14 (AllHashed.cons hash_checked_15 (AllHashed.cons hash_checked_16 (AllHashed.cons hash_checked_17 (AllHashed.cons hash_checked_18 (AllHashed.cons hash_checked_19 (AllHashed.cons hash_checked_20 (AllHashed.cons hash_checked_21 (AllHashed.cons hash_checked_22 (AllHashed.cons hash_checked_23 (AllHashed.cons hash_checked_24 (AllHashed.cons hash_checked_25 (AllHashed.cons hash_checked_26 (AllHashed.cons hash_checked_27 (AllHashed.cons hash_checked_28 (AllHashed.cons hash_checked_29 (AllHashed.cons hash_checked_30 (AllHashed.cons hash_checked_31 (AllHashed.cons hash_checked_32 (AllHashed.cons hash_checked_33 (AllHashed.cons hash_checked_34 (AllHashed.cons hash_checked_35 (AllHashed.cons hash_checked_36 (AllHashed.cons hash_checked_37 (AllHashed.cons hash_checked_38 (AllHashed.cons hash_checked_39 (AllHashed.cons hash_checked_40 (AllHashed.cons hash_checked_41 (AllHashed.cons hash_checked_42 (AllHashed.cons hash_checked_43 (AllHashed.cons hash_checked_44 (AllHashed.cons hash_checked_45 (AllHashed.cons hash_checked_46 (AllHashed.cons hash_checked_47 (AllHashed.cons hash_checked_48 (AllHashed.cons hash_checked_49 (AllHashed.cons hash_checked_50 (AllHashed.cons hash_checked_51 (AllHashed.cons hash_checked_52 (AllHashed.cons hash_checked_53 (AllHashed.cons hash_checked_54 (AllHashed.cons hash_checked_55 (AllHashed.cons hash_checked_56 (AllHashed.cons hash_checked_57 (AllHashed.cons hash_checked_58 (AllHashed.cons hash_checked_59 (AllHashed.cons hash_checked_60 (AllHashed.cons hash_checked_61 (AllHashed.cons hash_checked_62 (AllHashed.cons hash_checked_63 (AllHashed.cons hash_checked_64 (AllHashed.cons hash_checked_65 (AllHashed.cons hash_checked_66 (AllHashed.cons hash_checked_67 (AllHashed.cons hash_checked_68 (AllHashed.cons hash_checked_69 (AllHashed.cons hash_checked_70 (AllHashed.cons hash_checked_71 (AllHashed.cons hash_checked_72 (AllHashed.cons hash_checked_73 (AllHashed.cons hash_checked_74 (AllHashed.cons hash_checked_75 (AllHashed.cons hash_checked_76 (AllHashed.cons hash_checked_77 (AllHashed.cons hash_checked_78 (AllHashed.cons hash_checked_79 (AllHashed.cons hash_checked_80 (AllHashed.cons hash_checked_81 (AllHashed.cons hash_checked_82 (AllHashed.cons hash_checked_83 (AllHashed.cons hash_checked_84 (AllHashed.cons hash_checked_85 (AllHashed.cons hash_checked_86 (AllHashed.cons hash_checked_87 (AllHashed.cons hash_checked_88 (AllHashed.cons hash_checked_89 (AllHashed.cons hash_checked_90 (AllHashed.cons hash_checked_91 (AllHashed.cons hash_checked_92 (AllHashed.cons hash_checked_93 (AllHashed.cons hash_checked_94 (AllHashed.cons hash_checked_95 (AllHashed.cons hash_checked_96 (AllHashed.cons hash_checked_97 (AllHashed.cons hash_checked_98 (AllHashed.cons hash_checked_99 (AllHashed.cons hash_checked_100 (AllHashed.cons hash_checked_101 (AllHashed.cons hash_checked_102 (AllHashed.cons hash_checked_103 (AllHashed.cons hash_checked_104 (AllHashed.cons hash_checked_105 (AllHashed.cons hash_checked_106 (AllHashed.cons hash_checked_107 (AllHashed.cons hash_checked_108 (AllHashed.cons hash_checked_109 (AllHashed.cons hash_checked_110 (AllHashed.cons hash_checked_111 (AllHashed.cons hash_checked_112 (AllHashed.cons hash_checked_113 (AllHashed.cons hash_checked_114 (AllHashed.cons hash_checked_115 (AllHashed.cons hash_checked_116 (AllHashed.cons hash_checked_117 (AllHashed.cons hash_checked_118 (AllHashed.cons hash_checked_119 (AllHashed.cons hash_checked_120 (AllHashed.cons hash_checked_121 (AllHashed.cons hash_checked_122 (AllHashed.cons hash_checked_123 (AllHashed.cons hash_checked_124 (AllHashed.cons hash_checked_125 (AllHashed.cons hash_checked_126 (AllHashed.cons hash_checked_127 (AllHashed.cons hash_checked_128 (AllHashed.cons hash_checked_129 (AllHashed.cons hash_checked_130 (AllHashed.cons hash_checked_131 (AllHashed.cons hash_checked_132 (AllHashed.cons hash_checked_133 (AllHashed.cons hash_checked_134 (AllHashed.cons hash_checked_135 (AllHashed.cons hash_checked_136 (AllHashed.cons hash_checked_137 (AllHashed.cons hash_checked_138 (AllHashed.cons hash_checked_139 (AllHashed.cons hash_checked_140 (AllHashed.cons hash_checked_141 (AllHashed.cons hash_checked_142 (AllHashed.cons hash_checked_143 (AllHashed.cons hash_checked_144 (AllHashed.cons hash_checked_145 (AllHashed.cons hash_checked_146 (AllHashed.cons hash_checked_147 (AllHashed.cons hash_checked_148 (AllHashed.cons hash_checked_149 (AllHashed.cons hash_checked_150 (AllHashed.cons hash_checked_151 (AllHashed.cons hash_checked_152 (AllHashed.cons hash_checked_153 (AllHashed.cons hash_checked_154 (AllHashed.cons hash_checked_155 (AllHashed.cons hash_checked_156 (AllHashed.cons hash_checked_157 (AllHashed.cons hash_checked_158 (AllHashed.cons hash_checked_159 (AllHashed.cons hash_checked_160 (AllHashed.cons hash_checked_161 (AllHashed.cons hash_checked_162 (AllHashed.cons hash_checked_163 (AllHashed.cons hash_checked_164 (AllHashed.cons hash_checked_165 (AllHashed.cons hash_checked_166 (AllHashed.cons hash_checked_167 (AllHashed.cons hash_checked_168 (AllHashed.cons hash_checked_169 (AllHashed.cons hash_checked_170 (AllHashed.cons hash_checked_171 (AllHashed.cons hash_checked_172 (AllHashed.cons hash_checked_173 (AllHashed.cons hash_checked_174 (AllHashed.cons hash_checked_175 (AllHashed.cons hash_checked_176 (AllHashed.cons hash_checked_177 (AllHashed.cons hash_checked_178 (AllHashed.cons hash_checked_179 (AllHashed.cons hash_checked_180 (AllHashed.cons hash_checked_181 (AllHashed.cons hash_checked_182 (AllHashed.cons hash_checked_183 (AllHashed.cons hash_checked_184 (AllHashed.cons hash_checked_185 (AllHashed.cons hash_checked_186 (AllHashed.cons hash_checked_187 (AllHashed.cons hash_checked_188 (AllHashed.cons hash_checked_189 (AllHashed.cons hash_checked_190 (AllHashed.cons hash_checked_191 (AllHashed.cons hash_checked_192 (AllHashed.cons hash_checked_193 (AllHashed.cons hash_checked_194 (AllHashed.cons hash_checked_195 (AllHashed.cons hash_checked_196 (AllHashed.cons hash_checked_197 (AllHashed.cons hash_checked_198 (AllHashed.cons hash_checked_199 (AllHashed.cons hash_checked_200 (AllHashed.cons hash_checked_201 (AllHashed.cons hash_checked_202 (AllHashed.cons hash_checked_203 (AllHashed.cons hash_checked_204 (AllHashed.cons hash_checked_205 (AllHashed.cons hash_checked_206 (AllHashed.cons hash_checked_207 (AllHashed.cons hash_checked_208 (AllHashed.cons hash_checked_209 (AllHashed.cons hash_checked_210 (AllHashed.cons hash_checked_211 (AllHashed.cons hash_checked_212 (AllHashed.cons hash_checked_213 (AllHashed.cons hash_checked_214 (AllHashed.cons hash_checked_215 (AllHashed.cons hash_checked_216 (AllHashed.cons hash_checked_217 (AllHashed.cons hash_checked_218 (AllHashed.cons hash_checked_219 (AllHashed.cons hash_checked_220 (AllHashed.cons hash_checked_221 (AllHashed.cons hash_checked_222 (AllHashed.cons hash_checked_223 (AllHashed.cons hash_checked_224 (AllHashed.cons hash_checked_225 (AllHashed.cons hash_checked_226 (AllHashed.cons hash_checked_227 (AllHashed.cons hash_checked_228 (AllHashed.cons hash_checked_229 (AllHashed.cons hash_checked_230 (AllHashed.cons hash_checked_231 (AllHashed.cons hash_checked_232 (AllHashed.cons hash_checked_233 (AllHashed.cons hash_checked_234 (AllHashed.cons hash_checked_235 (AllHashed.cons hash_checked_236 (AllHashed.cons hash_checked_237 (AllHashed.cons hash_checked_238 (AllHashed.cons hash_checked_239 (AllHashed.cons hash_checked_240 (AllHashed.cons hash_checked_241 (AllHashed.cons hash_checked_242 (AllHashed.cons hash_checked_243 (AllHashed.cons hash_checked_244 (AllHashed.cons hash_checked_245 (AllHashed.cons hash_checked_246 (AllHashed.cons hash_checked_247 (AllHashed.cons hash_checked_248 (AllHashed.cons hash_checked_249 (AllHashed.cons hash_checked_250 (AllHashed.cons hash_checked_251 (AllHashed.cons hash_checked_252 (AllHashed.cons hash_checked_253 (AllHashed.cons hash_checked_254 (AllHashed.cons hash_checked_255 (AllHashed.cons hash_checked_256 (AllHashed.cons hash_checked_257 AllHashed.nil))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))

theorem selected_hash_inventory :
    selectedRecords.length = 258 ∧
    (selectedRecords.map (fun record => record.preimage.length)).sum = 98349 ∧
    (selectedRecords.map (fun record => (blocks (pad record.preimage)).length)).sum = 1652 ∧
    digestRecords selectedRecords = some (selectedRecords.map Phase17Preimages.HashRecord.digest) := by
  refine ⟨by decide +kernel, by decide +kernel, by decide +kernel, ?_⟩
  exact digest_records_sound selectedRecords all_selected_hashed

noncomputable def rankingRecords : List Phase17Preimages.HashRecord := [selectedRecord0]
theorem selected_ranking_digest :
    digestRecords rankingRecords = some (rankingRecords.map Phase17Preimages.HashRecord.digest) :=
  digest_records_sound _ (AllHashed.cons hash_checked_0 AllHashed.nil)

noncomputable def grammarRecords : List Phase17Preimages.HashRecord := [selectedRecord1, selectedRecord2, selectedRecord3, selectedRecord4, selectedRecord5, selectedRecord6, selectedRecord7, selectedRecord8, selectedRecord9, selectedRecord10, selectedRecord11, selectedRecord12, selectedRecord13, selectedRecord14, selectedRecord15, selectedRecord16, selectedRecord17, selectedRecord18, selectedRecord19, selectedRecord20, selectedRecord21, selectedRecord22, selectedRecord23, selectedRecord24, selectedRecord25, selectedRecord26, selectedRecord27, selectedRecord28, selectedRecord29, selectedRecord30, selectedRecord31, selectedRecord32]
theorem selected_grammar_digests :
    digestRecords grammarRecords = some (grammarRecords.map Phase17Preimages.HashRecord.digest) :=
  digest_records_sound _ (AllHashed.cons hash_checked_1 (AllHashed.cons hash_checked_2 (AllHashed.cons hash_checked_3 (AllHashed.cons hash_checked_4 (AllHashed.cons hash_checked_5 (AllHashed.cons hash_checked_6 (AllHashed.cons hash_checked_7 (AllHashed.cons hash_checked_8 (AllHashed.cons hash_checked_9 (AllHashed.cons hash_checked_10 (AllHashed.cons hash_checked_11 (AllHashed.cons hash_checked_12 (AllHashed.cons hash_checked_13 (AllHashed.cons hash_checked_14 (AllHashed.cons hash_checked_15 (AllHashed.cons hash_checked_16 (AllHashed.cons hash_checked_17 (AllHashed.cons hash_checked_18 (AllHashed.cons hash_checked_19 (AllHashed.cons hash_checked_20 (AllHashed.cons hash_checked_21 (AllHashed.cons hash_checked_22 (AllHashed.cons hash_checked_23 (AllHashed.cons hash_checked_24 (AllHashed.cons hash_checked_25 (AllHashed.cons hash_checked_26 (AllHashed.cons hash_checked_27 (AllHashed.cons hash_checked_28 (AllHashed.cons hash_checked_29 (AllHashed.cons hash_checked_30 (AllHashed.cons hash_checked_31 (AllHashed.cons hash_checked_32 AllHashed.nil))))))))))))))))))))))))))))))))

noncomputable def programRecords : List Phase17Preimages.HashRecord := [selectedRecord33, selectedRecord34, selectedRecord35, selectedRecord36, selectedRecord37, selectedRecord38, selectedRecord39, selectedRecord40, selectedRecord41, selectedRecord42, selectedRecord43, selectedRecord44, selectedRecord45, selectedRecord46, selectedRecord47, selectedRecord48, selectedRecord49, selectedRecord50, selectedRecord51, selectedRecord52, selectedRecord53, selectedRecord54, selectedRecord55, selectedRecord56, selectedRecord57, selectedRecord58, selectedRecord59, selectedRecord60, selectedRecord61, selectedRecord62, selectedRecord63, selectedRecord64]
theorem selected_program_digests :
    digestRecords programRecords = some (programRecords.map Phase17Preimages.HashRecord.digest) :=
  digest_records_sound _ (AllHashed.cons hash_checked_33 (AllHashed.cons hash_checked_34 (AllHashed.cons hash_checked_35 (AllHashed.cons hash_checked_36 (AllHashed.cons hash_checked_37 (AllHashed.cons hash_checked_38 (AllHashed.cons hash_checked_39 (AllHashed.cons hash_checked_40 (AllHashed.cons hash_checked_41 (AllHashed.cons hash_checked_42 (AllHashed.cons hash_checked_43 (AllHashed.cons hash_checked_44 (AllHashed.cons hash_checked_45 (AllHashed.cons hash_checked_46 (AllHashed.cons hash_checked_47 (AllHashed.cons hash_checked_48 (AllHashed.cons hash_checked_49 (AllHashed.cons hash_checked_50 (AllHashed.cons hash_checked_51 (AllHashed.cons hash_checked_52 (AllHashed.cons hash_checked_53 (AllHashed.cons hash_checked_54 (AllHashed.cons hash_checked_55 (AllHashed.cons hash_checked_56 (AllHashed.cons hash_checked_57 (AllHashed.cons hash_checked_58 (AllHashed.cons hash_checked_59 (AllHashed.cons hash_checked_60 (AllHashed.cons hash_checked_61 (AllHashed.cons hash_checked_62 (AllHashed.cons hash_checked_63 (AllHashed.cons hash_checked_64 AllHashed.nil))))))))))))))))))))))))))))))))

noncomputable def featureRecords : List Phase17Preimages.HashRecord := [selectedRecord65, selectedRecord66, selectedRecord67, selectedRecord68, selectedRecord69, selectedRecord70, selectedRecord71, selectedRecord72, selectedRecord73, selectedRecord74, selectedRecord75, selectedRecord76, selectedRecord77, selectedRecord78, selectedRecord79, selectedRecord80, selectedRecord81, selectedRecord82, selectedRecord83, selectedRecord84, selectedRecord85, selectedRecord86, selectedRecord87, selectedRecord88, selectedRecord89, selectedRecord90, selectedRecord91, selectedRecord92, selectedRecord93, selectedRecord94, selectedRecord95, selectedRecord96]
theorem selected_feature_digests :
    digestRecords featureRecords = some (featureRecords.map Phase17Preimages.HashRecord.digest) :=
  digest_records_sound _ (AllHashed.cons hash_checked_65 (AllHashed.cons hash_checked_66 (AllHashed.cons hash_checked_67 (AllHashed.cons hash_checked_68 (AllHashed.cons hash_checked_69 (AllHashed.cons hash_checked_70 (AllHashed.cons hash_checked_71 (AllHashed.cons hash_checked_72 (AllHashed.cons hash_checked_73 (AllHashed.cons hash_checked_74 (AllHashed.cons hash_checked_75 (AllHashed.cons hash_checked_76 (AllHashed.cons hash_checked_77 (AllHashed.cons hash_checked_78 (AllHashed.cons hash_checked_79 (AllHashed.cons hash_checked_80 (AllHashed.cons hash_checked_81 (AllHashed.cons hash_checked_82 (AllHashed.cons hash_checked_83 (AllHashed.cons hash_checked_84 (AllHashed.cons hash_checked_85 (AllHashed.cons hash_checked_86 (AllHashed.cons hash_checked_87 (AllHashed.cons hash_checked_88 (AllHashed.cons hash_checked_89 (AllHashed.cons hash_checked_90 (AllHashed.cons hash_checked_91 (AllHashed.cons hash_checked_92 (AllHashed.cons hash_checked_93 (AllHashed.cons hash_checked_94 (AllHashed.cons hash_checked_95 (AllHashed.cons hash_checked_96 AllHashed.nil))))))))))))))))))))))))))))))))

noncomputable def tieRecords : List Phase17Preimages.HashRecord := [selectedRecord97, selectedRecord98, selectedRecord99, selectedRecord100, selectedRecord101, selectedRecord102, selectedRecord103, selectedRecord104, selectedRecord105, selectedRecord106, selectedRecord107, selectedRecord108, selectedRecord109, selectedRecord110, selectedRecord111, selectedRecord112, selectedRecord113, selectedRecord114, selectedRecord115, selectedRecord116, selectedRecord117, selectedRecord118, selectedRecord119, selectedRecord120, selectedRecord121, selectedRecord122, selectedRecord123, selectedRecord124, selectedRecord125, selectedRecord126, selectedRecord127, selectedRecord128, selectedRecord129, selectedRecord130, selectedRecord131, selectedRecord132, selectedRecord133, selectedRecord134, selectedRecord135, selectedRecord136, selectedRecord137, selectedRecord138, selectedRecord139, selectedRecord140, selectedRecord141, selectedRecord142, selectedRecord143, selectedRecord144, selectedRecord145, selectedRecord146, selectedRecord147, selectedRecord148, selectedRecord149, selectedRecord150, selectedRecord151, selectedRecord152, selectedRecord153, selectedRecord154, selectedRecord155, selectedRecord156, selectedRecord157, selectedRecord158, selectedRecord159, selectedRecord160, selectedRecord161, selectedRecord162, selectedRecord163, selectedRecord164, selectedRecord165, selectedRecord166, selectedRecord167, selectedRecord168, selectedRecord169, selectedRecord170, selectedRecord171, selectedRecord172, selectedRecord173, selectedRecord174, selectedRecord175, selectedRecord176, selectedRecord177, selectedRecord178, selectedRecord179, selectedRecord180, selectedRecord181, selectedRecord182, selectedRecord183, selectedRecord184, selectedRecord185, selectedRecord186, selectedRecord187, selectedRecord188, selectedRecord189, selectedRecord190, selectedRecord191, selectedRecord192, selectedRecord193, selectedRecord194, selectedRecord195, selectedRecord196, selectedRecord197, selectedRecord198, selectedRecord199, selectedRecord200, selectedRecord201, selectedRecord202, selectedRecord203, selectedRecord204, selectedRecord205, selectedRecord206, selectedRecord207, selectedRecord208, selectedRecord209, selectedRecord210, selectedRecord211, selectedRecord212, selectedRecord213, selectedRecord214, selectedRecord215, selectedRecord216, selectedRecord217, selectedRecord218, selectedRecord219, selectedRecord220, selectedRecord221, selectedRecord222, selectedRecord223, selectedRecord224, selectedRecord225, selectedRecord226, selectedRecord227, selectedRecord228, selectedRecord229, selectedRecord230, selectedRecord231, selectedRecord232, selectedRecord233, selectedRecord234, selectedRecord235, selectedRecord236, selectedRecord237, selectedRecord238, selectedRecord239, selectedRecord240, selectedRecord241, selectedRecord242, selectedRecord243, selectedRecord244, selectedRecord245, selectedRecord246, selectedRecord247, selectedRecord248, selectedRecord249, selectedRecord250, selectedRecord251, selectedRecord252, selectedRecord253, selectedRecord254, selectedRecord255, selectedRecord256]
theorem selected_tie_digests :
    digestRecords tieRecords = some (tieRecords.map Phase17Preimages.HashRecord.digest) :=
  digest_records_sound _ (AllHashed.cons hash_checked_97 (AllHashed.cons hash_checked_98 (AllHashed.cons hash_checked_99 (AllHashed.cons hash_checked_100 (AllHashed.cons hash_checked_101 (AllHashed.cons hash_checked_102 (AllHashed.cons hash_checked_103 (AllHashed.cons hash_checked_104 (AllHashed.cons hash_checked_105 (AllHashed.cons hash_checked_106 (AllHashed.cons hash_checked_107 (AllHashed.cons hash_checked_108 (AllHashed.cons hash_checked_109 (AllHashed.cons hash_checked_110 (AllHashed.cons hash_checked_111 (AllHashed.cons hash_checked_112 (AllHashed.cons hash_checked_113 (AllHashed.cons hash_checked_114 (AllHashed.cons hash_checked_115 (AllHashed.cons hash_checked_116 (AllHashed.cons hash_checked_117 (AllHashed.cons hash_checked_118 (AllHashed.cons hash_checked_119 (AllHashed.cons hash_checked_120 (AllHashed.cons hash_checked_121 (AllHashed.cons hash_checked_122 (AllHashed.cons hash_checked_123 (AllHashed.cons hash_checked_124 (AllHashed.cons hash_checked_125 (AllHashed.cons hash_checked_126 (AllHashed.cons hash_checked_127 (AllHashed.cons hash_checked_128 (AllHashed.cons hash_checked_129 (AllHashed.cons hash_checked_130 (AllHashed.cons hash_checked_131 (AllHashed.cons hash_checked_132 (AllHashed.cons hash_checked_133 (AllHashed.cons hash_checked_134 (AllHashed.cons hash_checked_135 (AllHashed.cons hash_checked_136 (AllHashed.cons hash_checked_137 (AllHashed.cons hash_checked_138 (AllHashed.cons hash_checked_139 (AllHashed.cons hash_checked_140 (AllHashed.cons hash_checked_141 (AllHashed.cons hash_checked_142 (AllHashed.cons hash_checked_143 (AllHashed.cons hash_checked_144 (AllHashed.cons hash_checked_145 (AllHashed.cons hash_checked_146 (AllHashed.cons hash_checked_147 (AllHashed.cons hash_checked_148 (AllHashed.cons hash_checked_149 (AllHashed.cons hash_checked_150 (AllHashed.cons hash_checked_151 (AllHashed.cons hash_checked_152 (AllHashed.cons hash_checked_153 (AllHashed.cons hash_checked_154 (AllHashed.cons hash_checked_155 (AllHashed.cons hash_checked_156 (AllHashed.cons hash_checked_157 (AllHashed.cons hash_checked_158 (AllHashed.cons hash_checked_159 (AllHashed.cons hash_checked_160 (AllHashed.cons hash_checked_161 (AllHashed.cons hash_checked_162 (AllHashed.cons hash_checked_163 (AllHashed.cons hash_checked_164 (AllHashed.cons hash_checked_165 (AllHashed.cons hash_checked_166 (AllHashed.cons hash_checked_167 (AllHashed.cons hash_checked_168 (AllHashed.cons hash_checked_169 (AllHashed.cons hash_checked_170 (AllHashed.cons hash_checked_171 (AllHashed.cons hash_checked_172 (AllHashed.cons hash_checked_173 (AllHashed.cons hash_checked_174 (AllHashed.cons hash_checked_175 (AllHashed.cons hash_checked_176 (AllHashed.cons hash_checked_177 (AllHashed.cons hash_checked_178 (AllHashed.cons hash_checked_179 (AllHashed.cons hash_checked_180 (AllHashed.cons hash_checked_181 (AllHashed.cons hash_checked_182 (AllHashed.cons hash_checked_183 (AllHashed.cons hash_checked_184 (AllHashed.cons hash_checked_185 (AllHashed.cons hash_checked_186 (AllHashed.cons hash_checked_187 (AllHashed.cons hash_checked_188 (AllHashed.cons hash_checked_189 (AllHashed.cons hash_checked_190 (AllHashed.cons hash_checked_191 (AllHashed.cons hash_checked_192 (AllHashed.cons hash_checked_193 (AllHashed.cons hash_checked_194 (AllHashed.cons hash_checked_195 (AllHashed.cons hash_checked_196 (AllHashed.cons hash_checked_197 (AllHashed.cons hash_checked_198 (AllHashed.cons hash_checked_199 (AllHashed.cons hash_checked_200 (AllHashed.cons hash_checked_201 (AllHashed.cons hash_checked_202 (AllHashed.cons hash_checked_203 (AllHashed.cons hash_checked_204 (AllHashed.cons hash_checked_205 (AllHashed.cons hash_checked_206 (AllHashed.cons hash_checked_207 (AllHashed.cons hash_checked_208 (AllHashed.cons hash_checked_209 (AllHashed.cons hash_checked_210 (AllHashed.cons hash_checked_211 (AllHashed.cons hash_checked_212 (AllHashed.cons hash_checked_213 (AllHashed.cons hash_checked_214 (AllHashed.cons hash_checked_215 (AllHashed.cons hash_checked_216 (AllHashed.cons hash_checked_217 (AllHashed.cons hash_checked_218 (AllHashed.cons hash_checked_219 (AllHashed.cons hash_checked_220 (AllHashed.cons hash_checked_221 (AllHashed.cons hash_checked_222 (AllHashed.cons hash_checked_223 (AllHashed.cons hash_checked_224 (AllHashed.cons hash_checked_225 (AllHashed.cons hash_checked_226 (AllHashed.cons hash_checked_227 (AllHashed.cons hash_checked_228 (AllHashed.cons hash_checked_229 (AllHashed.cons hash_checked_230 (AllHashed.cons hash_checked_231 (AllHashed.cons hash_checked_232 (AllHashed.cons hash_checked_233 (AllHashed.cons hash_checked_234 (AllHashed.cons hash_checked_235 (AllHashed.cons hash_checked_236 (AllHashed.cons hash_checked_237 (AllHashed.cons hash_checked_238 (AllHashed.cons hash_checked_239 (AllHashed.cons hash_checked_240 (AllHashed.cons hash_checked_241 (AllHashed.cons hash_checked_242 (AllHashed.cons hash_checked_243 (AllHashed.cons hash_checked_244 (AllHashed.cons hash_checked_245 (AllHashed.cons hash_checked_246 (AllHashed.cons hash_checked_247 (AllHashed.cons hash_checked_248 (AllHashed.cons hash_checked_249 (AllHashed.cons hash_checked_250 (AllHashed.cons hash_checked_251 (AllHashed.cons hash_checked_252 (AllHashed.cons hash_checked_253 (AllHashed.cons hash_checked_254 (AllHashed.cons hash_checked_255 (AllHashed.cons hash_checked_256 AllHashed.nil))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))

noncomputable def freezeRecords : List Phase17Preimages.HashRecord := [selectedRecord257]
theorem selected_freeze_digest :
    digestRecords freezeRecords = some (freezeRecords.map Phase17Preimages.HashRecord.digest) :=
  digest_records_sound _ (AllHashed.cons hash_checked_257 AllHashed.nil)

theorem selected_standard_vectors :
    sha256 [] = some "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855" ∧
    sha256 [97, 98, 99] = some "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad" ∧
    sha256 (Phase17Preimages.ascii "abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq") =
      some "248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1" := by
  exact ⟨hash_checked_258, hash_checked_259, hash_checked_260⟩

theorem selected_padding_edges :
    (pad []).length = 64 ∧
    (pad (List.replicate 55 0)).length = 64 ∧
    (pad (List.replicate 56 0)).length = 128 ∧
    (pad (List.replicate 63 0)).length = 128 ∧
    (pad (List.replicate 64 0)).length = 128 ∧
    be64 440 = [0, 0, 0, 0, 0, 0, 1, 184] ∧
    be64 448 = [0, 0, 0, 0, 0, 0, 1, 192] ∧
    be64 18446744073709551615 = [255, 255, 255, 255, 255, 255, 255, 255] ∧
    word [1, 2, 3, 4] = 16909060 ∧
    ror 2147483649 1 = 3221225472 ∧
    u32 4294967296 = 0 ∧
    sha256 [256] = none ∧
    constants.length = 64 ∧ initial.length = 8 := by decide +kernel

theorem selected_learned_acceptance_bound :
    AllHashed selectedRecords ∧
    (Phase17Preimages.hashInput
      (Phase17Preimages.rankingSeedValue Phase17Preimages.selectedView)).bind sha256 =
        some Phase17Preimages.rankingSeedRecord.digest ∧
    (Phase17Preimages.hashInput
      (Phase17Preimages.freezeValue Phase17Preimages.selectedView Phase17Provenance.selectedContext.rows
        Phase17Metadata.candidateDescriptors)).bind sha256 = some Phase17Preimages.freezeRecord.digest ∧
    Phase17Preimages.derivedDescriptors = some Phase17Metadata.candidateDescriptors ∧
    Phase17Metadata.reconstructedContext Phase17Provenance.selectedContext Phase17Planner.beforeImage
      Phase17Preimages.freezeRecord.digest Phase17Preimages.selectedView.context Phase17Metadata.beforeImages
      Phase17Preimages.derivedPublicRows Phase17Preimages.derivedImages =
        some Phase17Finite.selectedConfiguration.context ∧
    Phase17Metadata.reconstructedContext Phase17Provenance.selectedContext Phase17Planner.afterImage
      Phase17Preimages.freezeRecord.digest Phase17Preimages.selectedView.context Phase17Metadata.afterImages
      Phase17Preimages.derivedPublicRows Phase17Preimages.derivedImages =
        some Phase17Finite.selectedConfiguration.context ∧
    Phase17Provenance.Produced Phase17Finite.selectedConfiguration.context Phase17Finite.selectedEvidence.proposal ∧
    Learned.LearnedAcceptedStep (Phase17Finite.learned Phase17Finite.selectedConfiguration)
      Phase17Finite.selectedBefore Phase17Finite.selectedCandidate
      (Phase17Finite.packet Phase17Finite.selectedConfiguration
        Phase17Finite.selectedBefore Phase17Finite.selectedEvidence) := by
  exact ⟨all_selected_hashed,
    preimage_digest_bound _ _ Phase17Preimages.selected_ranking_seed_preimage.1 hash_checked_0,
    preimage_digest_bound _ _ Phase17Preimages.selected_freeze_preimage.1 hash_checked_257,
    Phase17Preimages.selected_descriptors_bound.1,
    Phase17Preimages.selected_context_bound.1, Phase17Preimages.selected_context_bound.2,
    Phase17Provenance.selected_provenance, Phase17Finite.selected_learned_accepted⟩

end Phase17Sha256
#print axioms Phase17Sha256.schedule_checked_sound
#print axioms Phase17Sha256.rounds_checked_sound
#print axioms Phase17Sha256.block_checked_sound
#print axioms Phase17Sha256.compression_chain_sound
#print axioms Phase17Sha256.preimage_digest_bound
#print axioms Phase17Sha256.selected_standard_vectors
#print axioms Phase17Sha256.selected_padding_edges
#print axioms Phase17Sha256.selected_hash_inventory
#print axioms Phase17Sha256.selected_ranking_digest
#print axioms Phase17Sha256.selected_grammar_digests
#print axioms Phase17Sha256.selected_program_digests
#print axioms Phase17Sha256.selected_feature_digests
#print axioms Phase17Sha256.selected_tie_digests
#print axioms Phase17Sha256.selected_freeze_digest
#print axioms Phase17Sha256.selected_learned_acceptance_bound
