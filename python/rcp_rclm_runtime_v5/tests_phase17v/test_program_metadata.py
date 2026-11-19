"""Selected registry and descriptor projection tests; no historical campaigns.

The controlled packet fixture is built from retained U data and the pinned
historical predecessor. One integration check freshly reconstructs both physical
packages. Compiler-log fixtures in the companion module are not Lean evidence.
"""
from __future__ import annotations

import copy
from dataclasses import FrozenInstanceError
from functools import lru_cache
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from rcp_rclm_runtime_v5.phase17 import program_metadata as pm
from rcp_rclm_runtime_v5.phase17.campaign_transaction import load_predecessor

ROOT = Path(__file__).resolve().parents[3]


@lru_cache(maxsize=1)
def _fixture_bytes():
    parent = load_predecessor(ROOT)
    state = parent.state
    u = pm.load_json_strict((ROOT / pm.U_PACKET).read_bytes())
    candidate = next(row['program'] for row in u['ranking']['rows'] if row['key'] == u['bindings']['program_hash'])
    images = {}
    for side in ('before', 'after'):
        programs = [pm.load_json_strict(raw) for raw in parent.accepted_programs]
        if side == 'after':
            programs.append(candidate)
        manifest = {'schema_id': pm.REGISTRY_SCHEMA,
                    'inherited_program_hashes': state['installed_program_hashes'],
                    'candidate_program_hash': None if side == 'before' else u['bindings']['program_hash'],
                    'inherited_frontier': state['capability_frontier'],
                    'recursive_frontier': state['recursive_productivity_frontier'],
                    'candidate_active': False, 'promotion_authorized': False}
        entries = sorted(({'key': pm.planner.public_hash(program), 'image_hex': pm.canonical(program).hex()}
                          for program in programs), key=lambda entry: entry['key'])
        images[side] = {'manifest_hex': pm.canonical(manifest).hex(),
                        'historical_state_hex': parent.state_bytes.hex(), 'programs': entries}
    packet = {'schema': pm.SCHEMA, 'policy': pm.POLICY, 'base_commit': pm.BASE,
              'planner_refinement_packet': u, 'planner_refinement_packet_sha256': pm.U_PACKET_SHA,
              'bindings': u['bindings'], 'retained_u': dict(pm.RETAINED_U_PINS),
              'profile': copy.deepcopy(pm.PROFILE), 'scope': copy.deepcopy(pm.SCOPE),
              'claims': {name: False for name in pm.FALSE_CLAIMS}, 'registry_images': images,
              'candidate_images': [{'key': row['key'], 'image_hex': pm.canonical(row['program']).hex()}
                                   for row in u['ranking']['rows']]}
    return pm.canonical(packet)


def _packet():
    return pm.load_json_strict(_fixture_bytes())


@lru_cache(maxsize=1)
def _prepared():
    return pm.PreparedProgramMetadata(_fixture_bytes())


def _mutate_image(entry, mutate, field='image_hex'):
    value = pm.decoded_image(entry[field])
    mutate(value)
    entry[field] = pm.canonical(value).hex()


def _write_registry(package, image):
    files = {pm.REGISTRY_PATH: pm.image_bytes(image['manifest_hex']),
             pm.STATE_PATH: pm.image_bytes(image['historical_state_hex'])}
    files.update({pm.PROGRAM_PREFIX + entry['key'] + '.json': pm.image_bytes(entry['image_hex'])
                  for entry in image['programs']})
    for name, raw in files.items():
        path = package / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    return files


