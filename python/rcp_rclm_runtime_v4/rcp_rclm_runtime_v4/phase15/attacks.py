from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash
from rcp_rclm_runtime.canonical.json import canonical_json_bytes
from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime_v4.gatee.records import RouteHintPolicy

from rcp_rclm_runtime_v4.phase15.bundle import verify_phase15_bundle
from rcp_rclm_runtime_v4.phase15.challenges import DynamicHiddenChallenge
from rcp_rclm_runtime_v4.phase15.replay import replay_phase15_bundle


@dataclass(frozen=True, slots=True)
class Phase15AttackCase:
    attack_id: str
    rejected: bool
    reason_class: str

    schema_id: ClassVar[str] = "runtime.v4.phase15.attack_case.v1"

    @property
    def case_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "attack_id": self.attack_id,
            "rejected": self.rejected,
            "reason_class": self.reason_class,
        }


@dataclass(frozen=True, slots=True)
class Phase15AttackSuiteReport:
    source_head: str
    bundle_manifest_hash: str
    cases: Sequence[Phase15AttackCase]

    schema_id: ClassVar[str] = "runtime.v4.phase15.attack_suite.v1"

    @property
    def accepted(self) -> bool:
        return len(self.cases) == 12 and all(item.rejected for item in self.cases)

    @property
    def report_hash(self) -> str:
        return canonical_json_hash(self.content_json())

    def content_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "source_head": self.source_head,
            "bundle_manifest_hash": self.bundle_manifest_hash,
            "cases": [item.to_json() for item in self.cases],
            "attack_count": len(self.cases),
            "accepted": self.accepted,
            "phase15_exit_closed": False,
            "gate_e_closed": False,
        }

    def to_json(self) -> dict[str, object]:
        value = self.content_json()
        value["report_hash"] = self.report_hash
        return value

    @classmethod
    def from_json(cls, value: object) -> "Phase15AttackSuiteReport":
        if not isinstance(value, dict) or not isinstance(value.get("cases"), list):
            raise SchemaValidationError("phase15.attacks", "expected object with cases")
        result = cls(
            source_head=str(value["source_head"]),
            bundle_manifest_hash=str(value["bundle_manifest_hash"]),
            cases=tuple(
                Phase15AttackCase(
                    attack_id=str(item["attack_id"]),
                    rejected=bool(item["rejected"]),
                    reason_class=str(item["reason_class"]),
                )
                for item in value["cases"]
                if isinstance(item, dict)
            ),
        )
        if value.get("report_hash") != result.report_hash or value.get("accepted") is not result.accepted:
            raise SchemaValidationError("phase15.attacks", "derived evidence mismatch")
        return result


def _rejected(attack_id: str, action: Callable[[], object]) -> Phase15AttackCase:
    try:
        action()
    except Exception as error:  # selected adversarial boundary intentionally catches all fail-closed errors
        return Phase15AttackCase(
            attack_id=attack_id,
            rejected=True,
            reason_class=type(error).__name__,
        )
    return Phase15AttackCase(
        attack_id=attack_id,
        rejected=False,
        reason_class="UNEXPECTED_ACCEPT",
    )


def _link_or_copy(source: str, destination: str) -> str:
    try:
        os.link(source, destination)
    except OSError:
        shutil.copy2(source, destination)
    return destination


def _tamper_copy(bundle_root: Path, relative: str, transform: Callable[[bytes], bytes]) -> None:
    # The retained bundle is close to one gigabyte.  Create the attack copy on
    # the same filesystem and hard-link unchanged files so each selected
    # mutation remains exact without multiplying disk and I/O cost.  The one
    # attacked path is unlinked before replacement, preserving the original.
    with tempfile.TemporaryDirectory(
        prefix="rcp-rclm-phase15-attack-",
        dir=bundle_root.parent,
    ) as temporary:
        target = Path(temporary) / "bundle"
        shutil.copytree(
            bundle_root,
            target,
            symlinks=False,
            copy_function=_link_or_copy,
        )
        path = target / relative
        replacement = transform(path.read_bytes())
        path.unlink()
        path.write_bytes(replacement)
        verify_phase15_bundle(target)


