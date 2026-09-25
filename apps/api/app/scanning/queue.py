from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import Request

Enqueue = Callable[..., Awaitable[Any]]


def get_enqueue(request: Request) -> Enqueue:
    """Queue a background job on the ARQ worker (overridden in tests)."""
    pool = request.app.state.arq

    async def enqueue(name: str, *args: Any) -> Any:
        return await pool.enqueue_job(name, *args)

    return enqueue
