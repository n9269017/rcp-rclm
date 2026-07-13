#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Final, Literal, Sequence, TypeAlias

CONTRACT_VERSION: Final[str] = "rcp-rclm-runtime-contract-v2.0.0"
MANIFEST_SCHEMA_VERSION: Final[str] = "rcp-rclm-runtime-contract-manifest-v1"
DEFAULT_MANIFEST: Final[Path] = Path(
    "python/rcp_rclm_executable_core_v2/contract/runtime_contract_manifest.json"
)
DEFAULT_SCHEMA: Final[Path] = Path(
    "python/rcp_rclm_executable_core_v2/contract/runtime_records.schema.json"
)
FORBIDDEN_LEAN_TOKEN: Final[re.Pattern[str]] = re.compile(
    r"(?<![A-Za-z0-9_])(sorryAx|sorry|admit)(?![A-Za-z0-9_])"
)
LOCAL_AXIOM_DECLARATION: Final[re.Pattern[str]] = re.compile(
    r"^[ \t]*axiom[ \t]+", re.MULTILINE
)
HEX_40: Final[re.Pattern[str]] = re.compile(r"^[0-9a-f]{40}$")
HEX_64: Final[re.Pattern[str]] = re.compile(r"^[0-9a-f]{64}$")
OBJECT_ID: Final[re.Pattern[str]] = re.compile(r"^[a-z0-9][a-z0-9_.-]*$")
SCHEMA_ID: Final[re.Pattern[str]] = re.compile(r"^[a-z0-9][a-z0-9_.-]*\.v2$")
PYTHON_SYMBOL: Final[re.Pattern[str]] = re.compile(
    r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)+$"
)
RUNTIME_FUNCTION: Final[re.Pattern[str]] = re.compile(r"^[a-z_][a-z0-9_]*$")

JsonScalar: TypeAlias = None | bool | int | float | str
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]
Severity: TypeAlias = Literal["error", "warning"]


@dataclass(frozen=True, slots=True)
class Issue:
    severity: Severity
    code: str
    path: str
    message: str


@dataclass(frozen=True, slots=True)
class ValidationReport:
    ok: bool
    contract_version: str
    manifest_path: str
    schema_path: str
    mapped_object_count: int
    scanned_lean_file_count: int
    issues: tuple[Issue, ...]


class DuplicateKeyError(ValueError):
    def __init__(self, key: str) -> None:
        super().__init__(f"duplicate JSON object key: {key}")
        self.key = key


def reject_duplicate_keys(pairs: list[tuple[str, JsonValue]]) -> dict[str, JsonValue]:
    result: dict[str, JsonValue] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(key)
        result[key] = value
    return result


def load_json_strict(path: Path) -> JsonValue:
    text = path.read_text(encoding="utf-8")
    return json.loads(text, object_pairs_hook=reject_duplicate_keys)


def canonical_json_bytes(value: JsonValue) -> bytes:
    text = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return text.encode("utf-8")


