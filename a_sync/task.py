
import asyncio
import logging
from typing import Any, Awaitable, Optional, Set, TypeVar

_T = TypeVar('_T')

logger = logging.getLogger(__name__)

def create_task(awaitable: Awaitable[_T], *, name: Optional[str] = None, skip_gc_until_done: bool = False) -> "asyncio.Task[_T]":
    """A wrapper over `asyncio.create_task` which will work with any `Awaitable` object, not just `Coroutine` objects"""
    coro = awaitable if asyncio.iscoroutine(awaitable) else __await(awaitable)
    task = asyncio.create_task(coro, name=name)
    if skip_gc_until_done:
        __persist(task)
    return task

__persisted_tasks: Set["asyncio.Task[Any]"] = set()

async def __await(awaitable: Awaitable[_T]) -> _T:
    return await awaitable

def __persist(task: "asyncio.Task[Any]") -> None:
    __persisted_tasks.add(task)
    __prune_persisted_tasks()

def __prune_persisted_tasks():
    for task in __persisted_tasks:
        if task.done():
            if e := task.exception():
                logger.exception(e)
                raise e
            __persisted_tasks.discard(task)