class ProgramDecoderTests(unittest.TestCase):
    def setUp(self):
        self.program = pm.decode_program(pm.image_bytes(_packet()['candidate_images'][0]['image_hex']))

    def reject(self, **changes):
        value = dict(self.program, **changes)
        with self.assertRaises(ValueError):
            pm.decode_program(pm.canonical(value))

    def test_all_selected_descriptors_decode_exact_complete_values(self):
        packet = _packet()
        for entry, row in zip(packet['candidate_images'], packet['planner_refinement_packet']['ranking']['rows'], strict=True):
            self.assertEqual(pm.decode_program(pm.image_bytes(entry['image_hex'])), row['program'])
        for image in packet['registry_images'].values():
            for entry in image['programs']:
                self.assertEqual(pm.planner.public_hash(pm.decode_program(pm.image_bytes(entry['image_hex']))), entry['key'])

    def test_exact_nine_fields_required(self):
        self.reject(extra=1)
        for key in pm.PROGRAM_FIELDS:
            value = dict(self.program); del value[key]
            with self.subTest(key=key), self.assertRaises(ValueError):
                pm.decode_program(pm.canonical(value))

    def test_schema_substitution_rejected(self):
        for schema in ('', 'runtime.v4.phase16.mutation_program.v2', None, 1):
            self.reject(schema_id=schema)

    def test_family_names_are_exact(self):
        for family in ('Tool_policy', 'other', '', 6, True, None):
            self.reject(family=family)

    def test_operation_is_bound_to_family(self):
        index = pm.FAMILIES.index(self.program['family'])
        for operation in (pm.OPERATIONS[(index + 1) % 8], '', None, 1):
            self.reject(operation_id=operation)

    def test_each_family_has_exact_declared_operation(self):
        for family, operation in zip(pm.FAMILIES, pm.OPERATIONS, strict=True):
            value = dict(self.program, family=family, operation_id=operation)
            self.assertEqual(pm.decode_program(pm.canonical(value)), value)

    def test_generation_must_be_positive_exact_signed64_integer(self):
        for value in (0, -1, True, False, 1.0, None, (1 << 63)):
            self.reject(generation=value)

    def test_generation_signed64_maximum_is_valid_in_decoder_only(self):
        value = dict(self.program, generation=pm.MAX_METADATA)
        self.assertEqual(pm.decode_program(pm.canonical(value))['generation'], pm.MAX_METADATA)

    def test_variant_bound_and_boolean_rejection(self):
        for value in (-1, 4, True, False, 1.0, None):
            self.reject(variant=value)

    def test_parameter_endpoints_are_inclusive(self):
        for a in (-16, 16):
            for b in (-16, 16):
                value = dict(self.program, parameter_a=a, parameter_b=b)
                self.assertEqual(pm.decode_program(pm.canonical(value)), value)

    def test_parameter_bounds_and_booleans_rejected(self):
        for field in ('parameter_a', 'parameter_b'):
            for value in (-17, 17, True, False, 0.0, None):
                self.reject(**{field: value})

    def test_promotion_index_bounds_are_distinct_from_generation(self):
        for index in (0, pm.MAX_METADATA):
            value = dict(self.program, promotion_index=index)
            self.assertEqual(pm.decode_program(pm.canonical(value)), value)
        for index in (-1, True, False, 0.0, None, 1 << 63):
            self.reject(promotion_index=index)

    def test_nonce_is_complete_lowercase_digest_text(self):
        for value in ('0'*63, '0'*65, 'A'*64, 'g'*64, '', None, 0):
            self.reject(public_nonce_hash=value)

    def test_immutable_complete_bytes_required(self):
        raw = pm.canonical(self.program)
        for value in (bytearray(raw), memoryview(raw), raw[:-1], b'', raw+b'\n', raw+b' ', b' '+raw):
            with self.subTest(kind=type(value)), self.assertRaises(ValueError):
                pm.decode_program(value)

    def test_duplicate_keys_and_noncanonical_key_order_rejected(self):
        raw = pm.canonical(self.program)
        duplicate = b'{"family":"adapter_policy",' + raw[1:]
        reverse = ('{' + ','.join('"'+k+'":'+pm.canonical(self.program[k]).decode() for k in reversed(sorted(self.program))) + '}').encode()
        for data in (duplicate, reverse):
            with self.assertRaises(ValueError):
                pm.decode_program(data)

    def test_escapes_unicode_floating_point_and_trailing_values_rejected(self):
        raw = pm.canonical(self.program)
        for data in (raw.replace(b'"family"', b'"fami\\u006cy"'), raw.replace(b'"generation":2', b'"generation":2.0'),
                     raw+b'{}', raw.replace(b'"family"', '"familÿ"'.encode())):
            with self.assertRaises(ValueError):
                pm.decode_program(data)

    def test_hex_image_is_lowercase_bounded_even_and_not_raw_text(self):
        for text in ('', '0', 'AB', 'gg', '00 ' ,None, b'7b7d', '00'*(pm.MAX_JSON_BYTES+1)):
            with self.subTest(value=type(text)), self.assertRaises(ValueError):
                pm.image_bytes(text)

    def test_json_nonobject_program_rejected(self):
        for raw in (b'null', b'true', b'[]', b'1', b'"program"'):
            with self.assertRaises(ValueError):
                pm.decode_program(raw)


