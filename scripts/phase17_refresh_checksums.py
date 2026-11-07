"""Validate or refresh the repository manifest from canonical staged Git blobs.

Default is read-only. --write replaces only SHA256SUMS.txt; it never stages,
commits, pushes, or modifies any historical release. Stage intended files first.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import subprocess


def manifest(root: Path) -> bytes:
    def git(*args: str) -> bytes:
        return subprocess.check_output(["git", "-C", str(root), *args])
    entries = []
    for raw in git("ls-files", "--stage", "-z").split(b"\0"):
        if not raw:
            continue
        metadata, path = raw.split(b"\t", 1)
        mode, oid, stage = metadata.split()
        if stage != b"0" or mode not in (b"100644", b"100755"):
            raise ValueError("unmerged or unsupported index entry")
        if path == b"SHA256SUMS.txt":
            continue
        name = path.decode("utf-8")
        if any(c in name for c in "\r\n\\"):
            raise ValueError("nonportable manifest path")
        content = git("cat-file", "blob", oid.decode("ascii"))
        entries.append((path, f"{hashlib.sha256(content).hexdigest()}  {name}\n"))
    return "".join(line for _, line in sorted(entries)).encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    expected = manifest(root)
    destination = root / "SHA256SUMS.txt"
    if args.write:
        temporary = destination.with_name("SHA256SUMS.txt.phase17.tmp")
        if temporary.exists():
            raise SystemExit("temporary manifest already exists; inspect it before retrying")
        try:
            with temporary.open("xb") as handle:
                handle.write(expected)
                handle.flush()
            temporary.replace(destination)
        finally:
            temporary.unlink(missing_ok=True)
        print(f"Updated canonical manifest: {expected.count(bytes([10]))} entries; not committed")
        return 0
    actual = subprocess.check_output(["git", "-C", str(root), "cat-file", "blob", ":SHA256SUMS.txt"])
    if actual != expected:
        raise SystemExit("Staged SHA256SUMS.txt does not match staged canonical blobs")
    print(f"PASS: {expected.count(bytes([10]))} canonical index checksum entries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
