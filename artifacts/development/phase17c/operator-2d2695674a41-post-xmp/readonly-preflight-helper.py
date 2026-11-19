"""Read-only, bounded historical-bootstrap integrity diagnosis for Phase 17C.

Runs exactly twelve independent bootstrap-only observations; never retries an
observation until it passes. No live challenge, phase test suite, candidate,
acceptance bypass, source patch, Git write, installation, push, or promotion.
All expected data hashes are from the pinned already-public historical archives.
Additional observations are in-memory wrappers; original functions and their
return values/exceptions are preserved. This is not uninstrumented validation.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import importlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import subprocess
import sys
import time
import uuid

sys.dont_write_bytecode = True
BASE = "bb1f8669311c099938cc299c2b4fd9f5f77be9e3"
BRANCH = "agent/rcp-rclm-v5-phase-17-controller"
FAILED_SOURCE = "2d2695674a417cea04947400fa617ac6b34b9d5b"
MANIFEST_HASH = "1477e124cb7a4d214402595d84628c1403ba097bcd78717ae81d2ebd5f8d068e"
SUITE_REPORT_SHA256 = "93b0554fd3169870d3c21ff3e3ca9ea4b7be7a257964154ef86b5bb8449f8760"
OBSERVATIONS = 12
ALLOWED_EXTRA = {
    "SHA256SUMS.txt", "docs/executable_core_v5/PHASE_17_IMPLEMENTATION.md",
    "docs/executable_core_v5/PHASE_17_LOCAL_VALIDATION.json",
}
CLAIMS = {
    "diagnostic_only": True, "repair_applied": False,
    "phase17_exit_closed": False, "gate_e_closed": False,
    "egc0_started": False, "promotion_authorized": False,
    "full_validation_passed": False, "original_failure_resolved": False,
}

REFERENCE = {'archives': {'capture': {'path': 'artifacts/development/phase17b/phase16-capture-31153935872-1.zip', 'sha256': '7337079801916ecccce0e3a292d5379cea17b571acc6f31b9b38cb21f9f63dde', 'size': 6524813}, 'closure': {'path': 'artifacts/releases/v4.5-phase15-phase16-results/original-artifacts/runtime-v4-phase16-final-closure-31153935872-1.zip', 'sha256': 'ce7f1de4654306d5280970dfc92453a8743cf1e02fe98963f1e940c0077582f9', 'size': 3767}, 'm9': {'path': 'artifacts/private_phase16/bootstrap/runtime-v4-phase15-bundle-30969783629-1.zip', 'sha256': '56003f95ded054be21dd3f743c2145fdf6e92543af28bb350f64ec8f4fee00b5', 'size': 5310668}}, 'members': {'phase16_capture.json': {'archive': 'capture', 'sha256': 'fad1ef726a5c7385e8f4ee8f4c93960005eb5a91fbf268fcd6f9451bc6caf9b3', 'size': 50929889, 'crc32': 2041791256}, 'phase16_closure.json': {'archive': 'closure', 'sha256': 'ad27cdba93d3dd93e3092b2b3aa2e019b0dce9c759731103579d8c211b9c1e5a', 'size': 5770, 'crc32': 2616894657}, 'phase16_exit.json': {'archive': 'closure', 'sha256': 'ad27cdba93d3dd93e3092b2b3aa2e019b0dce9c759731103579d8c211b9c1e5a', 'size': 5770, 'crc32': 2616894657}, 'manifest.json': {'archive': 'closure', 'sha256': '5df5b5caed42760ffe5516510b4eef857453b90246bd616aa25391009ffb21e5', 'size': 1371, 'crc32': 2810921475}, 'campaign/candidate_freeze/multidomain/semantic_candidate/model/phase15_planner/manifest.json': {'archive': 'm9', 'sha256': '1439cb69b09d4d0b637c9b2a62172f4150f79bd57d0d52a813ef4435544c9ea9', 'size': 975, 'crc32': 398023694}, 'campaign/candidate_freeze/multidomain/semantic_candidate/model/phase15_planner/weights.i16le.bin': {'archive': 'm9', 'sha256': '19869eac5b0da770505214a6c5817b94dfda05730f97598bf2f855aff82d6c8d', 'size': 65536, 'crc32': 3854103287}, 'campaign/candidate_freeze/multidomain/semantic_candidate/package_manifest.json': {'archive': 'm9', 'sha256': 'd7679bf5a96baf19616c0a6a15b2f295580a4c47231acba39ad926e951efde6b', 'size': 2387, 'crc32': 544299995}}, 'records': {'ad6d25e453840cefb7240de7854d2a53572c7af0a6b38851efd76654fb84bbb6': {'label': 'capture', 'field': 'report_hash', 'canonical_size': 38104201, 'canonical_sha256': '440379d187507c5f671531699a2805a0529cdfe05bf56f9cbd663dccfaaae6b5', 'domain_hash': 'ad6d25e453840cefb7240de7854d2a53572c7af0a6b38851efd76654fb84bbb6'}, 'f5c4943647c3a54ab4e1686a45c64926844fb97a99f7eafe054679a34ba896ee': {'label': 'closure', 'field': 'report_hash', 'canonical_size': 4834, 'canonical_sha256': '60e65440b77ff86a7d40efc368622fa5b1b9ec8ef68815422ee2687382912461', 'domain_hash': 'f5c4943647c3a54ab4e1686a45c64926844fb97a99f7eafe054679a34ba896ee'}, 'f052e6055dcd2fe6fc34907a2684dd3cbac7e94d32bad18a4d9ed921da7c0513': {'label': 'bootstrap', 'field': 'report_hash', 'canonical_size': 1678, 'canonical_sha256': '9bdf9cbce9b9073faf4b79b430785fbb3af760bffc8fa94ffbf96a0e5cc00c21', 'domain_hash': 'f052e6055dcd2fe6fc34907a2684dd3cbac7e94d32bad18a4d9ed921da7c0513'}, '67045ba2da9dd897b851bba31f05ed0e9faf93fa665245f87803904cfa5fe6d7': {'label': 'planner', 'field': 'manifest_hash', 'canonical_size': 892, 'canonical_sha256': '3f62874ac5ee69b0dfe7e87e2c60e269b018bc3773ea485410cf2f40539e5ebd', 'domain_hash': '67045ba2da9dd897b851bba31f05ed0e9faf93fa665245f87803904cfa5fe6d7'}, 'e4e68386d2896d843bd741c0de93897ceeda7eecef503ec4a396b6d235dcb170': {'label': 'campaign-0', 'field': 'report_hash', 'canonical_size': 501944, 'canonical_sha256': 'f292b585edea1d85acf806d6f848638b4a73bec869f82a9efe42287266e617c7', 'domain_hash': 'e4e68386d2896d843bd741c0de93897ceeda7eecef503ec4a396b6d235dcb170'}, '6e82e9ed115464b540858a9fa5fe3c1a91615af7408291cad44110efad949631': {'label': 'campaign-1', 'field': 'report_hash', 'canonical_size': 937322, 'canonical_sha256': 'f3bcdc8fbc9bf2bbb9177403375d29fd0752c24ce49d5e66bd43e03ae2b62697', 'domain_hash': '6e82e9ed115464b540858a9fa5fe3c1a91615af7408291cad44110efad949631'}, '839d590a28b34ca2cedb43c6d5444eaa652cd413cc820978ceba8d6ecbc84f21': {'label': 'campaign-2', 'field': 'report_hash', 'canonical_size': 1821693, 'canonical_sha256': '6a5663b36a458e93d91c455b9796e28b32ce27678f65478a767d68b4ff178903', 'domain_hash': '839d590a28b34ca2cedb43c6d5444eaa652cd413cc820978ceba8d6ecbc84f21'}, '8d5e7b70372023bc4e7dfc8dcba33fb0874844ebf8e4abf1733d84f99b15f56c': {'label': 'campaign-3', 'field': 'report_hash', 'canonical_size': 4005749, 'canonical_sha256': 'c544455b1abafa1204c7b26b1be0ccf5752bf5d37d53ada15271d1cc6547ea72', 'domain_hash': '8d5e7b70372023bc4e7dfc8dcba33fb0874844ebf8e4abf1733d84f99b15f56c'}, '20b1ed589f2dcc1f085fd0aaa11859a1e9bdf0a43eb9063497574983747a1e3d': {'label': 'campaign-4', 'field': 'report_hash', 'canonical_size': 502059, 'canonical_sha256': 'ee8168ad6e9bba26e7dc5346de002dda53b2bc48f2ae95940be01c68ef66d571', 'domain_hash': '20b1ed589f2dcc1f085fd0aaa11859a1e9bdf0a43eb9063497574983747a1e3d'}, '589c36ce9627a16d0f5fa5aabe3f4e2d77f3828e56e3dc0dafc6a66cb3af3a36': {'label': 'campaign-5', 'field': 'report_hash', 'canonical_size': 1012330, 'canonical_sha256': 'd66c990fac098b1c8acc9ff4f50b1f376cadb5515411af77a6ebda6a62e01664', 'domain_hash': '589c36ce9627a16d0f5fa5aabe3f4e2d77f3828e56e3dc0dafc6a66cb3af3a36'}, 'aee5b4e7997a95e877838cb70d2a8eede92617864410436ca6db647f7167fb62': {'label': 'campaign-6', 'field': 'report_hash', 'canonical_size': 2012055, 'canonical_sha256': '857aac0deb2abc496398b603ce9fed777417432c655cbdda46af79d8a3d87b2f', 'domain_hash': 'aee5b4e7997a95e877838cb70d2a8eede92617864410436ca6db647f7167fb62'}, 'a640cdcbca7bfa7e7c334b7c045f11a4e9dcb01e4993deeece6c1067cdff1dac': {'label': 'campaign-7', 'field': 'report_hash', 'canonical_size': 4392220, 'canonical_sha256': '8f0ac26a01725af3247e13ec21f2668fe34e6a4c44b00be4dd47f658a9fd260f', 'domain_hash': 'a640cdcbca7bfa7e7c334b7c045f11a4e9dcb01e4993deeece6c1067cdff1dac'}, 'e979bb0fe58b7c36921a90f4fe51fdbbeb05a732ebf0ebf856681f9706c0de19': {'label': 'campaign-8', 'field': 'report_hash', 'canonical_size': 559928, 'canonical_sha256': 'b37a539a876e68eabbce300e6240811d17766fa456deaa69ff9eb82d18b0b1f6', 'domain_hash': 'e979bb0fe58b7c36921a90f4fe51fdbbeb05a732ebf0ebf856681f9706c0de19'}, 'f8fb09dda71c35ac7f6771c9a72c1d021c2a24d9151787e3ad16f01618b8515e': {'label': 'campaign-9', 'field': 'report_hash', 'canonical_size': 1070550, 'canonical_sha256': '1f1cbfc3eb3cfeec5e3477ca3462f36c1626a275a75f4cc0e567fe9a8d697cdd', 'domain_hash': 'f8fb09dda71c35ac7f6771c9a72c1d021c2a24d9151787e3ad16f01618b8515e'}, 'a648f3d7aaea082cbe5f1c945df3a787d1d49688199176cdf116782a5a332f77': {'label': 'campaign-10', 'field': 'report_hash', 'canonical_size': 2018735, 'canonical_sha256': 'd26b7bc41f2935a911e9d487c5b9dbacbbd6aa970d01169dd06e4c3b2d6a85e0', 'domain_hash': 'a648f3d7aaea082cbe5f1c945df3a787d1d49688199176cdf116782a5a332f77'}, '68ae85f8c9a196e35360379145a0ae2e3c369e0feec8378ed789ceedd0634a26': {'label': 'campaign-11', 'field': 'report_hash', 'canonical_size': 4289721, 'canonical_sha256': 'b9044201422b5cd40ca5ef1991e488d226211cfc0063d1fe33846a0a0340ee6f', 'domain_hash': '68ae85f8c9a196e35360379145a0ae2e3c369e0feec8378ed789ceedd0634a26'}, 'a4d8d0b5be7f798d2b31d9f0301a4f3a92f065bf8a9c16ed30144c607fdaea1e': {'label': 'campaign-12', 'field': 'report_hash', 'canonical_size': 404241, 'canonical_sha256': '5035ea98d6e44c5df72609e5015998d29959df3e19f5cb855fa4dccc7e72551d', 'domain_hash': 'a4d8d0b5be7f798d2b31d9f0301a4f3a92f065bf8a9c16ed30144c607fdaea1e'}, '1e8dcc237dd60e9633465fdd927875a10e11d80f405ba8583a30904ea5d9350d': {'label': 'campaign-13', 'field': 'report_hash', 'canonical_size': 1035895, 'canonical_sha256': '3015147be47cb68a31e9b853ee1b018a5c1c9b3997cdba8b29ee93fed4a8eb40', 'domain_hash': '1e8dcc237dd60e9633465fdd927875a10e11d80f405ba8583a30904ea5d9350d'}, '6c795e198d14e4c41a83f7e5de97ffef018d35d30dd3b02cc1c7adf7898a188e': {'label': 'campaign-14', 'field': 'report_hash', 'canonical_size': 1977949, 'canonical_sha256': '1e6ca9c098de662e9475641057cb9db00536802bc209d86ace33f8fb30054b99', 'domain_hash': '6c795e198d14e4c41a83f7e5de97ffef018d35d30dd3b02cc1c7adf7898a188e'}, '58996b3874f81b9b1604bc9ecd82acfa9c465f6f86ccc1345aa0c0edc968c78a': {'label': 'campaign-15', 'field': 'report_hash', 'canonical_size': 4162101, 'canonical_sha256': 'e21661361f9ec6c3dd02029d2eb429732845b56b884ba14b8674e68148867cf7', 'domain_hash': '58996b3874f81b9b1604bc9ecd82acfa9c465f6f86ccc1345aa0c0edc968c78a'}, '6a47aff091b3568012b61643bb9df94b17e6dbcc9de47c453465f973ec07ee90': {'label': 'campaign-16', 'field': 'report_hash', 'canonical_size': 7393384, 'canonical_sha256': 'e760205bcc98ba0e4ebc26f7667a8a363acd6127faf3a2693d98f37fafe8058b', 'domain_hash': '6a47aff091b3568012b61643bb9df94b17e6dbcc9de47c453465f973ec07ee90'}, 'e5166a8ff123c792fce3c390d8ef70b2758e42bb516a0cdbaca0a500ef41eb8a': {'label': 'replay-0', 'field': 'report_hash', 'canonical_size': 999, 'canonical_sha256': 'ec75cd1736556e27edd087211fb476166f4822a99ba7401c4b1fd57cc678c57e', 'domain_hash': 'e5166a8ff123c792fce3c390d8ef70b2758e42bb516a0cdbaca0a500ef41eb8a'}, '3ea54489b526d0a9250f053099e209a075f055847e925bd7cb3d6131b4963235': {'label': 'replay-1', 'field': 'report_hash', 'canonical_size': 1000, 'canonical_sha256': 'fdfa6a2c851605ceee2f5b708622944a0c8cb5027634799155837bbe3930ba5e', 'domain_hash': '3ea54489b526d0a9250f053099e209a075f055847e925bd7cb3d6131b4963235'}, 'b435ebf4412af72ed2f4c85af81785557a5f945df6f6be4b56829117843ea704': {'label': 'replay-2', 'field': 'report_hash', 'canonical_size': 998, 'canonical_sha256': 'd424c912c4ab9162dec968c0a783c5f6718a7b64480fc7d1add4652b4c7c0598', 'domain_hash': 'b435ebf4412af72ed2f4c85af81785557a5f945df6f6be4b56829117843ea704'}}, 'source_files': {'python/rcp_rclm_runtime_v5/rcp_rclm_runtime_v5/phase17/bootstrap.py': 'c95e37240101e94de540300f23a977d0492449e3890c2a5b928c142fd622389e', 'python/rcp_rclm_runtime_v2/rcp_rclm_runtime/canonical/hashing.py': '0753f5264f7b261cc5b684487a6506317907407307d582ec8091259deb58e62b', 'python/rcp_rclm_runtime_v2/rcp_rclm_runtime/canonical/json.py': 'c34dfb2895c11ff317dbbb37c563765d181a13731ad566e04f4bc09153832353'}}

def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def write_json(path: Path, value: object) -> None:
    path.write_bytes((json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode())

def git(repo: Path, *args: str) -> bytes:
    # These call sites use read-only Git commands only. Avoid optional index refresh.
    return subprocess.check_output(
        ["git", "--no-optional-locks", "-C", str(repo), *args],
        stderr=subprocess.PIPE, timeout=45,
    )

def text(repo: Path, *args: str) -> str:
    return git(repo, *args).decode("utf-8").strip()

def regular(path: Path) -> None:
    require(path.is_file() and not path.is_symlink(), "required regular file missing: " + str(path))

def relative(value: str) -> str:
    require(type(value) is str and value and not any(c in value for c in "\\:\x00\r\n"),
            "unsafe relative path")
    p = PurePosixPath(value)
    require(not p.is_absolute() and ".." not in p.parts and p.as_posix() == value,
            "unsafe relative path")
    return value

def snapshot(repo: Path) -> dict:
    regular(repo / "SHA256SUMS.txt")
    return {
        "head": text(repo, "rev-parse", "HEAD"),
        "tree": text(repo, "rev-parse", "HEAD^{tree}"),
        "branch": text(repo, "branch", "--show-current"),
        "status": git(repo, "status", "--porcelain", "--untracked-files=all").decode(),
        "root_manifest_sha256": sha((repo / "SHA256SUMS.txt").read_bytes()),
    }

def preflight(repo: Path, kit: Path, run: Path) -> tuple[Path, dict, dict]:
    require(Path(text(repo, "rev-parse", "--show-toplevel")).resolve() == repo,
            "use the exact original repository root")
    original = snapshot(repo)
    require(original["head"] == BASE and original["branch"] == BRANCH and not original["status"],
            "original branch moved or is not clean; no changes made")
    require(run.parent == (kit / "runs").resolve() and run.is_dir(),
            "failed run must be an existing direct child of the original kit/runs")
    for name in ("progress.json", "evidence/FAILED_COMMAND.json",
                 "evidence/command-logs/process-and-differential.stderr.txt"):
        regular(run / name)
    progress = json.loads((run / "progress.json").read_bytes())
    require(progress.get("original_checkout_changed") is False and progress.get("pushed") is False,
            "the supplied run is not the unadvanced failed installation")
    stage = (run / "checkout").resolve()
    require(stage.parent == run, "unexpected checkout location")
    before = snapshot(stage)
    source = progress.get("tested_code_commit")
    require(type(source) is str and re.fullmatch(r"[0-9a-f]{40}", source) is not None,
            "invalid recorded source commit")
    require(before["head"] == source and not before["status"], "failed checkout changed or is dirty")
    require(text(stage, "rev-list", "--parents", "-n", "1", source).split() == [source, BASE],
            "unexpected source ancestry; no branch rewrite is allowed")
    manifest = kit / "PAYLOAD_MANIFEST.json"
    regular(manifest)
    require(sha(manifest.read_bytes()) == MANIFEST_HASH, "original kit manifest differs")
    obj = json.loads(manifest.read_bytes())
    require(obj.get("base_commit") == BASE and obj.get("branch") == BRANCH, "wrong kit target")
    files = obj["files"]
    require(type(files) is dict and len(files) == 37, "original payload set differs")
    changed = {p.decode() for p in git(stage, "diff", "--name-only", "-z", BASE, source).split(b"\0") if p}
    require(changed == set(files) | ALLOWED_EXTRA, "source contains unexpected changed paths")
    for rel, expected in files.items():
        relative(rel)
        path = stage / rel
        regular(path)
        require(stage in path.resolve().parents, "source path escaped checkout")
        require(sha(git(stage, "cat-file", "blob", source + ":" + rel)) == expected
                and sha(path.read_bytes()) == expected, "source/preimage mismatch: " + rel)
    failed = json.loads((run / "evidence/FAILED_COMMAND.json").read_bytes())
    require(failed.get("name") == "process-and-differential" and failed.get("returncode") == 1,
            "this diagnostic is for the reported process-suite failure only")
    log = (run / "evidence/command-logs/process-and-differential.stderr.txt").read_bytes()
    require(sha(log) == failed.get("stderr_sha256"), "failed log differs from its recorded digest")
    require(b"test_seal_prevents_more_requests" in log and b"FAILED (errors=1)" in log,
            "reported failure signature differs")
    return stage, original, before


def alternate_backend():
    """Optional CPython built-in SHA-256 backend, not a replacement verifier."""
    for name in ("_sha2", "_sha256"):
        try:
            module = importlib.import_module(name)
            constructor = getattr(module, "sha256")
            # Refuse a broken backend without relabeling it as the default.
            if constructor(b"abc").hexdigest() != "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad":
                return None, name + ":known-answer-failed"
            return constructor, name + ".sha256"
        except (ImportError, AttributeError):
            continue
    return None, "unavailable"


def digest_observation(data: bytes, expected: str | None, alternate=None) -> dict:
    first = hashlib.sha256(data).hexdigest()
    second = hashlib.sha256(data).hexdigest()
    other = alternate(data).hexdigest() if alternate is not None else None
    return {
        "size": len(data), "expected_sha256": expected,
        "native_sha256_first": first, "native_sha256_second": second,
        "alternate_sha256": other,
        "native_repeat_equal": first == second,
        "native_matches_expected": first == expected if expected is not None else None,
        "alternate_matches_expected": other == expected if other is not None and expected is not None else None,
        "backends_agree": other == first if other is not None else None,
        "anomaly": first != second or (expected is not None and first != expected)
                   or (other is not None and other != first),
    }


def safe_exception(exc: BaseException, stage: Path) -> dict:
    """Types/locations/CRC numbers only. No exception text, data, or locals dump."""
    nodes, seen = [], set()
    current = exc
    for _ in range(8):
        if current is None or id(current) in seen:
            break
        seen.add(id(current))
        node = {"type": type(current).__name__, "module": type(current).__module__,
                "exception_text_retained": False, "locations": []}
        for key in ("errno", "winerror"):
            value = getattr(current, key, None)
            if type(value) is int:
                node[key] = value
        # Only classify a few known messages; do not retain arbitrary text.
        msg = current.args[0] if current.args and type(current.args[0]) is str else ""
        if msg == "invalid report_hash":
            node["category"] = "historical_record_hash_mismatch"
        elif msg.startswith("Bad CRC-32 for file"):
            node["category"] = "zip_crc32_mismatch"
        elif msg.startswith("could not read historical member:"):
            node["category"] = "wrapped_historical_member_read"
        elif msg == "historical archive digest mismatch":
            node["category"] = "compressed_archive_sha256_mismatch"
        elif msg.startswith("Error ") and type(current).__module__ == "zlib":
            node["category"] = "zlib_error"
        tb = current.__traceback__
        for _ in range(24):
            if tb is None:
                break
            frame = tb.tb_frame
            raw_path = Path(frame.f_code.co_filename)
            try:
                filename = raw_path.resolve().relative_to(stage).as_posix()
            except (ValueError, OSError):
                filename = "<runtime>/" + raw_path.name
            loc = {"file": filename, "function": frame.f_code.co_name,
                   "line": tb.tb_lineno}
            # zipfile's integrity state is numeric and contains no payload data.
            if raw_path.name == "__init__.py" and frame.f_globals.get("__name__") == "zipfile":
                info = frame.f_locals.get("self")
                crc = {}
                for attr in ("_running_crc", "_expected_crc", "_left", "_orig_file_size"):
                    value = getattr(info, attr, None)
                    if type(value) is int:
                        crc[attr] = value
                if crc:
                    loc["zip_integrity_numbers"] = crc
            node["locations"].append(loc)
            tb = tb.tb_next
        next_exc = current.__cause__ if current.__cause__ is not None else current.__context__
        node["next_relation"] = "cause" if current.__cause__ is not None else "context" if next_exc is not None else None
        nodes.append(node)
        current = next_exc
    return {"exception_chain": nodes, "raw_values_retained": False}


def source_pins(stage: Path) -> None:
    for rel, expected in REFERENCE["source_files"].items():
        path = stage / rel
        regular(path)
        require(sha(path.read_bytes()) == expected,
                "historical loader/canonical source differs: " + rel)


def archive_snapshot(stage: Path) -> dict:
    alt, name = alternate_backend()
    items = {}
    for label, ref in REFERENCE["archives"].items():
        path = stage / ref["path"]
        regular(path)
        require(path.stat().st_size <= 16 * 1024 * 1024, "archive exceeds diagnostic ingestion bound")
        data = path.read_bytes()
        obs = digest_observation(data, ref["sha256"], alt)
        obs["size_matches_reference"] = len(data) == ref["size"]
        obs["anomaly"] = obs["anomaly"] or not obs["size_matches_reference"]
        items[label] = obs
    return {"alternate_backend": name, "archives": items,
            "backend_self_test_failed": name.endswith(":known-answer-failed"),
            "anomaly": name.endswith(":known-answer-failed") or any(x["anomaly"] for x in items.values())}


def verify_suite_evidence(directory: Path, run: Path) -> dict:
    require(directory.is_dir() and directory.parent == run.parent and not directory.is_symlink(),
            "suite diagnostic must be an existing sibling run directory")
    report_path = directory / "diagnostic-report.json"
    regular(report_path)
    require(sha(report_path.read_bytes()) == SUITE_REPORT_SHA256,
            "ordered-suite report differs from the hash supplied by the owner")
    manifest = directory / "SHA256SUMS.txt"
    regular(manifest)
    listed = {}
    for line in manifest.read_text(encoding="ascii").splitlines():
        digest, name = line.split("  ", 1)
        relative(name)
        require("/" not in name and name not in listed and re.fullmatch("[0-9a-f]{64}", digest),
                "unsafe/duplicate suite diagnostic manifest entry")
        item = directory / name
        regular(item)
        require(sha(item.read_bytes()) == digest, "suite diagnostic evidence changed: " + name)
        listed[name] = digest
    require({p.name for p in directory.iterdir() if p.is_file() and p != manifest} == set(listed),
            "suite diagnostic file set differs")
    obj = json.loads(report_path.read_bytes())
    require(obj.get("schema") == "rcp-rclm.phase17c.ordered-suite-diagnostic.v1"
            and obj.get("source_commit") == FAILED_SOURCE
            and obj.get("original_checkout_unchanged") is True
            and obj.get("failed_checkout_unchanged") is True
            and obj.get("original_failure_resolved") is False,
            "ordered-suite source/boundary differs")
    suite = obj.get("suite") or {}
    require(suite.get("tests_run") == 18 and suite.get("errors") == 2
            and suite.get("failures") == 0 and suite.get("skipped") == 0
            and suite.get("suite_passed") is False,
            "expected the retained 18-test observation with two errors")
    return {"report_sha256": SUITE_REPORT_SHA256,
            "manifest_sha256": sha(manifest.read_bytes()),
            "source_commit": FAILED_SOURCE, "errors": 2}


def observe_bootstrap(stage: Path, out: Path, index: int) -> dict:
    """One production bootstrap call with observers; no challenge code imported."""
    source_pins(stage)
    sys.path[:0] = [str(stage / "python" / f"rcp_rclm_runtime_v{v}") for v in (2, 5)]
    import zlib
    from rcp_rclm_runtime.canonical import hashing
    from rcp_rclm_runtime_v5.phase17 import bootstrap as b

    alt, alt_name = alternate_backend()
    events = []
    context = [None]
    originals = (b._read_pinned_archive, b._member, b._bound, hashing.sha256_hex)
    event_path = out / f"observation-{index:02d}.events.jsonl"
    # The event file survives a subsequent crash/timeout.
    with event_path.open("x", encoding="utf-8", newline="\n") as stream:
        def record(event):
            if len(events) >= 4096:
                raise RuntimeError("diagnostic event bound exceeded")
            events.append(event)
            stream.write(json.dumps(event, sort_keys=True, allow_nan=False) + "\n")
            stream.flush()

        def archive_reader(path, digest, *, max_bytes=16 * 1024 * 1024):
            try:
                result = originals[0](path, digest, max_bytes=max_bytes)
            except Exception as exc:
                record({"event": "archive_open_exception", **safe_exception(exc, stage)})
                raise
            label = next((k for k, r in REFERENCE["archives"].items() if r["sha256"] == digest), "unknown")
            # The same immutable in-memory bytes already checked by production.
            obs = digest_observation(result.fp.getvalue(), digest, alt)
            record({"event": "compressed_archive", "archive": label, **obs})
            return result

        def member_reader(archive, name, limit):
            try:
                data = originals[1](archive, name, limit)
            except Exception as exc:
                record({"event": "member_read_exception", "member": name if name in REFERENCE["members"] else "<unlisted>",
                        **safe_exception(exc, stage)})
                raise
            ref = REFERENCE["members"].get(name)
            if ref is not None:
                obs = digest_observation(data, ref["sha256"], alt)
                obs["size_matches_reference"] = len(data) == ref["size"]
                obs["archive_header_crc32"] = archive.getinfo(name).CRC
                obs["reference_crc32"] = ref["crc32"]
                obs["anomaly"] |= not obs["size_matches_reference"] or obs["archive_header_crc32"] != ref["crc32"]
                record({"event": "decompressed_member", "member": name, **obs})
            return data

        def hash_observer(data):
            # Call the original exactly once and return that original result.
            actual = originals[3](data)
            ctx = context[0]
            if ctx is None:
                return actual
            wanted = ctx["observed"]
            ref = REFERENCE["records"].get(wanted)
            if ref is None and actual == wanted:
                return actual
            obs = digest_observation(data, wanted, alt)
            obs["production_hash_result"] = actual
            obs["anomaly"] |= actual != wanted or actual != obs["native_sha256_first"]
            body = data[len(hashing.CANONICAL_JSON_HASH_DOMAIN):]
            if ref is not None:
                canonical = digest_observation(body, ref["canonical_sha256"], alt)
                canonical["size_matches_reference"] = len(body) == ref["canonical_size"]
                canonical["anomaly"] |= not canonical["size_matches_reference"]
                obs["canonical_bytes"] = canonical
                obs["anomaly"] |= canonical["anomaly"]
            record({"event": "bound_record_hash", "record": ref["label"] if ref else "<unlisted-historical-record>",
                    "field": ctx["field"], **obs})
            return actual

        def bound_checker(record_value, field="report_hash"):
            prior = context[0]
            observed = record_value.get(field) if type(record_value) is dict else None
            context[0] = {"field": field, "observed": observed}
            try:
                return originals[2](record_value, field)
            except Exception as exc:
                record({"event": "bound_record_exception", **safe_exception(exc, stage)})
                raise
            finally:
                context[0] = prior

        start = datetime.now(timezone.utc).isoformat()
        status = {"observation": index, "bootstrap_passed": False,
                  "diagnostic_instrumentation": True, "production_source_modified": False,
                  "bootstrap_calls": 1, "automatic_retries": 0,
                  "challenge_generation_calls": 0, "started_at_utc": start,
                  "environment": {"os": platform.system(), "python_version": platform.python_version(),
                      "python_implementation": platform.python_implementation(),
                      "native_sha256_backend": type(hashlib.sha256()).__module__,
                      "alternate_sha256_backend": alt_name,
                      "zlib_compile_version": zlib.ZLIB_VERSION,
                      "zlib_runtime_version": zlib.ZLIB_RUNTIME_VERSION,
                      "isolated": bool(sys.flags.isolated), "no_site": bool(sys.flags.no_site)}}
        if alt_name.endswith(":known-answer-failed"):
            record({"event": "alternate_backend_known_answer_failed", "anomaly": True})
        b._read_pinned_archive, b._member, b._bound, hashing.sha256_hex = (
            archive_reader, member_reader, bound_checker, hash_observer)
        try:
            result = b.reopen_phase16(
                capture_archive=stage / REFERENCE["archives"]["capture"]["path"],
                closure_archive=stage / REFERENCE["archives"]["closure"]["path"],
                phase15_bundle=stage / REFERENCE["archives"]["m9"]["path"])
            status["bootstrap_passed"] = True
            status["receipt_hash"] = result.receipt["report_hash"]
        except Exception as exc:
            status["error"] = safe_exception(exc, stage)
        finally:
            b._read_pinned_archive, b._member, b._bound, hashing.sha256_hex = originals
        status["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
        status["anomalies"] = [e for e in events if e.get("anomaly") is True]
        status["event_count"] = len(events)
        status["claims"] = dict(CLAIMS)
        write_json(out / f"observation-{index:02d}.json", status)
        return status


def worker_environment() -> dict:
    allowed = {"SYSTEMROOT", "WINDIR", "SYSTEMDRIVE", "TEMP", "TMP", "LANG", "LC_ALL"}
    return {k: v for k, v in os.environ.items() if k.upper() in allowed}


def run_batch(stage: Path, out: Path) -> list[dict]:
    rows = []
    for index in range(1, OBSERVATIONS + 1):
        argv = [sys.executable, "-I", "-S", "-B", "-u", str(Path(__file__).resolve()),
                "--_probe", str(stage), "--_output", str(out), "--_index", str(index)]
        with (out / f"observation-{index:02d}.stdout.txt").open("xb") as so, (out / f"observation-{index:02d}.stderr.txt").open("xb") as se:
            try:
                result = subprocess.run(argv, cwd=out, env=worker_environment(),
                                        stdout=so, stderr=se, timeout=120)
                rc = result.returncode
            except subprocess.TimeoutExpired:
                rc = -999
        path = out / f"observation-{index:02d}.json"
        row = json.loads(path.read_bytes()) if path.is_file() else {
            "observation": index, "bootstrap_passed": False,
            "completion_report_missing": True, "anomalies": []}
        row["process_exit"] = rc
        rows.append(row)
        outcome = "PASS" if row["bootstrap_passed"] and not row["anomalies"] and rc == 0 else "ANOMALY/ERROR"
        print(f"Bootstrap observation {index}/{OBSERVATIONS}: {outcome}", flush=True)
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path)
    parser.add_argument("--kit", type=Path)
    parser.add_argument("--failed-run", type=Path)
    parser.add_argument("--suite-diagnostic", type=Path)
    parser.add_argument("--_probe", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--_output", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--_index", type=int, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    require(sys.version_info >= (3, 11), "Python 3.11 or later required")
    if args._probe is not None:
        require(args._output is not None and args._index in range(1, OBSERVATIONS + 1), "invalid child diagnostic arguments")
        status = observe_bootstrap(args._probe.resolve(), args._output.resolve(), args._index)
        return 0 if status["bootstrap_passed"] and not status["anomalies"] else 1
    require(all((args.repo, args.kit, args.failed_run, args.suite_diagnostic)),
            "--repo, --kit, --failed-run and --suite-diagnostic are required")
    repo, kit, run, suite = (p.resolve() for p in (args.repo, args.kit, args.failed_run, args.suite_diagnostic))
    stage, before_repo, before_stage = preflight(repo, kit, run)
    require(before_stage["head"] == FAILED_SOURCE, "failed source differs from the reported identity")
    source_pins(stage)
    prior = verify_suite_evidence(suite, run)
    failed_log = run / "evidence/command-logs/process-and-differential.stderr.txt"
    failed_hash = sha(failed_log.read_bytes())
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = kit / "runs" / ("bootstrap-integrity-" + stamp + "-" + uuid.uuid4().hex[:8])
    out.mkdir(exist_ok=False)
    print("Diagnostic output: " + str(out), flush=True)
    print("Twelve fixed bootstrap-only observations; no phase suites, live challenges, source changes or pushes.", flush=True)
    write_json(out / "reference.json", REFERENCE)
    inputs_before = archive_snapshot(stage)
    write_json(out / "inputs-before.json", inputs_before)
    if inputs_before["anomaly"]:
        report = {"schema": "rcp-rclm.phase17c.bootstrap-integrity-diagnostic.v1",
                  "stage": "preflight_archive_integrity_disagreement",
                  "source_commit": before_stage["head"], "observations_recorded": 0,
                  "inputs_before": inputs_before, "claims": dict(CLAIMS),
                  "original_checkout_unchanged": snapshot(repo) == before_repo,
                  "failed_checkout_unchanged": snapshot(stage) == before_stage}
        write_json(out / "diagnostic-report.json", report)
        listing = "".join(f"{sha(p.read_bytes())}  {p.name}\n" for p in sorted(out.iterdir()) if p.is_file())
        (out / "SHA256SUMS.txt").write_bytes(listing.encode("ascii"))
        print(json.dumps(report, indent=2))
        print("Archive integrity disagreement retained; no bootstrap workers started.")
        return 2
    start = datetime.now(timezone.utc).isoformat()
    rows = run_batch(stage, out)
    after_repo, after_stage = snapshot(repo), snapshot(stage)
    inputs_after = archive_snapshot(stage)
    # Verify immutable input evidence again, not just the source tree.
    prior_after = verify_suite_evidence(suite, run)
    unchanged = before_repo == after_repo and before_stage == after_stage
    preserved = prior_after == prior and sha(failed_log.read_bytes()) == failed_hash
    anomalies = sum(bool(r.get("anomalies")) for r in rows)
    errors = sum(r.get("bootstrap_passed") is not True or r["process_exit"] != 0 for r in rows)
    report = {"schema": "rcp-rclm.phase17c.bootstrap-integrity-diagnostic.v1",
              "started_at_utc": start, "finished_at_utc": datetime.now(timezone.utc).isoformat(),
              "source_commit": before_stage["head"], "source_tree": before_stage["tree"],
              "observations_planned": OBSERVATIONS, "observations_recorded": len(rows),
              "bootstrap_errors": errors, "observations_with_integrity_anomalies": anomalies,
              "all_observations_passed": errors == 0 and anomalies == 0,
              "original_checkout_unchanged": before_repo == after_repo,
              "failed_checkout_unchanged": before_stage == after_stage,
              "prior_evidence_preserved": preserved, "prior_suite_diagnostic": prior,
              "inputs_before": inputs_before, "inputs_after": inputs_after,
              "archive_observations_unchanged": inputs_before == inputs_after,
              "observations": rows, "claims": dict(CLAIMS),
              "interpretation": "A bounded instrumented observation of fixed historical bytes. Backend agreement is not hardware attestation. No run repairs or supersedes a previous failure or authorizes installation/push."}
    write_json(out / "diagnostic-report.json", report)
    listing = "".join(f"{sha(p.read_bytes())}  {p.name}\n" for p in sorted(out.iterdir()) if p.is_file())
    (out / "SHA256SUMS.txt").write_bytes(listing.encode("ascii"))
    print("\n===== BOOTSTRAP INTEGRITY SUMMARY =====")
    print(json.dumps({k: report[k] for k in ("bootstrap_errors", "observations_with_integrity_anomalies",
        "all_observations_passed", "original_checkout_unchanged", "failed_checkout_unchanged", "prior_evidence_preserved")}, indent=2))
    for row in rows:
        if row.get("error") or row.get("anomalies") or row["process_exit"] != 0:
            print("\n===== OBSERVATION " + str(row["observation"]) + " =====")
            print(json.dumps(row, indent=2))
    print("\nReport: " + str(out / "diagnostic-report.json"))
    print("Report SHA-256: " + sha((out / "diagnostic-report.json").read_bytes()))
    print("Diagnostic only. No repair, acceptance, source change, commit, reset, merge or push.")
    return 0 if unchanged and preserved and inputs_before == inputs_after and not inputs_after["anomaly"] else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        print("STOP: " + str(exc), file=sys.stderr)
        raise SystemExit(2)
