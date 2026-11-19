"""Selected SHA-256 arithmetic, complete traces and retained-input boundaries.

Known-answer and hashlib comparisons are runtime tests, not Lean certificates.
One integration test reconstructs the inherited fixture; no campaigns are run.
"""
from __future__ import annotations

import copy
from dataclasses import FrozenInstanceError
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

from rcp_rclm_runtime_v5.phase17 import producer_sha256 as p

ROOT = Path(__file__).resolve().parents[3]


@lru_cache(maxsize=1)
def _w():
    raw = (ROOT / p.W_PACKET).read_bytes()
    if p.sha(raw) != p.W_PACKET_SHA:
        raise AssertionError('retained W fixture identity changed')
    return p.load_json_strict(raw)


@lru_cache(maxsize=1)
def _records():
    return p.selected_records(_w())


@lru_cache(maxsize=1)
def _fixture_bytes():
    w = _w()
    return p.canonical({'schema': p.SCHEMA, 'policy': p.POLICY, 'base_commit': p.BASE,
        'producer_preimages_packet': w, 'producer_preimages_packet_sha256': p.W_PACKET_SHA,
        'bindings': w['bindings'], 'retained_w': dict(p.RETAINED_W_PINS),
        'profile': copy.deepcopy(p.PROFILE), 'scope': copy.deepcopy(p.SCOPE),
        'claims': {name: False for name in p.FALSE_CLAIMS}, 'hash_records': _records()})


@lru_cache(maxsize=1)
def _packet_template():
    return p.load_json_strict(_fixture_bytes())


def _packet():
    return copy.deepcopy(_packet_template())


@lru_cache(maxsize=1)
def _prepared():
    return p.PreparedProducerSha256(_fixture_bytes())


