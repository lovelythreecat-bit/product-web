"""Real MySQL admission, chain persistence and last-free-use serialization."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from uuid import uuid4

import test_task_admission as admission_tests
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.tasks.models import GenerationTask, TaskSnapshot

admission = admission_tests.admission
catalog = admission_tests.catalog


def completed_fixture(c, task_id):
    # Scope is regeneration admission, not upstream generation/publication. This
    # fixture supplies a prior completed task without dispatching a real provider.
    with c.engine.begin() as connection:
        connection.execute(update(GenerationTask).where(GenerationTask.id == task_id).values(
            state='SUCCEEDED'))


def regeneration_quote(c, source, body):
    response = c.client.post(f'/api/v1/tasks/{source}/regeneration-quote', json={
        'agent_id': body['agent_id'], 'input': body['input'],
    })
    assert response.status_code == 200, response.text
    return response.json()


def regeneration_body(source, body, quote):
    return {**deepcopy(body), 'confirmed_quote': quote['quote'], 'regeneration': {
        'source_task_id': source, 'expected_credits': quote['credits'],
        'expected_used': quote['free_regenerations_used'],
    }}


def test_three_free_uses_persist_and_concurrent_last_use_requotes(admission):
    c = admission
    body = admission_tests.request_body(c)
    original = admission_tests.submit(c, body)
    assert original.status_code == 201, original.text
    source = original.json()['task']['task_id']
    completed_fixture(c, source)
    versions = [source]

    for used in range(2):
        quote = regeneration_quote(c, source, body)
        assert quote['credits'] == 0 and quote['free_regenerations_used'] == used
        response = admission_tests.submit(c, regeneration_body(source, body, quote))
        assert response.status_code == 201, response.text
        assert response.json()['task']['quote']['credits'] == 0
        versions.append(response.json()['task']['task_id'])
        completed_fixture(c, versions[-1])

    quote = regeneration_quote(c, source, body)
    assert quote['free_regenerations_remaining'] == 1
    pending = regeneration_body(source, body, quote)
    keys = [uuid4().hex, uuid4().hex]
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda key: admission_tests.submit(c, pending, key), keys))
    assert sorted(response.status_code for response in responses) == [201, 409], [
        response.text for response in responses]
    accepted_index = next(i for i, response in enumerate(responses) if response.status_code == 201)
    rejected = next(response for response in responses if response.status_code == 409)
    assert rejected.json()['error']['code'] == 'QUOTE_STALE'
    replay = admission_tests.submit(c, pending, keys[accepted_index])
    assert replay.status_code == 200 and replay.json()['replayed'] is True
    versions.append(replay.json()['task']['task_id'])
    completed_fixture(c, versions[-1])

    # Starting from the old root still sees all three uses. A fresh confirmation
    # is required before any paid fourth regeneration can be admitted.
    quote = regeneration_quote(c, source, body)
    assert quote['free_regenerations_used'] == 3 and quote['credits'] == 7
    paid = admission_tests.submit(c, regeneration_body(source, body, quote))
    assert paid.status_code == 201, paid.text
    assert paid.json()['task']['quote']['credits'] == 7
    latest = paid.json()['task']['task_id']
    versions.append(latest)
    detail = c.client.get(f'/api/v1/tasks/{latest}')
    assert detail.status_code == 200, detail.text
    assert detail.json()['regeneration'] == dict(root_task_id=source,
        free_regenerations_used=3, free_regenerations_remaining=0)
    history = c.client.get(f'/api/v1/tasks/{latest}/history')
    assert history.status_code == 200, history.text
    assert {item['task']['task_id'] for item in history.json()} == set(versions[:-1])
    assert admission_tests.counts(c)['balances'] == (86, 14, 0)
    with Session(c.engine) as session:
        snapshots = session.scalars(select(TaskSnapshot).where(
            TaskSnapshot.task_id.in_(versions))).all()
        assert sorted(snapshot.quote['credits'] for snapshot in snapshots) == [0, 0, 0, 7, 7]
        assert all(snapshot.quote['credits'] == snapshot.price_snapshot['credits']
                   for snapshot in snapshots)


def test_edited_content_is_paid_and_does_not_receive_inherited_entitlement(admission):
    c = admission
    body = admission_tests.request_body(c)
    original = admission_tests.submit(c, body)
    source = original.json()['task']['task_id']
    completed_fixture(c, source)
    body['input']['instruction'] = 'Changed instruction'
    quote = regeneration_quote(c, source, body)
    assert quote['eligible'] is False and quote['credits'] == 7
    result = admission_tests.submit(c, regeneration_body(source, body, quote))
    assert result.status_code == 201, result.text
    task_id = result.json()['task']['task_id']
    with Session(c.engine) as session:
        assert 'regeneration' not in session.get(TaskSnapshot, task_id).price_snapshot
