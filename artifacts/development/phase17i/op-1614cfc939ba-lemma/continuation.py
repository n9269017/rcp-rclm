"""Continue the exact Phase17I pinned-Mathlib lemma-name failure.

Preserve both failed source commits and reports. Only the new Lean template's
cardinality import/name and its corresponding renderer hash change. Full formal
validation remains mandatory; no resets, force pushes, proof-policy relaxation,
old-proof reruns, tool setup, or main/release changes are performed.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import uuid

sys.dont_write_bytecode = True
BASE = '3826d94cd3af510e9fbdc1b38a8e83071b8c0aec'
FAILED_SOURCE = 'f61af85eafb46592e6dc49c10d724f3796e2d90b'
FAILED_TREE = 'edca6a8b7c83667db4ec5a585a451b2009c7e159'
PREVIOUS_SHA = 'c8c47fef3162168347a2a5de52cba9999fab9802fe57bf89925aad266f8d28e5'
TEMPLATE = 'lean/phase17_bridge/LearnedStateBinding.lean'
RENDERER = 'python/rcp_rclm_runtime_v5/rcp_rclm_runtime_v5/phase17/learned_binding_lean.py'
OLD_TEMPLATE_SHA = '077f8d66d7185b6395bf403e7be6b4da4aee26de50cd59ddfb3acbd9cf911b47'
NEW_TEMPLATE_SHA = '2184da4d22db9d9d55f5978968f7ba4e4d769b07d22f86a81cef678cb730f8ab'
OLD_NAME = b'Finset.card_insert_of_not_mem fresh'
NEW_NAME = b'Finset.card_insert_of_notMem fresh'
MATHLIB_REV = 'fabf563a7c95a166b8d7b6efca11c8b4dc9d911f'
CARD_PATH = 'Mathlib/Data/Finset/Card.lean'
CARD_BLOB = '2fd5eac026ce27031edf88a4afb654db9716aea7'
PACKET_SHA = '6003c7a60df20dddfbf8e005160773586ab4426e13bbfb98de33e38fe961bbc3'
COMPILER_STDOUT_SHA = '0321675a2e9bd6aa6cd955ecc5273d5411a4fb2768e261c00a29aca69ed3c89c'
RUNNER = 'scripts/run_phase17_learned_binding_tests.py'
GATE_RUNNER = 'scripts/run_phase17_learned_binding_gate.py'
TEST_COUNT = 68


def need(ok, message):
    if not ok:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def no_links(path):
    for p in (path, *path.parents):
        need(not p.is_symlink() and not (hasattr(p, 'is_junction') and p.is_junction()),
             'linked path: ' + str(p))


def load_previous(path, kit):
    no_links(path.absolute());no_links(kit.absolute())
    need(path.is_file() and sha(path.read_bytes()) == PREVIOUS_SHA,
         'previous report-format continuation differs')
    spec = importlib.util.spec_from_file_location('verified_phase17i_previous', path)
    need(spec is not None and spec.loader is not None, 'cannot import verified previous helper')
    previous = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(previous)
    need(previous.BASE == BASE, 'previous helper base differs')
    a, payload = previous.load_installer(kit)
    return previous, a, payload


def corrected_template(raw):
    need(sha(raw) == OLD_TEMPLATE_SHA, 'unexpected Lean template preimage')
    need(raw.count(b'import Mathlib.Tactic\n') == 1 and raw.count(OLD_NAME) == 1,
         'unexpected import or lemma reference')
    result = raw.replace(b'import Mathlib.Tactic\n',
                         b'import Mathlib.Tactic\nimport Mathlib.Data.Finset.Card\n', 1).replace(OLD_NAME, NEW_NAME, 1)
    need(sha(result) == NEW_TEMPLATE_SHA, 'incorrect corrected template digest')
    need(result.replace(b'import Mathlib.Data.Finset.Card\n', b'', 1).replace(NEW_NAME, OLD_NAME, 1) == raw,
         'proof correction broadened')
    return result


def corrected_sources(payload):
    original = payload[RENDERER]
    need(original.count(OLD_TEMPLATE_SHA.encode()) == 1, 'unexpected renderer hash preimage')
    renderer = original.replace(OLD_TEMPLATE_SHA.encode(), NEW_TEMPLATE_SHA.encode(), 1)
    need(renderer.replace(NEW_TEMPLATE_SHA.encode(), OLD_TEMPLATE_SHA.encode(), 1) == original,
         'renderer implementation changed beyond template hash')
    compile(renderer, RENDERER, 'exec')
    return {TEMPLATE: corrected_template(payload[TEMPLATE]), RENDERER: renderer}


def verify_current_source(previous, a, stage, payload):
    a.clean(stage)
    need(Path(a.text(stage, 'rev-parse', '--show-toplevel')).resolve() == stage, 'wrong failed checkout root')
    need(a.text(stage, 'rev-parse', 'HEAD') == FAILED_SOURCE and
         a.text(stage, 'rev-parse', 'HEAD^{tree}') == FAILED_TREE, 'failed source/tree changed')
    need(a.text(stage, 'rev-list', '--parents', '-n', '1', FAILED_SOURCE).split() ==
         [FAILED_SOURCE, previous.FAILED_SOURCE], 'failed source ancestry changed')
    expected = dict(payload);expected.update(previous.corrected_sources(payload))
    changed = {n.decode('utf-8') for n in a.git(stage, 'diff', '--name-only', '-z', BASE, FAILED_SOURCE).split(b'\0') if n}
    need(changed == set(payload) | {'SHA256SUMS.txt'}, 'failed source surface changed')
    for name, raw in expected.items():
        need(a.git(stage, 'cat-file', 'blob', FAILED_SOURCE + ':' + name) == raw and
             a.safe(stage, name).read_bytes() == raw, 'failed source bytes changed: ' + name)
    need(sha(a.safe(stage, previous.H_REPORT).read_bytes()) == a.H_HASH, 'historical report changed')


def check_manifest(a, folder, expected):
    files = {}
    for p in folder.iterdir():
        a.no_links(p)
        if p.is_file() and p.name != 'SHA256SUMS.txt':
            files[p.name] = p.read_bytes()
        elif p.is_dir():
            need(p.name in ('p', 'c'), 'unexpected directory in gate evidence')
    need(set(files) == set(expected), 'unexpected gate evidence inventory')
    wanted = ''.join(sha(raw) + '  ' + n + '\n' for n, raw in sorted(files.items())).encode('utf-8')
    need((folder / 'SHA256SUMS.txt').read_bytes() == wanted, 'gate evidence checksum mismatch')
    return files


def inspect_current_failure(previous, a, run, tools, payload):
    read = previous.read_json
    progress = read(run / 'progress.json')
    need(progress.get('stage') == 'stopped' and progress.get('base') == BASE and
         progress.get('original_checkout_changed') is False and progress.get('pushed') is False and
         progress.get('tested_code_commit') == FAILED_SOURCE and
         progress.get('previous_failed_source') == previous.FAILED_SOURCE, 'unexpected failed recovery state')
    out = run / 'e'
    tests = previous.retained_command(a, out, 'new-tests', RUNNER, TEST_COUNT)
    command = previous.retained_command(a, out, 'typed-binding-gate', GATE_RUNNER)
    argv = command['argv']
    need(type(command.get('returncode')) is int and command['returncode'] == 2 and len(argv) == 8 and
         argv[2:5] == ['--test-fixture', '--require-lean', '--lean-workspace'] and argv[6] == '--output' and
         Path(argv[5]).resolve() == (tools / 'formal-root').resolve() and
         Path(argv[7]).resolve() == (out / 'gate').resolve(), 'unexpected failed gate invocation')
    report = read(out / 'gate/execution.json')
    need(report.get('schema') == 'rcp-rclm.phase17i.typed-learned-binding-run.v1' and
         report.get('source_commit') == FAILED_SOURCE and report.get('source_tree') == FAILED_TREE and
         report.get('synthetic_fixture') is True and report.get('local_increment_checks_passed') is False and
         type(report.get('automatic_retries')) is int and report['automatic_retries'] == 0 and
         report.get('failure') == {'type': 'ControlError', 'reason': 'new typed learned-state gate failed'},
         'not the recorded typed-binding proof failure')
    need(set(report['claims']) == set(a.FALSE_KEYS) and all(v is False for v in report['claims'].values()),
         'failed execution overclaims success')
    need(read(out / 'typed-binding-gate.out.txt') == report and not (out / 'typed-binding-gate.err.txt').read_bytes(),
         'failed gate logs disagree with execution record')
    gate = report['typed_binding_gate']
    need(gate['status'] == 'rejected' and gate['theorem_axioms'] == {} and
         gate['typed_learned_state_binding_checked'] is False and
         gate['fixed_interpretation_preservation_checked'] is False and
         gate['negative_component_substitution_rejected'] is False and
         gate['packet_sha256'] == report['packet_sha256'] == PACKET_SHA and
         gate['failure'] == {'type': 'ControlError', 'reason': 'typed learned binding rejected'},
         'unexpected formal failure boundary')
    need(set(gate['claims']) == set(a.FALSE_KEYS) and all(v is False for v in gate['claims'].values()),
         'failed gate overclaims success')
    commands = gate['commands']
    need(len(commands) == 2 and [c.get('returncode') for c in commands] == [0, 1] and
         all(type(c['returncode']) is int for c in commands), 'unexpected compiler sequence')
    for c in commands:
        for stream in ('stdout', 'stderr'):
            need(type(c[stream]) is str and sha(c[stream].encode('utf-8')) == c[stream + '_sha256'],
                 'compiler log digest changed')
    need(not commands[0]['stderr'] and re.match(r'^Lean \(version 4\.31\.0(?:,|\))', commands[0]['stdout']),
         'wrong compiler version')
    compiler = commands[1]
    need(not compiler['stderr'] and compiler['stdout_sha256'] == COMPILER_STDOUT_SHA and
         'Unknown constant `Finset.card_insert_of_not_mem`' in compiler['stdout'] and
         "'Phase17LearnedBinding.frontier_grows' depends on axioms: [propext, sorryAx, Quot.sound]" in compiler['stdout'],
         'not the exact recorded lemma-name error')
    need(report['named_audits'] == list(a.NAMES) and report['operational_packet_sha256'] == a.H_PACKET and
         report['reused_phase17h']['retained_report_sha256'] == a.H_HASH and
         report['reused_phase17h']['proofs_retained_not_rerun'] == 172 and report['prior_proofs_rerun'] is False,
         'retained proof boundary differs')
    files = check_manifest(a, out / 'gate', {'execution.json', 'packet.json', 'operational_packet.json',
                                            'Binding.lean', 'ChangedComponent.lean'})
    for name, original in [('packet.json', 'prepared-packet.json'), ('Binding.lean', 'prepared-Binding.lean'),
                           ('ChangedComponent.lean', 'prepared-ChangedComponent.lean')]:
        need(files[name] == payload['artifacts/development/phase17i/' + original], 'original prepared evidence changed: ' + name)
    need(sha(files['packet.json']) == PACKET_SHA and sha(files['operational_packet.json']) == a.H_PACKET,
         'original packet bytes mismatch')
    expected = {label + suffix for label in ('clone-preserved-source', 'retained-manifest', 'new-tests', 'typed-binding-gate')
                for suffix in ('.json', '.out.txt', '.err.txt')} | {'gate/' + n for n in files} | {'gate/SHA256SUMS.txt'}
    need(set(a.retained_files(out)) == expected, 'unexpected failed continuation evidence surface')
    for label in ('clone-preserved-source', 'retained-manifest'):
        r = read(out / (label + '.json'))
        need(r.get('returncode') == 0 and r.get('problem') is None, 'earlier preflight command failed')
        for stream, suffix in [('stdout', '.out.txt'), ('stderr', '.err.txt')]:
            need(r[stream + '_sha256'] == sha((out / (label + suffix)).read_bytes()), 'preflight log changed')
    return dict(source_commit=FAILED_SOURCE, source_tree=FAILED_TREE, retained_new_tests=68,
                retained_tests_command=tests, failed_gate_command=command,
                failure=gate['failure'], execution_sha256=sha(files['execution.json']),
                compiler_stdout_sha256=COMPILER_STDOUT_SHA, original_failure_relabelled_as_success=False)


def verify_pinned_lemma(a, tools):
    root = tools / 'formal-root/lean/rcp_rclm_formal_core_v4/.lake/packages/mathlib'
    a.no_links(root);a.no_links(root / CARD_PATH)
    need(root.is_dir() and a.text(root, 'rev-parse', 'HEAD') == MATHLIB_REV, 'wrong prepared Mathlib revision')
    need(a.text(root, 'rev-parse', 'HEAD:' + CARD_PATH) == CARD_BLOB, 'wrong pinned cardinality module')
    raw = a.git(root, 'cat-file', 'blob', CARD_BLOB)
    need((root / CARD_PATH).read_bytes().replace(b'\r\n', b'\n') == raw,
         'cardinality source differs from pinned Git blob')
    need(b'theorem card_insert_of_notMem (h : a \xe2\x88\x89 s)' in raw and
         b'theorem card_insert_of_not_mem ' not in raw, 'unexpected pinned lemma declaration')
    return dict(mathlib_revision=MATHLIB_REV, source_path=CARD_PATH, git_blob=CARD_BLOB,
                source_sha256=sha(raw), theorem='Finset.card_insert_of_notMem', source_only_check=True,
                compiler_execution=False)


def verify_new_artifacts(a, out, payload, execution):
    files = check_manifest(a, out / 'gate', {'execution.json', 'packet.json', 'operational_packet.json',
                                            'Binding.lean', 'ChangedComponent.lean'})
    prefix = 'artifacts/development/phase17i/'
    need(files['packet.json'] == payload[prefix + 'prepared-packet.json'] and
         sha(files['packet.json']) == execution['packet_sha256'] == PACKET_SHA and
         sha(files['operational_packet.json']) == a.H_PACKET, 'candidate facts changed')
    before = payload[TEMPLATE];after = corrected_template(before)
    for name, original, field in [('Binding.lean', 'prepared-Binding.lean', 'positive_source_sha256'),
                                  ('ChangedComponent.lean', 'prepared-ChangedComponent.lean', 'negative_source_sha256')]:
        old = payload[prefix + original]
        need(old.startswith(before) and old.count(before) == 1, 'unexpected original proof prefix')
        need(files[name] == after + old[len(before):], 'certificate changed beyond exact template correction')
        need(sha(files[name]) == execution['typed_binding_gate'][field], 'new proof/report hash mismatch')


def copy_failure(a, destination, source, metadata):
    destination.mkdir()
    for name, raw in a.retained_files(source / 'e').items():
        p = a.safe(destination, 'e/' + name);p.parent.mkdir(parents=True, exist_ok=True);p.write_bytes(raw)
    (destination / 'progress.json').write_bytes((source / 'progress.json').read_bytes())
    a.write(destination / 'retention.json', metadata)


def retain_evidence(previous, a, stage, out, source, tree, commands, original, failed,
                    original_metadata, failed_metadata, payload, lemma):
    execution = previous.read_json(out / 'gate/execution.json')
    a.validate_execution(execution, source, tree);verify_new_artifacts(a, out, payload, execution)
    copy_failure(a, out / 'prior-format-failure', original, original_metadata)
    copy_failure(a, out / 'prior-lemma-failure', failed, failed_metadata)
    helper = Path(__file__).read_bytes();(out / 'continuation.py').write_bytes(helper)
    operator = dict(schema='rcp-rclm.phase17i.pinned-lemma-recovery.v1', source_commit=source, source_tree=tree,
        commands=commands, new_tests=TEST_COUNT, prior_successful_68_tests_source=FAILED_SOURCE,
        operational_regressions_retained_not_rerun=57, operational_regression_source=previous.FAILED_SOURCE,
        prior_format_failure=original_metadata, prior_lemma_failure=failed_metadata,
        pinned_lemma_source_check=lemma, retained_phase17h=execution['reused_phase17h'],
        synthetic_fixture=True, new_named_audits=8, new_proofs_kernel_executed=True,
        prior_history_bytes_rewritten=False, both_failures_preserved=True,
        candidate_facts_changed=False, theorem_statements_changed=False,
        acceptance_functions_changed=False, immutable_root_changed=False,
        template_correction='explicit pinned cardinality import and card_insert_of_notMem reference',
        old_template_sha256=OLD_TEMPLATE_SHA, new_template_sha256=NEW_TEMPLATE_SHA,
        continuation_sha256=sha(helper), gate_execution_sha256=sha((out / 'gate/execution.json').read_bytes()),
        github_hosted_ci_passed=False, cross_platform_validation=False, automatic_retries=0,
        network_setup_requested=False, root_admission=execution['root_admission'],
        **{k: False for k in a.FALSE_KEYS})
    a.write(out / 'operator-validation.json', operator)
    files = a.retained_files(out);files['.gitattributes'] = b'* -text\n'
    files['SHA256SUMS.txt'] = ''.join(sha(raw) + '  ' + n + '\n' for n, raw in sorted(files.items())).encode()
    rel = a.EVIDENCE + '/op-' + source[:12] + '-lemma'
    for name, raw in files.items():
        p = a.safe(stage, rel + '/' + name);p.parent.mkdir(parents=True, exist_ok=True);p.write_bytes(raw)
    status = previous.read_json(stage / a.STATUS);status['stage'] = 'phase17i_typed_learned_binding'
    status['evidence_records']['phase17i_operator_capture'] = rel + '/operator-validation.json'
    status['implemented_scope'].update(typed_learned_package_state_projection=True,
        anchored_operational_evidence_composition=True, conditional_root_information_binding=True,
        complete_recursive_productivity_recertification=False, root_transition_certificate_integration=False)
    status['validation'].update(phase17i_tested_code_commit=source, phase17i_new_tests=68,
        phase17i_operational_regressions_retained_not_rerun=57,
        phase17i_operational_regression_source=previous.FAILED_SOURCE, phase17i_new_formal_audits=8,
        phase17i_synthetic_fixture=True, phase17i_phase17h_proofs_retained=172,
        phase17i_root_admission='blocked_missing_semantic_witnesses', phase17i_full_root_evaluated=False,
        phase17i_new_recursive_tasks_closed=[], phase17i_preserved_failed_sources=[previous.FAILED_SOURCE, FAILED_SOURCE],
        phase17i_report_format_correction='strict formatted report after exact raw-byte digest; canonical packets unchanged',
        phase17i_lemma_correction='pinned Mathlib card_insert_of_notMem; unchanged theorem statement',
        phase17i_local='typed binding gate passed; not complete learned/root acceptance')
    a.write(stage / a.STATUS, status)
    add = {rel + '/' + n for n in files} | {a.STATUS};a.stage_exact(stage, add)
    for name, raw in files.items():
        need(a.git(stage, 'cat-file', 'blob', ':' + rel + '/' + name) == raw, 'evidence staging changed bytes')
    a.refresh(stage);need(a.staged(stage) == add | {'SHA256SUMS.txt'}, 'unexpected evidence-only changes')
    a.git(stage, 'commit', '-m', 'Retain Phase17I pinned lemma proof recovery and both failures [skip ci]');a.clean(stage)
    return a.text(stage, 'rev-parse', 'HEAD'), rel


def execute(previous, a, payload, args):
    for p in (args.repo, args.kit, args.tools, args.failed_run, args.original_failed_run, args.work_root):
        a.no_links(p.absolute())
    repo, kit, tools, failed, original, work = [p.resolve() for p in
        (args.repo, args.kit, args.tools, args.failed_run, args.original_failed_run, args.work_root)]
    for p in (kit, tools, failed, original, work):
        need(p != repo and repo not in p.parents and p not in repo.parents, 'repository overlaps input/work directory')
    need(failed != original and failed not in original.parents and original not in failed.parents, 'failure directories overlap')
    for p in (tools, kit):
        need(work != p and work not in p.parents and p not in work.parents, 'work overlaps kit/tools')
    a.clean(repo)
    need(Path(a.text(repo, 'rev-parse', '--show-toplevel')).resolve() == repo and
         a.text(repo, 'branch', '--show-current') == a.BRANCH and a.text(repo, 'rev-parse', 'HEAD') == BASE,
         'original checkout is not at expected clean development head')
    need(a.text(repo, 'remote', 'get-url', 'origin') in a.ORIGINS and
         a.text(repo, 'remote', 'get-url', '--push', 'origin') in a.ORIGINS and a.remote_head(repo) == BASE,
         'remote differs or moved')
    previous.verify_failed_source(a, original / 'c', payload)
    original_metadata = previous.inspect_failure(a, original, tools)
    verify_current_source(previous, a, failed / 'c', payload)
    failed_metadata = inspect_current_failure(previous, a, failed, tools, payload)
    lemma = verify_pinned_lemma(a, tools)
    snapshots = [(p, previous.prior_snapshot(a, p)) for p in (original, failed)]
    fixed = corrected_sources(payload)
    author = a.text(repo, 'config', 'user.name');email = a.text(repo, 'config', 'user.email')
    need(author and email, 'Git author missing')
    work.mkdir(parents=True, exist_ok=True);run = work / ('il-' + uuid.uuid4().hex[:8]);run.mkdir()
    stage = run / 'c';out = run / 'e';out.mkdir();hooks = run / 'h';hooks.mkdir()
    progress = dict(base=BASE, stage='created', original_checkout_changed=False, pushed=False,
                    previous_failed_source=FAILED_SOURCE, original_failed_source=previous.FAILED_SOURCE)
    a.write(run / 'progress.json', progress)
    print('Phase17I pinned-lemma continuation workspace: ' + str(run), flush=True)
    try:
        a.run_command(repo, out, 'clone-preserved-source', ['git', '-c', 'core.longpaths=true', 'clone',
            '--no-hardlinks', '--no-checkout', '--local', str(failed / 'c'), str(stage)])
        for key, value in [('core.autocrlf', 'false'), ('core.longpaths', 'true'), ('core.hooksPath', str(hooks)),
                           ('user.name', author), ('user.email', email)]:
            a.git(stage, 'config', key, value)
        a.git(stage, 'checkout', '--detach', FAILED_SOURCE);a.clean(stage)
        a.run_command(stage, out, 'retained-manifest', [sys.executable, 'scripts/phase17_refresh_checksums.py'])
        for name, raw in fixed.items():a.safe(stage, name).write_bytes(raw)
        a.stage_exact(stage, fixed)
        for name, raw in fixed.items():
            need(a.git(stage, 'cat-file', 'blob', ':' + name) == raw, 'repair staging conversion')
        a.refresh(stage);need(a.staged(stage) == set(fixed) | {'SHA256SUMS.txt'}, 'unexpected proof repair diff')
        a.git(stage, 'commit', '-m', 'Use pinned Mathlib cardinality lemma in Phase17I binding proof [skip ci]')
        source = a.text(stage, 'rev-parse', 'HEAD');tree = a.text(stage, 'rev-parse', 'HEAD^{tree}');a.clean(stage)
        progress.update(stage='source_committed', tested_code_commit=source);a.write(run / 'progress.json', progress)
        commands = [a.run_command(stage, out, 'new-tests', [sys.executable, RUNNER], TEST_COUNT)]
        print('Prior 57 operational regressions and 172 Phase17H proofs retained; not rerun.', flush=True)
        print('Checking corrected eight-audit certificate and changed-component rejection; no live campaign.', flush=True)
        try:
            commands.append(a.run_command(stage, out, 'typed-binding-gate', [sys.executable, GATE_RUNNER,
                '--test-fixture', '--require-lean', '--lean-workspace', str(tools / 'formal-root'),
                '--output', str(out / 'gate')], timeout=12000))
        except Exception:
            p = out / 'gate/execution.json'
            if p.is_file():
                failure = previous.read_json(p)
                print(json.dumps({k: failure[k] for k in ('source_commit', 'failure', 'typed_binding_gate') if k in failure},
                                 indent=2), flush=True)
            raise
        a.clean(stage);need(a.text(stage, 'rev-parse', 'HEAD') == source, 'tested source moved')
        need(verify_pinned_lemma(a, tools) == lemma, 'pinned Mathlib source changed')
        for p, old in snapshots:need(previous.prior_snapshot(a, p) == old, 'prior evidence changed')
        previous.verify_failed_source(a, original / 'c', payload)
        verify_current_source(previous, a, failed / 'c', payload)
        head, rel = retain_evidence(previous, a, stage, out, source, tree, commands, original, failed,
                                   original_metadata, failed_metadata, payload, lemma)
        for p, old in snapshots:need(previous.prior_snapshot(a, p) == old, 'prior evidence changed during retention')
        previous.verify_failed_source(a, original / 'c', payload)
        verify_current_source(previous, a, failed / 'c', payload)
        pr = run / 'PR_UPDATE.md'
        pr.write_text(f'''## Phase 17A-I development - keep draft and unmerged

Tested source `{source}`; evidence head `{head}`.
Preserved failures: original report parser `{previous.FAILED_SOURCE}` and
pinned-Mathlib lemma name `{FAILED_SOURCE}`. Neither failure is relabeled as success.

68 binding/parser/control tests freshly passed. The prior 57 Phase17H operational
regressions remain attributed to `{previous.FAILED_SOURCE}` and were not rerun.
The original strict formatted-report correction is retained. This correction only
imports the pinned Finset cardinality module, uses card_insert_of_notMem, and updates
the new template's integrity hash. No theorem statement, candidate fact, immutable
root, acceptance function, permitted-axiom policy, or dependency revision changed.

Actual pinned Lean accepted all eight new typed-binding named audits and rejected
the changed-component certificate. Phase17H's 172 proofs were retained only for
identical freshly recomputed operational evidence, not rerun. The candidate remains
synthetic. Full root admission stays blocked_missing_semantic_witnesses; the
conditional semantic binding and trusted byte/literal/import-cache boundaries remain.

No full root transition, recursive-productivity/frontier closure, full learned
refinement, decoder proof, complete resource accounting, live gain, promotion,
Phase17/Gate E closure, EGC-0, main merge, release/DOI change, or hosted CI is claimed.

Evidence: `{rel}/operator-validation.json`.
''', encoding='utf-8')
        progress.update(stage='validated', evidence_head=head);a.write(run / 'progress.json', progress)
        a.advance(repo, stage, head, hooks, progress, run, args.push)
        progress['stage'] = 'complete';a.write(run / 'progress.json', progress)
        print(json.dumps(dict(completed=True, tested_code_head=source, evidence_head=head, pushed=progress['pushed'],
            preserved_failed_sources=[previous.FAILED_SOURCE, FAILED_SOURCE], new_tests=68,
            operational_regressions_retained_not_rerun=57, new_named_audits=8,
            typed_learned_gate_status='passed', retained_operational_proofs_not_rerun=172,
            synthetic_fixture=True, candidate_facts_changed=False, theorem_statements_changed=False,
            pr_description_file=str(pr), pr68_keep_draft=True,
            full_root_assessment='blocked_missing_semantic_witnesses', **{k:False for k in a.FALSE_KEYS}), indent=2), flush=True)
        return 0
    except Exception:
        progress['stage'] = 'stopped';a.write(run / 'progress.json', progress)
        print('Stopped; workspace and logs retained: ' + str(run), file=sys.stderr)
        print('Original checkout advanced: ' + str(progress['original_checkout_changed']), file=sys.stderr)
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('repo', 'kit', 'tools', 'failed-run', 'original-failed-run', 'previous-resume'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--work-root', type=Path, default=Path.home() / '.r17')
    parser.add_argument('--push', action='store_true')
    args = parser.parse_args(argv)
    previous, a, payload = load_previous(args.previous_resume, args.kit)
    return execute(previous, a, payload, args)


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, OSError, KeyError, subprocess.SubprocessError) as exc:
        print(type(exc).__name__ + ': ' + str(exc), file=sys.stderr)
        raise SystemExit(2)
