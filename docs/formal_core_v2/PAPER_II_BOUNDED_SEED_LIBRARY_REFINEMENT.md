# Paper II bounded seed-library and packet-builder refinement

## Phase boundary

This phase identifies Paper II's declared bounded seed-library and
successor-verification packet-construction layer with the compiled Formal Core v2
architecture interfaces. It is Lean-only. It neither introduces an executable
runtime nor begins Gate C.

The phase refines the following chain:

```text
bounded seed-domain predecessor
  -> finite witness library
  -> finite certificate-word grammar
  -> generated proposal
  -> constructed certificate packet
  -> selected typed candidate
  -> realized successor
  -> trusted checker acceptance
  -> successor-verification obligations
  -> successor seed-domain persistence
```

The generator, certificate builder, selector, realizer, checker, and persistence
relations remain distinct. Checker soundness is not used to infer grammar
nonemptiness, generator coverage, packet construction, or successor availability.

## Generic bounded seed-library interface

`RCLM.PaperIIBoundedSeedLibrary` supplies the explicit data and laws required by
this phase:

```text
seedDomain
witnesses : State -> Finset Witness
grammar : State -> Finset Word
wordDepth and proofLength
maxWordDepth and maxProofLength
witness/proposal/certificate/candidate/resource decoders
seed-domain to architecture-domain refinement
grammar nonemptiness on the seed domain
word-to-witness membership
witness-library coverage
generator proposal relation
certificate-construction relation
candidate-selection relation
successor-realization relation
resource authorization
checker acceptance
successor seed-domain closure
```

The finite grammar is a declared bounded coverage class. It is not an assertion
that arbitrary proof search, arbitrary learned proposals, or unbounded candidate
spaces are complete.

`RCLM.PaperIIBoundedSeedPacket` records a concrete grammar word together with
seed-domain and grammar-membership evidence. Its map

```lean
RCLM.PaperIIBoundedSeedPacket.toEngineStep
```

constructs the already compiled `ArchitectureEngineStep` from that evidence. The
map therefore preserves the separation between untrusted construction relations
and trusted checker acceptance.

## Packet-builder soundness

The generic theorem

```lean
RCLM.paper_ii_bounded_seed_packet_builder_sound
```

proves that a bounded seed packet supplies:

```text
complete RCLM StepObligations
complete successor-verification obligations
successor seed-domain membership
declared verifier-schema persistence
declared uncertainty-envelope persistence
declared goal-identity drift bound
```

The theorem obtains formal obligations from actual checker acceptance and obtains
seed-domain closure from the independent library persistence field.

The stronger bridge

```lean
RCLM.paper_ii_bounded_seed_packet_refines_architecture
```

combines packet-builder soundness with the substantive RCLM-to-RCP architecture
refinement. Its result contains both:

```text
ArchitectureSuccessorResult
PaperIIBoundedSeedSuccessorResult
```

Accordingly, one checked bounded-library step carries the complete typed RCLM
successor obligations, complete forgotten RCP obligations, recovery and monitor
refinement evidence, and Paper II successor-verification packet obligations.

## Semantic identification boundary

`RCLM.PaperIISeedSemanticIdentification` explicitly identifies the paper-declared
objects with the compiled interfaces:

```text
declared verifier schema
verifier-schema transport
verifier-schema refinement relation
declared uncertainty envelope
uncertainty-envelope transport
uncertainty-envelope refinement relation
declared goal
goal transport
goal distance
goal-drift budget
```

These identifications are equality proofs supplied by an instantiation. Field
names alone do not establish semantic identity.

## Conditional infinite closure

`RCLM.PaperIIBoundedSeedPredecessor` pairs an architecture predecessor with
seed-domain membership. The recursive definitions in
`RCLM.PaperIIBoundedSeedTrajectory` select a grammar-certified packet, construct
the next architecture predecessor, and preserve the seed-domain proof.

The theorem

```lean
RCLM.conditional_infinite_paper_ii_bounded_seed_trajectory_exists
```

constructs an infinite architecture trajectory only from a library whose grammar
is nonempty at every seed-domain state and whose accepted packet explicitly
returns to the successor seed domain. The theorem does not derive these facts
from checker soundness.

Each selected step satisfies

```lean
RCLM.infinite_paper_ii_bounded_seed_step_result
```

which replays the bounded packet-builder soundness theorem at that time index.

## Concrete Gate B classical/binary instance

`RCLM.ClassicalBinary.boundedSeedLibrary` instantiates the generic interface with:

```text
states: initial and target
witnesses: strictImprovement and stableContinuation
words: improve, stabilize, rejected
active grammar at initial: {improve}
active grammar at target: {stabilize}
maximum update-word depth: 1
maximum proof-word length: 1
```

The rejected word is not in an active grammar. Exhaustive case analysis proves
that every active grammar word is exactly the improvement word at `initial` or
the stability word at `target`.

The concrete semantic identification uses named declared objects:

```text
verifier schema: trustedBinaryChecker
verifier transport: identity
uncertainty envelope: contained
uncertainty transport: identity
goal: biasedTarget
goal transport: identity
goal distance: the declared finite discrete distance
goal-drift budget: zero
```

The following concrete theorems are supplied:

```lean
RCLM.ClassicalBinary.initial_bounded_seed_packet_builder_refinement
RCLM.ClassicalBinary.initial_bounded_seed_direct_engine_refinement
RCLM.ClassicalBinary.classical_bounded_seed_packet_builder_refinement
RCLM.ClassicalBinary.classical_infinite_bounded_seed_trajectory_exists
RCLM.ClassicalBinary.classical_infinite_bounded_seed_step_result
```

The first selected step is the already proved strict KL-derived improvement. The
persisting path then uses the accepted stability packet at the target state. This
is bounded seed-library and packet-construction closure, not indefinitely strict
capability growth.

## Paper II alignment result

| Paper II object | Formal Core v2 object | Resolution |
|---|---|---|
| certified finite witness library | `PaperIIBoundedSeedLibrary.witnesses` | concrete finite refinement |
| bounded update/certificate grammar | `PaperIIBoundedSeedLibrary.grammar`, depth bounds | concrete finite refinement |
| generator coverage | `proposalGenerated` plus grammar membership | explicit theorem field |
| packet construction | `certificateConstructed`, `PaperIIBoundedSeedPacket` | explicit theorem field and packet object |
| candidate selection | `candidateSelected` | explicit theorem field |
| successor realization | `successorRealized` | explicit theorem field |
| checker acceptance | `checkerAccepted` | explicit evidence, not inferred |
| verifier schema and transport | `PaperIISeedSemanticIdentification` | explicit equality refinement |
| uncertainty envelope and transport | `PaperIISeedSemanticIdentification` | explicit equality refinement |
| goal identity and drift | `PaperIISeedSemanticIdentification` and packet result | explicit equality refinement and bound |
| successor seed-domain persistence | `successorSeedDomain` | explicit completeness premise |
| infinite seed-library path | bounded seed trajectory theorem | conditional construction from explicit closure |

## Claim boundary

This phase establishes a generic bounded seed-library refinement and a complete
finite classical/binary reference instantiation. It does not establish:

```text
unbounded grammar completeness
arbitrary proof-search completeness
arbitrary learned-system seed-domain entry
arbitrary learned generator coverage
strict useful improvement at every recursive step
exact identity with every semantic object in the full Paper II manuscript
Gate C finite-dimensional quantum closure
Python checker or generator correctness
an executable promotion loop
empirical recursive self-improvement
external benchmark performance
```

The executable phase remains unlicensed. Gate C also remains unstarted.
