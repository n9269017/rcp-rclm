from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from collections.abc import Sequence
from pathlib import Path
from unittest.mock import patch

from rcp_rclm_runtime._version import LEAN_TOOLCHAIN, MATHLIB_COMMIT
from rcp_rclm_runtime.lean_bridge.compiler import (
    LeanCompiler,
    LeanCompilerBridgeError,
    PinnedLeanProject,
)


class LeanCompilerTests(unittest.TestCase):
    def test_project_pin_discovery_is_exact(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            project = repo / "lean" / "rcp_rclm_formal_core_v2"
            project.mkdir(parents=True)
            (project / "lean-toolchain").write_text(LEAN_TOOLCHAIN + "\n", encoding="utf-8")
            (project / "lakefile.toml").write_text('name = "test"\n', encoding="utf-8")
            (project / "lake-manifest.json").write_text(
                json.dumps(
                    {
                        "packages": [
                            {
                                "name": "mathlib",
                                "rev": MATHLIB_COMMIT,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            pin = PinnedLeanProject.discover(repo, verify_git_pin=False)
            self.assertEqual(pin.toolchain, LEAN_TOOLCHAIN)
            self.assertEqual(pin.mathlib_commit, MATHLIB_COMMIT)
            self.assertEqual(len(pin.pin_hash), 64)
            self.assertEqual(len(pin.formal_source_tree), 64)

    def test_compiler_records_identity_and_output_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            project = _project_record(root)
            compiler = LeanCompiler(project, lake_command="lake", timeout_seconds=30)

            def fake_run(
                command: Sequence[str],
                **kwargs: object,
            ) -> subprocess.CompletedProcess[bytes]:
                command_tuple = tuple(command)
                if command_tuple[-2:] == ("lean", "--version"):
                    return subprocess.CompletedProcess(
                        command,
                        0,
                        b"Lean (version 4.31.0, test)\n",
                        b"",
                    )
                if command_tuple[-1:] == ("--version",):
                    return subprocess.CompletedProcess(
                        command,
                        0,
                        b"Lake version 5.0.0 (Lean version 4.31.0)\n",
                        b"",
                    )
                if command_tuple[-2:] == ("lean", "--print-prefix"):
                    return subprocess.CompletedProcess(command, 0, b"/lean/prefix\n", b"")
                return subprocess.CompletedProcess(command, 0, b"compiled\n", b"")

            with patch(
                "rcp_rclm_runtime.lean_bridge.compiler.subprocess.run",
                side_effect=fake_run,
            ):
                result = compiler.compile_source(
                    b"def bridgeValue : Nat := 1\n",
                    source_name="generated/test.lean",
                )
            self.assertTrue(result.succeeded)
            self.assertEqual(result.exit_code, 0)
            self.assertEqual(result.project_pin_hash, "5" * 64)
            self.assertEqual(result.source_name, "generated/test.lean")
            self.assertEqual(len(result.stdout_hash), 64)
            self.assertIn("version 4.31.0", result.toolchain_identity.lean_version)
            self.assertEqual(result.toolchain_identity.lean_prefix, "/lean/prefix")

    def test_native_elan_launcher_is_used_when_path_lookup_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            elan_home = root / "elan-home"
            launcher = elan_home / "bin" / "lake.exe"
            launcher.parent.mkdir(parents=True)
            launcher.write_bytes(b"native Elan Lake launcher fixture")
            environment = {
                "ELAN_HOME": str(elan_home.resolve()),
                "PATH": "/c/Users/runneradmin/.elan/bin",
            }
            with patch(
                "rcp_rclm_runtime.lean_bridge.compiler.shutil.which",
                return_value=None,
            ) as which_mock:
                compiler = LeanCompiler(
                    _project_record(root),
                    timeout_seconds=30,
                    environment=environment,
                )
            self.assertTrue(Path(compiler._lake_command).samefile(launcher))
            which_mock.assert_called_once_with(
                "lake",
                path=environment["PATH"],
            )

    def test_relative_elan_home_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            with patch(
                "rcp_rclm_runtime.lean_bridge.compiler.shutil.which",
                return_value=None,
            ):
                with self.assertRaises(LeanCompilerBridgeError) as captured:
                    LeanCompiler(
                        _project_record(root),
                        timeout_seconds=30,
                        environment={
                            "ELAN_HOME": "relative/elan",
                            "PATH": "",
                        },
                    )
            self.assertEqual(captured.exception.code, "ELAN_HOME_INVALID")
            self.assertEqual(captured.exception.path, "ELAN_HOME")

    def test_missing_path_and_native_elan_launcher_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            with patch(
                "rcp_rclm_runtime.lean_bridge.compiler.shutil.which",
                return_value=None,
            ):
                with self.assertRaises(LeanCompilerBridgeError) as captured:
                    LeanCompiler(
                        _project_record(root),
                        timeout_seconds=30,
                        environment={
                            "ELAN_HOME": str((root / "missing-elan").resolve()),
                            "PATH": "",
                        },
                    )
            self.assertEqual(captured.exception.code, "LAKE_NOT_FOUND")
            self.assertIn("native Elan home", captured.exception.detail)

    def test_forbidden_source_is_rejected_before_subprocess(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            compiler = LeanCompiler(
                _project_record(root),
                lake_command="lake",
                timeout_seconds=30,
            )
            with patch("rcp_rclm_runtime.lean_bridge.compiler.subprocess.run") as run_mock:
                with self.assertRaises(LeanCompilerBridgeError) as captured:
                    compiler.compile_source(
                        b"theorem bad : True := by sorry\n",
                        source_name="generated/rejected.lean",
                    )
            self.assertEqual(captured.exception.code, "LEAN_SOURCE_GUARD_REJECTED")
            self.assertEqual(captured.exception.path, "generated/rejected.lean")
            run_mock.assert_not_called()


def _project_record(root: Path) -> PinnedLeanProject:
    return PinnedLeanProject(
        repository_root=root,
        root=root,
        toolchain=LEAN_TOOLCHAIN,
        mathlib_commit=MATHLIB_COMMIT,
        formal_source_commit="0" * 40,
        formal_source_tree="0" * 40,
        toolchain_file_hash="1" * 64,
        manifest_hash="2" * 64,
        lakefile_hash="3" * 64,
        theorem_surface_hash="4" * 64,
        pin_hash="5" * 64,
    )


if __name__ == "__main__":
    unittest.main()
