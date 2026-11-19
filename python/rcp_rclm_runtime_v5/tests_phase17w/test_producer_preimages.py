"""Selected producer-preimage and seeded-grammar tests, without worker campaigns.

The reference fixture is derived from the retained V packet. One integration
test independently reconstructs the physical historical packages and V packet.
All compiler-log fixtures in the companion module remain controlled tests.
"""
from __future__ import annotations

import copy
from dataclasses import FrozenInstanceError
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from rcp_rclm_runtime_v5.phase17 import producer_preimages as pp

ROOT = Path(__file__).resolve().parents[3]


@lru_cache(maxsize=1)
def _base_v():
    raw = (ROOT / pp.V_PACKET).read_bytes()
    if pp.sha(raw) != pp.V_PACKET_SHA:
        raise AssertionError('retained V fixture identity changed')
    return pp.load_json_strict(raw)


@lru_cache(maxsize=1)
def _fixture_bytes():
    v = _base_v()
    return pp.canonical({'schema': pp.SCHEMA, 'policy': pp.POLICY, 'base_commit': pp.BASE,
        'program_metadata_packet': v, 'program_metadata_packet_sha256': pp.V_PACKET_SHA,
        'bindings': v['bindings'], 'retained_v': dict(pp.RETAINED_V_PINS),
        'profile': copy.deepcopy(pp.PROFILE), 'scope': copy.deepcopy(pp.SCOPE),
        'claims': {name: False for name in pp.FALSE_CLAIMS}, 'producer': pp.producer_inputs(v)})


def _packet():
    return pp.load_json_strict(_fixture_bytes())


@lru_cache(maxsize=1)
def _prepared():
    return pp.PreparedProducerPreimages(_fixture_bytes())


@lru_cache(maxsize=1)
def _producer_template():
    return pp.producer_inputs(_base_v())


def _producer():
    return copy.deepcopy(_producer_template())


def _rewrite(record, value):
    raw = pp.canonical(value)
    preimage = pp.PUBLIC_HASH_DOMAIN + raw
    record.update(json_hex=raw.hex(), preimage_hex=preimage.hex(), digest=pp.sha(preimage))