class Sha256ArithmeticTests(unittest.TestCase):
    def test_empty_known_answer(self):
        self.assertEqual(p.sha256_hex(b''),
            'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855')

    def test_abc_known_answer(self):
        self.assertEqual(p.sha256_hex(b'abc'),
            'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad')

    def test_two_block_known_answer(self):
        self.assertEqual(p.sha256_hex(b'abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq'),
            '248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1')

    def test_long_known_answer(self):
        raw=(b'abcdefghbcdefghicdefghijdefghijkefghijklfghijklmghijklmn'
             b'hijklmnoijklmnopjklmnopqklmnopqrlmnopqrsmnopqrstnopqrstu')
        self.assertEqual(p.sha256_hex(raw),
            'cf5b16a778af8380036ce59e7b0492370b249b11e8f07a51afac45037afee9d1')

    def test_all_padding_boundaries_match_independent_library(self):
        for n in (0,1,2,3,7,31,32,55,56,57,63,64,65,119,120,127,128,129,255,256,257,1024):
            raw=bytes((17*i+91)%256 for i in range(n))
            with self.subTest(length=n): self.assertEqual(p.sha256_bytes(raw),hashlib.sha256(raw).digest())

    def test_all_byte_values_and_high_bits_match_library(self):
        for raw in (bytes(range(256)),b'\xff'*64,b'\x80'*127,b'\0'*1000,bytes(reversed(range(256)))):
            self.assertEqual(p.sha256_hex(raw),hashlib.sha256(raw).hexdigest())

    def test_complete_supported_input_bound_matches_library(self):
        raw=b'\xa5'*p.MAX_IMAGE_BYTES
        self.assertEqual(p.sha256_hex(raw),hashlib.sha256(raw).hexdigest())

    def test_reference_does_not_call_library_hashes(self):
        with patch.object(hashlib,'sha256',side_effect=AssertionError('reference used hashlib')), \
             patch.object(p,'sha',side_effect=AssertionError('reference used production hash')):
            self.assertEqual(p.sha256_hex(b'abc'),
                'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad')

    def test_immutable_byte_input_required(self):
        for value in ('abc',bytearray(b'abc'),memoryview(b'abc'),[97,98,99],None,True):
            with self.subTest(kind=type(value)),self.assertRaises(ValueError): p.sha256_hex(value)

    def test_oversized_input_rejected_before_padding(self):
        with self.assertRaises(ValueError): p.pad_message(bytes(p.MAX_IMAGE_BYTES+1))

    def test_empty_padding_includes_one_bit_and64bit_length(self):
        self.assertEqual(p.pad_message(b''),b'\x80'+bytes(63))

    def test_abc_padding_has_big_endian_bit_length(self):
        raw=p.pad_message(b'abc')
        self.assertEqual(raw,b'abc\x80'+bytes(52)+b'\0'*7+b'\x18')
        self.assertEqual(len(raw),64)

    def test_padding_transition_at56bytes(self):
        self.assertEqual(len(p.pad_message(b'x'*55)),64)
        self.assertEqual(len(p.pad_message(b'x'*56)),128)
        self.assertEqual(p.pad_message(b'x'*56)[56],128)
        self.assertEqual(p.pad_message(b'x'*56)[-8:],(56*8).to_bytes(8,'big'))

    def test_complete_blocks_still_receive_padding(self):
        raw=b'y'*64
        self.assertEqual(len(p.pad_message(raw)),128)
        self.assertEqual(p.pad_message(raw)[64],128)
        self.assertEqual(p.pad_message(raw)[-8:],b'\0'*6+b'\x02\0')

    def test_rotations_wrap_high_bits_and_preserve32bit_range(self):
        self.assertEqual(p.rotate_right(1,1),0x80000000)
        self.assertEqual(p.rotate_right(0x80000000,31),1)
        self.assertEqual(p.rotate_right(0x12345678,8),0x78123456)
        self.assertEqual(p.rotate_right(0xffffffff,17),0xffffffff)
        self.assertEqual(p.rotate_right(0x87654321,0),0x87654321)

    def test_rotation_operands_are_exact_bounded_integers(self):
        for word,count in ((-1,1),(1<<32,1),(True,1),(1.0,1),(1,-1),(1,32),(1,True)):
            with self.assertRaises(ValueError): p.rotate_right(word,count)

    def test_schedule_parses_all16_big_endian_words(self):
        raw=bytes(range(64));schedule=p.message_schedule(raw)
        self.assertEqual(len(schedule),64)
        self.assertEqual(schedule[:16],tuple(int.from_bytes(raw[i:i+4],'big') for i in range(0,64,4)))
        self.assertTrue(all(type(w) is int and 0<=w<1<<32 for w in schedule))

    def test_schedule_complete_block_required(self):
        for raw in (b'',bytes(63),bytes(65),bytearray(64),'a'*64):
            with self.assertRaises(ValueError): p.message_schedule(raw)

    def test_initial_state_has_exact_fips_words(self):
        self.assertEqual(''.join(f'{w:08x}' for w in p.INITIAL_STATE),
                         '6a09e667bb67ae853c6ef372a54ff53a510e527f9b05688c1f83d9ab5be0cd19')
        self.assertEqual(len(p.ROUND_CONSTANTS),64)
        self.assertEqual(p.ROUND_CONSTANTS[0],0x428a2f98)
        self.assertEqual(p.ROUND_CONSTANTS[-1],0xc67178f2)

    def test_single_compression_has_exact_known_state(self):
        self.assertEqual(p.compress_block(p.INITIAL_STATE,p.pad_message(b'abc')),
            (0xba7816bf,0x8f01cfea,0x414140de,0x5dae2223,0xb00361a3,0x96177a9c,0xb410ff61,0xf20015ad))

    def test_first_abc_round_matches_nist_worked_example(self):
        rounds=p.compression_rounds(p.INITIAL_STATE,p.message_schedule(p.pad_message(b'abc')))
        self.assertEqual(rounds[0],(0x5d6aebcd,0x6a09e667,0xbb67ae85,0x3c6ef372,
                                    0xfa2a4622,0x510e527f,0x9b05688c,0x1f83d9ab))

    def test_compression_state_requires_exact8words(self):
        for state in (list(p.INITIAL_STATE),(),p.INITIAL_STATE[:-1],p.INITIAL_STATE+(0,),
                      (True,)+p.INITIAL_STATE[1:],(-1,)+p.INITIAL_STATE[1:],(1<<32,)+p.INITIAL_STATE[1:]):
            with self.assertRaises(ValueError): p.compress_block(state,bytes(64))

    def test_compression_addition_wraps_for_full_unsigned_state(self):
        result=p.compress_block((0xffffffff,)*8,b'\xff'*64)
        self.assertTrue(all(type(w) is int and 0<=w<1<<32 for w in result))
        self.assertEqual(len(result),8)


