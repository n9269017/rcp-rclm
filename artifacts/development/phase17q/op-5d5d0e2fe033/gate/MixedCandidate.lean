import RcpRclmFormalCoreV4
import Mathlib.Tactic
import Mathlib.Data.Finset.Card
import Mathlib.Data.Finset.Filter
import Mathlib
import RcpRclmFormalCoreV2.RCP.ClassicalFinite
import RcpRclmFormalCoreV2.RCP.QuantumDensity
import RcpRclmFormalCoreV3.Learned.Kernel

/- A typed projection of measured package components. FileRef digests are not
   a proof of physical-byte equality: the external verifier compares those bytes.
   Only a fixed pure interpretation of the frozen view is preserved. No complete
   learned or autonomous accepted step is constructed by these lemmas. -/
namespace Phase17LearnedBinding

open RcpRclmFormalCoreV2

structure FileRef where
  path : String
  size : Nat
  digest : String
  deriving DecidableEq

abbrev Image := List FileRef

abbrev RootState := RcpRclmFormalCoreV3.Learned.PackageState
  (List String) Image Image Image Image Image Image Image Image Image Image Image String

structure BoundState where
  package : RootState
  executionContext : Image
  packageHash : String

def frozenView (s : BoundState) : List Image :=
  [s.package.modelArchitecture, s.package.modelWeights, s.package.generator,
   s.package.planner, s.package.trainingPolicy, s.package.retrievalPolicy,
   s.package.memory, s.package.tokenizer, s.package.verificationPolicy,
   s.package.resourcePolicy, s.package.selfModel, s.executionContext]

def extend (s : BoundState) (key task packageHash : String) : BoundState :=
  { package := { s.package with
      base := s.package.base ++ [key]
      capabilityFrontier := insert task s.package.capabilityFrontier }
    executionContext := s.executionContext
    packageHash := packageHash }

theorem frozen_view_preserved (s : BoundState) (key task packageHash : String) :
    frozenView (extend s key task packageHash) = frozenView s := rfl

theorem fixed_interpretation_retained {Input Output : Type*}
    (interpret : List Image → Input → Output)
    (before after : BoundState) (same : frozenView after = frozenView before)
    (input : Input) :
    interpret (frozenView after) input = interpret (frozenView before) input := by
  rw [same]

theorem information_value_retained
    (information : List Image → ℝ) (before after : BoundState)
    (same : frozenView after = frozenView before) :
    information (frozenView after) = information (frozenView before) :=
  congrArg information same

/- This refers to the actual learned-root information field. The semantic
   interpretation binding is an explicit premise, NOT inferred from a hash. -/
theorem root_information_bound
    {Update BaseCertificate Protected ResidualIndex Task Generator Proposal PackageHash : Type*}
    [DecidableEq Task]
    {base : RCP.Kernel BoundState Update BaseCertificate Protected ResidualIndex}
    (learned : RcpRclmFormalCoreV3.Learned.FrontierKernel
      (Task := Task) (Generator := Generator) (Proposal := Proposal)
      (PackageHash := PackageHash) base)
    (state : BoundState) (candidate : RCP.Candidate BoundState Update)
    (information : List Image → ℝ)
    (binding : ∀ s, learned.informationValue s = information (frozenView s))
    (same : frozenView candidate.next = frozenView state) :
    learned.informationValue candidate.next ≤
      learned.informationValue state + learned.informationBudget state candidate := by
  rw [binding candidate.next, binding state, same]
  exact le_add_of_nonneg_right (learned.informationBudget_nonnegative state candidate)

theorem frontier_retained (s : BoundState) (key task packageHash : String) :
    s.package.capabilityFrontier ⊆ (extend s key task packageHash).package.capabilityFrontier := by
  intro t member
  change t ∈ insert task s.package.capabilityFrontier
  exact Finset.mem_insert_of_mem member

theorem frontier_grows (s : BoundState) (key task packageHash : String)
    (fresh : task ∉ s.package.capabilityFrontier) :
    s.package.capabilityFrontier.card < (extend s key task packageHash).package.capabilityFrontier.card := by
  change s.package.capabilityFrontier.card < (insert task s.package.capabilityFrontier).card
  rw [Finset.card_insert_of_notMem fresh]
  exact Nat.lt_succ_self _

end Phase17LearnedBinding

