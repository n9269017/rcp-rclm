# RCP/RCLM Executable Core v2 Schemas

This directory contains the frozen canonical schemas used by the RCP/RCLM theorem-to-
runtime refinement layer. The schemas cover Executable Core v2 Phases 0–8 and the first
bounded PyTorch learned-successor pilot.

## Status

```text
Phase 0 contract: complete
Phase 1 runtime types and canonical encodings: complete
Phase 2 pinned Lean packet/verdict bridge: complete
Phase 3 checker request/report: complete
Phase 4 hardened integrity and adversarial results: complete
Phase 5A bounded generator protocol: complete
Phase 6 candidate package and rollback evidence: complete
Phase 7 promotion store, ledger, pointer, and controller reports: complete
Phase 8 replay bundle and report: complete
First PyTorch pilot records: complete at the tiny CPU-only scope
```

## Schema inventory

```text
contract/
  executable_core_v2_contract.schema.json
  phase_3_checker.schema.json
  phase_4_hardened_checker.schema.json
  phase_5a_reference_generator.schema.json
  phase_6_successor_package.schema.json
  phase_7_promotion_controller.schema.json
  phase_8_independent_replay.schema.json
  pytorch_pilot.schema.json
```

The schemas are strict: unknown fields are rejected, structural integers cannot be
booleans, hashes are lowercase SHA-256 strings, semantic paths are normalized, and
candidate self-certification fields are not accepted as mathematical evidence.

## Canonical authority

The schema layer is interpreted together with Runtime v2 canonical JSON and semantic-tree
hashing. PyTorch serialization, `torch.save`, pickle, native floating-point reductions,
and GPU kernels are not canonical authorities.

The PyTorch pilot schema binds:

```text
architecture manifest
tensor names, shapes, dtypes, byte order, sizes, and raw-byte hashes
canonical model hash
optimizer manifest
training-data and held-out-feature manifests
seed and RNG-state hashes
training command and resource record
before/after model hashes
exact evaluation result
Phase 6 selection and rollback binding
Phase 7 admission/promotion evidence
independent replay report
```

The training worker may propose these artifacts, but the host reconstructs selection,
filesystem realization, exact evaluation, certificate evidence, Lean/checker requests,
promotion transactions, and replay.

## Validation

Schema meta-validation and record round trips are exercised by the phase-specific test
suites under `python/rcp_rclm_runtime_v2/`. The authoritative workflow index is
`docs/executable_core_v2/README.md`.

## Claim boundary

These schemas define the declared finite reference and tiny learned-pilot contracts. They
do not encode a general proof of arbitrary learned-system refinement, unbounded successor
availability, general noncommuting quantum channels, or autonomous RSI.
