# Phase 17AN — protected broker and actual worker boundary

## Baseline and scope

This additive increment starts at completed AM Windows evidence
`7a3bc388309e9184012a1f772ea19727882abd07`, source
`028a865724dcbf4e1dde8e39b06d84fa72f52d33`, tree
`3c41983b2306d115a00ff74572d1d92a859fb0cd`. The retained AM execution is
`artifacts/development/phase17am/op-028a865724dc/gate/execution.json`, SHA-256
`f558faeb7bf88e7ad3ae415578ba812df76f2b53fdb2a2109bd0f4d4ae582cc2`.
The controller branch and draft, unmerged PR #68 remain the publication boundary.

AM authenticated its client and authority, but its client retained the credential
and writable currentness anchor inside its own view. Its evaluator workers did
not use the frontend namespace profile. AN moves credential-bearing dispatch and
retained state into a trusted broker outside the request frontend, and applies a
new role-specific Linux profile to the actual fixed evaluator worker launch.
The inherited present-prefix controller still runs inside the trusted authority;
the external frontend is a bounded run-request frontend, not a new learned or
fully autonomous controller.

The implementation remains a locally commissioned reference. It does not create
an independently administered host or OS service account. It does not turn a
namespace observation into physical attestation, globally exclusive authority,
anti-rollback hardware, complete resource accounting, or promotion permission.

## Commissioning and protected broker ownership

The administrator constructs and retains a public commission outside frontend
dispatch. The broker requires its separately supplied digest at startup. It binds
the AM commission and root provision, exact server/client certificate pins, actual
implementation closure, controller source, fixed objective/evaluator/worker
protocols, launch profiles, accounting contract, and finite credit/intent limits.
A frontend's commission field is only an echo compared with that supplied pin.

The trusted capture parent owns the AM TLS client, private client credential,
AM currentness anchor, and separately provisioned broker state. Each frontend
has only inherited input/output pipes and a bounded public intent. Its interface
permits `read`, `run`, and `reconcile`; only `run` carries positive bounded credits.
No intent supplies a key, anchor path, endpoint, source root, interpreter,
evaluator, grant, completion, export, reopening operation, or shutdown request.
The actual AL authority continues to own reservations, fixed evaluation, and
durable completion. A new AN authority adapter changes the native worker launcher
without altering inherited AL/AM source or replacing their transition rules.

Before a run reaches AM, the broker durably consumes the frontend nonce and
retains its exact pending intent and current cursor. AM then retains its exact
wire request before sending. A missing reply leaves ambiguity in both records.
Another mutation is refused. Reconciliation reads authenticated history and does
not launch a worker. If AM completed immediately before broker settlement was
interrupted, the retained broker intent can be reconciled from AM's protected
history. Missing completion is never synthesized, refunded, or retried.

The broker's files and AM's anchor are distinct write-ahead records, not one
claimed cross-file atomic transaction. Their conservative recovery rules retain
uncertainty across the intervening crash boundaries. Locks and filesystem sync
remain OS/storage premises, and protection against an administrator jointly
rolling back all trusted state remains open.

## Actual Linux launch boundary

Both request frontends and actual evaluator workers use an exact source-bound
launcher profile. An outer `unshare` creates a private user/network namespace;
`bubblewrap` then uses that already-private network namespace while constructing
private mount, PID, IPC, UTS and user views. This avoids configuring loopback
through a route-netlink operation unavailable in the selected execution host.
The target's observed network namespace must differ from the original host's.

The profile clears the environment, drops capabilities, disables further user
namespace creation, sets no-new-privileges, mounts runtime and source read-only,
and supplies only a private writable scratch directory and standard pipes.
Authority roots, credential bundles, retained broker/AM state, and trusted native
evidence directories are absent from the mounted view. A source-bound wrapper
records the actual namespace/capability/descriptor state and designated denial
probes before executing the fixed target. The trusted parent retains that frame
outside the sandbox. Launcher and target process identities are kept distinct;
the original target is joined by its observed process start identity and
namespace identities, not by relabeling the supervisor PID.

The source-bound profile and observed checks depend on the trusted launcher,
kernel, Python runtime, namespace tools and host filesystem. They are not a
proof against all kernel exploits or a complete CPU/memory/process/energy budget.
No cgroup, complete host resource containment, independent host principal, or
remote attestation is claimed. Failure to construct the Linux profile stops the
run; there is no unconfined Linux fallback.

Windows exercises the broker protocol and actual fixed workers as an explicitly
unconfined reference. The interface does not transmit credentials, but this does
not establish that an arbitrary same-principal Windows process cannot access
host files. Windows receives zero Linux namespace observations and no Linux
confinement credit. A production Windows service-principal/DACL deployment is a
separate administrator transaction, not an action performed by this installer.

## Accounting and admission

AN fixes fourteen ordered accounting categories: reference evaluation,
controller/planning, admission/reservation, authentication/PKI, transport/protocol,
hashing/source binding, journal/persistence, process startup/IPC,
evidence/reconstruction, formal checking/tests, host CPU/GPU/memory,
storage/network/energy, deployment/provisioning, and historical/broader campaign.
This is an explicit declared coverage inventory, not a proof that the taxonomy
measures every physical cost. Unknown amounts and bounds are `null`; incomplete
grand totals remain `null`, with known subtotals separately labeled.