namespace Phase17LearnedBinding
set_option maxRecDepth 16384
set_option maxHeartbeats 4000000
-- Measured binding packet SHA256: beea315339dddd2863ff3c47067be1be38a04b23f66faa1fd513f36e046e3008
def observedBefore : BoundState :=
  { package :=
    { base := ["1b3e59ea732ae920aa4d272bf89d3cd3acb7930ff3d921459efda0f2888e0fc3", "40ddd0f569709b232e4d769b2b288d694705a4561ef039aae2781deca29581d6", "5dd1421b9968b2619b62416177c38a29898d05514db22440c2229ccd51679649", "7d98001be0bd64487cb44f7db6f741b3e0436eec4cc0c4b0d74f5e6f774f2c1a", "aedc8351d94932d37506d4d7b44fac9b1b40baf95d35f52bee726af598e7a5c2", "b1e1738eecfb2e51693f8aea51ff14a49d38787a26ea62ef81078b326a9a197f", "b558b30a69cfed7c0faa2157402ed7910269e29212cbb0d3354f02fe5e0c1aad", "ebb887e9009fdd02f1fc999cc900c47dee131970826c19bdc55a74b9c7cccd7e"]
      modelArchitecture := [⟨"base/model/architecture.json", 2682, "92f8ca31927af2f2baa2cdbb0070a73eade87d9b1ebe0c0e25665f384e75ba7c"⟩]
      modelWeights := [⟨"base/model/adapters/manifest.json", 40146, "cd29ddc339e6d761dc0c8f7f292ecd6ab97488560514253bc0c9442fbe1d3482"⟩, ⟨"base/model/adapters/tensors/adapter.layers.00.attn_output.A.i16le.bin", 5120, "0baf561aeb192113ce68ce363342f4a89997bf90729a8e441c7b980416731164"⟩, ⟨"base/model/adapters/tensors/adapter.layers.00.attn_output.B.i16le.bin", 5120, "6821935dc62822529f6f1ef01595066caf4b105736cc8b310cebb9f628fb433f"⟩, ⟨"base/model/adapters/tensors/adapter.layers.00.attn_qkv.A.i16le.bin", 5120, "5a07437b39bd7cf4d71c8bce410bcb4c53862fd3b7722674be4868a6b32a5c29"⟩, ⟨"base/model/adapters/tensors/adapter.layers.00.attn_qkv.B.i16le.bin", 15360, "0299f757a85a1aad6cbe1ad2b0eda925d8df667cd04e646af8917f65cbf24537"⟩, ⟨"base/model/adapters/tensors/adapter.layers.00.mlp_down.A.i16le.bin", 20480, "44b8c64f14cae5789a839425471801fd7f5765cc64abe19669287712a9d2dbcb"⟩, ⟨"base/model/adapters/tensors/adapter.layers.00.mlp_down.B.i16le.bin", 5120, "a11937f356a9b0ba592c82f5290bac8016cb33a3f9bc68d3490147c158ebb10d"⟩, ⟨"base/model/adapters/tensors/adapter.layers.00.mlp_gate.A.i16le.bin", 5120, "92b0310cf7a4606d502a976d2723ee77480388823ca3e73ebe89450a7335e1d9"⟩, ⟨"base/model/adapters/tensors/adapter.layers.00.mlp_gate.B.i16le.bin", 20480, "cc61635da46b2c9974335ea37e0b5fd660a5c8a42a89b271fa7ec2ac4b8b26f6"⟩, ⟨"base/model/adapters/tensors/adapter.layers.00.mlp_up.A.i16le.bin", 5120, "5d67769562ca9fac9cbd0bfcd6b248bdc03d1366f925d67a1b1370bc9772bd66"⟩, ⟨"base/model/adapters/tensors/adapter.layers.00.mlp_up.B.i16le.bin", 20480, "cc61635da46b2c9974335ea37e0b5fd660a5c8a42a89b271fa7ec2ac4b8b26f6"⟩, ⟨"base/model/adapters/tensors/adapter.layers.01.attn_output.A.i16le.bin", 5120, "afea522680ebee7f64b5c581ff3706f6c5a1d3fdf3852cd05d9e1ca91566febf"⟩, ⟨"base/model/adapters/tensors/adapter.layers.01.attn_output.B.i16le.bin", 5120, "a11937f356a9b0ba592c82f5290bac8016cb33a3f9bc68d3490147c158ebb10d"⟩, ⟨"base/model/adapters/tensors/adapter.layers.01.attn_qkv.A.i16le.bin", 5120, "0baf561aeb192113ce68ce363342f4a89997bf90729a8e441c7b980416731164"⟩, ⟨"base/model/adapters/tensors/adapter.layers.01.attn_qkv.B.i16le.bin", 15360, "0299f757a85a1aad6cbe1ad2b0eda925d8df667cd04e646af8917f65cbf24537"⟩, ⟨"base/model/adapters/tensors/adapter.layers.01.mlp_down.A.i16le.bin", 20480, "01126149b194d51ba3be40d7b35c2a6b6736ffa5d0af1dced91652816ba2a426"⟩, ⟨"base/model/adapters/tensors/adapter.layers.01.mlp_down.B.i16le.bin", 5120, "a11937f356a9b0ba592c82f5290bac8016cb33a3f9bc68d3490147c158ebb10d"⟩, ⟨"base/model/adapters/tensors/adapter.layers.01.mlp_gate.A.i16le.bin", 5120, "5d67769562ca9fac9cbd0bfcd6b248bdc03d1366f925d67a1b1370bc9772bd66"⟩, ⟨"base/model/adapters/tensors/adapter.layers.01.mlp_gate.B.i16le.bin", 20480, "cc61635da46b2c9974335ea37e0b5fd660a5c8a42a89b271fa7ec2ac4b8b26f6"⟩, ⟨"base/model/adapters/tensors/adapter.layers.01.mlp_up.A.i16le.bin", 5120, "dfe43ccfb05c9ebe703ed7ec1694db527220c58a3299bdbc7a3eb98e46de5dc0"⟩, ⟨"base/model/adapters/tensors/adapter.layers.01.mlp_up.B.i16le.bin", 20480, "cc61635da46b2c9974335ea37e0b5fd660a5c8a42a89b271fa7ec2ac4b8b26f6"⟩, ⟨"base/model/adapters/tensors/adapter.layers.02.attn_output.A.i16le.bin", 5120, "f24ac9956dcbca570f297083a40eef635e16453bba7c3ba69b625970d545dbc6"⟩, ⟨"base/model/adapters/tensors/adapter.layers.02.attn_output.B.i16le.bin", 5120, "a11937f356a9b0ba592c82f5290bac8016cb33a3f9bc68d3490147c158ebb10d"⟩, ⟨"base/model/adapters/tensors/adapter.layers.02.attn_qkv.A.i16le.bin", 5120, "afea522680ebee7f64b5c581ff3706f6c5a1d3fdf3852cd05d9e1ca91566febf"⟩, ⟨"base/model/adapters/tensors/adapter.layers.02.attn_qkv.B.i16le.bin", 15360, "0299f757a85a1aad6cbe1ad2b0eda925d8df667cd04e646af8917f65cbf24537"⟩, ⟨"base/model/adapters/tensors/adapter.layers.02.mlp_down.A.i16le.bin", 20480, "7c56c2606dab85ace8f632ce8fb4a8477cc7fc67d92170db22649eb52741ba79"⟩, ⟨"base/model/adapters/tensors/adapter.layers.02.mlp_down.B.i16le.bin", 5120, "a11937f356a9b0ba592c82f5290bac8016cb33a3f9bc68d3490147c158ebb10d"⟩, ⟨"base/model/adapters/tensors/adapter.layers.02.mlp_gate.A.i16le.bin", 5120, "dfe43ccfb05c9ebe703ed7ec1694db527220c58a3299bdbc7a3eb98e46de5dc0"⟩, ⟨"base/model/adapters/tensors/adapter.layers.02.mlp_gate.B.i16le.bin", 20480, "cc61635da46b2c9974335ea37e0b5fd660a5c8a42a89b271fa7ec2ac4b8b26f6"⟩, ⟨"base/model/adapters/tensors/adapter.layers.02.mlp_up.A.i16le.bin", 5120, "5a07437b39bd7cf4d71c8bce410bcb4c53862fd3b7722674be4868a6b32a5c29"⟩, ⟨"base/model/adapters/tensors/adapter.layers.02.mlp_up.B.i16le.bin", 20480, "cc61635da46b2c9974335ea37e0b5fd660a5c8a42a89b271fa7ec2ac4b8b26f6"⟩, ⟨"base/model/adapters/tensors/adapter.layers.03.attn_output.A.i16le.bin", 5120, "92b0310cf7a4606d502a976d2723ee77480388823ca3e73ebe89450a7335e1d9"⟩, ⟨"base/model/adapters/tensors/adapter.layers.03.attn_output.B.i16le.bin", 5120, "a11937f356a9b0ba592c82f5290bac8016cb33a3f9bc68d3490147c158ebb10d"⟩, ⟨"base/model/adapters/tensors/adapter.layers.03.attn_qkv.A.i16le.bin", 5120, "f24ac9956dcbca570f297083a40eef635e16453bba7c3ba69b625970d545dbc6"⟩, ⟨"base/model/adapters/tensors/adapter.layers.03.attn_qkv.B.i16le.bin", 15360, "0299f757a85a1aad6cbe1ad2b0eda925d8df667cd04e646af8917f65cbf24537"⟩, ⟨"base/model/adapters/tensors/adapter.layers.03.mlp_down.A.i16le.bin", 20480, "d369d41d0a7c78dba82147c97dfa99b0c055aea8c282ee9e211f5033316737d3"⟩, ⟨"base/model/adapters/tensors/adapter.layers.03.mlp_down.B.i16le.bin", 5120, "a11937f356a9b0ba592c82f5290bac8016cb33a3f9bc68d3490147c158ebb10d"⟩, ⟨"base/model/adapters/tensors/adapter.layers.03.mlp_gate.A.i16le.bin", 5120, "5a07437b39bd7cf4d71c8bce410bcb4c53862fd3b7722674be4868a6b32a5c29"⟩, ⟨"base/model/adapters/tensors/adapter.layers.03.mlp_gate.B.i16le.bin", 20480, "cc61635da46b2c9974335ea37e0b5fd660a5c8a42a89b271fa7ec2ac4b8b26f6"⟩, ⟨"base/model/adapters/tensors/adapter.layers.03.mlp_up.A.i16le.bin", 5120, "0baf561aeb192113ce68ce363342f4a89997bf90729a8e441c7b980416731164"⟩, ⟨"base/model/adapters/tensors/adapter.layers.03.mlp_up.B.i16le.bin", 20480, "cc61635da46b2c9974335ea37e0b5fd660a5c8a42a89b271fa7ec2ac4b8b26f6"⟩, ⟨"base/model/adapters/tensors/adapter.layers.04.attn_output.A.i16le.bin", 5120, "5d67769562ca9fac9cbd0bfcd6b248bdc03d1366f925d67a1b1370bc9772bd66"⟩, ⟨"base/model/adapters/tensors/adapter.layers.04.attn_output.B.i16le.bin", 5120, "a11937f356a9b0ba592c82f5290bac8016cb33a3f9bc68d3490147c158ebb10d"⟩, ⟨"base/model/adapters/tensors/adapter.layers.04.attn_qkv.A.i16le.bin", 5120, "92b0310cf7a4606d502a976d2723ee77480388823ca3e73ebe89450a7335e1d9"⟩, ⟨"base/model/adapters/tensors/adapter.layers.04.attn_qkv.B.i16le.bin", 15360, "0299f757a85a1aad6cbe1ad2b0eda925d8df667cd04e646af8917f65cbf24537"⟩, ⟨"base/model/adapters/tensors/adapter.layers.04.mlp_down.A.i16le.bin", 20480, "8be2c803d295ad5b300987f3e4bef0c2e6946b296895703b73502b5e9b760cb0"⟩, ⟨"base/model/adapters/tensors/adapter.layers.04.mlp_down.B.i16le.bin", 5120, "a11937f356a9b0ba592c82f5290bac8016cb33a3f9bc68d3490147c158ebb10d"⟩, ⟨"base/model/adapters/tensors/adapter.layers.04.mlp_gate.A.i16le.bin", 5120, "0baf561aeb192113ce68ce363342f4a89997bf90729a8e441c7b980416731164"⟩, ⟨"base/model/adapters/tensors/adapter.layers.04.mlp_gate.B.i16le.bin", 20480, "cc61635da46b2c9974335ea37e0b5fd660a5c8a42a89b271fa7ec2ac4b8b26f6"⟩, ⟨"base/model/adapters/tensors/adapter.layers.04.mlp_up.A.i16le.bin", 5120, "afea522680ebee7f64b5c581ff3706f6c5a1d3fdf3852cd05d9e1ca91566febf"⟩, ⟨"base/model/adapters/tensors/adapter.layers.04.mlp_up.B.i16le.bin", 20480, "cc61635da46b2c9974335ea37e0b5fd660a5c8a42a89b271fa7ec2ac4b8b26f6"⟩, ⟨"base/model/adapters/tensors/adapter.layers.05.attn_output.A.i16le.bin", 5120, "dfe43ccfb05c9ebe703ed7ec1694db527220c58a3299bdbc7a3eb98e46de5dc0"⟩, ⟨"base/model/adapters/tensors/adapter.layers.05.attn_output.B.i16le.bin", 5120, "a11937f356a9b0ba592c82f5290bac8016cb33a3f9bc68d3490147c158ebb10d"⟩, ⟨"base/model/adapters/tensors/adapter.layers.05.attn_qkv.A.i16le.bin", 5120, "5d67769562ca9fac9cbd0bfcd6b248bdc03d1366f925d67a1b1370bc9772bd66"⟩, ⟨"base/model/adapters/tensors/adapter.layers.05.attn_qkv.B.i16le.bin", 15360, "0299f757a85a1aad6cbe1ad2b0eda925d8df667cd04e646af8917f65cbf24537"⟩, ⟨"base/model/adapters/tensors/adapter.layers.05.mlp_down.A.i16le.bin", 20480, "2f04593443b343351655e4782e08305cce64cfe3c2cb227853d8889266914564"⟩, ⟨"base/model/adapters/tensors/adapter.layers.05.mlp_down.B.i16le.bin", 5120, "a11937f356a9b0ba592c82f5290bac8016cb33a3f9bc68d3490147c158ebb10d"⟩, ⟨"base/model/adapters/tensors/adapter.layers.05.mlp_gate.A.i16le.bin", 5120, "afea522680ebee7f64b5c581ff3706f6c5a1d3fdf3852cd05d9e1ca91566febf"⟩, ⟨"base/model/adapters/tensors/adapter.layers.05.mlp_gate.B.i16le.bin", 20480, "cc61635da46b2c9974335ea37e0b5fd660a5c8a42a89b271fa7ec2ac4b8b26f6"⟩, ⟨"base/model/adapters/tensors/adapter.layers.05.mlp_up.A.i16le.bin", 5120, "f24ac9956dcbca570f297083a40eef635e16453bba7c3ba69b625970d545dbc6"⟩, ⟨"base/model/adapters/tensors/adapter.layers.05.mlp_up.B.i16le.bin", 20480, "cc61635da46b2c9974335ea37e0b5fd660a5c8a42a89b271fa7ec2ac4b8b26f6"⟩, ⟨"base/model/adapters/tensors/adapter.layers.06.attn_output.A.i16le.bin", 5120, "5a07437b39bd7cf4d71c8bce410bcb4c53862fd3b7722674be4868a6b32a5c29"⟩, ⟨"base/model/adapters/tensors/adapter.layers.06.attn_output.B.i16le.bin", 5120, "a11937f356a9b0ba592c82f5290bac8016cb33a3f9bc68d3490147c158ebb10d"⟩, ⟨"base/model/adapters/tensors/adapter.layers.06.attn_qkv.A.i16le.bin", 5120, "dfe43ccfb05c9ebe703ed7ec1694db527220c58a3299bdbc7a3eb98e46de5dc0"⟩, ⟨"base/model/adapters/tensors/adapter.layers.06.attn_qkv.B.i16le.bin", 15360, "0299f757a85a1aad6cbe1ad2b0eda925d8df667cd04e646af8917f65cbf24537"⟩, ⟨"base/model/adapters/tensors/adapter.layers.06.mlp_down.A.i16le.bin", 20480, "7a1f4b14a0b3ab192781ccbc4300aa7629711fbd00094d9b713cd3c724fc0309"⟩, ⟨"base/model/adapters/tensors/adapter.layers.06.mlp_down.B.i16le.bin", 5120, "a11937f356a9b0ba592c82f5290bac8016cb33a3f9bc68d3490147c158ebb10d"⟩, ⟨"base/model/adapters/tensors/adapter.layers.06.mlp_gate.A.i16le.bin", 5120, "f24ac9956dcbca570f297083a40eef635e16453bba7c3ba69b625970d545dbc6"⟩, ⟨"base/model/adapters/tensors/adapter.layers.06.mlp_gate.B.i16le.bin", 20480, "cc61635da46b2c9974335ea37e0b5fd660a5c8a42a89b271fa7ec2ac4b8b26f6"⟩, ⟨"base/model/adapters/tensors/adapter.layers.06.mlp_up.A.i16le.bin", 5120, "92b0310cf7a4606d502a976d2723ee77480388823ca3e73ebe89450a7335e1d9"⟩, ⟨"base/model/adapters/tensors/adapter.layers.06.mlp_up.B.i16le.bin", 20480, "cc61635da46b2c9974335ea37e0b5fd660a5c8a42a89b271fa7ec2ac4b8b26f6"⟩, ⟨"base/model/adapters/tensors/adapter.layers.07.attn_output.A.i16le.bin", 5120, "0baf561aeb192113ce68ce363342f4a89997bf90729a8e441c7b980416731164"⟩, ⟨"base/model/adapters/tensors/adapter.layers.07.attn_output.B.i16le.bin", 5120, "a11937f356a9b0ba592c82f5290bac8016cb33a3f9bc68d3490147c158ebb10d"⟩, ⟨"base/model/adapters/tensors/adapter.layers.07.attn_qkv.A.i16le.bin", 5120, "5a07437b39bd7cf4d71c8bce410bcb4c53862fd3b7722674be4868a6b32a5c29"⟩, ⟨"base/model/adapters/tensors/adapter.layers.07.attn_qkv.B.i16le.bin", 15360, "0299f757a85a1aad6cbe1ad2b0eda925d8df667cd04e646af8917f65cbf24537"⟩, ⟨"base/model/adapters/tensors/adapter.layers.07.mlp_down.A.i16le.bin", 20480, "44b8c64f14cae5789a839425471801fd7f5765cc64abe19669287712a9d2dbcb"⟩, ⟨"base/model/adapters/tensors/adapter.layers.07.mlp_down.B.i16le.bin", 5120, "a11937f356a9b0ba592c82f5290bac8016cb33a3f9bc68d3490147c158ebb10d"⟩, ⟨"base/model/adapters/tensors/adapter.layers.07.mlp_gate.A.i16le.bin", 5120, "92b0310cf7a4606d502a976d2723ee77480388823ca3e73ebe89450a7335e1d9"⟩, ⟨"base/model/adapters/tensors/adapter.layers.07.mlp_gate.B.i16le.bin", 20480, "cc61635da46b2c9974335ea37e0b5fd660a5c8a42a89b271fa7ec2ac4b8b26f6"⟩, ⟨"base/model/adapters/tensors/adapter.layers.07.mlp_up.A.i16le.bin", 5120, "5d67769562ca9fac9cbd0bfcd6b248bdc03d1366f925d67a1b1370bc9772bd66"⟩, ⟨"base/model/adapters/tensors/adapter.layers.07.mlp_up.B.i16le.bin", 20480, "cc61635da46b2c9974335ea37e0b5fd660a5c8a42a89b271fa7ec2ac4b8b26f6"⟩, ⟨"base/model/tensors/manifest.json", 28234, "2164a2a3f64b3bbc9fb9f2ee14e3d15c0b9e66d548ede35065eeecf197f3b67f"⟩, ⟨"base/model/tensors/model.final_norm.weight.i16le.bin", 640, "f5aa5f72368b94c814f7ff12bc1d180d6296397628db16411765a9e713b12f3e"⟩, ⟨"base/model/tensors/model.layers.00.attn_norm.weight.i16le.bin", 640, "f5aa5f72368b94c814f7ff12bc1d180d6296397628db16411765a9e713b12f3e"⟩, ⟨"base/model/tensors/model.layers.00.attn_output.weight.i16le.bin", 204800, "63dd072a4aa0579d17890848d0b9948aabad4d6f9a47fa58868f4572b5e91c7c"⟩, ⟨"base/model/tensors/model.layers.00.attn_qkv.weight.i16le.bin", 614400, "171f38ece7178195cde6d203fed2907ac1f8ca7c1787322ad1674f3b7e9d2f0a"⟩, ⟨"base/model/tensors/model.layers.00.mlp_down.weight.i16le.bin", 819200, "dce79b8fea025a282b35a56f716c4766ca2949f23c30630060db91814710f4f5"⟩, ⟨"base/model/tensors/model.layers.00.mlp_gate.weight.i16le.bin", 819200, "dce79b8fea025a282b35a56f716c4766ca2949f23c30630060db91814710f4f5"⟩, ⟨"base/model/tensors/model.layers.00.mlp_norm.weight.i16le.bin", 640, "f5aa5f72368b94c814f7ff12bc1d180d6296397628db16411765a9e713b12f3e"⟩, ⟨"base/model/tensors/model.layers.00.mlp_up.weight.i16le.bin", 819200, "dce79b8fea025a282b35a56f716c4766ca2949f23c30630060db91814710f4f5"⟩, ⟨"base/model/tensors/model.layers.01.attn_norm.weight.i16le.bin", 640, "f5aa5f72368b94c814f7ff12bc1d180d6296397628db16411765a9e713b12f3e"⟩, ⟨"base/model/tensors/model.layers.01.attn_output.weight.i16le.bin", 204800, "8eafc7bd411c1f02b9e972a83d2b0a4164eefc5ef51e6b63ad7acc78be4ad44f"⟩, ⟨"base/model/tensors/model.layers.01.attn_qkv.weight.i16le.bin", 614400, "34c69899504b36f13e8b22120cf0fd894e61fcd6b046fb8535b79cc491fa3b3f"⟩, ⟨"base/model/tensors/model.layers.01.mlp_down.weight.i16le.bin", 819200, "dce79b8fea025a282b35a56f716c4766ca2949f23c30630060db91814710f4f5"⟩, ⟨"base/model/tensors/model.layers.01.mlp_gate.weight.i16le.bin", 819200, "dce79b8fea025a282b35a56f716c4766ca2949f23c30630060db91814710f4f5"⟩, ⟨"base/model/tensors/model.layers.01.mlp_norm.weight.i16le.bin", 640, "f5aa5f72368b94c814f7ff12bc1d180d6296397628db16411765a9e713b12f3e"⟩, ⟨"base/model/tensors/model.layers.01.mlp_up.weight.i16le.bin", 819200, "dce79b8fea025a282b35a56f716c4766ca2949f23c30630060db91814710f4f5"⟩, ⟨"base/model/tensors/model.layers.02.attn_norm.weight.i16le.bin", 640, "f5aa5f72368b94c814f7ff12bc1d180d6296397628db16411765a9e713b12f3e"⟩, ⟨"base/model/tensors/model.layers.02.attn_output.weight.i16le.bin", 204800, "8eafc7bd411c1f02b9e972a83d2b0a4164eefc5ef51e6b63ad7acc78be4ad44f"⟩, ⟨"base/model/tensors/model.layers.02.attn_qkv.weight.i16le.bin", 614400, "34c69899504b36f13e8b22120cf0fd894e61fcd6b046fb8535b79cc491fa3b3f"⟩, ⟨"base/model/tensors/model.layers.02.mlp_down.weight.i16le.bin", 819200, "dce79b8fea025a282b35a56f716c4766ca2949f23c30630060db91814710f4f5"⟩, ⟨"base/model/tensors/model.layers.02.mlp_gate.weight.i16le.bin", 819200, "dce79b8fea025a282b35a56f716c4766ca2949f23c30630060db91814710f4f5"⟩, ⟨"base/model/tensors/model.layers.02.mlp_norm.weight.i16le.bin", 640, "f5aa5f72368b94c814f7ff12bc1d180d6296397628db16411765a9e713b12f3e"⟩, ⟨"base/model/tensors/model.layers.02.mlp_up.weight.i16le.bin", 819200, "dce79b8fea025a282b35a56f716c4766ca2949f23c30630060db91814710f4f5"⟩, ⟨"base/model/tensors/model.layers.03.attn_norm.weight.i16le.bin", 640, "f5aa5f72368b94c814f7ff12bc1d180d6296397628db16411765a9e713b12f3e"⟩, ⟨"base/model/tensors/model.layers.03.attn_output.weight.i16le.bin", 204800, "8eafc7bd411c1f02b9e972a83d2b0a4164eefc5ef51e6b63ad7acc78be4ad44f"⟩, ⟨"base/model/tensors/model.layers.03.attn_qkv.weight.i16le.bin", 614400, "34c69899504b36f13e8b22120cf0fd894e61fcd6b046fb8535b79cc491fa3b3f"⟩, ⟨"base/model/tensors/model.layers.03.mlp_down.weight.i16le.bin", 819200, "dce79b8fea025a282b35a56f716c4766ca2949f23c30630060db91814710f4f5"⟩, ⟨"base/model/tensors/model.layers.03.mlp_gate.weight.i16le.bin", 819200, "dce79b8fea025a282b35a56f716c4766ca2949f23c30630060db91814710f4f5"⟩, ⟨"base/model/tensors/model.layers.03.mlp_norm.weight.i16le.bin", 640, "f5aa5f72368b94c814f7ff12bc1d180d6296397628db16411765a9e713b12f3e"⟩, ⟨"base/model/tensors/model.layers.03.mlp_up.weight.i16le.bin", 819200, "dce79b8fea025a282b35a56f716c4766ca2949f23c30630060db91814710f4f5"⟩, ⟨"base/model/tensors/model.layers.04.attn_norm.weight.i16le.bin", 640, "f5aa5f72368b94c814f7ff12bc1d180d6296397628db16411765a9e713b12f3e"⟩, ⟨"base/model/tensors/model.layers.04.attn_output.weight.i16le.bin", 204800, "8eafc7bd411c1f02b9e972a83d2b0a4164eefc5ef51e6b63ad7acc78be4ad44f"⟩, ⟨"base/model/tensors/model.layers.04.attn_qkv.weight.i16le.bin", 614400, "34c69899504b36f13e8b22120cf0fd894e61fcd6b046fb8535b79cc491fa3b3f"⟩, ⟨"base/model/tensors/model.layers.04.mlp_down.weight.i16le.bin", 819200, "dce79b8fea025a282b35a56f716c4766ca2949f23c30630060db91814710f4f5"⟩, ⟨"base/model/tensors/model.layers.04.mlp_gate.weight.i16le.bin", 819200, "dce79b8fea025a282b35a56f716c4766ca2949f23c30630060db91814710f4f5"⟩, ⟨"base/model/tensors/model.layers.04.mlp_norm.weight.i16le.bin", 640, "f5aa5f72368b94c814f7ff12bc1d180d6296397628db16411765a9e713b12f3e"⟩, ⟨"base/model/tensors/model.layers.04.mlp_up.weight.i16le.bin", 819200, "dce79b8fea025a282b35a56f716c4766ca2949f23c30630060db91814710f4f5"⟩, ⟨"base/model/tensors/model.layers.05.attn_norm.weight.i16le.bin", 640, "f5aa5f72368b94c814f7ff12bc1d180d6296397628db16411765a9e713b12f3e"⟩, ⟨"base/model/tensors/model.layers.05.attn_output.weight.i16le.bin", 204800, "8eafc7bd411c1f02b9e972a83d2b0a4164eefc5ef51e6b63ad7acc78be4ad44f"⟩, ⟨"base/model/tensors/model.layers.05.attn_qkv.weight.i16le.bin", 614400, "34c69899504b36f13e8b22120cf0fd894e61fcd6b046fb8535b79cc491fa3b3f"⟩, ⟨"base/model/tensors/model.layers.05.mlp_down.weight.i16le.bin", 819200, "dce79b8fea025a282b35a56f716c4766ca2949f23c30630060db91814710f4f5"⟩, ⟨"base/model/tensors/model.layers.05.mlp_gate.weight.i16le.bin", 819200, "dce79b8fea025a282b35a56f716c4766ca2949f23c30630060db91814710f4f5"⟩, ⟨"base/model/tensors/model.layers.05.mlp_norm.weight.i16le.bin", 640, "f5aa5f72368b94c814f7ff12bc1d180d6296397628db16411765a9e713b12f3e"⟩, ⟨"base/model/tensors/model.layers.05.mlp_up.weight.i16le.bin", 819200, "dce79b8fea025a282b35a56f716c4766ca2949f23c30630060db91814710f4f5"⟩, ⟨"base/model/tensors/model.layers.06.attn_norm.weight.i16le.bin", 640, "f5aa5f72368b94c814f7ff12bc1d180d6296397628db16411765a9e713b12f3e"⟩, ⟨"base/model/tensors/model.layers.06.attn_output.weight.i16le.bin", 204800, "8eafc7bd411c1f02b9e972a83d2b0a4164eefc5ef51e6b63ad7acc78be4ad44f"⟩, ⟨"base/model/tensors/model.layers.06.attn_qkv.weight.i16le.bin", 614400, "34c69899504b36f13e8b22120cf0fd894e61fcd6b046fb8535b79cc491fa3b3f"⟩, ⟨"base/model/tensors/model.layers.06.mlp_down.weight.i16le.bin", 819200, "dce79b8fea025a282b35a56f716c4766ca2949f23c30630060db91814710f4f5"⟩, ⟨"base/model/tensors/model.layers.06.mlp_gate.weight.i16le.bin", 819200, "dce79b8fea025a282b35a56f716c4766ca2949f23c30630060db91814710f4f5"⟩, ⟨"base/model/tensors/model.layers.06.mlp_norm.weight.i16le.bin", 640, "f5aa5f72368b94c814f7ff12bc1d180d6296397628db16411765a9e713b12f3e"⟩, ⟨"base/model/tensors/model.layers.06.mlp_up.weight.i16le.bin", 819200, "dce79b8fea025a282b35a56f716c4766ca2949f23c30630060db91814710f4f5"⟩, ⟨"base/model/tensors/model.layers.07.attn_norm.weight.i16le.bin", 640, "f5aa5f72368b94c814f7ff12bc1d180d6296397628db16411765a9e713b12f3e"⟩, ⟨"base/model/tensors/model.layers.07.attn_output.weight.i16le.bin", 204800, "8eafc7bd411c1f02b9e972a83d2b0a4164eefc5ef51e6b63ad7acc78be4ad44f"⟩, ⟨"base/model/tensors/model.layers.07.attn_qkv.weight.i16le.bin", 614400, "34c69899504b36f13e8b22120cf0fd894e61fcd6b046fb8535b79cc491fa3b3f"⟩, ⟨"base/model/tensors/model.layers.07.mlp_down.weight.i16le.bin", 819200, "dce79b8fea025a282b35a56f716c4766ca2949f23c30630060db91814710f4f5"⟩, ⟨"base/model/tensors/model.layers.07.mlp_gate.weight.i16le.bin", 819200, "dce79b8fea025a282b35a56f716c4766ca2949f23c30630060db91814710f4f5"⟩, ⟨"base/model/tensors/model.layers.07.mlp_norm.weight.i16le.bin", 640, "f5aa5f72368b94c814f7ff12bc1d180d6296397628db16411765a9e713b12f3e"⟩, ⟨"base/model/tensors/model.layers.07.mlp_up.weight.i16le.bin", 819200, "dce79b8fea025a282b35a56f716c4766ca2949f23c30630060db91814710f4f5"⟩, ⟨"base/model/tensors/model.token_embedding.weight.i16le.bin", 166400, "7716b6b19f19f6663a9f9c583b075c802889ce9206161b80d8741c49204fa9df"⟩]
      generator := [⟨"base/policies/generator_policy.json", 1851, "4aa9045b8ef05f1a5183cd078d1af0bcf3c92642faf0a9e34b09988ef5d623ec"⟩]
      planner := [⟨"base/model/phase15_planner/manifest.json", 975, "1439cb69b09d4d0b637c9b2a62172f4150f79bd57d0d52a813ef4435544c9ea9"⟩, ⟨"base/model/phase15_planner/public_curriculum.json", 16469, "c55a0ba69705faa4c75ee898b3c1f2195af3cf9fee358058fdaff8609d07bbc2"⟩, ⟨"base/model/phase15_planner/training_report.json", 650, "b0a7988383b27ad4c90b7abd411bc8461ce2fe47ebb5620416cac91f5b7471a5"⟩, ⟨"base/model/phase15_planner/vocabulary.json", 1157, "6ca846c992da7211397e07c8dab8775d01bbae465702311dcd276ee15aad0e9d"⟩, ⟨"base/model/phase15_planner/weights.i16le.bin", 65536, "19869eac5b0da770505214a6c5817b94dfda05730f97598bf2f855aff82d6c8d"⟩, ⟨"base/policies/planner_policy.json", 1955, "a585835e42d7bb47d047b24f8635f9e121410d0993e276dbdc77975d987b15fb"⟩]
      trainingPolicy := [⟨"base/training/data_curriculum.json", 468, "92a8e5d12e0ae7607b6f8547967c102681cc3cc2cf86a502f90aa45cfc6518e4"⟩, ⟨"base/training/optimizer_state.json", 1490, "1f046614c26415b1e0c77455bd32471a115ea354838a83789ade143781219637"⟩, ⟨"base/training/training_policy.json", 624, "9bddc0e826638f55f03dbaeb397dd6c1c97640c66f5839429bc8ce216ccc27f9"⟩]
      retrievalPolicy := [⟨"base/retrieval/index_manifest.json", 1368, "1f797fadc3d97eb5fb806a6e6332d0b85728d754dda68605e180b2dc33759738"⟩]
      memory := [⟨"base/memory/memory_manifest.json", 1293, "4c63a3c8199fdfd1e48dac688851c114a6a3dcc7d5446ac492225bae736bd9d5"⟩]
      tokenizer := [⟨"base/model/tokenizer/manifest.json", 463, "02189aacaca473e404291d41c29eeb3d8e9a0984ec9619194b3c6e89ec7d6414"⟩, ⟨"base/model/tokenizer/tokenizer.bin", 316, "b1eec973c9555f094f0ed805ab37b0ecac4cb3a7defba23d99ddc38ed5383d7d"⟩, ⟨"base/model/tokenizer/vocabulary.json", 10897, "61b8c71667b30ef6a0ea6b2186cd87b62bf53765e4aef755615ee50f63242dc5"⟩]
      verificationPolicy := [⟨"base/policies/verification_policy.json", 397, "64ece32b682cfe651db19fe80f8704aa45c3117fb83b6da6d954589773e19eea"⟩]
      resourcePolicy := [⟨"base/policies/resource_policy.json", 628, "1376fbf29c808c8f15ea97b7061d116f3a40193e31799c9401ffdb47cc1d77ee"⟩]
      selfModel := [⟨"base/self_model/manifest.json", 506, "32032a4ed4150482747c8b5f6882acec586c9ee07ac3caa48a204675abbeb8b0"⟩]
      capabilityFrontier := (["lean.phase10.heldout.linear_gap", "lean.phase10.protected.reflexive_seven", "lean.phase11.heldout.add_zero_macro", "lean.phase12.generation1.le_refl_macro", "lean.phase12.generation2.zero_le_macro", "lean.phase12.generation3.lt_succ_planner_macro", "lean.phase12.generation4.lt_add_two_adapter_macro", "lean.phase14.generation5_zero_lt_succ", "lean.phase14.generation6_lt_add_five", "lean.phase14.generation7_succ_le_add_two", "lean.phase14.generation8_le_add_four", "lean.phase15.dynamic.multistep.4a7a415bcd169bb8", "phase16.dynamic.adapter_policy.2624594ed996371dbea9", "phase16.dynamic.architecture_policy.c3cd1f252d113cb41ebc", "phase16.dynamic.memory_policy.f9734b7e402fa0a0e992", "phase16.dynamic.optimizer_policy.10a54f6a7c3503fa7430", "phase16.dynamic.planner_policy.e8a5ef052b4885132a71", "phase16.dynamic.retrieval_policy.376f6d7a4130a978e1e6", "phase16.dynamic.tool_policy.231b912e39ff91bade12", "phase16.dynamic.verification_automation_policy.4290be408ad83beccf87", "program.phase15.dynamic.affine.beb80dc125251a70"] : List String).toFinset }
    executionContext := [⟨"base/package_manifest.json", 2387, "d7679bf5a96baf19616c0a6a15b2f295580a4c47231acba39ad926e951efde6b"⟩, ⟨"base/policies/tool_policy.json", 561, "f8820ca3cded0e9c478e0c495df4bbee69d9af3fee389393049b2372fe87bd16"⟩, ⟨"base/runtime/environment.json", 179, "fc9d81f7e64b2e47c5ff3158945f602e4f31227c39ee8555acdc71897a0c28e1"⟩, ⟨"base/runtime/resource_measurement.json", 1015, "d8bd3ab1e5564cdd794644dbe97b5b340237c2b0e0533284a767958cf1fe5543"⟩, ⟨"base/runtime/rng_state.json", 169, "e638f51b37390af36ac358b25faeb927a5bc87722a73b0609ba338ae66030ff1"⟩]
    packageHash := "6759cc828b5b8cb4af041e32dcba7b136849591e793802ab7f1f1cc2f2bcd535" }
