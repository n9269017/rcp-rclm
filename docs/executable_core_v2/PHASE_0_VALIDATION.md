# Phase 0 validation record

## First clean contract validation

The frozen Phase 0 contract passed the dedicated clean GitHub Actions workflow at:

```text
validated branch head:
23632bae9601ecfdd0f4eb12f892620dfebe3131

pull-request merge checkout:
144da32553b64c9020086fdf7483d75f84ee104f

workflow run:
29258694605

result:
success

artifact:
executable-core-v2-contract-29258694605-1

artifact SHA-256:
80cf894621062cfe16584bb28aea09651f9bd36f6d8b13d3233267b80a489878
```

The workflow passed:

```text
Python 3.11 compilation
syntax-aware rejection of pass statements, ellipsis expressions, and TODO markers
contract-validator unit tests
strict JSON parsing
formal source and manifest pins
mapped Lean source blob pins
mapped Lean declaration surfaces
trust-boundary invariants
numerical decision invariants
fail-closed acceptance invariants
Phase 0 license boundary
artifact upload
```

The validation report contained:

```json
{
  "mapped_object_count": 27,
  "scanned_lean_file_count": 0,
  "issues": [],
  "ok": true
}
```

`scanned_lean_file_count` is zero because this validation did not compile a generated
certificate packet. The anti-placeholder scanner itself was exercised by unit tests
against clean source, forbidden proof tokens, and a project-local axiom declaration.

## Contract file hashes

```text
runtime_contract_manifest.json
cf8e3d6106c449d2c7dbe9e8fa36d1cd0d9dc65a0721e1c8fd38321aae88f125

runtime_records.schema.json
aff49b9dcc0c5e33f37170896d5380dfdbc957e13549dbdffd300f1c6c33cdd2

validate_runtime_contract.py
893093c2c1e6f8d289f6c677f07985772836119c5c93e664102528967e4e4e9a

test_validate_runtime_contract.py
554ca14d259cc99923466293d5c60df95e3100ba0a180875903ff3e06b586e5d
```

The machine-readable copy is:

```text
python/rcp_rclm_executable_core_v2/contract/phase_0_validation.json
```

## Evidence interpretation

This validation closes the contract-freeze phase and licenses work on the Phase 1
runtime bedrock. It does not validate a production mathematical engine, Lean
verifier bridge, successor checker, generator, promotion controller, PyTorch
backend, or benchmark adapter.

The final synchronized PR head is validated again after this evidence record is
added. That final workflow is recorded on PR #14 to avoid making a source file
self-reference its own as-yet-unassigned workflow identifier.
