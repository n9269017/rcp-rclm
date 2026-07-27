# Gate E object map

## Layer correspondence

| Concept | Lean Formal Core v4 | Executable Core v4 contract | Runtime v4 responsibility |
|---|---|---|---|
| Immutable search history | `SearchHistory` | `search_history` | canonical hash-chain projection |
| Active search state | `SearchState` | `active_state` | bind active package and history |
| Hidden challenge source | `FreshChallengeSource` | `fresh_challenge_binding` | external post-freeze challenge service |
| Endogenous objective | `EndogenousObjective` | `objective` | active package output |
| Endogenous mutation program | `EndogenousMutationProgram` | `mutation_program` | active package output and strict parser |
| Recursive-productivity task | `RecursiveProductivityTask` | `recursive_productivity_task` | independent verifier-backed record |
| Gate E packet | `Autonomous.CertificatePacket` | `gate_e_certificate` | bind Gate D packet plus search evidence |
| Candidate attempt | `SearchAttempt` | `attempt_record` | candidate, certificate, verdict, reasons |
| Deterministic enumerator | `CandidateEnumerator` | `enumeration_record` | canonical attempt order |
| Fair search policy | `FairSearchPolicy` | `fair_search_policy` | coverage and ranking policy |
| Gate E kernel | `Autonomous.Kernel` | `gate_e_kernel_binding` | immutable policy-hash correspondence |
| Gate E checker | `TrustedAutonomousChecker` | `gate_e_checker_report` | external Boolean acceptance authority |
| Accepted autonomous step | `AutonomousAcceptedStep` | `accepted_autonomous_step` | Gate D plus Gate E obligations |
| First accepted search | `firstAccepted` | `selected_attempt_index` | deterministic first-accept selection |
| Search exhaustion | `SearchExhaustionCertificate` | `search_exhaustion_certificate` | bind every enumerated rejection |
| Package autonomous improver | `AutonomousImprover` | `autonomous_improver_binding` | active history plus finite enumeration |
| Constructive availability | `ConstructiveSuccessorAvailability` | `constructive_availability_report` | accepted output at declared states |
| Finite trajectory | `FiniteAutonomousTrajectory` | `phase14_trajectory` | promotion and rejection ledger |
| Infinite conditional trajectory | `InfiniteAutonomousTrajectory` | theorem-only boundary | not an empirical runtime artifact |

## Gate D refinement

Every executable Gate E acceptance must retain an exact embedded Gate D packet and report.
The correspondence is:

```text
Gate E accepted
    -> Gate D learned checker accepted
    -> inherited RCP checker accepted
    -> complete base and learned obligations
```

No Gate E field may replace a Gate D field.

## Recursive-productivity frontier

The executable frontier record must bind:

```text
predecessor recursive frontier
successor recursive frontier
independent certification for every successor member
complete predecessor inclusion
optional strict witness
witness absence from predecessor
witness presence in successor
```

## Exhaustion correspondence

The runtime exhaustion record must contain enough immutable data to reconstruct the exact
finite list supplied to `firstAccepted`:

```text
enumerator policy hash
active package hash
history hash
challenge commitment
ordered attempt hashes
per-attempt checker verdict
per-attempt reason codes
complete-coverage declaration for the bounded grammar
```

The Lean theorem proves rejection of every enumerated attempt. Executable validation must
separately establish that the enumeration covers the declared bounded grammar.

## Forbidden host-route correspondence

The executable contract must carry explicit false-valued fields for:

```text
next_successful_transition_index_present
required_successful_component_set_present
accepted_program_bytes_present
expected_candidate_hash_present
expected_new_capability_present
expected_final_model_identity_present
host_selected_objective_present
```

Absence is checked from canonical input records rather than asserted only in prose.