def observedAfter : BoundState :=
  { package :=
    { base := ["1b3e59ea732ae920aa4d272bf89d3cd3acb7930ff3d921459efda0f2888e0fc3", "40ddd0f569709b232e4d769b2b288d694705a4561ef039aae2781deca29581d6", "5dd1421b9968b2619b62416177c38a29898d05514db22440c2229ccd51679649", "7d98001be0bd64487cb44f7db6f741b3e0436eec4cc0c4b0d74f5e6f774f2c1a", "aedc8351d94932d37506d4d7b44fac9b1b40baf95d35f52bee726af598e7a5c2", "b1e1738eecfb2e51693f8aea51ff14a49d38787a26ea62ef81078b326a9a197f", "b558b30a69cfed7c0faa2157402ed7910269e29212cbb0d3354f02fe5e0c1aad", "ebb887e9009fdd02f1fc999cc900c47dee131970826c19bdc55a74b9c7cccd7e", "a4f37fb8f2f7d3a90829340f2f02b2f19dbc5dfa5caf7a7633e9092837265c0e"]
      modelArchitecture := [⟨"base/model/architecture.json", 2682, "92f8ca31927af2f2baa2cdbb0070a73eade87d9b1ebe0c0e25665f384e75ba7c"⟩]
      modelWeights := [⟨"base/model/adapters/manifest.json", 40146, "cd29ddc339e6d761dc0c8f7f292ecd6ab97488560514253bc0c9442fbe1d3482"⟩, ⟨"base/model/adapters/tensors/adapter.layers.00.attn_output.A.i16le.bin", 5120, "0baf561aeb192113ce68ce363342f4a89997bf90729a8e441c7b980416731164"⟩, ⟨"base/model/adapters/tensors/adapter.layers.00.attn_output.B.i16le.bin", 5120, "6821935dc62822529f6f1ef01595066caf4b105736cc8b310cebb9f628fb433f"⟩, ⟨"base/model/adapters/tensors/adapter.layers.00.attn_qkv.A.i16le.bin", 5120, "5a07437b39bd7cf4d71c8bce410bcb4c53862fd3b7722674be4868a6b32a5c29"⟩, ⟨"base/model/adapters/tensors/adapter.layers.00.attn_qkv.B.i16le.bin", 15360, "0299f757a85a1aad6cbe1ad2b0eda925d8df667cd04e646af8917f65cbf24537"⟩, ⟨"base/model/adapters/tensors/adapter.layers.00.mlp_down.A.i16le.bin", 20480, "44b8c64f14cae5789a839425471801fd7f5765cc64abe19669287712a9d2dbcb"⟩, ⟨"base/model/adapters/tensors/adapter.layers.00.mlp_down.B.i16le.bin", 5120, "a11937f356a9b0ba592c82f5290bac8016cb33a3f9bc68d3490147c158ebb10d"⟩, ⟨"base/model/adapters/tensors/adapter.layers.00.mlp_gate.A.i16le.bin", 5120, "92b0310cf7a4606d502a976d2723ee77480388823ca3e73ebe89450a7335e1d9"⟩, ⟨"base/model/adapters/tensors/adapter.layers.00.mlp_gate.B.i16le.bin", 20480, "cc61635da46b2c9974335ea37e0b5fd660a5c8a42a89b271fa7ec2ac4b8b26f6"⟩, ⟨"base/model/adapters/tensors/adapter.layers.00.mlp_up.A.i16le.bin", 5120, "5d67769562ca9fac9cbd0bfcd6b248bdc03d1366f925d67a1b1370bc9772bd66"⟩, ⟨"base/model/adapters/tensors/adapter.layers.00.mlp_up.B.i16le.bin", 20480, "cc61635da46b2c9974335ea37e0b5fd660a5c8a42a89b271fa7ec2ac4b8b26f6"⟩, ⟨"base/model/adapters/tensors/adapter.layers.01.attn_output.A.i16le.bin", 5120, "afea522680ebee7f64b5c581ff3706f6c5a1d3fdf3852cd05d9e1ca91566febf"⟩, ⟨"base/model/adapters/tensors/adapter.layers.01.attn_output.B.i16le.bin", 5120, "a11937f356a9b0ba592c82f5290bac8016cb33a3f9bc68d3490147c158ebb10d"⟩, ⟨"base/model/adapters/tensors/adapter.layers.01.attn_qkv.A.i16le.bin", 5120, "0baf561aeb192113ce68ce363342f4a89997bf90729a8e441c7b980416731164"⟩, ⟨"base/model/adapters/tensors/adapter.layers.01.attn_qkv.B.i16le.bin", 15360, "0299f757a85a1aad6cbe1ad2b0eda925d8df667cd04e646af8917f65cbf24537"⟩, ⟨"base/model/adapters/tensors/adapter.layers.01.mlp_down.A.i16le.bin", 20480, "01126149b194d51ba3be40d7b35c2a6b6736ffa5d0af1dced91652816ba2a426"⟩, ⟨"base/model/adapters/tensors/adapter.layers.01.mlp_down.B.i16le.bin", 5120, "a11937f356a9b0ba592c82f5290bac8016cb33a3f9bc68d3490147c158ebb10d"⟩, ⟨"base/model/adapters/tensors/adapter.layers.01.mlp_gate.A.i16le.bin", 5120, "5d67769562ca9fac9cbd0bfcd6b248bdc03d1366f925d67a1b1370bc9772bd66"⟩, ⟨"base/model/adapters/tensors/adapter.layers.01.mlp_gate.B.i16le.bin", 20480, "cc61635da46b2c9974335ea37e0b5fd660a5c8a42a89b271fa7ec2ac4b8b26f6"⟩, ⟨"base/model/adapters/tensors/adapter.layers.01.mlp_up.A.i16le.bin", 5120, "dfe43ccfb05c9ebe703ed7ec1694db527220c58a3299bdbc7a3eb98e46de5dc0"⟩, ⟨"base/model/adapters/tensors/adapter.layers.01.mlp_up.B.i16le.bin", 20480, "cc61635da46b2c9974335ea37e0b5fd660a5c8a42a89b271fa7ec2ac4b8b26f6"⟩, ⟨"base/model/adapters/tensors/adapter.layers.02.attn_output.A.i16le.bin", 5120, "f24ac9956dcbca570f297083a40eef635e16453bba7c3ba69b625970d545dbc6"⟩, ⟨"base/model/adapters/tensors/adapter.layers.02.attn_output.B.i16le.bin", 5120, "a11937f356a9b0ba592c82f5290bac8016cb33a3f9bc68d3490147c158ebb10d"⟩, ⟨"base/model/adapters/tensors/adapter.layers.02.attn_qkv.A.i16le.bin", 5120, "afea522680ebee7f64b5c581ff3706f6c5a1d3fdf3852cd05d9e1ca91566febf"⟩, ⟨"base/model/adapters/tensors/adapter.layers.02.attn_qkv.B.i16le.bin", 15360, "0299f757a85a1aad6cbe1ad2b0eda925d8df667cd04e646af8917f65cbf24537"⟩, ⟨"base/model/adapters/tensors/adapter.layers.02.mlp_down.A.i16le.bin", 20480, "7c56c2606dab85ace8f632ce8fb4a8477cc7fc67d92170db22649eb52741ba79"⟩, ⟨"base/model/adapters/tensors/adapter.layers.02.mlp_down.B.i16le.bin", 5120, "a11937f356a9b0ba592c82f5290bac8016cb33a3f9bc68d3490147c158ebb10d"⟩, ⟨"base/model/adapters/tensors/adapter.layers.02.mlp_gate.A.i16le.bin", 5120, "dfe43ccfb05c9ebe703ed7ec1694db527220c58a3299bdbc7a3eb98e46de5dc0"⟩, ⟨"base/model/adapters/tensors/adapter.layers.02.mlp_gate.B.i16le.bin", 20480, "cc61635da46b2c9974335ea37e0b5fd660a5c8a42a89b271fa7ec2ac4b8b26f6"⟩, ⟨"base/model/adapters/tensors/adapter.layers.02.mlp_up.A.i16le.bin", 5120, "5a07437b39bd7cf4d71c8bce410bcb4c53862fd3b7722674be4868a6b32a5c29"⟩, ⟨"base/model/adapters/tensors/adapter.layers.02.mlp_up.B.i16le.bin", 20480, "cc61635da46b2c9974335ea37e0b5fd660a5c8a42a89b271fa7ec2ac4b8b26f6"⟩, ⟨"base/model/adapters/tensors/adapter.layers.03.attn_output.A.i16le.bin", 5120, "92b0310cf7a4606d502a976d2723ee77480388823ca3e73ebe89450a7335e1d9"⟩, ⟨"base/model/adapters/tensors/adapter.layers.03.attn_output.B.i16le.bin", 5120, "a11937f356a9b0ba592c82f5290bac8016cb33a3f9bc68d3490147c158ebb10d"⟩, ⟨"base/model/adapters/tensors/adapter.layers.03.attn_qkv.A.i16le.bin", 5120, "f24ac9956dcbca570f297083a40eef635e16453bba7c3ba69b625970d545dbc6"⟩, ⟨"base/model/adapters/tensors/adapter.layers.03.attn_qkv.B.i16le.bin", 15360, "0299f757a85a1aad6cbe1ad2b0eda925d8df667cd04e646af8917f65cbf24537"⟩, ⟨"base/model/adapters/tensors/adapter.layers.03.mlp_down.A.i16le.bin", 20480, "d369d41d0a7c78dba82147c97dfa99b0c055aea8c282ee9e211f5033316737d3"⟩, ⟨"base/model/adapters/tensors/adapter.layers.03.mlp_down.B.i16le.bin", 5120, "a11937f356a9b0ba592c82f5290bac8016cb33a3f9bc68d3490147c158ebb10d"⟩, ⟨"base/model/adapters/tensors/adapter.layers.03.mlp_gate.A.i16le.bin", 5120, "5a07437b39bd7cf4d71c8bce410bcb4c53862fd3b7722674be4868a6b32a5c29"⟩, ⟨"base/model/adapters/tensors/adapter.layers.03.mlp_gate.B.i16le.bin", 20480, "cc61635da46b2c9974335ea37e0b5fd660a5c8a42a89b271fa7ec2ac4b8b26f6"⟩, ⟨"base/model/adapters/tensors/adapter.layers.03.mlp_up.A.i16le.bin", 5120, "0baf561aeb192113ce68ce363342f4a89997bf90729a8e441c7b980416731164"⟩, ⟨"base/model/adapters/tensors/adapter.layers.03.mlp_up.B.i16le.bin", 20480, "cc61635da46b2c9974335ea37e0b5fd660a5c8a42a89b271fa7ec2ac4b8b26f6"⟩, ⟨"base/model/adapters/tensors/adapter.layers.04.attn_output.A.i16le.bin", 5120, "5d67769562ca9fac9cbd0bfcd6b248bdc03d1366f925d67a1b1370bc9772bd66"⟩, ⟨"base/model/adapters/tensors/adapter.layers.04.attn_output.B.i16le.bin", 5120, "a11937f356a9b0ba592c82f5290bac8016cb33a3f9bc68d3490147c158ebb10d"⟩, ⟨"base/model/adapters/tensors/adapter.layers.04.attn_qkv.A.i16le.bin", 5120, "92b0310cf7a4606d502a976d2723ee77480388823ca3e73ebe89450a7335e1d9"⟩, ⟨"base/model/adapters/tensors/adapter.layers.04.attn_qkv.B.i16le.bin", 15360, "0299f757a85a1aad6cbe1ad2b0eda925d8df667cd04e646af8917f65cbf24537"⟩, ⟨"base/model/adapters/tensors/adapter.layers.04.mlp_down.A.i16le.bin", 20480, "8be2c803d295ad5b300987f3e4bef0c2e6946b296895703b73502b5e9b760cb0"⟩, ⟨"base/model/adapters/tensors/adapter.layers.04.mlp_down.B.i16le.bin", 5120, "a11937f356a9b0ba592c82f5290bac8016cb33a3f9bc68d3490147c158ebb10d"⟩, ⟨"base/model/adapters/tensors/adapter.layers.04.mlp_gate.A.i16le.bin", 5120, "0baf561aeb192113ce68ce363342f4a89997bf90729a8e441c7b980416731164"⟩, ⟨"base/model/adapters/tensors/adapter.layers.04.mlp_gate.B.i16le.bin", 20480, "cc61635da46b2c9974335ea37e0b5fd660a5c8a42a89b271fa7ec2ac4b8b26f6"⟩, ⟨"base/model/adapters/tensors/adapter.layers.04.mlp_up.A.i16le.bin", 5120, "afea522680ebee7f64b5c581ff3706f6c5a1d3fdf3852cd05d9e1ca91566febf"⟩, ⟨"base/model/adapters/tensors/adapter.layers.04.mlp_up.B.i16le.bin", 20480, "cc61635da46b2c9974335ea37e0b5fd660a5c8a42a89b271fa7ec2ac4b8b26f6"⟩, ⟨"base/model/adapters/tensors/adapter.layers.05.attn_output.A.i16le.bin", 5120, "dfe43ccfb05c9ebe703ed7ec1694db527220c58a3299bdbc7a3eb98e46de5dc0"⟩, ⟨"base/model/adapters/tensors/adapter.layers.05.attn_output.B.i16le.bin", 5120, "a11937f356a9b0ba592c82f5290bac8016cb33a3f9bc68d3490147c158ebb10d"⟩, ⟨"base/model/adapters/tensors/adapter.layers.05.attn_qkv.A.i16le.bin", 5120, "5d67769562ca9fac9cbd0bfcd6b248bdc03d1366f925d67a1b1370bc9772bd66"⟩, ⟨"base/model/adapters/tensors/adapter.layers.05.attn_qkv.B.i16le.bin", 15360, "0299f757a85a1aad6cbe1ad2b0eda925d8df667cd04e646af8917f65cbf24537"⟩, ⟨"base/model/adapters/tensors/adapter.layers.05.mlp_down.A.i16le.bin", 20480, "2f04593443b343351655e4782e08305cce64cfe3c2cb227853d8889266914564"⟩, ⟨"base/model/adapters/tensors/adapter.layers.05.mlp_down.B.i16le.bin", 5120, "a11937f356a9b0ba592c82f5290bac8016cb33a3f9bc68d3490147c158ebb10d"⟩, ⟨"base/model/adapters/tensors/adapter.layers.05.mlp_gate.A.i16le.bin", 5120, "afea522680ebee7f64b5c581ff3706f6c5a1d3fdf3852cd05d9e1ca91566febf"⟩, ⟨"base/model/adapters/tensors/adapter.layers.05.mlp_gate.B.i16le.bin", 20480, "cc61635da46b2c9974335ea37e0b5fd660a5c8a42a89b271fa7ec2ac4b8b26f6"⟩, ⟨"base/model/adapters/tensors/adapter.layers.05.mlp_up.A.i16le.bin", 5120, "f24ac9956dcbca570f297083a40eef635e16453bba7c3ba69b625970d545dbc6"⟩, ⟨"base/model/adapters/tensors/adapter.layers.05.mlp_up.B.i16le.bin", 20480, "cc61635da46b2c9974335ea37e0b5fd660a5c8a42a89b271fa7ec2ac4b8b26f6"⟩, ⟨"base/model/adapters/tensors/adapter.layers.06.attn_output.A.i16le.bin", 5120, "5a07437b39bd7cf4d71c8bce410bcb4c53862fd3b7722674be4868a6b32a5c29"⟩, ⟨"base/model/adapters/tensors/adapter.layers.06.attn_output.B.i16le.bin", 5120, "a11937f356a9b0ba592c82f5290bac8016cb33a3f9bc68d3490147c158ebb10d"⟩, ⟨"base/model/adapters/tensors/adapter.layers.06.attn_qkv.A.i16le.bin", 5120, "dfe43ccfb05c9ebe703ed7ec1694db527220c58a3299bdbc7a3eb98e46de5dc0"⟩, ⟨"base/model/adapters/tensors/adapter.layers.06.attn_qkv.B.i16le.bin", 15360, "0299f757a85a1aad6cbe1ad2b0eda925d8df667cd04e646af8917f65cbf24537"⟩, ⟨"base/model/adapters/tensors/adapter.layers.06.mlp_down.A.i16le.bin", 20480, "7a1f4b14a0b3ab192781ccbc4300aa7629711fbd00094d9b713cd3c724fc0309"⟩, ⟨"base/model/adapters/tensors/adapter.layers.06.mlp_down.B.i16le.bin", 5120, "a11937f356a9b0ba592c82f5290bac8016cb33a3f9bc68d3490147c158ebb10d"⟩, ⟨"base/model/adapters/tensors/adapter.layers.06.mlp_gate.A.i16le.bin", 5120, "f24ac9956dcbca570f297083a40eef635e16453bba7c3ba69b625970d545dbc6"⟩, ⟨"base/model/adapters/tensors/adapter.layers.06.mlp_gate.B.i16le.bin", 20480, "cc61635da46b2c9974335ea37e0b5fd660a5c8a42a89b271fa7ec2ac4b8b26f6"⟩, ⟨"base/model/adapters/tensors/adapter.layers.06.mlp_up.A.i16le.bin", 5120, "92b0310cf7a4606d502a976d2723ee77480388823ca3e73ebe89450a7335e1d9"⟩, ⟨"base/model/adapters/tensors/adapter.layers.06.mlp_up.B.i16le.bin", 20480, "cc61635da46b2c9974335ea37e0b5fd660a5c8a42a89b271fa7ec2ac4b8b26f6"⟩, ⟨"base/model/adapters/tensors/adapter.layers.07.attn_output.A.i16le.bin", 5120, "0baf561aeb192113ce68ce363342f4a89997bf90729a8e441c7b980416731164"⟩, ⟨"base/model/adapters/tensors/adapter.layers.07.attn_output.B.i16le.bin", 5120, "a11937f356a9b0ba592c82f5290bac8016cb33a3f9bc68d3490147c158ebb10d"⟩, ⟨"base/model/adapters/tensors/adapter.layers.07.attn_qkv.A.i16le.bin", 5120, "5a07437b39bd7cf4d71c8bce410bcb4c53862fd3b7722674be4868a6b32a5c29"⟩, ⟨"base/model/adapters/tensors/adapter.layers.07.attn_qkv.B.i16le.bin", 15360, "0299f757a85a1aad6cbe1ad2b0eda925d8df667cd04e646af8917f65cbf24537"⟩, ⟨"base/model/adapters/tensors/adapter.layers.07.mlp_down.A.i16le.bin", 20480, "44b8c64f14cae5789a839425471801fd7f5765cc64abe19669287712a9d2dbcb"⟩, ⟨"base/model/adapters/tensors/adapter.layers.07.mlp_down.B.i16le.bin", 5120, "a11937f356a9b0ba592c82f5290bac8016cb33a3f9bc68d3490147c158ebb10d"⟩, ⟨"base/model/adapters/tensors/adapter.layers.07.mlp_gate.A.i16le.bin", 5120, "92b0310cf7a4606d502a976d2723ee77480388823ca3e73ebe89450a7335e1d9"⟩, ⟨"base/model/adapters/tensors/adapter.layers.07.mlp_gate.B.i16le.bin", 20480, "cc61635da46b2c9974335ea37e0b5fd660a5c8a42a89b271fa7ec2ac4b8b26f6"⟩, ⟨"base/model/adapters/tensors/adapter.layers.07.mlp_up.A.i16le.bin", 5120, "5d67769562ca9fac9cbd0bfcd6b248bdc03d1366f925d67a1b1370bc9772bd66"⟩, ⟨"base/model/adapters/tensors/adapter.layers.07.mlp_up.B.i16le.bin", 20480, "cc61635da46b2c9974335ea37e0b5fd660a5c8a42a89b271fa7ec2ac4b8b26f6"⟩, ⟨"base/model/tensors/manifest.json", 28234, "2164a2a3f64b3bbc9fb9f2ee14e3d15c0b9e66d548ede35065eeecf197f3b67f"⟩, ⟨"base/model/tensors/model.final_norm.weight.i16le.bin", 640, "f5aa5f72368b94c814f7ff12bc1d180d6296397628db16411765a9e713b12f3e"⟩, ⟨"base/model/tensors/model.layers.00.attn_norm.weight.i16le.bin", 640, "f5aa5f72368b94c814f7ff12bc1d180d6296397628db16411765a9e713b12f3e"⟩, ⟨"base/model/tensors/model.layers.00.attn_output.weight.i16le.bin", 204800, "63dd072a4aa0579d17890848d0b9948aabad4d6f9a47fa58868f4572b5e91c7c"⟩, ⟨"base/model/tensors/model.layers.00.attn_qkv.weight.i16le.bin", 614400, "171f38ece7178195cde6d203fed2907ac1f8ca7c1787322ad1674f3b7e9d2f0a"⟩, ⟨"base/model/tensors/model.layers.00.mlp_down.weight.i16le.bin", 819200, "dce79b8fea025a282b35a56f716c4766ca2949f23c30630060db91814710f4f5"⟩, ⟨"base/model/tensors/model.layers.00.mlp_gate.weight.i16le.bin", 819200, "dce79b8fea025a282b35a56f716c4766ca2949f23c30630060db91814710f4f5"⟩, ⟨"base/model/tensors/model.layers.00.mlp_norm.weight.i16le.bin", 640, "f5aa5f72368b94c814f7ff12bc1d180d6296397628db16411765a9e713b12f3e"⟩, ⟨"base/model/tensors/model.layers.00.mlp_up.weight.i16le.bin", 819200, "dce79b8fea025a282b35a56f716c4766ca2949f23c30630060db91814710f4f5"⟩, ⟨"base/model/tensors/model.layers.01.attn_norm.weight.i16le.bin", 640, "f5aa5f72368b94c814f7ff12bc1d180d6296397628db16411765a9e713b12f3e"⟩, ⟨"base/model/tensors/model.layers.01.attn_output.weight.i16le.bin", 204800, "8eafc7bd411c1f02b9e972a83d2b0a4164eefc5ef51e6b63ad7acc78be4ad44f"⟩, ⟨"base/model/tensors/model.layers.01.attn_qkv.weight.i16le.bin", 614400, "34c69899504b36f13e8b22120cf0fd894e61fcd6b046fb8535b79cc491fa3b3f"⟩, ⟨"base/model/tensors/model.layers.01.mlp_down.weight.i16le.bin", 819200, "dce79b8fea025a282b35a56f716c4766ca2949f23c30630060db91814710f4f5"⟩, ⟨"base/model/tensors/model.layers.01.mlp_gate.weight.i16le.bin", 819200, "dce79b8fea025a282b35a56f716c4766ca2949f23c30630060db91814710f4f5"⟩, ⟨"base/model/tensors/model.layers.01.mlp_norm.weight.i16le.bin", 640, "f5aa5f72368b94c814f7ff12bc1d180d6296397628db16411765a9e713b12f3e"⟩, ⟨"base/model/tensors/model.layers.01.mlp_up.weight.i16le.bin", 819200, "dce79b8fea025a282b35a56f716c4766ca2949f23c30630060db91814710f4f5"⟩, ⟨"base/model/tensors/model.layers.02.attn_norm.weight.i16le.bin", 640, "f5aa5f72368b94c814f7ff12bc1d180d6296397628db16411765a9e713b12f3e"⟩, ⟨"base/model/tensors/model.layers.02.attn_output.weight.i16le.bin", 204800, "8eafc7bd411c1f02b9e972a83d2b0a4164eefc5ef51e6b63ad7acc78be4ad44f"⟩, ⟨"base/model/tensors/model.layers.02.attn_qkv.weight.i16le.bin", 614400, "34c69899504b36f13e8b22120cf0fd894e61fcd6b046fb8535b79cc491fa3b3f"⟩, ⟨"base/model/tensors/model.layers.02.mlp_down.weight.i16le.bin", 819200, "dce79b8fea025a282b35a56f716c4766ca2949f23c30630060db91814710f4f5"⟩, ⟨"base/model/tensors/model.layers.02.mlp_gate.weight.i16le.bin", 819200, "dce79b8fea025a282b35a56f716c4766ca2949f23c30630060db91814710f4f5"⟩, ⟨"base/model/tensors/model.layers.02.mlp_norm.weight.i16le.bin", 640, "f5aa5f72368b94c814f7ff12bc1d180d6296397628db16411765a9e713b12f3e"⟩, ⟨"base/model/tensors/model.layers.02.mlp_up.weight.i16le.bin", 819200, "dce79b8fea025a282b35a56f716c4766ca2949f23c30630060db91814710f4f5"⟩, ⟨"base/model/tensors/model.layers.03.attn_norm.weight.i16le.bin", 640, "f5aa5f72368b94c814f7ff12bc1d180d6296397628db16411765a9e713b12f3e"⟩, ⟨"base/model/tensors/model.layers.03.attn_output.weight.i16le.bin", 204800, "8eafc7bd411c1f02b9e972a83d2b0a4164eefc5ef51e6b63ad7acc78be4ad44f"⟩, ⟨"base/model/tensors/model.layers.03.attn_qkv.weight.i16le.bin", 614400, "34c69899504b36f13e8b22120cf0fd894e61fcd6b046fb8535b79cc491fa3b3f"⟩, ⟨"base/model/tensors/model.layers.03.mlp_down.weight.i16le.bin", 819200, "dce79b8fea025a282b35a56f716c4766ca2949f23c30630060db91814710f4f5"⟩, ⟨"base/model/tensors/model.layers.03.mlp_gate.weight.i16le.bin", 819200, "dce79b8fea025a282b35a56f716c4766ca2949f23c30630060db91814710f4f5"⟩, ⟨"base/model/tensors/model.layers.03.mlp_norm.weight.i16le.bin", 640, "f5aa5f72368b94c814f7ff12bc1d180d6296397628db16411765a9e713b12f3e"⟩, ⟨"base/model/tensors/model.layers.03.mlp_up.weight.i16le.bin", 819200, "dce79b8fea025a282b35a56f716c4766ca2949f23c30630060db91814710f4f5"⟩, ⟨"base/model/tensors/model.layers.04.attn_norm.weight.i16le.bin", 640, "f5aa5f72368b94c814f7ff12bc1d180d6296397628db16411765a9e713b12f3e"⟩, ⟨"base/model/tensors/model.layers.04.attn_output.weight.i16le.bin", 204800, "8eafc7bd411c1f02b9e972a83d2b0a4164eefc5ef51e6b63ad7acc78be4ad44f"⟩, ⟨"base/model/tensors/model.layers.04.attn_qkv.weight.i16le.bin", 614400, "34c69899504b36f13e8b22120cf0fd894e61fcd6b046fb8535b79cc491fa3b3f"⟩, ⟨"base/model/tensors/model.layers.04.mlp_down.weight.i16le.bin", 819200, "dce79b8fea025a282b35a56f716c4766ca2949f23c30630060db91814710f4f5"⟩, ⟨"base/model/tensors/model.layers.04.mlp_gate.weight.i16le.bin", 819200, "dce79b8fea025a282b35a56f716c4766ca2949f23c30630060db91814710f4f5"⟩, ⟨"base/model/tensors/model.layers.04.mlp_norm.weight.i16le.bin", 640, "f5aa5f72368b94c814f7ff12bc1d180d6296397628db16411765a9e713b12f3e"⟩, ⟨"base/model/tensors/model.layers.04.mlp_up.weight.i16le.bin", 819200, "dce79b8fea025a282b35a56f716c4766ca2949f23c30630060db91814710f4f5"⟩, ⟨"base/model/tensors/model.layers.05.attn_norm.weight.i16le.bin", 640, "f5aa5f72368b94c814f7ff12bc1d180d6296397628db16411765a9e713b12f3e"⟩, ⟨"base/model/tensors/model.layers.05.attn_output.weight.i16le.bin", 204800, "8eafc7bd411c1f02b9e972a83d2b0a4164eefc5ef51e6b63ad7acc78be4ad44f"⟩, ⟨"base/model/tensors/model.layers.05.attn_qkv.weight.i16le.bin", 614400, "34c69899504b36f13e8b22120cf0fd894e61fcd6b046fb8535b79cc491fa3b3f"⟩, ⟨"base/model/tensors/model.layers.05.mlp_down.weight.i16le.bin", 819200, "dce79b8fea025a282b35a56f716c4766ca2949f23c30630060db91814710f4f5"⟩, ⟨"base/model/tensors/model.layers.05.mlp_gate.weight.i16le.bin", 819200, "dce79b8fea025a282b35a56f716c4766ca2949f23c30630060db91814710f4f5"⟩, ⟨"base/model/tensors/model.layers.05.mlp_norm.weight.i16le.bin", 640, "f5aa5f72368b94c814f7ff12bc1d180d6296397628db16411765a9e713b12f3e"⟩, ⟨"base/model/tensors/model.layers.05.mlp_up.weight.i16le.bin", 819200, "dce79b8fea025a282b35a56f716c4766ca2949f23c30630060db91814710f4f5"⟩, ⟨"base/model/tensors/model.layers.06.attn_norm.weight.i16le.bin", 640, "f5aa5f72368b94c814f7ff12bc1d180d6296397628db16411765a9e713b12f3e"⟩, ⟨"base/model/tensors/model.layers.06.attn_output.weight.i16le.bin", 204800, "8eafc7bd411c1f02b9e972a83d2b0a4164eefc5ef51e6b63ad7acc78be4ad44f"⟩, ⟨"base/model/tensors/model.layers.06.attn_qkv.weight.i16le.bin", 614400, "34c69899504b36f13e8b22120cf0fd894e61fcd6b046fb8535b79cc491fa3b3f"⟩, ⟨"base/model/tensors/model.layers.06.mlp_down.weight.i16le.bin", 819200, "dce79b8fea025a282b35a56f716c4766ca2949f23c30630060db91814710f4f5"⟩, ⟨"base/model/tensors/model.layers.06.mlp_gate.weight.i16le.bin", 819200, "dce79b8fea025a282b35a56f716c4766ca2949f23c30630060db91814710f4f5"⟩, ⟨"base/model/tensors/model.layers.06.mlp_norm.weight.i16le.bin", 640, "f5aa5f72368b94c814f7ff12bc1d180d6296397628db16411765a9e713b12f3e"⟩, ⟨"base/model/tensors/model.layers.06.mlp_up.weight.i16le.bin", 819200, "dce79b8fea025a282b35a56f716c4766ca2949f23c30630060db91814710f4f5"⟩, ⟨"base/model/tensors/model.layers.07.attn_norm.weight.i16le.bin", 640, "f5aa5f72368b94c814f7ff12bc1d180d6296397628db16411765a9e713b12f3e"⟩, ⟨"base/model/tensors/model.layers.07.attn_output.weight.i16le.bin", 204800, "8eafc7bd411c1f02b9e972a83d2b0a4164eefc5ef51e6b63ad7acc78be4ad44f"⟩, ⟨"base/model/tensors/model.layers.07.attn_qkv.weight.i16le.bin", 614400, "34c69899504b36f13e8b22120cf0fd894e61fcd6b046fb8535b79cc491fa3b3f"⟩, ⟨"base/model/tensors/model.layers.07.mlp_down.weight.i16le.bin", 819200, "dce79b8fea025a282b35a56f716c4766ca2949f23c30630060db91814710f4f5"⟩, ⟨"base/model/tensors/model.layers.07.mlp_gate.weight.i16le.bin", 819200, "dce79b8fea025a282b35a56f716c4766ca2949f23c30630060db91814710f4f5"⟩, ⟨"base/model/tensors/model.layers.07.mlp_norm.weight.i16le.bin", 640, "f5aa5f72368b94c814f7ff12bc1d180d6296397628db16411765a9e713b12f3e"⟩, ⟨"base/model/tensors/model.layers.07.mlp_up.weight.i16le.bin", 819200, "dce79b8fea025a282b35a56f716c4766ca2949f23c30630060db91814710f4f5"⟩, ⟨"base/model/tensors/model.token_embedding.weight.i16le.bin", 166400, "7716b6b19f19f6663a9f9c583b075c802889ce9206161b80d8741c49204fa9df"⟩]
      generator := [⟨"base/policies/generator_policy.json", 1851, "4aa9045b8ef05f1a5183cd078d1af0bcf3c92642faf0a9e34b09988ef5d623ec"⟩]
      planner := [⟨"base/model/phase15_planner/manifest.json", 975, "1439cb69b09d4d0b637c9b2a62172f4150f79bd57d0d52a813ef4435544c9ea9"⟩, ⟨"base/model/phase15_planner/public_curriculum.json", 16469, "c55a0ba69705faa4c75ee898b3c1f2195af3cf9fee358058fdaff8609d07bbc2"⟩, ⟨"base/model/phase15_planner/training_report.json", 650, "b0a7988383b27ad4c90b7abd411bc8461ce2fe47ebb5620416cac91f5b7471a5"⟩, ⟨"base/model/phase15_planner/vocabulary.json", 1157, "6ca846c992da7211397e07c8dab8775d01bbae465702311dcd276ee15aad0e9d"⟩, ⟨"base/model/phase15_planner/weights.i16le.bin", 65536, "19869eac5b0da770505214a6c5817b94dfda05730f97598bf2f855aff82d6c8d"⟩, ⟨"base/policies/planner_policy.json", 1955, "a585835e42d7bb47d047b24f8635f9e121410d0993e276dbdc77975d987b15fb"⟩]
      trainingPolicy := [⟨"base/training/data_curriculum.json", 468, "92a8e5d12e0ae7607b6f8547967c102681cc3cc2cf86a502f90aa45cfc6518e4"⟩, ⟨"base/training/optimizer_state.json", 1490, "1f046614c26415b1e0c77455bd32471a115ea354838a83789ade143781219637"⟩, ⟨"base/training/training_policy.json", 624, "9bddc0e826638f55f03dbaeb397dd6c1c97640c66f5839429bc8ce216ccc27f9"⟩]
      retrievalPolicy := [⟨"base/retrieval/index_manifest.json", 1368, "1f797fadc3d97eb5fb806a6e6332d0b85728d754dda68605e180b2dc33759738"⟩]
      memory := [⟨"base/memory/memory_manifest.json", 1293, "4c63a3c8199fdfd1e48dac688851c114a6a3dcc7d5446ac492225bae736bd9d5"⟩]
      tokenizer := [⟨"base/model/tokenizer/manifest.json", 463, "02189aacaca473e404291d41c29eeb3d8e9a0984ec9619194b3c6e89ec7d6414"⟩, ⟨"base/model/tokenizer/tokenizer.bin", 316, "b1eec973c9555f094f0ed805ab37b0ecac4cb3a7defba23d99ddc38ed5383d7d"⟩, ⟨"base/model/tokenizer/vocabulary.json", 10897, "61b8c71667b30ef6a0ea6b2186cd87b62bf53765e4aef755615ee50f63242dc5"⟩]
      verificationPolicy := [⟨"base/policies/verification_policy.json", 397, "64ece32b682cfe651db19fe80f8704aa45c3117fb83b6da6d954589773e19eea"⟩]
      resourcePolicy := [⟨"base/policies/resource_policy.json", 628, "1376fbf29c808c8f15ea97b7061d116f3a40193e31799c9401ffdb47cc1d77ee"⟩]
      selfModel := [⟨"base/self_model/manifest.json", 506, "32032a4ed4150482747c8b5f6882acec586c9ee07ac3caa48a204675abbeb8b0"⟩]
      capabilityFrontier := (["lean.phase10.heldout.linear_gap", "lean.phase10.protected.reflexive_seven", "lean.phase11.heldout.add_zero_macro", "lean.phase12.generation1.le_refl_macro", "lean.phase12.generation2.zero_le_macro", "lean.phase12.generation3.lt_succ_planner_macro", "lean.phase12.generation4.lt_add_two_adapter_macro", "lean.phase14.generation5_zero_lt_succ", "lean.phase14.generation6_lt_add_five", "lean.phase14.generation7_succ_le_add_two", "lean.phase14.generation8_le_add_four", "lean.phase15.dynamic.multistep.4a7a415bcd169bb8", "phase16.dynamic.adapter_policy.2624594ed996371dbea9", "phase16.dynamic.architecture_policy.c3cd1f252d113cb41ebc", "phase16.dynamic.memory_policy.f9734b7e402fa0a0e992", "phase16.dynamic.optimizer_policy.10a54f6a7c3503fa7430", "phase16.dynamic.planner_policy.e8a5ef052b4885132a71", "phase16.dynamic.retrieval_policy.376f6d7a4130a978e1e6", "phase16.dynamic.tool_policy.231b912e39ff91bade12", "phase16.dynamic.verification_automation_policy.4290be408ad83beccf87", "phase17.dynamic.478d7884588779bca1483fb65d06d2a4b4d430960c47a6fdfd8036fb8a39c2ab", "program.phase15.dynamic.affine.beb80dc125251a70"] : List String).toFinset }
    executionContext := [⟨"base/package_manifest.json", 2387, "d7679bf5a96baf19616c0a6a15b2f295580a4c47231acba39ad926e951efde6b"⟩, ⟨"base/policies/tool_policy.json", 561, "f8820ca3cded0e9c478e0c495df4bbee69d9af3fee389393049b2372fe87bd16"⟩, ⟨"base/runtime/environment.json", 179, "fc9d81f7e64b2e47c5ff3158945f602e4f31227c39ee8555acdc71897a0c28e1"⟩, ⟨"base/runtime/resource_measurement.json", 1015, "d8bd3ab1e5564cdd794644dbe97b5b340237c2b0e0533284a767958cf1fe5543"⟩, ⟨"base/runtime/rng_state.json", 169, "e638f51b37390af36ac358b25faeb927a5bc87722a73b0609ba338ae66030ff1"⟩]
    packageHash := "b4036b3e31a6608e30b421c08906b1e58c3e7d61fef6eb6730881c597656434e" }
