"""Validate the product long-image composition and its section review evidence."""
import re


def validate_long_image_review(asset, body):
    delivery = asset.get('delivery')
    best = isinstance(delivery, dict) and delivery.get('mode') == 'best_available'
    direct = isinstance(delivery, dict) and delivery.get('mode') == 'direct'
    review = asset.get('long_image_review')
    if not isinstance(review, dict):
        raise ValueError('Long image composition review missing')
    options = body.get('request', body).get('long_image') or {}
    width = options.get('width', 750)
    count = options.get('segment_count', 6)
    if (type(review.get('width')) is not int or review['width'] != width
            or type(review.get('height')) is not int or not 1 <= review['height'] <= 60000
            or not isinstance(review.get('sha256'), str)
            or not re.fullmatch(r'[a-f0-9]{64}', review['sha256'])):
        raise ValueError('Invalid long image composition dimensions/digest')
    candidates = asset.get('candidates')
    if not isinstance(candidates, list):
        raise ValueError('Long image has no final candidate')
    selected = [c for c in candidates if isinstance(c, dict)
                and c.get('candidate_id') == review.get('candidate_id')]
    if (not review.get('candidate_id') or len(selected) != 1
            or (selected[0].get('status') in (None, 'stage') if best
                else selected[0].get('status') != 'succeeded')):
        raise ValueError('Long image review is not bound to a completed candidate')
    if (best or direct) and (delivery.get('candidate_id') != review['candidate_id']
                 or delivery.get('sha256') != review['sha256']):
        raise ValueError('Long image delivery differs from composition review')
    sections = review.get('sections')
    if not isinstance(sections, list) or len(sections) != count:
        raise ValueError('Long image section count mismatch')
    ids, y = set(), 0
    for section in sections:
        if not isinstance(section, dict):
            raise ValueError('Invalid long image section')
        key = section.get('section_id')
        quality, copy = section.get('quality') or {}, section.get('copy_audit') or {}
        if (not isinstance(key, str) or not key or key in ids
                or section.get('status') not in (
                    {'succeeded', 'quality_failed', 'audit_error', 'pending_audit',
                     'budget_exhausted', 'generation_uncertain'} if best else {'succeeded'})
                or type(section.get('y')) is not int or section['y'] != y
                or type(section.get('width')) is not int or section['width'] != width
                or type(section.get('height')) is not int or section['height'] < 1):
            raise ValueError('Long image section is incomplete')
        if direct:
            section_delivery = section.get('delivery') or {}
            if (section.get('quality') is not None or section.get('copy_audit') is not None
                    or section_delivery.get('mode') != 'direct'
                    or section_delivery.get('score') is not None
                    or not isinstance(section_delivery.get('candidate_id'), str)
                    or not section_delivery['candidate_id']
                    or not re.fullmatch(r'[a-f0-9]{64}', str(section_delivery.get('sha256', '')))):
                raise ValueError('Invalid unaudited long image section delivery')
        if not best and not direct and (
            not isinstance(quality, dict) or quality.get('passed') is not True
            or quality.get('failed_checks') or quality.get('critical_failed_checks')
            or not isinstance(quality.get('deterministic_checks'), dict)
            or quality['deterministic_checks'].get('passed') is not True
            or not isinstance(copy, dict)
            or any(copy.get(k) is not True for k in (
                'passed', 'text_matches', 'no_invented_claims', 'layout_readable'))
        ):
            raise ValueError('Long image section is unapproved without a delivery decision')
        ids.add(key)
        y += section['height']
    if y != review['height']:
        raise ValueError('Long image section boundaries do not cover the final image')
