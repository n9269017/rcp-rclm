from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from rcp_rclm_runtime.canonical.hashing import (
    build_tree_records,
    canonical_json_hash,
    semantic_tree_hash,
    sha256_hex,
)
from rcp_rclm_runtime.canonical.json import load_json_strict
from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime.successor.package_verifier import verify_candidate_package

from rcp_rclm_runtime_v3.contract.certificate import HeldoutAccessPolicy, LearnedCertificatePacket
from rcp_rclm_runtime_v3.contract.state import LearnedRCLMState
from rcp_rclm_runtime_v3.contract.update import LearnedRCLMUpdate
from rcp_rclm_runtime_v3.contract.validation import validate_phase9_transition
from rcp_rclm_runtime_v3.phase10.adapters import verify_adapter_manifest
from rcp_rclm_runtime_v3.phase10.package import (
    SUPPORT_HASH_FIELD_BY_PATH,
    TOKENIZER_BYTES_PATH,
    VOCABULARY_PATH,
    load_package_components,
    recompute_payload_tree_hash,
)
from rcp_rclm_runtime_v3.phase10.tensors import verify_base_tensor_manifest
from rcp_rclm_runtime_v3.phase12.phase12b_candidate import build_phase12b_information_report
from rcp_rclm_runtime_v3.phase12.phase12c_candidate import build_phase12c_information_report
from rcp_rclm_runtime_v3.phase12.phase12d_candidate import build_phase12d_information_report
from rcp_rclm_runtime_v3.phase12.phase12e_candidate import build_phase12e_information_report
from rcp_rclm_runtime_v3.phase13.full_records import (
    Phase13CheckRecord,
    Phase13StructuralReplayReport,
)


_PHASE11_REFERENCE_PATH = (
    "phase12d/phase12c/phase12b/phase12a/phase11_reference/retained/reference.json"
)
_FINAL_REFERENCE_PATH = "retained/reference.json"

_PHASE_PATHS: Sequence[tuple[str, str]] = (
    ("M1", "phase12d/phase12c/phase12b"),
    ("M2", "phase12d/phase12c"),
    ("M3", "phase12d"),
    ("M4", ""),
)

_EXPECTED_MANIFEST_DIFFS: Mapping[str, Sequence[str]] = {
    "M0_to_M1": ("model_identity_hash", "tensor_manifest_hash", "weights_tree_hash"),
    "M1_to_M2": ("memory_manifest_hash", "retrieval_index_hash"),
    "M2_to_M3": ("generator_policy_hash", "planner_policy_hash"),
    "M3_to_M4": (
        "adapter_manifest_hash",
        "model_identity_hash",
        "optimizer_state_hash",
        "parameter_count",
    ),
}

_EXPECTED_CHANGED_COMPONENTS: Mapping[str, Sequence[str]] = {
    "M0_to_M1": ("model_weights",),
    "M1_to_M2": ("memory_state", "retrieval_policy"),
    "M2_to_M3": ("generator_policy", "planner_policy"),
    "M3_to_M4": ("adapter_manifest", "model_architecture", "optimizer_policy"),
}

_PHASE6_COMPONENTS: Mapping[str, Sequence[str]] = {
    "M1": ("model_weights",),
    "M2": ("memory_policy", "retrieval_policy"),
    "M3": ("code_generation_policy", "planning_policy"),
    "M4": ("architecture_code", "training_policy"),
}


def _object(path: Path) -> dict[str, object]:
    value = load_json_strict(path.resolve(strict=True).read_bytes(), require_canonical=True)
    if not isinstance(value, dict):
        raise SchemaValidationError("phase13.structural.json", f"expected object at {path}")
    return value