def addedKey : String := "a4f37fb8f2f7d3a90829340f2f02b2f19dbc5dfa5caf7a7633e9092837265c0e"
def addedTask : String := "phase17.dynamic.478d7884588779bca1483fb65d06d2a4b4d430960c47a6fdfd8036fb8a39c2ab"

theorem selected_typed_binding :
    frozenView observedAfter = frozenView observedBefore ∧
    observedAfter.package.base = observedBefore.package.base ++ [addedKey] ∧
    observedAfter.package.capabilityFrontier = insert addedTask observedBefore.package.capabilityFrontier ∧
    addedTask ∉ observedBefore.package.capabilityFrontier ∧
    observedAfter.packageHash ≠ observedBefore.packageHash := by
  decide

theorem selected_interpretation_retention {Input Output : Type*}
    (interpret : List Image → Input → Output) (input : Input) :
    interpret (frozenView observedAfter) input = interpret (frozenView observedBefore) input :=
  fixed_interpretation_retained interpret observedBefore observedAfter selected_typed_binding.1 input

end Phase17LearnedBinding


namespace Phase17TaskMeaning

structure Program where
  family : Nat
  variant : Nat
  a : Int
  b : Int
  deriving DecidableEq, Repr

def insertInt (a : Int) : List Int → List Int
  | [] => [a]
  | b :: bs => if a ≤ b then a :: b :: bs else b :: insertInt a bs

def sortInts : List Int → List Int
  | [] => []
  | a :: rest => insertInt a (sortInts rest)

/-- Independent Lean semantics of the unchanged four-integer mutation DSL. -/
def execute (p : Program) (xs : List Int) : List Int :=
  let v := p.variant + 1
  let vi : Int := Int.ofNat v
  let x := fun (i : Nat) => xs.getD i 0
  match p.family with
  | 0 => xs.map (fun z => vi * z + p.a - p.b)
  | 1 => (List.range 4).map (fun i => x ((i + v + 1) % 4) + p.a * Int.ofNat (i + 1) + p.b)
  | 2 => (List.range 4).map (fun i => x ((i + v) % 4) + if i = 0 then p.a else 0)
  | 3 => (List.range 4).map (fun i => xs.sum + p.a + Int.ofNat (v * (i + 1) * (i + 2) / 2) - p.b * Int.ofNat (i + 1))
  | 4 => [x 0 + p.a, x 1 * vi, x 2 - p.b, x 3 + x 0 * vi]
  | 5 => (List.range 4).map (fun i => x ((i * v + p.b.natAbs) % 4))
  | 6 => [x 0 + x 1 + p.a, x 1 - x 2 + p.b, x 2 * vi, x 3 + p.a - p.b]
  | 7 => sortInts (xs.map (fun z => z + p.a * vi - p.b))
  | _ => []

-- State projection is supplied by the external physical evaluator. These proofs
-- do not establish that arbitrary self-reported observations describe a model.
structure ObservationState where
  proofs : List (String × String × String)
  programs : List (String × Program)

structure Meaning where
  check : ObservationState → Bool
  holds : ObservationState → Prop
  sound : ∀ s, check s = true → holds s

def theoremMeaning (task source decode : String) (P : Prop) (proof : P) : Meaning where
  check := fun s => decide ((task, source, decode) ∈ s.proofs)
  holds := fun s => (task, source, decode) ∈ s.proofs ∧ P
  sound := by
    intro s h
    exact ⟨of_decide_eq_true h, proof⟩

structure VectorContract where
  family : Nat
  requiredProgram : Option String
  inputs : List (List Int)
  targets : List (List Int)

def vectorMeaning (t : VectorContract) : Meaning where
  check := fun s => s.programs.any (fun e => decide
    (e.2.family = t.family ∧
     (t.requiredProgram = none ∨ t.requiredProgram = some e.1) ∧
     t.inputs.map (execute e.2) = t.targets))
  holds := fun s => ∃ e ∈ s.programs,
    e.2.family = t.family ∧
    (t.requiredProgram = none ∨ t.requiredProgram = some e.1) ∧
    t.inputs.map (execute e.2) = t.targets
  sound := by
    intro s h
    simpa only [List.any_eq_true, decide_eq_true_eq] using h

def rejectMeaning : Meaning where
  check := fun _ => false
  holds := fun _ => False
  sound := by intro s h; cases h

def checkedFrontier (declared : Finset Nat) (catalog : Nat → Meaning)
    (s : ObservationState) : Finset Nat :=
  declared.filter (fun t => (catalog t).check s = true)

theorem checked_frontier_sound (declared : Finset Nat) (catalog : Nat → Meaning)
    (s : ObservationState) {task : Nat}
    (member : task ∈ checkedFrontier declared catalog s) : (catalog task).holds s := by
  exact (catalog task).sound s (Finset.mem_filter.mp member).2

open RcpRclmFormalCoreV2 RcpRclmFormalCoreV3

