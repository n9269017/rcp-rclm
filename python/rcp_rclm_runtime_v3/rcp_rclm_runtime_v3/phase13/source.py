from __future__ import annotations

from pathlib import Path


def discover_repository_head(repo_root: Path) -> str:
    repo = repo_root.resolve(strict=True)
    marker = repo / ".git"
    git_root = marker
    if marker.is_file():
        value = marker.read_text(encoding="utf-8").strip()
        prefix = "gitdir: "
        if not value.startswith(prefix):
            raise ValueError("repository .git indirection is malformed")
        git_root = (repo / value[len(prefix) :]).resolve(strict=True)
    if not git_root.is_dir():
        raise ValueError("repository Git metadata is unavailable")
    head = (git_root / "HEAD").read_text(encoding="utf-8").strip()
    if head.startswith("ref: "):
        reference = head[5:]
        reference_path = git_root / reference
        if reference_path.is_file():
            head = reference_path.read_text(encoding="utf-8").strip()
        else:
            packed = git_root / "packed-refs"
            if not packed.is_file():
                raise ValueError(f"Git reference is unavailable: {reference}")
            matches = [
                line.split(" ", 1)[0]
                for line in packed.read_text(encoding="utf-8").splitlines()
                if line
                and not line.startswith(("#", "^"))
                and line.endswith(f" {reference}")
            ]
            if len(matches) != 1:
                raise ValueError(
                    f"Git reference is ambiguous or unavailable: {reference}"
                )
            head = matches[0]
    if len(head) != 40 or any(
        character not in "0123456789abcdef" for character in head
    ):
        raise ValueError(
            "repository HEAD is not a lowercase 40-character Git SHA"
        )
    return head


__all__ = ["discover_repository_head"]
