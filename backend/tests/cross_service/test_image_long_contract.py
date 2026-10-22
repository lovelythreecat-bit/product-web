"""Exercise the sibling's real pipeline/HTTP DTO and web delivery without providers."""
import asyncio
import importlib
import socket
import sys
from copy import deepcopy
from pathlib import Path

import pytest


@pytest.fixture
def image_modules(monkeypatch):
    sibling = Path(__file__).resolve().parents[4] / 'imageAgent'
    if not (sibling / 'src/image_agent/pipeline.py').is_file():
        pytest.skip('Requires sibling imageAgent checkout')
    monkeypatch.syspath_prepend(str(sibling))
    monkeypatch.syspath_prepend(str(sibling / 'src'))
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2]))
    monkeypatch.setattr(sys, 'path', [*sys.path, str(sibling / '.venv/Lib/site-packages')])
    original_modules = set(sys.modules)
    test_package = None
    original_attributes = set()
    try:
        # Web's tests package is already imported during full-suite collection.
        # Expose sibling helpers without replacing Web's package or its fixtures.
        test_package = importlib.import_module('tests')
        original_attributes = set(vars(test_package))
        monkeypatch.setattr(test_package, '__path__', [
            *test_package.__path__, str(sibling / 'tests'),
        ])
        yield (
            importlib.import_module('image_agent.contracts'),
            importlib.import_module('image_agent.pipeline'),
            importlib.import_module('tests.test_product_long_image_pipeline'),
        )
    finally:
        for name in set(sys.modules) - original_modules:
            if name == 'tests' or name.startswith('tests.'):
                del sys.modules[name]
        if test_package is not None:
            for name in set(vars(test_package)) - original_attributes:
                delattr(test_package, name)


@pytest.mark.parametrize('platform', [
    'amazon', 'taobao', 'tmall', 'jd', 'pinduoduo', 'shopee', 'lazada', 'shein', 'temu',
])
def test_real_white_request_and_targets_keep_selected_platform(image_modules, platform):
    contracts, _, _ = image_modules
    from image_agent.models import ImageSource
    from image_agent.prompt import build_targets
    dto = contracts.CreationRequestDTO(
        product_name='Cup', category='kitchen', platforms=[platform],
        output_types=['pdd_white_background'], materials=[dict(material_id='m1', media_id='m1')],
    )
    request = contracts.request_from_dto(dto, {'m1': ImageSource(data=b'x')})
    targets = build_targets(request, 'model_wear')
    assert len(targets) == 1 and targets[0].platform == platform
    assert targets[0].presentation_mode == 'product_only'


