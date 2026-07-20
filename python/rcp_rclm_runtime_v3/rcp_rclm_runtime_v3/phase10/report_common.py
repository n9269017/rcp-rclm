from __future__ import annotations

from collections.abc import Sequence


def ordered_reason_codes(values: Sequence[str]) -> Sequence[str]:
    return tuple(sorted(set(values), key=lambda item: item.encode("utf-8")))


__all__ = ["ordered_reason_codes"]