class RegistryProjectionTests(unittest.TestCase):
    def setUp(self):
        self.packet = _packet()

    def reject(self, mutate):
        mutate(self.packet)
        with self.assertRaises((ValueError, KeyError, TypeError)):
            pm._projection(self.packet)

    def test_counts_are_derived_from_both_complete_inherited_inventories(self):
        projection = pm._projection(self.packet)
        for side in ('before', 'after'):
            self.assertEqual(projection['registries'][side]['family_counts'], [1]*8)
        self.assertEqual(len(projection['registries']['after']['programs']), 9)

    def test_after_candidate_does_not_increment_u_predecessor_counts(self):
        projection = pm._projection(self.packet)
        programs = projection['registries']['after']['programs']
        tool_count = sum(program['family'] == 'tool_policy' for program in programs.values())
        self.assertEqual(tool_count, 2)
        self.assertEqual(projection['registries']['after']['family_counts'][6], 1)

    def test_every_decoded_program_matches_actual_q_semantic_inventory(self):
        projection = pm._projection(self.packet)
        joint = self.packet['planner_refinement_packet']['captured_json_packet']['routing_packet']['sparse_packet'][
            'finite_packet']['protected_packet']['joint_packet']
        for side, key in (('before', 'predecessor'), ('after', 'candidate')):
            programs = [projection['registries'][side]['programs'][program_key]
                        for program_key in joint['typed_binding'][key]['base']]
            self.assertEqual(programs, joint['task_meanings'][side]['programs'])

    def test_unrelated_q_semantic_parameter_inventory_cannot_be_used(self):
        def change(packet):
            joint = packet['planner_refinement_packet']['captured_json_packet']['routing_packet']['sparse_packet'][
                'finite_packet']['protected_packet']['joint_packet']
            joint['task_meanings']['before']['programs'][0]['parameter_a'] += 1
        self.reject(change)

    def test_missing_inherited_descriptor_rejected_on_either_side(self):
        for side in ('before', 'after'):
            packet = _packet(); packet['registry_images'][side]['programs'].pop(0)
            with self.assertRaises(ValueError):pm._projection(packet)

    def test_duplicate_descriptor_rejected(self):
        self.reject(lambda p: p['registry_images']['before']['programs'].__setitem__(1, copy.deepcopy(p['registry_images']['before']['programs'][0])))

    def test_registry_order_is_fixed_and_complete(self):
        self.reject(lambda p: p['registry_images']['after']['programs'].reverse())

    def test_extra_unlisted_descriptor_rejected(self):
        self.reject(lambda p: p['registry_images']['before']['programs'].append(copy.deepcopy(p['candidate_images'][0])))

    def test_after_candidate_cannot_replace_inherited_member(self):
        self.reject(lambda p: p['registry_images']['after']['programs'].__setitem__(0, copy.deepcopy(p['candidate_images'][0])))

    def test_no_candidate_in_predecessor_registry(self):
        self.reject(lambda p: _mutate_image(p['registry_images']['before'], lambda m:m.update(candidate_program_hash=p['bindings']['program_hash']), 'manifest_hex'))

    def test_after_candidate_must_be_selected_q_identity(self):
        self.reject(lambda p: _mutate_image(p['registry_images']['after'], lambda m:m.update(candidate_program_hash=p['candidate_images'][0]['key']), 'manifest_hex'))

    def test_inactive_candidate_cannot_be_marked_active(self):
        self.reject(lambda p: _mutate_image(p['registry_images']['after'], lambda m:m.update(candidate_active=True), 'manifest_hex'))

    def test_registry_promotion_authority_cannot_be_enabled_or_numeric(self):
        for value in (True, 0, None):
            packet = _packet(); _mutate_image(packet['registry_images']['after'], lambda m:m.update(promotion_authorized=value), 'manifest_hex')
            with self.assertRaises(ValueError):pm._projection(packet)

    def test_manifest_schema_and_exact_keys_are_checked(self):
        self.reject(lambda p: _mutate_image(p['registry_images']['before'], lambda m:m.update(schema_id='other'), 'manifest_hex'))

    def test_inherited_list_cannot_omit_or_duplicate_members(self):
        self.reject(lambda p: _mutate_image(p['registry_images']['before'], lambda m:m['inherited_program_hashes'].pop(), 'manifest_hex'))

    def test_registry_frontier_cannot_be_caller_selected(self):
        self.reject(lambda p: _mutate_image(p['registry_images']['before'], lambda m:m['inherited_frontier'].pop(), 'manifest_hex'))

    def test_registry_recursive_frontier_cannot_be_caller_selected(self):
        self.reject(lambda p: _mutate_image(p['registry_images']['before'], lambda m:m['recursive_frontier'].pop(), 'manifest_hex'))

    def test_changed_historical_generation_rejected(self):
        self.reject(lambda p: _mutate_image(p['registry_images']['before'], lambda s:s['component_generations'].__setitem__('tool_policy',2), 'historical_state_hex'))

    def test_candidate_state_cannot_replace_retained_predecessor(self):
        self.reject(lambda p: _mutate_image(p['registry_images']['after'], lambda s:s.update(model_index=18), 'historical_state_hex'))

    def test_unbound_state_field_is_still_protected_by_complete_image_hash(self):
        self.reject(lambda p: _mutate_image(p['registry_images']['before'], lambda s:s.update(archive_root_hash='0'*64), 'historical_state_hex'))

    def test_changed_installed_descriptor_cannot_hide_behind_old_key(self):
        self.reject(lambda p: _mutate_image(p['registry_images']['before']['programs'][0], lambda s:s.update(parameter_a=1)))

    def test_rehashing_changed_descriptor_cannot_replace_imported_inventory(self):
        def change(p):
            entry = p['registry_images']['before']['programs'][0]
            _mutate_image(entry, lambda s:s.update(parameter_a=1))
            entry['key'] = pm.planner.public_hash(pm.decoded_image(entry['image_hex']))
        self.reject(change)

    def test_descriptor_key_cannot_include_path_traversal(self):
        self.reject(lambda p: p['registry_images']['before']['programs'][0].update(key='../other'))

    def test_descriptor_image_cannot_have_extra_fields(self):
        self.reject(lambda p: p['registry_images']['before']['programs'][0].update(unchecked=b''))

    def test_inherited_history_generations_must_cover_each_index_once(self):
        key1,key2 = 'a'*64,'b'*64
        program = pm.decode_program(pm.image_bytes(self.packet['registry_images']['before']['programs'][0]['image_hex']))
        with self.assertRaises(ValueError):pm.inherited_counts({key1:program,key2:program},[key1,key2])
        program2 = dict(program,generation=2)
        counts = pm.inherited_counts({key1:program,key2:program2},[key1,key2])
        self.assertEqual(counts[pm.FAMILIES.index(program['family'])],2)


