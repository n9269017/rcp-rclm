# Formal Core v2 — proof-admission and axiom audit

This audit distinguishes:

1. whether project source contains admitted proofs;
2. whether the project declares new axioms; and
3. which foundational axioms the compiled public theorems use.

A successful build alone answers none of these questions. The workflow performs
and preserves separate source scans and `#print axioms` reports.

## Audited source scope

```text
lean/rcp_rclm_formal_core_v2/RcpRclmFormalCoreV2.lean
lean/rcp_rclm_formal_core_v2/RcpRclmFormalCoreV2/**/*.lean
```

Generated dependencies under `.lake/` are excluded. The source scan fails on
`sorry`, `sorryAx`, `admit`, or a project-local declaration beginning with
`axiom`.

## Gate A public theorem audit

The Gate A audit covers 22 public declarations, including checker soundness,
finite composition, endpoint recovery, monitor composition, conditional infinite
trajectories, summability, and the paper-facing abstract wrappers.

```text
Audit source:
  docs/formal_core_v2/audit/GateAAxiomAudit.lean

Authoritative Gate A workflow:
  run 29187317488
  build 1941 jobs, success
  no admitted proof token
  no project-local axioms
  no sorryAx
```

The Gate A theorem surface reports the standard Lean/mathlib foundational union:

```lean
[propext, Classical.choice, Quot.sound]
```

Classical choice remains visible because the conditional infinite theorem selects
successors from an explicit `Nonempty` availability premise.

## Gate B public theorem audit

The Gate B audit covers 22 finite classical declarations, including finite KL,
conservative extension, exact recovery, Boolean checker refinement, recovery
laws, monitors, and the worked trajectory.

```text
Audit source:
  docs/formal_core_v2/audit/GateBAxiomAudit.lean

Authoritative Gate B workflow:
  run 29208133524
  build 1942 jobs, success
  no admitted proof token
  no project-local axioms
  no sorryAx
```

Most Gate B declarations report:

```lean
[propext, Classical.choice, Quot.sound]
```

The invalid-candidate rejection theorem is axiom-free. Gate B introduces no local
axiom and contains no admitted proof.

## RCLM, architecture-engine, Paper II, and bounded-seed audit

The expanded RCLM audit is fixed in:

```text
docs/formal_core_v2/audit/RCLMRefinementAxiomAudit.lean
```

It covers 47 public declarations across:

```text
kernel, checker, monitor, and recovery refinement
conditional architecture successor theorem
conditional architecture infinite trajectory
direct-engine strict-successor alignment
successor-verification and robust-reflective alignment
concrete Gate B RCLM reference
bounded seed-library packet availability
bounded packet-builder soundness
bounded packet-to-architecture refinement
conditional infinite bounded seed-library trajectory
generic per-step bounded-seed architecture refinement
concrete binary grammar, packet, trajectory, and per-step architecture theorems
```

The authoritative bounded-seed validation record is:

```text
Branch source head:   a09c742ca2541ad3302a5c1041852974649e09c8
CI checkout commit:   02790b14d1fe9b16745ec8236bf91c9a0608e9b8
Workflow run:         29224543624
Build:                1953 jobs, success
No admitted token:    pass
Project-local axioms: none
No sorryAx:           pass
Audited declarations: 47
Artifact:             formal-core-v2-audit-29224543624-1
Artifact SHA-256:     e1f00cad76ac2799b8006e01cfdf6ba47f9348b4074d664bb4d1a2314716b6b2
```

The generic and most concrete RCLM theorems report only the standard union:

```lean
[propext, Classical.choice, Quot.sound]
```

Classical choice in bounded infinite recursion is explicit: a finite grammar must
be nonempty at every seed-domain state, and one certified word is selected from
that `Nonempty` witness. Grammar nonemptiness and successor seed-domain closure
are independent fields and are not inferred from checker soundness.

## Gate C selected quantum theorem audit

The selected Gate C audit is fixed in:

```text
docs/formal_core_v2/audit/GateCAxiomAudit.lean
```

It covers 32 public declarations across:

```text
diagonal density-matrix Hermitian, positive-semidefinite, and trace-one evidence
spectral quantum-relative-entropy nonnegativity and self-zero
positive source-to-target QRE witness
basis-swap involution
selected channel entropy and QRE preservation
selected exact recovery
quantum packet characterization and invalid-candidate rejection
complete quantum StepObligations
quantum checker refinement
quantum Lyapunov, collapse, and relevance monitors
finite quantum trajectory, strict first step, endpoint recovery, and monitor bounds
RCLM quantum checker, architecture evidence, and selected architecture successor
```

The first complete selected Gate C validation record is:

```text
Branch source head:   9250d1fa40179738ca161dbd9b1d9310f9c901ce
CI checkout commit:   de60b043147906a411a8b827ce41120a0e2f4e1c
Workflow run:         29246781311
Build:                2636 jobs, success
No admitted token:    pass
Project-local axioms: none
No sorryAx:           pass
Audited declarations: 32
Artifact:             formal-core-v2-audit-29246781311-1
Artifact SHA-256:     38d2776534e94a6ebb6281924e30133ff9c35d4edbbe34393b4f1d1c48c03072
```

The reported Gate C foundational union is:

```lean
[propext, Classical.choice, Quot.sound]
```

`quantumCheck_rejects_invalidCandidate` is axiom-free. No audited Gate C
declaration reports `sorryAx`, and the source introduces no project-local axiom.

This audit applies to the selected commuting/diagonal quantum reference. It does
not certify arbitrary noncommuting density matrices, arbitrary CPTP channels, a
general matrix-logarithm formulation, general quantum data processing, or Petz
recovery.

## Combined acceptance rule

The Formal Core audit passes only when:

```text
paper source blobs and mapped theorem surfaces match their pins
no project Lean source contains sorry, sorryAx, or admit
no project-local axiom declaration is present
all Gate A audit declarations elaborate
all Gate B audit declarations elaborate
all RCLM/refinement/engine/bounded-seed declarations elaborate
all selected Gate C audit declarations elaborate
no axiom report contains sorryAx
a clean pinned build succeeds
audit artifacts are uploaded even on failure
```

## Prohibited inferences

```text
clean build => exact Paper I or Paper II theorem equivalence
no project-local axioms => no standard Lean/mathlib foundational dependencies
checker soundness => successor availability
checker soundness => grammar nonemptiness
checker soundness => generator coverage
checker soundness => successor seed-domain persistence
finite grammar completeness => unbounded proof-search completeness
bounded seed-library closure => arbitrary learned-system entry
architecture availability => strict useful improvement at every step
concrete finite path => unbounded empirical RSI
selected diagonal QRE => arbitrary noncommuting matrix QRE
identity/swap preservation => general CPTP data processing
exact involutive recovery => Petz or approximate recovery
conditional architecture theorem => executable generator correctness
```

## Reproduction

After a successful build, run from `lean/rcp_rclm_formal_core_v2`:

```text
lake env lean ../../docs/formal_core_v2/audit/GateAAxiomAudit.lean
lake env lean ../../docs/formal_core_v2/audit/GateBAxiomAudit.lean
lake env lean ../../docs/formal_core_v2/audit/RCLMRefinementAxiomAudit.lean
lake env lean ../../docs/formal_core_v2/audit/GateCAxiomAudit.lean
```

The GitHub workflow additionally performs the source scans and uploads all
reports.
