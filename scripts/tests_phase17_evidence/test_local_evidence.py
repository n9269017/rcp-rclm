"""Recorder tests use temporary fixture repositories, never claim Phase 17 results."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("local_evidence", SCRIPTS / "phase17_local_evidence.py")
assert spec is not None and spec.loader is not None
evidence = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evidence)


class LocalEvidenceTests(unittest.TestCase):
    def setUp(self):
        # Package enumeration is environment metadata, not the behavior under test.
        patcher = mock.patch.object(evidence.importlib.metadata, "distributions", return_value=())
        patcher.start()
        self.addCleanup(patcher.stop)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.root = self.home / "checkout"
        self.root.mkdir()
        self.git("init", "-q")
        (self.root / ".gitignore").write_text("__pycache__/\n*.pyc\n", encoding="utf-8")
        (self.root / "scripts").mkdir()
        for name in ("phase17_local_evidence.py", "phase17_refresh_checksums.py"):
            shutil.copyfile(SCRIPTS / name, self.root / "scripts" / name)
        (self.root / "python/rcp_rclm_runtime_v5").mkdir(parents=True)
        (self.root / "python/rcp_rclm_runtime_v5/fixture.py").write_text("VALUE = 1\n", encoding="utf-8")
        self.write_tests()
        self.commit()
        self.output = self.home / "evidence"

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.root), *args], stderr=subprocess.PIPE)

    def write_tests(self, count=33, skipped=False):
        code = (
            "# Synthetic recorder-test fixture; not RCP/RCLM foundation evidence.\n"
            "import unittest\n"
            "class Fixture(unittest.TestCase):\n    pass\n"
            "def check(self):\n    self.assertTrue(True)\n"
            + ("check = unittest.skip('fixture skip')(check)\n" if skipped else "")
            + f"for i in range({count}):\n    setattr(Fixture, f'test_{{i:02}}', check)\n"
            "unittest.main(verbosity=2)\n"
        )
        (self.root / "scripts/run_phase17_tests.py").write_text(code, encoding="utf-8")

    def commit(self):
        self.git("add", "-A")
        subprocess.check_output([sys.executable, str(self.root / "scripts/phase17_refresh_checksums.py"), "--write"])
        self.git("add", "SHA256SUMS.txt")
        self.git("-c", "user.name=Evidence Test", "-c", "user.email=fixture@example.invalid",
                 "commit", "-qm", "test fixture")
        self.head = self.git("rev-parse", "HEAD").decode().strip()

    def anchor(self):
        return evidence._sha((self.output / "SHA256SUMS.txt").read_bytes())

    def capture(self, **kwargs):
        return evidence.capture(self.root, self.output, self.head, **kwargs)

    def verify(self):
        return evidence.verify(self.output, self.head, self.anchor())

    def rehash(self):
        files = sorted(p for p in self.output.rglob("*") if p.is_file() and p.name != "SHA256SUMS.txt")
        content = "".join(f"{evidence._sha(p.read_bytes())}  {p.relative_to(self.output).as_posix()}\n" for p in files)
        (self.output / "SHA256SUMS.txt").write_text(content, encoding="utf-8", newline="\n")

    def rewrite(self, change):
        p = self.output / "evidence.json"
        report = json.loads(p.read_text(encoding="utf-8"))
        change(report)
        p.write_bytes(evidence._json_bytes(report))
        self.rehash()

    def test_capture_verify_round_trip_and_no_closure(self):
        result = self.capture()
        self.assertTrue(result["local_checks_passed"])
        self.assertEqual(result["commands"][1]["test_summary"]["tests_run"], 33)
        self.assertTrue(self.verify()["local_checks_passed"])
        self.assertTrue(all(v is False for v in result["claims"].values()))
        self.assertEqual(result["source"]["tree"], self.git("rev-parse", "HEAD^{tree}").decode().strip())

    def test_wrong_expected_head_rejected_before_creation(self):
        with self.assertRaisesRegex(ValueError, "expected HEAD"):
            evidence.capture(self.root, self.output, "0" * 40)
        self.assertFalse(self.output.exists())

    def test_output_inside_checkout_rejected(self):
        with self.assertRaisesRegex(ValueError, "outside"):
            evidence.capture(self.root, self.root / "evidence", self.head)

    def test_dirty_checkout_rejected(self):
        (self.root / "untracked.txt").write_text("uncommitted", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "clean checkout"):
            self.capture()

    def test_existing_output_not_overwritten(self):
        self.output.mkdir()
        marker = self.output / "keep.txt"
        marker.write_text("keep", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            self.capture()
        self.assertEqual(marker.read_text(), "keep")

    def test_compile_failure_stops_remaining_commands(self):
        (self.root / "python/rcp_rclm_runtime_v5/fixture.py").write_text("invalid python!\n", encoding="utf-8")
        self.commit()
        result = self.capture()
        self.assertEqual([c["status"] for c in result["commands"]], ["failed", "not_run", "not_run"])
        self.assertFalse(self.verify()["local_checks_passed"])

    def test_too_few_tests_do_not_pass(self):
        self.write_tests(count=1)
        self.commit()
        result = self.capture()
        self.assertFalse(result["local_checks_passed"])
        self.assertEqual(result["commands"][2]["status"], "not_run")
        self.assertFalse(self.verify()["local_checks_passed"])

    def test_skipped_tests_do_not_pass(self):
        self.write_tests(skipped=True)
        self.commit()
        self.assertFalse(self.capture()["local_checks_passed"])
        self.assertFalse(self.verify()["local_checks_passed"])

    def test_timeout_retained_not_success(self):
        p = self.root / "scripts/run_phase17_tests.py"
        p.write_text("import time\ntime.sleep(3)\n", encoding="utf-8")
        self.commit()
        result = self.capture(timeout=1)
        self.assertEqual(result["commands"][1]["status"], "timed_out")
        self.assertFalse(self.verify()["local_checks_passed"])

    def test_log_tampering_rejected(self):
        self.capture()
        (self.output / "logs/foundation-tests.stderr.txt").write_text("replacement", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "checksum"):
            self.verify()

    def test_rehashed_bundle_rejected_against_prior_anchor(self):
        self.capture()
        old = self.anchor()
        self.rewrite(lambda r: r["environment"].update(os="fictional OS"))
        with self.assertRaisesRegex(ValueError, "anchor"):
            evidence.verify(self.output, self.head, old)

    def test_caller_cannot_replace_expected_source(self):
        self.capture()
        self.rewrite(lambda r: r["source"].update(commit="0" * 40))
        with self.assertRaisesRegex(ValueError, "source binding"):
            self.verify()

    def test_rehashed_closure_claim_rejected(self):
        self.capture()
        self.rewrite(lambda r: r["claims"].update(gate_e_closed=True))
        with self.assertRaisesRegex(ValueError, "closure claim"):
            self.verify()

    def test_rehashed_omitted_command_rejected(self):
        self.capture()
        self.rewrite(lambda r: r["commands"].pop())
        with self.assertRaisesRegex(ValueError, "command omitted"):
            self.verify()

    def test_rehashed_command_substitution_rejected(self):
        self.capture()
        self.rewrite(lambda r: r["commands"][1].update(argv=["python", "replacement.py"]))
        with self.assertRaisesRegex(ValueError, "command profile"):
            self.verify()

    def test_rehashed_false_exit_code_rejected(self):
        self.capture()
        self.rewrite(lambda r: r["commands"][0].update(returncode=False))
        with self.assertRaisesRegex(ValueError, "integer"):
            self.verify()

    def test_rehashed_forged_test_count_rejected(self):
        self.capture()
        self.rewrite(lambda r: r["commands"][1]["test_summary"].update(tests_run=999))
        with self.assertRaisesRegex(ValueError, "test summary"):
            self.verify()

    def test_duplicate_json_key_rejected(self):
        self.capture()
        p = self.output / "evidence.json"
        data = p.read_text(encoding="utf-8").replace('{\n', '{\n  "profile": "duplicate",\n', 1)
        p.write_text(data, encoding="utf-8")
        self.rehash()
        with self.assertRaisesRegex(ValueError, "duplicate JSON"):
            self.verify()

    def test_extra_file_rejected_even_if_rehashed(self):
        self.capture()
        (self.output / "extra.txt").write_text("unlisted extra", encoding="utf-8")
        self.rehash()
        with self.assertRaisesRegex(ValueError, "membership"):
            self.verify()

    def test_manifest_traversal_rejected(self):
        self.capture()
        p = self.output / "SHA256SUMS.txt"
        p.write_bytes(p.read_bytes() + ("0" * 64 + "  ../outside.txt\n").encode())
        with self.assertRaisesRegex(ValueError, "unsafe"):
            self.verify()

    def test_unsupported_float_in_report_rejected(self):
        self.capture()
        self.rewrite(lambda r: r["commands"][0].update(duration_ms=0.5))
        with self.assertRaisesRegex(ValueError, "floating-point"):
            self.verify()

    def test_unknown_report_field_rejected(self):
        self.capture()
        self.rewrite(lambda r: r.update(allow_promotion=True))
        with self.assertRaisesRegex(ValueError, "unknown or missing"):
            self.verify()


if __name__ == "__main__":
    unittest.main(verbosity=2)