class CanonicalEncoderTests(unittest.TestCase):
    def test_literal_values_and_empty_collections_have_exact_encodings(self):
        for value, expected in ((None,b'null'),(False,b'false'),(True,b'true'),(0,b'0'),
                                (-1,b'-1'),('',b'""'),([],b'[]'),({},b'{}')):
            with self.subTest(value=value): self.assertEqual(pp.encode_canonical(value),expected)

    def test_object_keys_are_sorted_and_arrays_remain_ordered(self):
        self.assertEqual(pp.encode_canonical({'z':[3,2,1],'A':{'b':False,'a':None}}),
                         b'{"A":{"a":null,"b":false},"z":[3,2,1]}')

    def test_signed64_endpoints_are_exact_decimal(self):
        self.assertEqual(pp.encode_canonical(-(1<<63)),b'-9223372036854775808')
        self.assertEqual(pp.encode_canonical((1<<63)-1),b'9223372036854775807')

    def test_out_of_range_integers_are_rejected(self):
        for value in (-(1<<63)-1,1<<63,10**100):
            with self.assertRaises(ValueError): pp.encode_canonical(value)

    def test_boolean_values_are_not_rendered_as_numbers(self):
        self.assertEqual(pp.encode_canonical([False,0,True,1]),b'[false,0,true,1]')

    def test_floating_point_nonfinite_and_unsupported_types_are_rejected(self):
        for value in (1.0,float('nan'),float('inf'),(1,2),b'abc',bytearray(b'abc'),{1,2},object()):
            with self.subTest(kind=type(value)),self.assertRaises(ValueError): pp.encode_canonical(value)

    def test_strings_requiring_escapes_or_non_ascii_are_rejected(self):
        for value in ('a"b','a\\b','a\nb','a\tb','\0','\x7f','é','e\u0301','😀'):
            with self.subTest(value=repr(value)),self.assertRaises(ValueError): pp.encode_canonical(value)

    def test_printable_ascii_and_exact_string_bound(self):
        self.assertEqual(pp.encode_canonical(' ~'),b'" ~"')
        self.assertEqual(len(pp.encode_canonical('a'*pp.MAX_STRING)),pp.MAX_STRING+2)
        with self.assertRaises(ValueError): pp.encode_canonical('a'*(pp.MAX_STRING+1))

    def test_non_string_or_unencodable_object_keys_are_rejected(self):
        for value in ({1:'x'},{True:'x'},{None:'x'},{'bad"key':0},{'bäck':0}):
            with self.assertRaises(ValueError): pp.encode_canonical(value)

    def test_array_and_object_collection_bounds(self):
        self.assertEqual(len(pp.encode_canonical([0]*pp.MAX_ARRAY)),2*pp.MAX_ARRAY+1)
        pp.encode_canonical({str(i):0 for i in range(pp.MAX_OBJECT)})
        for value in ([0]*(pp.MAX_ARRAY+1),{str(i):0 for i in range(pp.MAX_OBJECT+1)}):
            with self.assertRaises(ValueError): pp.encode_canonical(value)

    def test_depth_is_bounded_independently_of_total_size(self):
        value=0
        for _ in range(pp.MAX_DEPTH): value=[value]
        pp.encode_canonical(value)
        with self.assertRaises(ValueError): pp.encode_canonical([value])

    def test_complete_image_bound_cannot_be_evaded_with_short_strings(self):
        with self.assertRaises(ValueError): pp.encode_canonical(['a'*pp.MAX_STRING]*9)

    def test_encoder_matches_original_canonical_bytes_for_all258_inputs(self):
        count=0
        for values in pp.preimage_groups(_producer()).values():
            for record in values:
                raw=bytes.fromhex(record['json_hex'])
                value=json.loads(raw)
                self.assertEqual(pp.encode_canonical(value),raw)
                self.assertEqual(pp.encode_canonical(value),pp.canonical(value))
                self.assertEqual(pp.metadata.decode_captured_json(raw),value)
                count+=1
        self.assertEqual(count,258)

    def test_domain_prefix_is_exact_and_encoder_never_calls_hash(self):
        with patch.object(pp,'sha',side_effect=AssertionError('encoding must not hash')):
            self.assertEqual(pp.hash_preimage({'a':1}),b'RCPRCLM-CANONICAL-JSON-V2\0{"a":1}')
        self.assertEqual(len(pp.PUBLIC_HASH_DOMAIN),26)