def run_phase15_attacks(
    *,
    bundle_root: Path,
    repo_root: Path,
    source_head: str,
) -> Phase15AttackSuiteReport:
    root = bundle_root.resolve(strict=True)
    manifest = verify_phase15_bundle(root)
    cases: list[Phase15AttackCase] = []
    cases.append(
        _rejected(
            "host_route_hint",
            lambda: RouteHintPolicy(host_selected_objective_present=True),
        )
    )
    cases.append(
        _rejected(
            "challenge_before_candidate_freeze",
            lambda: DynamicHiddenChallenge(
                challenge_id="invalid",
                domain="lean_multistep",
                commitment_hash="0" * 64,
                parameter_a=0,
                parameter_b=1,
                generated_after_candidate_freeze=False,
            ),
        )
    )
    cases.append(
        _rejected(
            "private_answer_store_substitution",
            lambda: _tamper_copy(
                root,
                "campaign/answer_store_private.json",
                lambda payload: b'[' + payload[1:],
            ),
        )
    )
    cases.append(
        _rejected(
            "post_freeze_decoder_mutation",
            lambda: _tamper_copy(
                root,
                "campaign/candidate_freeze/multidomain/semantic_candidate/model/phase15_planner/weights.i16le.bin",
                lambda payload: bytes([payload[0] ^ 1]) + payload[1:],
            ),
        )
    )
    cases.append(
        _rejected(
            "inherited_context_substitution",
            lambda: _tamper_copy(
                root,
                "campaign/candidate_freeze/multidomain/semantic_candidate/policies/generator_policy.json",
                lambda payload: payload.replace(b'"manual_repair_permitted":false', b'"manual_repair_permitted":true', 1),
            ),
        )
    )
    cases.append(
        _rejected(
            "hidden_prompt_in_training_request",
            lambda: _run_invalid_training_request(root, "heldout_prompt_present"),
        )
    )
    cases.append(
        _rejected(
            "hidden_answer_in_training_request",
            lambda: _run_invalid_training_request(root, "heldout_reference_answer_present"),
        )
    )
    cases.append(
        _rejected(
            "private_challenge_in_training_request",
            lambda: _run_invalid_training_request(root, "private_challenge_material_present"),
        )
    )
    cases.append(
        _rejected(
            "protected_frontier_regression",
            lambda: _tamper_copy(
                root,
                "campaign/phase15_trajectory.json",
                lambda payload: payload.replace(b'"final_capability_frontier":[', b'"final_capability_frontier":[] ,"discarded":[', 1),
            ),
        )
    )
    cases.append(
        _rejected(
            "candidate_freeze_manifest_substitution",
            lambda: _tamper_copy(
                root,
                "campaign/candidate_freeze_manifest.json",
                lambda payload: payload.replace(b'"challenge_generated_after_all_candidate_freezes":true', b'"challenge_generated_after_all_candidate_freezes":false', 1),
            ),
        )
    )
    replay = replay_phase15_bundle(
        bundle_root=root,
        repo_root=repo_root,
        lean_project_root=None,
        source_head=source_head,
        platform_id="attack-unpinned",
    )
    cases.append(
        Phase15AttackCase(
            attack_id="unpinned_final_replay",
            rejected=not replay.accepted and replay.semantic_replay_accepted,
            reason_class="PINNED_LEAN_REQUIRED",
        )
    )
    source = (repo_root / "python/rcp_rclm_runtime_v4/rcp_rclm_runtime_v4/phase15/training_worker.py").read_text(encoding="utf-8")
    forbidden_imports = (
        "phase15.challenges",
        "answer_store_private",
        "DynamicHiddenChallenge",
    )
    cases.append(
        Phase15AttackCase(
            attack_id="private_challenge_import_in_training_worker",
            rejected=not any(item in source for item in forbidden_imports),
            reason_class="STATIC_SOURCE_BOUNDARY",
        )
    )
    report = Phase15AttackSuiteReport(
        source_head=source_head,
        bundle_manifest_hash=manifest.manifest_hash,
        cases=tuple(cases),
    )
    if not report.accepted:
        failed = [item.attack_id for item in report.cases if not item.rejected]
        raise SchemaValidationError("phase15.attacks", f"attack cases unexpectedly accepted: {failed}")
    return report


def _run_invalid_training_request(bundle_root: Path, field: str) -> None:
    module_name = "rcp_rclm_runtime_v4.phase15.training_worker"
    from rcp_rclm_runtime_v4.phase15.training_worker import run_worker

    request_path = bundle_root / "campaign/candidate_freeze/multidomain/training/training_request.json"
    value = json.loads(request_path.read_text(encoding="utf-8"))
    value[field] = True
    try:
        with tempfile.TemporaryDirectory(prefix="rcp-rclm-phase15-training-attack-") as temporary:
            root = Path(temporary)
            modified = root / "request.json"
            modified.write_bytes(canonical_json_bytes(value))
            run_worker(modified, root / "output")
    finally:
        sys.modules.pop(module_name, None)


__all__ = [
    "Phase15AttackCase",
    "Phase15AttackSuiteReport",
    "run_phase15_attacks",
]
