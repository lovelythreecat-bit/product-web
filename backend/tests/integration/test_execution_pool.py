"""Real MySQL coordination across independent worker instances."""

from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from app.agents.execution_pool import TextExecutionPool, text_scope


def test_independent_workers_share_six_slots_and_released_slot_runs_next(mysql_engine):
    factory = sessionmaker(mysql_engine)
    scope = uuid4().hex
    pools = [TextExecutionPool(factory, 6) for _ in range(10)]
    with ThreadPoolExecutor(max_workers=10) as executor:
        tokens = list(executor.map(lambda pool: pool.acquire(scope), pools))
    acquired = [token for token in tokens if token]
    assert len(acquired) == 6
    try:
        assert TextExecutionPool(factory, 6).acquire(scope) is None
        pools[0].release(scope, acquired.pop())
        next_token = pools[-1].acquire(scope)
        assert next_token is not None
        acquired.append(next_token)
        assert pools[0].acquire(scope) is None
    finally:
        for token in acquired:
            pools[0].release(scope, token)


def test_abandoned_slot_expires_without_releasing_someone_elses_slot(mysql_engine):
    factory = sessionmaker(mysql_engine)
    scope = uuid4().hex
    pool = TextExecutionPool(factory, 1)
    abandoned = pool.acquire(scope)
    assert pool.acquire(scope) is None
    with factory.begin() as session:
        session.execute(text("UPDATE upstream_execution_pools SET holders=:holders "
                             "WHERE scope_key=:scope"),
                        {"scope": scope, "holders": '{"' + abandoned + '":0}'})
    replacement = pool.acquire(scope)
    assert replacement is not None
    pool.release(scope, abandoned)
    assert pool.acquire(scope) is None
    pool.release(scope, replacement)


def test_text_capacity_is_shared_across_equivalent_origins():
    assert text_scope("http://LOCALHOST") == text_scope("http://localhost:80/")
    assert text_scope("http://localhost:8000") != text_scope("http://localhost:8001")
