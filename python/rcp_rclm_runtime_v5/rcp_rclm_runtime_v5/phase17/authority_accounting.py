"""AN's explicit accounting coverage contract and nonpromoting admission.

Amounts use one declared accounting unit chosen by this contract. Observations
and meter digests are declarations to be checked against separately retained
evidence; their syntactic presence is never physical completeness. Unknown work
has a null amount, not an invented zero. This reference backend cannot authorize
a promotion-bearing campaign, including when every declaration is populated.
"""
from __future__ import annotations

from .resource_ledger import canonical, exact, nat, require, sha, digest, PROFILE

SCHEMA = 'phase17an.accounting-coverage.v1'
UNIT = 'declared_accounting_units'
CATEGORIES = (
    'reference_evaluator',
    'controller_and_planning',
    'admission_and_reservation',
    'authentication_and_pki',
    'transport_and_protocol',
    'hashing_and_source_binding',
    'journal_and_persistence',
    'process_startup_and_ipc',
    'evidence_capture_and_reconstruction',
    'formal_verification_and_tests',
    'host_cpu_gpu_memory',
    'storage_network_energy',
    'deployment_and_provisioning',
    'historical_and_broader_campaign',
)
MAX_AMOUNT = 2 ** 63 - 1


def _amount(value):
    nat(value)
    require(value <= MAX_AMOUNT, 'accounting amount exceeds finite profile')
    return value


def reference_coverage(budget=4480):
    """Declare the inherited reference allowance and every missing category."""
    _amount(budget)
    rows = [{'category': name, 'observed': None, 'upper_bound': None, 'meter': ''}
            for name in CATEGORIES]
    rows[0].update(upper_bound=budget, meter=sha(canonical({'reference_profile': PROFILE})))
    return {'schema': SCHEMA, 'unit': UNIT, 'required_categories': list(CATEGORIES),
            'coverage': rows, 'budget': budget}


def validate_coverage(value):
    exact(value, {'schema', 'unit', 'required_categories', 'coverage', 'budget'})
    require(value['schema'] == SCHEMA and value['unit'] == UNIT and
            value['required_categories'] == list(CATEGORIES),
            'fixed complete category inventory or accounting unit differs')
    _amount(value['budget'])
    rows = value['coverage']
    require(type(rows) is list and len(rows) == len(CATEGORIES),
            'exact ordered accounting coverage required')
    for name, row in zip(CATEGORIES, rows):
        exact(row, {'category', 'observed', 'upper_bound', 'meter'})
        require(row['category'] == name, 'accounting category omitted, duplicated or reordered')
        observed, bound, meter = row['observed'], row['upper_bound'], row['meter']
        require(type(meter) is str, 'accounting meter identity must be a string')
        if meter:
            digest(meter)
        if observed is not None:
            _amount(observed)
            require(bound is not None and bool(meter),
                    'observed accounting requires a bound and identified meter')
        if bound is not None:
            _amount(bound)
            require(bool(meter), 'declared accounting bound requires an identified meter')
        if observed is not None:
            require(observed <= bound, 'observed work exceeds declared category bound')
        require(meter == '' or observed is not None or bound is not None,
                'meter identity without a declared bound or observation')
    # Round-trip only through the project's canonical byte encoding.
    from rcp_rclm_runtime.canonical.json import load_json_strict
    return load_json_strict(canonical(value), require_canonical=True)


def coverage_report(value):
    value = validate_coverage(value)
    known = [r for r in value['coverage'] if r['observed'] is not None]
    unknown = [r['category'] for r in value['coverage'] if r['observed'] is None]
    missing_bounds = [r['category'] for r in value['coverage'] if r['upper_bound'] is None]
    observed = sum(r['observed'] for r in known)
    reserved = sum(r['upper_bound'] for r in value['coverage'] if r['upper_bound'] is not None)
    within_budget = reserved <= value['budget']
    return {'schema': 'phase17an.accounting-coverage-report.v1',
            'contract_sha256': sha(canonical(value)), 'required_categories': list(CATEGORIES),
            'unknown_categories': unknown, 'unbounded_categories': missing_bounds,
            'known_observed_subtotal': observed, 'known_bound_subtotal': reserved,
            'total_observed_declared_units': None if unknown else observed,
            'total_bounded_declared_units': None if missing_bounds else reserved,
            'budget': value['budget'], 'declared_bounds_fit_budget': within_budget,
            'all_categories_observed_and_bounded': not unknown and not missing_bounds and within_budget,
            'declarations_are_physical_attestation': False,
            'complete_resource_accounting': False}


def admission_report(value, *, mode='reference'):
    require(mode in ('reference', 'promotion'), 'unknown campaign admission mode')
    coverage = coverage_report(value)
    reasons = []
    if not coverage['declared_bounds_fit_budget']:
        reasons.append('declared_bounds_exceed_budget')
    if mode == 'promotion':
        if coverage['unknown_categories']:
            reasons.append('accounting_categories_unobserved')
        if coverage['unbounded_categories']:
            reasons.append('accounting_categories_unbounded')
        reasons.extend(['independent_provisioning_not_established',
                        'protected_production_principal_not_established',
                        'physical_currentness_and_exclusivity_not_established',
                        'complete_accounting_evidence_not_established',
                        'root_promotion_acceptance_not_established',
                        'reference_backend_cannot_authorize_promotion'])
    return {'schema': 'phase17an.campaign-admission.v1', 'mode': mode,
            'admitted': not reasons, 'denial_reasons': reasons, 'coverage': coverage,
            'promotion_authorized': False, 'promotion_performed': False,
            'independently_protected_deployment_established': False,
            'complete_resource_accounting': False}
