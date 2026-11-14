"""AE source factoring and exact formal-evidence refusal controls.

Synthetic compiler messages below exercise parsers only. They cannot create a
formal acceptance result and do not replace the real pinned Lean application.
"""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from rcp_rclm_runtime_v5.phase17 import task_interpretation_check as check
from rcp_rclm_runtime_v5.phase17 import task_interpretation_lean as formal


ROOT = Path(__file__).resolve().parents[3]
FALSE_SOURCE = b'''-- CONTROLLED PARSER INPUT; NOT A PROOF RESULT
def wrongClaim : Bool := false
theorem actual_rejection : wrongClaim = false := by decide
example : wrongClaim = true := by
  simp only [actual_rejection, Bool.false_eq_true]
  decide
'''


def audit_text():
    return ''.join("'" + name + "' depends on axioms: [propext, Classical.choice, Quot.sound]\n"
                   for name in formal.NAMES)


def negative_text(label):
    line, column = formal.negative_location(FALSE_SOURCE)
    return (label + '.lean:' + str(line) + ':' + str(column) +
            ': error: Tactic `decide` proved that the proposition\n  False\nis false\n')


class FormalEvidenceTests(unittest.TestCase):
    def test_inherited_template_pins_match_actual_files(self):
        for name, expected in formal.PINS.items():
            self.assertEqual(formal.sha(formal._read(ROOT, name)), expected)

    def test_generic_module_preserves_every_original_body_once(self):
        source = formal.generic_finite_module(ROOT).decode()
        for name in formal.GENERIC_BODIES:
            _, body = formal._split_imports(formal._read(ROOT, name))
            self.assertEqual(source.count(body), 1)
        _, provenance = formal._split_imports(formal._read(ROOT, 'ProposalProvenance'))
        self.assertNotIn(provenance, source)
        self.assertTrue(source.startswith('import ProposalProvenance\n'))

    def test_changed_inherited_template_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / 'lean/phase17_bridge/ProposalProvenance.lean'
            target.parent.mkdir(parents=True)
            target.write_bytes(formal._read(ROOT, 'ProposalProvenance') + b'\n')
            with self.assertRaisesRegex(ValueError, 'template changed'):
                formal._read(root, 'ProposalProvenance')

    def test_embedded_import_cannot_escape_factoring(self):
        with self.assertRaisesRegex(ValueError, 'embedded template import'):
            formal._split_imports(b'import Mathlib\nnamespace X\nimport Forged\n')

    def test_audit_names_are_distinct_and_include_preservation_and_guard(self):
        self.assertEqual(len(formal.NAMES), len(set(formal.NAMES)))
        for name in ('Phase17TaskInterpretation.catalog_legacy_preserved',
                     'Phase17TaskInterpretation.catalog_complete',
                     'Phase17TaskInterpretation.accepted_semantic_gain',
                     'Phase17TaskInterpretation.already_solved_rejected',
                     'Phase17TaskInterpretationExamples.selected_first_accepted',
                     'Phase17TaskInterpretationExamples.selected_existing_behavior_rejected'):
            self.assertIn(name, formal.NAMES)

    def test_exact_approved_audits_parse(self):
        self.assertEqual(list(formal.parse_audits(audit_text())), list(formal.NAMES))

    def test_axiom_free_audit_allowed(self):
        text = audit_text().replace('depends on axioms: [propext, Classical.choice, Quot.sound]',
                                    'does not depend on any axioms', 1)
        self.assertEqual(formal.parse_audits(text)[formal.NAMES[0]], [])

    def test_missing_audit_rejected(self):
        with self.assertRaises(ValueError):
            formal.parse_audits('\n'.join(audit_text().splitlines()[1:]) + '\n')

    def test_reordered_audits_rejected(self):
        lines = audit_text().splitlines()
        lines[0], lines[1] = lines[1], lines[0]
        with self.assertRaises(ValueError):
            formal.parse_audits('\n'.join(lines) + '\n')

    def test_extra_compiler_output_rejected(self):
        with self.assertRaises(ValueError):
            formal.parse_audits(audit_text() + 'warning: unrelated\n')

    def test_unapproved_axiom_rejected(self):
        with self.assertRaises(ValueError):
            formal.parse_audits(audit_text().replace('propext', 'sorryAx', 1))

    def test_repeated_axiom_rejected(self):
        with self.assertRaises(ValueError):
            formal.parse_audits(audit_text().replace('propext,', 'propext, propext,', 1))

    def test_exact_designated_rejection_parses(self):
        for label in formal.NEGATIVES:
            formal.validate_negative(label, FALSE_SOURCE, negative_text(label), '', 1)

    def test_negative_compiler_success_rejected(self):
        with self.assertRaises(ValueError):
            formal.validate_negative(formal.NEGATIVES[0], FALSE_SOURCE, '', '', 0)

    def test_negative_import_error_rejected(self):
        with self.assertRaises(ValueError):
            formal.validate_negative(formal.NEGATIVES[0], FALSE_SOURCE,
                                     'error: unknown module prefix\n', '', 1)

    def test_negative_wrong_line_rejected(self):
        label = formal.NEGATIVES[0]
        with self.assertRaises(ValueError):
            formal.validate_negative(label, FALSE_SOURCE,
                                     negative_text(label).replace('.lean:6:2', '.lean:1:2'), '', 1)

    def test_negative_extra_diagnostic_rejected(self):
        label = formal.NEGATIVES[0]
        with self.assertRaises(ValueError):
            formal.validate_negative(label, FALSE_SOURCE, negative_text(label) + 'error: other\n', '', 1)

    def test_negative_stderr_rejected(self):
        label = formal.NEGATIVES[0]
        with self.assertRaises(ValueError):
            formal.validate_negative(label, FALSE_SOURCE, negative_text(label), 'signal', 1)

    def test_negative_boolean_returncode_rejected(self):
        label = formal.NEGATIVES[0]
        with self.assertRaises(ValueError):
            formal.validate_negative(label, FALSE_SOURCE, negative_text(label), '', True)

    def test_unknown_negative_label_rejected(self):
        with self.assertRaises(ValueError):
            formal.validate_negative('Unknown', FALSE_SOURCE, negative_text('Unknown'), '', 1)

    def test_missing_designated_assertion_rejected(self):
        with self.assertRaises(ValueError):
            formal.negative_location(FALSE_SOURCE.replace(b'example : wrongClaim', b'example : otherClaim'))

    def test_new_gate_and_document_are_source_bound(self):
        names = check.source_paths(ROOT)
        self.assertIn('scripts/run_phase17_task_interpretation_gate.py', names)
        self.assertIn('docs/executable_core_v5/PHASE_17_TASK_INTERPRETATION.md', names)
        self.assertIn('python/rcp_rclm_runtime_v5/tests_phase17ae/test_task_interpretation_check.py', names)
        self.assertEqual(len(names), len(set(names)))

    def test_import_resolution_requires_current_object_path(self):
        label = formal.MODULES[-1]
        record = {'returncode': 0, 'stderr': '',
                  'stdout': '/tool/Init.olean\n/old/' + label + '.olean\n/tool/Init.olean\n'}
        with self.assertRaisesRegex(ValueError, 'restored compiled artifact'):
            check._resolve(record, label, '/current', '/tool/Init.olean')

    def test_import_resolution_checks_init_identity(self):
        label = formal.MODULES[-1]
        record = {'returncode': 0, 'stderr': '',
                  'stdout': '/other/Init.olean\n/current/' + label + '.olean\n/tool/Init.olean\n'}
        with self.assertRaisesRegex(ValueError, 'another Init'):
            check._resolve(record, label, '/current', '/tool/Init.olean')

    def test_import_resolution_rejects_unknown_module(self):
        record = {'returncode': 0, 'stderr': '',
                  'stdout': '/tool/Init.olean\n/current/Unknown.olean\n/tool/Init.olean\n'}
        with self.assertRaises(ValueError):
            check._resolve(record, 'Unknown', '/current', '/tool/Init.olean')


if __name__ == '__main__':
    unittest.main()
