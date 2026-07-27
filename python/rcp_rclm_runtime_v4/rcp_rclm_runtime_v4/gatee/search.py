from __future__ import annotations

from collections.abc import Sequence

from rcp_rclm_runtime_v4.gatee.records import AttemptRecord


def select_first_accepted(attempts: Sequence[AttemptRecord]) -> AttemptRecord | None:
    """Return the first independently accepted attempt in canonical enumeration order."""

    for attempt in attempts:
        if attempt.evaluator_accepted:
            return attempt
    return None


def all_attempts_rejected(attempts: Sequence[AttemptRecord]) -> bool:
    return all(not attempt.evaluator_accepted for attempt in attempts)
