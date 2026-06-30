# RCP/RCLM Canonical Finite Mechanization Project

This Lean 4 project mechanizes the narrow canonical finite reference core for the RCP/RCLM paper set.

Scope:
- RCP canonical core certificate.
- RCLM canonical refinement certificate.
- Finite proof-carrying checker/refinement theorems for the declared canonical reference class.

Non-scope:
- The full 200+ page RCP/RCLM theorem stack.
- Arbitrary trained-system entry.
- Full empirical validation.

## Build commands

From the project root:

```powershell
lake env lean .\RcpRclmMech\RCP.lean
lake build RcpRclmMech.RCP
lake env lean .\RcpRclmMech\RCLM.lean
lake build RcpRclmMech.RCLM
lake env lean .\RcpRclmMech.lean
lake build
```

`lake build` builds the root module `RcpRclmMech.lean`, which imports both proof modules. There is no executable target, so no Windows C linker is invoked.
