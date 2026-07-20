from __future__ import annotations

import subprocess
from pathlib import Path

BRANCH = "agent/rcp-rclm-v3-phase-10-substrate"


def run(*args: str) -> str:
    completed = subprocess.run(args, check=True, text=True, capture_output=True)
    return completed.stdout.strip()


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"expected one {label} replacement, found {count}")
    return text.replace(old, new)


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    branch = run("git", "-C", str(repo), "branch", "--show-current")
    if branch != BRANCH:
        raise RuntimeError(f"expected {BRANCH}, found {branch}")

    lifecycle_path = (
        repo
        / "python/rcp_rclm_runtime_v3/rcp_rclm_runtime_v3/phase10/lifecycle.py"
    )
    lifecycle = lifecycle_path.read_text(encoding="utf-8")
    lifecycle = replace_once(
        lifecycle,
        "from dataclasses import dataclass\n",
        "from dataclasses import dataclass, replace\n",
        "dataclass import",
    )
    lifecycle = replace_once(
        lifecycle,
        "from rcp_rclm_runtime_v3.contract.validation import validate_phase9_transition\n",
        "from rcp_rclm_runtime_v3.contract.validation import (\n"
        "    Phase9TransitionReport,\n"
        "    validate_phase9_transition,\n"
        ")\n",
        "Phase 9 report import",
    )
    lifecycle = replace_once(
        lifecycle,
        "def _candidate_transition_pairs() -> Sequence[tuple[int, int]]:\n"
        "    return tuple(sorted({*PROTECTED_CHAIN, *LEARNED_CHAIN}))\n\n\n"
        "@dataclass(frozen=True, slots=True)\n",
        "def _candidate_transition_pairs() -> Sequence[tuple[int, int]]:\n"
        "    return tuple(sorted({*PROTECTED_CHAIN, *LEARNED_CHAIN}))\n\n\n"
        "def _bind_lifecycle_certificate(\n"
        "    reference: Phase10LearnedReference,\n"
        "    phase6: Phase6PackageBuildEvidence,\n"
        "    candidate_report: Mapping[str, object],\n"
        ") -> tuple[LearnedCertificatePacket, Phase9TransitionReport]:\n"
        "    realization = phase6.report.realization\n"
        "    if realization is None or not realization.rollback.verified:\n"
        "        return reference.certificate, reference.transition_report\n"
        "    certificate = replace(\n"
        "        reference.certificate,\n"
        "        architecture_compatibility_hash=str(candidate_report[\"report_hash\"]),\n"
        "        resource_evidence_hash=canonical_json_hash(\n"
        "            {\n"
        "                \"schema_id\": \"runtime.v3.phase10.lifecycle_resource_evidence.v1\",\n"
        "                \"successor_training_semantic_hash\": (\n"
        "                    reference.successor_training_semantic_hash\n"
        "                ),\n"
        "                \"phase6_usage_hash\": realization.resources.usage_hash,\n"
        "                \"phase6_environment_hash\": realization.environment.environment_hash,\n"
        "                \"changed_file_count\": len(realization.changes),\n"
        "                \"rollback_hash\": realization.rollback.rollback_hash,\n"
        "            }\n"
        "        ),\n"
        "        rollback_evidence_hash=realization.rollback.rollback_hash,\n"
        "    )\n"
        "    transition = validate_phase9_transition(\n"
        "        reference.predecessor_state,\n"
        "        reference.update,\n"
        "        reference.candidate_state,\n"
        "        certificate,\n"
        "        reference.heldout_policy,\n"
        "    )\n"
        "    return certificate, transition\n\n\n"
        "@dataclass(frozen=True, slots=True)\n",
        "lifecycle certificate binder",
    )
    lifecycle = replace_once(
        lifecycle,
        "    embedded_predecessor_report: Mapping[str, object]\n"
        "    embedded_candidate_report: Mapping[str, object]\n",
        "    embedded_predecessor_report: Mapping[str, object]\n"
        "    embedded_candidate_report: Mapping[str, object]\n"
        "    lifecycle_certificate: LearnedCertificatePacket\n"
        "    lifecycle_transition: Phase9TransitionReport\n",
        "fixture lifecycle fields",
    )
    lifecycle = replace_once(
        lifecycle,
        "            and rollback_verified\n"
        "            and observed_candidate.package_hash\n",
        "            and rollback_verified\n"
        "            and self.lifecycle_transition.accepted\n"
        "            and self.lifecycle_certificate.rollback_evidence_hash\n"
        "            == self.phase6.report.realization.rollback.rollback_hash\n"
        "            and observed_candidate.package_hash\n",
        "fixture lifecycle acceptance",
    )
    lifecycle = replace_once(
        lifecycle,
        "            \"phase6_report_hash\": self.phase6.report.report_hash,\n"
        "            \"phase6_candidate_manifest_hash\": (\n",
        "            \"phase6_report_hash\": self.phase6.report.report_hash,\n"
        "            \"lifecycle_certificate_hash\": self.lifecycle_certificate.certificate_hash,\n"
        "            \"lifecycle_transition_report_hash\": (\n"
        "                self.lifecycle_transition.semantic_report_hash\n"
        "            ),\n"
        "            \"lifecycle_transition_accepted\": self.lifecycle_transition.accepted,\n"
        "            \"phase6_candidate_manifest_hash\": (\n",
        "fixture lifecycle JSON",
    )
    lifecycle = replace_once(
        lifecycle,
        "    fixture = Phase10Phase6Fixture(\n"
        "        root=root,\n"
        "        reference=reference,\n"
        "        wrapper_predecessor=wrapper,\n"
        "        selection=selection,\n"
        "        phase6=phase6,\n"
        "        embedded_predecessor_report=embedded_predecessor_report,\n"
        "        embedded_candidate_report=embedded_candidate_report,\n"
        "    )\n",
        "    lifecycle_certificate, lifecycle_transition = _bind_lifecycle_certificate(\n"
        "        reference,\n"
        "        phase6,\n"
        "        embedded_candidate_report,\n"
        "    )\n"
        "    fixture = Phase10Phase6Fixture(\n"
        "        root=root,\n"
        "        reference=reference,\n"
        "        wrapper_predecessor=wrapper,\n"
        "        selection=selection,\n"
        "        phase6=phase6,\n"
        "        embedded_predecessor_report=embedded_predecessor_report,\n"
        "        embedded_candidate_report=embedded_candidate_report,\n"
        "        lifecycle_certificate=lifecycle_certificate,\n"
        "        lifecycle_transition=lifecycle_transition,\n"
        "    )\n",
        "fixture construction",
    )
    lifecycle = replace_once(
        lifecycle,
        "    _write_json(evidence_root / \"phase6_report.json\", phase6.report.to_json())\n"
        "    _write_json(evidence_root / \"fixture.json\", fixture.to_json())\n",
        "    _write_json(evidence_root / \"phase6_report.json\", phase6.report.to_json())\n"
        "    _write_json(\n"
        "        evidence_root / \"lifecycle_certificate.json\",\n"
        "        lifecycle_certificate.to_json(),\n"
        "    )\n"
        "    _write_json(\n"
        "        evidence_root / \"lifecycle_transition.json\",\n"
        "        lifecycle_transition.to_json(),\n"
        "    )\n"
        "    _write_json(evidence_root / \"fixture.json\", fixture.to_json())\n",
        "retained lifecycle evidence",
    )
    lifecycle = replace_once(
        lifecycle,
        "    certificate = LearnedCertificatePacket.from_json(reference_value[\"certificate\"])\n",
        "    certificate = LearnedCertificatePacket.from_json(\n"
        "        load_json_strict(\n"
        "            (retained / \"lifecycle_certificate.json\").read_bytes(),\n"
        "            require_canonical=True,\n"
        "        )\n"
        "    )\n",
        "replay lifecycle certificate",
    )
    lifecycle = replace_once(
        lifecycle,
        "        \"phase6_realization_accepts\": phase6.report.built,\n"
        "        \"rollback_verified\": bool(realization and realization.rollback.verified),\n",
        "        \"phase6_realization_accepts\": phase6.report.built,\n"
        "        \"rollback_verified\": bool(realization and realization.rollback.verified),\n"
        "        \"rollback_evidence_recomputed\": bool(\n"
        "            realization\n"
        "            and certificate.rollback_evidence_hash\n"
        "            == realization.rollback.rollback_hash\n"
        "        ),\n",
        "replay rollback binding check",
    )
    lifecycle = replace_once(
        lifecycle,
        "        \"information_report_hash\": information.report_hash,\n"
        "        \"phase9_transition_report_hash\": transition.semantic_report_hash,\n",
        "        \"information_report_hash\": information.report_hash,\n"
        "        \"lifecycle_certificate_hash\": certificate.certificate_hash,\n"
        "        \"phase9_transition_report_hash\": transition.semantic_report_hash,\n",
        "replay lifecycle report hashes",
    )
    lifecycle_path.write_text(lifecycle, encoding="utf-8", newline="\n")

    promotion_path = (
        repo
        / "python/rcp_rclm_runtime_v3/rcp_rclm_runtime_v3/phase10/promotion.py"
    )
    promotion = promotion_path.read_text(encoding="utf-8")
    promotion = replace_once(
        promotion,
        "from rcp_rclm_runtime_v3.phase10.policy import (\n"
        "    PHASE10_CONTROLLER_ENVIRONMENT_HASH,\n"
        "    phase10_phase7_budget,\n"
        "    phase10_phase7_policy,\n"
        ")\n",
        "from rcp_rclm_runtime_v3.phase10.policy import (\n"
        "    PHASE10_CONTROLLER_ENVIRONMENT_HASH,\n"
        "    PHASE10_TRANSPORT_PROFILE,\n"
        "    phase10_phase7_budget,\n"
        "    phase10_phase7_policy,\n"
        ")\n",
        "transport profile import",
    )
    promotion = replace_once(
        promotion,
        "PHASE10_PROMOTION_POLICY_NOTE: Final[str] = (\n"
        "    \"phase10_specific_policy_over_immutable_runtime_v2_store\"\n"
        ")",
        "PHASE10_PROMOTION_POLICY_NOTE: Final[str] = PHASE10_TRANSPORT_PROFILE",
        "promotion policy note",
    )
    transition_replacements = promotion.count("fixture.reference.transition_report")
    certificate_replacements = promotion.count("fixture.reference.certificate")
    if transition_replacements < 1 or certificate_replacements < 1:
        raise RuntimeError(
            "expected lifecycle promotion bindings; "
            f"transition={transition_replacements}, certificate={certificate_replacements}"
        )
    promotion = promotion.replace(
        "fixture.reference.transition_report",
        "fixture.lifecycle_transition",
    )
    promotion = promotion.replace(
        "fixture.reference.certificate",
        "fixture.lifecycle_certificate",
    )
    promotion_path.write_text(promotion, encoding="utf-8", newline="\n")

    closure_path = (
        repo
        / "python/rcp_rclm_runtime_v3/rcp_rclm_runtime_v3/phase10/closure.py"
    )
    closure = closure_path.read_text(encoding="utf-8")
    closure_count = closure.count("self.fixture.reference.transition_report")
    if closure_count != 2:
        raise RuntimeError(
            f"expected two closure transition bindings, found {closure_count}"
        )
    closure = closure.replace(
        "self.fixture.reference.transition_report",
        "self.fixture.lifecycle_transition",
    )
    closure_path.write_text(closure, encoding="utf-8", newline="\n")

    test_path = repo / "python/rcp_rclm_runtime_v3/tests_phase10/test_lifecycle.py"
    test = test_path.read_text(encoding="utf-8")
    test = replace_once(
        test,
        "        self.assertTrue(fixture.phase6.report.realization.rollback.verified)\n"
        "        self.assertGreater(len(fixture.phase6.report.realization.changes), 0)\n",
        "        self.assertTrue(fixture.phase6.report.realization.rollback.verified)\n"
        "        self.assertTrue(fixture.lifecycle_transition.accepted)\n"
        "        self.assertEqual(\n"
        "            fixture.lifecycle_certificate.rollback_evidence_hash,\n"
        "            fixture.phase6.report.realization.rollback.rollback_hash,\n"
        "        )\n"
        "        self.assertGreater(len(fixture.phase6.report.realization.changes), 0)\n",
        "lifecycle certificate test",
    )
    test = replace_once(
        test,
        "        self.assertTrue(report[\"checks\"][\"forbidden_training_modules_absent\"])\n",
        "        self.assertTrue(report[\"checks\"][\"forbidden_training_modules_absent\"])\n"
        "        self.assertTrue(report[\"checks\"][\"rollback_evidence_recomputed\"])\n",
        "replay rollback certificate test",
    )
    test_path.write_text(test, encoding="utf-8", newline="\n")

    for path in (lifecycle_path, promotion_path, closure_path, test_path):
        run("python", "-m", "py_compile", str(path))

    run("git", "-C", str(repo), "config", "user.name", "github-actions[bot]")
    run(
        "git",
        "-C",
        str(repo),
        "config",
        "user.email",
        "41898282+github-actions[bot]@users.noreply.github.com",
    )
    run(
        "git",
        "-C",
        str(repo),
        "add",
        str(lifecycle_path.relative_to(repo)),
        str(promotion_path.relative_to(repo)),
        str(closure_path.relative_to(repo)),
        str(test_path.relative_to(repo)),
    )
    run(
        "git",
        "-C",
        str(repo),
        "commit",
        "-m",
        "Bind Gate D lifecycle certificate to actual rollback",
    )
    run("git", "-C", str(repo), "push", "origin", f"HEAD:{BRANCH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
