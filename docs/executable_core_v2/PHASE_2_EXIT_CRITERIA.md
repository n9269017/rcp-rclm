# Phase 2 exit criteria

Phase 2 may be closed only when all of the following are true:

- [x] A strict immutable reference-packet schema exists.
- [x] The packet grammar is limited to the selected Gate B and Gate C references.
- [x] Python computes an independent deterministic acceptance interpretation.
- [x] Generated Lean source is deterministic and content-hashed.
- [x] The source guard runs before every compiler invocation.
- [x] `sorry`, `sorryAx`, `admit`, local `axiom`, and invalid UTF-8 are rejected.
- [x] The exact formal-source Git commit, Lean pin, and mathlib pin are checked before compilation.
- [x] Lean and Lake runtime identity evidence is recorded.
- [x] Raw compiler stdout, stderr, exit code, timeout state, and hashes are retained.
- [x] Exactly one canonical structured Lean verdict marker is required.
- [x] Gate B accept, stability, and mutation cases are covered.
- [x] Gate C accept, stability, and mutation cases are covered.
- [x] RCP and canonical RCLM checker results must agree for every case.
- [x] Accepted cases instantiate the existing complete RCP step-obligation theorem.
- [x] RCP and RCLM classical and quantum theorem surfaces are checked by generated source.
- [x] Unit tests cover parsing, generation, pin validation, pre-compilation rejection, and fail-closed mismatch behavior.
- [ ] The pinned Linux Lean conformance workflow passes at the synchronized branch head.
- [ ] Linux, Windows, and macOS Python bridge tests pass at the synchronized branch head.
- [ ] The final workflow artifact and digest are recorded.
- [ ] The Phase 2 manifest and validation record identify the final clean head.

The following remain outside Phase 2 and must remain false:

```text
production candidate acceptance
production checker soundness
untrusted generator correctness
successor selection and realization
promotion or rollback
independent replay
PyTorch proposal correctness
external benchmark evidence
arbitrary noncommuting quantum semantics
```