-- Supplies the ACTUAL frontier/solves/frontierSound fields of the immutable root.
-- All other kernel fields and their adequacy remain obligations of the caller.
def attachTaskSemantics
    {State Update BaseCertificate Protected ResidualIndex Generator Proposal PackageHash : Type*}
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    (other : Learned.FrontierKernel (Task := Nat) (Generator := Generator)
      (Proposal := Proposal) (PackageHash := PackageHash) base)
    (observe : State → ObservationState) (declared : State → Finset Nat)
    (catalog : Nat → Meaning) :
    Learned.FrontierKernel (Task := Nat) (Generator := Generator)
      (Proposal := Proposal) (PackageHash := PackageHash) base :=
  { other with
    frontier := fun s => checkedFrontier (declared s) catalog (observe s)
    solves := fun s task => (catalog task).holds (observe s)
    frontierSound := by
      intro s task member
      exact checked_frontier_sound (declared s) catalog (observe s) member }

theorem attached_root_frontier_sound
    {State Update BaseCertificate Protected ResidualIndex Generator Proposal PackageHash : Type*}
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    (other : Learned.FrontierKernel (Task := Nat) (Generator := Generator)
      (Proposal := Proposal) (PackageHash := PackageHash) base)
    (observe : State → ObservationState) (declared : State → Finset Nat)
    (catalog : Nat → Meaning) {s : State} {task : Nat}
    (member : task ∈ (attachTaskSemantics other observe declared catalog).frontier s) :
    (attachTaskSemantics other observe declared catalog).solves s task :=
  (attachTaskSemantics other observe declared catalog).frontierSound member

end Phase17TaskMeaning

namespace Phase17TaskMeaning
set_option maxRecDepth 16384
set_option maxHeartbeats 4000000
-- Independently recomputed catalog SHA256: 30c9e00f93d23713ac658c004a8102e35a57c021bd6169da2cb1f877afa28670
namespace Inherited0
theorem phase17_c4df74a5676f3be58d91172a (a b : Nat) (h : a + 2 <= b) : a < b := by
  omega


def Target : Prop := ∀ (a b : Nat) (_h : a + 2 <= b), a < b
end Inherited0
theorem inherited_0 : Inherited0.Target := Inherited0.phase17_c4df74a5676f3be58d91172a
namespace Inherited1
theorem phase17_90f3310a3ade240161a9ccfe : (7 : Nat) = 7 := by
  rfl


def Target : Prop := (7 : Nat) = 7
end Inherited1
theorem inherited_1 : Inherited1.Target := Inherited1.phase17_90f3310a3ade240161a9ccfe
namespace Inherited2
theorem phase17_aa812b822aba1af8a0a8ee21 (n : Nat) : n + 0 = n := by
  simp


def Target : Prop := ∀ (n : Nat), n + 0 = n
end Inherited2
theorem inherited_2 : Inherited2.Target := Inherited2.phase17_aa812b822aba1af8a0a8ee21
namespace Inherited3
theorem phase17_a6f303464a35370717f5b43b (n : Nat) : n <= n := by
  omega


def Target : Prop := ∀ (n : Nat), n <= n
end Inherited3
theorem inherited_3 : Inherited3.Target := Inherited3.phase17_a6f303464a35370717f5b43b
namespace Inherited4
theorem phase17_ab4b84ad0b06a5f8bb5b3feb (n : Nat) : 0 <= n := by
  omega


def Target : Prop := ∀ (n : Nat), 0 <= n
end Inherited4
theorem inherited_4 : Inherited4.Target := Inherited4.phase17_ab4b84ad0b06a5f8bb5b3feb
namespace Inherited5
theorem phase17_95bcb898619e04c7c7a8dc7c (n : Nat) : n < n + 1 := by
  omega


def Target : Prop := ∀ (n : Nat), n < n + 1
end Inherited5
theorem inherited_5 : Inherited5.Target := Inherited5.phase17_95bcb898619e04c7c7a8dc7c
namespace Inherited6
theorem phase17_4b6c1b29c9bb833d61e2f656 (n : Nat) : n < n + 2 := by
  omega


def Target : Prop := ∀ (n : Nat), n < n + 2
end Inherited6
theorem inherited_6 : Inherited6.Target := Inherited6.phase17_4b6c1b29c9bb833d61e2f656
namespace Inherited7
theorem phase17_eedfa6455d98671e410ad7f1 (n : Nat) : 0 < n + 1 := by
  omega


def Target : Prop := ∀ (n : Nat), 0 < n + 1
end Inherited7
theorem inherited_7 : Inherited7.Target := Inherited7.phase17_eedfa6455d98671e410ad7f1
namespace Inherited8
theorem phase17_8b38bcb47eda0b70b2b7db53 (n : Nat) : n < n + 5 := by
  omega


def Target : Prop := ∀ (n : Nat), n < n + 5
end Inherited8
theorem inherited_8 : Inherited8.Target := Inherited8.phase17_8b38bcb47eda0b70b2b7db53
namespace Inherited9
theorem phase17_d69e7a698f7d392c9d7249ed (n : Nat) : n + 1 <= n + 2 := by
  omega


def Target : Prop := ∀ (n : Nat), n + 1 <= n + 2
end Inherited9
theorem inherited_9 : Inherited9.Target := Inherited9.phase17_d69e7a698f7d392c9d7249ed
namespace Inherited10
theorem phase17_ef6490ca1028e2f8266b9016 (n : Nat) : n <= n + 4 := by
  omega


def Target : Prop := ∀ (n : Nat), n <= n + 4
end Inherited10
theorem inherited_10 : Inherited10.Target := Inherited10.phase17_ef6490ca1028e2f8266b9016
namespace Inherited11
theorem phase17_40d58c7bcb7e075de355931f (x : Nat) : x + 2 < x + 3 := by
  have h : 2 < 3 := by omega
  exact Nat.add_lt_add_left h x


def Target : Prop := ∀ (x : Nat), x + 2 < x + 3
end Inherited11
theorem inherited_11 : Inherited11.Target := Inherited11.phase17_40d58c7bcb7e075de355931f
namespace Inherited12
def phase17Affine (x : Int) : Int := (-2) * x + (-7)
theorem phase17_ea08af8580910d01fc67b2a9 (x : Int) : phase17Affine x = (-2) * x + (-7) := by
  rfl


def Target : Prop := ∀ (x : Int), phase17Affine x = (-2) * x + (-7)
end Inherited12
theorem inherited_12 : Inherited12.Target := Inherited12.phase17_ea08af8580910d01fc67b2a9
def catalog : Nat → Meaning
  | 0 => theoremMeaning "lean.phase10.heldout.linear_gap" "8410efe3df3b56346023950e05536e31d3ed1436ba189e5d081eca7ecae3c2a3" "06b1bfcdd4b4d556af71bc4b9ad25705bdccc8769043bd28693b0494b1938da2" Inherited0.Target inherited_0
  | 1 => theoremMeaning "lean.phase10.protected.reflexive_seven" "2923a5127ebb2dce77b93f25bfacd4ff8d23778e9c045de8ddabed164da927fb" "5392f810f0edaae2646222e27e4ba85dd09365294490637453dd5afc4086fd0a" Inherited1.Target inherited_1
  | 2 => theoremMeaning "lean.phase11.heldout.add_zero_macro" "f17a5ce95e825ce7b1f160ea01b9af617754a0599dc79e598631d760d2737662" "047c1526c8be605c14dbb1ea9e7fdf798d960958c44b0c54e2c3b20b72e5e8f1" Inherited2.Target inherited_2
  | 3 => theoremMeaning "lean.phase12.generation1.le_refl_macro" "29a44f8162d395296df0b6a3695ef84d4c53754badd4fc40ac572339afe81343" "64b40cfc1967d7c61ff59e88447dda1c08214b7d4f6854ab21dfce92a58ef432" Inherited3.Target inherited_3
  | 4 => theoremMeaning "lean.phase12.generation2.zero_le_macro" "2ccfa1a6941344d7717e88514799bc03b443551733ef5f6611568e3b709d11ad" "810b78e6006b0587963765efe4a87f9e1cf374126d4cdbee47d22b3483200d2c" Inherited4.Target inherited_4
  | 5 => theoremMeaning "lean.phase12.generation3.lt_succ_planner_macro" "ef24333062d901e017672cd228a08665df7fe26cd039bd30af051edfe0bf1f15" "0a157eea313f12a5c66a407b2ab782cb22f9e6c4a49d5c231ccb29d5854b2caf" Inherited5.Target inherited_5
  | 6 => theoremMeaning "lean.phase12.generation4.lt_add_two_adapter_macro" "60e6bbca487b6807d97338b84253481f2884d25644d8f9274b716799a504d269" "32fae1c4dd17a247879289f9b8f1b4e9988f76195a101abaab29f579438c1a6e" Inherited6.Target inherited_6
  | 7 => theoremMeaning "lean.phase14.generation5_zero_lt_succ" "00a2b7cac3e41ec4f7f10326f38e7876550a166956b3133ab43b60a71d167d77" "c548cc466699b3891f55e2ea9b89cb03ffa95345e797b85abd1b5ccef11fab8c" Inherited7.Target inherited_7
  | 8 => theoremMeaning "lean.phase14.generation6_lt_add_five" "5f3d24df1725dd940f10edd1a1fc857d3e0a0a74aee4af2970c17e87e88e1387" "d81b0c93645b5d1fe8038d6bdc5bf36bc7ce66f65c98e5e0e437351553f5a771" Inherited8.Target inherited_8
  | 9 => theoremMeaning "lean.phase14.generation7_succ_le_add_two" "e674398024eb21a38ba89194a88e47bdb9e76adc711744020733036883991f1e" "fcfda49e8ce97e014155ca5d8a1f66e5b74eadad09c53517ac8829cc3dffb910" Inherited9.Target inherited_9
  | 10 => theoremMeaning "lean.phase14.generation8_le_add_four" "e213d8c64ed0c514b3be2f8e1dabde63c3b432d738e0a603140a3c948ba6ddfa" "f08827e9b291f026e450572beb47983bb520419f39f515a22f1338dfa0bece31" Inherited10.Target inherited_10
  | 11 => theoremMeaning "lean.phase15.dynamic.multistep.4a7a415bcd169bb8" "a269501136730bdcde4b1ab63efdb521ebb95bf9007b4dce32025cd893b3f830" "f34f041f82c60bc693c28bcee6677254696d0988d8ab656af003131fdf93d5b8" Inherited11.Target inherited_11
  | 12 => vectorMeaning { family := 0, requiredProgram := (some "7d98001be0bd64487cb44f7db6f741b3e0436eec4cc0c4b0d74f5e6f774f2c1a"), inputs := [[(-4), 14, (-5), (-11)]], targets := [[(-6), 66, (-10), (-34)]] }
  | 13 => vectorMeaning { family := 1, requiredProgram := (some "aedc8351d94932d37506d4d7b44fac9b1b40baf95d35f52bee726af598e7a5c2"), inputs := [[(-13), (-15), 11, 15]], targets := [[5, (-28), (-35), (-14)]] }
  | 14 => vectorMeaning { family := 2, requiredProgram := (some "ebb887e9009fdd02f1fc999cc900c47dee131970826c19bdc55a74b9c7cccd7e"), inputs := [[1, (-13), 15, 16]], targets := [[(-14), (-13), 15, 16]] }
  | 15 => vectorMeaning { family := 3, requiredProgram := (some "40ddd0f569709b232e4d769b2b288d694705a4561ef039aae2781deca29581d6"), inputs := [[(-10), 3, (-1), (-2)]], targets := [[(-7), 8, 24, 41]] }
  | 16 => vectorMeaning { family := 4, requiredProgram := (some "5dd1421b9968b2619b62416177c38a29898d05514db22440c2229ccd51679649"), inputs := [[16, (-13), (-5), (-14)]], targets := [[23, (-26), (-7), 18]] }
  | 17 => vectorMeaning { family := 5, requiredProgram := (some "b558b30a69cfed7c0faa2157402ed7910269e29212cbb0d3354f02fe5e0c1aad"), inputs := [[8, 8, (-2), 2]], targets := [[2, 8, 2, 8]] }
  | 18 => vectorMeaning { family := 6, requiredProgram := (some "1b3e59ea732ae920aa4d272bf89d3cd3acb7930ff3d921459efda0f2888e0fc3"), inputs := [[(-6), 11, (-15), 8]], targets := [[5, 14, (-45), 20]] }
  | 19 => vectorMeaning { family := 7, requiredProgram := (some "b1e1738eecfb2e51693f8aea51ff14a49d38787a26ea62ef81078b326a9a197f"), inputs := [[(-1), (-7), (-6), (-10)]], targets := [[(-34), (-31), (-30), (-25)]] }
  | 20 => theoremMeaning "program.phase15.dynamic.affine.beb80dc125251a70" "74b00915a34bd9b2abc617337883e545052e5193f01de883549f4b61c1e9bb9e" "3020c0904123f2b84315c42fe0e13b211f9a554d81b0e2f8e730805d737f505e" Inherited12.Target inherited_12
  | 21 => vectorMeaning { family := 6, requiredProgram := none, inputs := [[24, (-13), (-1), (-6)], [23, (-29), (-4), 10], [(-9), 28, 12, 11], [23, (-32), (-6), 13], [(-21), 4, (-21), (-3)], [3, (-17), (-21), 19], [3, 4, (-21), (-5)], [26, (-18), (-29), 29]], targets := [[7, 4, (-2), (-26)], [(-10), (-9), (-8), (-10)], [15, 32, 24, (-9)], [(-13), (-10), (-12), (-7)], [(-21), 41, (-42), (-23)], [(-18), 20, (-42), (-1)], [3, 41, (-42), (-25)], [4, 27, (-58), 9]] }
  | _ => rejectMeaning
def taskIds : List String := ["lean.phase10.heldout.linear_gap", "lean.phase10.protected.reflexive_seven", "lean.phase11.heldout.add_zero_macro", "lean.phase12.generation1.le_refl_macro", "lean.phase12.generation2.zero_le_macro", "lean.phase12.generation3.lt_succ_planner_macro", "lean.phase12.generation4.lt_add_two_adapter_macro", "lean.phase14.generation5_zero_lt_succ", "lean.phase14.generation6_lt_add_five", "lean.phase14.generation7_succ_le_add_two", "lean.phase14.generation8_le_add_four", "lean.phase15.dynamic.multistep.4a7a415bcd169bb8", "phase16.dynamic.adapter_policy.2624594ed996371dbea9", "phase16.dynamic.architecture_policy.c3cd1f252d113cb41ebc", "phase16.dynamic.memory_policy.f9734b7e402fa0a0e992", "phase16.dynamic.optimizer_policy.10a54f6a7c3503fa7430", "phase16.dynamic.planner_policy.e8a5ef052b4885132a71", "phase16.dynamic.retrieval_policy.376f6d7a4130a978e1e6", "phase16.dynamic.tool_policy.231b912e39ff91bade12", "phase16.dynamic.verification_automation_policy.4290be408ad83beccf87", "program.phase15.dynamic.affine.beb80dc125251a70", "phase17.dynamic.478d7884588779bca1483fb65d06d2a4b4d430960c47a6fdfd8036fb8a39c2ab"]
def before : ObservationState := { proofs := [("lean.phase10.heldout.linear_gap", "8410efe3df3b56346023950e05536e31d3ed1436ba189e5d081eca7ecae3c2a3", "06b1bfcdd4b4d556af71bc4b9ad25705bdccc8769043bd28693b0494b1938da2"), ("lean.phase10.protected.reflexive_seven", "2923a5127ebb2dce77b93f25bfacd4ff8d23778e9c045de8ddabed164da927fb", "5392f810f0edaae2646222e27e4ba85dd09365294490637453dd5afc4086fd0a"), ("lean.phase11.heldout.add_zero_macro", "f17a5ce95e825ce7b1f160ea01b9af617754a0599dc79e598631d760d2737662", "047c1526c8be605c14dbb1ea9e7fdf798d960958c44b0c54e2c3b20b72e5e8f1"), ("lean.phase12.generation1.le_refl_macro", "29a44f8162d395296df0b6a3695ef84d4c53754badd4fc40ac572339afe81343", "64b40cfc1967d7c61ff59e88447dda1c08214b7d4f6854ab21dfce92a58ef432"), ("lean.phase12.generation2.zero_le_macro", "2ccfa1a6941344d7717e88514799bc03b443551733ef5f6611568e3b709d11ad", "810b78e6006b0587963765efe4a87f9e1cf374126d4cdbee47d22b3483200d2c"), ("lean.phase12.generation3.lt_succ_planner_macro", "ef24333062d901e017672cd228a08665df7fe26cd039bd30af051edfe0bf1f15", "0a157eea313f12a5c66a407b2ab782cb22f9e6c4a49d5c231ccb29d5854b2caf"), ("lean.phase12.generation4.lt_add_two_adapter_macro", "60e6bbca487b6807d97338b84253481f2884d25644d8f9274b716799a504d269", "32fae1c4dd17a247879289f9b8f1b4e9988f76195a101abaab29f579438c1a6e"), ("lean.phase14.generation5_zero_lt_succ", "00a2b7cac3e41ec4f7f10326f38e7876550a166956b3133ab43b60a71d167d77", "c548cc466699b3891f55e2ea9b89cb03ffa95345e797b85abd1b5ccef11fab8c"), ("lean.phase14.generation6_lt_add_five", "5f3d24df1725dd940f10edd1a1fc857d3e0a0a74aee4af2970c17e87e88e1387", "d81b0c93645b5d1fe8038d6bdc5bf36bc7ce66f65c98e5e0e437351553f5a771"), ("lean.phase14.generation7_succ_le_add_two", "e674398024eb21a38ba89194a88e47bdb9e76adc711744020733036883991f1e", "fcfda49e8ce97e014155ca5d8a1f66e5b74eadad09c53517ac8829cc3dffb910"), ("lean.phase14.generation8_le_add_four", "e213d8c64ed0c514b3be2f8e1dabde63c3b432d738e0a603140a3c948ba6ddfa", "f08827e9b291f026e450572beb47983bb520419f39f515a22f1338dfa0bece31"), ("lean.phase15.dynamic.multistep.4a7a415bcd169bb8", "a269501136730bdcde4b1ab63efdb521ebb95bf9007b4dce32025cd893b3f830", "f34f041f82c60bc693c28bcee6677254696d0988d8ab656af003131fdf93d5b8"), ("program.phase15.dynamic.affine.beb80dc125251a70", "74b00915a34bd9b2abc617337883e545052e5193f01de883549f4b61c1e9bb9e", "3020c0904123f2b84315c42fe0e13b211f9a554d81b0e2f8e730805d737f505e")], programs := [("1b3e59ea732ae920aa4d272bf89d3cd3acb7930ff3d921459efda0f2888e0fc3", { family := 6, variant := 2, a := 0, b := (-12) }), ("40ddd0f569709b232e4d769b2b288d694705a4561ef039aae2781deca29581d6", { family := 3, variant := 0, a := (-11), b := (-13) }), ("5dd1421b9968b2619b62416177c38a29898d05514db22440c2229ccd51679649", { family := 4, variant := 1, a := 7, b := 2 }), ("7d98001be0bd64487cb44f7db6f741b3e0436eec4cc0c4b0d74f5e6f774f2c1a", { family := 0, variant := 3, a := 11, b := 1 }), ("aedc8351d94932d37506d4d7b44fac9b1b40baf95d35f52bee726af598e7a5c2", { family := 1, variant := 1, a := (-5), b := (-5) }), ("b1e1738eecfb2e51693f8aea51ff14a49d38787a26ea62ef81078b326a9a197f", { family := 7, variant := 1, a := (-13), b := (-2) }), ("b558b30a69cfed7c0faa2157402ed7910269e29212cbb0d3354f02fe5e0c1aad", { family := 5, variant := 1, a := 12, b := (-7) }), ("ebb887e9009fdd02f1fc999cc900c47dee131970826c19bdc55a74b9c7cccd7e", { family := 2, variant := 3, a := (-15), b := (-3) })] }
def after : ObservationState := { proofs := [("lean.phase10.heldout.linear_gap", "8410efe3df3b56346023950e05536e31d3ed1436ba189e5d081eca7ecae3c2a3", "06b1bfcdd4b4d556af71bc4b9ad25705bdccc8769043bd28693b0494b1938da2"), ("lean.phase10.protected.reflexive_seven", "2923a5127ebb2dce77b93f25bfacd4ff8d23778e9c045de8ddabed164da927fb", "5392f810f0edaae2646222e27e4ba85dd09365294490637453dd5afc4086fd0a"), ("lean.phase11.heldout.add_zero_macro", "f17a5ce95e825ce7b1f160ea01b9af617754a0599dc79e598631d760d2737662", "047c1526c8be605c14dbb1ea9e7fdf798d960958c44b0c54e2c3b20b72e5e8f1"), ("lean.phase12.generation1.le_refl_macro", "29a44f8162d395296df0b6a3695ef84d4c53754badd4fc40ac572339afe81343", "64b40cfc1967d7c61ff59e88447dda1c08214b7d4f6854ab21dfce92a58ef432"), ("lean.phase12.generation2.zero_le_macro", "2ccfa1a6941344d7717e88514799bc03b443551733ef5f6611568e3b709d11ad", "810b78e6006b0587963765efe4a87f9e1cf374126d4cdbee47d22b3483200d2c"), ("lean.phase12.generation3.lt_succ_planner_macro", "ef24333062d901e017672cd228a08665df7fe26cd039bd30af051edfe0bf1f15", "0a157eea313f12a5c66a407b2ab782cb22f9e6c4a49d5c231ccb29d5854b2caf"), ("lean.phase12.generation4.lt_add_two_adapter_macro", "60e6bbca487b6807d97338b84253481f2884d25644d8f9274b716799a504d269", "32fae1c4dd17a247879289f9b8f1b4e9988f76195a101abaab29f579438c1a6e"), ("lean.phase14.generation5_zero_lt_succ", "00a2b7cac3e41ec4f7f10326f38e7876550a166956b3133ab43b60a71d167d77", "c548cc466699b3891f55e2ea9b89cb03ffa95345e797b85abd1b5ccef11fab8c"), ("lean.phase14.generation6_lt_add_five", "5f3d24df1725dd940f10edd1a1fc857d3e0a0a74aee4af2970c17e87e88e1387", "d81b0c93645b5d1fe8038d6bdc5bf36bc7ce66f65c98e5e0e437351553f5a771"), ("lean.phase14.generation7_succ_le_add_two", "e674398024eb21a38ba89194a88e47bdb9e76adc711744020733036883991f1e", "fcfda49e8ce97e014155ca5d8a1f66e5b74eadad09c53517ac8829cc3dffb910"), ("lean.phase14.generation8_le_add_four", "e213d8c64ed0c514b3be2f8e1dabde63c3b432d738e0a603140a3c948ba6ddfa", "f08827e9b291f026e450572beb47983bb520419f39f515a22f1338dfa0bece31"), ("lean.phase15.dynamic.multistep.4a7a415bcd169bb8", "a269501136730bdcde4b1ab63efdb521ebb95bf9007b4dce32025cd893b3f830", "f34f041f82c60bc693c28bcee6677254696d0988d8ab656af003131fdf93d5b8"), ("program.phase15.dynamic.affine.beb80dc125251a70", "74b00915a34bd9b2abc617337883e545052e5193f01de883549f4b61c1e9bb9e", "3020c0904123f2b84315c42fe0e13b211f9a554d81b0e2f8e730805d737f505e")], programs := [("1b3e59ea732ae920aa4d272bf89d3cd3acb7930ff3d921459efda0f2888e0fc3", { family := 6, variant := 2, a := 0, b := (-12) }), ("40ddd0f569709b232e4d769b2b288d694705a4561ef039aae2781deca29581d6", { family := 3, variant := 0, a := (-11), b := (-13) }), ("5dd1421b9968b2619b62416177c38a29898d05514db22440c2229ccd51679649", { family := 4, variant := 1, a := 7, b := 2 }), ("7d98001be0bd64487cb44f7db6f741b3e0436eec4cc0c4b0d74f5e6f774f2c1a", { family := 0, variant := 3, a := 11, b := 1 }), ("aedc8351d94932d37506d4d7b44fac9b1b40baf95d35f52bee726af598e7a5c2", { family := 1, variant := 1, a := (-5), b := (-5) }), ("b1e1738eecfb2e51693f8aea51ff14a49d38787a26ea62ef81078b326a9a197f", { family := 7, variant := 1, a := (-13), b := (-2) }), ("b558b30a69cfed7c0faa2157402ed7910269e29212cbb0d3354f02fe5e0c1aad", { family := 5, variant := 1, a := 12, b := (-7) }), ("ebb887e9009fdd02f1fc999cc900c47dee131970826c19bdc55a74b9c7cccd7e", { family := 2, variant := 3, a := (-15), b := (-3) }), ("a4f37fb8f2f7d3a90829340f2f02b2f19dbc5dfa5caf7a7633e9092837265c0e", { family := 6, variant := 1, a := (-4), b := 16 })] }

