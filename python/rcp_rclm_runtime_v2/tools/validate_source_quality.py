from __future__ import annotations

import argparse
import ast
import json
import tokenize
from dataclasses import dataclass
from pathlib import Path
from collections.abc import Sequence
from typing import Final


BANNED_RUNTIME_IMPORT_ROOTS: Final[frozenset[str]] = frozenset(
    {"numpy", "random", "secrets", "torch"}
)
TORCH_BACKEND_RELATIVE_PATH: Final[tuple[str, str]] = ("torch_backend", "proposal_backend.py")


@dataclass(frozen=True, slots=True)
class QualityIssue:
    path: str
    line: int
    code: str
    detail: str

    def to_json(self) -> dict[str, object]:
        return {
            "path": self.path,
            "line": self.line,
            "code": self.code,
            "detail": self.detail,
        }


def python_files(root: Path) -> Sequence[Path]:
    return tuple(sorted(path for path in root.rglob("*.py") if "__pycache__" not in path.parts))


def evaluate_source_quality(package_root: Path) -> dict[str, object]:
    package_root = package_root.resolve(strict=True)
    runtime_root = package_root / "rcp_rclm_runtime"
    torch_backend_entry = runtime_root.joinpath(*TORCH_BACKEND_RELATIVE_PATH)
    issues: list[QualityIssue] = []
    paths = python_files(package_root)

    for path in paths:
        relative = path.relative_to(package_root).as_posix()
        text = path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(text, filename=relative)
        except SyntaxError as exc:
            issues.append(
                QualityIssue(
                    path=relative,
                    line=exc.lineno or 1,
                    code="PYTHON_SYNTAX_ERROR",
                    detail=exc.msg,
                )
            )
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Pass):
                issues.append(
                    QualityIssue(relative, node.lineno, "PYTHON_PASS_FORBIDDEN", "pass statement")
                )
            if isinstance(node, ast.Constant) and node.value is Ellipsis:
                issues.append(
                    QualityIssue(
                        relative,
                        node.lineno,
                        "PYTHON_ELLIPSIS_FORBIDDEN",
                        "ellipsis expression",
                    )
                )
            if path.is_relative_to(runtime_root):
                imported_roots: set[str] = set()
                if isinstance(node, ast.Import):
                    imported_roots.update(alias.name.split(".", 1)[0] for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module is not None:
                    imported_roots.add(node.module.split(".", 1)[0])
                for imported_root in sorted(imported_roots & BANNED_RUNTIME_IMPORT_ROOTS):
                    if imported_root == "torch" and path == torch_backend_entry:
                        continue
                    issues.append(
                        QualityIssue(
                            relative,
                            node.lineno,
                            "NONDETERMINISTIC_OR_FLOAT_BACKEND_IMPORT",
                            imported_root,
                        )
                    )

        with path.open("rb") as source:
            for token in tokenize.tokenize(source.readline):
                if token.type == tokenize.COMMENT and "TODO" in token.string.upper():
                    issues.append(
                        QualityIssue(
                            relative,
                            token.start[0],
                            "PYTHON_TODO_FORBIDDEN",
                            token.string.strip(),
                        )
                    )

    issues.sort(key=lambda issue: (issue.path, issue.line, issue.code, issue.detail))
    return {
        "schema_version": "rcp-rclm-runtime-phase-1-source-quality-v1",
        "package_root": package_root.name,
        "python_file_count": len(paths),
        "issues": [issue.to_json() for issue in issues],
        "ok": not issues,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-root", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    report = evaluate_source_quality(args.package_root)
    text = json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if report["ok"] is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
