# Canonical serialization and hashing

## Canonical JSON profile

All semantic JSON documents use the `RCPRCLM-CJSON-V2` profile.

Required encoding:

```text
UTF-8 without BOM
Unicode normalized to NFC before serialization
object keys sorted lexicographically by Unicode scalar value
no insignificant whitespace
JSON strings escaped with the shortest valid JSON escape
booleans and null use standard lowercase JSON tokens
arrays preserve declared semantic order
```

Native JSON floating-point numbers are forbidden. Mathematical integers and
rationals use the string-based encodings in `NUMERICAL_SEMANTICS.md`. JSON numbers
may be used only for bounded structural counts whose schema explicitly permits
them, such as a dimension or schema version component.

Duplicate object keys, unknown required-object fields, invalid Unicode, and
noncanonical encodings are rejected.

## Canonical byte function

For semantic object `x`:

```text
canonical_payload(x) = RCPRCLM-CJSON-V2 canonical UTF-8 bytes
```

The object content hash is:

```text
SHA256(
  "RCPRCLM-CANONICAL-JSON-V2\0" || canonical_payload(x)
)
```

The NUL byte is literal. Hashes are lowercase hexadecimal in serialized records.

## Path profile

Semantic package paths must be:

```text
relative
POSIX slash separated
Unicode NFC
nonempty
free of empty segments
free of `.` and `..` segments
free of backslashes
free of NUL bytes
```

The following are forbidden:

```text
absolute paths
drive letters
UNC paths
symlinks
hard-link aliases
device files
sockets
named pipes
```

Each semantic file has a declared mode of either:

```text
0644
0755
```

Host ownership, ACLs, creation time, modification time, and access time are not part
of the semantic hash.

## File record

A semantic file record is:

```json
{
  "path": "normalized/relative/path",
  "mode": "0644",
  "size": "1234",
  "sha256": "lowercase-hex"
}
```

`size` is a canonical nonnegative decimal string.

## Tree hash

Files are sorted by the UTF-8 bytes of normalized paths. Each record contributes:

```text
path_utf8 || NUL || mode_ascii || NUL || size_ascii || NUL || sha256_ascii || LF
```

The semantic tree hash is:

```text
SHA256(
  "RCPRCLM-TREE-V2\0" || concatenated_sorted_file_records
)
```

Directories are implicit in paths and do not receive separate records.

## Package manifest

Every candidate and promoted package contains a canonical manifest with at least:

```text
schema_id
contract_version
package_id
parent_package_id
parent_manifest_hash
semantic_tree_hash
candidate_hash
certificate_packet_hash
checker_policy_hash
Lean verifier policy hash
trust_anchor_hash
resource_record_hash
claim_boundary_hash
```

A root package uses JSON `null` for parent identifiers. Nonroot packages must provide
both parent fields and they must match the active predecessor.

## Candidate linkage

The candidate semantic hash covers only the Lean-corresponding update and claimed
successor object:

```text
candidate_hash = hash(update, next)
```

Generator metadata, timestamps, natural-language explanations, and candidate
self-assessments are kept in a separate provenance record and cannot alter the
semantic candidate hash.

## Certificate linkage

The certificate packet hash covers all RCLM evidence registers:

```text
core
semantics
typing
ledger
goal transport
trust
resources
reality
recovery
progress
```

Evidence file references are content addressed. A certificate cannot point to an
unhashed mutable path.

## Parent linkage

For a transition from predecessor `P_t` to candidate `C_{t+1}`:

```text
C_{t+1}.parent_package_id = P_t.package_id
C_{t+1}.parent_manifest_hash = hash(P_t.manifest)
```

The checker obtains the predecessor hash from the immutable active package, not
from the candidate's declaration.

## Trust-anchor linkage

The trust anchor is content addressed and immutable within a run. A candidate that
changes the trust-anchor hash is rejected unless a later contract version defines
an independently verified trust-anchor transition theorem.

## Timestamp policy

Wall-clock timestamps may appear in nonsemantic event logs. They are excluded from:

```text
candidate hash
certificate hash
semantic tree hash
checker verdict hash
promotion identity
```

Semantic ordering uses explicit sequence numbers and parent hashes, not timestamps.

## Verdict serialization

A checker verdict is canonical JSON. It includes:

```text
verdict
reason codes
contract version
input hashes
computed evidence hashes
numeric backend identity
Lean verifier report hash
checker implementation hash
```

Human-readable messages are optional nonsemantic annotations. Reason codes and all
acceptance-relevant values are semantic.

## Cross-platform invariant

Windows, Linux, and macOS must produce identical canonical bytes and SHA-256 values
for identical logical records. Conformance fixtures must include non-ASCII NFC/NFD
cases, Windows path attempts, duplicate-key inputs, ordering mutations, and
whitespace mutations.
