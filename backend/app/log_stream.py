import asyncio
import json
import logging
from collections import deque
from datetime import datetime, timezone
from typing import AsyncIterator

_backlog: deque = deque(maxlen=500)
_clients: list[asyncio.Queue] = []
_loop: asyncio.AbstractEventLoop | None = None


class LogStreamHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            entry = {
                "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
                "level": record.levelname,
                "name": record.name,
                "message": record.getMessage(),
            }
            _backlog.append(entry)
            if _loop and _loop.is_running():
                for q in list(_clients):
                    _loop.call_soon_threadsafe(_safe_put, q, entry)
        except Exception:
            pass


def _safe_put(q: asyncio.Queue, entry: dict) -> None:
    try:
        q.put_nowait(entry)
    except asyncio.QueueFull:
        pass


def install() -> None:
    global _loop
    _loop = asyncio.get_running_loop()
    handler = LogStreamHandler()
    handler.setLevel(logging.DEBUG)
    logging.getLogger().addHandler(handler)


async def stream_logs() -> AsyncIterator[str]:
    queue: asyncio.Queue = asyncio.Queue(maxsize=500)
    for entry in list(_backlog):
        yield f"data: {json.dumps(entry)}\n\n"
    _clients.append(queue)
    try:
        while True:
            try:
                entry = await asyncio.wait_for(queue.get(), timeout=15.0)
                yield f"data: {json.dumps(entry)}\n\n"
            except asyncio.TimeoutError:
                yield ": keepalive\n\n"
    finally:
        try:
            _clients.remove(queue)
        except ValueError:
            pass
