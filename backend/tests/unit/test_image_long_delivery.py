from copy import deepcopy

import pytest

from app.agents.image_long import validate_long_image_review


def long_asset():
    digest = 'a' * 64
    return {
        'delivery': {'mode': 'best_available', 'candidate_id': 'full0002',
                     'sha256': digest, 'score': 80, 'stop_reason': 'quality_repair_limit'},
        'candidates': [{'candidate_id': 'full0002', 'status': 'quality_failed'}],
        'long_image_review': {
            'candidate_id': 'full0002', 'width': 750, 'height': 3000, 'sha256': digest,
            'sections': [dict(section_id=f's{i}', y=i * 1000, width=750, height=1000,
                              status='quality_failed', quality={'passed': False},
                              copy_audit={'passed': False}) for i in range(3)],
        },
    }


BODY = {'request': {'long_image': {'width': 750, 'segment_count': 3}}}


def direct_asset():
    asset = long_asset()
    asset['delivery'].update(mode='direct', score=None, stop_reason='generation_completed')
    asset['candidates'][0]['status'] = 'succeeded'
    for i, section in enumerate(asset['long_image_review']['sections']):
        section.update(status='succeeded', quality=None, copy_audit=None,
                       delivery=dict(mode='direct', candidate_id=f'c{i}', sha256='b' * 64,
                                     score=None, stop_reason='generation_completed'))
    return asset


def test_direct_long_delivery_requires_no_model_reviews():
    validate_long_image_review(direct_asset(), BODY)


@pytest.mark.parametrize('mutation', ['gap', 'count', 'digest', 'failed', 'section_delivery'])
def test_direct_long_delivery_still_requires_complete_bound_sections(mutation):
    asset = direct_asset()
    review = asset['long_image_review']
    if mutation == 'gap':
        review['sections'][1]['y'] += 1
    elif mutation == 'count':
        review['sections'].pop()
    elif mutation == 'digest':
        asset['delivery']['sha256'] = 'c' * 64
    elif mutation == 'failed':
        review['sections'][0]['status'] = 'failed'
    else:
        review['sections'][0].pop('delivery')
    with pytest.raises(ValueError):
        validate_long_image_review(asset, BODY)


def test_best_available_long_accepts_real_failed_section_audits():
    validate_long_image_review(long_asset(), BODY)


def test_best_available_long_accepts_unavailable_audits():
    asset = long_asset()
    for section in asset['long_image_review']['sections']:
        section.update(status='audit_error', quality=None, copy_audit=None)
    validate_long_image_review(asset, BODY)


@pytest.mark.parametrize('mutation', [
    'no_delivery', 'candidate', 'digest', 'stage', 'missing_section', 'gap', 'duplicate',
])
def test_long_best_delivery_keeps_completeness_and_identity_checks(mutation):
    asset = deepcopy(long_asset())
    review = asset['long_image_review']
    if mutation == 'no_delivery':
        asset.pop('delivery')
    elif mutation == 'candidate':
        asset['delivery']['candidate_id'] = 'unrelated'
    elif mutation == 'digest':
        asset['delivery']['sha256'] = 'b' * 64
    elif mutation == 'stage':
        asset['candidates'][0]['status'] = 'stage'
    elif mutation == 'missing_section':
        review['sections'].pop()
    elif mutation == 'gap':
        review['sections'][1]['y'] += 1
    else:
        review['sections'][1]['section_id'] = review['sections'][0]['section_id']
    with pytest.raises(ValueError):
        validate_long_image_review(asset, BODY)