class CompressionTraceTests(unittest.TestCase):
    def setUp(self):
        self.raw=bytes(range(200))
        self.blocks=p.compression_trace(self.raw)
        self.digest=hashlib.sha256(self.raw).hexdigest()

    def bad(self,mutate):
        blocks=copy.deepcopy(self.blocks);mutate(blocks)
        with self.assertRaises(ValueError): p.validate_trace(self.raw,blocks,self.digest)

    def test_complete_trace_replays_to_library_digest(self):
        p.validate_trace(self.raw,self.blocks,self.digest)
        self.assertEqual(len(self.blocks),4)

    def test_padding_bytes_are_bound_before_hash_checks(self):
        self.bad(lambda b:b[-1].update(block_hex='00'*64))

    def test_middle_input_byte_change_rejected(self):
        self.bad(lambda b:b[1].update(block_hex='ff'+b[1]['block_hex'][2:]))

    def test_block_order_cannot_change(self):
        self.bad(lambda b:b.reverse())

    def test_missing_or_extra_block_rejected(self):
        self.bad(lambda b:b.pop())
        self.bad(lambda b:b.append(copy.deepcopy(b[-1])))

    def test_duplicate_block_is_not_valid_chaining(self):
        self.bad(lambda b:b.__setitem__(1,copy.deepcopy(b[0])))

    def test_initial_state_is_bound(self):
        self.bad(lambda b:b[0]['input_state'].__setitem__(0,0))

    def test_intermediate_state_is_bound(self):
        self.bad(lambda b:b[2]['input_state'].__setitem__(7,0))

    def test_output_state_is_bound(self):
        self.bad(lambda b:b[1]['output_state'].__setitem__(3,0))

    def test_expanded_schedule_word_is_checked(self):
        self.bad(lambda b:b[0]['schedule'].__setitem__(63,b[0]['schedule'][63]^1))

    def test_initial_schedule_word_is_checked(self):
        self.bad(lambda b:b[0]['schedule'].__setitem__(0,0))

    def test_all_schedule_words_required(self):
        self.bad(lambda b:b[0]['schedule'].pop())
        self.bad(lambda b:b[0]['schedule'].append(0))

    def test_exact_word_types_and_bounds_required(self):
        for key in ('input_state','schedule','output_state'):
            for bad in (True,-1,1<<32,1.0):
                self.bad(lambda b,k=key,v=bad:b[0][k].__setitem__(0,v))

    def test_round_states_include_all64_transitions(self):
        self.assertTrue(all(len(block['round_states'])==64 and
                            all(len(state)==8 for state in block['round_states']) for block in self.blocks))

    def test_middle_round_word_mutation_rejected(self):
        self.bad(lambda b:b[0]['round_states'][37].__setitem__(3,b[0]['round_states'][37][3]^1))

    def test_round_state_omission_or_reordering_rejected(self):
        self.bad(lambda b:b[0]['round_states'].pop())
        self.bad(lambda b:b[0]['round_states'].reverse())

    def test_round_state_exact_word_types_required(self):
        for value in (True,-1,1<<32,1.0):
            self.bad(lambda b,v=value:b[0]['round_states'][0].__setitem__(0,v))

    def test_final_round_and_feed_forward_are_distinct(self):
        for block in self.blocks:
            self.assertEqual(block['output_state'],[(old+last)&p.WORD_MASK for old,last in
                zip(block['input_state'],block['round_states'][-1],strict=True)])
            self.assertNotEqual(block['output_state'],block['round_states'][-1])

    def test_index_boolean_or_wrong_index_rejected(self):
        self.bad(lambda b:b[0].update(index=False))
        self.bad(lambda b:b[1].update(index=0))

    def test_digest_uses_complete_big_endian_output(self):
        for bad in ('0'*64,self.digest.upper(),self.digest[:-2],self.digest+'00',bytes.fromhex(self.digest)[::-1].hex()):
            with self.assertRaises(ValueError): p.validate_trace(self.raw,self.blocks,bad)

    def test_trace_does_not_accept_extra_fields(self):
        self.bad(lambda b:b[0].update(trusted=True))