The selected reference allowance is bound to the actual AL root policy. AL's
nonrefundable whole-envelope reservation remains the actual worker-budget owner.
After the selected campaign, a derived closeout binds the known reference cost
to the original worker-accounting bytes and retains all other unresolved
categories. The category declarations are not a replacement campaign ledger or
an attested conversion from physical resources to one cost unit.

Promotion-mode admission rejects missing observations, missing bounds and
insufficient declared budget. Even fully populated declarations cannot authorize
promotion in this reference backend: independent production provisioning,
protected production principal, physical currentness/exclusivity, complete
accounting evidence and root promotion acceptance are still unavailable. The
frontend cannot select that trusted dispatcher mode. The selected promotion-mode
negative demonstrates refusal before broker-state or network mutation.

## Formal and original native evidence

`lean/phase17_bridge/ProtectedAuthority.lean` gives a generic bounded broker model.
It checks fixed commission/runtime/current-cursor bindings, exact operation and
credit/intent limits, nonce consumption, retained ambiguity, refusal of repeated
mutation, read-only reconciliation, exact accounting-category coverage and
separate root acceptance. A cloned-broker counterexample explicitly preserves
the limit of local continuity guarantees.

Selected Lean declarations are generated from independently reconstructed
original broker, AM wire, anchor and accounting records. The lost-response
mutation supplies the selected before/issued/pending states. The frontend's
reconciliation nonce is distinct from AM's independently generated read nonce;
the reconciliation theorem certifies a read and zero modeled launches, not a
false equality between those nonces.

The gate retains original administrative authority lifetimes, actual frontend
and worker launches, trusted boundary frames, broker decisions, TLS peers/frames,
AL exports, exact worker streams and accounting. Saved-evidence reconstruction
checks those bytes, source bindings, generated proofs, compiled objects and
explicit completed-stage lineage without starting a compiler, authority or
worker. Historical campaigns are not rerun or reassigned as AN evidence.

The two bounded result flags are:

```text
protected_broker_dispatch_checked
campaign_boundary_admission_checked
```

Their truth requires the complete selected application. Platform-specific native
confinement observations remain separate from those protocol/formal results.
This design document alone establishes no execution acceptance.

## Remaining obligations and retention

All 24 inherited broader flags remain false. Independent production deployment,
complete resource accounting, campaign budget authority integration, physical
and root-transition certification, full learned/autonomous-step instantiation,
promotion, capability gain, frontier/productivity recertification, hosted CI,
Phase 18 independent replay, Gate E and Phase 17 exit remain open.

The next deployment obligation is to supply an independently commissioned
principal or host and externally retained provisioning identity; protect the
authority, broker anchors and credentials from the actual controller/candidate
principal; justify physical durable currentness and exclusivity across restart,
rollback and cloning; close every required accounting category with legitimate
retained measurement rules; and connect the actual promotion-capable campaign to
immutable root acceptance. The v5 Phase 17 → 18 → X → Y → Ω → Z roadmap is unchanged.

Retain the complete application workspace, including its physical authority root
and private credential/state directories, separately from the public execution
recovery archive. Public archives exclude private key material and do not claim
automatic path relocation, takeover of an interrupted installer, or independent
replay. Local reference certificate generation does not provision a production
issuer. The sealed handoff performs no account creation, privilege elevation,
service installation, or production deployment.

## r02 worker scratch-path repair

The r01 worker allocated its scratch directory under the default system temp
parent and immediately applied the strict resolved-path equality guard. Windows
may supply that parent with an MS-DOS 8.3 spelling. The retained successful AM
and AL Windows worker records use such a spelling; resolving it expands the
username component, so the original spelling fails the new AN equality guard.
The frontend's separately allocated `.r17` scratch directory does not exercise
this worker setup path.

The r02 worker resolves the existing system temp parent with `strict=True`
before allocating its fresh owned directory under that parent. The resulting
single directory name supplies the launch specification, actual working
directory, and original native child record. The strict path, protected-target,
overlap, source, and platform-profile validators remain unchanged. Missing or
inaccessible parents still fail; no unconfined Linux fallback is introduced.

The supplied r01 Windows transcript records successful tests, then a live gate
failure, with no advancement of the operator checkout. Its client EOF and final
authority-lifetime error do not reveal the original backend exception: the
inherited transport can replace a worker failure with a poisoned-authority
error. The 8.3 incompatibility is a concrete defect supported by the historical
Windows paths; attribution as the sole cause of that particular failed run
requires additional original diagnostics or successful corrected validation.
The failed physical workspace and original r01 evidence must remain retained.

Constructor regression tests exercise canonical parent allocation and failure
cleanup without launching a worker. Those controlled tests are distinct from
the sealed application's actual workers and from native Windows acceptance.
The earlier complete Linux r01 application retains its original source and kit
attribution. A rebuilt r02 kit requires a fresh complete application.

## Primary implementation references

- [Bubblewrap security model](https://github.com/containers/bubblewrap/blob/main/README.md)
- [Bubblewrap argument specification](https://github.com/containers/bubblewrap/blob/main/bwrap.xml)
- [util-linux unshare implementation](https://github.com/util-linux/util-linux/blob/master/sys-utils/unshare.c)
- [Python TLS interfaces](https://docs.python.org/3/library/ssl.html)
- [Python 3.13 canonical Windows paths](https://docs.python.org/3.13/library/os.path.html#os.path.realpath)
- [Python 3.13 temporary-directory allocation](https://docs.python.org/3.13/library/tempfile.html#tempfile.TemporaryDirectory)
- [SQLite synchronization modes](https://www.sqlite.org/pragma.html#pragma_synchronous)