def _mapping(value: object, path: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise SchemaValidationError(path, "expected object")
    return value


def _sequence(value: object, path: str) -> Sequence[object]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise SchemaValidationError(path, "expected array")
    return value


def _tree_hash(root: Path) -> str:
    return semantic_tree_hash(build_tree_records(root.resolve(strict=True)))


def _phase_node(final_reference: Mapping[str, object], label: str) -> Mapping[str, object]:
    if label == "M4":
        return final_reference
    if label == "M3":
        return _mapping(final_reference["phase12d"], "phase13.reference.phase12d")
    phase12d = _mapping(final_reference["phase12d"], "phase13.reference.phase12d")
    if label == "M2":
        return _mapping(phase12d["phase12c"], "phase13.reference.phase12c")
    phase12c = _mapping(phase12d["phase12c"], "phase13.reference.phase12c")
    return _mapping(phase12c["phase12b"], "phase13.reference.phase12b")


def _package_roots(reference_root: Path) -> Mapping[str, Path]:
    root = reference_root.resolve(strict=True)
    return {
        "M0": root
        / "phase12d/phase12c/phase12b/wrapper_predecessor/payload/model/weights/phase12_package",
        "M1": root / "phase12d/phase12c/phase12b/semantic_candidate",
        "M2": root / "phase12d/phase12c/semantic_candidate",
        "M3": root / "phase12d/semantic_candidate",
        "M4": root / "semantic_candidate",
    }


def _phase_root(reference_root: Path, prefix: str) -> Path:
    return reference_root.resolve(strict=True) / prefix if prefix else reference_root.resolve(strict=True)


def _package_record(label: str, package_root: Path) -> Phase13CheckRecord:
    manifest, architecture, tokenizer, tensors, adapter = load_package_components(package_root)
    verify_base_tensor_manifest(package_root, architecture, tensors)
    if adapter.status == "absent":
        adapter_files_and_graph_valid = (
            adapter.rank == 0
            and adapter.alpha == 0
            and adapter.parameter_count == 0
            and not adapter.records
            and not adapter.target_base_tensors
        )
    else:
        adapter_verification = verify_adapter_manifest(
            package_root,
            architecture,
            tensors.weights_tree_hash,
            adapter,
        )
        adapter_files_and_graph_valid = (
            adapter_verification.expected_tensor_graph
            and adapter.base_weights_tree_hash == tensors.weights_tree_hash
            and (
                adapter_verification.accepted
                or (adapter.status == "trained" and not adapter_verification.all_b_tensors_zero)
            )
        )
    support_checks: dict[str, bool] = {}
    for relative, field_name in SUPPORT_HASH_FIELD_BY_PATH.items():
        value = load_json_strict((package_root / relative).read_bytes(), require_canonical=True)
        support_checks[f"support_{field_name}"] = canonical_json_hash(value) == getattr(
            manifest, field_name
        )
    vocabulary = load_json_strict(
        (package_root / VOCABULARY_PATH).read_bytes(),
        require_canonical=True,
    )
    checks = {
        "adapter_files_and_graph_valid": adapter_files_and_graph_valid,
        "adapter_manifest_bound": adapter.manifest_hash == manifest.adapter_manifest_hash,
        "architecture_bound": architecture.architecture_hash == manifest.architecture_hash,
        "base_tensor_files_valid": True,
        "model_identity_bound": manifest.model_identity().model_identity_hash
        == manifest.model_identity_hash,
        "parameter_count_bound": manifest.parameter_count
        == tensors.parameter_count + adapter.parameter_count,
        "payload_tree_hash_bound": recompute_payload_tree_hash(package_root)
        == manifest.payload_tree_hash,
        "tensor_manifest_bound": tensors.manifest_hash == manifest.tensor_manifest_hash,
        "tokenizer_bytes_bound": sha256_hex((package_root / TOKENIZER_BYTES_PATH).read_bytes())
        == manifest.tokenizer_hash,
        "tokenizer_manifest_bound": tokenizer.manifest_hash == manifest.tokenizer_manifest_hash,
        "vocabulary_bound": canonical_json_hash(vocabulary) == manifest.vocabulary_hash,
        "weights_tree_bound": tensors.weights_tree_hash == manifest.weights_tree_hash,
        **support_checks,
    }
    return Phase13CheckRecord(
        record_id=f"package.{label}",
        checks={key: checks[key] for key in sorted(checks, key=lambda item: item.encode("utf-8"))},
        evidence_hashes={
            "adapter_manifest_hash": manifest.adapter_manifest_hash,
            "model_identity_hash": manifest.model_identity_hash,
            "package_hash": manifest.package_hash,
            "payload_tree_hash": manifest.payload_tree_hash,
            "tensor_manifest_hash": manifest.tensor_manifest_hash,
            "weights_tree_hash": manifest.weights_tree_hash,
        },
    )


def _manifest_diff_record(
    transition_id: str,
    predecessor_root: Path,
    candidate_root: Path,
) -> Phase13CheckRecord:
    predecessor = load_package_components(predecessor_root)[0]
    candidate = load_package_components(candidate_root)[0]
    ignored = {
        "package_id",
        "parent_package_id",
        "payload_tree_hash",
    }
    before = predecessor.content_json()
    after = candidate.content_json()
    changed = tuple(
        sorted(
            (
                key
                for key in set(before) | set(after)
                if key not in ignored and before.get(key) != after.get(key)
            ),
            key=lambda item: item.encode("utf-8"),
        )
    )
    expected = tuple(_EXPECTED_MANIFEST_DIFFS[transition_id])
    checks = {
        "declared_parent_package_bound": candidate.parent_package_id == predecessor.package_id,
        "manifest_change_schedule_exact": changed == expected,
        "package_hash_changed": candidate.package_hash != predecessor.package_hash,
    }
    return Phase13CheckRecord(
        record_id=f"manifest_diff.{transition_id}",
        checks={key: checks[key] for key in sorted(checks)},
        evidence_hashes={
            "candidate_package_hash": candidate.package_hash,
            "manifest_diff_hash": canonical_json_hash(list(changed)),
            "predecessor_package_hash": predecessor.package_hash,
        },
    )


def _promotion_record(
    label: str,
    prefix: str,
    node: Mapping[str, object],
    reference_root: Path,
    predecessor_package_root: Path,
    semantic_package_root: Path,
) -> Phase13CheckRecord:
    phase_root = _phase_root(reference_root, prefix)
    candidate_root = phase_root / "phase6_candidate"
    wrapper_root = phase_root / "wrapper_predecessor"
    candidate_manifest = verify_candidate_package(candidate_root)
    embedded_candidate = candidate_root / "payload/model/weights/phase12_package"
    embedded_predecessor = wrapper_root / "payload/model/weights/phase12_package"
    phase6 = _mapping(node["phase6"], f"phase13.{label}.phase6")
    phase6_report = _mapping(phase6["phase6_report"], f"phase13.{label}.phase6_report")
    summary = _mapping(node["summary"], f"phase13.{label}.summary")
    report_candidate = _mapping(
        phase6_report["candidate_manifest"],
        f"phase13.{label}.phase6_report.candidate_manifest",
    )
    rollback = _object(candidate_root / "evidence/rollback.json")
    selection = _object(candidate_root / "evidence/selection.json")
    expected_components = tuple(_PHASE6_COMPONENTS[label])
    observed_components = tuple(
        _sequence(selection["substantive_component_kinds"], "phase13.selection.components")
    )
    checks = {
        "candidate_manifest_matches_retained_report": candidate_manifest.to_json()
        == dict(report_candidate),
        "candidate_payload_embeds_semantic_package": _tree_hash(embedded_candidate)
        == _tree_hash(semantic_package_root),
        "candidate_verified_by_phase6_verifier": True,
        "phase6_record_hash_bound": canonical_json_hash(dict(phase6)) == summary["phase6_hash"],
        "predecessor_wrapper_embeds_active_package": _tree_hash(embedded_predecessor)
        == _tree_hash(predecessor_package_root),
        "rollback_record_hash_bound": canonical_json_hash(rollback) == phase6["rollback_hash"],
        "rollback_restoration_verified": phase6["rollback_verified"] is True,
        "substantive_component_schedule_exact": observed_components == expected_components,
    }
    return Phase13CheckRecord(
        record_id=f"promotion.{label}",
        checks={key: checks[key] for key in sorted(checks)},
        evidence_hashes={
            "candidate_manifest_hash": candidate_manifest.manifest_hash,
            "candidate_package_tree_hash": _tree_hash(candidate_root),
            "candidate_payload_tree_hash": candidate_manifest.payload_tree_hash,
            "phase6_record_hash": canonical_json_hash(dict(phase6)),
            "rollback_archive_sha256": sha256_hex(
                (candidate_root / "rollback/predecessor.tar").read_bytes()
            ),
            "rollback_record_hash": canonical_json_hash(rollback),
            "selection_hash": canonical_json_hash(selection),
        },
    )


def _phase12a_rejection(final_reference: Mapping[str, object]) -> Phase13CheckRecord:
    phase12d = _mapping(final_reference["phase12d"], "phase13.phase12d")
    phase12c = _mapping(phase12d["phase12c"], "phase13.phase12c")
    phase12b = _mapping(phase12c["phase12b"], "phase13.phase12b")
    phase12a = _mapping(phase12b["phase12a"], "phase13.phase12a")
    first = _mapping(phase12a["first_invocation"], "phase13.phase12a.first")
    replay = _mapping(phase12a["replay_invocation"], "phase13.phase12a.replay")
    validation = _mapping(phase12a["first_validation"], "phase13.phase12a.validation")
    summary = _mapping(phase12a["summary"], "phase13.phase12a.summary")
    reasons = tuple(_sequence(validation["reason_codes"], "phase13.phase12a.reasons"))
    program = _mapping(first["program"], "phase13.phase12a.program")
    checks = {
        "deterministic_duplicate_capture": dict(first) == dict(replay),
        "heldout_material_not_consumed": summary["heldout_material_consumed"] is False,
        "manual_repairs_zero": summary["manual_repairs"] == 0,
        "package_unchanged_after_rejection": phase12a["package_unchanged"] is True,
        "program_hash_bound": canonical_json_hash(dict(program)) == first["program_hash"],
        "rejection_reason_exact": reasons == ("PHASE12_GENERATION_NOT_ADVANCED",),
        "summary_invocation_hash_bound": canonical_json_hash(dict(first))
        == summary["first_invocation_hash"],
        "summary_validation_hash_bound": canonical_json_hash(dict(validation))
        == summary["first_validation_hash"],
        "validation_rejected": validation["accepted"] is False,
    }
    return Phase13CheckRecord(
        record_id="rejection.phase12a_generation_not_advanced",
        checks={key: checks[key] for key in sorted(checks)},
        evidence_hashes={
            "invocation_hash": canonical_json_hash(dict(first)),
            "program_hash": canonical_json_hash(dict(program)),
            "validation_hash": canonical_json_hash(dict(validation)),
        },
    )


def _phase12c_rejection(final_reference: Mapping[str, object]) -> Phase13CheckRecord:
    phase12d = _mapping(final_reference["phase12d"], "phase13.phase12d")
    phase12c = _mapping(phase12d["phase12c"], "phase13.phase12c")
    proposal = _mapping(phase12c["invalid_proposal"], "phase13.phase12c.invalid_proposal")
    replay = _mapping(
        phase12c["invalid_proposal_replay"],
        "phase13.phase12c.invalid_proposal_replay",
    )
    validation = _mapping(
        phase12c["invalid_validation"],
        "phase13.phase12c.invalid_validation",
    )
    summary = _mapping(phase12c["summary"], "phase13.phase12c.summary")
    reasons = tuple(_sequence(validation["reason_codes"], "phase13.phase12c.reasons"))
    program = _mapping(proposal["program"], "phase13.phase12c.program")
    selected_classes = set(
        _sequence(program["selected_update_classes"], "phase13.phase12c.selected_update_classes")
    )
    selected_components = set(
        _sequence(
            program["expected_affected_components"],
            "phase13.phase12c.expected_affected_components",
        )
    )
    checks = {
        "component_schedule_is_incomplete": selected_classes != {
            "memory_update",
            "retrieval_update",
        }
        or selected_components != {"memory_state", "retrieval_policy"},
        "deterministic_duplicate_capture": dict(proposal) == dict(replay),
        "heldout_material_not_consumed": proposal["heldout_material_consumed"] is False,
        "manual_repairs_zero": proposal["manual_repairs"] == 0,
        "package_unchanged_after_rejection": proposal["package_unchanged"] is True,
        "program_hash_bound": canonical_json_hash(dict(program)) == proposal["program_hash"],
        "rejection_reason_exact": reasons == ("PHASE12C_COMPONENT_SCHEDULE_INCOMPLETE",),
        "summary_proposal_hash_bound": canonical_json_hash(dict(proposal))
        == summary["invalid_proposal_hash"],
        "summary_validation_hash_bound": canonical_json_hash(dict(validation))
        == summary["invalid_validation_hash"],
        "validation_rejected": validation["accepted"] is False,
    }
    return Phase13CheckRecord(
        record_id="rejection.phase12c_component_schedule_incomplete",
        checks={key: checks[key] for key in sorted(checks)},
        evidence_hashes={
            "program_hash": canonical_json_hash(dict(program)),
            "proposal_hash": canonical_json_hash(dict(proposal)),
            "validation_hash": canonical_json_hash(dict(validation)),
        },
    )


def _information_records(
    final_reference: Mapping[str, object],
    package_roots: Mapping[str, Path],
) -> Sequence[Phase13CheckRecord]:
    builders = (
        ("M0_to_M1", build_phase12b_information_report, "M0", "M1", "M1"),
        ("M1_to_M2", build_phase12c_information_report, "M1", "M2", "M2"),
        ("M2_to_M3", build_phase12d_information_report, "M2", "M3", "M3"),
        ("M3_to_M4", build_phase12e_information_report, "M3", "M4", "M4"),
    )
    records = []
    for transition_id, builder, before_label, after_label, node_label in builders:
        report = builder(package_roots[before_label], package_roots[after_label])
        node = _phase_node(final_reference, node_label)
        semantic_candidate = _mapping(
            node["semantic_candidate"],
            f"phase13.{node_label}.semantic_candidate",
        )
        retained = _mapping(
            semantic_candidate["information_report"],
            f"phase13.{node_label}.information_report",
        )
        certificate = _mapping(node["lifecycle_certificate"], f"phase13.{node_label}.certificate")
        report_hash = canonical_json_hash(report.to_json())
        checks = {
            "certificate_information_hash_bound": certificate["entropy_kl_qre_evidence_hash"]
            == report_hash,
            "information_report_accepted": report.accepted,
            "retained_information_exact": report.to_json() == dict(retained),
        }
        records.append(
            Phase13CheckRecord(
                record_id=f"information.{transition_id}",
                checks={key: checks[key] for key in sorted(checks)},
                evidence_hashes={
                    "information_report_hash": report_hash,
                    "retained_information_hash": canonical_json_hash(dict(retained)),
                },
            )
        )
    return tuple(records)


def _lifecycle_records(
    final_reference: Mapping[str, object],
    phase11_reference: Mapping[str, object],
) -> Sequence[Phase13CheckRecord]:
    beta_candidate = _mapping(phase11_reference["beta_candidate"], "phase13.phase11.beta_candidate")
    predecessor_state_json = _mapping(
        beta_candidate["candidate_state"],
        "phase13.phase11.beta_candidate.candidate_state",
    )
    records = []
    for transition_id, label in (
        ("M0_to_M1", "M1"),
        ("M1_to_M2", "M2"),
        ("M2_to_M3", "M3"),
        ("M3_to_M4", "M4"),
    ):
        node = _phase_node(final_reference, label)
        semantic = _mapping(node["semantic_candidate"], f"phase13.{label}.semantic_candidate")
        candidate_state_json = _mapping(
            semantic["candidate_state"],
            f"phase13.{label}.candidate_state",
        )
        update_json = _mapping(semantic["update"], f"phase13.{label}.update")
        certificate_json = _mapping(semantic["certificate"], f"phase13.{label}.certificate")
        retained_certificate_json = _mapping(
            node["lifecycle_certificate"],
            f"phase13.{label}.lifecycle_certificate",
        )
        policy_json = _mapping(semantic["heldout_policy"], f"phase13.{label}.heldout_policy")
        predecessor = LearnedRCLMState.from_json(dict(predecessor_state_json))
        candidate = LearnedRCLMState.from_json(dict(candidate_state_json))
        update = LearnedRCLMUpdate.from_json(dict(update_json))
        certificate = LearnedCertificatePacket.from_json(dict(certificate_json))
        retained_certificate = LearnedCertificatePacket.from_json(dict(retained_certificate_json))
        policy = HeldoutAccessPolicy.from_json(dict(policy_json))
        semantic_recomputed = validate_phase9_transition(
            predecessor,
            update,
            candidate,
            certificate,
            policy,
        )
        retained_recomputed = validate_phase9_transition(
            predecessor,
            update,
            candidate,
            retained_certificate,
            policy,
        )
        retained_transition = _mapping(
            node["lifecycle_transition"],
            f"phase13.{label}.lifecycle_transition",
        )
        semantic_transition = _mapping(
            semantic["transition_report"],
            f"phase13.{label}.semantic_transition",
        )
        expected_changed = tuple(_EXPECTED_CHANGED_COMPONENTS[transition_id])
        checks = {
            "candidate_parent_state_bound": candidate.parent_package_id == predecessor.package_id,
            "changed_component_schedule_exact": tuple(semantic_recomputed.changed_components)
            == expected_changed,
            "recomputed_transition_accepted": semantic_recomputed.accepted
            and retained_recomputed.accepted,
            "retained_transition_exact": retained_recomputed.to_json()
            == dict(retained_transition),
            "semantic_transition_exact": semantic_recomputed.to_json()
            == dict(semantic_transition),
        }
        records.append(
            Phase13CheckRecord(
                record_id=f"lifecycle.{transition_id}",
                checks={key: checks[key] for key in sorted(checks)},
                evidence_hashes={
                    "candidate_state_hash": candidate.state_hash,
                    "certificate_hash": certificate.certificate_hash,
                    "predecessor_state_hash": predecessor.state_hash,
                    "retained_certificate_hash": retained_certificate.certificate_hash,
                    "retained_transition_report_hash": canonical_json_hash(
                        retained_recomputed.to_json()
                    ),
                    "transition_report_hash": canonical_json_hash(
                        semantic_recomputed.to_json()
                    ),
                    "update_hash": update.update_hash,
                },
            )
        )
        predecessor_state_json = candidate_state_json
    return tuple(records)


def replay_phase13_structural_reference(reference_root: Path) -> Phase13StructuralReplayReport:
    root = reference_root.resolve(strict=True)
    final_reference = _object(root / _FINAL_REFERENCE_PATH)
    phase11_reference = _object(root / _PHASE11_REFERENCE_PATH)
    package_roots = _package_roots(root)
    package_records = tuple(
        _package_record(label, package_roots[label])
        for label in ("M0", "M1", "M2", "M3", "M4")
    )
    manifest_diff_records = tuple(
        _manifest_diff_record(transition_id, package_roots[before], package_roots[after])
        for transition_id, before, after in (
            ("M0_to_M1", "M0", "M1"),
            ("M1_to_M2", "M1", "M2"),
            ("M2_to_M3", "M2", "M3"),
            ("M3_to_M4", "M3", "M4"),
        )
    )
    promotion_records = []
    for label, prefix in _PHASE_PATHS:
        predecessor_label = f"M{int(label[1:]) - 1}"
        promotion_records.append(
            _promotion_record(
                label,
                prefix,
                _phase_node(final_reference, label),
                root,
                package_roots[predecessor_label],
                package_roots[label],
            )
        )
    promotion_records.extend(manifest_diff_records)
    promotion_records.sort(key=lambda item: item.record_id.encode("utf-8"))
    rejection_records = tuple(
        sorted(
            (_phase12a_rejection(final_reference), _phase12c_rejection(final_reference)),
            key=lambda item: item.record_id.encode("utf-8"),
        )
    )
    information_records = tuple(
        sorted(
            _information_records(final_reference, package_roots),
            key=lambda item: item.record_id.encode("utf-8"),
        )
    )
    lifecycle_records = tuple(
        sorted(
            _lifecycle_records(final_reference, phase11_reference),
            key=lambda item: item.record_id.encode("utf-8"),
        )
    )
    ledger = _mapping(final_reference["ledger"], "phase13.reference.ledger")
    invocation_checks = {
        "captured_generator_invocations_six": ledger["generator_invocations"] == 6,
        "captured_manual_repairs_zero": ledger["manual_repairs"] == 0,
        "captured_rejections_two": ledger["rejected_attempts"] == 2,
        "heldout_material_not_consumed": final_reference["summary"]["heldout_material_consumed"]
        is False,
        "replay_generator_invocations_zero": True,
        "replay_planner_invocations_zero": True,
        "replay_training_invocations_zero": True,
    }
    return Phase13StructuralReplayReport(
        source_reference_hash=canonical_json_hash(final_reference),
        package_records=package_records,
        promotion_records=tuple(promotion_records),
        rejection_records=rejection_records,
        information_records=information_records,
        lifecycle_records=lifecycle_records,
        invocation_checks={
            key: invocation_checks[key]
            for key in sorted(invocation_checks, key=lambda item: item.encode("utf-8"))
        },
    )


__all__ = ["replay_phase13_structural_reference"]
