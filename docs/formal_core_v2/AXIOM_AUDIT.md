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
`sorry`, `admit`, or a project-local declaration beginning with `axiom`.

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
  no sorry/admit
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
  no sorry/admit
  no project-local axioms
  no sorryAx
```

Most Gate B declarations report:

```lean
[propext, Classical.choice, Quot.sound]
```

The invalid-candidate rejection theorem is axiom-free, and the exact Boolean
checker characterization has a narrower report. Gate B introduces no local
axiom and contains no admitted proof.

## RCLM, architecture-engine, Paper II, and bounded-seed audit

The expanded RCLM audit is fixed in:

```text
docs/formal_core_v2/audit/RCLMRefinementAxiomAudit.lean
```

It covers 45 public declarations across:

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
concrete binary grammar, packet, and trajectory theorems
```

The authoritative bounded-seed validation record is:

```text
Branch head:          78e9db0b0f2336d50ad4ec00d11bbc4415efc1a4
CI checkout commit:   f43f08c4693aec79fe01a2af3e71dbe73279714e
Workflow run:         29222655146
Build:                1953 jobs, success
No sorry/admit:       pass
Project-local axioms: none
No sorryAx:           pass
Audited declarations: 45
Artifact:             formal-core-v2-audit-29222655146-1
Artifact SHA-256:     c1a59e1b365e2dedd8515fd4952584057edaef0d2043206dde680c28628149af
```

The generic and most concrete RCLM theorems report only the standard union:

```lean
[propext, Classical.choice, Quot.sound]
```

The concrete grammar-case theorem reports `[propext, Quot.sound]`, and the
concrete theorem converting architecture-domain membership to the bounded seed
domain is axiom-free. No audited declaration reports `sorryAx`.

The use of classical choice in bounded infinite recursion is explicit: a finite
grammar is required to be nonempty at every seed-domain state, and one certified
word is selected from that `Nonempty` witness. Grammar nonemptiness and successor
seed-domain closure are independent structure fields and are not inferred from
checker soundness.

## Combined acceptance rule

The Formal Core audit passes only when:

```text
paper source blobs and mapped theorem surfaces match their pins
no project source contains sorry or admit
no project-local axiom declaration is present
all Gate A audit declarations elaborate
all Gate B audit declarations elaborate
all RCLM/refinement/engine/bounded-seed declarations elaborate
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
concrete binary infinite path => unbounded empirical RSI
Gate B finite KL => quantum relative entropy
conditional architecture theorem => executable generator correctness
```

## Reproduction

After a successful build, run from `lean/rcp_rclm_formal_core_v2`:

```text
lake env lean ../../docs/formal_core_v2/audit/GateAAxiomAudit.lean
lake env lean ../../docs/formal_core_v2/audit/GateBAxiomAudit.lean
lake env lean ../../docs/formal_core_v2/audit/RCLMRefinementAxiomAudit.lean
```

The GitHub workflow additionally performs the source scans and uploads all
reports.