class MetadataRowsTests(unittest.TestCase):
    def setUp(self):
        self.packet = _packet()
        self.rows = self.packet['candidate_images']
        self.ranking = self.packet['planner_refinement_packet']['ranking']

    def reject(self, mutate):
        mutate()
        with self.assertRaises((ValueError, KeyError, TypeError)):
            pm.metadata_rows(self.rows,[1]*8,self.ranking)

    def test_all_32_actual_u_row_inputs_reconstructed(self):
        rows = pm.metadata_rows(self.rows,[1]*8,self.ranking)
        self.assertEqual(len(rows),32)
        self.assertEqual({(r['family'],r['variant']) for r in rows},{(f,v) for f in range(8) for v in range(4)})
        for actual,source in zip(rows,self.ranking['rows'],strict=True):
            self.assertEqual(actual['key'],source['key'])
            self.assertEqual(actual['featureDigest'],source['feature_digest'])
            self.assertEqual(actual['tieDigests'],source['tie_digests'])
            self.assertEqual(actual['generation'],2)
            self.assertEqual(actual['familyCount'],1)

    def test_omitted_or_extra_grammar_rows_rejected(self):
        self.reject(lambda:self.rows.pop())

    def test_reordered_grammar_rows_rejected(self):
        self.reject(self.rows.reverse)

    def test_duplicate_grammar_rows_rejected(self):
        self.reject(lambda:self.rows.__setitem__(1,copy.deepcopy(self.rows[0])))

    def test_changed_external_metadata_key_rejected(self):
        self.reject(lambda:self.rows[0].update(key='0'*64))

    def test_changed_program_family_even_with_valid_operation_rejected(self):
        old = pm.decode_program(pm.image_bytes(self.rows[0]['image_hex']))
        index = (pm.FAMILIES.index(old['family'])+1)%8
        self.reject(lambda:_mutate_image(self.rows[0],lambda p:p.update(family=pm.FAMILIES[index],operation_id=pm.OPERATIONS[index])))

    def test_generation_and_nonce_and_turn_are_context_bound(self):
        for field,value in (('generation',3),('public_nonce_hash','9'*64),('promotion_index',1)):
            rows = copy.deepcopy(self.rows);_mutate_image(rows[0],lambda p:p.update(**{field:value}))
            with self.assertRaises(ValueError):pm.metadata_rows(rows,[1]*8,self.ranking)

    def test_rehashing_parameter_changes_does_not_rebind_actual_u(self):
        def change():
            _mutate_image(self.rows[0],lambda p:p.update(parameter_a=16))
            self.rows[0]['key']=pm.planner.public_hash(pm.decoded_image(self.rows[0]['image_hex']))
        self.reject(change)

    def test_family_count_cannot_include_inactive_candidate(self):
        with self.assertRaises(ValueError):pm.metadata_rows(self.rows,[1,1,1,1,1,1,2,1],self.ranking)

    def test_boolean_count_and_family_index_rejected(self):
        with self.assertRaises(ValueError):pm.metadata_rows(self.rows,[True]*8,self.ranking)
        self.reject(lambda:self.ranking['rows'][0].update(family=True))

    def test_external_digest_fields_must_remain_complete(self):
        for field,value in (('feature_digest','0'*63),('tie_digests',['0'*64]*4)):
            ranking = copy.deepcopy(self.ranking);ranking['rows'][0][field]=value
            with self.assertRaises(ValueError):pm.metadata_rows(self.rows,[1]*8,ranking)


class MetadataPacketTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prepared = _prepared()
        cls.packet = cls.prepared.packet

    def reject(self, mutate):
        packet = copy.deepcopy(self.packet);mutate(packet)
        with self.assertRaises((ValueError, KeyError, TypeError)):
            pm.PreparedProgramMetadata(pm.canonical(packet))

    def test_packet_preserves_exact_u_anchor_and_original_claim_boundaries(self):
        self.assertEqual(self.prepared.planner_refinement().packet_bytes,(ROOT/pm.U_PACKET).read_bytes())
        self.assertEqual(len(self.packet['claims']),24)
        self.assertFalse(any(self.packet['claims'].values()))

    def test_prepared_wrapper_is_immutable_and_returns_isolated_decodings(self):
        with self.assertRaises(FrozenInstanceError):self.prepared.packet_bytes=b'{}'
        packet=self.prepared.packet;packet['bindings']['program_hash']='0'*64
        self.assertNotEqual(packet,self.prepared.packet)

    def test_exact_packet_fields_and_schema_are_required(self):
        self.reject(lambda p:p.update(extra='unchecked'))
        self.reject(lambda p:p.update(schema='other'))
        self.reject(lambda p:p.pop('registry_images'))

    def test_policy_base_and_profile_cannot_change(self):
        self.reject(lambda p:p.update(base_commit='0'*40))
        self.reject(lambda p:p.update(policy='other'))
        self.reject(lambda p:p['profile'].update(package_file_images=20))

    def test_u_packet_cannot_be_replaced_even_if_internal_hash_is_recomputed(self):
        def change(p):
            p['planner_refinement_packet']['ranking']['rows'][0]['family_count']=2
            p['planner_refinement_packet_sha256']=pm.sha(pm.canonical(p['planner_refinement_packet']))
        self.reject(change)

    def test_retained_u_anchors_are_external_constants(self):
        self.reject(lambda p:p['retained_u'].__setitem__(pm.U_EXECUTION,'0'*64))

    def test_selected_candidate_and_package_bindings_cannot_change(self):
        for key in self.packet['bindings']:
            with self.subTest(key=key):self.reject(lambda p,k=key:p['bindings'].__setitem__(k,'0'*64))

    def test_every_broader_claim_remains_strict_false(self):
        for key in pm.FALSE_CLAIMS:
            with self.subTest(key=key):self.reject(lambda p,k=key:p['claims'].__setitem__(k,True))
        self.reject(lambda p:p['claims'].__setitem__('root_transition_verified',0))

    def test_selected_scope_does_not_remove_general_and_hash_boundaries(self):
        for key in ('general_program_metadata_interpretation_remains_external','grammar_parameter_derivation_remains_external',
                    'public_hash_computation_remains_external','byte_capture_remains_external','python_execution_remains_external'):
            self.reject(lambda p,k=key:p['scope'].__setitem__(k,False))
        self.reject(lambda p:p['scope'].update(program_metadata_interpretation_remains_external=False))

    def test_packet_encoding_requires_complete_canonical_immutable_bytes(self):
        for raw in (self.prepared.packet_bytes+b'\n',self.prepared.packet_bytes[:-1],bytearray(self.prepared.packet_bytes),b'{}'):
            with self.assertRaises(ValueError):pm.PreparedProgramMetadata(raw)

    def test_malformed_v_payload_rejected_before_deep_u_revalidation(self):
        packet=copy.deepcopy(self.packet);packet['candidate_images'].pop()
        with patch.object(pm.planner,'PreparedPlannerRefinement',side_effect=AssertionError('deep U must not run')):
            with self.assertRaises(ValueError):pm.PreparedProgramMetadata(pm.canonical(packet))

    def test_external_packet_hash_and_exact_reconstruction_required(self):
        with self.assertRaises(ValueError):pm.verify_packet_bytes(self.prepared.packet_bytes,self.prepared,expected_sha256='0'*64)
        changed=bytearray(self.prepared.packet_bytes);changed[-1]=32
        with self.assertRaises(ValueError):pm.verify_packet_bytes(bytes(changed),self.prepared,expected_sha256=pm.sha(bytes(changed)))

    def test_summary_distinguishes_package_captures_from_reconstructed_descriptors(self):
        summary=pm.summary(self.prepared)
        self.assertEqual(summary['package_file_images'],21)
        self.assertEqual(summary['canonical_grammar_descriptor_images'],32)
        self.assertEqual(summary['installed_programs'],{'before':8,'after':9})
        self.assertEqual(summary['inherited_family_counts'],[1]*8)
        self.assertTrue(summary['candidate_excluded_from_family_counts'])
        self.assertIn('reconstruction',summary['grammar_image_origin'])
        self.assertFalse(summary['candidate_active'])


