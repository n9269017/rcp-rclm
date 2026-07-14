# Phase 3 exit criteria

Phase 3 implementation is complete when all of the following pass at one exact
Git head:

- [ ] The checker request parser rejects unknown and duplicate fields.
- [ ] Candidate success assertions are absent from the semantic input schema.
- [ ] Inputs are immutable and unchanged by repeated checks.
- [ ] Repeated checks produce byte-identical canonical reports.
- [ ] Gate B improvement and stability references are accepted.
- [ ] Gate C diagonal improvement and stability references are accepted.
- [ ] Typed successor and packet residuals are recomputed.
- [ ] Shannon/von Neumann entropy and KL/QRE intervals are recorded.
- [ ] Protected non-loss uses zero selected-reference budgets.
- [ ] Recovery is recomputed from the actual successor and update.
- [ ] Progress nondecrease is interval certified.
- [ ] Strict progress is required only for the derived improvement witness.
- [ ] Frozen trust roots and checker policy hashes are checked.
- [ ] Model, network, mutation, manual-repair, and hidden-oracle counts must be zero.
- [ ] Successor domain, containment, and protected invariants are recomputed.
- [ ] RCLM state, update, successor, and certificate are exact canonical lifts.
- [ ] Preservation monitor obligations are recomputed.
- [ ] The Lean bridge report is bound to the exact recomputed packet.
- [ ] An indeterminate or rejected Lean result is nonaccepting.
- [ ] Every authoritative input and derived binding has a computed hash.
- [ ] Phase 1 and Phase 2 regression suites remain green.
- [ ] Linux, Windows, and macOS Phase 3 checker jobs pass.
- [ ] Source quality contains no placeholders or forbidden runtime dependencies.

After these criteria pass, Phase 4 adversarial checker testing may begin.

The following remain false after Phase 3:

```text
candidate promotion licensed
generator trusted
package realization complete
rollback complete
independent replay complete
PyTorch backend trusted
general noncommuting quantum scope implemented
autonomous or unbounded RSI established
```
