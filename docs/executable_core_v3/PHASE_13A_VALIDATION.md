# Phase 13A validation boundary

Phase 13A freezes the worker-free independent-replay boundary before the concrete multi-generation trajectory is replayed.

The selected slice requires:

- canonical retained-evidence packaging;
- training, generator, and planner invocation counts equal to zero;
- no forbidden learned or training modules loaded;
- no forbidden worker or training paths inside the replay bundle;
- deterministic replay-source guard acceptance;
- deterministic rejection of all twenty-one Phase 13 adversarial cases;
- byte-identical repository and package entry points on Linux, Windows, and macOS.

The Phase 13A report deliberately records `phase13_exit_closed=false`. Full Phase 13 additionally requires restoration and replay of every accepted transition and captured rejection, pinned-Lean recertification, complete parent-chain and rollback verification, and exact-head artifact binding.

The dependency audit is fail-visible: if the merged Phase 12 source lacks any required final-trajectory implementation surface, the report lists the missing paths rather than treating prior prose or candidate self-report as authoritative evidence.
