import asyncio
from collections.abc import Callable
from typing import Any, TypeVar, cast

import pytest

from a_sync.primitives import Event

_F = TypeVar("_F", bound=Callable[..., Any])
asyncio_cooperative = cast(Callable[[_F], _F], pytest.mark.asyncio_cooperative)

@asyncio_cooperative
async def test_event_basic_functionality() -> None:
    event = Event()
    assert not event.is_set()
    event.set()
    assert event.is_set()
    event.clear()
    assert not event.is_set()


@asyncio_cooperative
async def test_event_wait() -> None:
    event = Event()

    async def waiter() -> str:
        await event.wait()
        return "done"

    waiter_task = asyncio.create_task(waiter())
    await asyncio.sleep(0.1)  # Ensure the waiter is waiting
    event.set()
    result = await waiter_task
    assert result == "done"


@asyncio_cooperative
async def test_event_multiple_waiters() -> None:
    event = Event()
    results: list[int] = []

    async def waiter(index: int) -> None:
        await event.wait()
        results.append(index)

    tasks = [asyncio.create_task(waiter(i)) for i in range(5)]
    await asyncio.sleep(0.1)  # Ensure all waiters are waiting
    event.set()
    await asyncio.gather(*tasks)
    assert results == [0, 1, 2, 3, 4]


@asyncio_cooperative
async def test_event_reset() -> None:
    event = Event()
    event.set()
    assert event.is_set()
    event.clear()
    assert not event.is_set()

    async def waiter() -> str:
        await event.wait()
        return "done"

    waiter_task = asyncio.create_task(waiter())
    await asyncio.sleep(0.1)  # Ensure the waiter is waiting
    event.set()
    result = await waiter_task
    assert result == "done"


@asyncio_cooperative
async def test_event_timeout() -> None:
    event = Event()

    async def waiter() -> str | None:
        try:
            await asyncio.wait_for(event.wait(), timeout=0.1)
        except asyncio.TimeoutError:
            return "timeout"
        return None

    result = await waiter()
    assert result == "timeout"


@asyncio_cooperative
async def test_event_cancellation() -> None:
    event = Event()

    async def waiter() -> str | None:
        try:
            await event.wait()
        except asyncio.CancelledError:
            return "cancelled"
        return None

    waiter_task = asyncio.create_task(waiter())
    await asyncio.sleep(0.1)  # Ensure the waiter is waiting
    waiter_task.cancel()
    result = await waiter_task
    assert result == "cancelled"


@asyncio_cooperative
async def test_event_set_already_set() -> None:
    event = Event()
    event.set()
    assert event.is_set()
    event.set()  # Set again, should have no adverse effect
    assert event.is_set()


@asyncio_cooperative
async def test_event_clear_already_cleared() -> None:
    event = Event()
    event.clear()  # Clear when already cleared, should have no adverse effect
    assert not event.is_set()


@asyncio_cooperative
async def test_event_wait_after_set() -> None:
    event = Event()
    event.set()

    async def waiter() -> bool:
        return bool(await event.wait())

    result = await waiter()
    assert result is True


@asyncio_cooperative
async def test_event_wait_after_clear() -> None:
    event = Event()
    event.set()
    event.clear()

    async def waiter() -> str | None:
        try:
            await asyncio.wait_for(event.wait(), timeout=0.1)
        except asyncio.TimeoutError:
            return "timeout"
        return None

    result = await waiter()
    assert result == "timeout"


@asyncio_cooperative
async def test_simultaneous_set_and_wait() -> None:
    event = Event()
    results: list[int] = []

    async def waiter(index: int) -> None:
        await event.wait()
        results.append(index)

    tasks = [asyncio.create_task(waiter(i)) for i in range(5)]
    event.set()
    await asyncio.gather(*tasks)
    assert results == [0, 1, 2, 3, 4]


@asyncio_cooperative
async def test_reentrant_set() -> None:
    event = Event()
    event.set()
    event.set()  # Reentrant set
    assert event.is_set()


@asyncio_cooperative
async def test_large_number_of_waiters() -> None:
    event = Event()
    num_waiters = 1000
    results: list[int] = []

    async def waiter(index: int) -> None:
        await event.wait()
        results.append(index)

    tasks = [asyncio.create_task(waiter(i)) for i in range(num_waiters)]
    event.set()
    await asyncio.gather(*tasks)
    assert results == list(range(num_waiters))


@asyncio_cooperative
async def test_event_with_no_waiters() -> None:
    event = Event()
    event.set()
    event.clear()
    assert not event.is_set()


@asyncio_cooperative
async def test_immediate_set_and_wait() -> None:
    event = Event()
    event.set()

    async def waiter() -> bool:
        return bool(await event.wait())

    result = await waiter()
    assert result is True


@asyncio_cooperative
async def test_event_with_exception_handling() -> None:
    event = Event()

    async def waiter() -> str:
        try:
            await event.wait()
            raise ValueError("Intentional error")
        except ValueError as e:
            return str(e)

    event.set()
    result = await waiter()
    assert result == "Intentional error"


@asyncio_cooperative
async def test_event_with_loop_reentrancy() -> None:
    event = Event()

    async def loop_task() -> None:
        for _ in range(3):
            event.set()
            await event.wait()
            event.clear()

    await loop_task()


@asyncio_cooperative
async def test_event_with_delayed_set() -> None:
    event = Event()

    async def waiter() -> str:
        await event.wait()
        return "done"

    waiter_task = asyncio.create_task(waiter())
    await asyncio.sleep(0.5)  # Delay before setting the event
    event.set()
    result = await waiter_task
    assert result == "done"


@asyncio_cooperative
async def test_event_with_multiple_clears() -> None:
    event = Event()
    event.clear()
    event.clear()  # Multiple clears
    assert not event.is_set()