class SelectedRecordTests(unittest.TestCase):
    def test_all258_complete_inputs_match_independent_hashlib(self):
        self.assertEqual(len(_records()),258)
        for r in _records():
            self.assertEqual(r['digest'],hashlib.sha256(bytes.fromhex(r['preimage_hex'])).hexdigest())

    def test_inventory_preserves_all1652_block_occurrences(self):
        self.assertEqual(sum(len(r['blocks']) for r in _records()),1652)
        self.assertEqual(sum(len(bytes.fromhex(r['preimage_hex'])) for r in _records()),98349)
        self.assertEqual(sum(len(r['blocks'])*64 for r in _records()),105728)

    def test_transition_sharing_retains692_distinct_computations(self):
        transitions={}
        for r in _records():
            for b in r['blocks']:
                key=(tuple(b['input_state']),b['block_hex'])
                if key in transitions: self.assertEqual(transitions[key],tuple(b['output_state']))
                transitions[key]=tuple(b['output_state'])
        self.assertEqual(len(transitions),692)

    def test_group_order_and_counts_are_complete(self):
        self.assertEqual([(k,sum(r['category']==k for r in _records())) for k in p.GROUP_COUNTS],
                         list(p.GROUP_COUNTS.items()))
        self.assertEqual(_records()[0]['category'],'ranking_seed')
        self.assertEqual(_records()[-1]['category'],'freeze')

    def test_long_freeze_and_ranking_seed_have_complete_chains(self):
        self.assertEqual(len(_records()[0]['blocks']),11)
        self.assertEqual(len(_records()[-1]['blocks']),83)

    def test_all_exact_w_records_are_bound(self):
        p.validate_hash_records(_records(),_w())

    def test_removed_or_added_record_rejected(self):
        for records in (_records()[:-1],_records()+[_records()[-1]]):
            with self.assertRaises(ValueError): p.validate_hash_records(records,_w())

    def test_record_category_index_and_order_are_fixed(self):
        for field,value in (('category','freeze'),('index',True),('index',1)):
            records=copy.deepcopy(_records());records[0][field]=value
            with self.assertRaises(ValueError): p.validate_hash_records(records,_w())
        records=list(_records());records[0],records[-1]=records[-1],records[0]
        with self.assertRaises(ValueError): p.validate_hash_records(records,_w())

    def test_complete_domain_prefix_cannot_be_removed(self):
        records=copy.deepcopy(_records());records[0]['preimage_hex']=records[0]['preimage_hex'][52:]
        records[0]['digest']=hashlib.sha256(bytes.fromhex(records[0]['preimage_hex'])).hexdigest()
        with self.assertRaises(ValueError): p.validate_hash_records(records,_w())

    def test_self_consistent_substitute_image_and_digest_rejected(self):
        records=copy.deepcopy(_records());records[0].update(preimage_hex=b'substitute'.hex(),
            digest=p.sha256_hex(b'substitute'),blocks=p.compression_trace(b'substitute'))
        with self.assertRaises(ValueError): p.validate_hash_records(records,_w())

    def test_selected_input_preparation_does_not_use_worker(self):
        with patch.object(p.preimages,'prepare_producer_preimages',side_effect=AssertionError('worker path')):
            records=p.selected_records(_w())
        self.assertEqual(len(records),258)


