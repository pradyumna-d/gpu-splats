from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class EventMessage:
    event: str
    data: dict[str, Any]

    def encode(self) -> str:
        payload = json.dumps(self.data, default=str)
        return f"event: {self.event}\ndata: {payload}\n\n"


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[str, set[asyncio.Queue[EventMessage]]] = defaultdict(set)
        self._latest: dict[str, EventMessage] = {}
        self._lock = asyncio.Lock()

    async def publish(self, job_id: str, event: str, data: dict[str, Any]) -> None:
        message = EventMessage(event=event, data=data)
        async with self._lock:
            self._latest[job_id] = message
            subscribers = list(self._subscribers[job_id])

        for queue in subscribers:
            if queue.full():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            queue.put_nowait(message)

    async def stream(self, job_id: str) -> AsyncIterator[str]:
        queue: asyncio.Queue[EventMessage] = asyncio.Queue(maxsize=16)
        async with self._lock:
            self._subscribers[job_id].add(queue)
            latest = self._latest.get(job_id)
        if latest:
            queue.put_nowait(latest)

        try:
            while True:
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=15)
                    yield message.encode()
                except TimeoutError:
                    yield ": keep-alive\n\n"
        finally:
            async with self._lock:
                self._subscribers[job_id].discard(queue)

