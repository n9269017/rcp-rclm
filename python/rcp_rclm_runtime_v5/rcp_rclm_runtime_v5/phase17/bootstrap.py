"""Reopen an externally pinned, historically accepted Phase 16 predecessor.

This is an integrity/lineage handoff, NOT a new Lean verification, a fresh
full-tensor execution, Phase 18 replay, or promotion authority. Archive digests
are fixed in trusted source; no candidate-supplied anchor or success bit can
select a different historical package. Only selected small bundle members are
read, in memory, and no archive path is extracted or executed.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import hashlib
import io
from pathlib import Path, PurePosixPath
import stat
import struct
import zipfile

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash
from rcp_rclm_runtime.canonical.json import canonical_json_bytes, load_json_strict
from rcp_rclm_runtime_v5.phase17.controller import (
    ControlError, FAMILIES, FIXED_VERIFIER, SEMANTICS, _hash, _integer, _keys,
)

CAPTURE_SHA256 = "7337079801916ecccce0e3a292d5379cea17b571acc6f31b9b38cb21f9f63dde"
CLOSURE_SHA256 = "ce7f1de4654306d5280970dfc92453a8743cf1e02fe98963f1e940c0077582f9"
M9_BUNDLE_SHA256 = "56003f95ded054be21dd3f743c2145fdf6e92543af28bb350f64ec8f4fee00b5"
CAPTURE_HASH = "ad6d25e453840cefb7240de7854d2a53572c7af0a6b38851efd76654fb84bbb6"
CLOSURE_HASH = "f5c4943647c3a54ab4e1686a45c64926844fb97a99f7eafe054679a34ba896ee"
BOOTSTRAP_HASH = "f052e6055dcd2fe6fc34907a2684dd3cbac7e94d32bad18a4d9ed921da7c0513"
M9_PACKAGE_HASH = "a20e01b73f6b6ab069ce93bcbb43d5b745d3210268a4f958be5e744057e53dc6"
PLANNER_HASH = "67045ba2da9dd897b851bba31f05ed0e9faf93fa665245f87803904cfa5fe6d7"
WEIGHTS_SHA256 = "19869eac5b0da770505214a6c5817b94dfda05730f97598bf2f855aff82d6c8d"
SOURCE_HEAD = "b870b3cff8ae5c7fe5e26c2308279bea357bc99c"
SOURCE_TREE = "4cba347fc51480e67402ba176643c2e985f45bd0"
SELECTED_CAMPAIGN_HASH = "e4e68386d2896d843bd741c0de93897ceeda7eecef503ec4a396b6d235dcb170"
SELECTED_STATE_HASH = "7d2b823c05e4e4cef7566a89d3d440dba60a6417c6a3401f1248e59f89e91567"
CATALOG_HASH = "8a14b55b6ca8d751e250e86cfd21958cd5715702fd0fd62997d71f0a77b23cd9"
HANDOFF_RECEIPT_HASH = "c2872b3a27781b0289f92e4d76f0a154032a706a560c9255412cf3ef73d33103"
SELECTION_POLICY = "phase17.minimum-rung-then-utf8-seed-stream.v1"
M9_PREFIX = "campaign/candidate_freeze/multidomain/semantic_candidate/"
SCHEMA = "runtime.v5.phase17.historical_bootstrap.v1"

OPERATIONS = dict(zip(FAMILIES, (
    "install_transfer_adapter_motif", "install_bounded_execution_route",
    "install_content_addressed_memory_motif", "install_expanding_resource_schedule",
    "install_fair_search_planning_rule", "install_rejection_conditioned_retrieval_route",
    "install_package_bound_tool_chain", "install_untrusted_proof_search_policy",
), strict=True))
RECURSIVE = dict(zip(FAMILIES, (
    "recursive.transfer_verified_mutation_motif", "recursive.select_bounded_execution_route",
    "recursive.archive_rejection_context", "recursive.expand_resource_envelope",
    "recursive.plan_fair_search_prefix", "recursive.retrieve_mutation_motifs",
    "recursive.invoke_package_bound_search_tool", "recursive.produce_root_checked_proof_attempt",
), strict=True))


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ControlError(message)


def _json(data: bytes) -> dict:
    value = load_json_strict(data, require_canonical=False)
    _require(type(value) is dict, "JSON object required")
    return value


def _bound(record: dict, field: str = "report_hash") -> str:
    _require(type(record) is dict, "bound object required")
    observed = _hash(record.get(field), field)
    payload = {key: value for key, value in record.items() if key != field}
    _require(canonical_json_hash(payload) == observed, f"invalid {field}")
    return observed


def _read_pinned_archive(path: Path, digest: str, *, max_bytes: int = 16 * 1024 * 1024) -> zipfile.ZipFile:
    # Read once: avoid a check-then-reopen race between hashing and decompression.
    path = Path(path)
    _require(not path.is_symlink() and path.is_file(), "regular archive file required")
    with path.open("rb") as handle:
        data = handle.read(max_bytes + 1)
    _require(len(data) <= max_bytes, "archive exceeds ingestion bound")
    _require(hashlib.sha256(data).hexdigest() == digest, "historical archive digest mismatch")
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
        try:
            names: set[str] = set()
            for info in archive.infolist():
                # ZipInfo.filename may normalize Windows separators or truncate
                # a NUL. Validate the original decoded header name first; never
                # let normalization silently admit a nonportable member.
                name = info.orig_filename
                p = PurePosixPath(name)
                _require(bool(name) and name == info.filename and not p.is_absolute()
                         and ".." not in p.parts and "\\" not in name
                         and ":" not in name and "\x00" not in name,
                         "nonportable archive member")
                _require(name not in names, "duplicate archive member")
                names.add(name)
                mode = (info.external_attr >> 16) & 0xFFFF
                _require(not stat.S_ISLNK(mode) and not info.flag_bits & 1,
                         "symlink or encrypted archive member")
        except Exception:
            archive.close()
            raise
        return archive
    except (zipfile.BadZipFile, OSError) as exc:
        raise ControlError("invalid historical archive") from exc


def _member(archive: zipfile.ZipFile, name: str, limit: int) -> bytes:
    try:
        info = archive.getinfo(name)
        _require(not info.is_dir() and 0 <= info.file_size <= limit, "invalid member size")
        with archive.open(info) as handle:
            data = handle.read(limit + 1)
        _require(len(data) == info.file_size, "member length mismatch")
        return data
    except (KeyError, zipfile.BadZipFile, RuntimeError, OSError) as exc:
        raise ControlError(f"could not read historical member: {name}") from exc


def _sorted_unique(values: object, name: str, *, hashes: bool = False) -> list[str]:
    _require(type(values) is list and all(type(x) is str and x for x in values), f"invalid {name}")
    _require(values == sorted(set(values), key=lambda x: x.encode("utf-8")), f"unordered {name}")
    if hashes:
        for item in values:
            _hash(item, name)
    return values


def validate_state(state: object) -> dict:
    obj = _keys(state, {"schema_id", "model_index", "active_package_hash",
        "component_generations", "installed_program_hashes", "capability_frontier",
        "recursive_productivity_frontier", "archive_root_hash", "fixed_verifier_hash",
        "semantics_id"}, "Phase16 state")
    _require(obj["schema_id"] == "runtime.v4.phase16.model_state.v1", "state schema changed")
    _integer(obj["model_index"], "model_index", 9)
    for field in ("active_package_hash", "archive_root_hash", "fixed_verifier_hash"):
        _hash(obj[field], field)
    _require(obj["fixed_verifier_hash"] == FIXED_VERIFIER and obj["semantics_id"] == SEMANTICS,
             "historical trust constitution changed")
    generations = _keys(obj["component_generations"], set(FAMILIES), "component_generations")
    for value in generations.values():
        _integer(value, "component generation")
    _sorted_unique(obj["installed_program_hashes"], "installed_program_hashes", hashes=True)
    _sorted_unique(obj["capability_frontier"], "capability_frontier")
    _sorted_unique(obj["recursive_productivity_frontier"], "recursive_productivity_frontier")
    return obj


def _validate_program(program: dict) -> None:
    _keys(program, {"schema_id", "promotion_index", "family", "variant", "generation",
                   "operation_id", "parameter_a", "parameter_b", "public_nonce_hash"}, "program")
    _require(program["schema_id"] == "runtime.v4.phase16.mutation_program.v1", "program schema changed")
    _require(program["family"] in FAMILIES, "unknown family")
    _require(program["operation_id"] == OPERATIONS[program["family"]], "operation substitution")
    _integer(program["promotion_index"], "promotion_index")
    _integer(program["generation"], "generation", 1)
    _integer(program["variant"], "variant")
    _require(program["variant"] < 4, "variant outside fixed grammar")
    for key in ("parameter_a", "parameter_b"):
        _require(type(program[key]) is int and -16 <= program[key] <= 16, "invalid grammar parameter")
    _hash(program["public_nonce_hash"], "public_nonce_hash")


def _archive_roots(campaign: dict) -> list[str]:
    archive = campaign["archive"]
    _require(archive["untrusted_for_acceptance"] is True, "archive trust escalation")
    roots = [archive["bootstrap_hash"]]
    _require(roots[0] == BOOTSTRAP_HASH, "archive bootstrap substitution")
    records = archive["records"]
    _require(type(records) is list and len(records) == archive["record_count"], "archive count mismatch")
    for i, record in enumerate(records):
        _require(type(record["sequence_number"]) is int and record["sequence_number"] == i,
                 "archive sequence mismatch")
        _require(record["parent_record_hash"] == roots[-1], "archive parent mismatch")
        _require(record["payload_hash"] == canonical_json_hash(record["payload"]), "archive payload mismatch")
        roots.append(_bound(record, "record_hash"))
    _require(roots[-1] == archive["root_hash"] == campaign["archive_root_hash"], "archive root mismatch")
    return roots


def validate_selected_lineage(campaign: dict) -> tuple[bytes, ...]:
    """Recompute selected historical state/hash linkage, not prior Lean proofs."""
    _bound(campaign)
    state = validate_state(campaign["initial_state"])
    _require(state["active_package_hash"] == M9_PACKAGE_HASH and state["model_index"] == 9,
             "initial M9 identity mismatch")
    _require(canonical_json_hash(state) == campaign["initial_state_hash"], "initial state hash mismatch")
    roots = _archive_roots(campaign)
    programs: list[bytes] = []
    archive_cursor = 0
    family_counts: Counter[str] = Counter()
    transitions = campaign["transitions"]
    _require(len(transitions) == campaign["accepted_promotions"] == campaign["target_promotions"],
             "historical transition count mismatch")
    for index, transition in enumerate(transitions):
        _bound(transition, "transition_hash")
        _require(transition["promotion_index"] == index and type(transition["promotion_index"]) is int,
                 "historical transition ordering mismatch")
        _require(transition["accepted"] is True and transition["manual_repairs"] == 0
                 and type(transition["manual_repairs"]) is int
                 and transition["host_authored_success_schedule_present"] is False,
                 "historical transition claim mismatch")
        _require(transition["predecessor_state"] == state
                 and transition["predecessor_state_hash"] == canonical_json_hash(state),
                 "predecessor substitution")
        _require(transition["fixed_verifier_hash"] == FIXED_VERIFIER
                 and transition["semantics_id"] == SEMANTICS
                 and transition["protected_base_m9_semantic_package_hash"] == M9_PACKAGE_HASH
                 and transition["protected_base_package_mutated"] is False,
                 "transition trust substitution")
        program = transition["accepted_program"]
        _validate_program(program)
        program_hash = canonical_json_hash(program)
        family = program["family"]
        _require(program_hash == transition["accepted_program_hash"]
                 and family == transition["accepted_family"]
                 and program["variant"] == transition["accepted_variant"]
                 and program["promotion_index"] == index
                 and program["generation"] == state["component_generations"][family] + 1
                 and program["public_nonce_hash"] == transition["public_nonce_hash"],
                 "accepted mutation identity mismatch")
        attempts = transition["search_attempts"]
        evaluations = transition["independent_evaluations"]
        _require(type(attempts) is list and attempts and len(attempts) == len(evaluations),
                 "missing evaluation history")
        for attempt, evaluation in zip(attempts, evaluations, strict=True):
            _require(_bound(evaluation) == attempt["evaluation_hash"], "evaluation substitution")
            _require(evaluation["program_hash"] == attempt["program_hash"]
                     and canonical_json_hash(attempt["program"]) == attempt["program_hash"],
                     "attempt program substitution")
        evaluation = evaluations[-1]
        _require(evaluation["accepted"] is True and evaluation["program_hash"] == program_hash
                 and evaluation["report_hash"] == transition["accepted_evaluation_hash"],
                 "accepted evaluation mismatch")
        # Phase 16 writes six archive records for every attempted program.
        archive_cursor += 6 * len(attempts)
        _require(archive_cursor < len(roots)
                 and roots[archive_cursor] == transition["archive_root_after"], "transition archive mismatch")
        successor = validate_state(transition["successor_state"])
        generations = dict(state["component_generations"])
        generations[family] += 1
        challenge = transition["public_challenge"]
        private = transition["retained_private_challenge"]
        _require(private["target_program_hash"] == program_hash
                 and private["target_family"] == family
                 and private["commitment_hash"] == challenge["commitment_hash"]
                 and private["capability_id"] == f"phase16.dynamic.{family}.{challenge['commitment_hash'][:20]}",
                 "historical challenge binding mismatch")
        capabilities = sorted((*state["capability_frontier"], transition["retained_private_challenge"]["capability_id"]))
        recursive = sorted(set(state["recursive_productivity_frontier"]) | {RECURSIVE[family]})
        installed = sorted((*state["installed_program_hashes"], program_hash))
        expected_package = canonical_json_hash({
            "domain": "phase16.atomic_successor_package.v1",
            "predecessor_package_hash": state["active_package_hash"],
            "protected_base_m9_semantic_package_hash": M9_PACKAGE_HASH,
            "protected_base_package_mutated": False,
            "predecessor_state_hash": canonical_json_hash(state),
            "program": program, "program_hash": program_hash,
            "challenge_commitment_hash": challenge["commitment_hash"],
            "accepted_evaluation_hash": evaluation["report_hash"],
            "archive_root_hash": roots[archive_cursor],
            "capability_frontier": capabilities,
            "recursive_productivity_frontier": recursive,
            "component_generations": generations,
            "fixed_verifier_hash": FIXED_VERIFIER, "semantics_id": SEMANTICS,
        })
        expected_state = dict(state, model_index=state["model_index"] + 1,
                              active_package_hash=expected_package,
                              component_generations=generations,
                              installed_program_hashes=installed,
                              capability_frontier=capabilities,
                              recursive_productivity_frontier=recursive,
                              archive_root_hash=roots[archive_cursor])
        _require(successor == expected_state and canonical_json_hash(successor) == transition["successor_state_hash"],
                 "successor state/frontier/package mismatch")
        programs.append(canonical_json_bytes(program))
        family_counts[family] += 1
        state = successor
    _require(archive_cursor == len(roots) - 1, "unbound archive suffix")
    _require(state == campaign["final_state"]
             and canonical_json_hash(state) == campaign["final_state_hash"], "terminal mismatch")
    _require(dict(family_counts) == campaign["update_family_counts"], "family count mismatch")
    return tuple(programs)


@dataclass(frozen=True, slots=True)
class HistoricalPredecessor:
    """Detached, byte-backed handoff. This object is not a promotion certificate."""
    state_bytes: bytes
    accepted_programs: tuple[bytes, ...]
    planner_weights: bytes
    catalog_bytes: bytes
    receipt_bytes: bytes

    def __post_init__(self) -> None:
        _require(all(type(x) is bytes for x in (self.state_bytes, self.planner_weights,
                 self.catalog_bytes, self.receipt_bytes)), "immutable bootstrap bytes required")
        _require(type(self.accepted_programs) is tuple and all(type(x) is bytes for x in self.accepted_programs),
                 "immutable program tuple required")
        self.validate()

    def validate(self) -> None:
        state = validate_state(_json(self.state_bytes))
        _require(canonical_json_bytes(state) == self.state_bytes
                 and canonical_json_hash(state) == SELECTED_STATE_HASH, "unanchored bootstrap state")
        _require(hashlib.sha256(self.planner_weights).hexdigest() == WEIGHTS_SHA256, "unanchored planner weights")
        hashes = []
        for index, data in enumerate(self.accepted_programs):
            p = _json(data)
            _require(p["promotion_index"] == index, "installed program order mismatch")
            _validate_program(p)
            _require(canonical_json_bytes(p) == data, "noncanonical installed program")
            hashes.append(canonical_json_hash(p))
        _require(sorted(hashes) == state["installed_program_hashes"] and len(set(hashes)) == len(hashes),
                 "installed program registry mismatch")
        receipt = _json(self.receipt_bytes)
        _require(canonical_json_bytes(receipt) == self.receipt_bytes
                 and canonical_json_bytes(_json(self.catalog_bytes)) == self.catalog_bytes,
                 "noncanonical bootstrap record")
        _require(_bound(receipt) == HANDOFF_RECEIPT_HASH, "unanchored bootstrap receipt")
        _require(canonical_json_hash(_json(self.catalog_bytes)) == CATALOG_HASH, "unanchored terminal catalog")
        _require(receipt["capture_report_hash"] == CAPTURE_HASH
                 and receipt["closure_report_hash"] == CLOSURE_HASH
                 and receipt["selected_campaign_hash"] == SELECTED_CAMPAIGN_HASH
                 and receipt["terminal_state_hash"] == SELECTED_STATE_HASH
                 and receipt["catalog_hash"] == canonical_json_hash(_json(self.catalog_bytes))
                 and receipt["phase17_exit_closed"] is False
                 and receipt["gate_e_closed"] is False
                 and receipt["fresh_lean_verification"] is False, "bootstrap receipt substitution")

    @property
    def state(self) -> dict:
        return _json(self.state_bytes)

    @property
    def receipt(self) -> dict:
        return _json(self.receipt_bytes)

    @property
    def catalog(self) -> dict:
        return _json(self.catalog_bytes)

    @property
    def planner_projection(self) -> tuple[tuple[int, int], ...]:
        return tuple((i, w[0]) for i, w in enumerate(struct.iter_unpack("<h", self.planner_weights)) if w[0])

    def phase16_state(self):
        """Use the real Phase 16 constructor at the integration boundary."""
        from rcp_rclm_runtime_v4.phase16.records import ModelState
        self.validate()
        obj = self.state
        del obj["schema_id"]
        return ModelState(**obj)


def reopen_phase16(*, capture_archive: Path, closure_archive: Path,
                   phase15_bundle: Path) -> HistoricalPredecessor:
    """Accept only the pinned historical archives; never regenerate a substitute."""
    with _read_pinned_archive(closure_archive, CLOSURE_SHA256) as z:
        closure_bytes = _member(z, "phase16_closure.json", 128 * 1024)
        _require(closure_bytes == _member(z, "phase16_exit.json", 128 * 1024), "exit/closure disagreement")
        closure = _json(closure_bytes)
        evidence_manifest = _json(_member(z, "manifest.json", 128 * 1024))
    _require(_bound(closure) == CLOSURE_HASH and closure["accepted"] is True
             and closure["phase16_exit_closed"] is True and closure["gate_e_closed"] is False
             and type(closure["next_phase"]) is int and closure["next_phase"] == 17,
             "historical closure boundary mismatch")
    with _read_pinned_archive(capture_archive, CAPTURE_SHA256) as z:
        capture_bytes = _member(z, "phase16_capture.json", 64 * 1024 * 1024)
        capture = _json(capture_bytes)
    _require(_bound(capture) == CAPTURE_HASH == closure["capture_report_hash"], "capture/closure mismatch")
    _require(evidence_manifest["files"]["artifacts/runtime_v4_phase16/capture/phase16_capture.json"]
             == hashlib.sha256(capture_bytes).hexdigest(), "final capture byte binding mismatch")
    for record in (closure, capture):
        _require(record["source_head"] == SOURCE_HEAD and record["source_tree"] == SOURCE_TREE
                 and record["fixed_verifier_hash"] == FIXED_VERIFIER and record["semantics_id"] == SEMANTICS,
                 "source or verifier substitution")
    _require(_bound(capture["bootstrap"]) == BOOTSTRAP_HASH == closure["bootstrap_report_hash"],
             "bootstrap report substitution")
    for report in closure["replay_reports"]:
        _bound(report)
        _require(report["accepted"] is True and report["worker_free_replay"] is True
                 and report["reconstructed_capture_hash"] == CAPTURE_HASH, "historical replay mismatch")
    _require(sorted(r["platform_id"] for r in closure["replay_reports"]) == ["macos", "ubuntu", "windows"],
             "missing historical replay platform")
    campaigns = capture["campaigns"]
    _require(len(campaigns) == 16 == capture["campaign_count"], "missing historical campaign")
    _require(sorted(_bound(c) for c in campaigns) == sorted(capture["campaign_hashes"]), "campaign list mismatch")
    all_campaigns = [*campaigns, capture["stretch_campaign"]]
    catalog = []
    for campaign in all_campaigns:
        _bound(campaign)
        state = validate_state(campaign["final_state"])
        _require(campaign["accepted"] is True and canonical_json_hash(state) == campaign["final_state_hash"],
                 "invalid terminal catalog state")
        catalog.append({key: campaign[key] for key in ("seed", "challenge_stream", "target_promotions",
                        "report_hash", "final_state_hash")})
        catalog[-1]["active_package_hash"] = state["active_package_hash"]
    catalog.sort(key=lambda c: (c["target_promotions"], c["seed"].encode("utf-8"), c["challenge_stream"].encode("utf-8")))
    _require(sum(c["accepted_promotions"] for c in all_campaigns) == 580
             and sum(c["rejected_attempts"] for c in all_campaigns) == 3752, "historical totals mismatch")
    chosen = min(campaigns, key=lambda c: (c["target_promotions"], c["seed"].encode("utf-8"),
                                          c["challenge_stream"].encode("utf-8")))
    _require(chosen["report_hash"] == SELECTED_CAMPAIGN_HASH
             and chosen["final_state_hash"] == SELECTED_STATE_HASH, "bootstrap selection drift")
    programs = validate_selected_lineage(chosen)
    with _read_pinned_archive(phase15_bundle, M9_BUNDLE_SHA256) as z:
        # Do not extract the approximately 1GB expanded evidence bundle.
        planner = _json(_member(z, M9_PREFIX + "model/phase15_planner/manifest.json", 16384))
        weights = _member(z, M9_PREFIX + "model/phase15_planner/weights.i16le.bin", 65536)
        package = _json(_member(z, M9_PREFIX + "package_manifest.json", 32768))
    _require(_bound(planner, "manifest_hash") == PLANNER_HASH
             and planner["weights_sha256"] == hashlib.sha256(weights).hexdigest() == WEIGHTS_SHA256
             and len(weights) == 65536 and package["package_hash"] == M9_PACKAGE_HASH,
             "inherited planner/package mismatch")
    catalog_obj = {"schema_id": "runtime.v5.phase17.phase16_terminal_catalog.v1",
                   "selection_policy": SELECTION_POLICY, "terminals": catalog,
                   "egc0_evaluation_performed": False}
    receipt = {
        "schema_id": SCHEMA, "accepted_for_historical_handoff": True,
        "evidence_scope": "pinned_historical_identity_and_selected_lineage_only",
        "capture_archive_sha256": CAPTURE_SHA256, "closure_archive_sha256": CLOSURE_SHA256,
        "phase15_bundle_sha256": M9_BUNDLE_SHA256,
        "capture_report_hash": CAPTURE_HASH, "closure_report_hash": CLOSURE_HASH,
        "source_head": SOURCE_HEAD, "source_tree": SOURCE_TREE,
        "selected_campaign_hash": SELECTED_CAMPAIGN_HASH, "terminal_state_hash": SELECTED_STATE_HASH,
        "active_package_hash": chosen["final_state"]["active_package_hash"],
        "selected_historical_promotions": len(programs), "catalog_terminal_count": len(catalog),
        "catalog_hash": canonical_json_hash(catalog_obj), "selection_policy": SELECTION_POLICY,
        "inherited_planner_manifest_hash": PLANNER_HASH, "inherited_planner_weights_sha256": WEIGHTS_SHA256,
        "fresh_lean_verification": False, "fresh_full_tensor_execution": False,
        "phase18_independent_replay": False, "promotion_authorized": False,
        "phase17_exit_closed": False, "gate_e_closed": False, "egc0_started": False,
    }
    receipt["report_hash"] = canonical_json_hash(receipt)
    return HistoricalPredecessor(canonical_json_bytes(chosen["final_state"]), programs,
                                 weights, canonical_json_bytes(catalog_obj), canonical_json_bytes(receipt))
