# Phase 10A substrate validation

## Validation state

The canonical compact-transformer substrate and zero-output LoRA extension are
implementation-complete locally and are entering exact-head CI validation. This record
must not be read as full Phase 10 completion.

The local deterministic reference currently reports:

```text
architecture hash:
6b00c2df239868a4e7359cd2ee9e0292a9c877d06e893248bb36521450e32a0a

predecessor package hash:
1bcea7aff72d5c3f6027631d419ca730c980b3b1e2b72c60fd3b40750db69df5

zero-LoRA package hash:
7325101f8dc927d6f9047a530ea4682d20979f90c0e261cafd053a8a29f405ca

predecessor model identity:
e360f49bc573d814bf8f13ac91a9888ceae21e3a2a4dd5a59cf8b13be31223bb

zero-LoRA model identity:
dc72411ccdfa7b1c060fba790999d62356a308d1cc5a9b089bdaef57000274fb

conservative-extension report:
6372cbbe7e0b2a01896cb22edbb4226a88b490273f6c451c9bc2f4db94d0bc2a

complete reference hash:
e9368750ffd4d729ec7e39c7b323c0b5d375ec9f150dd47bd0beb0df1658d8d9
```

Local checks completed:

```text
Python compilation:                  success
focused Phase 10 tests:             10 passed
source-quality findings:            0
Draft 2020-12 schema validation:    success
manifest/hash recomputation:        success
predecessor package validation:     accept
zero-LoRA package validation:       accept
conservative-extension validation: accept
```

## CI closure required

The branch workflow must still establish at one exact head:

```text
Ubuntu deterministic reference and tests
Windows deterministic reference and tests
macOS deterministic reference and tests
identical cross-platform hashes
pinned Lean build
forbidden-token and local-axiom scans
Phase 10 transformer-extension axiom audit
Phase 9 regression tests
workflow closure artifact
```

After that run succeeds, this record should be amended with the exact branch head,
merge-test commit, run identifier, and artifact digests.

## Claim boundary

This validation covers a real compact-transformer **package graph** and conservative
adapter extension. The reference weights are structural zeros. It does not establish a
trained language model, task-frontier expansion, KL/QRE evidence, promotion, replay, or
full Phase 10 closure.