class SeededGrammarTests(unittest.TestCase):
    def test_zero_and_full_unsigned_seed_windows_have_known_results(self):
        self.assertEqual(pp.signed_parameter('0'*64,0),-16)
        self.assertEqual(pp.signed_parameter('f'*64,0),-13)

    def test_big_endian_window_and_both_parameter_extremes(self):
        self.assertEqual(pp.signed_parameter('00000020'+'0'*56,0),16)
        self.assertEqual(pp.signed_parameter('00000021'+'0'*56,0),-16)
        self.assertEqual(pp.signed_parameter('01000000'+'0'*56,0),(1<<24)%33-16)

    def test_eight_nibble_window_moves_by_two_digits(self):
        value='0000000100000002000000030000000400000005000000060000000700000008'
        self.assertEqual(pp.signed_parameter(value,0),-15)
        self.assertEqual(pp.signed_parameter(value,4),-14)
        self.assertEqual(pp.signed_parameter(value,8),-13)

    def test_window_wraps_at56_without_using_digest_suffix_as_a_prefix(self):
        value='0123456789abcdef'*4
        self.assertEqual(pp.signed_parameter(value,28),pp.signed_parameter(value,0))
        self.assertEqual(pp.signed_parameter(value,27),int(value[54:62],16)%33-16)
        self.assertEqual(pp.signed_parameter(value,pp.MAX_METADATA),
                         int(value[(2*pp.MAX_METADATA)%56:(2*pp.MAX_METADATA)%56+8],16)%33-16)

    def test_full_digest_is_required_even_outside_selected_window(self):
        for seed in ('0'*63,'0'*65,'0'*63+'g','0'*62+'GG','A'*64,'',None,1,b'0'*64):
            with self.subTest(seed=type(seed)),self.assertRaises(ValueError): pp.signed_parameter(seed,0)

    def test_parameter_offset_requires_an_exact_bounded_natural(self):
        for offset in (-1,True,False,1.0,None,1<<63):
            with self.assertRaises(ValueError): pp.signed_parameter('0'*64,offset)

    def test_all64_parameters_reconstruct_actual_v_descriptors(self):
        view=_base_v()['planner_refinement_packet']['ranking']['current_view']
        for row,image in zip(_producer()['rows'],_base_v()['candidate_images'],strict=True):
            program=pp.metadata.decode_program(bytes.fromhex(image['image_hex']))
            family=pp.FAMILIES.index(program['family'])
            derived=pp.grammar_descriptor(view,family,program['variant'],row['grammar_seed']['digest'])
            self.assertEqual(derived,program)
            self.assertEqual(pp.encode_canonical(derived),bytes.fromhex(image['image_hex']))

    def test_seed_preimage_contains_all_seven_exact_context_fields(self):
        view=_base_v()['planner_refinement_packet']['ranking']['current_view']
        value=pp.grammar_seed_value(view,6,3)
        self.assertEqual(value,{'domain':'phase16.legal_mutation_program.v1',
            'active_package_hash':view['active_package_hash'],'promotion_index':0,'family':'tool_policy',
            'variant':3,'generation':2,'public_nonce_hash':view['public_nonce_hash']})

    def test_seed_input_changes_with_each_present_grammar_field(self):
        view=copy.deepcopy(_base_v()['planner_refinement_packet']['ranking']['current_view'])
        original=pp.hash_preimage(pp.grammar_seed_value(view,0,0))
        for key,value in [('active_package_hash','1'*64),('turn_index',1),('public_nonce_hash','2'*64),
                          ('family_counts',[2,1,1,1,1,1,1,1])]:
            changed=dict(view,**{key:value})
            self.assertNotEqual(pp.hash_preimage(pp.grammar_seed_value(changed,0,0)),original)
        self.assertNotEqual(pp.hash_preimage(pp.grammar_seed_value(view,1,0)),original)
        self.assertNotEqual(pp.hash_preimage(pp.grammar_seed_value(view,0,1)),original)

    def test_each_family_derives_its_actual_operation(self):
        view=_base_v()['planner_refinement_packet']['ranking']['current_view']
        for family,operation in enumerate(pp.metadata.OPERATIONS):
            value=pp.grammar_descriptor(view,family,0,'0'*64)
            self.assertEqual(value['operation_id'],operation)
            self.assertEqual(value['family'],pp.FAMILIES[family])
            self.assertEqual(value['generation'],2)

    def test_generation_uses_inherited_count_plus_one(self):
        view=copy.deepcopy(_base_v()['planner_refinement_packet']['ranking']['current_view'])
        view['family_counts'][6]=2
        self.assertEqual(pp.grammar_descriptor(view,6,0,'0'*64)['generation'],3)

    def test_family_variant_and_generation_bounds_are_checked(self):
        view=_base_v()['planner_refinement_packet']['ranking']['current_view']
        for family,variant in [(-1,0),(8,0),(True,0),(0,-1),(0,4),(0,True)]:
            with self.assertRaises(ValueError): pp.grammar_descriptor(view,family,variant,'0'*64)
        changed=copy.deepcopy(view);changed['family_counts'][0]=pp.MAX_METADATA
        with self.assertRaises(ValueError): pp.grammar_seed_value(changed,0,0)


