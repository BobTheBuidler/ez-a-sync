import asyncio
from collections.abc import Callable
from typing import Any, TypeVar, cast

import pytest

from a_sync import PrioritySemaphore

_F = TypeVar("_F", bound=Callable[..., Any])
asyncio_cooperative = cast(Callable[[_F], _F], pytest.mark.asyncio_cooperative)

def test_prio_semaphore_init() -> None:
    assert PrioritySemaphore(1)._value == 1
    with_name = PrioritySemaphore(10, name="test")
    assert with_name._value == 10 and with_name.name == "test"


@asyncio_cooperative
async def test_prio_semaphore_count_waiters() -> None:
    semaphore = PrioritySemaphore(1)
    tasks = [asyncio.create_task(semaphore[i].acquire()) for i in range(5)]
    await asyncio.sleep(1)
    print(semaphore)


@asyncio_cooperative
async def test_prio_semaphore_use() -> None:
    semaphore = PrioritySemaphore(1)
    assert semaphore._value == 1
    await semaphore.acquire()
    assert semaphore._value == 0
    semaphore.release()
    assert semaphore._value == 1

    cm = semaphore[100]
    async with cm:
        assert semaphore._value == 0
    assert semaphore._value == 1
    async with semaphore:
        assert semaphore._value == 0
    assert semaphore._value == 1