class PacketBoundaryTests(unittest.TestCase):
    def bad(self,mutate):
        packet=_packet();mutate(packet)
        with self.assertRaises((ValueError,TypeError,KeyError)): p.validate_packet(packet)

    def test_prepared_packet_is_immutable(self):
        prepared=_prepared()
        with self.assertRaises((FrozenInstanceError,AttributeError)): prepared.packet_bytes=b'changed'
        copy_packet=prepared.packet;copy_packet['schema']='changed'
        self.assertEqual(prepared.packet['schema'],p.SCHEMA)

    def test_prior_w_packet_remains_exact_original(self):
        self.assertEqual(_prepared().producer_preimages().packet_bytes,(ROOT/p.W_PACKET).read_bytes())
        self.assertEqual(p.sha(_prepared().producer_preimages().packet_bytes),p.W_PACKET_SHA)

    def test_read_retained_binds_all4_w_artifacts(self):
        retained=p.read_retained(ROOT)
        self.assertEqual({k:p.sha(v) for k,v in retained.items()},p.RETAINED_W_PINS)

    def test_all_outer_schema_policy_and_base_fields_are_pinned(self):
        for field in ('schema','policy','base_commit'):
            self.bad(lambda v,f=field:v.__setitem__(f,'changed'))

    def test_profile_constants_cannot_be_replaced(self):
        for key in ('initial_state','round_constants'):
            self.bad(lambda v,k=key:v['profile'][k].__setitem__(0,0))
        self.bad(lambda v:v['profile'].__setitem__('word_byte_order','little-endian'))

    def test_scope_cannot_claim_general_equivalence_or_authenticity(self):
        for key in ('general_sha256_equivalence','general_json_parser_equivalence',
                    'digest_authenticity_remains_external','python_execution_remains_external'):
            self.bad(lambda v,k=key:v['scope'].__setitem__(k,not v['scope'][k]))

    def test_all24_broader_claims_remain_exact_false(self):
        self.assertEqual(len(p.FALSE_CLAIMS),24)
        for key in p.FALSE_CLAIMS:
            self.bad(lambda v,k=key:v['claims'].__setitem__(k,True))
        self.bad(lambda v:v['claims'].__setitem__('root_transition_verified',0))

    def test_w_packet_and_anchors_cannot_change(self):
        self.bad(lambda v:v.update(producer_preimages_packet_sha256='0'*64))
        self.bad(lambda v:v['producer_preimages_packet'].__setitem__('base_commit','0'*40))
        self.bad(lambda v:v['retained_w'].__setitem__(p.W_SOURCE,'0'*64))

    def test_cross_package_binding_change_rejected(self):
        self.bad(lambda v:v['bindings'].__setitem__('program_hash','0'*64))

    def test_unknown_packet_field_or_success_boolean_rejected(self):
        self.bad(lambda v:v.update(trusted_sha256=True))
        self.bad(lambda v:v['hash_records'][0].update(verified=True))

    def test_noncanonical_or_mutable_serialization_rejected(self):
        for raw in (bytearray(_fixture_bytes()),_fixture_bytes()+b'\n',json.dumps(_packet()).encode()):
            with self.assertRaises(ValueError): p.PreparedProducerSha256(raw)

    def test_duplicate_json_keys_rejected(self):
        raw=_fixture_bytes()
        changed=b'{"schema":"duplicate",'+raw[1:]
        with self.assertRaises(ValueError): p.PreparedProducerSha256(changed)

    def test_external_packet_anchor_and_content_both_required(self):
        with self.assertRaises(ValueError): p.verify_packet_bytes(_fixture_bytes(),_prepared(),expected_sha256='0'*64)
        with self.assertRaises(ValueError): p.verify_packet_bytes(_fixture_bytes()+b'\n',_prepared(),expected_sha256=p.sha(_fixture_bytes()+b'\n'))

    def test_retained_file_substitution_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            for name,raw in p.read_retained(ROOT).items():
                path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
            (root/p.W_SOURCE).write_bytes(b'not the W source')
            with self.assertRaises(ValueError): p.read_retained(root)

    def test_summary_describes_selected_reference_and_not_live_gain(self):
        summary=p.summary(_prepared())
        self.assertEqual(summary['complete_preimages'],258)
        self.assertEqual(summary['compression_blocks'],1652)
        self.assertEqual(summary['compression_rounds'],105728)
        self.assertEqual(summary['digest_bytes'],8256)
        self.assertTrue(summary['digest_authenticity_remains_external'])
        self.assertFalse(summary['fresh_worker_output_captured'])
        self.assertFalse(summary['candidate_active'])

    def test_one_full_retained_package_reconstruction_matches_fixture(self):
        with tempfile.TemporaryDirectory(prefix='r17x-runtime-') as temp:
            prepared=p.prepare_producer_sha256(ROOT,Path(temp)/'packages')
            self.assertEqual(prepared.packet_bytes,_fixture_bytes())
            p.verify_packet_bytes(prepared.packet_bytes,prepared,expected_sha256=p.sha(_fixture_bytes()))


