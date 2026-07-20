# Phase 10 validation

## Phase 10A exact-head closure

The canonical compact-transformer package and zero-output LoRA extension closed at
validated branch head:

```text
95a4679291b25da5093d757cc6e7baf5461a8a6a
```

with PR merge-test commit:

```text
482f065308cf4735d36959bf06fbe12f1e27ea3e
```

and successful workflow:

```text
29710470650
```

That exact head passed Ubuntu, Windows, macOS, pinned Lean, proof-hygiene, schema,
manifest, deterministic reference, and closure jobs.  The Phase 10A closure explicitly
records `phase10_exit_closed=false`.

The retained Phase 10A model identities are:

```text
predecessor:
e360f49bc573d814bf8f13ac91a9888ceae21e3a2a4dd5a59cf8b13be31223bb

zero-LoRA extension:
dc72411ccdfa7b1c060fba790999d62356a308d1cc5a9b089bdaef57000274fb
```

## Phase 10B implementation validation

Phase 10B adds the selected learned execution and certified-language slice.  The source
must close at one exact head with:

```text
Ubuntu learned-reference and Phase 9 regression validation
Windows learned-reference and Phase 9 regression validation
macOS learned-reference and Phase 9 regression validation
two fresh bootstrap PyTorch worker invocations
two fresh successor PyTorch worker invocations
host-exact tensor-byte recomputation
pinned Lean compilation of the protected completion
pinned Lean compilation of the new held-out completion
rejection of the predecessor on the held-out task
selected information theorem axiom audit
exact Phase 9 learned-transition acceptance
workflow closure artifact
```

The Phase 10B machine-readable manifest remains in
`implementation_started_pending_authoritative_ci` status until that exact-head run
succeeds and its reference and artifact hashes are committed.

## Full Phase 10 boundary

Even after Phase 10B closure, full Phase 10 remains open until the learned candidate is
realized through Phase 6, rollback is byte-exact, the inherited pinned-Lean and hardened
checker gates accept, Phase 7 atomically promotes the package, and independent replay
succeeds with the training worker absent and zero training invocations.
