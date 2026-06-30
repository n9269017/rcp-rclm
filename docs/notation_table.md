# Notation table

| Symbol | Meaning | Paper / artifact role |
|---|---|---|
| `RCP` | Recursive Coherence Preservation | Architecture-general theorem framework |
| `RCLM` | Recursive Coherence Language Model | Architecture instantiation |
| `K_t^{SV-seedlib,N}` | finite successor-verification seed-library domain | theorem-entry domain |
| `K_t^{SV,N}` | finite successor-verification domain | certified trajectory domain |
| `SVPkg_t` | successor-verification packet | carries verifier, goal, uncertainty, trust, budget, persistence evidence |
| `SVBuilder_t` | packet builder | constructs SV packet in declared domains |
| `PCS_t` | proof-carrying successor packet | finite reference/checker object |
| `Check_RCP` | trusted checker | Lean/paper checker target |
| `BuildRefSV_{0:N}` | reference compiler/builder | constructs finite reference instance |
| `RefSV_{0:N}^{RCP}` | RCP finite reference instance | math-side reference object |
| `RefSV_{0:N}^{RCLM}` | RCLM finite reference instance | architecture-side reference object |
| `MechCert` | external mechanization certificate | Lean 4 certificate scope marker |
| `LECert` | learned-entry certificate | M3-Min learned-system entry boundary |
| `RealCont` | reality-containment / misspecification certificate | required for real-world reliability claims |
| `SVTract` | restricted tractability certificate | required for strong computational tractability claims |