def git_blob_sha1(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def run_git(repo_root: Path, arguments: Sequence[str]) -> subprocess.CompletedProcess[str]:
    command = ["git", "-C", str(repo_root), *arguments]
    return subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def require_dict(
    value: JsonValue,
    path: str,
    issues: list[Issue],
) -> dict[str, JsonValue]:
    if isinstance(value, dict):
        return value
    issues.append(Issue("error", "TYPE_OBJECT_REQUIRED", path, "expected JSON object"))
    return {}


def require_list(
    value: JsonValue,
    path: str,
    issues: list[Issue],
) -> list[JsonValue]:
    if isinstance(value, list):
        return value
    issues.append(Issue("error", "TYPE_ARRAY_REQUIRED", path, "expected JSON array"))
    return []


def require_string_field(
    obj: dict[str, JsonValue],
    field: str,
    path: str,
    issues: list[Issue],
) -> str:
    value = obj.get(field)
    if isinstance(value, str) and value:
        return value
    issues.append(
        Issue("error", "STRING_FIELD_REQUIRED", f"{path}.{field}", "expected nonempty string")
    )
    return ""


def require_bool_field(
    obj: dict[str, JsonValue],
    field: str,
    path: str,
    issues: list[Issue],
) -> bool:
    value = obj.get(field)
    if isinstance(value, bool):
        return value
    issues.append(Issue("error", "BOOL_FIELD_REQUIRED", f"{path}.{field}", "expected bool"))
    return False


def validate_formal_source(
    repo_root: Path,
    formal_source: dict[str, JsonValue],
    issues: list[Issue],
) -> None:
    commit = require_string_field(formal_source, "commit", "formal_source", issues)
    if commit and not HEX_40.fullmatch(commit):
        issues.append(Issue("error", "FORMAL_COMMIT_FORMAT", "formal_source.commit", commit))
    if commit:
        exists = run_git(repo_root, ["cat-file", "-e", f"{commit}^{{commit}}"])
        if exists.returncode != 0:
            issues.append(
                Issue("error", "FORMAL_COMMIT_MISSING", "formal_source.commit", exists.stderr.strip())
            )
        ancestor = run_git(repo_root, ["merge-base", "--is-ancestor", commit, "HEAD"])
        if ancestor.returncode != 0:
            issues.append(
                Issue(
                    "error",
                    "FORMAL_COMMIT_NOT_ANCESTOR",
                    "formal_source.commit",
                    "pinned formal source is not an ancestor of HEAD",
                )
            )

    manifest_path_text = require_string_field(
        formal_source, "formal_manifest_path", "formal_source", issues
    )
    expected_blob = require_string_field(
        formal_source, "formal_manifest_git_blob_sha", "formal_source", issues
    )
    if expected_blob and not HEX_40.fullmatch(expected_blob):
        issues.append(
            Issue("error", "FORMAL_MANIFEST_BLOB_FORMAT", "formal_source.formal_manifest_git_blob_sha", expected_blob)
        )
    if manifest_path_text:
        manifest_path = repo_root / manifest_path_text
        if not manifest_path.is_file():
            issues.append(
                Issue("error", "FORMAL_MANIFEST_MISSING", manifest_path_text, "file does not exist")
            )
        else:
            actual_blob = git_blob_sha1(manifest_path.read_bytes())
            if expected_blob and actual_blob != expected_blob:
                issues.append(
                    Issue(
                        "error",
                        "FORMAL_MANIFEST_BLOB_MISMATCH",
                        manifest_path_text,
                        f"expected {expected_blob}, found {actual_blob}",
                    )
                )

    expected_toolchain = "leanprover/lean4:v4.31.0"
    toolchain = require_string_field(formal_source, "lean_toolchain", "formal_source", issues)
    if toolchain and toolchain != expected_toolchain:
        issues.append(
            Issue("error", "LEAN_TOOLCHAIN_MISMATCH", "formal_source.lean_toolchain", toolchain)
        )

    expected_mathlib = "fabf563a7c95a166b8d7b6efca11c8b4dc9d911f"
    mathlib = require_string_field(formal_source, "mathlib_commit", "formal_source", issues)
    if mathlib and mathlib != expected_mathlib:
        issues.append(
            Issue("error", "MATHLIB_COMMIT_MISMATCH", "formal_source.mathlib_commit", mathlib)
        )

    artifact_sha = require_string_field(
        formal_source, "validation_artifact_sha256", "formal_source", issues
    )
    if artifact_sha and not HEX_64.fullmatch(artifact_sha):
        issues.append(
            Issue("error", "AUDIT_ARTIFACT_SHA_FORMAT", "formal_source.validation_artifact_sha256", artifact_sha)
        )


def validate_object_correspondence(
    repo_root: Path,
    entries: list[JsonValue],
    issues: list[Issue],
) -> int:
    seen_ids: set[str] = set()
    seen_tests: set[str] = set()
    required_fields = (
        "id",
        "gate",
        "lean_path",
        "lean_git_blob_sha",
        "lean_declaration",
        "schema_id",
        "python_type",
        "runtime_function",
        "certificate_evidence",
        "conformance_test",
        "implementation_status",
    )
    valid_count = 0

    for index, raw_entry in enumerate(entries):
        path = f"object_correspondence[{index}]"
        entry = require_dict(raw_entry, path, issues)
        values = {
            field: require_string_field(entry, field, path, issues)
            for field in required_fields
        }
        object_id = values["id"]
        if object_id:
            if not OBJECT_ID.fullmatch(object_id):
                issues.append(Issue("error", "OBJECT_ID_FORMAT", f"{path}.id", object_id))
            if object_id in seen_ids:
                issues.append(Issue("error", "OBJECT_ID_DUPLICATE", f"{path}.id", object_id))
            seen_ids.add(object_id)

        schema_id = values["schema_id"]
        if schema_id and not SCHEMA_ID.fullmatch(schema_id):
            issues.append(Issue("error", "SCHEMA_ID_FORMAT", f"{path}.schema_id", schema_id))

        python_type = values["python_type"]
        if python_type and not PYTHON_SYMBOL.fullmatch(python_type):
            issues.append(Issue("error", "PYTHON_TYPE_FORMAT", f"{path}.python_type", python_type))

        runtime_function = values["runtime_function"]
        if runtime_function and not RUNTIME_FUNCTION.fullmatch(runtime_function):
            issues.append(
                Issue("error", "RUNTIME_FUNCTION_FORMAT", f"{path}.runtime_function", runtime_function)
            )

        conformance_test = values["conformance_test"]
        if conformance_test:
            if conformance_test in seen_tests:
                issues.append(
                    Issue("error", "CONFORMANCE_TEST_DUPLICATE", f"{path}.conformance_test", conformance_test)
                )
            seen_tests.add(conformance_test)

        if values["implementation_status"] != "reserved_contract_surface":
            issues.append(
                Issue(
                    "error",
                    "IMPLEMENTATION_STATUS_INVALID",
                    f"{path}.implementation_status",
                    values["implementation_status"],
                )
            )

        lean_path_text = values["lean_path"]
        lean_path = repo_root / lean_path_text
        if not lean_path.is_file():
            issues.append(Issue("error", "LEAN_SOURCE_MISSING", lean_path_text, "file does not exist"))
            continue

        data = lean_path.read_bytes()
        actual_blob = git_blob_sha1(data)
        expected_blob = values["lean_git_blob_sha"]
        if not HEX_40.fullmatch(expected_blob):
            issues.append(Issue("error", "LEAN_BLOB_FORMAT", f"{path}.lean_git_blob_sha", expected_blob))
        elif actual_blob != expected_blob:
            issues.append(
                Issue(
                    "error",
                    "LEAN_BLOB_MISMATCH",
                    lean_path_text,
                    f"expected {expected_blob}, found {actual_blob}",
                )
            )

        source = data.decode("utf-8")
        declaration = values["lean_declaration"]
        if declaration not in source:
            issues.append(
                Issue(
                    "error",
                    "LEAN_DECLARATION_MISSING",
                    lean_path_text,
                    declaration,
                )
            )
        else:
            valid_count += 1

    if valid_count < 20:
        issues.append(
            Issue(
                "error",
                "OBJECT_SURFACE_TOO_SMALL",
                "object_correspondence",
                f"expected at least 20 valid mappings, found {valid_count}",
            )
        )
    return valid_count


def validate_documents(
    repo_root: Path,
    documents: list[JsonValue],
    issues: list[Issue],
) -> None:
    seen: set[str] = set()
    for index, value in enumerate(documents):
        path = f"documents[{index}]"
        if not isinstance(value, str) or not value:
            issues.append(Issue("error", "DOCUMENT_PATH_INVALID", path, "expected nonempty string"))
            continue
        if value in seen:
            issues.append(Issue("error", "DOCUMENT_PATH_DUPLICATE", path, value))
        seen.add(value)
        document_path = repo_root / value
        if not document_path.is_file():
            issues.append(Issue("error", "DOCUMENT_MISSING", value, "file does not exist"))


def validate_contract_invariants(
    manifest: dict[str, JsonValue],
    issues: list[Issue],
) -> None:
    if manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        issues.append(
            Issue(
                "error",
                "MANIFEST_SCHEMA_VERSION",
                "schema_version",
                str(manifest.get("schema_version")),
            )
        )
    if manifest.get("contract_version") != CONTRACT_VERSION:
        issues.append(
            Issue(
                "error",
                "CONTRACT_VERSION",
                "contract_version",
                str(manifest.get("contract_version")),
            )
        )

    trust = require_dict(manifest.get("trust_boundary"), "trust_boundary", issues)
    if require_bool_field(trust, "generator_may_certify_itself", "trust_boundary", issues):
        issues.append(
            Issue(
                "error",
                "GENERATOR_SELF_CERTIFICATION",
                "trust_boundary.generator_may_certify_itself",
                "must be false",
            )
        )
    if require_bool_field(trust, "manual_override_to_accept", "trust_boundary", issues):
        issues.append(
            Issue(
                "error",
                "MANUAL_ACCEPT_OVERRIDE",
                "trust_boundary.manual_override_to_accept",
                "must be false",
            )
        )

    numeric = require_dict(manifest.get("numerical_semantics"), "numerical_semantics", issues)
    if numeric.get("boundary_overlap_result") != "indeterminate":
        issues.append(
            Issue(
                "error",
                "BOUNDARY_OVERLAP_POLICY",
                "numerical_semantics.boundary_overlap_result",
                "must be indeterminate",
            )
        )
    if numeric.get("nan_allowed") is not False or numeric.get("infinity_allowed") is not False:
        issues.append(
            Issue(
                "error",
                "NONFINITE_NUMBERS_ALLOWED",
                "numerical_semantics",
                "NaN and infinity must be forbidden",
            )
        )

    acceptance = require_dict(manifest.get("acceptance"), "acceptance", issues)
    if acceptance.get("promotable_verdict") != "accept":
        issues.append(
            Issue(
                "error",
                "PROMOTABLE_VERDICT",
                "acceptance.promotable_verdict",
                "only accept may be promotable",
            )
        )
    if acceptance.get("fail_closed") is not True:
        issues.append(Issue("error", "FAIL_CLOSED_REQUIRED", "acceptance.fail_closed", "must be true"))
    if acceptance.get("lean_bridge_required_initially") is not True:
        issues.append(
            Issue(
                "error",
                "LEAN_BRIDGE_REQUIRED",
                "acceptance.lean_bridge_required_initially",
                "must be true",
            )
        )

    licenses = require_dict(manifest.get("licenses"), "licenses", issues)
    forbidden_licenses = (
        "production_runtime_records",
        "production_mathematical_engine",
        "production_checker",
        "generator",
        "promotion_controller",
        "pytorch_backend",
        "benchmark_adapter",
    )
    for field in forbidden_licenses:
        if licenses.get(field) is not False:
            issues.append(
                Issue("error", "PREMATURE_LICENSE", f"licenses.{field}", "must remain false in Phase 0")
            )


def scan_lean_source(path: Path, reject_local_axiom: bool) -> tuple[Issue, ...]:
    issues: list[Issue] = []
    text = path.read_text(encoding="utf-8")
    for match in FORBIDDEN_LEAN_TOKEN.finditer(text):
        line = text.count("\n", 0, match.start()) + 1
        column = match.start() - text.rfind("\n", 0, match.start())
        issues.append(
            Issue(
                "error",
                "LEAN_FORBIDDEN_TOKEN",
                str(path),
                f"{match.group(1)} at line {line}, column {column}",
            )
        )
    if reject_local_axiom:
        for match in LOCAL_AXIOM_DECLARATION.finditer(text):
            line = text.count("\n", 0, match.start()) + 1
            issues.append(
                Issue(
                    "error",
                    "LEAN_LOCAL_AXIOM",
                    str(path),
                    f"axiom declaration at line {line}",
                )
            )
    return tuple(issues)


def validate_schema(schema: JsonValue, issues: list[Issue]) -> None:
    root = require_dict(schema, "runtime_records.schema", issues)
    if root.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
        issues.append(
            Issue(
                "error",
                "JSON_SCHEMA_DRAFT",
                "runtime_records.schema.$schema",
                str(root.get("$schema")),
            )
        )
    definitions = require_dict(root.get("$defs"), "runtime_records.schema.$defs", issues)
    required_definitions = {
        "rational",
        "interval",
        "distribution",
        "diagonalDensity",
        "selectedChannel",
        "candidate",
        "rclmState",
        "rclmUpdate",
        "rclmCertificatePacket",
        "packageManifest",
        "checkVerdict",
        "leanVerifierReport",
    }
    missing = sorted(required_definitions.difference(definitions))
    if missing:
        issues.append(
            Issue(
                "error",
                "SCHEMA_DEFINITIONS_MISSING",
                "runtime_records.schema.$defs",
                ", ".join(missing),
            )
        )


def validate(
    repo_root: Path,
    manifest_path: Path,
    schema_path: Path,
    lean_scan_paths: Sequence[Path],
) -> ValidationReport:
    issues: list[Issue] = []

    try:
        manifest_value = load_json_strict(manifest_path)
    except (OSError, UnicodeError, json.JSONDecodeError, DuplicateKeyError) as exc:
        issues.append(Issue("error", "MANIFEST_PARSE_FAILED", str(manifest_path), str(exc)))
        manifest_value = {}

    try:
        schema_value = load_json_strict(schema_path)
    except (OSError, UnicodeError, json.JSONDecodeError, DuplicateKeyError) as exc:
        issues.append(Issue("error", "SCHEMA_PARSE_FAILED", str(schema_path), str(exc)))
        schema_value = {}

    manifest = require_dict(manifest_value, "manifest", issues)
    validate_contract_invariants(manifest, issues)
    formal_source = require_dict(manifest.get("formal_source"), "formal_source", issues)
    validate_formal_source(repo_root, formal_source, issues)

    correspondence = require_list(
        manifest.get("object_correspondence"), "object_correspondence", issues
    )
    mapped_count = validate_object_correspondence(repo_root, correspondence, issues)

    documents = require_list(manifest.get("documents"), "documents", issues)
    validate_documents(repo_root, documents, issues)
    validate_schema(schema_value, issues)

    anti_placeholder = require_dict(
        manifest.get("anti_placeholder_gate"), "anti_placeholder_gate", issues
    )
    reject_local_axiom = anti_placeholder.get("forbid_local_axiom_in_generated_source") is True
    for scan_path in lean_scan_paths:
        if not scan_path.is_file():
            issues.append(Issue("error", "LEAN_SCAN_FILE_MISSING", str(scan_path), "file does not exist"))
        else:
            issues.extend(scan_lean_source(scan_path, reject_local_axiom))

    error_count = sum(issue.severity == "error" for issue in issues)
    return ValidationReport(
        ok=error_count == 0,
        contract_version=str(manifest.get("contract_version", "")),
        manifest_path=str(manifest_path),
        schema_path=str(schema_path),
        mapped_object_count=mapped_count,
        scanned_lean_file_count=len(lean_scan_paths),
        issues=tuple(issues),
    )


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate the frozen RCP/RCLM Executable Core v2 Phase 0 contract."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="Repository root. Defaults to the current working directory.",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help="Contract manifest path relative to repo root unless absolute.",
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=DEFAULT_SCHEMA,
        help="Runtime-record schema path relative to repo root unless absolute.",
    )
    parser.add_argument(
        "--scan-lean",
        type=Path,
        action="append",
        default=[],
        help="Generated Lean file to scan before compilation. May be repeated.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        help="Optional JSON report path. The report is also printed to stdout.",
    )
    return parser


def resolve_under_root(repo_root: Path, path: Path) -> Path:
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


def report_to_json(report: ValidationReport) -> str:
    value = asdict(report)
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_argument_parser()
    args = parser.parse_args(argv)
    repo_root = args.repo_root.resolve()
    manifest_path = resolve_under_root(repo_root, args.manifest)
    schema_path = resolve_under_root(repo_root, args.schema)
    scan_paths = tuple(resolve_under_root(repo_root, path) for path in args.scan_lean)

    report = validate(repo_root, manifest_path, schema_path, scan_paths)
    output = report_to_json(report)
    sys.stdout.write(output)

    if args.out is not None:
        output_path = resolve_under_root(repo_root, args.out)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output, encoding="utf-8", newline="\n")

    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