def beforeDeclared : Finset Nat := Finset.range 21
def afterDeclared : Finset Nat := Finset.range 22

theorem before_coverage : checkedFrontier beforeDeclared catalog before = beforeDeclared := by decide
theorem after_coverage : checkedFrontier afterDeclared catalog after = afterDeclared := by decide

theorem selected_before_sound {task : Nat} (member : task ∈ beforeDeclared) :
    (catalog task).holds before := by
  apply checked_frontier_sound beforeDeclared catalog before
  rw [before_coverage]
  exact member

theorem selected_after_sound {task : Nat} (member : task ∈ afterDeclared) :
    (catalog task).holds after := by
  apply checked_frontier_sound afterDeclared catalog after
  rw [after_coverage]
  exact member

theorem selected_frontier_retention :
    checkedFrontier beforeDeclared catalog before ⊆ checkedFrontier afterDeclared catalog after := by
  rw [before_coverage, after_coverage]
  decide

theorem selected_frontier_expansion :
    (checkedFrontier beforeDeclared catalog before).card <
      (checkedFrontier afterDeclared catalog after).card := by
  rw [before_coverage, after_coverage]
  decide

theorem selected_predecessor_rejects_new : (catalog 21).check before = false := by decide

theorem selected_catalog_bijection : taskIds.length = 22 ∧ taskIds.Nodup := by decide

end Phase17TaskMeaning


namespace Phase17Provenance

/- Hashes, score-table construction and physical bindings are checked externally.
   This model checks deterministic present-prefix selection from the entire table.
   It does not attest that a historical process ran or furnish a full root step. -/
structure RankedProgram where
  key : String
  family : Nat
  baseScore : Int
  ties : List Nat
  deriving DecidableEq

structure Context where
  generator : String
  parentPackage : String
  contextHash : String
  transcriptHash : String
  credits : Nat
  offset : Nat
  rows : List RankedProgram
  deriving DecidableEq

structure Proposal where
  generator : String
  parentPackage : String
  contextHash : String
  transcriptHash : String
  choices : List Nat
  verdicts : List Bool
  program : String
  candidatePackage : String
  deriving DecidableEq

structure CandidateView where
  parentPackage : String
  contextHash : String
  program : String
  package : String
  deriving DecidableEq

def rowAt (c : Context) (i : Nat) : RankedProgram :=
  c.rows.getD i { key := "", family := 8, baseScore := 0, ties := [] }

def rejectedCount (c : Context) (seen : List Nat) (family : Nat) : Nat :=
  (seen.filter (fun i => (rowAt c i).family == family)).length

def score (c : Context) (seen : List Nat) (i : Nat) : Int :=
  (rowAt c i).baseScore + 797 * Int.ofNat (rejectedCount c seen (rowAt c i).family)

def tie (c : Context) (seen : List Nat) (i : Nat) : Nat :=
  (rowAt c i).ties.getD (rejectedCount c seen (rowAt c i).family) 0

def beats (c : Context) (seen : List Nat) (i j : Nat) : Bool :=
  decide (score c seen i > score c seen j ∨
    (score c seen i = score c seen j ∧ tie c seen i > tie c seen j) ∨
    (score c seen i = score c seen j ∧ tie c seen i = tie c seen j ∧ i > j))

def choose (c : Context) (seen : List Nat) : Option Nat :=
  if seen.length < 4 then
    match (List.range c.rows.length).filter (fun i => !seen.contains i) with
    | [] => none
    | first :: rest => some (rest.foldl (fun best i => if beats c seen i best then i else best) first)
  else
    ((List.range 32).map (fun i => (c.offset + 17 * i) % 32)).find? (fun i => !seen.contains i)

def follows (c : Context) (seen : List Nat) : List Nat → Bool
  | [] => true
  | i :: rest => (choose c seen == some i) && follows c (seen ++ [i]) rest

def ContextValid (c : Context) : Prop :=
  c.rows.length = 32 ∧ c.credits ≤ 32 ∧ c.offset < 32 ∧
  (c.rows.map (fun r => r.key)).Nodup ∧
  ∀ r ∈ c.rows, r.family < 8 ∧ r.ties.length = 5

def Produced (c : Context) (p : Proposal) : Prop :=
  p.generator = c.generator ∧ p.parentPackage = c.parentPackage ∧
  p.contextHash = c.contextHash ∧ p.transcriptHash = c.transcriptHash ∧
  ContextValid c ∧ follows c [] p.choices = true ∧ p.choices.Nodup ∧
  p.choices.length ≤ c.credits ∧ p.choices ≠ [] ∧
  p.verdicts = List.replicate (p.choices.length - 1) false ++ [true] ∧
  p.program = (rowAt c (p.choices.getD (p.choices.length - 1) 32)).key ∧
  p.candidatePackage ≠ p.parentPackage

def CandidateMatches (c : Context) (p : Proposal) (result : CandidateView) : Prop :=
  Produced c p ∧ result.parentPackage = c.parentPackage ∧
  result.contextHash = c.contextHash ∧ result.program = p.program ∧
  result.package = p.candidatePackage

theorem trace_no_repeat (c : Context) (p : Proposal) (h : Produced c p) :
    p.choices.Nodup := by
  rcases h with ⟨_, _, _, _, _, _, unique, _⟩
  exact unique

open RcpRclmFormalCoreV2 RcpRclmFormalCoreV3

/- Supplies the actual six provenance fields. The remaining compatible kernel and
   physical observation projections are parameters, not discharged premises. -/
def attachProvenance
    {State Update BaseCertificate Protected ResidualIndex Task : Type*}
    [DecidableEq Task]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    (other : Learned.FrontierKernel (Task := Task) (Generator := String)
      (Proposal := Proposal) (PackageHash := String) base)
    (observe : State → Context) (candidateView : RCP.Candidate State Update → CandidateView) :
    Learned.FrontierKernel (Task := Task) (Generator := String)
      (Proposal := Proposal) (PackageHash := String) base :=
  { other with
    activeGenerator := fun s => (observe s).generator
    activePackageHash := fun s => (observe s).parentPackage
    generatorBound := fun s g => g = (observe s).generator ∧ ContextValid (observe s)
    proposalProducedBy := fun g s p => g = (observe s).generator ∧ Produced (observe s) p
    proposalBindsCandidate := fun s p candidate => CandidateMatches (observe s) p (candidateView candidate)
    packageHashBound := fun s g hash => g = (observe s).generator ∧
      hash = (observe s).parentPackage ∧ ContextValid (observe s) }

theorem attached_generator_bound
    {State Update BaseCertificate Protected ResidualIndex Task : Type*}
    [DecidableEq Task]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    (other : Learned.FrontierKernel (Task := Task) (Generator := String)
      (Proposal := Proposal) (PackageHash := String) base)
    (observe : State → Context) (candidateView : RCP.Candidate State Update → CandidateView)
    (s : State) (valid : ContextValid (observe s)) :
    (attachProvenance other observe candidateView).generatorBound s
      ((attachProvenance other observe candidateView).activeGenerator s) := ⟨rfl, valid⟩

theorem attached_package_bound
    {State Update BaseCertificate Protected ResidualIndex Task : Type*}
    [DecidableEq Task]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    (other : Learned.FrontierKernel (Task := Task) (Generator := String)
      (Proposal := Proposal) (PackageHash := String) base)
    (observe : State → Context) (candidateView : RCP.Candidate State Update → CandidateView)
    (s : State) (valid : ContextValid (observe s)) :
    (attachProvenance other observe candidateView).packageHashBound s
      ((attachProvenance other observe candidateView).activeGenerator s)
      ((attachProvenance other observe candidateView).activePackageHash s) := ⟨rfl, rfl, valid⟩

theorem attached_proposal_produced
    {State Update BaseCertificate Protected ResidualIndex Task : Type*}
    [DecidableEq Task]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    (other : Learned.FrontierKernel (Task := Task) (Generator := String)
      (Proposal := Proposal) (PackageHash := String) base)
    (observe : State → Context) (candidateView : RCP.Candidate State Update → CandidateView)
    (s : State) (p : Proposal) (produced : Produced (observe s) p) :
    (attachProvenance other observe candidateView).proposalProducedBy
      ((attachProvenance other observe candidateView).activeGenerator s) s p := ⟨rfl, produced⟩

theorem attached_candidate_bound
    {State Update BaseCertificate Protected ResidualIndex Task : Type*}
    [DecidableEq Task]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    (other : Learned.FrontierKernel (Task := Task) (Generator := String)
      (Proposal := Proposal) (PackageHash := String) base)
    (observe : State → Context) (candidateView : RCP.Candidate State Update → CandidateView)
    (s : State) (p : Proposal) (candidate : RCP.Candidate State Update)
    (matched : CandidateMatches (observe s) p (candidateView candidate)) :
    (attachProvenance other observe candidateView).proposalBindsCandidate s p candidate := matched

end Phase17Provenance

namespace Phase17Provenance
set_option maxRecDepth 16384
set_option maxHeartbeats 4000000
def selectedContext : Context := { generator := "9cd3e747c0e1a93a02ac5bff1d3a07fa7706172ae4a75a0a373629260a675dc5", parentPackage := "6759cc828b5b8cb4af041e32dcba7b136849591e793802ab7f1f1cc2f2bcd535", contextHash := "6668900a9ec4dadb06e51489ea7a3751b801cab7ff9657a80bb44d74337cf2f6", transcriptHash := "16aee43b8b4f211f15917980d0d573e90a0d642427724271dd32e61ddeae1c0f", credits := 32, offset := 20, rows := [{ key := "0ccebe71727ce54ff3a19b21fe576e09d43e44f9e2e08ad36dcef047c1f79757", family := 7, baseScore := 19500, ties := [9543860648081008819, 3986821735351615470, 825746532280847598, 17001314346561978364, 13351325592102680237] }, { key := "0e14e91e830ffbf45bf7393807a5aade7d3ee8687c812c947e3cc2531cbf63ac", family := 0, baseScore := 19478, ties := [2478412217797925231, 4952073402234272453, 6410835891427668742, 7585352493249011854, 564345016447607857] }, { key := "1ecfac36f3c68428ba26508bca2f0c8db4a78db705c2389bf06c702fbd5f10b5", family := 4, baseScore := 19453, ties := [6926660447509656195, 15938766398069759487, 10415543623678175031, 13840774463448155652, 15518046404860127241] }, { key := "2cf62e580eb264801c146a82d7946b8ff3876c007ef906f4fa2ae155c2763933", family := 4, baseScore := 19511, ties := [8150133364245794037, 15602764634322946874, 13392954838966468289, 7903206724535872410, 10389729442995148786] }, { key := "2ecde82a7df7ff5575e47e129aa9f6763c0e9ee3000ef68a9e34d3c9597fe4a8", family := 7, baseScore := 19457, ties := [6267249027547442838, 11802557578107583196, 3573854276885852263, 4632763963828844255, 8078852471064255554] }, { key := "3c53b375ed7d796a6ead3f57edff0ca2bec48cd0d82d3f00e94891e20f67cf37", family := 2, baseScore := 19513, ties := [3711246983035555146, 9392402904921580765, 17780474027121794000, 3396803482688375717, 6849742246718093496] }, { key := "3d77cb7cac506bf87708193dfc6e6f77e291a65ef4827f51da60cad2816ac308", family := 1, baseScore := 19477, ties := [2649540343373259679, 6846808915173765847, 17515316580299738942, 17893706698655125100, 7295491786506786006] }, { key := "4022426ee83c2c3f99e3575db0b0dfdb2ee9c21d84c0dcd4bd16beddc79e9f1e", family := 2, baseScore := 19461, ties := [3367686222335547501, 2334632568370419648, 15738148556525812901, 13876416194485205561, 17090631277782618190] }, { key := "4677d24595acdc93eb98a8756accf75cc209e7cb65f3da91fc413998d938bc90", family := 1, baseScore := 19463, ties := [2408805383885846081, 15698376057770116370, 11965904924747752585, 14474548167273289030, 112542496099690264] }, { key := "4a94e6caf0ffc3e0042b150248d3b002375fe03953dbe05505f1eec92e7540f3", family := 5, baseScore := 19421, ties := [18026470090072901573, 8661548565402000749, 4104814434003148999, 12331012964429129284, 17835237858885086118] }, { key := "4e46438f039bc9e03f8418bb954a356470a2b7ab19cf6325098d1a3c84693436", family := 3, baseScore := 19482, ties := [9906582390397776349, 15344037628855689015, 11288843140053017474, 6981166375638331370, 16932492284211806416] }, { key := "5e093ff6378d7f51505e59154e642e54387f7e69536a47f038047309db2f21e4", family := 6, baseScore := 19469, ties := [12442890687401092662, 2810638280771006471, 4340151003288216385, 12539753374090342698, 12694902134990752429] }, { key := "62284df64ad409933f2b7fb08307d037bc75b0af758f5b3f81de191803d00c6d", family := 4, baseScore := 19488, ties := [17395010458261258995, 13841608280534480694, 6864139855934553582, 3515426712982889939, 501085376997440217] }, { key := "634b6e89afa828bd87e36e8862f536c3053b84fa776eb102c3dc8d948d6915e7", family := 3, baseScore := 19480, ties := [7443435974636069586, 17015840504638147347, 14078768256273083565, 923609335749601218, 2117103808860832839] }, { key := "64ce7d9730e3f4d704c430a159c9dbc6d4d405d89f1148508e443202b8d653c3", family := 6, baseScore := 19490, ties := [1825200460390365923, 7798173558651306652, 18374575800109165881, 9980076251569551113, 15175454222141752179] }, { key := "6ad7e6e11c5a715041c0d1e037b0d48ae072191e1433ae35c64e780231ecdc50", family := 1, baseScore := 19406, ties := [2288002094929966476, 9353561645136059924, 4702557895750206816, 5690668765208076663, 2663570918416143959] }, { key := "71c947eeb13f0c166058414f7b64faf6798de23a191e36126957cfaae536a0bd", family := 2, baseScore := 19466, ties := [6200852322706347257, 9820514042028955971, 7274442152615381451, 1379982242784742979, 1660428862859231517] }, { key := "74c67d91d381e32057f708cf07cb671d2575c852b66bd54c78ab0172577e888f", family := 1, baseScore := 19441, ties := [8540966648915212792, 13577434514563920436, 12284559500917620523, 8660986038877652935, 6678563798156207960] }, { key := "7936853f064d99b4c87ad0c017a502799a20b398a9948c9a4b71cae0642095e9", family := 5, baseScore := 19473, ties := [1005189969281360074, 15252314669334195950, 1677355114584468213, 14793242972975010867, 1700405426260283322] }, { key := "7cf429d12e04c55acef236646a2b0a8e5a0b3c13371df064c5d8dad2fbf5bb4f", family := 7, baseScore := 19475, ties := [8546551864574073392, 8090086383034992962, 9974530755710984380, 17559250649144876309, 10637278024437988078] }, { key := "7ec7d557c116962ac4a13ef48d12e24f0cb56c5262bae03a84c40d88cbc54d7d", family := 5, baseScore := 19463, ties := [16683943206201673779, 3943913173367315537, 15356282562439470394, 9003023824975183001, 2079802003204519093] }, { key := "836a08670cdfdcb082f55c64677c8eaca60a62d0005749e54e72eb67f94554c0", family := 0, baseScore := 19516, ties := [6430628686343350880, 3326988897348347730, 7288211664416347152, 17061342938759865996, 7836705224492594673] }, { key := "9862ef65bf4a9113a26f1734ad6ec98e0640eb6656cb1a4334972a2f9be1c6ac", family := 4, baseScore := 19502, ties := [8260079361839178878, 8008380571476166928, 7923025157480009945, 18281990603738430032, 10826349845351107097] }, { key := "a342c721f01211e03af69b331f4a012efb6a1efa012a406078278419e9272cc7", family := 5, baseScore := 19510, ties := [4766866663976868429, 3047071987004524432, 9940253806458247809, 4790087559697392821, 14286961818133190237] }, { key := "a4f37fb8f2f7d3a90829340f2f02b2f19dbc5dfa5caf7a7633e9092837265c0e", family := 6, baseScore := 19451, ties := [11688903147512217911, 13464938556235774340, 2096340461987256118, 7445147631916617319, 8748932342811588969] }, { key := "b1158ed7d34cfcad68c952f03a56102e7cb06b2c773129984a69e603960622d0", family := 2, baseScore := 19466, ties := [703329657200080849, 5361894098738257560, 15006032774167209900, 9873795357456281678, 10248833694836621885] }, { key := "c1f6e3e15772658a58c60b05772015054da09bb91580e62a49b4d0095f59eb66", family := 7, baseScore := 19494, ties := [7208938742527617328, 13755169071181738946, 2637320062845703835, 13818705467271995722, 7444373634666181866] }, { key := "c55761ed74319ddefeb28f554779813e19bb1f9accb4bc85be93b56f01c657e1", family := 3, baseScore := 19427, ties := [8088889808519105341, 936751310522426649, 6016279536750806828, 7984829587334844554, 14105222320240295221] }, { key := "df564cb25de35976dfcbef5e28404498aafd1fce538d0a8aa0e454cf96b11b59", family := 0, baseScore := 19500, ties := [8836220844570832805, 8448612075404267478, 8484827671774169061, 9590386969351737448, 2545991111721416260] }, { key := "e2654af87c885cf417002f13400f5bef1ac23eae87fd7b9fd479aae38f443d21", family := 0, baseScore := 19465, ties := [16012764203337167111, 7852343854022862808, 5709658358219961421, 6664323027437590972, 3243564184122138769] }, { key := "e7579f5e4f38614a40454dca7ae484ae24ab7ffa0d2a03d8ad282fcb7bead25c", family := 6, baseScore := 19462, ties := [13621612582292769046, 2862715562856875574, 10447682337024963304, 17667135270069867225, 15848566133317293010] }, { key := "f2a5dc234b5f195665d205b53e984e94ad894aa5b27e38b9056b9f03862d236b", family := 3, baseScore := 19468, ties := [8099424813576472301, 1776357734177914557, 1403918482063791230, 5144572711022291504, 2485642695817742413] }] }
def selectedProposal : Proposal := { generator := "9cd3e747c0e1a93a02ac5bff1d3a07fa7706172ae4a75a0a373629260a675dc5", parentPackage := "6759cc828b5b8cb4af041e32dcba7b136849591e793802ab7f1f1cc2f2bcd535", contextHash := "6668900a9ec4dadb06e51489ea7a3751b801cab7ff9657a80bb44d74337cf2f6", transcriptHash := "16aee43b8b4f211f15917980d0d573e90a0d642427724271dd32e61ddeae1c0f", choices := [21, 28, 1, 29, 20, 5, 22, 7, 24], verdicts := [false, false, false, false, false, false, false, false, true], program := "a4f37fb8f2f7d3a90829340f2f02b2f19dbc5dfa5caf7a7633e9092837265c0e", candidatePackage := "b4036b3e31a6608e30b421c08906b1e58c3e7d61fef6eb6730881c597656434e" }
def selectedCandidate : CandidateView := { parentPackage := "6759cc828b5b8cb4af041e32dcba7b136849591e793802ab7f1f1cc2f2bcd535", contextHash := "6668900a9ec4dadb06e51489ea7a3751b801cab7ff9657a80bb44d74337cf2f6", program := "a4f37fb8f2f7d3a90829340f2f02b2f19dbc5dfa5caf7a7633e9092837265c0e", package := "b4036b3e31a6608e30b421c08906b1e58c3e7d61fef6eb6730881c597656434e" }

