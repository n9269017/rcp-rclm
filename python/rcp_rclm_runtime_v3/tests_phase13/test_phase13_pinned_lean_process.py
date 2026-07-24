from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime_v3.phase10.lean_process import (
    DEFAULT_PINNED_LEAN_TIMEOUT_SECONDS,
    run_pinned_lean_source,
)


class Phase13PinnedLeanProcessTests(unittest.TestCase):
    def test_resolves_platform_launcher_and_uses_bounded_timeout(self) -> None:
        source = b"import Mathlib\nexample : True := by trivial\n"
        with tempfile.TemporaryDirectory(prefix="rcp-rclm-phase13-lean-process-") as temporary:
            project = Path(temporary)
            observed: dict[str, object] = {}

            def completed_process(
                command: list[str],
                *,
                cwd: Path,
                capture_output: bool,
                check: bool,
                timeout: int,
            ) -> subprocess.CompletedProcess[bytes]:
                observed["command"] = command
                observed["cwd"] = cwd
                observed["capture_output"] = capture_output
                observed["check"] = check
                observed["timeout"] = timeout
                self.assertEqual(Path(command[3]).read_bytes(), source)
                return subprocess.CompletedProcess(command, 0, b"", b"")

            with (
                mock.patch(
                    "rcp_rclm_runtime_v3.phase10.lean_process.shutil.which",
                    return_value="C:/elan/bin/lake.exe",
                ),
                mock.patch(
                    "rcp_rclm_runtime_v3.phase10.lean_process.subprocess.run",
                    side_effect=completed_process,
                ),
            ):
                result = run_pinned_lean_source(
                    source,
                    project,
                    temporary_prefix="phase13-test-",
                    source_file_name="SelectedTask.lean",
                )

        self.assertEqual(result.returncode, 0)
        self.assertEqual(observed["command"][0], "C:/elan/bin/lake.exe")
        self.assertEqual(observed["timeout"], DEFAULT_PINNED_LEAN_TIMEOUT_SECONDS)
        self.assertEqual(observed["cwd"], project.resolve())
        self.assertTrue(observed["capture_output"])
        self.assertFalse(observed["check"])

    def test_missing_platform_launcher_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rcp-rclm-phase13-lean-missing-") as temporary:
            with mock.patch(
                "rcp_rclm_runtime_v3.phase10.lean_process.shutil.which",
                return_value=None,
            ):
                with self.assertRaisesRegex(
                    SchemaValidationError,
                    "pinned lake executable is unavailable",
                ):
                    run_pinned_lean_source(
                        b"example : True := by trivial\n",
                        Path(temporary),
                        temporary_prefix="phase13-test-",
                        source_file_name="SelectedTask.lean",
                    )

    def test_timeout_is_fail_visible_and_remains_bounded(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rcp-rclm-phase13-lean-timeout-") as temporary:
            with (
                mock.patch(
                    "rcp_rclm_runtime_v3.phase10.lean_process.shutil.which",
                    return_value="/opt/elan/bin/lake",
                ),
                mock.patch(
                    "rcp_rclm_runtime_v3.phase10.lean_process.subprocess.run",
                    side_effect=subprocess.TimeoutExpired(
                        cmd=("lake", "env", "lean"),
                        timeout=DEFAULT_PINNED_LEAN_TIMEOUT_SECONDS,
                    ),
                ),
            ):
                with self.assertRaisesRegex(
                    SchemaValidationError,
                    f"exceeded {DEFAULT_PINNED_LEAN_TIMEOUT_SECONDS} seconds",
                ):
                    run_pinned_lean_source(
                        b"example : True := by trivial\n",
                        Path(temporary),
                        temporary_prefix="phase13-test-",
                        source_file_name="SelectedTask.lean",
                    )


if __name__ == "__main__":
    unittest.main()