@pytest.mark.parametrize('best', [False, True, 'direct'])
def test_real_long_pipeline_public_dto_delivers_and_recovers_in_web(
    image_modules, monkeypatch, best,
):
    contracts, pipeline, support = image_modules
    from hashlib import sha256

    from image_agent.config import AgentConfig
    from image_agent.execution import ExecutionPolicy
    from image_agent.server.task_service import sanitize_public_model

    from app.agents.image import ImageAgentAdapter, ImageAgentProfile

    connect = socket.socket.connect
    def denied(sock, *args, **kwargs):
        caller = sys._getframe(1)
        if caller.f_globals.get('__name__') == 'socket' and 'socketpair' in caller.f_code.co_name:
            return connect(sock, *args, **kwargs)
        raise AssertionError('No network/provider calls permitted')

    monkeypatch.setattr(socket.socket, 'connect', denied)
    request, deps, _, _ = support.long_setup(dict(
        product_name='Cup', category='kitchen', platforms=['taobao'], output_types=['long_image'],
        materials=[dict(material_id='m1', source={'data': b'x'})],
    ), scores={'main': [{'identity': 60, 'same': False}]} if best else None)
    result = asyncio.run(pipeline.run_pipeline(request, AgentConfig(), dependencies=deps,
        policy=ExecutionPolicy(max_quality_repairs=0, review_generated_images=best != 'direct')))
    assert result.status == 'succeeded'
    bundle = contracts.result_to_bundle(result)
    digest = sha256(next(iter(bundle.blobs.values()))).hexdigest()
    public = sanitize_public_model(
        contracts.CreationResultDTO, bundle.dto, ['TEST_ONLY_private'], Path('C:/private'),
        trusted_hashes={digest}, identity_key='TEST_ONLY_key',
    ).model_dump(mode='json')
    review = public['assets'][0]['long_image_review']
    assert review['sha256'] == digest and len(review['sections']) == 6
    if best == 'direct':
        assert public['assets'][0]['delivery']['mode'] == 'direct'
        assert all(s['quality'] is None and s['copy_audit'] is None for s in review['sections'])
    elif best:
        assert public['assets'][0]['delivery']['mode'] == 'best_available'
        assert all(s['quality']['passed'] is False for s in review['sections'])
        assert public['warnings']
    assert 'C:/private' not in str(public) and 'plan_ref' not in str(review)
    obj = ImageAgentAdapter(profile=ImageAgentProfile(
        base_url='http://127.0.0.1:8100', service_key='TEST_ONLY', agent_config_id='a',
    ))
    state = {'scope': obj.retry_scope(), 'upstream_task_id': 'original'}
    obj.load_state = lambda: deepcopy(state)
    obj.save_state = lambda patch: state.update(deepcopy(patch))
    obj.client = type('Client', (), {'download': lambda _, path: (
        bundle.blobs[path.rsplit('/', 1)[-1]], 'image/png',
    )})()
    body = {'request': {'platforms': ['taobao'], 'output_types': ['long_image'],
                        'long_image': {'width': 750, 'segment_count': 6}}}
    manifest = obj._manifest('original', body, public)
    assert manifest.expected_items == 1 and manifest.items[0].sha256 == digest
    state['manifest'] = manifest.model_dump(mode='json')
    assert obj.retrieve_original(manifest.items[0].locator).status == 'AVAILABLE'
    for mutation in ('missing', 'count', 'quality', 'copy', 'duplicate', 'boundary',
                     'width', 'height', 'digest', 'candidate', 'stage'):
        bad = deepcopy(public)
        asset = bad['assets'][0]
        proof = asset['long_image_review']
        if mutation == 'missing':
            del asset['long_image_review']
        elif mutation == 'count':
            proof['sections'].pop()
        elif mutation == 'quality':
            if best == 'direct':
                proof['sections'][0]['quality'] = {'passed': True}
            else:
                proof['sections'][0]['quality']['passed'] = False
        elif mutation == 'copy':
            if best == 'direct':
                proof['sections'][0]['copy_audit'] = {'text_matches': True}
            else:
                proof['sections'][0]['copy_audit']['text_matches'] = False
        elif mutation == 'duplicate':
            proof['sections'][1]['section_id'] = proof['sections'][0]['section_id']
        elif mutation == 'boundary':
            proof['sections'][1]['y'] += 1
        elif mutation == 'width':
            proof['width'] += 1
        elif mutation == 'height':
            proof['height'] += 1
        elif mutation == 'digest':
            proof['sha256'] = 'a' * 64
        elif mutation == 'candidate':
            proof['candidate_id'] = 'unrelated'
        else:
            asset['candidates'][-1]['status'] = 'stage'
        if best is True and mutation in ('quality', 'copy'):
            assert obj._manifest('original', body, bad).expected_items == 1
            continue
        with pytest.raises(ValueError):
            obj._manifest('original', body, bad)


def test_all_image_outputs_deliver_best_when_repairs_are_exhausted(image_modules):
    _, pipeline, support = image_modules
    from image_agent.config import AgentConfig
    from image_agent.execution import ExecutionPolicy

    failed = [{'identity': 60, 'same': False}]
    request, deps, _, _ = support.long_setup(dict(
        product_name='Cup', category='kitchen', platforms=['taobao'],
        output_types=['long_image'], materials=[dict(material_id='m1', source={'data': b'x'})],
    ), scores={key: failed for key in ('main', 'scene', 'feature', 'closeup')})
    request.output_types = ['main_image', 'detail_page', 'pdd_white_background', 'long_image']
    result = asyncio.run(pipeline.run_pipeline(request, AgentConfig(), dependencies=deps,
        policy=ExecutionPolicy(max_quality_repairs=0)))
    assert result.status == 'succeeded'
    assert len(result.assets) == 6
    assert {a.output_type for a in result.assets} == set(request.output_types)
    assert all(a.image and a.delivery for a in result.assets)
