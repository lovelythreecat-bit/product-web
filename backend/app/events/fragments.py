"""TEST_ONLY local fixture hub. Real D-01 upstream fragment integration stays disabled.

Bounded, per-connection queues have no replay, sequence or billing semantics.
No public write endpoint exists. Publishers must already be trusted internal test code.
"""

from collections import deque
from threading import Lock
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select

from app.events.schemas import TransientFragment
from app.tasks.models import GenerationTask


class TestFragmentHub:
    def __init__(self):
        self._lock = Lock()
        self._subscribers = {}

    def subscribe(self, user_id):
        key = uuid4().hex
        with self._lock:
            self._subscribers[key] = (str(user_id), deque(maxlen=32))
        return key

    def unsubscribe(self, key):
        with self._lock:
            self._subscribers.pop(key, None)

    def publish(self, session, user_id, task_id, fragment):
        user_id, task_id = str(user_id), str(task_id)
        owned = session.scalar(
            select(GenerationTask.id).where(
                GenerationTask.id == task_id,
                GenerationTask.user_id == user_id,
            )
        )
        if owned is None:
            raise HTTPException(404)
        data = TransientFragment(task_id=task_id, text=fragment).model_dump_json()
        with self._lock:
            for owner, queue in self._subscribers.values():
                if owner == user_id:
                    queue.append(data)

    def pop(self, key, user_id):
        with self._lock:
            entry = self._subscribers.get(key)
            if entry and entry[0] == str(user_id) and entry[1]:
                return entry[1].popleft()
        return None
