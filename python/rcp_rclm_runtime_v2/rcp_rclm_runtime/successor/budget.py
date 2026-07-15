from __future__ import annotations

from rcp_rclm_runtime.successor.records import Phase6ResourceBudgetRecord


def reference_phase6_budget() -> Phase6ResourceBudgetRecord:
    return Phase6ResourceBudgetRecord(
        max_file_count=64,
        max_total_bytes=1_048_576,
        max_changed_files=8,
        max_written_bytes=4_194_304,
        max_commands=16,
        max_snapshot_bytes=2_097_152,
    )


__all__ = ["reference_phase6_budget"]