theorem selected_provenance : Produced selectedContext selectedProposal := by
  unfold Produced ContextValid
  decide

theorem selected_candidate_binding :
    CandidateMatches selectedContext selectedProposal selectedCandidate := by
  unfold CandidateMatches
  refine ⟨selected_provenance, ?_, ?_, ?_, ?_⟩ <;> decide

theorem selected_rejection_prefix :
    selectedProposal.verdicts = List.replicate (selectedProposal.choices.length - 1) false ++ [true] := by decide

end Phase17Provenance

/- This template is appended after the pinned, regenerated typed/task/provenance
   source bodies. It does not import a historical successful result as evidence.
   All remaining base, goal, resource and information premises stay explicit. -/
namespace Phase17Joint

open RcpRclmFormalCoreV2 RcpRclmFormalCoreV3

/-- One kernel receives both adapters, rather than two unrelated kernels. -/
def compose
    {State Update BaseCertificate Protected ResidualIndex : Type*}
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    (other : Learned.FrontierKernel (Task := Nat) (Generator := String)
      (Proposal := Phase17Provenance.Proposal) (PackageHash := String) base)
    (observeTasks : State → Phase17TaskMeaning.ObservationState)
    (declared : State → Finset Nat) (catalog : Nat → Phase17TaskMeaning.Meaning)
    (context : State → Phase17Provenance.Context)
    (candidateView : RCP.Candidate State Update → Phase17Provenance.CandidateView) :=
  Phase17Provenance.attachProvenance
    (Phase17TaskMeaning.attachTaskSemantics other observeTasks declared catalog)
    context candidateView

theorem composed_frontier_sound
    {State Update BaseCertificate Protected ResidualIndex : Type*}
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    (other : Learned.FrontierKernel (Task := Nat) (Generator := String)
      (Proposal := Phase17Provenance.Proposal) (PackageHash := String) base)
    (observeTasks : State → Phase17TaskMeaning.ObservationState)
    (declared : State → Finset Nat) (catalog : Nat → Phase17TaskMeaning.Meaning)
    (context : State → Phase17Provenance.Context)
    (candidateView : RCP.Candidate State Update → Phase17Provenance.CandidateView)
    {s : State} {task : Nat}
    (member : task ∈ (compose other observeTasks declared catalog context candidateView).frontier s) :
    (catalog task).holds (observeTasks s) :=
  (compose other observeTasks declared catalog context candidateView).frontierSound member

theorem composed_provenance_bound
    {State Update BaseCertificate Protected ResidualIndex : Type*}
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    (other : Learned.FrontierKernel (Task := Nat) (Generator := String)
      (Proposal := Phase17Provenance.Proposal) (PackageHash := String) base)
    (observeTasks : State → Phase17TaskMeaning.ObservationState)
    (declared : State → Finset Nat) (catalog : Nat → Phase17TaskMeaning.Meaning)
    (context : State → Phase17Provenance.Context)
    (candidateView : RCP.Candidate State Update → Phase17Provenance.CandidateView)
    (s : State) (p : Phase17Provenance.Proposal)
    (valid : Phase17Provenance.ContextValid (context s))
    (produced : Phase17Provenance.Produced (context s) p) :
    (compose other observeTasks declared catalog context candidateView).generatorBound s (context s).generator ∧
    (compose other observeTasks declared catalog context candidateView).proposalProducedBy
      (context s).generator s p :=
  ⟨⟨rfl, valid⟩, ⟨rfl, produced⟩⟩

/-- Composition does not replace open semantic/resource fields with constants. -/
theorem remaining_semantics_unchanged
    {State Update BaseCertificate Protected ResidualIndex : Type*}
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    (other : Learned.FrontierKernel (Task := Nat) (Generator := String)
      (Proposal := Phase17Provenance.Proposal) (PackageHash := String) base)
    (observeTasks : State → Phase17TaskMeaning.ObservationState)
    (declared : State → Finset Nat) (catalog : Nat → Phase17TaskMeaning.Meaning)
    (context : State → Phase17Provenance.Context)
    (candidateView : RCP.Candidate State Update → Phase17Provenance.CandidateView) :
    (compose other observeTasks declared catalog context candidateView).goalDrift = other.goalDrift ∧
    (compose other observeTasks declared catalog context candidateView).goalDriftBudget = other.goalDriftBudget ∧
    (compose other observeTasks declared catalog context candidateView).resourceUsed = other.resourceUsed ∧
    (compose other observeTasks declared catalog context candidateView).resourceBudget = other.resourceBudget ∧
    (compose other observeTasks declared catalog context candidateView).informationValue = other.informationValue ∧
    (compose other observeTasks declared catalog context candidateView).informationBudget = other.informationBudget :=
  ⟨rfl, rfl, rfl, rfl, rfl, rfl⟩

def certificate
    {State Update BaseCertificate Protected ResidualIndex : Type*}
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    (other : Learned.FrontierKernel (Task := Nat) (Generator := String)
      (Proposal := Phase17Provenance.Proposal) (PackageHash := String) base)
    (observeTasks : State → Phase17TaskMeaning.ObservationState)
    (declared : State → Finset Nat) (catalog : Nat → Phase17TaskMeaning.Meaning)
    (context : State → Phase17Provenance.Context)
    (candidateView : RCP.Candidate State Update → Phase17Provenance.CandidateView)
    (s : State) (p : Phase17Provenance.Proposal) (baseCertificate : BaseCertificate) :
    Learned.CertificatePacket BaseCertificate Nat String Phase17Provenance.Proposal String :=
  { base := baseCertificate
    protectedFrontier := (compose other observeTasks declared catalog context candidateView).frontier s
    generator := (context s).generator
    proposal := p
    generatorPackageHash := (context s).parentPackage }

/-- Actual LearnedAcceptedStep constructor, CONDITIONAL on all remaining premises.
    It is not instantiated for a physical transition by this development gate. -/
theorem assemble_learned_step
    {State Update BaseCertificate Protected ResidualIndex : Type*}
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    (other : Learned.FrontierKernel (Task := Nat) (Generator := String)
      (Proposal := Phase17Provenance.Proposal) (PackageHash := String) base)
    (observeTasks : State → Phase17TaskMeaning.ObservationState)
    (declared : State → Finset Nat) (catalog : Nat → Phase17TaskMeaning.Meaning)
    (context : State → Phase17Provenance.Context)
    (candidateView : RCP.Candidate State Update → Phase17Provenance.CandidateView)
    (s : State) (candidate : RCP.Candidate State Update)
    (p : Phase17Provenance.Proposal) (baseCertificate : BaseCertificate)
    (valid : Phase17Provenance.ContextValid (context s))
    (produced : Phase17Provenance.Produced (context s) p)
    (matched : Phase17Provenance.CandidateMatches (context s) p (candidateView candidate))
    (expansion : Learned.StrictFrontierExpansion
      (compose other observeTasks declared catalog context candidateView) s candidate)
    (baseProof : RCP.StepObligations base s candidate baseCertificate)
    (goal : other.goalDrift s candidate ≤ other.goalDriftBudget s candidate)
    (resources : other.resourceUsed s candidate ≤ other.resourceBudget s candidate)
    (information : other.informationValue candidate.next ≤
      other.informationValue s + other.informationBudget s candidate) :
    Learned.LearnedAcceptedStep
      (compose other observeTasks declared catalog context candidateView) s candidate
      (certificate other observeTasks declared catalog context candidateView s p baseCertificate) := by
  exact {
    baseObligations := baseProof
    learnedObligations := {
      protectedFrontierCertified := by intro task h; exact h
      protectedFrontierRetained := expansion.1
      strictFrontierExpansion := expansion
      generatorIsActive := rfl
      generatorBound := ⟨rfl, valid⟩
      proposalProduced := ⟨rfl, produced⟩
      proposalBindsCandidate := matched
      packageHashIsActive := rfl
      packageHashBound := ⟨rfl, rfl, valid⟩
      goalDriftWithinBudget := goal
      resourceWithinBudget := resources
      informationNonRegression := information } }

structure Binding where
  historicalState : String
  predecessor : String
  candidate : String
  transcript : String
  program : String
  objective : String
  challenge : String
  deriving DecidableEq

end Phase17Joint

namespace Phase17Joint
set_option maxRecDepth 16384
set_option maxHeartbeats 8000000
-- Joint capsule SHA256: 035c570a3e4b7f1ed2fd43085d9cd6357b2596a169eebcd621c0ff5d0fe274ac
def typedBinding : Binding := { historicalState := "7d2b823c05e4e4cef7566a89d3d440dba60a6417c6a3401f1248e59f89e91567", predecessor := "6759cc828b5b8cb4af041e32dcba7b136849591e793802ab7f1f1cc2f2bcd535", candidate := "b4036b3e31a6608e30b421c08906b1e58c3e7d61fef6eb6730881c597656434e", transcript := "16aee43b8b4f211f15917980d0d573e90a0d642427724271dd32e61ddeae1c0f", program := "a4f37fb8f2f7d3a90829340f2f02b2f19dbc5dfa5caf7a7633e9092837265c0e", objective := "e6a40e7a55002356e5a5c35262b35a7e98f54e9aa1153db60945215d56e941d3", challenge := "478d7884588779bca1483fb65d06d2a4b4d430960c47a6fdfd8036fb8a39c2ab" }
def taskBinding : Binding := { historicalState := "7d2b823c05e4e4cef7566a89d3d440dba60a6417c6a3401f1248e59f89e91567", predecessor := "6759cc828b5b8cb4af041e32dcba7b136849591e793802ab7f1f1cc2f2bcd535", candidate := "b4036b3e31a6608e30b421c08906b1e58c3e7d61fef6eb6730881c597656434e", transcript := "16aee43b8b4f211f15917980d0d573e90a0d642427724271dd32e61ddeae1c0f", program := "a4f37fb8f2f7d3a90829340f2f02b2f19dbc5dfa5caf7a7633e9092837265c0e", objective := "e6a40e7a55002356e5a5c35262b35a7e98f54e9aa1153db60945215d56e941d3", challenge := "478d7884588779bca1483fb65d06d2a4b4d430960c47a6fdfd8036fb8a39c2ab" }
def producerBinding : Binding := { historicalState := "7d2b823c05e4e4cef7566a89d3d440dba60a6417c6a3401f1248e59f89e91567", predecessor := "6759cc828b5b8cb4af041e32dcba7b136849591e793802ab7f1f1cc2f2bcd535", candidate := "b4036b3e31a6608e30b421c08906b1e58c3e7d61fef6eb6730881c597656434e", transcript := "16aee43b8b4f211f15917980d0d573e90a0d642427724271dd32e61ddeae1c0f", program := "a4f37fb8f2f7d3a90829340f2f02b2f19dbc5dfa5caf7a7633e9092837265c0e", objective := "e6a40e7a55002356e5a5c35262b35a7e98f54e9aa1153db60945215d56e941d3", challenge := "478d7884588779bca1483fb65d06d2a4b4d430960c47a6fdfd8036fb8a39c2ab" }

theorem selected_shared_identity :
    typedBinding = taskBinding ∧ taskBinding = producerBinding ∧
    typedBinding.predecessor = Phase17LearnedBinding.observedBefore.packageHash ∧
    typedBinding.candidate = Phase17LearnedBinding.observedAfter.packageHash ∧
    producerBinding.predecessor = Phase17Provenance.selectedContext.parentPackage ∧
    producerBinding.candidate = Phase17Provenance.selectedCandidate.package ∧
    producerBinding.transcript = Phase17Provenance.selectedContext.transcriptHash ∧
    producerBinding.program = Phase17Provenance.selectedProposal.program ∧
    typedBinding.program = Phase17LearnedBinding.addedKey ∧
    Phase17LearnedBinding.addedTask = Phase17TaskMeaning.taskIds.getD 21 "" := by
  decide

theorem selected_joint_facts :
    Phase17LearnedBinding.frozenView Phase17LearnedBinding.observedAfter =
      Phase17LearnedBinding.frozenView Phase17LearnedBinding.observedBefore ∧
    (Phase17TaskMeaning.checkedFrontier Phase17TaskMeaning.beforeDeclared
      Phase17TaskMeaning.catalog Phase17TaskMeaning.before ⊆
     Phase17TaskMeaning.checkedFrontier Phase17TaskMeaning.afterDeclared
      Phase17TaskMeaning.catalog Phase17TaskMeaning.after) ∧
    (Phase17TaskMeaning.checkedFrontier Phase17TaskMeaning.beforeDeclared
      Phase17TaskMeaning.catalog Phase17TaskMeaning.before).card <
     (Phase17TaskMeaning.checkedFrontier Phase17TaskMeaning.afterDeclared
      Phase17TaskMeaning.catalog Phase17TaskMeaning.after).card ∧
    Phase17Provenance.Produced Phase17Provenance.selectedContext Phase17Provenance.selectedProposal ∧
    Phase17Provenance.CandidateMatches Phase17Provenance.selectedContext
      Phase17Provenance.selectedProposal Phase17Provenance.selectedCandidate :=
  ⟨Phase17LearnedBinding.selected_typed_binding.1,
   Phase17TaskMeaning.selected_frontier_retention,
   Phase17TaskMeaning.selected_frontier_expansion,
   Phase17Provenance.selected_provenance,
   Phase17Provenance.selected_candidate_binding⟩

end Phase17Joint


/- Exact semantics of the DECLARED inherited 260-token sparse profile.
   The complete RCLM kernel and physical observation refinement are not supplied.
   Natural entries encode positive unnormalized weights minus one. -/
namespace Phase17Protected

open scoped BigOperators
open RcpRclmFormalCoreV2 RcpRclmFormalCoreV3

abbrev Token := Fin 260

def weight (row : List Nat) (i : Token) : Nat := row.getD i.val 0 + 1
noncomputable def total (row : List Nat) : ℝ := ∑ i : Token, (weight row i : ℝ)

theorem total_positive (row : List Nat) : 0 < total row := by
  unfold total
  apply Finset.sum_pos
  · intro i _
    exact_mod_cast (Nat.succ_pos (row.getD i.val 0))
  · exact ⟨⟨0, by decide⟩, Finset.mem_univ _⟩

noncomputable def distribution (row : List Nat) : RCP.ClassicalFinite.PositiveDistribution 260 where
  distribution :=
    { mass := fun i => (weight row i : ℝ) / total row
      nonnegative := by
        intro i
        exact div_nonneg (Nat.cast_nonneg _) (total_positive row).le
      normalized := by
        rw [← Finset.sum_div]
        exact div_self (ne_of_gt (total_positive row)) }
  positive := by
    intro i
    apply div_pos
    · exact_mod_cast (Nat.succ_pos (row.getD i.val 0))
    · exact total_positive row

theorem mass_distribution_normalized (row : List Nat) :
    (∑ i : Token, (distribution row).distribution.mass i) = 1 :=
  (distribution row).distribution.normalized

noncomputable def density (row : List Nat) : RCP.QuantumFinite.DiagonalDensityMatrix 260 :=
  ⟨(distribution row).distribution⟩

theorem diagonal_density_sound (row : List Nat) :
    RCP.QuantumFinite.DensityMatrixEvidence (density row).matrix :=
  (density row).densityEvidence

theorem diagonal_information_is_kl (row target : List Nat) :
    RCP.QuantumFinite.quantumRelativeEntropy (density row) (density target) =
      RCP.ClassicalFinite.positiveKLDivergence (distribution row) (distribution target) ∧
    RCP.QuantumFinite.vonNeumannEntropy (density row) =
      RCP.ClassicalFinite.shannonEntropy (distribution row).distribution :=
  ⟨rfl, rfl⟩

structure Observation where
  rows : List (List Nat)
  selectors : List Nat
  goals : List (List Nat)
  deriving DecidableEq

structure Contract where
  positions : List (Nat × Nat)
  expectedGoals : List (List Nat)
  deriving DecidableEq

def rowAt (o : Observation) (current : Nat) : List Nat :=
  o.rows.getD (o.selectors.getD current 0) []

def targetRow (target : Nat) : List Nat :=
  (List.range 260).map (fun i => if i = target then 4095 else 0)

noncomputable def informationSum (o : Observation) : List (Nat × Nat) → ℝ
  | [] => 0
  | (current, target) :: rest =>
      RCP.ClassicalFinite.positiveKLDivergence
        (distribution (rowAt o current)) (distribution (targetRow target)) + informationSum o rest

noncomputable def informationValue (contract : Contract) (o : Observation) : ℝ :=
  informationSum o contract.positions

theorem information_sum_nonnegative (o : Observation) (positions : List (Nat × Nat)) :
    0 ≤ informationSum o positions := by
  induction positions with
  | nil => exact le_rfl
  | cons pair rest ih =>
    rcases pair with ⟨current, target⟩
    exact add_nonneg (RCP.ClassicalFinite.positiveKLDivergence_nonnegative _ _) ih

def goalDistance : List (List Nat) → List (List Nat) → Nat
  | [], ys => ys.length
  | _ :: xs, [] => xs.length + 1
  | x :: xs, y :: ys => (if x = y then 0 else 1) + goalDistance xs ys

theorem goal_distance_self (goals : List (List Nat)) : goalDistance goals goals = 0 := by
  induction goals with
  | nil => rfl
  | cons row rest ih => simp [goalDistance, ih]

/- These are explicit protected-profile fields with a zero-regression policy.
   Resource fields and all capability/provenance fields are left unchanged. -/
noncomputable def attach
    {State Update BaseCertificate Protected ResidualIndex Task Generator Proposal PackageHash : Type*}
    [DecidableEq Task]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    (other : Learned.FrontierKernel (Task := Task) (Generator := Generator)
      (Proposal := Proposal) (PackageHash := PackageHash) base)
    (observe : State → Observation) (contract : Contract) :
    Learned.FrontierKernel (Task := Task) (Generator := Generator)
      (Proposal := Proposal) (PackageHash := PackageHash) base :=
  { other with
    goalDrift := fun s c => goalDistance (observe s).goals (observe c.next).goals
    goalDriftBudget := fun _ _ => 0
    informationValue := fun s => informationValue contract (observe s)
    informationBudget := fun _ _ => 0
    informationBudget_nonnegative := fun _ _ => le_rfl }

theorem unrelated_root_fields_unchanged
    {State Update BaseCertificate Protected ResidualIndex Task Generator Proposal PackageHash : Type*}
    [DecidableEq Task]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    (other : Learned.FrontierKernel (Task := Task) (Generator := Generator)
      (Proposal := Proposal) (PackageHash := PackageHash) base)
    (observe : State → Observation) (contract : Contract) :
    (attach other observe contract).resourceUsed = other.resourceUsed ∧
    (attach other observe contract).resourceBudget = other.resourceBudget ∧
    (attach other observe contract).frontier = other.frontier ∧
    (attach other observe contract).solves = other.solves ∧
    (attach other observe contract).activeGenerator = other.activeGenerator ∧
    (attach other observe contract).proposalProducedBy = other.proposalProducedBy ∧
    (attach other observe contract).proposalBindsCandidate = other.proposalBindsCandidate :=
  ⟨rfl, rfl, rfl, rfl, rfl, rfl, rfl⟩