class ProducerSha256RendererTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from rcp_rclm_runtime_v5.phase17 import producer_sha256_lean as renderer
        cls.renderer=renderer
        cls.sources=renderer.generated_sources(_prepared(),source_root=ROOT)

    def test_exact_dependency_and_positive_case_inventory(self):
        self.assertEqual(list(self.sources),[*self.renderer.DEPENDENCY_LABELS,*self.renderer.AUXILIARY_LABELS,*self.renderer.LABELS])
        self.assertEqual(len(self.renderer.DEPENDENCY_LABELS),7)
        self.assertEqual(self.renderer.AUXILIARY_LABELS,('Phase17XSha256Blocks',))
        self.assertEqual(len(self.sources),21)
        self.assertEqual(self.renderer.LABELS[0],'ProducerSha256')
        self.assertEqual(len(set(self.renderer.NAMES)),len(self.renderer.NAMES))
        for name in (*self.renderer.DEPENDENCY_LABELS,*self.renderer.AUXILIARY_LABELS):
            self.assertNotIn(b'#print',self.sources[name])
        for name in self.renderer.LABELS:
            self.assertTrue(self.sources[name].startswith(
                b'import Phase17WDependency\nimport Phase17XSha256Blocks\n\nset_option Elab.async false\n'))

    def test_auxiliary_checks_all_blocks_without_importing_w(self):
        source=self.sources['Phase17XSha256Blocks']
        self.assertTrue(source.startswith(b'import Lean\n\nset_option Elab.async false\n'))
        self.assertNotIn(b'Phase17Preimages.',source)
        self.assertNotIn(b'import Phase17WDependency',source)
        numbers=[str(index).encode('ascii') for index in range(696)]
        self.assertEqual(re.findall(rb'^theorem block_checked_([0-9]+) :$',source,re.M),numbers)
        self.assertEqual(re.findall(rb'^theorem block_step_([0-9]+) :',source,re.M),numbers)
        for name in self.renderer.LABELS:
            self.assertNotIn(b'def modulus :',self.sources[name])
            self.assertNotIn(b'theorem block_step_0 :',self.sources[name])

    def test_auxiliary_rejects_forbidden_arithmetic_core(self):
        original=self.renderer.template(ROOT)
        marker=self.renderer.BRIDGE_MARKER.encode()
        altered=original.replace(marker,b'axiom forged_compression : False\n'+marker,1)
        with patch.object(self.renderer,'template',return_value=altered),self.assertRaises(ValueError):
            self.renderer._auxiliary_validated(_prepared(),source_root=ROOT)

    def test_corrupted_control_witnesses_do_not_redeclare_imported_blocks(self):
        for name in ('WrongScheduleWord','WrongRoundState','WrongInitialState','WrongFeedForward'):
            source=self.sources[name]
            self.assertIn(b'noncomputable def block1000 :',source)
            self.assertIn(b'BlockChecked before1000 block1000 trace1000 after1000',source)
            self.assertNotIn(b'noncomputable def block0 :',source)

    def test_w_dependency_preserves_proofs_except_exact_audit_commands(self):
        from rcp_rclm_runtime_v5.phase17 import producer_preimages_lean as prior
        original=(ROOT/p.W_SOURCE).read_bytes()
        audit_lines={('#print axioms '+name+'\n').encode() for name in prior.NAMES}
        expected=b''.join(line for line in original.splitlines(keepends=True) if line not in audit_lines)
        self.assertEqual(self.sources['Phase17WDependency'],expected)
        self.assertEqual(p.sha(original),p.W_SOURCE_SHA)

    def test_all_negatives_have_explicit_false_decision_witnesses(self):
        for label in self.renderer.LABELS[1:]:
            with self.subTest(label=label):
                source=self.sources[label].decode()
                self.assertIn('theorem control_false :',source)
                self.assertIn('of_decide_eq_false control_false',source)
                self.assertIn('decide +kernel',source)
                self.assertNotIn('#print axioms',source)

    def test_renderer_rejects_native_shortcuts_placeholders_and_new_axioms(self):
        original=self.renderer.template(ROOT)
        for suffix in (b'\nexample : True := by native_decide\n',b'\nexample : True := by decide +native\n',
                       b'\nexample : True := by decide + native\n',b'\nexample : True := by sorry\n',
                       b'\naxiom counterfeit : False\n',b'\nunsafe def counterfeit : Nat := 0\n',
                       b'\npartial def counterfeit : Nat := 0\n'):
            with self.subTest(suffix=suffix),patch.object(self.renderer,'template',return_value=original+suffix):
                with self.assertRaises(ValueError):
                    self.renderer._render_validated(_prepared(),source_root=ROOT,negative=self.renderer.LABELS[1])

    def test_template_pin_rejects_nonsemantic_mutation(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);path=root/self.renderer.BRIDGE_PATH
            path.parent.mkdir(parents=True);path.write_bytes(self.renderer.template(ROOT)+b'\n')
            with self.assertRaises(ValueError): self.renderer.template(root)

    def test_renderer_requires_prepared_wrapper_and_known_control(self):
        with self.assertRaises(ValueError): self.renderer.generated_sources(_packet(),source_root=ROOT)
        with self.assertRaises(ValueError): self.renderer.render(_prepared(),source_root=ROOT,negative='invented')


if __name__=='__main__':
    unittest.main()