class PhysicalMetadataPreparationTests(unittest.TestCase):
    def test_fresh_u_packages_and_v_images_reconstruct_without_workers_or_compiler(self):
        with tempfile.TemporaryDirectory(prefix='r17v-test-') as temp:
            with patch('subprocess.Popen',side_effect=AssertionError('no process permitted during preparation')):
                prepared=pm.prepare_program_metadata(ROOT,Path(temp)/'packages')
            self.assertEqual(prepared.packet_bytes,_fixture_bytes())
            pm.verify_packet_bytes(prepared.packet_bytes,prepared,expected_sha256=pm.sha(prepared.packet_bytes))

    def test_missing_retained_inputs_rejected(self):
        with tempfile.TemporaryDirectory() as temp,self.assertRaises(ValueError):pm.read_retained(Path(temp))

    def test_corrupt_retained_inputs_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/pm.U_EXECUTION;path.parent.mkdir(parents=True);path.write_bytes(b'{}')
            with self.assertRaisesRegex(ValueError,'retained U input changed'):pm.read_retained(Path(temp))

    def test_linked_retained_inputs_rejected(self):
        with patch.object(Path,'is_symlink',return_value=True),self.assertRaises(ValueError):pm.read_retained(ROOT)

    def test_capture_preserves_every_complete_file(self):
        image=_packet()['registry_images']['after']
        with tempfile.TemporaryDirectory() as temp:
            files=_write_registry(Path(temp),image)
            actual,captured=pm.capture_registry(Path(temp))
            self.assertEqual(actual,image)
            self.assertEqual(captured,files)

    def test_capture_rejects_extra_registry_file(self):
        with tempfile.TemporaryDirectory() as temp:
            package=Path(temp);_write_registry(package,_packet()['registry_images']['before'])
            (package/'registry'/'extra.json').write_bytes(b'{}')
            with self.assertRaises(ValueError):pm.capture_registry(package)

    def test_capture_rejects_nested_registry_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            package=Path(temp);_write_registry(package,_packet()['registry_images']['before'])
            (package/'registry'/'nested').mkdir()
            with self.assertRaises(ValueError):pm.capture_registry(package)

    def test_capture_rejects_malformed_program_filename(self):
        with tempfile.TemporaryDirectory() as temp:
            package=Path(temp);_write_registry(package,_packet()['registry_images']['before'])
            (package/'registry'/'programs'/'other.json').write_bytes(b'{}')
            with self.assertRaises(ValueError):pm.capture_registry(package)

    def test_capture_rejects_missing_historical_state(self):
        with tempfile.TemporaryDirectory() as temp:
            package=Path(temp);_write_registry(package,_packet()['registry_images']['before'])
            (package/pm.STATE_PATH).unlink()
            with self.assertRaises(ValueError):pm.capture_registry(package)

    def test_capture_rejects_empty_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            package=Path(temp);_write_registry(package,_packet()['registry_images']['before'])
            (package/pm.REGISTRY_PATH).write_bytes(b'')
            with self.assertRaises(ValueError):pm.capture_registry(package)

    def test_capture_rejects_link_metadata_without_platform_symlink_privileges(self):
        with patch.object(Path,'is_symlink',return_value=True),self.assertRaises(ValueError):pm.capture_registry(ROOT)

    def test_missing_after_capture_cannot_reuse_before(self):
        with tempfile.TemporaryDirectory() as temp:
            packages=Path(temp)/'packages';_write_registry(packages/'before',_packet()['registry_images']['before'])
            with patch.object(pm.planner,'prepare_planner_refinement',return_value=_prepared().planner_refinement()):
                with self.assertRaisesRegex(ValueError,'complete registry directory missing'):
                    pm.prepare_program_metadata(ROOT,packages)


class MetadataRendererTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from rcp_rclm_runtime_v5.phase17 import program_metadata_lean as renderer
        cls.renderer=renderer
        cls.sources=renderer.generated_sources(_prepared(),source_root=ROOT)

    def test_exact_dependency_chain_and_control_inventory(self):
        self.assertEqual(list(self.sources),[*self.renderer.DEPENDENCY_LABELS,*self.renderer.LABELS])
        self.assertEqual(len(self.renderer.DEPENDENCY_LABELS),5)
        self.assertEqual(len(self.renderer.NAMES),15)
        self.assertEqual(len(self.renderer.LABELS)-1,12)
        for name in self.renderer.DEPENDENCY_LABELS:self.assertNotIn(b'#print',self.sources[name])
        for name in self.renderer.LABELS:self.assertTrue(self.sources[name].startswith(b'import Phase17UDependency\n'))

    def test_u_dependency_preserves_all_proof_lines_except_exact_audit_commands(self):
        from rcp_rclm_runtime_v5.phase17 import planner_refinement_lean as prior
        original=(ROOT/pm.U_SOURCE).read_bytes()
        audit_lines={('#print axioms '+name+'\n').encode() for name in prior.NAMES}
        expected=b''.join(line for line in original.splitlines(keepends=True) if line not in audit_lines)
        self.assertEqual(self.sources['Phase17UDependency'],expected)
        self.assertEqual(pm.sha(original),pm.U_SOURCE_SHA)

    def test_targets_bind_actual_imported_u_inputs_and_q_selected_update(self):
        source=self.sources['ProgramMetadata'].decode()
        self.assertIn('Phase17Planner.rowInputs',source)
        self.assertIn('Phase17Finite.selectedUpdate.program',source)
        self.assertIn('Phase17Provenance.selectedContext',source)

    def test_every_negative_uses_an_explicit_false_decision_witness(self):
        for label in self.renderer.LABELS[1:]:
            text=self.sources[label].decode()
            with self.subTest(label=label):
                self.assertIn('theorem control_false :',text)
                self.assertIn('of_decide_eq_false control_false',text)
                self.assertIn('decide +kernel',text)
                self.assertNotIn('#print axioms',text)

    def test_renderer_source_guards_reject_shortcuts_and_placeholders(self):
        original=self.renderer.template(ROOT)
        for suffix in (b'\nexample : True := by native_decide\n',b'\nexample : True := by decide +native\n',
                       b'\nexample : True := by decide + native\n',b'\nexample : True := by sorry\n',
                       b'\naxiom counterfeit : False\n',b'\nunsafe def counterfeit : Nat := 0\n',
                       b'\npartial def counterfeit : Nat := 0\n'):
            with self.subTest(suffix=suffix),patch.object(self.renderer,'template',return_value=original+suffix):
                with self.assertRaises(ValueError):
                    self.renderer._render_validated(_prepared(),source_root=ROOT,negative='ChangedMetadataKey')

    def test_template_pin_detects_even_nonsemantic_mutation(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);path=root/self.renderer.BRIDGE_PATH
            path.parent.mkdir(parents=True);path.write_bytes(self.renderer.template(ROOT)+b'\n')
            with self.assertRaises(ValueError):self.renderer.template(root)

    def test_renderer_requires_prepared_wrapper_and_known_control(self):
        with self.assertRaises(ValueError):self.renderer.generated_sources(_packet(),source_root=ROOT)
        with self.assertRaises(ValueError):self.renderer.render(_prepared(),source_root=ROOT,negative='invented')


if __name__ == '__main__':
    unittest.main()