class ProducerPreimageTests(unittest.TestCase):
    def setUp(self): self.producer=_producer()

    def reject(self,mutate):
        value=copy.deepcopy(self.producer);mutate(value)
        with self.assertRaises(ValueError): pp.validate_producer(value,_base_v())

    def test_complete_input_inventory_and_exact_sizes(self):
        expected={'ranking_seed':(1,618,644),'grammar_seed':(32,9524,10356),
                  'program':(32,9723,10555),'feature':(32,21595,22427),
                  'tie':(160,44960,49120),'freeze':(1,5221,5247)}
        groups=pp.preimage_groups(self.producer)
        for name,values in groups.items():
            self.assertEqual((len(values),sum(len(bytes.fromhex(v['json_hex'])) for v in values),
                              sum(len(bytes.fromhex(v['preimage_hex'])) for v in values)),expected[name])

    def test_ranking_seed_is_complete_actual_u_view(self):
        ranking=_base_v()['planner_refinement_packet']['ranking']
        record=self.producer['ranking_seed']
        self.assertEqual(bytes.fromhex(record['json_hex']),pp.canonical(ranking['seed_preimage']))
        self.assertEqual(record['digest'],ranking['seed_digest'])
        self.assertEqual(json.loads(bytes.fromhex(record['json_hex']))['view'],ranking['current_view'])

    def test_all_program_images_are_the_actual_imported_v_images(self):
        for row,image in zip(self.producer['rows'],_base_v()['candidate_images'],strict=True):
            self.assertEqual(row['key'],image['key'])
            self.assertEqual(row['program']['json_hex'],image['image_hex'])
            self.assertEqual(row['program']['digest'],image['key'])

    def test_features_and_ties_bind_all_actual_u_inputs(self):
        for row,target in zip(self.producer['rows'],_base_v()['planner_refinement_packet']['ranking']['rows'],strict=True):
            self.assertEqual(row['feature']['digest'],target['feature_digest'])
            self.assertEqual(bytes.fromhex(row['feature']['json_hex']),pp.canonical(target['feature_preimage']))
            self.assertEqual([x['digest'] for x in row['ties']],target['tie_digests'])
            self.assertEqual([json.loads(bytes.fromhex(x['json_hex'])) for x in row['ties']],target['tie_preimages'])

    def test_freeze_uses_complete_actual_u_order_scores_and_view(self):
        ranking=_base_v()['planner_refinement_packet']['ranking']
        self.assertEqual(bytes.fromhex(self.producer['freeze']['json_hex']),pp.canonical(ranking['freeze_preimage']))
        self.assertEqual(self.producer['freeze']['digest'],ranking['freeze_digest'])
        value=json.loads(bytes.fromhex(self.producer['freeze']['json_hex']))
        self.assertEqual(len(value['candidates']),32)
        self.assertEqual(value['view'],ranking['current_view'])

    def test_all_external_hashes_match_stdlib_preparation_computation(self):
        for records in pp.preimage_groups(self.producer).values():
            for record in records:
                preimage=bytes.fromhex(record['preimage_hex'])
                self.assertEqual(record['digest'],hashlib.sha256(preimage).hexdigest())
                self.assertEqual(preimage,pp.PUBLIC_HASH_DOMAIN+bytes.fromhex(record['json_hex']))

    def test_complete_pair_domain_has_no_duplicates_or_omissions(self):
        pairs=[]
        for row in self.producer['rows']:
            value=json.loads(bytes.fromhex(row['grammar_seed']['json_hex']))
            pairs.append((value['family'],value['variant']))
        self.assertEqual(sorted(pairs),sorted((f,v) for f in pp.FAMILIES for v in range(4)))
        self.reject(lambda p:p['rows'].pop())
        self.reject(lambda p:p['rows'].append(copy.deepcopy(p['rows'][0])))
        self.reject(lambda p:p['rows'].__setitem__(1,copy.deepcopy(p['rows'][0])))

    def test_reordered_rows_or_changed_keys_are_rejected(self):
        self.reject(lambda p:p['rows'].reverse())
        self.reject(lambda p:p['rows'][0].update(key='0'*64))

    def test_current_view_changes_and_future_fields_are_rejected(self):
        for key,value in [('turn_index',1),('family_counts',[2]*8),('public_nonce_hash','1'*64),
                          ('challenge_commitment_hash','2'*64),('predecessor_state_hash','3'*64)]:
            self.reject(lambda p,k=key,v=value:p['current_view'].__setitem__(k,v))
        self.reject(lambda p:p['current_view'].update(future_horizon=100))

    def test_record_field_inventory_is_exact(self):
        self.reject(lambda p:p['ranking_seed'].update(extra=True))
        self.reject(lambda p:p['rows'][0]['feature'].pop('digest'))
        self.reject(lambda p:p['rows'][0].update(extra=True))
        self.reject(lambda p:p.update(extra=True))

    def test_hex_representation_must_be_lowercase_even_and_bounded(self):
        for value in ('','0','GG','0 ',None,b'00','00'*(pp.MAX_JSON_BYTES+1)):
            self.reject(lambda p,v=value:p['ranking_seed'].update(json_hex=v))
        self.reject(lambda p:p['ranking_seed'].update(preimage_hex='00'*(pp.MAX_JSON_BYTES+27)))

    def test_domain_terminator_cannot_be_omitted_or_duplicated(self):
        for domain in (pp.PUBLIC_HASH_DOMAIN[:-1],pp.PUBLIC_HASH_DOMAIN+b'\0',b'wrong\0'):
            def change(p,domain=domain):
                raw=domain+bytes.fromhex(p['ranking_seed']['json_hex'])
                p['ranking_seed'].update(preimage_hex=raw.hex(),digest=pp.sha(raw))
            self.reject(change)

    def test_json_whitespace_or_trailing_bytes_rejected_even_with_new_hash(self):
        for suffix in (b'\n',b' ',b'{}'):
            def change(p,suffix=suffix):
                raw=bytes.fromhex(p['ranking_seed']['json_hex'])+suffix
                preimage=pp.PUBLIC_HASH_DOMAIN+raw
                p['ranking_seed'].update(json_hex=raw.hex(),preimage_hex=preimage.hex(),digest=pp.sha(preimage))
            self.reject(change)

    def test_changed_grammar_domain_rejected_even_with_consistent_hash(self):
        def change(p):
            value=json.loads(bytes.fromhex(p['rows'][0]['grammar_seed']['json_hex']))
            value['domain']='phase16.legal_mutation_program.v2'
            _rewrite(p['rows'][0]['grammar_seed'],value)
        self.reject(change)

    def test_program_parameter_change_rejected_even_with_consistent_hash(self):
        def change(p):
            value=json.loads(bytes.fromhex(p['rows'][0]['program']['json_hex']))
            value['parameter_a']=value['parameter_a']+1
            _rewrite(p['rows'][0]['program'],value)
        self.reject(change)

    def test_feature_seed_weights_and_stream_are_bound(self):
        for key,value in [('seed','1'*64),('planner_weights_sha256','2'*64),('challenge_stream','other')]:
            def change(p,key=key,value=value):
                obj=json.loads(bytes.fromhex(p['rows'][0]['feature']['json_hex']))
                obj[key]=value;_rewrite(p['rows'][0]['feature'],obj)
            self.reject(change)

    def test_tie_rejection_order_and_full_inventory_are_bound(self):
        self.reject(lambda p:p['rows'][0]['ties'].pop())
        self.reject(lambda p:p['rows'][0]['ties'].reverse())
        self.reject(lambda p:p['rows'][0]['ties'].__setitem__(1,copy.deepcopy(p['rows'][0]['ties'][0])))

    def test_tie_policy_family_count_and_program_key_are_bound(self):
        for key,value in [('policy_id','other'),('family_count',2),('program_hash','1'*64),('rejection_count',5)]:
            def change(p,key=key,value=value):
                obj=json.loads(bytes.fromhex(p['rows'][0]['ties'][0]['json_hex']))
                obj[key]=value;_rewrite(p['rows'][0]['ties'][0],obj)
            self.reject(change)

    def test_freeze_score_order_and_schema_are_bound(self):
        for which in ('score','order','schema','omit'):
            def change(p,which=which):
                obj=json.loads(bytes.fromhex(p['freeze']['json_hex']))
                if which=='score': obj['candidates'][0]['base_score']+=1
                elif which=='order': obj['candidates'].reverse()
                elif which=='schema': obj['schema']='other'
                else: obj['candidates'].pop()
                _rewrite(p['freeze'],obj)
            self.reject(change)

    def test_supplied_digest_format_and_anchor_are_checked(self):
        for value in ('0'*64,'A'*64,'0'*63,True):
            self.reject(lambda p,v=value:p['rows'][0]['feature'].update(digest=v))

    def test_context_helpers_reject_out_of_domain_tie_and_freeze_inputs(self):
        view=self.producer['current_view'];table=_base_v()['planner_refinement_packet']['before_table']
        for family,rejected in [(8,0),(0,5),(-1,0),(0,True)]:
            with self.assertRaises(ValueError): pp.tie_value(view,'0'*64,family,rejected)
        for malformed in (table[:-1],list(reversed(table)),[table[0]]*32):
            with self.assertRaises(ValueError): pp.freeze_value(view,malformed)

    def test_substituted_imported_descriptor_cannot_seed_its_own_expected_value(self):
        v=copy.deepcopy(_base_v())
        program=json.loads(bytes.fromhex(v['candidate_images'][0]['image_hex']))
        program['parameter_a']+=1
        v['candidate_images'][0]['image_hex']=pp.canonical(program).hex()
        v['planner_refinement_packet']['ranking']['rows'][0]['program']=program
        with self.assertRaisesRegex(ValueError,'seed-derived descriptor'): pp.producer_inputs(v)


class ProducerPacketTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.prepared=_prepared()

    def setUp(self): self.packet=_packet()

    def reject(self,mutate):
        packet=copy.deepcopy(self.packet);mutate(packet)
        with self.assertRaises(ValueError): pp.PreparedProducerPreimages(pp.canonical(packet))

    def test_wrapper_is_immutable_and_returns_detached_packet_objects(self):
        with self.assertRaises(FrozenInstanceError): self.prepared.packet_bytes=b'{}'
        packet=self.prepared.packet;packet['producer']['rows'][0]['key']='0'*64
        self.assertNotEqual(packet,self.prepared.packet)
        self.assertIsInstance(self.prepared.program_metadata(),pp.metadata.PreparedProgramMetadata)

    def test_exact_packet_fields_and_schema_are_required(self):
        self.reject(lambda p:p.update(extra=1))
        self.reject(lambda p:p.pop('producer'))
        self.reject(lambda p:p.update(schema='other'))

    def test_policy_base_and_profile_are_fixed(self):
        self.reject(lambda p:p.update(policy='other'))
        self.reject(lambda p:p.update(base_commit='0'*40))
        self.reject(lambda p:p['profile'].update(preimage_count=257))

    def test_all24_broader_claims_remain_strictly_false(self):
        for key in pp.FALSE_CLAIMS:
            with self.subTest(key=key): self.reject(lambda p,k=key:p['claims'].__setitem__(k,True))
        self.reject(lambda p:p['claims'].update(root_transition_verified=0))

    def test_sha_capture_execution_and_general_scope_boundaries_cannot_change(self):
        for key in ('sha256_computation_remains_external','public_hash_computation_remains_external',
                    'digest_authenticity_remains_external','byte_capture_remains_external',
                    'python_execution_remains_external','general_grammar_parameter_derivation_remains_external'):
            with self.subTest(key=key): self.reject(lambda p,k=key:p['scope'].__setitem__(k,False))
        self.reject(lambda p:p['scope'].update(general_json_parser_equivalence=True))

    def test_retained_v_pins_and_all_bindings_are_fixed(self):
        for key in pp.RETAINED_V_PINS:
            self.reject(lambda p,k=key:p['retained_v'].__setitem__(k,'0'*64))
        for key in self.packet['bindings']:
            self.reject(lambda p,k=key:p['bindings'].__setitem__(k,'0'*64))

    def test_v_packet_substitution_rejected_even_with_recomputed_outer_hash(self):
        def change(p):
            p['program_metadata_packet']['candidate_images'][0]['key']='0'*64
            p['program_metadata_packet_sha256']=pp.sha(pp.canonical(p['program_metadata_packet']))
        self.reject(change)

    def test_canonical_complete_immutable_packet_bytes_are_required(self):
        for raw in (b'',b'{}',self.prepared.packet_bytes+b'\n',self.prepared.packet_bytes[:-1],
                    bytearray(self.prepared.packet_bytes),memoryview(self.prepared.packet_bytes)):
            with self.assertRaises(ValueError): pp.PreparedProducerPreimages(raw)

    def test_malformed_w_rejected_before_deep_v_revalidation(self):
        packet=copy.deepcopy(self.packet);packet['producer']['rows'].pop()
        with patch.object(pp.metadata,'PreparedProgramMetadata',side_effect=AssertionError('deep V must not run')):
            with self.assertRaises(ValueError): pp.validate_packet(packet)

    def test_external_packet_hash_and_exact_reconstruction_required(self):
        with self.assertRaises(ValueError):
            pp.verify_packet_bytes(self.prepared.packet_bytes,self.prepared,expected_sha256='0'*64)
        changed=self.prepared.packet_bytes+b'\n'
        with self.assertRaises(ValueError): pp.verify_packet_bytes(changed,self.prepared,expected_sha256=pp.sha(changed))
        with self.assertRaises(ValueError):
            pp.verify_packet_bytes(self.prepared.packet_bytes,object(),expected_sha256=pp.sha(self.prepared.packet_bytes))

    def test_summary_records_complete_scope_and_keeps_sha_external(self):
        value=pp.summary(self.prepared)
        self.assertEqual(value['complete_json_images'],258)
        self.assertEqual(value['complete_json_bytes'],91641)
        self.assertEqual(value['complete_prefixed_bytes'],98349)
        self.assertEqual(value['canonical_grammar_descriptors'],32)
        self.assertEqual(value['derived_parameters'],64)
        self.assertEqual(value['selected_program_hash'],self.packet['bindings']['program_hash'])
        self.assertTrue(value['sha256_is_external_preparation_consistency_check'])
        self.assertFalse(value['sha256_formally_checked'])
        self.assertFalse(value['fresh_worker_output_captured'])


