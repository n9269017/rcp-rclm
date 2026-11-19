"""Capture/verify local Phase 17A evidence; never grant promotion or phase closure.

Python 3.11+ and ordinary Git only. Output must be outside the checkout.
A clean Git checkout is NOT an isolated/clean operating-system environment.
A pinned manifest detects altered bytes; it does NOT authenticate their author.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import subprocess
import sys
import time

PROFILE = "phase17a-local-foundation-v1"
SCHEMA = "rcp-rclm.local-validation.v1"
MAX_FILE_BYTES = 32 * 1024 * 1024
FALSE_CLAIMS = (
    "github_hosted_ci_passed", "clean_environment_replay_passed",
    "independent_worker_free_replay_passed", "cross_platform_validation_passed",
    "pinned_lean_verification_passed", "phase17_exit_closed", "gate_e_closed",
    "egc0_started", "promotion_authorized", "main_merge_authorized",
)
COMMANDS = (
    ("compile", ("python", "-m", "compileall", "-q",
                 "python/rcp_rclm_runtime_v5", "scripts/run_phase17_tests.py",
                 "scripts/phase17_refresh_checksums.py", "scripts/phase17_local_evidence.py")),
    ("foundation-tests", ("python", "scripts/run_phase17_tests.py")),
    ("canonical-checksums", ("python", "scripts/phase17_refresh_checksums.py")),
)
REPORT_KEYS = {
    "schema", "profile", "evidence_kind", "source", "environment",
    "started_at_utc", "finished_at_utc", "commands", "source_unchanged",
    "local_checks_passed", "claims", "limitations",
}
COMMAND_KEYS = {
    "id", "argv", "status", "returncode", "duration_ms", "stdout", "stderr",
    "started_at_utc", "finished_at_utc", "test_summary",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _git(root: Path, *args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(root), *args], stderr=subprocess.PIPE)


def _source(root: Path) -> dict[str, str]:
    if _git(root, "status", "--porcelain", "--untracked-files=all").strip():
        raise ValueError("clean checkout required; preserve/stage/commit intended work first")
    commit = _git(root, "rev-parse", "HEAD").decode().strip()
    tree = _git(root, "rev-parse", "HEAD^{tree}").decode().strip()
    if _git(root, "write-tree").decode().strip() != tree:
        raise ValueError("index differs from HEAD")
    return {"commit": commit, "tree": tree,
            "root_manifest_sha256": _sha(_git(root, "cat-file", "blob", "HEAD:SHA256SUMS.txt"))}


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2,
                       allow_nan=False) + "\n").encode("utf-8")


def _strict_json(data: bytes) -> object:
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result
    def no_float(_):
        raise ValueError("floating-point/nonfinite report number is forbidden")
    return json.loads(data.decode("utf-8"), object_pairs_hook=pairs,
                      parse_float=no_float, parse_constant=no_float)


def _test_summary(stderr: bytes) -> dict[str, object]:
    text = stderr.decode("utf-8", errors="replace")
    counts = re.findall(r"^Ran (\d+) tests? in .+$", text, re.MULTILINE)
    skipped = re.findall(r"^.* \.\.\. skipped .+$", text, re.MULTILINE)
    count = int(counts[-1]) if len(counts) == 1 else None
    plain_ok = re.search(r"^OK\s*$", text, re.MULTILINE) is not None
    return {"tests_run": count, "skipped": len(skipped),
            "minimum_required": 33,
            "accepted": count is not None and count >= 33 and plain_ok and not skipped}


def _plan_passed(commands: list[dict]) -> bool:
    return all(c["status"] == "passed" for c in commands)


def capture(root: Path, output: Path, expected_head: str, timeout: int = 900) -> dict:
    if sys.version_info < (3, 11):
        raise ValueError("Python 3.11+ is required")
    if type(timeout) is not int or not 1 <= timeout <= 86400:
        raise ValueError("timeout must be between 1 and 86400 seconds per command")
    root, output = root.resolve(), output.resolve()
    if root == output or root in output.parents:
        raise ValueError("evidence output must be outside the source checkout")
    if not re.fullmatch(r"[0-9a-f]{40}", expected_head):
        raise ValueError("expected HEAD must be a full Git SHA-1")
    source = _source(root)
    if source["commit"] != expected_head:
        raise ValueError("source HEAD does not match the externally supplied expected HEAD")
    output.mkdir(parents=True, exist_ok=False)
    (output / "logs").mkdir()
    report = {
        "schema": SCHEMA, "profile": PROFILE, "evidence_kind": "local_process_capture",
        "source": source,
        "environment": {
            "os": platform.system(), "os_release": platform.release(),
            "machine": platform.machine(), "python_version": platform.python_version(),
            "python_implementation": platform.python_implementation(),
            "git_version": _git(root, "--version").decode().strip(),
            "installed_distributions": sorted(
                [{"name": d.metadata.get("Name", "unknown"), "version": d.version}
                 for d in importlib.metadata.distributions()],
                key=lambda d: (d["name"].lower(), d["version"])),
            "python_utf8": True,
            "environment_isolation": "not_established",
            "execution_location": "local_not_github_hosted",
        },
        "started_at_utc": _now(), "finished_at_utc": None, "commands": [],
        "source_unchanged": False, "local_checks_passed": False,
        "claims": {key: False for key in FALSE_CLAIMS},
        "limitations": [
            "Local capture is not hosted CI, a platform matrix, pinned Lean verification, or phase closure.",
            "A clean repository does not establish a clean or isolated execution environment.",
            "Checksums provide integrity relative to an external anchor, not author authentication.",
            "Logs and installed package metadata must be reviewed before public upload.",
        ],
    }
    stopped = False
    for name, argv in COMMANDS:
        stdout, stderr = f"logs/{name}.stdout.txt", f"logs/{name}.stderr.txt"
        entry = {"id": name, "argv": list(argv), "status": "not_run", "returncode": None,
                 "duration_ms": None, "stdout": stdout, "stderr": stderr,
                 "started_at_utc": None, "finished_at_utc": None, "test_summary": None}
        with (output / stdout).open("xb") as out, (output / stderr).open("xb") as err:
            if not stopped:
                entry["started_at_utc"] = _now()
                start = time.monotonic_ns()
                try:
                    env = dict(os.environ, PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1")
                    result = subprocess.run([sys.executable, *argv[1:]], cwd=root,
                                            env=env, stdin=subprocess.DEVNULL,
                                            stdout=out, stderr=err, timeout=timeout, check=False)
                    entry["returncode"] = result.returncode
                    entry["status"] = "passed" if result.returncode == 0 else "failed"
                except subprocess.TimeoutExpired:
                    entry["status"] = "timed_out"
                except OSError as exc:
                    entry["status"] = "start_failed"
                    err.write((type(exc).__name__ + ": " + str(exc) + "\n").encode("utf-8"))
                entry["duration_ms"] = (time.monotonic_ns() - start) // 1_000_000
                entry["finished_at_utc"] = _now()
        if any((output / p).stat().st_size > MAX_FILE_BYTES for p in (stdout, stderr)):
            entry["status"] = "log_limit_exceeded"
        if name == "foundation-tests" and entry["status"] == "passed":
            entry["test_summary"] = _test_summary((output / stderr).read_bytes())
            if not entry["test_summary"]["accepted"]:
                entry["status"] = "failed"
        report["commands"].append(entry)
        stopped = stopped or entry["status"] != "passed"
    try:
        report["source_unchanged"] = _source(root) == source
    except (ValueError, subprocess.CalledProcessError):
        report["source_unchanged"] = False
    report["local_checks_passed"] = _plan_passed(report["commands"]) and report["source_unchanged"]
    report["finished_at_utc"] = _now()
    (output / "evidence.json").write_bytes(_json_bytes(report))
    names = ["evidence.json"] + [str(c[k]) for c in report["commands"] for k in ("stdout", "stderr")]
    manifest = "".join(f"{_sha((output / n).read_bytes())}  {n}\n" for n in sorted(names))
    (output / "SHA256SUMS.txt").write_bytes(manifest.encode("utf-8"))
    return report


def verify(output: Path, expected_head: str, expected_manifest_sha256: str) -> dict:
    """Integrity/consistency check only. This never executes commands in a report."""
    output = output.resolve()
    if not re.fullmatch(r"[0-9a-f]{40}", expected_head):
        raise ValueError("expected HEAD must be a full Git SHA-1")
    if not re.fullmatch(r"[0-9a-f]{64}", expected_manifest_sha256):
        raise ValueError("an externally retained manifest SHA-256 is required")
    files = [p for p in output.rglob("*") if p.is_file()]
    if any(p.is_symlink() for p in output.rglob("*")):
        raise ValueError("symlinks are forbidden in evidence")
    if any(p.stat().st_size > MAX_FILE_BYTES for p in files):
        raise ValueError("evidence file too large")
    manifest = (output / "SHA256SUMS.txt").read_bytes()
    if _sha(manifest) != expected_manifest_sha256:
        raise ValueError("external manifest anchor mismatch")
    listed = {}
    for line in manifest.decode("utf-8").splitlines():
        digest, name = line.split("  ", 1)
        pure = PurePosixPath(name)
        if (name in listed or not re.fullmatch(r"[0-9a-f]{64}", digest)
            or pure.is_absolute() or ".." in pure.parts or "\\" in name or ":" in name
            or pure.as_posix() != name):
            raise ValueError("unsafe or duplicate manifest entry")
        listed[name] = digest
    actual = {p.relative_to(output).as_posix(): _sha(p.read_bytes())
              for p in files if p != output / "SHA256SUMS.txt"}
    expected_names = {"evidence.json"} | {f"logs/{n}.{s}.txt" for n, _ in COMMANDS for s in ("stdout", "stderr")}
    if set(actual) != expected_names or actual != listed:
        raise ValueError("evidence membership or content checksum mismatch")
    report = _strict_json((output / "evidence.json").read_bytes())
    if not isinstance(report, dict) or set(report) != REPORT_KEYS:
        raise ValueError("unknown or missing report fields")
    if (report["schema"] != SCHEMA or report["profile"] != PROFILE
        or report["evidence_kind"] != "local_process_capture"):
        raise ValueError("unsupported evidence profile")
    source = report["source"]
    if (not isinstance(source, dict) or set(source) != {"commit", "tree", "root_manifest_sha256"}
        or source["commit"] != expected_head or not re.fullmatch(r"[0-9a-f]{40}", source["tree"])
        or not re.fullmatch(r"[0-9a-f]{64}", source["root_manifest_sha256"])):
        raise ValueError("source binding mismatch")
    claims = report["claims"]
    if not isinstance(claims, dict) or set(claims) != set(FALSE_CLAIMS) or any(v is not False for v in claims.values()):
        raise ValueError("unsupported success or closure claim")
    commands = report["commands"]
    if not isinstance(commands, list) or len(commands) != len(COMMANDS):
        raise ValueError("required command omitted or duplicated")
    stopped = False
    for entry, (name, argv) in zip(commands, COMMANDS, strict=True):
        if (not isinstance(entry, dict) or set(entry) != COMMAND_KEYS
            or entry["id"] != name or entry["argv"] != list(argv)
            or entry["stdout"] != f"logs/{name}.stdout.txt"
            or entry["stderr"] != f"logs/{name}.stderr.txt"):
            raise ValueError("command profile mismatch")
        state, rc = entry["status"], entry["returncode"]
        if state not in {"passed", "failed", "timed_out", "start_failed", "not_run", "log_limit_exceeded"}:
            raise ValueError("unknown command state")
        if state == "not_run":
            if not stopped or rc is not None or entry["duration_ms"] is not None:
                raise ValueError("unjustified or inconsistent skipped command")
            if any((output / entry[k]).read_bytes() for k in ("stdout", "stderr")):
                raise ValueError("unexecuted command has output")
        else:
            if stopped or type(entry["duration_ms"]) is not int or entry["duration_ms"] < 0:
                raise ValueError("fail-fast or timing boundary violated")
            if rc is not None and type(rc) is not int:
                raise ValueError("return code must be an integer or null")
            if state == "passed" and (type(rc) is not int or rc != 0):
                raise ValueError("pass without successful exit")
        if name == "foundation-tests" and rc == 0 and state in {"passed", "failed"}:
            summary = _test_summary((output / entry["stderr"]).read_bytes())
            if summary != entry["test_summary"] or (state == "passed") != summary["accepted"]:
                raise ValueError("test summary inconsistent with retained log")
        elif entry["test_summary"] is not None:
            raise ValueError("unexpected test summary")
        stopped = stopped or state != "passed"
    if type(report["source_unchanged"]) is not bool:
        raise ValueError("source_unchanged must be a boolean")
    passed = _plan_passed(commands) and report["source_unchanged"]
    if report["local_checks_passed"] is not passed:
        raise ValueError("claimed local pass differs from command/source evidence")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    cap = sub.add_parser("capture")
    cap.add_argument("--output", type=Path, required=True)
    cap.add_argument("--expected-head", required=True)
    cap.add_argument("--timeout", type=int, default=900)
    check = sub.add_parser("verify")
    check.add_argument("--bundle", type=Path, required=True)
    check.add_argument("--expected-head", required=True)
    check.add_argument("--expected-manifest-sha256", required=True)
    args = parser.parse_args()
    try:
        if args.mode == "capture":
            report = capture(Path(__file__).resolve().parents[1], args.output, args.expected_head, args.timeout)
            digest = _sha((args.output / "SHA256SUMS.txt").read_bytes())
            print(json.dumps({"source_commit": args.expected_head,
                              "manifest_sha256": digest,
                              "local_checks_passed": report["local_checks_passed"],
                              "phase17_exit_closed": False, "gate_e_closed": False}, sort_keys=True))
        else:
            report = verify(args.bundle, args.expected_head, args.expected_manifest_sha256)
            print(json.dumps({"integrity_checked": True, "author_authenticated": False,
                              "local_checks_passed": report["local_checks_passed"],
                              "phase17_exit_closed": False, "gate_e_closed": False}, sort_keys=True))
        return 0 if report["local_checks_passed"] else 1
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