theorem attached_protected_bounds
    {State Update BaseCertificate Protected ResidualIndex Task Generator Proposal PackageHash : Type*}
    [DecidableEq Task]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    (other : Learned.FrontierKernel (Task := Task) (Generator := Generator)
      (Proposal := Proposal) (PackageHash := PackageHash) base)
    (observe : State → Observation) (contract : Contract)
    (s : State) (c : RCP.Candidate State Update)
    (retained : observe c.next = observe s) :
    (attach other observe contract).goalDrift s c ≤ (attach other observe contract).goalDriftBudget s c ∧
    (attach other observe contract).informationValue c.next ≤
      (attach other observe contract).informationValue s + (attach other observe contract).informationBudget s c := by
  change goalDistance (observe s).goals (observe c.next).goals ≤ 0 ∧
    informationValue contract (observe c.next) ≤ informationValue contract (observe s) + 0
  rw [retained, goal_distance_self, add_zero]
  exact ⟨le_rfl, le_rfl⟩

def WellFormed (o : Observation) : Prop :=
  o.selectors.length = 260 ∧ (∀ i ∈ o.selectors, i < o.rows.length) ∧
  (∀ r ∈ o.rows, r.length = 260) ∧ o.goals.length = 11

end Phase17Protected

namespace Phase17Protected
open RcpRclmFormalCoreV2
set_option maxRecDepth 16384
set_option maxHeartbeats 8000000
-- Prepared semantic packet SHA256: a720bdaeac1b316d6e50b9a640cddfad52baff44c09a44a4fdeda2b977e4da67
def observedBefore : Observation := { rows := [[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 16383, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]], selectors := [0, 1, 2, 3, 4, 5, 2, 6, 4, 0, 2, 7, 4, 8, 2, 8, 4, 9, 2, 10, 4, 1, 11, 12, 11, 13, 11, 14, 15, 11, 1, 11, 1, 2, 16, 4, 0, 2, 17, 4, 18, 2, 19, 4, 1, 2, 20, 4, 1, 21, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 23, 22, 22, 24, 25, 26, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 21, 22, 22, 22, 27, 28, 29, 22, 22, 22, 22, 21, 30, 22, 31, 22, 21, 32, 22, 22, 22, 22, 22, 22, 22, 21, 22, 22, 22, 22, 22, 0, 1, 2, 3, 4, 5, 2, 6, 4, 33, 34, 19, 20, 2, 7, 4, 8, 2, 8, 4, 9, 2, 10, 4, 1, 11, 12, 11, 1, 11, 14, 15, 11, 1, 11, 1, 2, 16, 4, 33, 34, 19, 20, 2, 17, 4, 18, 2, 19, 4, 13, 2, 20, 4, 13, 21, 22, 22, 22, 22, 22, 22, 22, 22, 0, 1, 2, 3, 4, 5, 2, 6, 4, 33, 34, 35, 19, 20, 2, 7, 4, 8, 2, 8, 4, 9, 2, 10, 4, 1, 11, 12, 11, 1, 11, 14, 15, 11, 1, 11, 1, 2, 16, 4, 36, 34, 35, 19, 20, 2, 17, 4, 18, 2, 19, 4, 13, 2, 20, 4, 13, 21, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22], goals := [[79, 111, 109, 101, 103, 97, 258], [82, 114, 102, 108, 258], [83, 122, 258], [84, 113, 258], [84, 113, 258], [84, 113, 258], [84, 113, 258], [84, 113, 258], [84, 113, 258], [84, 113, 258], [84, 113, 258]] }
def observedAfter : Observation := { rows := [[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 16383, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]], selectors := [0, 1, 2, 3, 4, 5, 2, 6, 4, 0, 2, 7, 4, 8, 2, 8, 4, 9, 2, 10, 4, 1, 11, 12, 11, 13, 11, 14, 15, 11, 1, 11, 1, 2, 16, 4, 0, 2, 17, 4, 18, 2, 19, 4, 1, 2, 20, 4, 1, 21, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 23, 22, 22, 24, 25, 26, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 21, 22, 22, 22, 27, 28, 29, 22, 22, 22, 22, 21, 30, 22, 31, 22, 21, 32, 22, 22, 22, 22, 22, 22, 22, 21, 22, 22, 22, 22, 22, 0, 1, 2, 3, 4, 5, 2, 6, 4, 33, 34, 19, 20, 2, 7, 4, 8, 2, 8, 4, 9, 2, 10, 4, 1, 11, 12, 11, 1, 11, 14, 15, 11, 1, 11, 1, 2, 16, 4, 33, 34, 19, 20, 2, 17, 4, 18, 2, 19, 4, 13, 2, 20, 4, 13, 21, 22, 22, 22, 22, 22, 22, 22, 22, 0, 1, 2, 3, 4, 5, 2, 6, 4, 33, 34, 35, 19, 20, 2, 7, 4, 8, 2, 8, 4, 9, 2, 10, 4, 1, 11, 12, 11, 1, 11, 14, 15, 11, 1, 11, 1, 2, 16, 4, 36, 34, 35, 19, 20, 2, 17, 4, 18, 2, 19, 4, 13, 2, 20, 4, 13, 21, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22], goals := [[79, 111, 109, 101, 103, 97, 258], [82, 114, 102, 108, 258], [83, 122, 258], [84, 113, 258], [84, 113, 258], [84, 113, 258], [84, 113, 258], [84, 113, 258], [84, 113, 258], [84, 113, 258], [84, 113, 258]] }
def selectedContract : Contract := { positions := [(79, 111), (111, 109), (109, 101), (101, 103), (103, 97), (97, 258), (82, 114), (114, 102), (102, 108), (108, 258), (83, 122), (122, 258), (84, 113), (113, 258), (84, 113), (113, 258), (84, 113), (113, 258), (84, 113), (113, 258), (84, 113), (113, 258), (84, 113), (113, 258), (84, 113), (113, 258), (84, 113), (113, 258)], expectedGoals := [[79, 111, 109, 101, 103, 97, 258], [82, 114, 102, 108, 258], [83, 122, 258], [84, 113, 258], [84, 113, 258], [84, 113, 258], [84, 113, 258], [84, 113, 258], [84, 113, 258], [84, 113, 258], [84, 113, 258]] }
def boundContract : Contract := { positions := [(79, 111), (111, 109), (109, 101), (101, 103), (103, 97), (97, 258), (82, 114), (114, 102), (102, 108), (108, 258), (83, 122), (122, 258), (84, 113), (113, 258), (84, 113), (113, 258), (84, 113), (113, 258), (84, 113), (113, 258), (84, 113), (113, 258), (84, 113), (113, 258), (84, 113), (113, 258), (84, 113), (113, 258)], expectedGoals := [[79, 111, 109, 101, 103, 97, 258], [82, 114, 102, 108, 258], [83, 122, 258], [84, 113, 258], [84, 113, 258], [84, 113, 258], [84, 113, 258], [84, 113, 258], [84, 113, 258], [84, 113, 258], [84, 113, 258]] }
def jointBinding : List String := ["7d2b823c05e4e4cef7566a89d3d440dba60a6417c6a3401f1248e59f89e91567", "6759cc828b5b8cb4af041e32dcba7b136849591e793802ab7f1f1cc2f2bcd535", "b4036b3e31a6608e30b421c08906b1e58c3e7d61fef6eb6730881c597656434e", "16aee43b8b4f211f15917980d0d573e90a0d642427724271dd32e61ddeae1c0f", "a4f37fb8f2f7d3a90829340f2f02b2f19dbc5dfa5caf7a7633e9092837265c0e", "e6a40e7a55002356e5a5c35262b35a7e98f54e9aa1153db60945215d56e941d3", "478d7884588779bca1483fb65d06d2a4b4d430960c47a6fdfd8036fb8a39c2ab", "af34fb682a920122318f001bf2b76e826244f38202d0377f99f65515e4a14e28", "035c570a3e4b7f1ed2fd43085d9cd6357b2596a169eebcd621c0ff5d0fe274ac"]
def semanticBinding : List String := ["7d2b823c05e4e4cef7566a89d3d440dba60a6417c6a3401f1248e59f89e91567", "6759cc828b5b8cb4af041e32dcba7b136849591e793802ab7f1f1cc2f2bcd535", "b4036b3e31a6608e30b421c08906b1e58c3e7d61fef6eb6730881c597656434e", "16aee43b8b4f211f15917980d0d573e90a0d642427724271dd32e61ddeae1c0f", "a4f37fb8f2f7d3a90829340f2f02b2f19dbc5dfa5caf7a7633e9092837265c0e", "e6a40e7a55002356e5a5c35262b35a7e98f54e9aa1153db60945215d56e941d3", "478d7884588779bca1483fb65d06d2a4b4d430960c47a6fdfd8036fb8a39c2ab", "af34fb682a920122318f001bf2b76e826244f38202d0377f99f65515e4a14e28", "035c570a3e4b7f1ed2fd43085d9cd6357b2596a169eebcd621c0ff5d0fe274ac"]

theorem selected_wellformed : WellFormed observedBefore ∧ WellFormed observedAfter := by
  unfold WellFormed
  decide

theorem selected_targets_bound : selectedContract = boundContract ∧
    observedBefore.goals = boundContract.expectedGoals ∧
    boundContract.positions.length = 28 ∧
    (∀ pair ∈ boundContract.positions, pair.1 < 260 ∧ pair.2 < 260) := by decide

theorem selected_observation_retained : observedAfter = observedBefore := by decide

theorem selected_goal_bound : goalDistance observedBefore.goals observedAfter.goals ≤ 0 := by decide

theorem selected_information_bound : informationValue selectedContract observedAfter ≤
    informationValue selectedContract observedBefore + 0 := by
  simpa only [selected_observation_retained, add_zero] using
    (le_refl (informationValue selectedContract observedBefore))

theorem selected_distribution_entropy_retention (current : Token) (target : List Nat) :
    (density (rowAt observedAfter current.val)).distribution =
      (density (rowAt observedBefore current.val)).distribution ∧
    RCP.QuantumFinite.vonNeumannEntropy (density (rowAt observedAfter current.val)) =
      RCP.QuantumFinite.vonNeumannEntropy (density (rowAt observedBefore current.val)) ∧
    RCP.QuantumFinite.quantumRelativeEntropy (density (rowAt observedAfter current.val)) (density target) =
      RCP.QuantumFinite.quantumRelativeEntropy (density (rowAt observedBefore current.val)) (density target) := by
  rw [selected_observation_retained]
  exact ⟨rfl, rfl, rfl⟩

theorem selected_transaction_binding : semanticBinding = jointBinding := by decide

end Phase17Protected


/- Phase 17N: declared reference-work tariffs, not physical resource totals.
   Journal persistence, extraction and actual execution are external bindings. -/
namespace Phase17Resource
open RcpRclmFormalCoreV2 RcpRclmFormalCoreV3

inductive Kind where
  | candidate
  | vector
  deriving DecidableEq

abbrev Dimension := Fin 4

def tariff (k : Kind) (i : Dimension) : Nat :=
  match k, i.val with
  | .candidate, 0 => 1
  | .vector, 1 => 1
  | .vector, 2 => 4
  | .vector, 3 => 4
  | _, _ => 0

def unitCost : Kind → Nat
  | .candidate => 64
  | .vector => 24

def counter (xs : List Kind) (i : Dimension) : Nat :=
  (xs.map (fun k => tariff k i)).sum

def totalCost (xs : List Kind) : Nat := (xs.map unitCost).sum

structure Policy where
  limits : Dimension → Nat
  costLimit : Nat

def Fits (p : Policy) (xs : List Kind) : Prop :=
  totalCost xs ≤ p.costLimit ∧ ∀ i, counter xs i ≤ p.limits i

theorem cost_matches_weighted_counters (xs : List Kind) :
    totalCost xs = 64 * counter xs 0 + 16 * counter xs 1 + counter xs 2 + counter xs 3 := by
  induction xs with
  | nil => simp [totalCost, counter]
  | cons k rest ih =>
    cases k <;> simp [totalCost, counter, unitCost, tariff] at * <;> omega

theorem counter_prefix_non_decreasing (xs ys : List Kind) (i : Dimension) :
    counter xs i ≤ counter (xs ++ ys) i := by
  simp only [counter, List.map_append, List.sum_append]
  omega

theorem cost_prefix_non_decreasing (xs ys : List Kind) :
    totalCost xs ≤ totalCost (xs ++ ys) := by
  simp only [totalCost, List.map_append, List.sum_append]
  omega

theorem bounded_final_implies_bounded_prefix (p : Policy) (xs ys : List Kind)
    (h : Fits p (xs ++ ys)) : Fits p xs := by
  exact ⟨le_trans (cost_prefix_non_decreasing xs ys) h.1,
    fun i => le_trans (counter_prefix_non_decreasing xs ys i) (h.2 i)⟩

theorem over_budget_excluded (p : Policy) (xs : List Kind)
    (exceeded : p.costLimit < totalCost xs) : ¬ Fits p xs := by
  intro h
  exact (Nat.not_le_of_gt exceeded) h.1

theorem appended_charge_not_refunded (xs : List Kind) (k : Kind) :
    totalCost xs ≤ totalCost (xs ++ [k]) :=
  cost_prefix_non_decreasing xs [k]

/- Only resourceUsed/resourceBudget are supplied by this adapter. The concrete
   base, goal/information, frontier and producer obligations remain unchanged. -/
noncomputable def attach
    {State Update BaseCertificate Protected ResidualIndex Task Generator Proposal PackageHash : Type*}
    [DecidableEq Task]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    (other : Learned.FrontierKernel (Task := Task) (Generator := Generator)
      (Proposal := Proposal) (PackageHash := PackageHash) base)
    (charges : State → RCP.Candidate State Update → List Kind)
    (policy : State → RCP.Candidate State Update → Policy) :
    Learned.FrontierKernel (Task := Task) (Generator := Generator)
      (Proposal := Proposal) (PackageHash := PackageHash) base :=
  { other with
    resourceUsed := fun s c => totalCost (charges s c)
    resourceBudget := fun s c => (policy s c).costLimit }

theorem unrelated_fields_unchanged
    {State Update BaseCertificate Protected ResidualIndex Task Generator Proposal PackageHash : Type*}
    [DecidableEq Task]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    (other : Learned.FrontierKernel (Task := Task) (Generator := Generator)
      (Proposal := Proposal) (PackageHash := PackageHash) base)
    (charges : State → RCP.Candidate State Update → List Kind)
    (policy : State → RCP.Candidate State Update → Policy) :
    (attach other charges policy).goalDrift = other.goalDrift ∧
    (attach other charges policy).informationValue = other.informationValue ∧
    (attach other charges policy).frontier = other.frontier ∧
    (attach other charges policy).proposalProducedBy = other.proposalProducedBy ∧
    (attach other charges policy).proposalBindsCandidate = other.proposalBindsCandidate :=
  ⟨rfl, rfl, rfl, rfl, rfl⟩

theorem attached_resource_bound
    {State Update BaseCertificate Protected ResidualIndex Task Generator Proposal PackageHash : Type*}
    [DecidableEq Task]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    (other : Learned.FrontierKernel (Task := Task) (Generator := Generator)
      (Proposal := Proposal) (PackageHash := PackageHash) base)
    (charges : State → RCP.Candidate State Update → List Kind)
    (policy : State → RCP.Candidate State Update → Policy)
    (s : State) (c : RCP.Candidate State Update)
    (h : Fits (policy s c) (charges s c)) :
    (attach other charges policy).resourceUsed s c ≤ (attach other charges policy).resourceBudget s c :=
  h.1

end Phase17Resource
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

namespace Phase17Finite
open RcpRclmFormalCoreV2 RcpRclmFormalCoreV3
set_option maxRecDepth 32768
set_option maxHeartbeats 16000000
-- Fresh Q packet SHA256: b6dd8df26fb7efc25c6fed6cc7832bf65a42b933fd2d1276346695bd8451c9e5
-- Resource trace is retained N reference-work evidence, not new Q physical cost.
def fixedRoot : String := "fc4cf15ec370547b14fc67ae360269cea71cbc10d773536d1a77891acbe3bf7e"
def expectedTrace : List Phase17Resource.Kind := [.vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .candidate, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .candidate, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .candidate, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .candidate, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .candidate, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .candidate, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .candidate, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .candidate, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .candidate, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector]
def selectedTrace : List Phase17Resource.Kind := [.vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .candidate, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .candidate, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .candidate, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .candidate, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .candidate, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .candidate, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .candidate, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .candidate, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .candidate, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector]
def selectedPolicy : Phase17Resource.Policy := { limits := fun i => ([32, 328, 1312, 1312] : List Nat).getD i.val 0, costLimit := 9920 }

def selectedConfiguration : Configuration :=
  { root := fixedRoot
    catalog := Phase17TaskMeaning.catalog
    taskName := fun n => Phase17TaskMeaning.taskIds.getD n ""
    contract := Phase17Protected.boundContract
    context := Phase17Provenance.selectedContext
    policy := selectedPolicy
    expectedCharges := expectedTrace }

def selectedBefore : State := ofObservations fixedRoot
  Phase17LearnedBinding.observedBefore Phase17TaskMeaning.before
  Phase17TaskMeaning.beforeDeclared Phase17Protected.observedBefore
def selectedAfter : State := ofObservations fixedRoot
  Phase17LearnedBinding.observedAfter Phase17TaskMeaning.after
  Phase17TaskMeaning.afterDeclared Phase17Protected.observedAfter
def selectedUpdate : Update :=
  { key := Phase17LearnedBinding.addedKey
    program := { family := 6, variant := 1, a := (-4), b := 16 }
    task := 21
    taskName := Phase17LearnedBinding.addedTask
    parentPackage := "6759cc828b5b8cb4af041e32dcba7b136849591e793802ab7f1f1cc2f2bcd535"
    candidatePackage := "b4036b3e31a6608e30b421c08906b1e58c3e7d61fef6eb6730881c597656434e"
    contextHash := Phase17Provenance.selectedContext.contextHash
    charges := selectedTrace }
def selectedCandidate : RCP.Candidate State Update := ⟨selectedUpdate, selectedAfter⟩
def selectedProposal : Phase17Provenance.Proposal := Phase17Provenance.selectedProposal
def selectedEvidence : Evidence :=
  { root := "fc4cf15ec370547b14fc67ae360269cea71cbc10d773536d1a77891acbe3bf7e"
    parentPackage := "6759cc828b5b8cb4af041e32dcba7b136849591e793802ab7f1f1cc2f2bcd535"
    candidatePackage := "0000000000000000000000000000000000000000000000000000000000000000"
    contextHash := Phase17Provenance.selectedContext.contextHash
    transcriptHash := "16aee43b8b4f211f15917980d0d573e90a0d642427724271dd32e61ddeae1c0f"
    proposal := selectedProposal
    charges := selectedTrace }

theorem selected_facts :
    Facts selectedConfiguration selectedBefore selectedCandidate selectedEvidence := by
  constructor
  · unfold admissible Phase17Protected.WellFormed
    decide
  · unfold admissible Phase17Protected.WellFormed
    decide
  · apply state_ext <;> decide
  · unfold UpdateValid
    decide
  · unfold trustValid Phase17Provenance.ContextValid
    decide
  · unfold resourceValid Phase17Resource.Fits
    decide
  · unfold Phase17Provenance.CandidateMatches Phase17Provenance.Produced
      Phase17Provenance.ContextValid
    decide
  · decide

theorem selected_base_step :
    RCP.StepObligations (base selectedConfiguration)
      selectedBefore selectedCandidate selectedEvidence :=
  base_step selectedConfiguration selectedBefore selectedCandidate selectedEvidence selected_facts

theorem selected_learned_accepted :
    Learned.LearnedAcceptedStep (learned selectedConfiguration)
      selectedBefore selectedCandidate (packet selectedConfiguration selectedBefore selectedEvidence) :=
  accepted selectedConfiguration selectedBefore selectedCandidate selectedEvidence selected_facts

theorem selected_exact_recovery : recover selectedUpdate selectedAfter = selectedBefore := by
  have typed := selected_facts.typed
  change selectedAfter = apply selectedBefore selectedUpdate at typed
  rw [typed]
  apply exact_recovery
  · decide
  · decide
  · decide

theorem selected_resource_totals :
    selectedTrace.length = 153 ∧ Phase17Resource.counter selectedTrace 0 = 9 ∧
    Phase17Resource.counter selectedTrace 1 = 144 ∧
    Phase17Resource.counter selectedTrace 2 = 576 ∧
    Phase17Resource.counter selectedTrace 3 = 576 ∧
    Phase17Resource.totalCost selectedTrace = 4032 := by decide

end Phase17Finite
#print axioms Phase17Finite.base
#print axioms Phase17Finite.learned
#print axioms Phase17Finite.protected_view_preserved
#print axioms Phase17Finite.exact_recovery
#print axioms Phase17Finite.residuals_nonpositive
#print axioms Phase17Finite.base_step
#print axioms Phase17Finite.accepted
#print axioms Phase17Finite.accepted_protected_frontier
#print axioms Phase17Finite.accepted_all_resource_dimensions
#print axioms Phase17Finite.selected_facts
#print axioms Phase17Finite.selected_base_step
#print axioms Phase17Finite.selected_learned_accepted
#print axioms Phase17Finite.selected_exact_recovery
#print axioms Phase17Finite.selected_resource_totals