class ProducerPreparationTests(unittest.TestCase):
    def test_fresh_v_packages_and_w_preimages_reconstruct_without_workers_or_compiler(self):
        with tempfile.TemporaryDirectory(prefix='r17w-test-') as temp:
            with patch('subprocess.Popen',side_effect=AssertionError('preparation cannot execute processes')):
                prepared=pp.prepare_producer_preimages(ROOT,Path(temp)/'packages')
            self.assertEqual(prepared.packet_bytes,_fixture_bytes())
            pp.verify_packet_bytes(prepared.packet_bytes,prepared,expected_sha256=pp.sha(prepared.packet_bytes))

    def test_missing_retained_v_inputs_rejected(self):
        with tempfile.TemporaryDirectory() as temp,self.assertRaises(ValueError): pp.read_retained(Path(temp))

    def test_corrupt_retained_v_input_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/pp.V_EXECUTION;path.parent.mkdir(parents=True);path.write_bytes(b'{}')
            with self.assertRaisesRegex(ValueError,'retained V input changed'): pp.read_retained(Path(temp))

    def test_linked_retained_v_input_rejected(self):
        with patch.object(Path,'is_symlink',return_value=True),self.assertRaises(ValueError): pp.read_retained(ROOT)

    def test_retained_v_record_changes_during_preparation_are_rejected(self):
        retained=pp.read_retained(ROOT)
        changed=dict(retained);changed[pp.V_EXECUTION]=b'{}'
        with tempfile.TemporaryDirectory() as temp,\
             patch.object(pp.metadata,'prepare_program_metadata',return_value=_prepared().program_metadata()),\
             patch.object(pp,'read_retained',side_effect=[retained,changed]):
            with self.assertRaisesRegex(ValueError,'changed during'): pp.prepare_producer_preimages(ROOT,Path(temp))


class ProducerRendererTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from rcp_rclm_runtime_v5.phase17 import producer_preimages_lean as renderer
        cls.renderer=renderer
        cls.sources=renderer.generated_sources(_prepared(),source_root=ROOT)

    def test_exact_dependency_and_positive_case_inventory(self):
        self.assertEqual(list(self.sources),[*self.renderer.DEPENDENCY_LABELS,*self.renderer.LABELS])
        self.assertEqual(len(self.renderer.DEPENDENCY_LABELS),6)
        self.assertEqual(self.renderer.LABELS[0],'ProducerPreimages')
        self.assertEqual(len(set(self.renderer.NAMES)),len(self.renderer.NAMES))
        for name in self.renderer.DEPENDENCY_LABELS: self.assertNotIn(b'#print',self.sources[name])
        for name in self.renderer.LABELS: self.assertTrue(self.sources[name].startswith(b'import Phase17VDependency\n'))

    def test_v_dependency_preserves_proof_lines_except_exact_named_audit_commands(self):
        from rcp_rclm_runtime_v5.phase17 import program_metadata_lean as prior
        original=(ROOT/pp.V_SOURCE).read_bytes()
        audit_lines={('#print axioms '+name+'\n').encode() for name in prior.NAMES}
        expected=b''.join(line for line in original.splitlines(keepends=True) if line not in audit_lines)
        self.assertEqual(self.sources['Phase17VDependency'],expected)
        self.assertEqual(pp.sha(original),pp.V_SOURCE_SHA)

    def test_actual_imported_descriptors_images_and_producer_inputs_are_referenced(self):
        source=self.sources['ProducerPreimages'].decode()
        self.assertIn('Phase17Metadata.candidateDescriptors',source)
        self.assertIn('Phase17Metadata.candidateImages',source)
        self.assertIn('Phase17Planner.rowInputs',source)
        self.assertIn('Phase17Joint.producerBinding.historicalState',source)
        self.assertIn('Phase17Joint.producerBinding.challenge',source)
        self.assertIn('Phase17LearnedBinding.observedBefore.package.planner',source)
        self.assertIn('Phase17LearnedBinding.observedAfter.package.planner',source)
        self.assertIn('base/model/phase15_planner/weights.i16le.bin',source)
        self.assertIn('some (65536, plannerHash)',source)

    def test_all_negatives_have_explicit_false_decision_witnesses(self):
        for label in self.renderer.LABELS[1:]:
            with self.subTest(label=label):
                source=self.sources[label].decode()
                self.assertIn('theorem control_false :',source)
                self.assertIn('of_decide_eq_false control_false',source)
                self.assertIn('decide +kernel',source)
                self.assertNotIn('#print axioms',source)
        order_control=self.sources['NoncanonicalObjectOrder'].decode()
        self.assertIn('some (ascii "{\\"z\\":0,\\"a\\":1}")',order_control)

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
