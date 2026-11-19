# Phase 17AM — authenticated authority and retained client currentness

## Baseline and scope

This additive increment starts at completed AL Windows evidence
`ce595d33e68ddd22f16a624d1a1c5d6fa26abd4c` on
`agent/rcp-rclm-v5-phase-17-controller`. AL's tested source is
`643c0ad947d5635ca6d0075397467f3df5483aa6`, tree
`4145435d3bb456673cd4186b31c8394c2f841ac9`. Its retained execution record is
`artifacts/development/phase17al/op-643c0ad947d5/gate/execution.json`, SHA-256
`e603c11f33bf9a8bbc4ac5fc979ca6881930612278333af360a3de7854e288b7`.
PR #68 remains draft and unmerged.

AL owns the actual bounded campaign journal, fixed objective and evaluator,
whole-envelope reservation, once-only launch consumption, and original worker
evidence. Its inherited stdio transport supplies no remote peer authentication.
AM adds an authenticated controller endpoint and a separately retained client
currentness anchor around that same authority. It does not replace AL's root or
reinterpret its historical execution as an AM run.

The selected deployment remains a reference deployment. A successful AM gate
checks real mutually authenticated connections, exact identity and reply
bindings, current-history extension, retained ambiguity after a lost reply,
and two newly admitted bounded workers. Independent production provisioning,
physical durable currentness and global exclusivity remain open.

## Administrative commissioning and fixed dispatch

Commissioning is an administrator action outside controller dispatch. The
public commission binds the AL root provision digest, dedicated CA certificate,
exact server and permitted client certificate identities, server name, protocol,
allowed operations, and AM implementation source closure. Client and service
startup require an independently supplied commission digest and root pin.
Neither endpoint silently trusts a configuration first received over the wire.

The server uses TLS 1.3, requires a verified client certificate, and compares the
actual peer certificate returned by its TLS socket with the commissioned client
identity before application dispatch. The client verifies the dedicated CA,
server hostname and exact actual server certificate identity before sending an
application request. JSON fields cannot supply an authentication result.

The controller interface permits only `read` and `run`. Requests cannot choose
the evaluator, interpreter, source root, grant, completion, storage location,
administrative export, reopening, or shutdown. A trusted parent retains the
separate administrative stop channel. `run` invokes AL's existing admission and
worker path with the exact current cursor and permanently consumed request nonce.
Every reply binds its commission, root, request digest, challenge and before/after
cursors. Framing and request inventories are bounded and exact.

Reference validation generates new ephemeral keys and certificates for each
capture. Private keys are neither payload source nor public evidence and are
excluded from delivery archives. These local reference credentials do not
authenticate an independent production issuer. A production operator must
provision and protect production credentials separately.

## Client currentness and ambiguous responses

An explicitly initialized client anchor starts from an administrator-supplied
trusted AL event prefix. Each authenticated response supplies the actual event
headers. The client recomputes their existing AL hash chain, checks the root and
serial/epoch relationships, and requires extension of the retained prefix.
Replacing a current view with an older or differently forked view is refused.

Before sending a mutation, the client durably records its exact pending request.
A lost or malformed response leaves that pending record. Normal continuation
cannot automatically retry, reissue, refund, or invent completion. An explicit
read-only reconciliation checks authenticated history for that request's durable
completion or denial. An unresolved request remains pending. Learning a result
does not rerun its worker.

The client anchor is a trusted-storage premise. Keeping it separate from the
authority root makes their roles explicit; an owner who can roll back both can
still defeat the local currentness check. A clone possessing the same authorized
key and trusted root history can authenticate. TLS and a cooperative local lock
do not establish global uniqueness, distributed consensus, or power-loss
durability. The formal model retains these limits.

## Observed process boundary

Where the Linux environment supports the selected bubblewrap profile, the
controller client runs with private user, mount, PID, IPC and UTS namespaces,
no capabilities, a read-only source and credential view, and separately scoped
writable client-state and observation directories. A source-bound wrapper
records concrete filesystem and process-visibility denial probes before
executing the client in the same sandbox. The trusted launcher retains that
initial stdout observation. Authority roots and server/CA private keys are not
mounted into that view.

This is a narrow observed controller-confinement result under the Linux kernel
and wrapper assumptions. The network namespace is shared; network access and
host resource use are not fully contained. AL's fixed evaluator workers are not
claimed to use this controller profile. The mutable client anchor still depends
on trusted client behavior and retention. The profile does not provision a
separate production principal or protect against the host owner.

Windows validation exercises the authenticated transport and retained client
protocol without borrowing a Linux isolation result. An unsupported isolation
profile is recorded explicitly. The broader `os_resource_containment`,
`cross_platform_validation`, and independent protected-deployment claims remain
false.

## Formal and native evidence

`lean/phase17_bridge/AuthenticatedAuthority.lean` specifies the structural
authorization and client-currentness rules. Generic proofs cover exact observed
identity and role binding, exact request/reply joins, monotone authenticated
history extension, write-ahead ambiguity, refusal of automatic retry, and
terminal reconciliation. Selected certificates are generated from original
retained request/reply and event-header records, after independent Python
validation. No controller-supplied formal state establishes acceptance.

Lean does not prove TLS, certificate issuance, SHA implementation, Python-to-Lean
refinement, OS isolation, physical storage, or process execution. Socket peer
observations and process records retain their native observer attribution.
The application compiles the new formal module, checks its import resolution,
audits the named theorem inventory and verifies each designated negative
control's exact intended rejection using pinned Lean 4.31.0. It does not rerun
historical proof campaigns or attribute their success to AM.

Saved-evidence reconstruction launches no compiler, authority, worker or live
challenge. It checks original bytes, source bindings, public certificates,
authenticated exchange records, AL exports, worker observations, generated Lean
sources, compiled objects and the completed formal-stage lineage. The installer
must pass that reconstruction before guarded publication.

The two bounded result flags are:

```text
authenticated_authority_transport_checked
pinned_authority_client_checked
```

Their truth requires the complete selected application; this design document
alone is not execution evidence.

## Accounting and remaining obligations

AL's nonrefundable declared-work tariff remains unchanged. AM records actual
application frames and native timings where observed, but does not price omitted
work at zero or turn those observations into complete resource accounting.
Authentication, certificate provisioning, source hashing, transport overhead,
storage synchronization, host CPU/GPU/memory/energy, proof checking, tests,
deployment, and broader/historical campaign activity remain outside that tariff.

All 24 inherited broader claim flags remain false, including complete resource
accounting, campaign budget authority integration, root-transition verification,
physical attestation, promotion, capability gain, Phase 18 independent replay,
frontier/productivity recertification, Gate E and Phase 17 exit.

The next deployment obligation is an independently commissioned protected
authority principal or host, protected retained anchors and credentials,
justified physical durable currentness and exclusivity, and complete campaign
accounting. The admitted endpoint must then be connected to the actual campaign
that can authorize promotion under the immutable root constitution. The v5
Phase 17 → 18 → X → Y → Ω → Z trajectory is unchanged.

## Primary implementation references

- [Python TLS socket and certificate interfaces](https://docs.python.org/3/library/ssl.html)
- [Bubblewrap security model and limitations](https://github.com/containers/bubblewrap/blob/main/README.md)
- [SQLite synchronization modes](https://www.sqlite.org/pragma.html#pragma_synchronous)

